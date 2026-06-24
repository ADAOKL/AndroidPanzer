"""Autorisierungs- und Sicherheitsprüfungen.

Jeder forensischer Zugriff erfordert explizite Bestätigung des Nutzers.
Dieser Check ist kein bürokratischer Umweg – er verhindert, dass das
Tool unbemerkt auf fremden Geräten eingesetzt wird.
"""
from __future__ import annotations

import sys

# Lazy import – ui nicht auf Modulebene laden (vermeidet Circular-Import)
_AUTHORIZED: bool = False


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
    print(f"\n  {ui.GREEN}Autorisierung bestätigt: {labels[choice]}{ui.RESET}\n")
    return True


def is_authorized() -> bool:
    return _AUTHORIZED


def reset_authorization() -> None:
    global _AUTHORIZED
    _AUTHORIZED = False
