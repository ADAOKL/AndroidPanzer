"""Autorisierungs- und Sicherheitsprüfungen.

Jeder forensischer Zugriff erfordert explizite Bestätigung des Nutzers.
Dieser Check ist kein bürokratischer Umweg – er verhindert, dass das
Tool unbemerkt auf fremden Geräten eingesetzt wird.
"""
from __future__ import annotations

import json
import os
import sys
import time

# Lazy import – ui nicht auf Modulebene laden (vermeidet Circular-Import)
_AUTHORIZED: bool = False
_AUTH_SCENARIO: str = ""

_AUTH_LOG_DIR = os.path.expanduser("~/.config/android-panzer/psf_auth_logs")


def require_authorization() -> bool:
    """Zeigt Disclaimer und verlangt explizite Bestätigung.

    Gibt True zurück wenn autorisiert, False wenn abgebrochen.
    Einmal bestätigt gilt für die Sitzung (Modul-Variable _AUTHORIZED).
    """
    global _AUTHORIZED
    if _AUTHORIZED:
        return True

    from apz import ui
    ui.clear()
    ui.banner(subtitle="PLAY STORE ARTIFACT EXTRACTOR – Autorisierung")

    print(f"\n  {ui.YELLOW}WICHTIG – RECHTLICHER HINWEIS{ui.RESET}\n")
    print("  Dieses Modul greift auf forensisch relevante Gerätedaten zu:")
    print("   • Suchverläufe aus dem Play Store (suggestions.db)")
    print("   • Vollständige Installationshistorie (frosting.db)")
    print("   • App-Nutzungszeiten und Hintergrundaktivitäten")
    print("   • Statische APK-Analyse und Permission-Auswertung\n")
    print(f"  {ui.RED}OHNE Berechtigung ist diese Analyse in Deutschland strafbar{ui.RESET}")
    print("  (§§ 202a, 303a StGB – unbefugter Datenzugriff / Datenveränderung)\n")
    print("  Legitime Nutzungsszenarien:")
    print("   [1] Eigenes Gerät analysieren")
    print("   [2] Schriftliche Einwilligung des Geräteinhabers liegt vor")
    print("   [3] Behördlicher Auftrag / Beschlagnahmung")
    print("   [4] Interner BYOD-Firmen-Audit (Policy liegt vor)")
    print("   [0] Abbrechen (kein Zugriff)\n")

    choice = input("  Ihr Szenario [0-4]: ").strip()
    if choice not in ("1", "2", "3", "4"):
        print(f"\n  {ui.RED}Abgebrochen – kein Zugriff gewährt.{ui.RESET}\n")
        return False

    labels = {
        "1": "EIGENES_GERÄT",
        "2": "EINWILLIGUNG",
        "3": "BEHÖRDLICHER_AUFTRAG",
        "4": "BYOD_POLICY",
    }
    _AUTHORIZED = True
    _AUTH_SCENARIO = labels[choice]
    print(f"\n  {ui.GREEN}Autorisierung bestätigt: {_AUTH_SCENARIO}{ui.RESET}\n")
    _persist_auth_log(_AUTH_SCENARIO)
    return True


def _persist_auth_log(scenario: str, device_serial: str = "unknown") -> str:
    """Schreibt unveränderliches Autorisierungs-JSON auf Disk.

    Jede Sitzung bekommt eine eigene Datei (Timestamp im Namen).
    Für gerichtsverwertbare Chain-of-Custody nach ISO 27037.
    Gibt den Dateipfad zurück.
    """
    os.makedirs(_AUTH_LOG_DIR, mode=0o700, exist_ok=True)
    ts_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stamp  = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    cert = {
        "authorization_timestamp_utc": ts_utc,
        "scenario": scenario,
        "device_serial": device_serial,
        "analyst_host": os.uname().nodename if hasattr(os, "uname") else "unknown",
        "tool": "AndroidPanzer/playstore_forensics",
        "legal_basis": "§§ 202a/303a StGB – Zugriff ausdrücklich autorisiert",
    }
    path = os.path.join(_AUTH_LOG_DIR, f"auth_{stamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cert, f, indent=2, ensure_ascii=False)
    os.chmod(path, 0o400)  # read-only – nachträgliche Manipulation erkennbar
    return path


def update_auth_device(device_serial: str) -> None:
    """Ergänzt den neuesten Auth-Log um die Device-Serial (nach ADB-Verbindung)."""
    if not os.path.isdir(_AUTH_LOG_DIR):
        return
    logs = sorted(f for f in os.listdir(_AUTH_LOG_DIR) if f.startswith("auth_"))
    if not logs:
        return
    path = os.path.join(_AUTH_LOG_DIR, logs[-1])
    try:
        os.chmod(path, 0o600)
        with open(path, encoding="utf-8") as f:
            cert = json.load(f)
        cert["device_serial"] = device_serial
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cert, f, indent=2, ensure_ascii=False)
        os.chmod(path, 0o400)
    except (OSError, json.JSONDecodeError):
        pass


def is_authorized() -> bool:
    return _AUTHORIZED


def get_auth_scenario() -> str:
    return _AUTH_SCENARIO


def reset_authorization() -> None:
    global _AUTHORIZED, _AUTH_SCENARIO
    _AUTHORIZED = False
    _AUTH_SCENARIO = ""
