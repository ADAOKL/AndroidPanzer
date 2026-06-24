"""Core Extractor – zieht alle Artefakte vom Gerät via ADB/Root.

Jede Extraktor-Funktion:
  1. Prüft Verfügbarkeit / Root-Voraussetzung
  2. Zieht die Rohdaten (DB-Pull oder ADB-Shell-Query)
  3. Delegiert Parsing an parsers.py
  4. Gibt strukturierte Model-Objekte zurück
"""
from __future__ import annotations

import os
import re
import tempfile
import time
from apz.adb import ADB
from apz.util import shq

from .config import APaths, KNOWN_STORES, SUSPICIOUS_PERMISSIONS
from .models import (
    InstallRecord, SearchRecord, UsageRecord, ApkArtifact,
    VersionEntry, ForensicReport,
)
from .parsers import (
    parse_frosting_db, parse_frosting_db_from_device_output,
    parse_suggestions_db, parse_suggestions_from_device_output,
    parse_usage_stats_directory, parse_packages_xml,
)
from .utils import (
    file_exists_on_device, dir_exists_on_device, pull_db_via_sdcard,
    sqlite_query_on_device, list_tables, detect_db_encryption,
    list_third_party_packages, get_installer, get_dumpsys_package,
    extract_strings_from_apk, ensure_output_dir, epoch_to_human,
)


# ---------------------------------------------------------------------------
# Installations-Historie (dumpsys + frosting.db)
# ---------------------------------------------------------------------------

def extract_install_history(adb: ADB, st: dict, progress_cb=None) -> list[InstallRecord]:
    """Extrahiert vollständige Installations-Historie.

    Quellen (nach Priorität):
      1. frosting.db (Root, vollständige Historie inkl. alter Versionen)
      2. dumpsys package <pkg> (ohne Root, aktuelle Infos)
    """
    records: list[InstallRecord] = []
    is_root = st.get("is_root", False)

    # --- Quelle 1: frosting.db (Root) ---
    if is_root:
        for db_path in (APaths.FROSTING_DB,
                        APaths.VENDING_DB_DIR + "/frosting.db"):
            if not file_exists_on_device(adb, db_path, root=True):
                continue

            if detect_db_encryption(adb, db_path, root=True):
                break  # verschlüsselt → kein direkter Zugriff

            # Direkte DB-Abfrage auf Gerät
            raw = sqlite_query_on_device(
                adb, db_path,
                "SELECT packageName,versionCode,versionName,"
                "firstInstallTime,lastUpdateTime,installerPackageName "
                "FROM frosting_pkgs ORDER BY firstInstallTime DESC LIMIT 2000",
                root=True,
            )
            if raw.strip() and "|" in raw:
                records = parse_frosting_db_from_device_output(raw)
                if records:
                    break

            # Fallback: DB-Pull + lokales Parsen
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
                tmp = tf.name
            try:
                if pull_db_via_sdcard(adb, db_path, tmp, root=True):
                    records = parse_frosting_db(tmp)
                    if records:
                        break
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    # --- Quelle 2: dumpsys (immer verfügbar) ---
    pkgs = list_third_party_packages(adb)
    existing_pkgs = {r.package for r in records}

    for i, pkg in enumerate(pkgs):
        if progress_cb:
            progress_cb(i, len(pkgs), pkg)

        if pkg in existing_pkgs:
            continue  # Bereits aus frosting.db bekannt

        raw = get_dumpsys_package(adb, pkg)
        rec = InstallRecord.from_dumpsys(pkg, raw)
        records.append(rec)

    records.sort(key=lambda r: r.first_install, reverse=True)
    return records


# ---------------------------------------------------------------------------
# Suchhistorie (suggestions.db)
# ---------------------------------------------------------------------------

def extract_search_history(adb: ADB, st: dict) -> list[SearchRecord]:
    """Extrahiert Play-Store-Suchhistorie aus suggestions.db."""
    is_root = st.get("is_root", False)
    if not is_root:
        return [SearchRecord(
            query="[Root benötigt – suggestions.db liegt in /data/data/com.android.vending/]",
            timestamp="—", source="info",
        )]

    results: list[SearchRecord] = []

    for db_path in (APaths.SUGGESTIONS_DB,
                    APaths.VENDING_DB_DIR + "/suggest.db",
                    APaths.VENDING_DB_DIR + "/search.db"):
        if not file_exists_on_device(adb, db_path, root=True):
            continue

        if detect_db_encryption(adb, db_path, root=True):
            results.append(SearchRecord(
                query=f"[VERSCHLÜSSELT: {db_path}]", timestamp="—",
            ))
            continue

        # Tabellenstruktur aufklären
        tables = list_tables(adb, db_path, root=True)
        target_table = None
        for t in tables:
            if any(kw in t.lower() for kw in ("suggest", "search", "query", "hist")):
                target_table = t
                break
        if not target_table and tables:
            target_table = tables[0]

        if not target_table:
            continue

        raw = sqlite_query_on_device(
            adb, db_path,
            f"SELECT * FROM [{target_table}] ORDER BY rowid DESC LIMIT 5000",
            root=True,
        )
        if raw.strip():
            parsed = parse_suggestions_from_device_output(raw)
            results.extend(parsed)
            break

        # Fallback: Pull
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tmp = tf.name
        try:
            if pull_db_via_sdcard(adb, db_path, tmp, root=True):
                from .parsers import parse_suggestions_db
                results.extend(parse_suggestions_db(tmp))
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    if not results:
        results.append(SearchRecord(
            query="[Keine suggestions.db gefunden oder leer]",
            timestamp="—", source="info",
        ))

    return results


# ---------------------------------------------------------------------------
# Nutzungsstatistiken (usagestats)
# ---------------------------------------------------------------------------

def extract_usage_stats(adb: ADB, st: dict) -> list[UsageRecord]:
    """Extrahiert App-Nutzungszeiten via dumpsys usagestats."""
    records: list[UsageRecord] = []

    # Methode 1: dumpsys usagestats (Shell-Berechtigung reicht oft)
    raw = adb.shell("dumpsys usagestats", timeout=45)
    if raw.strip():
        records = parse_usage_stats_directory(raw)

    # Methode 2: XML-Dateien direkt (Root)
    if not records and st.get("is_root"):
        xml_path = APaths.APP_USAGE_XML
        if file_exists_on_device(adb, xml_path, root=True):
            xml_content = adb.shell(f"cat {shq(xml_path)} 2>/dev/null", root=True)
            if xml_content.strip():
                from .parsers import parse_usage_stats_xml
                records = parse_usage_stats_xml(xml_content)

    # Methode 3: Verzeichnisliste (Root)
    if not records and st.get("is_root"):
        if dir_exists_on_device(adb, APaths.USAGE_STATS_DIR, root=True):
            files = adb.shell(
                f"find {APaths.USAGE_STATS_DIR} -name '*.xml' 2>/dev/null",
                root=True
            ).splitlines()
            for f in files[:5]:
                xml_content = adb.shell(f"cat {shq(f.strip())} 2>/dev/null", root=True)
                if xml_content.strip():
                    from .parsers import parse_usage_stats_xml
                    records.extend(parse_usage_stats_xml(xml_content))

    records.sort(key=lambda r: r.fg_time_ms, reverse=True)
    return records


# ---------------------------------------------------------------------------
# Versions-Timeline (packages.xml)
# ---------------------------------------------------------------------------

def extract_version_timeline(adb: ADB, st: dict) -> list[VersionEntry]:
    """Extrahiert Versionszeitlinie aus packages.xml (Root) und dumpsys."""
    timeline: list[VersionEntry] = []

    if st.get("is_root") and file_exists_on_device(adb, APaths.PACKAGES_XML, root=True):
        xml = adb.shell(f"cat {shq(APaths.PACKAGES_XML)} 2>/dev/null", root=True, timeout=30)
        if xml.strip():
            timeline = parse_packages_xml(xml)

    # Fallback ohne Root: dumpsys package für alle Pakete
    if not timeline:
        pkgs = list_third_party_packages(adb)
        for pkg in pkgs[:50]:
            raw = get_dumpsys_package(adb, pkg)
            rec = InstallRecord.from_dumpsys(pkg, raw)
            if rec.first_install != "—":
                timeline.append(VersionEntry(
                    package=pkg, version_name=rec.version_name,
                    version_code=rec.version_code,
                    timestamp=rec.first_install, event_type="INSTALL",
                ))
            if rec.last_update != "—" and rec.last_update != rec.first_install:
                timeline.append(VersionEntry(
                    package=pkg, version_name=rec.version_name,
                    version_code=rec.version_code,
                    timestamp=rec.last_update, event_type="UPDATE",
                ))

    timeline.sort(key=lambda e: e.timestamp)
    return timeline


# ---------------------------------------------------------------------------
# APK Deep Scan (statische Analyse)
# ---------------------------------------------------------------------------

def extract_apk_artifacts(
    adb: ADB, st: dict, pkgs: list[str] | None = None,
    progress_cb=None,
) -> list[ApkArtifact]:
    """Statische Analyse installierter APKs auf dem Gerät.

    Analysiert Permissions, Hardcoded IPs/URLs und verdächtige Strings.
    Kein APK-Pull – alles direkt auf dem Gerät via grep/strings.
    """
    artifacts: list[ApkArtifact] = []
    is_root = st.get("is_root", False)

    if pkgs is None:
        pkgs = list_third_party_packages(adb)

    for i, pkg in enumerate(pkgs):
        if progress_cb:
            progress_cb(i, len(pkgs), pkg)

        # APK-Pfad ermitteln
        apk_path = ""
        pm_out = adb.shell(f"pm path {shq(pkg)}")
        m = re.search(r"package:(\S+)", pm_out)
        if m:
            apk_path = m.group(1)
        if not apk_path:
            continue

        art = ApkArtifact(package=pkg, apk_path=apk_path)

        # Permissions via pm dump
        pm_dump = adb.shell(f"pm dump {shq(pkg)} | grep -A 1000 'declared permissions'", timeout=15)
        for perm in SUSPICIOUS_PERMISSIONS:
            if perm in pm_dump:
                art.suspicious_perms.append(perm)

        # String-Analyse
        strings_data = extract_strings_from_apk(adb, apk_path, root=is_root)
        art.hardcoded_ips = [ip for ip in strings_data.get("ips", [])
                              if not ip.startswith("127.") and ip != "0.0.0.0"]
        art.strings_of_interest = strings_data.get("secrets", [])[:10]

        # Signatur prüfen
        sig_out = adb.shell(f"pm verify {shq(pkg)} 2>/dev/null")
        art.signature_valid = "verified" in sig_out.lower() or not sig_out.strip()

        art.assess_risk()
        artifacts.append(art)

    return artifacts


# ---------------------------------------------------------------------------
# Vollständige Geräte-Info
# ---------------------------------------------------------------------------

def collect_device_info(adb: ADB, st: dict) -> dict:
    return {
        "model":          adb.getprop("ro.product.model"),
        "manufacturer":   adb.getprop("ro.product.manufacturer"),
        "android_version": adb.getprop("ro.build.version.release"),
        "sdk_version":    adb.getprop("ro.build.version.sdk"),
        "serial":         adb.serial or "unknown",
        "root":           "ja" if st.get("is_root") else "nein",
        "build_id":       adb.getprop("ro.build.id"),
        "security_patch": adb.getprop("ro.build.version.security_patch"),
        "fingerprint":    adb.getprop("ro.build.fingerprint"),
    }


# ---------------------------------------------------------------------------
# SharedPreferences Extractor
# ---------------------------------------------------------------------------

def extract_shared_preferences(
    adb: ADB, pkgs: list[str], st: dict,
) -> list[dict]:
    """Liest SharedPreferences aller Apps – sucht API-Keys, Tokens, URLs."""
    from .parsers import parse_shared_prefs_xml

    is_root = st.get("is_root", False)
    if not is_root:
        return [{
            "pkg": "[Root benötigt]", "error": "Kein Root-Zugriff",
            "urls_found": [], "ips_found": [], "api_keys_found": [],
        }]

    results: list[dict] = []

    for pkg in pkgs:
        prefs_dir = f"/data/data/{pkg}/shared_prefs"
        ls_out = adb.shell(f"ls {shq(prefs_dir)} 2>/dev/null", root=True)
        xml_files = [
            f.strip() for f in ls_out.splitlines()
            if f.strip().endswith(".xml")
        ]
        if not xml_files:
            continue

        pkg_result: dict = {
            "pkg": pkg,
            "prefs_files": len(xml_files),
            "urls_found": [],
            "ips_found": [],
            "api_keys_found": [],
            "raw_keys": {},
        }

        for xml_f in xml_files[:10]:
            content = adb.shell(
                f"cat {shq(prefs_dir + '/' + xml_f)} 2>/dev/null",
                root=True,
            )
            if not content.strip():
                continue
            parsed = parse_shared_prefs_xml(content)
            pkg_result["urls_found"].extend(parsed.get("urls_found", []))
            pkg_result["ips_found"].extend(parsed.get("ips_found", []))
            pkg_result["api_keys_found"].extend(parsed.get("api_keys_found", []))
            pkg_result["raw_keys"].update(parsed.get("keys", {}))

        pkg_result["urls_found"]     = list(dict.fromkeys(pkg_result["urls_found"]))[:20]
        pkg_result["ips_found"]      = list(dict.fromkeys(pkg_result["ips_found"]))[:20]
        pkg_result["api_keys_found"] = list(dict.fromkeys(pkg_result["api_keys_found"]))[:20]
        results.append(pkg_result)

    return results


# ---------------------------------------------------------------------------
# App-Datenbank-Inventar
# ---------------------------------------------------------------------------

def extract_app_databases(
    adb: ADB, pkgs: list[str], st: dict,
) -> list[dict]:
    """Inventarisiert alle SQLite-Datenbanken pro App (Tabellen, Größe, WAL)."""
    from .utils import list_tables, sqlite_query_on_device

    is_root = st.get("is_root", False)
    if not is_root:
        return [{
            "pkg": "[Root benötigt]", "db_path": "—",
            "is_encrypted": False, "has_wal": False,
            "total_size_bytes": 0, "row_counts": {},
        }]

    inventory: list[dict] = []

    for pkg in pkgs:
        db_dir  = f"/data/data/{pkg}/databases"
        ls_out  = adb.shell(f"ls -la {shq(db_dir)} 2>/dev/null", root=True)

        db_files: list[dict] = []
        for line in ls_out.splitlines():
            parts = line.split()
            if not parts:
                continue
            fname = parts[-1]
            if not any(fname.endswith(ext) for ext in (".db", ".sqlite", ".sqlite3")):
                continue
            size = 0
            try:
                size = int(parts[4]) if len(parts) >= 5 else 0
            except (ValueError, IndexError):
                pass
            db_files.append({"name": fname, "size": size})

        for db_info in db_files[:5]:
            db_path = f"{db_dir}/{db_info['name']}"
            entry: dict = {
                "pkg": pkg,
                "db_path": db_path,
                "is_encrypted": False,
                "has_wal": False,
                "total_size_bytes": db_info["size"],
                "row_counts": {},
                "tables": [],
            }

            wal_check = adb.shell(
                f"ls {shq(db_path + '-wal')} 2>/dev/null", root=True,
            ).strip()
            if wal_check:
                entry["has_wal"] = True
                wal_sz = adb.shell(
                    f"wc -c < {shq(db_path + '-wal')} 2>/dev/null", root=True,
                ).strip()
                try:
                    entry["wal_size_bytes"] = int(wal_sz)
                except ValueError:
                    pass

            entry["is_encrypted"] = detect_db_encryption(adb, db_path, root=True)

            if not entry["is_encrypted"]:
                tables = list_tables(adb, db_path, root=True)
                entry["tables"] = tables[:20]
                for tbl in tables[:10]:
                    cnt_raw = sqlite_query_on_device(
                        adb, db_path,
                        f"SELECT COUNT(*) FROM [{tbl}]",
                        root=True,
                    ).strip()
                    try:
                        entry["row_counts"][tbl] = int(cnt_raw.splitlines()[-1])
                    except (ValueError, IndexError):
                        entry["row_counts"][tbl] = -1

            inventory.append(entry)

    return inventory


# ---------------------------------------------------------------------------
# Payment Forensics
# ---------------------------------------------------------------------------

def extract_payment_forensics(adb: ADB, st: dict) -> dict:
    """Extrahiert Zahlungsdaten aus billing.db / acquire.db."""
    from .parsers import parse_billing_db

    is_root = st.get("is_root", False)
    result: dict = {"source": "—", "purchases": [], "subscriptions": []}

    if is_root:
        billing_candidates = [
            APaths.VENDING_DB_DIR + "/billing.db",
            APaths.VENDING_DB_DIR + "/acquire.db",
            APaths.VENDING_DB_DIR + "/purchase.db",
        ]
        for db_path in billing_candidates:
            if not file_exists_on_device(adb, db_path, root=True):
                continue
            if detect_db_encryption(adb, db_path, root=True):
                result["source"] = f"[VERSCHLÜSSELT: {db_path}]"
                continue
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
                tmp = tf.name
            try:
                if pull_db_via_sdcard(adb, db_path, tmp, root=True):
                    records = parse_billing_db(tmp)
                    result["source"] = db_path
                    for rec in records:
                        if any(kw in rec.get("status", "").lower()
                               for kw in ("sub", "renew", "active", "recurring")):
                            result["subscriptions"].append(rec)
                        else:
                            result["purchases"].append(rec)
                    if records:
                        break
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    if not result["purchases"] and not result["subscriptions"]:
        raw = adb.shell("dumpsys account", timeout=20)
        if "com.android.vending" in raw.lower():
            result["source"] = "dumpsys account (kein Root)"
            for line in raw.splitlines():
                if "com.google" in line.lower() or "vending" in line.lower():
                    result["purchases"].append({
                        "item": line.strip()[:80],
                        "timestamp": "—",
                        "price": "—",
                        "status": "info",
                    })

    return result


# ---------------------------------------------------------------------------
# Account Token Metadaten
# ---------------------------------------------------------------------------

def extract_account_tokens(adb: ADB, st: dict) -> list[dict]:
    """Extrahiert Account-Metadaten (KEINE Token-Werte)."""
    from .parsers import parse_accounts_db

    is_root = st.get("is_root", False)
    results: list[dict] = []

    if is_root:
        accounts_candidates = [
            "/data/system/users/0/accounts.db",
            "/data/system_de/0/accounts.db",
            "/data/system/accounts.db",
        ]
        for db_path in accounts_candidates:
            if not file_exists_on_device(adb, db_path, root=True):
                continue
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
                tmp = tf.name
            try:
                if pull_db_via_sdcard(adb, db_path, tmp, root=True):
                    results = parse_accounts_db(tmp)
                    if results:
                        break
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    if not results:
        raw = adb.shell("dumpsys account", timeout=20)
        _acct_re = re.compile(r'Account\s*\{name=([^,]+),\s*type=([^}]+)\}')
        for m in _acct_re.finditer(raw):
            name_raw  = m.group(1).strip()
            acct_type = m.group(2).strip()
            if "@" in name_raw:
                user, domain = name_raw.split("@", 1)
                masked = f"{user[:2]}{'*' * max(0, len(user)-2)}@{domain}"
            elif len(name_raw) > 4:
                masked = name_raw[:2] + "*" * (len(name_raw) - 2)
            else:
                masked = "****"
            results.append({
                "account_type":        acct_type,
                "account_name_masked": masked,
                "token_count":         0,
                "source":              "dumpsys",
            })

    return results


# ---------------------------------------------------------------------------
# Clipboard History
# ---------------------------------------------------------------------------

def extract_clipboard_history(adb: ADB, st: dict) -> list[dict]:
    """Extrahiert Zwischenablagen-Historie (geräteabhängig, Root bevorzugt)."""
    import sqlite3 as _sqlite3

    is_root = st.get("is_root", False)
    results: list[dict] = []

    _CLIPBOARD_DBS = [
        "/data/data/com.sec.android.clipboard/databases/clipboard.db",
        "/data/data/com.samsung.android.clipboard/databases/clipboard.db",
        "/data/system/clipboard.db",
    ]

    if is_root:
        for db_path in _CLIPBOARD_DBS:
            if not file_exists_on_device(adb, db_path, root=True):
                continue
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
                tmp = tf.name
            try:
                if pull_db_via_sdcard(adb, db_path, tmp, root=True):
                    try:
                        conn = _sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
                        cur  = conn.cursor()
                        cur.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )
                        tables = [r[0] for r in cur.fetchall()]
                        for tbl in tables:
                            try:
                                cur.execute(
                                    f"SELECT * FROM [{tbl}] ORDER BY rowid DESC LIMIT 200"
                                )
                                cols = [d[0] for d in cur.description]
                                for row in cur.fetchall():
                                    d    = dict(zip(cols, row))
                                    text = str(
                                        d.get("data") or d.get("text") or
                                        d.get("content") or d.get("clip_data") or ""
                                    )
                                    if len(text) > 2:
                                        results.append({
                                            "text": text[:200],
                                            "timestamp": epoch_to_human(
                                                d.get("timestamp") or d.get("date") or ""
                                            ),
                                            "source": db_path,
                                        })
                            except _sqlite3.Error:
                                pass
                        conn.close()
                    except _sqlite3.Error:
                        pass
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

        if not results:
            clip_dir = "/data/system/clipboard/"
            ls_out = adb.shell(f"ls {shq(clip_dir)} 2>/dev/null", root=True)
            for fname in ls_out.splitlines():
                fname = fname.strip()
                if fname:
                    content = adb.shell(
                        f"cat {shq(clip_dir + fname)} 2>/dev/null", root=True
                    ).strip()
                    if content:
                        results.append({
                            "text": content[:200],
                            "timestamp": "—",
                            "source": f"clipboard_dir/{fname}",
                        })

    if not results:
        results.append({
            "text": "[Keine Zwischenablagen-Daten gefunden oder kein Root]",
            "timestamp": "—",
            "source": "info",
        })

    return results
