"""Standalone CLI – python -m playstore_forensics

Verwendung ohne laufendes AndroidPanzer-Hauptmenü.
Direkt mit ADB-Gerät verbunden oder im Offline-Demo-Modus.

Beispiele:
  python -m playstore_forensics --auth OWN_DEVICE --full
  python -m playstore_forensics --auth CONSENT --device-id R3CN904JNHZ --output ./output
  python -m playstore_forensics --demo
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Projekt-Root zum sys.path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))


def _print_banner() -> None:
    print("═" * 70)
    print("  🕵️  PLAY STORE FORENSIC ARTIFACT EXTRACTOR  v1.0")
    print("  AndroidPanzer  –  Standalone CLI")
    print("═" * 70)


def _run_demo() -> None:
    """Demo-Modus mit synthetischen Testdaten (kein Gerät nötig)."""
    from playstore_forensics.models import (
        InstallRecord, SearchRecord, UsageRecord, ForensicReport,
    )
    from playstore_forensics.analyzer import detect_anomalies, compute_stats, build_timeline
    from playstore_forensics.output import generate_text_report, save_reports

    print("\n  [DEMO-MODUS] Synthetische Forensik-Daten\n")

    report = ForensicReport(
        device_model="Demo Samsung Galaxy S23",
        android_version="14",
        root_available=True,
        scan_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    report.installs = [
        InstallRecord("com.whatsapp",
                      first_install="2024-01-10 08:22:31",
                      last_update="2024-06-03 14:10:00",
                      installer="com.android.vending",
                      version_name="2.24.9.1", version_code="224091"),
        InstallRecord("com.telegram.messenger",
                      first_install="2024-02-15 20:11:44",
                      installer="com.android.vending",
                      version_name="10.1.2", version_code="101200"),
        InstallRecord("com.evil.spyware",
                      first_install="2024-03-22 02:47:11",
                      installer="", is_sideloaded=True,
                      version_name="1.0", version_code="1"),
        InstallRecord("com.cracked.premium",
                      first_install="2024-04-01 19:05:00",
                      installer="com.unknown.market", is_sideloaded=True,
                      version_name="5.9.1-mod", version_code="591"),
    ]
    report.searches = [
        SearchRecord("whatsapp",               timestamp="2024-01-09 10:00:00"),
        SearchRecord("telegram download",       timestamp="2024-02-14 22:30:00"),
        SearchRecord("spy app kostenlos",       timestamp="2024-03-20 01:12:00"),
        SearchRecord("cracked premium apk mod", timestamp="2024-03-31 18:45:00"),
        SearchRecord("hack instagram account",  timestamp="2024-04-10 15:20:00"),
    ]
    report.usage = [
        UsageRecord("com.whatsapp",    last_used="2024-06-24 09:15:00", fg_time_ms=7_200_000, launch_count=312),
        UsageRecord("com.telegram.messenger", last_used="2024-06-23 22:05:00", fg_time_ms=3_600_000, launch_count=89),
        UsageRecord("com.evil.spyware", last_used="2024-06-22 03:45:00", fg_time_ms=600_000, launch_count=4),
    ]

    anomalies = detect_anomalies(report)
    stats     = compute_stats(report)

    print(generate_text_report(report))
    print()
    print(f"  Anomalien erkannt: {len(anomalies)}")
    for a in anomalies:
        marker = {"CRITICAL": "!!!","HIGH": "!! ","MEDIUM": "!  ","INFO": "   "}.get(a["severity"], "   ")
        print(f"  [{a['severity']:8}] {marker} {a['type']:<28} {a['detail'][:55]}")

    out_dir = Path("./psf_demo_output")
    saved = save_reports(report, out_dir)
    print()
    print(f"  Demo-Reports gespeichert in {out_dir}:")
    for fmt, p in saved.items():
        print(f"    {fmt.upper():8} → {p}")


def _run_live(args: argparse.Namespace) -> None:
    """Live-Analyse mit verbundenem ADB-Gerät."""
    from apz.adb import ADB, AdbError
    from playstore_forensics.security import require_authorization
    from playstore_forensics.main import full_scan

    # Autorisierung
    _AUTH_MAP = {
        "OWN_DEVICE":    "1",
        "CONSENT":       "2",
        "LAW_ENFORCE":   "3",
        "BYOD":          "4",
    }
    if args.auth.upper() not in _AUTH_MAP:
        print(f"  ✗ Ungültiger Auth-Typ: {args.auth}")
        print(f"    Gültig: {', '.join(_AUTH_MAP)}")
        sys.exit(1)

    # Geräte-Verbindung
    try:
        adb = ADB(serial=args.device_id)
    except Exception as e:
        print(f"  ✗ ADB-Fehler: {e}")
        sys.exit(1)

    # Root prüfen
    is_root = adb.check_root()
    st = {"is_root": is_root}

    print(f"  Gerät    : {adb.getprop('ro.product.model')} ({adb.serial or 'auto'})")
    print(f"  Android  : {adb.getprop('ro.build.version.release')}")
    print(f"  Root     : {'JA' if is_root else 'NEIN'}")
    print()

    # Autorisierung
    from playstore_forensics import security
    security._AUTHORIZED = True   # CLI-Autorisierung via --auth Flag

    # Output-Verzeichnis
    out_dir = Path(args.output) if args.output else Path("./psf_live_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Scan ausführen
    if args.full:
        from playstore_forensics.main import _build_report, full_scan
        from playstore_forensics.output import save_reports
        from playstore_forensics.analyzer import detect_anomalies

        tasks = ["installs", "searches", "usage", "timeline"]
        if is_root:
            tasks += ["apk"]

        report = _build_report(adb, st, tasks)
        anomalies = detect_anomalies(report)
        saved = save_reports(report, out_dir)

        print(report.summary())
        print(f"  Anomalien: {len(anomalies)}")
        print(f"  Reports  : {out_dir}")
        for fmt, p in saved.items():
            print(f"    {fmt.upper():8} → {p}")
    else:
        print("  Hinweis: Verwende --full für vollständige Extraktion.")
        print(f"  Ausgabe  : {out_dir}")


def main() -> None:
    _print_banner()

    parser = argparse.ArgumentParser(
        prog="python -m playstore_forensics",
        description="Play Store Forensic Artifact Extractor",
        add_help=True,
    )
    parser.add_argument(
        "--auth", default="OWN_DEVICE",
        choices=["OWN_DEVICE", "CONSENT", "LAW_ENFORCE", "BYOD"],
        help="Rechtlicher Autorisierungstyp (Standard: OWN_DEVICE)",
    )
    parser.add_argument(
        "--device-id", default=None,
        help="ADB Serial (z.B. R3CN904JNHZ) – leer = erstes verfügbares Gerät",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Vollständige Extraktion aller Artefakte",
    )
    parser.add_argument(
        "--output", default="./psf_output",
        help="Ausgabe-Verzeichnis (Standard: ./psf_output)",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Demo-Modus mit synthetischen Daten (kein Gerät nötig)",
    )

    args = parser.parse_args()

    print(f"  Auth     : {args.auth}")
    print(f"  Modus    : {'DEMO' if args.demo else 'LIVE – ADB'}")
    print(f"  Ausgabe  : {args.output}")
    print()

    if args.demo:
        _run_demo()
    else:
        _run_live(args)


if __name__ == "__main__":
    main()
