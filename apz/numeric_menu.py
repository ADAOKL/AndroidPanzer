"""NUMERIC MAIN MENU: Nur Zahlen - Schnell & Effizient!

Alle Tools nur mit Nummern (1-30). Kein Alphabet, keine Sonderzeichen.
"""
from __future__ import annotations

import unicodedata

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


class NumericMainMenu:
    """Hauptmenü nur mit Zahlen."""

    MENU_ITEMS = [
        # TIER 1: Basis-Analyse (1-5)
        (1, "🔬 TIEFE ANALYSE", "Alle 450 Features", "deep_analysis"),
        (2, "📊 DASHBOARD", "System-Übersicht", "dashboard"),
        (3, "📋 KATEGORIEN", "45 Kategorien detailliert", "categories"),
        (4, "🎨 UI THEME", "Design-Optionen", "theme"),
        (5, "⚙️  EINSTELLUNGEN", "Konfiguration", "settings"),

        # TIER 2: Audio & Video (6-8)
        (6, "🎙️  MICROPHONE TAP", "Audio-Recording + Keywords", "microphone"),
        (7, "📷 CAMERA TAP", "Video & Screenshots", "camera"),
        (8, "🌐 NETWORK ANALYZER", "SIM/WiFi/Cellular", "network"),

        # TIER 3: Forensik & Scanning (9-13)
        (9, "🔍 FORENSIK SUITE", "Umfassende Analyse", "forensics"),
        (10, "📦 APK SCANNER", "Malware & Security", "apk"),
        (11, "🗃️  APP SCANNER", "Tiefe App-Analyse", "apps"),
        (12, "📁 DATEI TREE", "Dateisystem-Explorer", "files"),
        (13, "💾 DATEN FORENSIK", "Datenrettung & Recovery", "dataforensics"),

        # TIER 4: Erweiterte Tools (14-18)
        (14, "🎯 TIEFE ENGINE", "Advanced Feature Explorer", "depth"),
        (15, "🗂️  CASE DATABASE", "Fall-Management", "casedb"),
        (16, "📄 REPORT GENERATOR", "Berichte & Export", "report"),
        (17, "🔄 MODE SWITCH", "ADB Mode Switching", "modeswitch"),
        (18, "🔧 CUSTOM FIRMWARE", "Firmware-Modding", "firmware"),

        # TIER 5: Specials & Advanced (19-24)
        (19, "🌐 ROOTKIT SCANNER", "Kernel-Level Threats", "rootkit"),
        (20, "🚀 ROOTING TOOLS", "Device Rooting", "rooting"),
        (21, "📸 DATA ACQUISITION", "Vollständige Extraktion", "acquisition"),
        (22, "🔓 APP DECRYPTION", "Hashcat-basiert", "decryption"),
        (23, "🔨 BRUTE FORCE", "50 Attack Strategies", "bruteforce"),
        (24, "📡 WIFI HANDSHAKE", "Aircrack-ng Style", "wifi"),

        # TIER 6: Security & Intelligence (25-30)
        (25, "🛡️  DNS GUARDIAN", "Monitor & Filter", "dns"),
        (26, "🎯 TRACKER SYSTEM", "IP/Phone/Geo", "tracker"),
        (27, "🧠 INTELLIGENT ENGINE", "ML/KI/Automation", "intel"),
        (28, "💾 DATABASE SCANNER", "Clone & Archive", "dbscan"),
        (29, "🧪 LAB MANAGER", "venv Labs", "labs"),
        (30, "🌐 3D WIFI SCANNER", "Raumkartographie", "w3d"),

        # TIER 7: NEW ADVANCED (31-36)
        (31, "🔍 ADULT DETECTOR", "Audio+Geruch", "aad"),
        (32, "🔴 ANOMALY DETECTOR", "ROT Pulsierend", "anomaly"),
        (33, "🏥 AI DOCTOR", "Auto-Fix", "doctor"),

        # TIER 8: FORENSIC & SECURITY (34-40)
        (34, "🔬 FORENSIC ANALYZER", "Sexual Activity Detection", "forensic"),
        (35, "🔐 SECURITY FRAMEWORK", "Enterprise Security", "security"),
        (36, "🔑 PASSWORD MANAGER", "Passwort-Verwaltung", "passwords"),
        (37, "🎵 AUDIO PLAYBACK", "Wiedergabe & Analyse", "playback"),
        (38, "🐚 ADB SHELL", "Interactive Shell", "shell"),
        (39, "🔓 AUTO ROOT ENGINE", "Rooting + Data Recovery", "autoroot"),
        (40, "🎤 KEYWORD RECORDER", "Audio mit Keywords", "recorder"),

        # TIER 9: KLASSISCHE TOOLS AUS ALTER VERSION (41-49)
        (41, "🚑 AUTO-RESCUE", "Automatische Rettungs-/Flash-Kaskade", "rescue"),
        (42, "📡 BOOTLOOP-MONITOR", "USB-Zyklen Live-Ueberwachung", "bootloop"),
        (43, "🕵  OSINT-TOOLKIT", "IP/Mail/Username/Domain/KI-Analyst", "osint"),
        (44, "🤖 KI-ADB-SHELL", "Lokale Ollama KI-Shell", "aishell"),
        (45, "📱 SAMSUNG TOOLS", "Root / Odin / TWRP / Flasher", "samsung"),
        (46, "🔶 MEDIATEK ROOT", "mtkclient / BROM-Root", "mediatek"),
        (47, "🏷  HERSTELLER-TOOLS", "Xiaomi / Pixel / OnePlus / Moto / Huawei", "brands"),
        (48, "📶 MOBILFUNK-MONITOR", "Live Zellen- & IMSI-Monitor", "cellmonitor"),
        (49, "🧪 LABOR-EINRICHTUNG", "Alle Forensik-Tools installieren (apt/pip)", "labsetup"),
        (50, "🔬 DEEP-FORENSIK", "Timeline / Geo-Map / Radio-History / gelöschte Daten", "deepforensics"),
        (51, "📞 TELEFON-OSINT", "Carrier-Lookup / Reputation / Social-Media-Suche", "phoneosint"),
        (52, "🔑 GOOGLE-KONTEN",   "Alle angemeldeten Google-Konten + FRP-Schutz scannen", "gaccounts"),
        (53, "📱 KONTO-SCANNER",   "Samsung / Microsoft / Social Media / Streaming-Konten", "accounts"),
        (54, "🔒 FRP-SCANNER",     "Factory Reset Protection – 10 Erkennungsmethoden", "frp"),

        # TIER 10: SIM-TOOLKIT
        (55, "💳 SIM-TOOLKIT",    "35 Kategorien · 350 Features · Alle SIM-Modelle", "simtoolkit"),

        # TIER 11: APP-DOMAIN MONITOR
        (56, "🌐 APP-DOMAIN MONITOR", "Echtzeit DNS · Tracker · Blacklist · App-Traffic", "appdomains"),

        # TIER 12: PLAY STORE FORENSICS
        (57, "🕵️  PLAY STORE FORENSICS", "Install-Historie · Suchverlauf · APK-Scan · Timeline", "psforensics"),

        # TIER 13: NEUE FORENSIK-MODULE
        (58, "🔐 VERSCHLÜSSELUNGS-SCANNER", "Disk-Encryption · TLS-Zertifikate · VPN-Erkennung", "encscanner"),
        (59, "📍 GEO-FORENSIK",             "Location-History · Tower-Triangulation · Reisehistorie", "geoforensics"),
        (60, "🧬 SENSOR-FORENSIK",          "Accelerometer · Barometer · Biometrie · NFC-Log", "sensorforensics"),
    ]

    def __init__(self, adb=None):
        """Initialisiere Numeric Menu."""
        self.adb = adb
        self.handlers = {}

    # TIER-Gruppen: (titel, slice_start, slice_end)
    _TIERS = [
        ("TIER  1 · BASIS-ANALYSE",                  0,  5),
        ("TIER  2 · AUDIO / VIDEO / NETZWERK",        5,  8),
        ("TIER  3 · FORENSIK & SCANNING",             8, 13),
        ("TIER  4 · ERWEITERTE TOOLS",               13, 18),
        ("TIER  5 · SPECIALS & ADVANCED",            18, 24),
        ("TIER  6 · SECURITY & INTELLIGENCE",        24, 30),
        ("TIER  7 · NEW ADVANCED FEATURES",          30, 33),
        ("TIER  8 · FORENSIC & SECURITY ADVANCED",   33, 40),
        ("TIER  9 · KLASSISCHE TOOLS",               40, 54),
        ("TIER 10 · SIM-KARTEN TOOLKIT",             54, 55),
        ("TIER 11 · APP-DOMAIN MONITOR",             55, 56),
        ("TIER 12 · PLAY STORE FORENSICS",           56, 57),
        ("TIER 13 · NEUE FORENSIK-MODULE",           57, None),
    ]

    def show_numeric_menu(self, handler_map: dict) -> str:
        """Zeigt Numeric Menu unterhalb des bereits gesetzten Banners."""
        print()
        for title, start, end in self._TIERS:
            ui.rule(title, ui.CYAN)
            for num, icon, desc, key in self.MENU_ITEMS[start:end]:
                print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {_ljust(icon, 30)}  {ui.GREY}{desc}{ui.RESET}")
            print()

        ui.rule(color=ui.CYAN)
        auto_badge = f"{ui.BGREEN}● AUTO AN{ui.RESET}" if ui.is_auto() else f"{ui.GREY}○ AUTO AUS{ui.RESET}"
        print(f"  {ui.GREY}  0  Zurück / Gerät wechseln     Q  Beenden     A  Auto-Modus [{auto_badge}{ui.GREY}]{ui.RESET}")
        print()

        choice = ui.ask("Auswahl (0-60, Q, A)", "Q").upper()
        return choice

    def get_handler(self, choice: str) -> str:
        """Gibt Handler-Key für Nummer zurück."""
        try:
            num = int(choice)
            for menu_num, _, _, key in self.MENU_ITEMS:
                if menu_num == num:
                    return key
        except ValueError:
            pass
        return None


def create_numeric_menu(adb=None):
    """Factory: Erstellt Numeric Menu."""
    return NumericMainMenu(adb)
