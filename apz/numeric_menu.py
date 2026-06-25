"""NUMERIC MAIN MENU: Nur Zahlen - Schnell & Effizient!

Alle Tools nur mit Nummern (1-60). Kein Alphabet, keine Sonderzeichen.
Menü-Einträge und Tier-Struktur werden zur Laufzeit aus MENU_STRUCTURE.json geladen.
Fallback auf eingebettete Hardcode-Werte wenn JSON nicht verfügbar.
"""
from __future__ import annotations

import json as _json
import unicodedata
from pathlib import Path as _Path

from . import ui


def _dispw(s: str) -> int:
    """Visuelle Terminal-Breite eines Strings (Wide-Emoji = 2, VS/Combining = 0)."""
    w = 0
    for c in s:
        cp = ord(c)
        if 0xFE00 <= cp <= 0xFE0F or unicodedata.category(c) in ('Mn', 'Me', 'Cf'):
            continue  # Variation Selectors + Combining: unsichtbar
        eaw = unicodedata.east_asian_width(c)
        if eaw in ('W', 'F') or cp >= 0x1F000:
            w += 2
        else:
            w += 1
    return w


def _ljust(s: str, width: int) -> str:
    """Wie str.ljust(), aber basierend auf visueller Terminal-Breite."""
    return s + ' ' * max(0, width - _dispw(s))


def _load_from_json() -> tuple[list, list] | tuple[None, None]:
    """Lädt MENU_ITEMS und _TIERS aus MENU_STRUCTURE.json (einmalig beim Import)."""
    try:
        path = _Path(__file__).parent.parent / "MENU_STRUCTURE.json"
        with open(path, encoding="utf-8") as f:
            data = _json.load(f)
        items: list = []
        tiers: list = []
        offset = 0
        for tier in data["main_menu"]["tiers"]:
            start = offset
            for item in tier["items"]:
                items.append((
                    item["n"],
                    f"{item['icon']} {item['name']}",
                    item["desc"],
                    str(item["n"]),
                ))
                offset += 1
            tiers.append((f"TIER {tier['tier']:2d} · {tier['title']}", start, offset))
        return items, tiers
    except Exception:
        return None, None


class NumericMainMenu:
    """Hauptmenü nur mit Zahlen."""

    # ── Hardcode-Fallback (aktiv wenn MENU_STRUCTURE.json nicht lesbar) ──────
    MENU_ITEMS = [
        (1,  "🔬 TIEFE ANALYSE",            "Alle 450 Features",                                  "1"),
        (2,  "📊 DASHBOARD",                "System-Übersicht",                                   "2"),
        (3,  "📋 KATEGORIEN",               "45 Kategorien detailliert",                          "3"),
        (4,  "🎨 UI THEME",                 "Design-Optionen",                                    "4"),
        (5,  "⚙️  EINSTELLUNGEN",           "Konfiguration",                                      "5"),
        (6,  "🎙️  MICROPHONE TAP",          "Audio-Recording + Keywords",                         "6"),
        (7,  "📷 CAMERA TAP",               "Video & Screenshots",                                "7"),
        (8,  "🌐 NETWORK ANALYZER",         "SIM/WiFi/Cellular",                                  "8"),
        (9,  "🔍 FORENSIK SUITE",           "Umfassende Analyse",                                 "9"),
        (10, "📦 APK SCANNER",              "Malware & Security",                                 "10"),
        (11, "🗃️  APP SCANNER",             "Tiefe App-Analyse",                                  "11"),
        (12, "📁 DATEI TREE",               "Dateisystem-Explorer",                               "12"),
        (13, "💾 DATEN FORENSIK",           "Datenrettung & Recovery",                            "13"),
        (14, "🎯 TIEFE ENGINE",             "Advanced Feature Explorer",                          "14"),
        (15, "🗂️  CASE DATABASE",           "Fall-Management",                                    "15"),
        (16, "📄 REPORT GENERATOR",         "Berichte & Export",                                  "16"),
        (17, "🔄 MODE SWITCH",              "ADB Mode Switching",                                 "17"),
        (18, "🔧 CUSTOM FIRMWARE",          "Firmware-Modding",                                   "18"),
        (19, "🌐 ROOTKIT SCANNER",          "Kernel-Level Threats",                               "19"),
        (20, "🚀 ROOTING TOOLS",            "Device Rooting",                                     "20"),
        (21, "📸 DATA ACQUISITION",         "Vollständige Extraktion",                            "21"),
        (22, "🔓 APP DECRYPTION",           "Hashcat-basiert",                                    "22"),
        (23, "🔨 BRUTE FORCE",              "50 Attack Strategies",                               "23"),
        (24, "📡 WIFI HANDSHAKE",           "Aircrack-ng Style",                                  "24"),
        (25, "🛡️  DNS GUARDIAN",            "Monitor & Filter",                                   "25"),
        (26, "🎯 TRACKER SYSTEM",           "IP/Phone/Geo",                                       "26"),
        (27, "🧠 INTELLIGENT ENGINE",       "ML/KI/Automation",                                   "27"),
        (28, "💾 DATABASE SCANNER",         "Clone & Archive",                                    "28"),
        (29, "🧪 LAB MANAGER",              "venv Labs",                                          "29"),
        (30, "🌐 3D WIFI SCANNER",          "Raumkartographie",                                   "30"),
        (31, "🔍 ADULT DETECTOR",           "Audio+Geruch",                                       "31"),
        (32, "🔴 ANOMALY DETECTOR",         "ROT Pulsierend",                                     "32"),
        (33, "🏥 AI DOCTOR",                "Auto-Fix",                                           "33"),
        (34, "🔬 FORENSIC ANALYZER",        "Sexual Activity Detection",                          "34"),
        (35, "🔐 SECURITY FRAMEWORK",       "Enterprise Security",                                "35"),
        (36, "🔑 PASSWORD MANAGER",         "Passwort-Verwaltung",                                "36"),
        (37, "🎵 AUDIO PLAYBACK",           "Wiedergabe & Analyse",                               "37"),
        (38, "🐚 ADB SHELL",                "Interactive Shell",                                  "38"),
        (39, "🔓 AUTO ROOT ENGINE",         "Rooting + Data Recovery",                            "39"),
        (40, "🎤 KEYWORD RECORDER",         "Audio mit Keywords",                                 "40"),
        (41, "🚑 AUTO-RESCUE",              "Automatische Rettungs-/Flash-Kaskade",               "41"),
        (42, "📡 BOOTLOOP-MONITOR",         "USB-Zyklen Live-Überwachung",                        "42"),
        (43, "🕵  OSINT-TOOLKIT",           "IP/Mail/Username/Domain/KI-Analyst",                 "43"),
        (44, "🤖 KI-ADB-SHELL",             "Lokale Ollama KI-Shell",                             "44"),
        (45, "📱 SAMSUNG TOOLS",            "Root / Odin / TWRP / Flasher",                       "45"),
        (46, "🔶 MEDIATEK ROOT",            "mtkclient / BROM-Root",                              "46"),
        (47, "🏷  HERSTELLER-TOOLS",        "Xiaomi / Pixel / OnePlus / Moto / Huawei",           "47"),
        (48, "📶 MOBILFUNK-MONITOR",        "Live Zellen- & IMSI-Monitor",                        "48"),
        (49, "🧪 LABOR-EINRICHTUNG",        "Alle Forensik-Tools installieren (apt/pip)",          "49"),
        (50, "🔬 DEEP-FORENSIK",            "Timeline / Geo-Map / Radio-History / gelöschte Daten","50"),
        (51, "📞 TELEFON-OSINT",            "Carrier-Lookup / Reputation / Social-Media-Suche",   "51"),
        (52, "🔑 GOOGLE-KONTEN",            "Alle angemeldeten Google-Konten + FRP-Schutz scannen","52"),
        (53, "📱 KONTO-SCANNER",            "Samsung / Microsoft / Social Media / Streaming-Konten","53"),
        (54, "🔒 FRP-SCANNER",              "Factory Reset Protection – 10 Erkennungsmethoden",   "54"),
        (55, "💳 SIM-TOOLKIT",              "35 Kategorien · 350 Features · Alle SIM-Modelle",    "55"),
        (56, "🌐 APP-DOMAIN MONITOR",       "Echtzeit DNS · Tracker · Blacklist · App-Traffic",   "56"),
        (57, "🕵️  PLAY STORE FORENSICS",    "Install-Historie · Suchverlauf · APK-Scan · Timeline","57"),
        (58, "🔐 VERSCHLÜSSELUNGS-SCANNER", "Disk-Encryption · TLS-Zertifikate · VPN-Erkennung",  "58"),
        (59, "📍 GEO-FORENSIK",             "Location-History · Tower-Triangulation · Reisehistorie","59"),
        (60, "🧬 SENSOR-FORENSIK",          "Accelerometer · Barometer · Biometrie · NFC-Log",    "60"),
        (61, "🔒 BOOTLOADER SPERREN",       "Download-Modus → fastboot lock → Reboot",             "61"),
    ]

    # TIER-Gruppen: (titel, slice_start, slice_end)
    _TIERS = [
        ("TIER  1 · BASIS-ANALYSE",                  0,   5),
        ("TIER  2 · AUDIO / VIDEO / NETZWERK",        5,   8),
        ("TIER  3 · FORENSIK & SCANNING",             8,  13),
        ("TIER  4 · ERWEITERTE TOOLS",               13,  18),
        ("TIER  5 · SPECIALS & ADVANCED",            18,  24),
        ("TIER  6 · SECURITY & INTELLIGENCE",        24,  30),
        ("TIER  7 · NEW ADVANCED FEATURES",          30,  33),
        ("TIER  8 · FORENSIC & SECURITY ADVANCED",   33,  40),
        ("TIER  9 · KLASSISCHE TOOLS",               40,  54),
        ("TIER 10 · SIM-KARTEN TOOLKIT",             54,  55),
        ("TIER 11 · APP-DOMAIN MONITOR",             55,  56),
        ("TIER 12 · PLAY STORE FORENSICS",           56,  57),
        ("TIER 13 · NEUE FORENSIK-MODULE",           57, None),
        ("TIER 14 · DEVICE HARDENING",               60, None),
    ]

    def __init__(self, adb=None):
        self.adb = adb

    def show_numeric_menu(self, handler_map: dict) -> str:
        """Zeigt Numeric Menu unterhalb des bereits gesetzten Banners."""
        print()
        for title, start, end in self._TIERS:
            ui.rule(title, ui.CYAN)
            for num, icon, desc, _ in self.MENU_ITEMS[start:end]:
                print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {_ljust(icon, 30)}  {ui.GREY}{desc}{ui.RESET}")
            print()

        ui.rule(color=ui.CYAN)
        auto_badge = f"{ui.BGREEN}● AUTO AN{ui.RESET}" if ui.is_auto() else f"{ui.GREY}○ AUTO AUS{ui.RESET}"
        print(f"  {ui.GREY}  0  Zurück / Gerät wechseln     Q  Beenden     A  Auto-Modus [{auto_badge}{ui.GREY}]{ui.RESET}")
        print()

        choice = ui.ask("Auswahl (0-61, Q, A)", "Q").upper()
        return choice

    def get_handler(self, choice: str) -> str | None:
        """Gibt den numerischen Key für eine Menünummer zurück."""
        try:
            num = int(choice)
            for menu_num, _, _, key in self.MENU_ITEMS:
                if menu_num == num:
                    return key
        except ValueError:
            pass
        return None


# ── JSON als Source of Truth: bei Erfolg Klassen-Attribute überschreiben ──
_json_items, _json_tiers = _load_from_json()
if _json_items is not None:
    NumericMainMenu.MENU_ITEMS = _json_items
    NumericMainMenu._TIERS     = _json_tiers


def create_numeric_menu(adb=None) -> NumericMainMenu:
    """Factory: Erstellt Numeric Menu."""
    return NumericMainMenu(adb)
