"""SQLite & XML Parser für alle Play-Store-Artefakte.

Jede Funktion arbeitet ausschließlich auf dem Host (lokale Datei oder
ADB-Abfrage-Ergebnis als String). Kein direkter ADB-Zugriff hier.
"""
from __future__ import annotations

import re
import os
import sqlite3
import xml.etree.ElementTree as ET
from typing import Optional

from .models import InstallRecord, SearchRecord, UsageRecord, VersionEntry, _fmt_ts
from .utils import epoch_to_human


# ---------------------------------------------------------------------------
# frosting.db Parser
# ---------------------------------------------------------------------------

def parse_frosting_db(local_path: str) -> list[InstallRecord]:
    """Parst frosting.db lokal und gibt InstallRecord-Liste zurück.

    Schema (typisch Android 10+):
      frosting_pkgs(packageName TEXT, versionCode INTEGER, ...)
    """
    records: list[InstallRecord] = []
    if not os.path.exists(local_path):
        return records

    conn = None
    try:
        conn = sqlite3.connect(f"file:{local_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        if "frosting_pkgs" in tables:
            _parse_frosting_pkgs(cur, records)
        elif "installed_apps" in tables:
            _parse_installed_apps(cur, records)
        elif tables:
            _parse_generic_table(cur, tables[0], records)

    except sqlite3.Error as e:
        records.append(InstallRecord(
            package=f"[PARSE ERROR: {e}]",
            first_install="—", last_update="—",
        ))
    finally:
        if conn:
            conn.close()

    return records


def _parse_frosting_pkgs(cur: sqlite3.Cursor, out: list[InstallRecord]) -> None:
    try:
        cur.execute("SELECT * FROM frosting_pkgs LIMIT 2000")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            pkg = d.get("packageName") or d.get("package_name") or "unknown"
            vc  = str(d.get("versionCode") or d.get("version_code") or "—")
            vn  = str(d.get("versionName") or d.get("version_name") or "—")
            fi  = epoch_to_human(d.get("firstInstallTime") or d.get("first_install_time"))
            lu  = epoch_to_human(d.get("lastUpdateTime")  or d.get("last_update_time"))
            inst = str(d.get("installerPackageName") or d.get("installer") or "—")
            out.append(InstallRecord(
                package=pkg, version_code=vc, version_name=vn,
                first_install=fi, last_update=lu, installer=inst,
            ))
    except sqlite3.Error:
        pass


def _parse_installed_apps(cur: sqlite3.Cursor, out: list[InstallRecord]) -> None:
    try:
        cur.execute("SELECT * FROM installed_apps LIMIT 2000")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            pkg = str(d.get("package") or d.get("packageName") or "unknown")
            out.append(InstallRecord(
                package=pkg,
                first_install=epoch_to_human(d.get("install_time")),
                last_update=epoch_to_human(d.get("update_time")),
                installer=str(d.get("installer") or "—"),
            ))
    except sqlite3.Error:
        pass


def _parse_generic_table(cur: sqlite3.Cursor, table: str, out: list[InstallRecord]) -> None:
    try:
        cur.execute(f"SELECT * FROM [{table}] LIMIT 500")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            # Suche nach Paketname-Feld
            pkg = "unknown"
            for key in ("packageName", "package_name", "package", "pkg"):
                if key in d and d[key]:
                    pkg = str(d[key])
                    break
            if pkg != "unknown":
                out.append(InstallRecord(package=pkg))
    except sqlite3.Error:
        pass


def parse_frosting_db_from_device_output(raw: str) -> list[InstallRecord]:
    """Parst ADB-sqlite3-Ausgabe (pipe-separated) als Fallback."""
    records: list[InstallRecord] = []
    lines = raw.strip().splitlines()
    if not lines:
        return records

    header = lines[0].split("|")
    for line in lines[1:]:
        parts = line.split("|")
        if len(parts) < 2:
            continue
        d = dict(zip(header, parts))
        pkg = d.get("packageName") or d.get("package_name") or parts[0]
        records.append(InstallRecord(
            package=pkg.strip(),
            version_code=d.get("versionCode", "—").strip(),
            version_name=d.get("versionName", "—").strip(),
            first_install=epoch_to_human(d.get("firstInstallTime", "").strip()),
            last_update=epoch_to_human(d.get("lastUpdateTime", "").strip()),
            installer=d.get("installerPackageName", "—").strip(),
        ))
    return records


# ---------------------------------------------------------------------------
# suggestions.db Parser
# ---------------------------------------------------------------------------

def parse_suggestions_db(local_path: str) -> list[SearchRecord]:
    """Parst suggestions.db lokal."""
    records: list[SearchRecord] = []
    if not os.path.exists(local_path):
        return records

    conn = None
    try:
        conn = sqlite3.connect(f"file:{local_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        target = None
        for t in ("suggestions", "search_history", "queries"):
            if t in tables:
                target = t
                break
        if not target and tables:
            target = tables[0]

        if target:
            cur.execute(f"SELECT * FROM [{target}] ORDER BY rowid DESC LIMIT 5000")
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                query = (d.get("query") or d.get("search_text") or
                         d.get("suggestion") or d.get("display1") or "")
                if not query:
                    continue
                ts_raw = (d.get("timestamp") or d.get("date") or
                          d.get("last_access") or d.get("_id") or "")
                records.append(SearchRecord(
                    query=str(query).strip(),
                    timestamp=epoch_to_human(ts_raw),
                    source=str(d.get("source") or "search"),
                ))
    except sqlite3.Error as e:
        records.append(SearchRecord(query=f"[PARSE ERROR: {e}]"))
    finally:
        if conn:
            conn.close()

    return records


def parse_suggestions_from_device_output(raw: str) -> list[SearchRecord]:
    """Parst ADB-sqlite3-Ausgabe für suggestions."""
    records: list[SearchRecord] = []
    lines = raw.strip().splitlines()
    if not lines:
        return records
    header = lines[0].split("|")
    for line in lines[1:]:
        parts = line.split("|")
        if len(parts) < 1:
            continue
        d = dict(zip(header, parts))
        query = d.get("query") or d.get("display1") or (parts[0] if parts else "")
        if query and not query.startswith("["):
            ts = epoch_to_human(d.get("timestamp") or d.get("date") or "")
            records.append(SearchRecord(query=query.strip(), timestamp=ts))
    return records


# ---------------------------------------------------------------------------
# usagestats XML Parser
# ---------------------------------------------------------------------------

def parse_usage_stats_xml(xml_content: str) -> list[UsageRecord]:
    """Parst app_usage_stats.xml oder usagestats-Verzeichnisinhalt."""
    records: list[UsageRecord] = []
    if not xml_content.strip():
        return records

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return records

    # Format 1: <package name="..." totalTimeInForeground="..." lastTimeUsed="..."/>
    for el in root.iter():
        pkg = el.get("name") or el.get("package")
        if not pkg or "." not in pkg:
            continue
        fg_ms = int(el.get("totalTimeInForeground") or el.get("totalTime") or 0)
        last  = epoch_to_human(el.get("lastTimeUsed") or el.get("lastUsed") or "")
        first = epoch_to_human(el.get("firstTimeStamp") or "")
        count = int(el.get("launchCount") or el.get("count") or 0)
        records.append(UsageRecord(
            package=pkg,
            date_bucket=first,
            fg_time_ms=fg_ms,
            last_used=last,
            launch_count=count,
        ))

    return records


def parse_usage_stats_directory(adb_output: str) -> list[UsageRecord]:
    """Parst `dumpsys usagestats` Output."""
    records: list[UsageRecord] = []
    current_pkg: Optional[str] = None
    fg_ms = 0
    last_used = "—"
    count = 0

    for line in adb_output.splitlines():
        line = line.strip()

        # Neues Paket beginnt
        pm = re.match(r"^package=(\S+)", line)
        if pm:
            if current_pkg:
                records.append(UsageRecord(
                    package=current_pkg, fg_time_ms=fg_ms,
                    last_used=last_used, launch_count=count,
                ))
            current_pkg = pm.group(1)
            fg_ms = 0; last_used = "—"; count = 0
            continue

        m = re.search(r"totalTimeInForeground=(\d+)", line)
        if m:
            fg_ms = int(m.group(1))

        m = re.search(r"lastTimeUsed=(\d+)", line)
        if m:
            last_used = epoch_to_human(m.group(1))

        m = re.search(r"launchCount=(\d+)", line)
        if m:
            count = int(m.group(1))

    if current_pkg:
        records.append(UsageRecord(
            package=current_pkg, fg_time_ms=fg_ms,
            last_used=last_used, launch_count=count,
        ))

    return records


# ---------------------------------------------------------------------------
# packages.xml Parser (Version-Timeline)
# ---------------------------------------------------------------------------

_PKG_RE = re.compile(
    r'<package name="([^"]+)"[^>]*'
    r'(?:codePath="([^"]*)")?[^>]*'
    r'(?:version="([^"]*)")?[^>]*'
    r'(?:ft="([^"]*)")?[^>]*'
    r'(?:it="([^"]*)")?',
    re.DOTALL
)

def parse_packages_xml(xml_content: str) -> list[VersionEntry]:
    """Parst /data/system/packages.xml für Installations-Timestamps."""
    entries: list[VersionEntry] = []
    for m in _PKG_RE.finditer(xml_content):
        pkg, path, ver, ft, it = m.groups()
        if not pkg:
            continue
        # ft = firstInstallTime hex, it = lastUpdateTime hex
        first = _hex_to_date(ft)
        last  = _hex_to_date(it)
        entries.append(VersionEntry(
            package=pkg,
            version_name=ver or "—",
            version_code="—",
            timestamp=first,
            event_type="INSTALL",
        ))
        if last and last != first:
            entries.append(VersionEntry(
                package=pkg, version_name=ver or "—",
                version_code="—", timestamp=last,
                event_type="UPDATE",
            ))
    return entries


def _hex_to_date(hex_str: Optional[str]) -> str:
    if not hex_str:
        return "—"
    try:
        ms = int(hex_str, 16)
        return epoch_to_human(ms)
    except (ValueError, TypeError):
        return hex_str


# ---------------------------------------------------------------------------
# SharedPreferences XML Parser
# ---------------------------------------------------------------------------

_URL_RE     = re.compile(r'https?://[^\s"\'<>]{4,}')
_IP_RE      = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
_API_KEY_RE = re.compile(
    r'(?i)(?:api[_-]?key|secret|token|password|auth|bearer|credential)s?\s*[=:]\s*["\']?([A-Za-z0-9+/=_\-]{8,})'
)


def parse_shared_prefs_xml(xml_content: str) -> dict:
    """Parst Android SharedPreferences XML – sucht API-Keys, Tokens, URLs."""
    result: dict = {"keys": {}, "urls_found": [], "api_keys_found": [], "ips_found": []}
    if not xml_content.strip():
        return result

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return result

    for el in root:
        name  = el.get("name", "")
        value = str(el.get("value", "") or el.text or "")
        result["keys"][name] = value[:200]

        result["urls_found"].extend(_URL_RE.findall(value))
        ips = _IP_RE.findall(value)
        result["ips_found"].extend(
            ip for ip in ips if not ip.startswith(("127.", "0."))
        )
        key_lower = name.lower()
        if any(kw in key_lower for kw in
               ("key", "secret", "token", "password", "auth", "api", "credential")):
            if len(value) >= 8:
                result["api_keys_found"].append(
                    f"{name}={value[:40]}{'…' if len(value) > 40 else ''}"
                )
        result["api_keys_found"].extend(_API_KEY_RE.findall(value)[:3])

    result["urls_found"]     = list(dict.fromkeys(result["urls_found"]))[:20]
    result["ips_found"]      = list(dict.fromkeys(result["ips_found"]))[:20]
    result["api_keys_found"] = list(dict.fromkeys(result["api_keys_found"]))[:20]
    return result


# ---------------------------------------------------------------------------
# billing.db Parser
# ---------------------------------------------------------------------------

def parse_billing_db(local_path: str) -> list[dict]:
    """Parst billing.db / acquire.db – Käufe und Abonnements."""
    records: list[dict] = []
    if not os.path.exists(local_path):
        return records

    conn = None
    try:
        conn = sqlite3.connect(f"file:{local_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        _BILLING_KWDS = ("purchase", "order", "billing", "buy", "subscription", "acquire")
        for tbl in tables:
            if not any(kw in tbl.lower() for kw in _BILLING_KWDS):
                continue
            try:
                cur.execute(f"SELECT * FROM [{tbl}] ORDER BY rowid DESC LIMIT 500")
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    d = dict(zip(cols, row))
                    item = next(
                        (str(d[f]) for f in (
                            "packageName", "package_name", "sku", "productId",
                            "product_id", "orderId", "order_id",
                        ) if f in d and d[f]),
                        None,
                    )
                    if not item:
                        continue
                    ts = next(
                        (epoch_to_human(d[f]) for f in (
                            "purchaseTime", "purchase_time", "timestamp", "date",
                        ) if f in d and d[f]),
                        "—",
                    )
                    price = next(
                        (str(d[f]) for f in (
                            "price", "amount", "originalPrice", "micros",
                        ) if f in d and d[f]),
                        "—",
                    )
                    status = str(
                        d.get("purchaseState") or d.get("state") or d.get("status") or "?"
                    )
                    records.append({
                        "table": tbl, "item": item,
                        "timestamp": ts, "price": price, "status": status,
                    })
            except sqlite3.Error:
                pass
    except sqlite3.Error as e:
        records.append({
            "table": "?", "item": f"PARSE ERROR: {e}",
            "timestamp": "—", "price": "—", "status": "?",
        })
    finally:
        if conn:
            conn.close()
    return records


# ---------------------------------------------------------------------------
# accounts.db Parser
# ---------------------------------------------------------------------------

def parse_accounts_db(local_path: str) -> list[dict]:
    """Parst accounts.db – Account-Metadaten (KEINE Token-Werte)."""
    records: list[dict] = []
    if not os.path.exists(local_path):
        return records

    conn = None
    try:
        conn = sqlite3.connect(f"file:{local_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM accounts LIMIT 200")
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                d         = dict(zip(cols, row))
                acct_id   = d.get("_id") or d.get("id") or "?"
                raw_name  = str(d.get("name") or "unknown")
                acct_type = str(d.get("type") or "unknown")

                if "@" in raw_name:
                    user, domain = raw_name.split("@", 1)
                    masked = f"{user[:2]}{'*' * max(0, len(user) - 2)}@{domain}"
                elif len(raw_name) > 4:
                    masked = raw_name[:2] + "*" * (len(raw_name) - 2)
                else:
                    masked = "****"

                token_count = 0
                try:
                    c2 = conn.cursor()
                    c2.execute(
                        "SELECT COUNT(*) FROM authtokens WHERE accounts_id=?",
                        (acct_id,),
                    )
                    r2 = c2.fetchone()
                    if r2:
                        token_count = int(r2[0])
                except sqlite3.Error:
                    pass

                records.append({
                    "account_type":         acct_type,
                    "account_name_masked":  masked,
                    "token_count":          token_count,
                })
        except sqlite3.Error:
            pass
    except sqlite3.Error as e:
        records.append({
            "account_type":        f"PARSE ERROR: {e}",
            "account_name_masked": "?",
            "token_count":         0,
        })
    finally:
        if conn:
            conn.close()
    return records


# ---------------------------------------------------------------------------
# library.db Parser
# ---------------------------------------------------------------------------

def parse_vending_db_library(local_path: str) -> list[dict]:
    """Parst library.db – gekaufte/heruntergeladene App-Liste."""
    records: list[dict] = []
    if not os.path.exists(local_path):
        return records

    conn = None
    try:
        conn = sqlite3.connect(f"file:{local_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        for tbl in tables:
            try:
                cur.execute(f"SELECT * FROM [{tbl}] LIMIT 1000")
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    d   = dict(zip(cols, row))
                    pkg = str(
                        d.get("doc_id") or d.get("packageName") or
                        d.get("package_name") or ""
                    )
                    if pkg and "." in pkg:
                        ts = epoch_to_human(
                            d.get("timestamp") or d.get("acquired_time") or ""
                        )
                        records.append({
                            "package": pkg,
                            "timestamp": ts,
                            "source_table": tbl,
                        })
            except sqlite3.Error:
                pass
    except sqlite3.Error:
        pass
    finally:
        if conn:
            conn.close()
    return records
