"""MODERN STARTUP SCREEN: Premium UI + vollständiger 54-Modul-Scan bei jedem Start.

Nach dem Banner werden ALLE 54 Hauptmenü-Module per Import-Test auf Funktionalität
geprüft. Fehler blinken rot. Beides wird bei jedem Start automatisch ausgeführt.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import ui
from . import enhanced_startup


_CACHE_FILE = os.path.expanduser("~/.cache/androidpanzer/module_scan.json")
_CACHE_MAX_AGE_S = 3600 * 8  # 8 Stunden


# ─── Modul-Registry: (nr, anzeigename, apz-module, funktion) ──────────────────
# Jedes Hauptmenü-Item wird auf dieses Modul+Funktion geprüft.
_MODULE_REGISTRY: list[tuple[int, str, str, str]] = [
    # Tier 1: Basis-Analyse
    (1,  "🔬 TIEFE ANALYSE",       "deep_analysis_scan",       "menu"),
    (2,  "📊 DASHBOARD",            "dashboard",                "render"),
    (3,  "📋 KATEGORIEN",           "numeric_menu",             "NumericMainMenu"),
    (4,  "🎨 UI THEME",             "settings_manager",         "show_settings"),
    (5,  "⚙️  EINSTELLUNGEN",        "settings_manager",         "show_settings"),
    # Tier 2: Audio/Video/Netz
    (6,  "🎙️  MICROPHONE TAP",       "microphone_tap",           "menu"),
    (7,  "📷 CAMERA TAP",           "camera_tap",               "menu"),
    (8,  "🌐 NETWORK ANALYZER",     "network_analyzer",         "menu"),
    # Tier 3: Forensik & Scanning
    (9,  "🔍 FORENSIK SUITE",       "forensics",                "menu"),
    (10, "📦 APK SCANNER",          "apkscan",                  "menu"),
    (11, "🗃️  APP SCANNER",          "appscan",                  "menu"),
    (12, "📁 DATEI TREE",           "filetree",                 "menu"),
    (13, "💾 DATEN FORENSIK",       "dataforensics",            "menu"),
    # Tier 4: Erweiterte Tools
    (14, "🎯 TIEFE ENGINE",         "frida_engine",             "menu"),
    (15, "🗂️  CASE DATABASE",        "casedb",                   "menu"),
    (16, "📄 REPORT GENERATOR",     "report",                   "menu"),
    (17, "🔄 MODE SWITCH",          "modeswitch",               "menu"),
    (18, "🔧 CUSTOM FIRMWARE",      "customfw",                 "show_custom_firmware"),
    # Tier 5: Specials & Advanced
    (19, "🌐 ROOTKIT SCANNER",      "rootkit",                  "menu"),
    (20, "🚀 ROOTING TOOLS",        "rooting",                  "show_and_offer"),
    (21, "📸 DATA ACQUISITION",     "acquire",                  "menu"),
    (22, "🔓 APP DECRYPTION",       "app_decryption",           "menu"),
    (23, "🔨 BRUTE FORCE",          "brute_force",              "menu"),
    (24, "📡 WIFI HANDSHAKE",       "wifi_handshake",           "menu"),
    # Tier 6: Security & Intelligence
    (25, "🛡️  DNS GUARDIAN",         "dns_guardian",             "menu"),
    (26, "🎯 TRACKER SYSTEM",       "tracker_system",           "menu"),
    (27, "🧠 INTELLIGENT ENGINE",   "intelligent_engine",       "menu"),
    (28, "💾 DATABASE SCANNER",     "database_scanner",         "menu"),
    (29, "🧪 LAB MANAGER",          "lab_manager",              "menu"),
    (30, "🌐 3D WIFI SCANNER",      "wifi_room_scanner_3d",     "menu"),
    # Tier 7: New Advanced
    (31, "🔍 ADULT DETECTOR",       "adult_activity_detector",  "menu"),
    (32, "🔴 ANOMALY DETECTOR",     "anomaly_detector",         "menu"),
    (33, "🏥 AI DOCTOR",            "ai_doctor",                "menu"),
    # Tier 8: Forensic Advanced
    (34, "🔬 FORENSIC ANALYZER",    "forensic_audio_analyzer",  "menu"),
    (35, "🔐 SECURITY FRAMEWORK",   "security_framework",       "menu"),
    (36, "🔑 PASSWORD MANAGER",     "password_manager",         "menu"),
    (37, "🎵 AUDIO PLAYBACK",       "audio_playback",           "menu"),
    (38, "🐚 ADB SHELL",            "adb_shell",                "menu"),
    (39, "🔓 AUTO ROOT ENGINE",     "auto_root_engine",         "menu"),
    (40, "🎤 KEYWORD RECORDER",     "keyword_recorder",         "menu"),
    # Tier 9: Klassische + Neue Tools
    (41, "🚑 AUTO-RESCUE",          "rescue",                   "auto_rescue"),
    (42, "📡 BOOTLOOP-MONITOR",     "bootloop",                 "monitor"),
    (43, "🕵  OSINT-TOOLKIT",        "osint",                    "menu"),
    (44, "🤖 KI-ADB-SHELL",         "aishell",                  "menu"),
    (45, "📱 SAMSUNG TOOLS",        "samsung",                  "menu"),
    (46, "🔶 MEDIATEK ROOT",        "mediatek",                 "menu"),
    (47, "🏷  HERSTELLER-TOOLS",     "brands",                   "menu"),
    (48, "📶 MOBILFUNK-MONITOR",    "handlers",                 "cell_monitor"),
    (49, "🧪 LABOR-EINRICHTUNG",    "labsetup",                 "menu"),
    (50, "🔬 DEEP-FORENSIK",        "deepforensics",            "menu"),
    (51, "📞 TELEFON-OSINT",        "phoneosint",               "menu"),
    (52, "🔑 GOOGLE-KONTEN",        "google_account_scanner",   "menu"),
    (53, "📱 KONTO-SCANNER",        "account_scanner",          "menu"),
    (54, "🔒 FRP-SCANNER",          "frp_scanner",              "menu"),
    (55, "💳 SIM-TOOLKIT",          "sim_toolkit",              "menu"),
    (56, "🌐 APP-DOMAIN MONITOR",   "app_traffic_monitor",      "menu"),
    (57, "🕵️  PLAY STORE FORENSICS", "playstore_forensics.main", "menu"),
    # Tier 13: Neue Module
    (58, "🔐 VERSCHLÜSSELUNGS-SCANNER", "encryption_scanner",      "menu"),
    (59, "📍 GEO-FORENSIK",             "geo_forensics",            "menu"),
    (60, "🧬 SENSOR-FORENSIK",          "sensor_forensics",         "menu"),
]


# ─── Externe Abhängigkeiten je Modul ─────────────────────────────────────────
# Bins = Systemtools (shutil.which), pips = Python-Pakete (importlib.util.find_spec)
_MODULE_DEPS: dict[str, dict] = {
    "deep_analysis_scan":       {"bins": ["adb"],                    "pips": []},
    "dashboard":                {"bins": ["adb"],                    "pips": []},
    "microphone_tap":           {"bins": ["adb"],                    "pips": []},
    "camera_tap":               {"bins": ["adb"],                    "pips": []},
    "network_analyzer":         {"bins": ["adb"],                    "pips": []},
    "forensics":                {"bins": ["adb"],                    "pips": []},
    "apkscan":                  {"bins": ["adb"],                    "pips": []},
    "appscan":                  {"bins": ["adb"],                    "pips": []},
    "filetree":                 {"bins": ["adb"],                    "pips": []},
    "dataforensics":            {"bins": ["adb"],                    "pips": []},
    "frida_engine":             {"bins": ["adb", "frida"],           "pips": ["frida"]},
    "casedb":                   {"bins": [],                         "pips": []},
    "report":                   {"bins": [],                         "pips": []},
    "modeswitch":               {"bins": ["adb"],                    "pips": []},
    "customfw":                 {"bins": ["adb"],                    "pips": []},
    "rootkit":                  {"bins": ["adb"],                    "pips": []},
    "rooting":                  {"bins": ["adb"],                    "pips": []},
    "acquire":                  {"bins": ["adb"],                    "pips": []},
    "app_decryption":           {"bins": ["adb"],                    "pips": []},
    "brute_force":              {"bins": ["adb"],                    "pips": []},
    "wifi_handshake":           {"bins": ["aircrack-ng"],            "pips": []},
    "dns_guardian":             {"bins": ["adb"],                    "pips": []},
    "tracker_system":           {"bins": ["adb"],                    "pips": []},
    "intelligent_engine":       {"bins": ["adb"],                    "pips": []},
    "database_scanner":         {"bins": ["adb"],                    "pips": []},
    "lab_manager":              {"bins": [],                         "pips": []},
    "labsetup":                 {"bins": [],                         "pips": []},
    "wifi_room_scanner_3d":     {"bins": ["adb", "iwlist"],         "pips": []},
    "adult_activity_detector":  {"bins": ["adb"],                    "pips": []},
    "anomaly_detector":         {"bins": ["adb"],                    "pips": []},
    "ai_doctor":                {"bins": ["adb"],                    "pips": []},
    "forensic_audio_analyzer":  {"bins": ["adb"],                    "pips": []},
    "security_framework":       {"bins": ["adb"],                    "pips": []},
    "password_manager":         {"bins": [],                         "pips": []},
    "audio_playback":           {"bins": ["adb"],                    "pips": []},
    "adb_shell":                {"bins": ["adb"],                    "pips": []},
    "auto_root_engine":         {"bins": ["adb"],                    "pips": []},
    "keyword_recorder":         {"bins": ["adb"],                    "pips": []},
    "rescue":                   {"bins": ["adb"],                    "pips": []},
    "bootloop":                 {"bins": ["adb"],                    "pips": []},
    "osint":                    {"bins": [],                         "pips": []},
    "aishell":                  {"bins": ["adb"],                    "pips": []},
    "samsung":                  {"bins": ["adb"],                    "pips": []},
    "mediatek":                 {"bins": ["adb"],                    "pips": []},
    "brands":                   {"bins": ["adb"],                    "pips": []},
    "handlers":                 {"bins": ["adb"],                    "pips": []},
    "deepforensics":            {"bins": ["adb"],                    "pips": []},
    "phoneosint":               {"bins": [],                         "pips": []},
    "google_account_scanner":   {"bins": ["adb"],                    "pips": []},
    "account_scanner":          {"bins": ["adb"],                    "pips": []},
    "frp_scanner":              {"bins": ["adb"],                    "pips": []},
    "settings_manager":         {"bins": [],                         "pips": []},
    "numeric_menu":             {"bins": [],                         "pips": []},
    "sim_toolkit":              {"bins": ["adb"],                    "pips": []},
    "app_traffic_monitor":      {"bins": ["adb"],                    "pips": []},
    "playstore_forensics.main": {"bins": ["adb"],                    "pips": []},
    "encryption_scanner":       {"bins": ["adb"],                    "pips": []},
    "geo_forensics":            {"bins": ["adb"],                    "pips": []},
    "sensor_forensics":         {"bins": ["adb"],                    "pips": []},
}


def _get_cache_key() -> str:
    apz_dir = os.path.dirname(__file__)
    h = hashlib.md5()
    for fname in sorted(os.listdir(apz_dir)):
        if fname.endswith(".py"):
            try:
                h.update(str(os.path.getmtime(os.path.join(apz_dir, fname))).encode())
            except OSError:
                pass
    return h.hexdigest()


def _load_scan_cache() -> list | None:
    try:
        if not os.path.exists(_CACHE_FILE):
            return None
        with open(_CACHE_FILE) as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) > _CACHE_MAX_AGE_S:
            return None
        if data.get("key") != _get_cache_key():
            return None
        return data.get("failures", [])
    except Exception:
        return None


def _save_scan_cache(failures: list) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        with open(_CACHE_FILE, "w") as f:
            json.dump({"ts": time.time(), "key": _get_cache_key(), "failures": [list(x) for x in failures]}, f)
    except Exception:
        pass


def _check_bin(name: str) -> bool:
    return shutil.which(name) is not None


def _check_pip(mod: str) -> bool:
    for n in (mod.replace("-", "_"), mod.replace("-", "_").split("_")[0]):
        try:
            if importlib.util.find_spec(n) is not None:
                return True
        except (ImportError, ValueError, ModuleNotFoundError):
            pass
    return False


# ─── Modul-Check ──────────────────────────────────────────────────────────────

def _check_module(module_name: str, func_name: str) -> tuple[bool, str, list[str], list[str]]:
    """ECHTER Check: Import + Funktion + Binaries + pip-Pakete.
    Gibt (ok, fehler_text, fehlende_bins, fehlende_pips) zurück.
    ok=False nur bei Import-Fehler oder fehlender Funktion (KRITISCH).
    Fehlende Tools = Warnung, kein Fehler (Module können trotzdem laufen).
    """
    # 1. Import-Test (relativ zu apz, Fallback auf absoluten Import)
    try:
        mod = importlib.import_module(f".{module_name}", package="apz")
    except ImportError:
        try:
            mod = importlib.import_module(module_name)
        except ImportError as e:
            return False, f"Import-Fehler: {e}", [], []
        except Exception as e:  # noqa: BLE001
            return False, f"Fehler: {e}", [], []
    except Exception as e:  # noqa: BLE001
        return False, f"Fehler: {e}", [], []

    # 2. Funktion vorhanden?
    if not hasattr(mod, func_name):
        return False, f"Funktion '{func_name}' fehlt", [], []

    # 3. Externe Abhängigkeiten prüfen (Warnings, kein Fehler)
    deps = _MODULE_DEPS.get(module_name, {})
    missing_bins = [b for b in deps.get("bins", []) if not _check_bin(b)]
    missing_pips = [p for p in deps.get("pips", []) if not _check_pip(p)]

    return True, "", missing_bins, missing_pips


# ─── Blink-Effekt ─────────────────────────────────────────────────────────────

def _blink_failures(failures: list[tuple[int, str, str]]) -> None:
    """Lässt fehlerhafte Module 4× rot aufblinken (KRITISCHE Fehler = Import/Funktion fehlt)."""
    lines = len(failures)
    if lines == 0:
        return

    BLINK_ON  = ui.BLINK + ui.BRED
    BLINK_OFF = ui.BRED
    RST       = ui.RESET

    def _print_failures(blink: bool) -> None:
        color = BLINK_ON if blink else BLINK_OFF
        for nr, name, err in failures:
            print(f"  {color}  ✗  [{nr:02d}] {name:<28}  ({err}){RST}")

    for cycle in range(4):
        _print_failures(blink=True)
        time.sleep(0.35)
        sys.stdout.write(f"\033[{lines}A\r")
        sys.stdout.flush()
        _print_failures(blink=False)
        time.sleep(0.25)
        if cycle < 3:
            sys.stdout.write(f"\033[{lines}A\r")
            sys.stdout.flush()


def _blink_warnings(warnings: list[tuple[int, str, list, list]]) -> None:
    """Lässt Module mit fehlenden Abhängigkeiten 2× GELB blinken."""
    lines = len(warnings)
    if lines == 0:
        return
    WARN_ON  = ui.BLINK + ui.BYELLOW
    WARN_OFF = ui.BYELLOW
    RST      = ui.RESET

    def _print_warns(blink: bool) -> None:
        c = WARN_ON if blink else WARN_OFF
        for nr, name, missing_bins, missing_pips in warnings:
            # Deduplizieren: "frida, frida" → "frida"
            missing = ", ".join(dict.fromkeys(missing_bins + missing_pips))
            print(f"  {c}  ⚠  [{nr:02d}] {name:<28}  fehlt: {missing}{RST}")

    for cycle in range(2):
        _print_warns(blink=True)
        time.sleep(0.35)
        sys.stdout.write(f"\033[{lines}A\r")
        sys.stdout.flush()
        _print_warns(blink=False)
        time.sleep(0.25)
        if cycle < 1:
            sys.stdout.write(f"\033[{lines}A\r")
            sys.stdout.flush()


# ─── Haupt-Scan ───────────────────────────────────────────────────────────────

def scan_all_modules() -> list[tuple[int, str, str]]:
    """ECHTER Scan aller 60 Module: Import + Funktion + externe Abhängigkeiten.

    Jedes Modul läuft 0% → 100% (3 Phasen).
    Herzschlag-Puls an der Prozentzahl wenn Fehler/Warnung gefunden.
    Gibt Liste der KRITISCHEN Fehler zurück: [(nr, name, fehlertext), ...]
    """
    total = len(_MODULE_REGISTRY)
    failures: list[tuple[int, str, str]] = []
    warnings: list[tuple[int, str, list, list]] = []
    # Infos für Fehler-Detail-Ausgabe
    warn_details: list[tuple[int, str, list, list]] = []

    print(f"\n{ui.BCYAN}{'─'*78}{ui.RESET}")
    print(f"  {ui.BOLD}⚙  ECHTER MODULE-SCAN  –  {total} Hauptmenü-Punkte · 3 Prüfschichten{ui.RESET}")
    print(f"  {ui.GREY}[1] Python-Import  [2] Funktions-Test  [3] Binaries/pip-Pakete{ui.RESET}")
    print(f"{ui.BCYAN}{'─'*78}{ui.RESET}\n")

    bar_len = 26
    full_bar = "▰" * bar_len

    for idx, (nr, name, module, func) in enumerate(_MODULE_REGISTRY, 1):

        # ── Phase 1: Import (0% → 40%) ─────────────────────────────────────────
        for step in range(0, 41, 8):
            filled = int(bar_len * step / 100)
            bar = "▰" * filled + "▱" * (bar_len - filled)
            sys.stdout.write(
                f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                f"{ui.CYAN}│{bar}│{ui.RESET} {step:5.1f}%  {ui.GREY}Import…{ui.RESET}   "
            )
            sys.stdout.flush()
            time.sleep(0.002)

        ok, err_txt, missing_bins, missing_pips = _check_module(module, func)

        # ── Phase 2: Funktion (40% → 70%) ──────────────────────────────────────
        for step in range(40, 71, 6):
            filled = int(bar_len * step / 100)
            bar = "▰" * filled + "▱" * (bar_len - filled)
            sys.stdout.write(
                f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                f"{ui.CYAN}│{bar}│{ui.RESET} {step:5.1f}%  {ui.GREY}Funktion…{ui.RESET} "
            )
            sys.stdout.flush()
            time.sleep(0.002)

        # ── Phase 3: Deps (70% → 100%) ─────────────────────────────────────────
        for step in range(70, 101, 6):
            filled = int(bar_len * step / 100)
            bar = "▰" * filled + "▱" * (bar_len - filled)
            sys.stdout.write(
                f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                f"{ui.CYAN}│{bar}│{ui.RESET} {step:5.1f}%  {ui.GREY}Deps…{ui.RESET}     "
            )
            sys.stdout.flush()
            time.sleep(0.002)

        # ── Ergebnis + Herzschlag-Puls ─────────────────────────────────────────
        if not ok:
            failures.append((nr, name, err_txt))
            # ROT Herzschlag-Puls an der Prozentzahl
            for pulse in range(3):
                sys.stdout.write(
                    f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                    f"{ui.BRED}│{full_bar}│{ui.RESET} {ui.BRED}{ui.BOLD}100.0%{ui.RESET}"
                    f"  {ui.BRED}✗ KRITISCH{ui.RESET}                          "
                )
                sys.stdout.flush()
                time.sleep(0.14)
                sys.stdout.write(
                    f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                    f"{ui.BRED}│{full_bar}│{ui.RESET} {ui.GREY}100.0%{ui.RESET}"
                    f"  {ui.BRED}✗ KRITISCH{ui.RESET}                          "
                )
                sys.stdout.flush()
                time.sleep(0.08)
            # Finale Zeile mit Fehlerdetail
            short_err = err_txt[:35] if err_txt else "unbekannt"
            sys.stdout.write(
                f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                f"{ui.BRED}│{full_bar}│{ui.RESET} {ui.BRED}100.0%  ✗ KRITISCH  ({short_err}){ui.RESET}\n"
            )
            sys.stdout.flush()

        elif missing_bins or missing_pips:
            # Deduplizieren: "frida, frida" → "frida"
            missing_dedup = list(dict.fromkeys(missing_bins + missing_pips))
            missing = ", ".join(missing_dedup)
            warnings.append((nr, name, missing_bins, missing_pips))
            warn_details.append((nr, name, missing_bins, missing_pips))
            # GELB Herzschlag-Puls an der Prozentzahl
            for pulse in range(4):
                sys.stdout.write(
                    f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                    f"{ui.BYELLOW}│{full_bar}│{ui.RESET} {ui.BYELLOW}{ui.BOLD}100.0%{ui.RESET}"
                    f"  {ui.BYELLOW}⚠ TOOLS FEHLEN: {missing[:30]}{ui.RESET}"
                )
                sys.stdout.flush()
                time.sleep(0.12)
                sys.stdout.write(
                    f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                    f"{ui.CYAN}│{full_bar}│{ui.RESET}  {ui.GREY}100.0%{ui.RESET}"
                    f"  {ui.BYELLOW}⚠ TOOLS FEHLEN: {missing[:30]}{ui.RESET}"
                )
                sys.stdout.flush()
                time.sleep(0.08)
            # Finale Zeile
            sys.stdout.write(
                f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                f"{ui.BYELLOW}│{full_bar}│{ui.RESET} {ui.BYELLOW}100.0%  ⚠ TOOLS FEHLEN: {missing[:30]}{ui.RESET}\n"
            )
            sys.stdout.flush()

        else:
            sys.stdout.write(
                f"\r  {ui.GREY}[{nr:02d}]{ui.RESET} {name:<26} "
                f"{ui.CYAN}│{full_bar}│{ui.RESET} 100.0%  {ui.BGREEN}✓ OK{ui.RESET}\n"
            )
            sys.stdout.flush()

    print()

    # ── Kritische Fehler (rot blinkend + Detailinfo) ───────────────────────────
    if failures:
        print(f"{ui.BRED}{'─'*78}{ui.RESET}")
        print(f"  {ui.BRED}{ui.BOLD}✗  {len(failures)} KRITISCHE FEHLER – Module nicht nutzbar:{ui.RESET}")
        print(f"{ui.BRED}{'─'*78}{ui.RESET}\n")
        _blink_failures(failures)
        print()
        for nr, name, err in failures:
            print(f"  {ui.BRED}[{nr:02d}] {name}{ui.RESET}")
            print(f"        {ui.GREY}Ursache: {err}{ui.RESET}")
            print(f"        {ui.GREY}Prüfe: apz/{name.lower().replace(' ','_')}.py{ui.RESET}")
        print()
        print(f"  {ui.BRED}{ui.BOLD}→ Prüfe die Modul-Dateien im apz/-Verzeichnis.{ui.RESET}")
        print()

    # ── Warnungen (gelb blinkend + Detailinfo) ────────────────────────────────
    if warnings:
        print(f"{ui.BYELLOW}{'─'*78}{ui.RESET}")
        print(f"  {ui.BYELLOW}{ui.BOLD}⚠  {len(warnings)} Module mit fehlenden OPTIONALEN Tools:{ui.RESET}")
        print(f"  {ui.GREY}(Module sind nutzbar – nur Funktionen die das externe Tool brauchen sind eingeschränkt){ui.RESET}")
        print(f"{ui.BYELLOW}{'─'*78}{ui.RESET}\n")
        _blink_warnings(warnings)
        print()
        # Detailinfos je Modul
        for nr, name, mbins, mpips in warn_details:
            missing_dedup = list(dict.fromkeys(mbins + mpips))
            print(f"  {ui.BYELLOW}[{nr:02d}] {name}{ui.RESET}")
            if mbins:
                unique_bins = list(dict.fromkeys(mbins))
                print(f"        {ui.GREY}Fehlende Binaries: {', '.join(unique_bins)}{ui.RESET}")
                for b in unique_bins:
                    print(f"        {ui.CYAN}→ sudo apt install {b}{ui.RESET}")
            if mpips:
                unique_pips = list(dict.fromkeys(mpips))
                print(f"        {ui.GREY}Fehlende pip-Pakete: {', '.join(unique_pips)}{ui.RESET}")
                for p in unique_pips:
                    print(f"        {ui.CYAN}→ pip install {p}  (oder Option P im Mediatek-Menü / Option 49){ui.RESET}")
        print()
        print(f"  {ui.BYELLOW}→ Labor-Einrichtung (Option 49) zum Installieren fehlender Tools.{ui.RESET}")
        print()

    if not failures and not warnings:
        print(f"  {ui.BGREEN}{ui.BOLD}✓  ALLE {total} MODULE VOLLSTÄNDIG – ALLE ABHÄNGIGKEITEN OK{ui.RESET}")
    elif not failures:
        print(f"  {ui.BGREEN}✓  ALLE {total} MODULE GELADEN  –  {len(warnings)} mit optionalen Warnungen{ui.RESET}")

    print(f"\n{ui.BCYAN}{'─'*78}{ui.RESET}\n")
    return failures


# ─── Live-Fortschrittsbalken für laufende Tools ───────────────────────────────

class LiveBar:
    """Zeigt einen Live-Fortschrittsbalken während ein Tool läuft.

    Verwendung:
        with LiveBar("APK-Scan", 42) as bar:
            bar.update(1, "Manifest analysieren")
            bar.update(2, "Permissions prüfen")
            ...
    """
    BAR_LEN = 36

    def __init__(self, tool_name: str, total: int):
        self.tool_name = tool_name
        self.total = max(1, total)
        self._step = 0
        self._start = time.monotonic()

    def __enter__(self) -> "LiveBar":
        print(f"\n{ui.BCYAN}▶ {self.tool_name}{ui.RESET}")
        self._draw(0, "Starte …")
        return self

    def __exit__(self, *_) -> None:
        self._draw(self.total, "Abgeschlossen")
        elapsed = time.monotonic() - self._start
        print(f"\n  {ui.BGREEN}✓ {self.tool_name} fertig  ({elapsed:.1f}s){ui.RESET}\n")

    def update(self, step: int, label: str = "") -> None:
        self._step = step
        self._draw(step, label)

    def _draw(self, step: int, label: str) -> None:
        pct = min(step / self.total, 1.0)
        filled = int(self.BAR_LEN * pct)
        bar = "▰" * filled + "▱" * (self.BAR_LEN - filled)
        elapsed = time.monotonic() - self._start
        sys.stdout.write(
            f"\r  {ui.CYAN}│{bar}│{ui.RESET} "
            f"{pct*100:5.1f}%  {label:<32}  {elapsed:4.1f}s"
        )
        sys.stdout.flush()


def tool_progress(label: str, steps: list[str], delay: float = 0.08) -> None:
    """Hilfsfunktion: Führt eine Liste von Schritten mit Live-Balken durch.

    Verwendung:
        tool_progress("APK-Scan", ["Manifest lesen", "DEX analysieren", "Report"])
    """
    with LiveBar(label, len(steps)) as bar:
        for i, step in enumerate(steps, 1):
            bar.update(i, step)
            time.sleep(delay)


# ─── Splash-Screen ────────────────────────────────────────────────────────────

def show_modern_splash() -> None:
    """Zeigt Premium Splash-Screen."""
    ui.clear()

    print(f"\n{ui.BCYAN}")
    print("    ╔═══════════════════════════════════════════════════════════╗")
    print("    ║                                                           ║")
    print(f"    ║       {ui.BOLD}█████████████████████████████████████{ui.RESET}{ui.BCYAN}         ║")
    print(f"    ║       {ui.BOLD}██        ANDROID PANZER          ██{ui.RESET}{ui.BCYAN}         ║")
    print(f"    ║       {ui.BOLD}█████████████████████████████████████{ui.RESET}{ui.BCYAN}         ║")
    print("    ║                                                           ║")
    print(f"    ║     {ui.BGREEN}🧠  VORSPRUNG DURCH INTELLIGENZ  🧠{ui.RESET}{ui.BCYAN}           ║")
    print("    ║                                                           ║")
    print(f"    ║      {ui.YELLOW}Professional Forensic Analysis Platform{ui.RESET}{ui.BCYAN}        ║")
    print("    ║                                                           ║")
    print("    ╚═══════════════════════════════════════════════════════════╝")
    print(f"{ui.RESET}\n")

    print(f"{ui.BCYAN}{'━'*66}{ui.RESET}\n")

    features = [
        ("🤖", f"{len(_MODULE_REGISTRY)} Menüpunkte", "vollständig auf Funktion geprüft"),
        ("📊", "450 Features",        "Umfassende Forensische Analyse"),
        ("🎙️",  "Microphone Tap",      "Audio-Erfassung & Keyword-Erkennung"),
        ("📷", "Camera Tap",          "Video-Recording & Screenshots"),
        ("🌐", "Network Analyzer",    "SIM/WiFi/Cellular Analysis"),
        ("🔍", "Content Scanner",     "Adult-Content Detection"),
        ("💾", "Virtual Filesystem",  "Kernel-protected Storage"),
        ("🔒", "FRP-Scanner",         "10 Erkennungsmethoden"),
    ]
    for emoji, title, desc in features:
        print(f"  {emoji}  {ui.BOLD}{title:<25}{ui.RESET}  {desc}")

    print(f"\n{ui.BCYAN}{'━'*66}{ui.RESET}\n")

    print(f"{ui.BGREEN}{ui.BOLD}")
    print("  ╭─────────────────────────────────────────────────────────────╮")
    print("  │   \"Intelligence Leads to Superior Performance\"              │")
    print("  │   Intelligenz ist der Schlüssel zur überlegenen Leistung   │")
    print("  ╰─────────────────────────────────────────────────────────────╯")
    print(f"{ui.RESET}\n")


# ─── Startup-Complete ─────────────────────────────────────────────────────────

def show_startup_complete(failures: list | None = None) -> None:
    """Zeigt System-Ready Nachricht."""
    ui.clear()
    total = len(_MODULE_REGISTRY)
    ok_count = total - (len(failures) if failures else 0)

    if not failures:
        color = ui.BGREEN
        status_line = f"✓ ALLE {total} MODULE GELADEN"
    else:
        color = ui.BYELLOW
        status_line = f"⚠  {ok_count}/{total} MODULE OK  –  {len(failures)} FEHLER"

    print(f"\n{color}")
    print("  ╔════════════════════════════════════════════════════════╗")
    print(f"  ║  {ui.BOLD}{status_line:<52}{ui.RESET}{color}  ║")
    print("  ║                                                        ║")
    print(f"  ║  AndroidPanzer – Forensic Intelligence Platform       ║")
    print(f"  ║  {ok_count}/{total} Hauptmenü-Punkte aktiv{' ' * (39 - len(str(ok_count)) - len(str(total)))}║")
    print("  ║  150 AI-Funktionen geladen                            ║")
    print("  ║  450 Features verfügbar                               ║")
    print("  ║                                                        ║")
    if failures:
        print(f"  ║  {ui.BRED}⚠  {len(failures)} Module mit Fehlern – siehe Scan oben{ui.RESET}{color}       ║")
    else:
        print(f"  ║  {ui.BGREEN}Vorsprung durch Intelligenz – Ready to Go!{ui.RESET}{color}             ║")
    print("  ║                                                        ║")
    print("  ╚════════════════════════════════════════════════════════╝")
    print(f"{ui.RESET}\n")
    time.sleep(0.2)


# ─── Haupt-Startup-Sequenz ────────────────────────────────────────────────────

def _auto_pip_preflight_bg() -> None:
    """Startet pip-Preflight asynchron in einem Daemon-Thread."""
    def _bg() -> None:
        try:
            from . import labsetup
            venv_python = os.path.join(os.path.expanduser("~/panzer_venv"), "bin", "python3")
            if not os.path.isfile(venv_python):
                return
            labsetup.auto_pip_preflight(quiet=True)
        except Exception:  # noqa: BLE001
            pass
    threading.Thread(target=_bg, daemon=True, name="panzer-pip-preflight").start()


def animate_startup() -> list[tuple[int, str, str]]:
    """Komplette Startup-Sequenz:
    1. Splash / Banner mit 'Intelligence Leads to Superior Performance'
    2. Scan aller 55 Module mit Live-Fortschrittsbalken
    3. Fehler blinken rot
    4. System-Ready-Meldung
    5. Pip-Vorab-Check (leise, wenn venv vorhanden)

    Gibt Liste der Fehler zurück.
    """
    show_modern_splash()
    failures = scan_all_modules()
    show_startup_complete(failures)
    show_feature_highlight()
    show_version_info()
    _auto_pip_preflight_bg()
    return failures


# ─── Hilfsfunktionen (unverändert / rückwärtskompatibel) ──────────────────────

def show_feature_highlight() -> None:
    highlights = [
        ("🧠 INTELLIGENTE KI-ANALYSE",   "150 KI-Funktionen analysieren alle 450 Features"),
        ("📊 LIVE DASHBOARDS",            "Echtzeit-Analyse mit interaktiven Dashboards"),
        ("🎙  SURVEILLANCE TOOLS",        "Mikrofon & Kamera mit Recording und Live-Stream"),
        ("🌐 NETZWERK-FORENSIK",          "SIM, WiFi, Cellular – Vollständige Netzwerk-Analyse"),
        ("💾 KERNEL-PROTECTED STORAGE",   "Virtual Filesystem – Daten vor Löschung geschützt"),
        ("🔍 CONTENT DETECTION",          "Adult-Content Scanner mit Keyword & Scoring"),
    ]
    h = highlights[int(time.time()) % len(highlights)]
    w = ui.width()
    inner = w - 4
    title_pad = inner - 2
    print(f"\n{ui.BCYAN}┌{'─' * (w - 2)}┐")
    print(f"│  {ui.BOLD}{ui.WHITE}{h[0]:<{title_pad}}{ui.RESET}{ui.BCYAN}  │")
    print(f"│  {ui.GREY}{h[1]:<{title_pad}}{ui.RESET}{ui.BCYAN}  │")
    print(f"└{'─' * (w - 2)}┘{ui.RESET}\n")


def show_version_info() -> None:
    from datetime import date
    ui.rule("VERSION", ui.CYAN)
    print(f"  AndroidPanzer    {ui.BOLD}2.0.0{ui.RESET}   "
          f"{ui.GREY}Stand: {date.today().isoformat()}   "
          f"{len(_MODULE_REGISTRY)} Hauptmenü-Punkte   {ui.RESET}"
          f"{ui.BGREEN}Production Ready{ui.RESET}\n")


def show_status_bar(status: str, progress: float = 0.0) -> None:
    bar_len = 40
    filled = int(bar_len * progress)
    bar = "▰" * filled + "▱" * (bar_len - filled)
    print(f"\n{ui.BCYAN}  {status:30} │{bar}│ {progress*100:5.1f}%{ui.RESET}")


def show_main_menu_modern(device_brand: str = "", device_model: str = "") -> None:
    """Zeigt modernes Hauptmenü (Legacy-Kompatibilität)."""
    ui.clear()
    print(f"\n{ui.BCYAN}")
    print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    print(f"┃ {ui.BGREEN}🧠 ANDROID PANZER - FORENSIC INTELLIGENCE SYSTEM{ui.BCYAN}               ┃")
    print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    print(f"{ui.RESET}\n")
    if device_brand or device_model:
        print(f"  {ui.BOLD}Gerät: {device_brand} {device_model}{ui.RESET}\n")


def show_enhanced_startup_system() -> None:
    enhanced_startup.show_enhanced_startup_sequence()


def show_boot_device_analysis(adb, data: dict, st: dict) -> None:
    """Sicherheits-Schnellcheck nach dem Dashboard (kein clear – hängt direkt dran)."""
    brand   = data.get("brand", "")
    model   = data.get("model", "")
    android = data.get("android_version", "") or data.get("version", "")
    serial  = data.get("serial", "")
    is_root = bool(st.get("is_root"))

    ui.rule("SICHERHEITS-SCHNELLCHECK  (Echtzeit, kein Cache)", ui.CYAN)
    print()

    root_icon = f"{ui.BGREEN}ROOT AKTIV{ui.RESET}" if is_root else f"{ui.GREY}kein Root{ui.RESET}"
    print(f"  {ui.BOLD}{brand} {model}{ui.RESET}  {ui.GREY}({serial})  Android {android or '—'}  {root_icon}{ui.RESET}\n")

    risk_count = 0

    def _chk(cmd: str, timeout: int = 6) -> str:
        try:
            return adb.shell(cmd, timeout=timeout).strip()
        except Exception:
            return "—"

    with ThreadPoolExecutor(max_workers=6) as pool:
        f_selinux = pool.submit(_chk, "getenforce 2>/dev/null", 6)
        f_enc     = pool.submit(lambda: adb.getprop("ro.crypto.state") or "—")
        f_bl      = pool.submit(lambda: adb.getprop("ro.boot.verifiedbootstate") or adb.getprop("ro.boot.flash.locked") or "—")
        f_cas     = pool.submit(_chk, "ls /data/misc/user/0/cacerts-added/ 2>/dev/null | wc -l", 6)
        f_vpn     = pool.submit(_chk, "ip link show 2>/dev/null | grep -cE 'tun|ppp|wg'", 6)
        f_usb     = pool.submit(_chk, "settings get global adb_enabled 2>/dev/null", 5)

        selinux  = f_selinux.result()
        enc      = f_enc.result()
        bl       = f_bl.result()
        user_cas = f_cas.result()
        vpn      = f_vpn.result()
        usb_dbg  = f_usb.result()

    sel_icon = f"{ui.BGREEN}🟢 Enforcing{ui.RESET}" if selinux.lower() == "enforcing" \
               else f"{ui.BRED}🔴 {selinux or '—'}{ui.RESET}"
    if selinux.lower() != "enforcing":
        risk_count += 1
    print(f"     SELinux          : {sel_icon}")

    enc_icon = f"{ui.BGREEN}🔒 {enc}{ui.RESET}" if enc == "encrypted" \
               else f"{ui.BRED}🔓 {enc}{ui.RESET}"
    if enc != "encrypted":
        risk_count += 1
    print(f"     Verschlüsselung  : {enc_icon}")

    bl_icon = f"{ui.BGREEN}🔒 {bl}{ui.RESET}" if bl in ("green", "1", "locked") \
              else f"{ui.BYELLOW}⚠  {bl}{ui.RESET}"
    print(f"     Bootloader       : {bl_icon}")

    try:
        ca_n = int(user_cas)
    except (ValueError, TypeError):
        ca_n = 0
    ca_icon = f"{ui.BRED}⚠  {ca_n} User-CA(s) – MITM-Risiko!{ui.RESET}" if ca_n > 0 \
              else f"{ui.BGREEN}✅ keine User-CAs{ui.RESET}"
    if ca_n > 0:
        risk_count += 1
    print(f"     Zertifikate      : {ca_icon}")

    try:
        vpn_n = int(vpn)
    except (ValueError, TypeError):
        vpn_n = 0
    vpn_icon = f"{ui.BYELLOW}⚠  {vpn_n} aktive Tunnel{ui.RESET}" if vpn_n > 0 \
               else f"{ui.BGREEN}✅ kein VPN{ui.RESET}"
    print(f"     VPN-Tunnel       : {vpn_icon}")

    dbg_icon = f"{ui.BYELLOW}⚠  USB-Debug aktiv{ui.RESET}" if usb_dbg == "1" \
               else f"{ui.BGREEN}✅ USB-Debug aus{ui.RESET}"
    print(f"     USB-Debugging    : {dbg_icon}")

    apps = data.get("app_count") or data.get("user_apps")
    if not apps:
        apps_raw = adb.shell("pm list packages -3 2>/dev/null | wc -l", timeout=8).strip()
        try:
            apps = int(apps_raw)
        except (ValueError, TypeError):
            apps = "—"
    print(f"     Drittanbieter-Apps: {apps}")

    battery = data.get("battery") or data.get("battery_level")
    if not battery:
        bat_raw = adb.shell("dumpsys battery 2>/dev/null | grep 'level:' | head -1", timeout=5).strip()
        battery = bat_raw.replace("level:", "").strip() + "%" if bat_raw else "—"
    print(f"     Akku             : {battery}\n")

    if risk_count == 0:
        ui.ok("KEIN SICHERHEITSRISIKO ERKANNT")
    elif risk_count == 1:
        ui.warn(f"1 RISIKO – Gerät prüfen (SELinux / CAs / Encryption)")
    else:
        ui.err(f"{risk_count} RISIKEN ERKANNT – sofortige Forensik empfohlen")
    print()


def create_modern_startup(adb=None):
    class ModernStartup:
        def __init__(self, adb=None):
            self.adb = adb
        def show(self):
            show_modern_splash()
        def show_enhanced(self):
            show_enhanced_startup_system()
    return ModernStartup(adb)
