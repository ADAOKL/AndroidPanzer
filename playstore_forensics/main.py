"""Play Store Artifact Extractor – AndroidPanzer Menü-Integration.

Einstiegspunkte:
  menu(adb, dev, st)  – interaktives Untermenü
  full_scan(adb, st)  – kompletter Scan ohne Prompts

Folgt exakt dem AndroidPanzer-Muster:
  func(adb: ADB, dev, st: dict, _auto: bool = False)
"""
from __future__ import annotations

import os
import sys
import time
from apz.adb import ADB
from apz import ui
from apz.util import outdir

from .security import require_authorization, is_authorized
from .slack_recovery import scan_database, generate_chain_of_custody
from .extractor import (
    extract_install_history,
    extract_search_history,
    extract_usage_stats,
    extract_apk_artifacts,
    extract_version_timeline,
    collect_device_info,
)
from .analyzer import (
    detect_anomalies,
    compute_stats,
    analyze_version_timeline,
)
from .models import ForensicReport
from .output import (
    generate_text_report,
    generate_timeline_ascii,
    save_reports,
)
from .config import OUTPUT_DIR

# Ausgabe-Verzeichnis
OUT = outdir("forensik/playstore")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _progress(i: int, total: int, label: str) -> None:
    pct = int(100 * i / max(total, 1))
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    print(f"\r  [{bar}] {pct:3}%  {label[:40]:<40}", end="", flush=True)


def _write(name: str, content: str) -> str:
    try:
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
    except OSError as e:
        print(f"  ⚠ Schreib-Fehler: {e}", file=sys.stderr)
        return ""


def _build_report(adb: ADB, st: dict, tasks: list[str]) -> ForensicReport:
    """Baut ForensicReport aus gewählten Tasks auf."""
    dev_info = collect_device_info(adb, st)
    report = ForensicReport(
        device_serial=dev_info.get("serial", "?"),
        device_model=dev_info.get("model", "?") + " " + dev_info.get("manufacturer", ""),
        android_version=dev_info.get("android_version", "?"),
        root_available=bool(st.get("is_root")),
        scan_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    )

    if "installs" in tasks:
        ui.info("Extrahiere Installations-Historie …")
        report.installs = extract_install_history(
            adb, st, progress_cb=lambda i, t, l: _progress(i, t, l)
        )
        print()
        ui.ok(f"{len(report.installs)} Apps analysiert")

    if "searches" in tasks:
        ui.info("Extrahiere Suchhistorie aus suggestions.db …")
        report.searches = extract_search_history(adb, st)
        ui.ok(f"{len(report.searches)} Suchanfragen")

    if "usage" in tasks:
        ui.info("Extrahiere Nutzungsstatistiken …")
        report.usage = extract_usage_stats(adb, st)
        ui.ok(f"{len(report.usage)} Nutzungs-Records")

    if "apk" in tasks:
        ui.info("APK-Scan (statische Analyse) …")
        pkgs = [r.package for r in report.installs[:10000]] if report.installs else None
        report.apk_scans = extract_apk_artifacts(
            adb, st, pkgs=pkgs,
            progress_cb=lambda i, t, l: _progress(i, t, l),
        )
        print()
        ui.ok(f"{len(report.apk_scans)} APKs analysiert")

    if "timeline" in tasks:
        ui.info("Versionstimeline …")
        report.timeline = extract_version_timeline(adb, st)
        ui.ok(f"{len(report.timeline)} Timeline-Einträge")

    return report


# ---------------------------------------------------------------------------
# Einzelne Menü-Aktionen
# ---------------------------------------------------------------------------

def action_install_history(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Play Store – Installations-Historie", ui.CYAN)
    report = _build_report(adb, st, ["installs"])

    text = generate_text_report(report)
    p = _write("install_history.txt", text)
    ui.pager(
        "\n".join(str(r) for r in report.installs[:10000]),
        f"Installations-Historie ({min(len(report.installs), 10000)} Einträge)"
    )
    ui.ok(f"Vollständig gespeichert → {p}")
    if not _auto:
        ui.pause()


def action_search_history(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Play Store – Suchhistorie (suggestions.db)", ui.CYAN)

    if not st.get("is_root"):
        ui.warn("Kein Root – suggestions.db liegt in /data/data/ (geschützt)")
        ui.info("Tipp: Mit Root oder ADB backup möglich")
        if not _auto:
            ui.pause()
        return

    report = _build_report(adb, st, ["searches"])
    out_text = "\n".join(str(s) for s in report.searches)
    p = _write("search_history.txt", out_text)
    ui.pager(out_text[:100000], "Suchhistorie")
    ui.ok(f"Gespeichert → {p}")
    if not _auto:
        ui.pause()


def action_usage_stats(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Play Store – App-Nutzungsstatistiken", ui.CYAN)
    report = _build_report(adb, st, ["usage"])

    # Nur Apps mit tatsächlicher Nutzung
    used = [r for r in report.usage if r.fg_time_ms > 0 or r.launch_count > 0]
    used.sort(key=lambda r: (r.fg_time_ms, r.launch_count), reverse=True)
    never = [r for r in report.usage if r.fg_time_ms == 0 and r.launch_count == 0]

    rank_icons = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    lines: list[str] = []

    lines.append(f"  Gesamt Records : {len(report.usage)}")
    lines.append(f"  Mit Nutzung    : {len(used)}")
    lines.append(f"  Nie gestartet  : {len(never)}")
    lines.append("")

    if used:
        lines.append("── TOP GENUTZTE APPS ──────────────────────────────────────────────")
        for i, u in enumerate(used[:10000]):
            icon = rank_icons[i] if i < len(rank_icons) else "  ⬢"
            mins = u.fg_time_ms / 60_000
            hrs_str = f"{mins/60:.1f}h" if mins >= 60 else f"{mins:.1f}min"
            launch_str = f"  ({u.launch_count}× gestartet)" if u.launch_count > 0 else ""
            date_str = f"  {u.last_used}" if u.last_used and u.last_used != "—" else ""
            lines.append(
                f"  {icon}  {u.package:<45}  {hrs_str:>8}{launch_str}{date_str}"
            )
        if len(used) > 10000:
            lines.append(f"  ... und {len(used)-10000} weitere")
    else:
        lines.append("  ℹ  Keine Nutzungsdaten gefunden (dumpsys usagestats leer)")

    text = "\n".join(lines)
    ui.pager(text, f"Nutzungsstatistiken ({len(used)} aktive Apps)")
    p = _write("usage_stats.txt", text + "\n\n── ALLE RECORDS ──\n" +
               "\n".join(str(u) for u in report.usage))
    ui.ok(f"Gespeichert → {p}")
    if not _auto:
        ui.pause()


def action_apk_scan(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("APK Deep Scan – Manifest · Permissions · Obfuskierung · Malware", ui.CYAN)
        ui.info("Analysiert: AndroidManifest, Permission-Scoring, Spyware-Combos, Obfuskierung, Malware-Strings")
        if not ui.confirm("Deep-Scan der installierten Apps starten?", True):
            return

    # Paketliste holen
    report = _build_report(adb, st, ["installs"])
    pkgs = [r.package for r in report.installs if not r.is_system]
    if not pkgs:
        ui.warn("Keine User-Apps gefunden"); ui.pause(); return

    try:
        from .apk_deep_scanner import batch_deep_scan, filter_noteworthy
        ui.info(f"Deep-Scan von {len(pkgs)} Apps (Manifest + Obfuskierung + Malware) …")
        results = batch_deep_scan(adb, pkgs, st, progress_cb=lambda i, t, l: _progress(i, t, l))
        print()
        noteworthy = filter_noteworthy(results)
        ui.ok(f"{len(noteworthy)} auffällige Apps (HIGH/CRITICAL)")

        lines = []
        for r in noteworthy:
            lines.append(r.to_text())
            lines.append("─" * 60)
        out = "\n".join(lines) if lines else "Keine HIGH/CRITICAL Risiken gefunden"
        ui.pager(out, f"APK Deep Scan – {len(noteworthy)} Treffer")
        p = _write("apk_deep_scan.txt", "\n".join(r.to_text() for r in results))
        ui.ok(f"Vollständig gespeichert → {p}")
    except ImportError:
        # Fallback auf alten Scanner
        report = _build_report(adb, st, ["installs", "apk"])
        risky = [a for a in report.apk_scans if a.risk_level != "LOW"]
        text_output = "\n".join(str(a) for a in report.apk_scans)
        p = _write("apk_scan.txt", text_output)
        ui.ok(f"Gespeichert → {p}")
    if not _auto:
        ui.pause()


def action_version_timeline(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Versions-Timeline aller Apps", ui.CYAN)
    report = _build_report(adb, st, ["timeline"])

    tl_text = generate_timeline_ascii(report)
    ui.pager(tl_text, "Versions-Timeline")

    findings = analyze_version_timeline(report.timeline)
    if findings:
        ui.rule(f"{len(findings)} Auffälligkeiten in Versionsverlauf", ui.YELLOW)
        for f in findings:
            print(f"  [{f['type']}] {f['package']}: {f['detail']}")

    p = _write("version_timeline.txt", tl_text)
    ui.ok(f"Gespeichert → {p}")
    if not _auto:
        ui.pause()


def action_anomaly_report(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Anomalie-Analyse – Auffälligkeiten erkennen", ui.CYAN)
    report = _build_report(adb, st, ["installs", "searches", "usage"])

    anomalies = detect_anomalies(report)
    if not anomalies:
        ui.ok("Keine Anomalien erkannt")
    else:
        for a in anomalies:
            color = {
                "CRITICAL": ui.RED,
                "HIGH": ui.RED,
                "MEDIUM": ui.YELLOW,
                "INFO": ui.CYAN,
            }.get(a["severity"], ui.RESET)
            print(f"\n  {color}[{a['severity']}] {a['type']}{ui.RESET}")
            print(f"  Paket : {a.get('package', '—')}")
            print(f"  Detail: {a['detail']}")

    lines = [f"[{a['severity']}] {a['type']} | {a.get('package','—')} | {a['detail']}"
             for a in anomalies]
    p = _write("anomalies.txt", "\n".join(lines))
    ui.ok(f"Gespeichert → {p}")
    if not _auto:
        ui.pause()


def action_slack_recovery(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    """Slack-Space-Recovery: gelöschte Einträge aus Play-Store-DBs wiederherstellen."""
    if not _auto:
        ui.clear(); ui.rule("Slack-Space Recovery – gelöschte SQLite-Einträge", ui.CYAN)

    if not st.get("is_root"):
        ui.warn("Root erforderlich – DBs liegen in /data/data/ (geschützt)")
        if not _auto:
            ui.pause()
        return

    import tempfile
    from .utils import pull_db_via_sdcard
    from .config import APaths

    db_candidates = [
        APaths.FROSTING_DB,
        APaths.SUGGESTIONS_DB,
        APaths.VENDING_DB_DIR + "/localapps.db",
    ]

    all_reports = []
    pulled_paths: list[str] = []

    for db_path in db_candidates:
        ui.info(f"Prüfe {db_path} …")
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            tmp = tf.name
        if pull_db_via_sdcard(adb, db_path, tmp, root=True):
            ui.info(f"Scanne {os.path.basename(db_path)} ({os.path.getsize(tmp):,} Bytes) …")
            try:
                rep = scan_database(tmp, max_pages=200)
                all_reports.append((os.path.basename(db_path), rep))
                pulled_paths.append(tmp)
                hc = rep.high_confidence()
                ui.ok(f"  → {len(rep.records)} Funde, {len(hc)} hochkonfident, {len(rep.unique_packages())} unique Pakete")
            except Exception as e:
                ui.err(f"  Scan-Fehler: {e}")
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        else:
            ui.warn(f"  Nicht zugänglich: {db_path}")
            try:
                os.unlink(tmp)
            except OSError:
                pass

    if not all_reports:
        ui.err("Keine DB analysierbar – Root-Zugriff oder Verschlüsselung?")
        if not _auto:
            ui.pause()
        return

    # Ergebnisse ausgeben & speichern
    for db_name, rep in all_reports:
        text = rep.to_text()
        print()
        ui.pager(text[:100000], f"Slack-Space: {db_name}")
        p = _write(f"slack_{db_name}.txt", text)
        ui.ok(f"Gespeichert → {p}")

    # Chain-of-Custody-Zertifikat
    results = {name: rep.to_dict() for name, rep in all_reports}
    cert = generate_chain_of_custody(pulled_paths, results)
    import json as _json
    p = _write("chain_of_custody.json", _json.dumps(cert, indent=2))
    ui.ok(f"Chain-of-Custody → {p}")

    # Cleanup tmp files
    for tmp in pulled_paths:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    if not _auto:
        ui.pause()


def action_permission_matrix(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Permission Matrix – AppOps & Spyware-Scoring", ui.CYAN)
    try:
        from .permission_matrix import analyze_all_apps, format_permission_matrix, format_top_risky_apps
        pkgs = [r.package for r in _build_report(adb, st, ["installs"]).installs]
        ui.info(f"Analysiere {len(pkgs)} Apps …")
        profiles = analyze_all_apps(adb, pkgs, st,
                                    progress_cb=lambda i, t, l: _progress(i, t, l))
        print()
        table = format_permission_matrix(profiles)
        ui.pager(table, "Permission Matrix")
        p = _write("permission_matrix.txt", table)
        ui.ok(f"Gespeichert → {p}")
    except ImportError:
        ui.warn("permission_matrix.py noch nicht verfügbar – bitte erneut versuchen")
    if not _auto:
        ui.pause()


def action_network_forensics(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Netzwerk-Forensik – Verbindungen, DNS, Traffic", ui.CYAN)
    try:
        from .network_forensics import run_network_forensics
        result = run_network_forensics(adb, dev, st)
        summary = result.get("summary", "Keine Daten")
        ui.pager(summary, "Netzwerk-Forensik")
        import json as _j
        p = _write("network_forensics.json", _j.dumps(result, default=str, indent=2))
        ui.ok(f"Gespeichert → {p}")
    except ImportError:
        ui.warn("network_forensics.py noch nicht verfügbar")
    if not _auto:
        ui.pause()


def action_shared_prefs(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("SharedPreferences – API-Keys, Tokens, URLs", ui.CYAN)
    try:
        from .extractor import extract_shared_preferences
        pkgs = [r.package for r in _build_report(adb, st, ["installs"]).installs[:10000]]
        ui.info(f"Analysiere SharedPrefs von {len(pkgs)} Apps …")
        results = extract_shared_preferences(adb, pkgs, st)
        hits = [r for r in results if r.get("urls_found") or r.get("api_keys_found") or r.get("ips_found")]
        ui.ok(f"{len(hits)} von {len(results)} Apps mit verdächtigen Einträgen")
        lines = []
        for r in hits:
            lines.append(f"\n  [{r['pkg']}]")
            if r.get("urls_found"):   lines.append(f"    URLs   : {', '.join(r['urls_found'][:3])}")
            if r.get("ips_found"):    lines.append(f"    IPs    : {', '.join(r['ips_found'][:3])}")
            if r.get("api_keys_found"): lines.append(f"    API-Keys: {', '.join(r['api_keys_found'][:5])}")
        out = "\n".join(lines)
        if out:
            ui.pager(out, "SharedPrefs-Funde")
        p = _write("shared_prefs.txt", out or "Keine verdächtigen Einträge")
        ui.ok(f"Gespeichert → {p}")
    except (ImportError, AttributeError):
        ui.warn("extract_shared_preferences noch nicht verfügbar")
    if not _auto:
        ui.pause()


def action_payment_forensics(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Payment-Forensik – Käufe & Abonnements", ui.CYAN)
    try:
        from .extractor import extract_payment_forensics
        data = extract_payment_forensics(adb, st)
        lines = [f"  Quelle: {data.get('source', '?')}"]
        if data.get("purchases"):
            lines.append(f"\n  KÄUFE ({len(data['purchases'])}):")
            for p in data["purchases"][:20]:
                lines.append(f"    {p.get('timestamp','—'):<22} {p.get('item','?'):<30} {p.get('price','?')}")
        if data.get("subscriptions"):
            lines.append(f"\n  ABONNEMENTS ({len(data['subscriptions'])}):")
            for s in data["subscriptions"][:10]:
                lines.append(f"    {s.get('item','?'):<35} Status: {s.get('status','?')}")
        out = "\n".join(lines) or "Keine Zahlungsdaten gefunden"
        ui.pager(out, "Payment-Forensik")
        p = _write("payment_forensics.txt", out)
        ui.ok(f"Gespeichert → {p}")
    except (ImportError, AttributeError):
        ui.warn("extract_payment_forensics noch nicht verfügbar")
    if not _auto:
        ui.pause()


def action_account_tokens(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Account-Token Metadaten", ui.CYAN)
        ui.info("Gibt NUR Metadaten aus – keine Token-Werte (Datenschutz).")
    try:
        from .extractor import extract_account_tokens
        tokens = extract_account_tokens(adb, st)
        lines = [f"  {'TYP':<30} {'KONTO (maskiert)':<35} TOKENS"]
        lines.append("  " + "─" * 70)
        for t in tokens:
            lines.append(f"  {t.get('account_type','?'):<30} "
                         f"{t.get('account_name_masked','?'):<35} "
                         f"{t.get('token_count',0)}")
        out = "\n".join(lines)
        ui.pager(out, "Account-Metadaten")
        p = _write("account_tokens.txt", out)
        ui.ok(f"Gespeichert → {p}")
    except (ImportError, AttributeError):
        ui.warn("extract_account_tokens noch nicht verfügbar")
    if not _auto:
        ui.pause()


def action_wal_recovery(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("WAL / Journal Recovery", ui.CYAN)
    if not st.get("is_root"):
        ui.warn("Root erforderlich")
        if not _auto: ui.pause()
        return
    try:
        from .wal_recovery import run_wal_recovery
        result = run_wal_recovery(adb, st, OUT)
        ui.ok(f"WAL-Dateien gefunden : {result.get('wal_files_found', 0)}")
        ui.ok(f"Records extrahiert   : {result.get('records_extracted', 0)}")
        ui.ok(f"Hochkonfident        : {result.get('high_confidence_records', 0)}")
        if result.get("unique_packages"):
            ui.info(f"Pakete in WAL: {', '.join(result['unique_packages'][:8])}")
        for f in result.get("output_files", []):
            ui.info(f"  → {f}")
    except ImportError:
        ui.warn("wal_recovery.py noch nicht verfügbar")
    if not _auto:
        ui.pause()


def action_db_inventory(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("App-Datenbank-Inventar – alle SQLite-DBs", ui.CYAN)
    if not st.get("is_root"):
        ui.warn("Root erforderlich")
        if not _auto: ui.pause()
        return
    try:
        from .extractor import extract_app_databases
        pkgs = [r.package for r in _build_report(adb, st, ["installs"]).installs[:25]]
        ui.info(f"Inventarisiere DBs für {len(pkgs)} Apps …")
        dbs = extract_app_databases(adb, pkgs, st)
        lines = []
        for d in dbs:
            enc = " [ENCRYPTED]" if d.get("is_encrypted") else ""
            wal = " [WAL]" if d.get("has_wal") else ""
            size_kb = d.get("total_size_bytes", 0) // 1024
            lines.append(f"\n  {d['pkg']}")
            lines.append(f"    DB : {d['db_path']}{enc}{wal}  ({size_kb} KB)")
            for tbl, cnt in list(d.get("row_counts", {}).items())[:10000]:
                lines.append(f"    Tabelle {tbl:<30} {cnt:>6} Zeilen")
        out = "\n".join(lines) or "Keine DBs gefunden"
        ui.pager(out[:100000], "DB-Inventar")
        p = _write("db_inventory.txt", out)
        ui.ok(f"Gespeichert → {p}")
    except (ImportError, AttributeError):
        ui.warn("extract_app_databases noch nicht verfügbar")
    if not _auto:
        ui.pause()


def action_master_risk_report(adb: ADB, dev, st: dict, _auto: bool = False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Master Risk-Report – Gesamtrisiko-Bewertung", ui.CYAN)
        ui.info("Kombiniert alle Datenquellen zu einem priorisierten Risikobericht …")
    tasks = ["installs", "searches", "usage"]
    if st.get("is_root"):
        tasks.append("apk")
    report = _build_report(adb, st, tasks)
    anomalies = detect_anomalies(report)
    stats = compute_stats(report)

    # Versuche permission_matrix einzubinden
    perm_data = ""
    try:
        from .permission_matrix import analyze_all_apps, format_top_risky_apps
        pkgs = [r.package for r in report.installs[:20]]
        profiles = analyze_all_apps(adb, pkgs, st)
        perm_data = format_top_risky_apps(profiles, n=10)
    except (ImportError, Exception):
        perm_data = "  [Permission Matrix nicht verfügbar]"

    lines = [
        "═" * 70,
        "  MASTER RISK-REPORT",
        "═" * 70,
        report.summary(),
        "─" * 70,
        "  TOP-ANOMALIEN:",
    ]
    for a in anomalies[:15]:
        sev_icon = {"CRITICAL": "🔴","HIGH": "🟠","MEDIUM": "🟡","INFO": "🔵"}.get(a["severity"], "⚪")
        lines.append(f"  {sev_icon} [{a['severity']:8}] {a['type']:<28} {a['detail'][:45]}")

    lines += ["", "─" * 70, "  PERMISSION RISIKO (Top 10):", perm_data]

    lines += [
        "", "─" * 70,
        "  STATISTIK:",
        f"  Apps gesamt     : {stats['total_apps']}",
        f"  Sideloaded      : {stats['sideloaded_count']}",
        f"  Suspicious Search: {len([a for a in anomalies if a['type']=='SUSPICIOUS_SEARCH'])}",
        f"  Nacht-Aktivität : {len([a for a in anomalies if a['type']=='NIGHTTIME_ACTIVITY'])}",
        "═" * 70,
    ]

    out = "\n".join(lines)
    ui.pager(out, "Master Risk-Report")
    p = _write("master_risk_report.txt", out)
    ui.ok(f"Gespeichert → {p}")
    if not _auto:
        ui.pause()


def full_scan(adb: ADB, dev=None, st: dict | None = None) -> None:
    """Vollständiger automatisierter Scan aller Module mit Checkpoint-Resume."""
    from .security import require_authorization, update_auth_device
    if not require_authorization():
        return
    st = st or {}

    # Device-Serial in Auth-Log nachpflegen
    serial = getattr(dev, "serial", None) or adb.serial if hasattr(adb, "serial") else "unknown"
    update_auth_device(str(serial))

    import json as _j

    # Checkpoint-Pfad – eine Datei pro Gerät+Tag
    ckpt_stamp = time.strftime("%Y%m%d")
    ckpt_path  = os.path.join(OUT, f"checkpoint_{ckpt_stamp}.json")

    def _save_checkpoint(report, phase: int) -> None:
        d = report.to_dict()
        d["_checkpoint"] = {"phase_completed": phase, "phases_total": 5}
        try:
            os.makedirs(OUT, exist_ok=True)
            with open(ckpt_path, "w", encoding="utf-8") as f:
                _j.dump(d, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def _load_checkpoint():
        from .models import ForensicReport
        r = ForensicReport.from_checkpoint(ckpt_path)
        if r is None:
            return None, 0
        # Lese die Phase aus dem Checkpoint-Dict
        try:
            with open(ckpt_path, encoding="utf-8") as f:
                raw = _j.load(f)
            phase = int(raw.get("_checkpoint", {}).get("phase_completed", 0))
        except (OSError, ValueError):
            phase = 0
        return r, phase

    ui.clear(); ui.rule("PLAY STORE ARTIFACT EXTRACTOR – VOLLSCAN", ui.CYAN)

    # Resume-Möglichkeit anbieten
    existing, last_phase = _load_checkpoint()
    if existing and last_phase > 0:
        ui.info(f"Checkpoint gefunden: Phase {last_phase}/5 abgeschlossen ({ckpt_path})")
        if ui.confirm(f"Scan ab Phase {last_phase + 1} fortsetzen?", True):
            report = existing
            ui.ok(f"Resume ab Phase {last_phase + 1}")
        else:
            report = None
            last_phase = 0
            ui.info("Starte neu …")
    else:
        report = None
        last_phase = 0
    print()

    # Phase 1: Basis-Artefakte
    if last_phase < 1:
        ui.rule("Phase 1/5 – Basis-Artefakte", ui.YELLOW)
        tasks = ["installs", "searches", "usage", "timeline"]
        if st.get("is_root"):
            tasks.append("apk")
        report = _build_report(adb, st, tasks)
        _save_checkpoint(report, 1)
    else:
        ui.info("Phase 1/5 – Basis-Artefakte (aus Checkpoint)")

    # Phase 2: APK Deep Scan
    if last_phase < 2:
        ui.rule("Phase 2/5 – APK Deep Scan", ui.YELLOW)
        try:
            from .apk_deep_scanner import batch_deep_scan
            pkgs = [r.package for r in report.installs if not r.is_system][:40]
            ui.info(f"Scanne {len(pkgs)} Apps …")
            deep_results = batch_deep_scan(adb, pkgs, st, progress_cb=lambda i,t,l: _progress(i,t,l))
            print()
            ui.ok(f"{len(deep_results)} APKs tief analysiert")
            _write("apk_deep_scan.txt", "\n".join(r.to_text() for r in deep_results))
            _save_checkpoint(report, 2)
        except Exception as e:
            ui.warn(f"APK Deep Scan Fehler: {e}")
    else:
        ui.info("Phase 2/5 – APK Deep Scan (aus Checkpoint)")

    # Phase 3: Netzwerk-Forensik
    if last_phase < 3:
        ui.rule("Phase 3/5 – Netzwerk-Forensik", ui.YELLOW)
        try:
            from .network_forensics import run_network_forensics
            net_result = run_network_forensics(adb, dev, st)
            _write("network_forensics.json", _j.dumps(net_result, default=str, indent=2))
            ui.ok(f"{len(net_result.get('connections',[]))} Verbindungen, "
                  f"{len(net_result.get('anomalies',[]))} Anomalien")
            _save_checkpoint(report, 3)
        except Exception as e:
            ui.warn(f"Netzwerk-Forensik Fehler: {e}")
    else:
        ui.info("Phase 3/5 – Netzwerk-Forensik (aus Checkpoint)")

    # Phase 4: Permission Matrix
    if last_phase < 4:
        ui.rule("Phase 4/5 – Permission Matrix", ui.YELLOW)
        try:
            from .permission_matrix import analyze_all_apps, format_permission_matrix
            pkgs_perm = [r.package for r in report.installs if not r.is_system][:25]
            profiles = analyze_all_apps(adb, pkgs_perm, st,
                                        progress_cb=lambda i,t,l: _progress(i,t,l))
            print()
            _write("permission_matrix.txt", format_permission_matrix(profiles))
            critical = [p for p in profiles if p.risk_level == "CRITICAL"]
            high = [p for p in profiles if p.risk_level == "HIGH"]
            ui.ok(f"CRITICAL: {len(critical)}  HIGH: {len(high)}")
            _save_checkpoint(report, 4)
        except Exception as e:
            ui.warn(f"Permission Matrix Fehler: {e}")
    else:
        ui.info("Phase 4/5 – Permission Matrix (aus Checkpoint)")

    # Phase 5: Anomalien & Reports
    ui.rule("Phase 5/5 – Anomalie-Analyse & Reports", ui.YELLOW)
    anomalies = detect_anomalies(report)
    compute_stats(report)

    print()
    ui.rule("VOLLSCAN ABGESCHLOSSEN", ui.GREEN)
    print(report.summary())

    if anomalies:
        ui.rule(f"{len(anomalies)} Anomalien erkannt", ui.RED)
        for a in anomalies[:15]:
            sev_icon = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","INFO":"🔵"}.get(a["severity"],"")
            print(f"  {sev_icon} [{a['severity']:8}] {a['type']:<28} {a['detail'][:55]}")

    os.makedirs(OUT, exist_ok=True)
    saved = save_reports(report, OUT)
    print()
    ui.ok(f"Reports gespeichert in {OUT}:")
    for fmt, path in saved.items():
        ui.info(f"  {fmt.upper():8} → {path}")

    # Checkpoint löschen nach erfolgreichem Abschluss
    try:
        os.unlink(ckpt_path)
    except OSError:
        pass

    ui.pause()


# ---------------------------------------------------------------------------
# Menü
# ---------------------------------------------------------------------------

def _dispatch(adb: ADB, dev, st: dict, handler) -> None:
    try:
        handler(adb, dev, st)
    except KeyboardInterrupt:
        print(); ui.warn("Abgebrochen."); time.sleep(0.5)
    except Exception as e:
        ui.err(f"Fehler: {e}"); ui.pause()


_MENU_GROUPS = [
    ("ARTEFAKT-EXTRAKTION", [
        ("1",  "Installations-Historie",                   "installs",  False),
        ("2",  "Suchhistorie  (suggestions.db)",           "searches",  True),
        ("3",  "App-Nutzungsstatistiken",                   "usage",     False),
        ("5",  "Versions-Timeline",                         "timeline",  False),
    ]),
    ("TIEFENANALYSE  [ROOT empfohlen]", [
        ("4",  "APK Deep Scan  (Manifest + Obfuskierung)", "apk",       True),
        ("9",  "Permission Matrix  (AppOps + Spyware)",    "perms",     True),
        ("10", "Netzwerk-Forensik  (Verbindungen / DNS)",  "network",   False),
        ("11", "SharedPrefs  (API-Keys / Token / URLs)",   "prefs",     True),
        ("12", "Payment-Forensik  (Käufe / Abos)",        "payment",   True),
        ("13", "Account-Token Metadaten",                  "accounts",  True),
    ]),
    ("RECOVERY", [
        ("7",  "Slack-Space Recovery  (gelöschte SQLite-Einträge)", "slack",   True),
        ("14", "WAL / Journal Recovery",                             "wal",     True),
        ("15", "App-Datenbank-Inventar  (alle DBs pro App)",        "dbinv",   True),
    ]),
    ("KORRELATION & BERICHT", [
        ("6",  "Anomalie-Analyse  (7 Erkennungsregeln)",  "anomaly",  False),
        ("16", "Master Risk-Report  (kombiniert alle Daten)", "risk", False),
        ("8",  "VOLLSCAN  (alle Module)",                  "full",    False),
    ]),
]


def menu(adb: ADB, dev=None, st: dict | None = None) -> None:
    """Interaktives Untermenü für Play Store Forensics."""
    st = st or {}

    if not require_authorization():
        return

    root_hint = (f"{ui.GREEN}Root: JA{ui.RESET}" if st.get("is_root")
                 else f"{ui.YELLOW}Root: NEIN (einige Module eingeschränkt){ui.RESET}")

    ROOT_KEYS = {item[0] for _, items in _MENU_GROUPS for item in items if item[3]}

    while True:
        ui.clear()
        ui.banner(subtitle="PLAY STORE ARTIFACT EXTRACTOR  [Option 57]")
        print(f"  {root_hint}\n  Ausgabe : {OUT}\n")

        for group_name, items in _MENU_GROUPS:
            ui.rule(group_name, ui.CYAN)
            for key, label, _, needs_root in items:
                warn = ""
                if needs_root and not st.get("is_root"):
                    warn = f"  {ui.YELLOW}[ROOT]{ui.RESET}"
                print(f"  [{key:>2}] {label}{warn}")
            print()

        print(f"  [{'0':>2}] Zurück\n")
        choice = ui.ask("Auswahl", "0")

        if choice in ("0", "q", "Q", "back", "exit"):
            break

        # Dispatch
        if choice == "1":   _dispatch(adb, dev, st, action_install_history)
        elif choice == "2": _dispatch(adb, dev, st, action_search_history)
        elif choice == "3": _dispatch(adb, dev, st, action_usage_stats)
        elif choice == "4": _dispatch(adb, dev, st, action_apk_scan)
        elif choice == "5": _dispatch(adb, dev, st, action_version_timeline)
        elif choice == "6": _dispatch(adb, dev, st, action_anomaly_report)
        elif choice == "7": _dispatch(adb, dev, st, action_slack_recovery)
        elif choice == "8": _dispatch(adb, dev, st, lambda a,d,s: full_scan(a,d,s))
        elif choice == "9":  _dispatch(adb, dev, st, action_permission_matrix)
        elif choice == "10": _dispatch(adb, dev, st, action_network_forensics)
        elif choice == "11": _dispatch(adb, dev, st, action_shared_prefs)
        elif choice == "12": _dispatch(adb, dev, st, action_payment_forensics)
        elif choice == "13": _dispatch(adb, dev, st, action_account_tokens)
        elif choice == "14": _dispatch(adb, dev, st, action_wal_recovery)
        elif choice == "15": _dispatch(adb, dev, st, action_db_inventory)
        elif choice == "16": _dispatch(adb, dev, st, action_master_risk_report)
        else:
            ui.err("Ungültige Auswahl"); time.sleep(0.6)
