"""NUMERIC MAIN MENU: Nur Zahlen - Schnell & Effizient!

Alle Tools nur mit Nummern (1-30). Kein Alphabet, keine Sonderzeichen.
"""
from __future__ import annotations

from . import ui


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
    ]

    def __init__(self, adb=None):
        """Initialisiere Numeric Menu."""
        self.adb = adb
        self.handlers = {}

    def show_numeric_menu(self, handler_map: dict) -> str:
        """Zeigt Numeric Menu und gibt Auswahl zurück."""
        ui.clear()
        ui.banner(subtitle="🔢 ANDROID PANZER - NUMERIC MENU")
        print()

        # Gruppe 1
        print(f"{ui.BGREEN}{'TIER 1: BASIS-ANALYSE':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[0:5]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 2
        print(f"{ui.BCYAN}{'TIER 2: AUDIO & VIDEO & NETZWERK':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[5:8]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 3
        print(f"{ui.BYELLOW}{'TIER 3: FORENSIK & SCANNING':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[8:13]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 4
        print(f"{ui.BMAGENTA}{'TIER 4: ERWEITERTE TOOLS':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[13:18]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 5
        print(f"{ui.BRED}{'TIER 5: SPECIALS & ADVANCED':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[18:24]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 6
        print(f"{ui.BGREEN}{'TIER 6: SECURITY & INTELLIGENCE':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[24:30]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 7
        print(f"{ui.BCYAN}{'TIER 7: NEW ADVANCED FEATURES':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[30:33]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 8
        print(f"{ui.BMAGENTA}{'TIER 8: FORENSIC & SECURITY ADVANCED':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[33:40]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 9
        print(f"{ui.BGREEN}{'TIER 9: KLASSISCHE TOOLS (aus alter Version)':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[40:54]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 10: SIM-Toolkit
        print(f"{ui.BCYAN}{'TIER 10: SIM-KARTEN TOOLKIT':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[54:55]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 11: App-Domain Monitor
        print(f"{ui.BGREEN}{'TIER 11: APP-DOMAIN MONITOR':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[55:56]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        # Gruppe 12: Play Store Forensics
        print(f"{ui.BGREEN}{'TIER 12: PLAY STORE FORENSICS':^80}{ui.RESET}")
        print()
        for num, icon, desc, key in self.MENU_ITEMS[56:]:
            print(f"  {ui.BOLD}{num:2d}{ui.RESET}  {icon:30}  {desc}")
        print()

        print(f"{ui.BGREEN}{'='*80}{ui.RESET}")
        print()
        print("   0  Zurück / Gerät wechseln")
        print("   Q  Beenden")
        print()

        choice = input(f"  {ui.BOLD}☠ ❯ Auswahl (0-57, Q): {ui.RESET}").strip().upper()
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
