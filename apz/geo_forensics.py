"""Geo-Forensik – Location-History, Tower-Triangulation, Reisehistorie.

Quellen: dumpsys location, content://com.google.android.gms.fitness,
         /sdcard/DCIM EXIF-Daten, cell tower data via dumpsys telephony
"""
from __future__ import annotations

from . import ui


def menu(adb=None, dev=None, st: dict | None = None) -> None:
    """Hauptmenü: Geo-Forensik."""
    if st is None:
        st = {}

    while True:
        ui.clear()
        ui.banner(subtitle="📍 GEO-FORENSIK")
        print()
        ui.rule("Optionen", ui.CYAN)
        print("  [1] Aktueller Standort (GPS/Netz)")
        print("  [2] Cell-Tower Triangulation")
        print("  [3] WLAN-Standortverlauf")
        print("  [4] Location-Berechtigungen je App")
        print("  [5] Foto-EXIF Geo-Daten (DCIM)")
        print("  [6] Google Maps / Fitness Indizien")
        print("  [7] Komplettstatus")
        print()
        print("  [0] Zurück")
        print()
        choice = input(f"{ui.PROMPT} Auswahl: ").strip()

        if choice == "0":
            return
        elif choice == "1":
            _current_location(adb, st)
        elif choice == "2":
            _cell_triangulation(adb, st)
        elif choice == "3":
            _wifi_location(adb, st)
        elif choice == "4":
            _location_permissions(adb, st)
        elif choice == "5":
            _exif_geodata(adb, st)
        elif choice == "6":
            _maps_indications(adb, st)
        elif choice == "7":
            _full_report(adb, st)
        else:
            ui.warn("Ungültige Auswahl")


def _current_location(adb, st: dict) -> None:
    ui.clear(); ui.rule("Aktueller Standort", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    loc = adb.shell(
        "dumpsys location 2>/dev/null | grep -E 'last known|latitude|longitude|accuracy|provider' | head -20",
        timeout=10
    ).strip()
    if loc:
        print(f"  Standortdaten aus dumpsys location:\n")
        for line in loc.splitlines():
            print(f"    {line.strip()}")
    else:
        print(f"  ℹ  Keine Standortdaten verfügbar (Location-Dienste inaktiv)")

    # GPS-Provider Status
    gps_enabled = adb.shell(
        "settings get secure location_mode 2>/dev/null || "
        "settings get secure location_providers_allowed 2>/dev/null",
        timeout=5
    ).strip()
    print(f"\n  Location-Mode : {gps_enabled or '—'}")

    ui.pause()


def _cell_triangulation(adb, st: dict) -> None:
    ui.clear(); ui.rule("Cell-Tower Triangulation", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    towers = adb.shell(
        "dumpsys telephony.registry 2>/dev/null | "
        "grep -E 'mCellInfo|mCid|mLac|mMcc|mMnc|signalStrength|mPci' | head -30",
        timeout=10
    ).strip()

    if not towers:
        towers = adb.shell(
            "dumpsys telephony 2>/dev/null | "
            "grep -E 'CellInfo|cellId|lac|mcc|mnc' | head -20",
            timeout=10
        ).strip()

    if towers:
        print(f"  Erkannte Cell-Tower:\n")
        for line in towers.splitlines()[:20]:
            print(f"    {line.strip()}")
    else:
        print(f"  ℹ  Keine Cell-Tower Daten lesbar")

    # SIM + Netz-Info
    mcc = adb.getprop("gsm.sim.operator.numeric") or "—"
    op  = adb.getprop("gsm.operator.alpha") or "—"
    print(f"\n  Netzoperator    : {op}")
    print(f"  MCC/MNC         : {mcc}")

    ui.pause()


def _wifi_location(adb, st: dict) -> None:
    ui.clear(); ui.rule("WLAN-Standortverlauf", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # Gespeicherte WLANs (Hinweis auf besuchte Orte)
    nets = adb.shell(
        "cmd wifi list-networks 2>/dev/null | head -20 || "
        "dumpsys wifi 2>/dev/null | grep -E 'SSID:|configKey' | head -20",
        timeout=10
    ).strip()

    if nets:
        print(f"  Gespeicherte WLAN-Netzwerke (Standorthinweise):\n")
        for line in nets.splitlines()[:20]:
            print(f"    {line.strip()}")
        print(f"\n  ℹ  Gespeicherte WLANs = besuchte Orte (SSID-Geolocation möglich)")
    else:
        print(f"  ℹ  WLAN-Liste nicht abrufbar")

    ui.pause()


def _location_permissions(adb, st: dict) -> None:
    ui.clear(); ui.rule("Location-Berechtigungen je App", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # Apps mit ACCESS_FINE_LOCATION
    fine = adb.shell(
        "pm list packages -3 2>/dev/null | while read p; do p=${p#package:}; "
        "pm dump $p 2>/dev/null | grep -q 'ACCESS_FINE_LOCATION' && echo $p; "
        "done 2>/dev/null | head -15",
        timeout=20
    ).strip()

    coarse = adb.shell(
        "pm list packages -3 2>/dev/null | while read p; do p=${p#package:}; "
        "pm dump $p 2>/dev/null | grep -q 'ACCESS_BACKGROUND_LOCATION' && echo $p; "
        "done 2>/dev/null | head -10",
        timeout=20
    ).strip()

    print(f"  Apps mit FINE_LOCATION:")
    if fine:
        for pkg in fine.splitlines():
            print(f"    📍 {pkg}")
    else:
        print(f"    (keine)")

    print(f"\n  Apps mit BACKGROUND_LOCATION (dauerhaft):")
    if coarse:
        for pkg in coarse.splitlines():
            print(f"    🔴 {pkg}")
    else:
        print(f"    (keine)")

    ui.pause()


def _exif_geodata(adb, st: dict) -> None:
    ui.clear(); ui.rule("Foto-EXIF Geo-Daten (DCIM)", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # EXIF via exiftool auf dem Gerät (falls vorhanden), sonst strings-Fallback
    exif_tool = adb.shell("which exiftool 2>/dev/null", timeout=3).strip()
    photos = adb.shell(
        "find /sdcard/DCIM /sdcard/Pictures 2>/dev/null -name '*.jpg' -o -name '*.jpeg' | head -5",
        timeout=8
    ).strip()

    if not photos:
        print(f"  ℹ  Keine Fotos in /sdcard/DCIM oder /sdcard/Pictures gefunden")
        ui.pause()
        return

    print(f"  Neueste Fotos ({len(photos.splitlines())} gefunden):\n")
    for photo in photos.splitlines()[:5]:
        print(f"  📸 {photo}")
        # GPS-Strings aus JPEG-Daten lesen (EXIF ohne exiftool)
        gps = adb.shell(
            f"strings {photo!r} 2>/dev/null | grep -iE 'GPS|lat|lon|°' | head -3",
            timeout=5
        ).strip()
        if gps:
            for g in gps.splitlines():
                print(f"       {g}")

    ui.pause()


def _maps_indications(adb, st: dict) -> None:
    ui.clear(); ui.rule("Google Maps / Fitness Indizien", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # Maps-App vorhanden?
    maps_installed = adb.shell("pm list packages | grep 'com.google.android.apps.maps'", timeout=5).strip()
    fitness = adb.shell("pm list packages | grep -E 'fitness|health|strava|komoot|runkeeper'", timeout=5).strip()

    print(f"  Google Maps    : {'✅ installiert' if maps_installed else '❌ nicht installiert'}")
    if fitness:
        print(f"\n  Sport/Fitness-Apps (Location-Tracking):")
        for pkg in fitness.splitlines():
            print(f"    🏃 {pkg.replace('package:','')}")

    # Letzter bekannter Ort via Location Manager
    last_known = adb.shell(
        "dumpsys location 2>/dev/null | grep -A3 'last location' | head -8",
        timeout=8
    ).strip()
    if last_known:
        print(f"\n  Letzter bekannter Standort:")
        for line in last_known.splitlines():
            print(f"    {line.strip()}")

    ui.pause()


def _full_report(adb, st: dict) -> None:
    ui.clear(); ui.rule("Geo-Forensik Komplettstatus", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    lines = ["=== GEO-FORENSIK KOMPLETTSTATUS ===\n"]

    loc_mode = adb.shell("settings get secure location_mode 2>/dev/null", timeout=5).strip()
    lines.append(f"  Location-Mode       : {loc_mode or '—'}")

    gps_apps = adb.shell(
        "cmd appops query-op FINE_LOCATION allow 2>/dev/null | head -10 || "
        "dumpsys appops 2>/dev/null | grep 'FINE_LOCATION.*allow' | head -10",
        timeout=10
    ).strip()
    if gps_apps:
        lines.append(f"\n  Apps mit aktivem GPS-Zugriff:")
        for line in gps_apps.splitlines()[:10]:
            lines.append(f"    {line.strip()}")

    towers = adb.shell(
        "dumpsys telephony.registry 2>/dev/null | grep -c 'mCellInfo'", timeout=5
    ).strip()
    lines.append(f"\n  Cell-Tower Records  : {towers or '0'}")

    photos = adb.shell(
        "find /sdcard/DCIM /sdcard/Pictures 2>/dev/null -name '*.jpg' | wc -l", timeout=5
    ).strip()
    lines.append(f"  Fotos gesamt        : {photos or '0'}")

    report_text = "\n".join(lines)
    ui.pager(report_text, "Geo-Forensik Bericht")
    ui.pause()
