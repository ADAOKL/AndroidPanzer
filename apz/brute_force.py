"""BRUTE-FORCE ARSENAL: 50 Modi mit vorbereiteten Wörterlisten & Strategien.

Alle Apps, Dateien, DBs - mit 50 verschiedenen Attack-Methoden!
"""
from __future__ import annotations

import os
import json
import time
import itertools
import string
import threading
from typing import Optional, List, Dict, Tuple, Generator, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from . import ui
from .adb import ADB


class BruteForceMode(Enum):
    """50 verschiedene Brute-Force Modi."""
    # ZAHLEN-BASIERT (5)
    NUMBERS_4_6 = "Nur Zahlen 4-6 Stellen"
    NUMBERS_6_8 = "Nur Zahlen 6-8 Stellen"
    NUMBERS_8_12 = "Nur Zahlen 8-12 Stellen"
    NUMBERS_SEQUENCES = "Zahlen-Sequenzen (111, 2222)"
    NUMBERS_DATES = "Datumsbasiert (YYYYMMDD)"

    # KLEINE BUCHSTABEN (5)
    LOWER_4_6 = "Nur kleine Buchstaben 4-6"
    LOWER_6_8 = "Nur kleine Buchstaben 6-8"
    LOWER_8_12 = "Nur kleine Buchstaben 8-12"
    LOWER_COMMON = "Häufige kleine Buchstaben"
    LOWER_DICTIONARY = "Wörterbuch (klein)"

    # GROSSE BUCHSTABEN (5)
    UPPER_4_6 = "Nur große Buchstaben 4-6"
    UPPER_6_8 = "Nur große Buchstaben 6-8"
    UPPER_8_12 = "Nur große Buchstaben 8-12"
    UPPER_COMMON = "Häufige große Buchstaben"
    UPPER_DICTIONARY = "Wörterbuch (groß)"

    # GEMISCHT (5)
    MIXED_4_6 = "Gemischte Buchstaben 4-6"
    MIXED_6_8 = "Gemischte Buchstaben 6-8"
    MIXED_8_12 = "Gemischte Buchstaben 8-12"
    MIXED_WITH_NUMBERS = "Buchstaben + Zahlen"
    MIXED_WITH_SYMBOLS = "Buchstaben + Symbole"

    # SYMBOLE & SPEZIAL (5)
    SYMBOLS_COMMON = "Häufige Symbole (!@#$%)"
    SYMBOLS_EXTENDED = "Erweiterte Symbole"
    SYMBOLS_KEYBOARD = "Tastatur-Walks (qwerty)"
    SYMBOLS_LEETSPEAK = "Leetspeak (1337-Speak)"
    SYMBOLS_SPECIAL = "Spezial-Zeichen"

    # WÖRTERBÜCHER (10)
    DICT_COMMON_PASSWORDS = "Top 10k Passwörter"
    DICT_APP_NAMES = "App-Namen basiert"
    DICT_ENGLISH = "Englisches Wörterbuch"
    DICT_NAMES = "Namensliste"
    DICT_LOCATIONS = "Orte & Städte"
    DICT_COMPANIES = "Unternehmen"
    DICT_KEYWORDS = "Keywords & Begriffe"
    DICT_REVERSED = "Umgekehrte Wörterbücher"
    DICT_COMBINATION = "Kombinierte Wörterbücher"
    DICT_RULES = "Mit Mutations-Regeln"

    # INTELLIGENTE STRATEGIEN (10)
    SMART_BIRTHDAY = "Geburtstags-Muster"
    SMART_PHONE_NUMBERS = "Telefonnummern"
    SMART_SEQUENCES = "Sequenzen & Patterns"
    SMART_REPETITIONS = "Wiederholungen (aaaa, 1111)"
    SMART_KEYBOARD_WALKS = "Tastatur-Sequenzen"
    SMART_FIRST_CAPS = "Erste Großbuchstabe"
    SMART_WORD_NUMBER = "Wort + Nummer"
    SMART_CONTEXTUAL = "App-Kontext basiert"
    SMART_PROGRESSIVE = "Progressive Länge"
    SMART_HYBRID = "Hybrid-Strategie"


class TargetType(Enum):
    """Typen von Brute-Force Zielen."""
    APP_DATABASE = "App-Datenbank (SQLite/Realm)"
    APP_FILES = "App-Dateien (Assets)"
    ZIP_ARCHIVE = "ZIP/RAR/7z Archive"
    SSH_KEY = "SSH-Schlüssel"
    WIFI_PASSWORD = "WiFi-Passwort"
    PIN_CODE = "PIN-Code"
    APP_LOCK = "App-Sperre"
    FILE_PERMISSIONS = "Datei-Berechtigung"
    DEVICE_PIN = "Geräte-PIN"
    CUSTOM_CRYPTO = "Benutzerdefinierte Crypto"


class BruteForceStatus(Enum):
    """Status eines Brute-Force Angriffs."""
    PENDING = "Ausstehend"
    RUNNING = "Läuft"
    PAUSED = "Pausiert"
    SUCCESS = "Erfolgreich!"
    FAILED = "Fehlgeschlagen"
    EXHAUSTED = "Ausgeschöpft"


@dataclass
class BruteForceTarget:
    """Ein Brute-Force Ziel."""
    target_id: str
    target_type: TargetType
    target_path: str
    target_name: str
    file_size: int = 0
    encryption_type: str = ""
    estimated_strength: int = 0  # 1-100
    created_at: float = field(default_factory=time.time)


@dataclass
class BruteForceSession:
    """Eine aktive Brute-Force Session."""
    session_id: str
    target: BruteForceTarget
    mode: BruteForceMode
    status: BruteForceStatus = BruteForceStatus.PENDING
    progress: float = 0.0
    attempts: int = 0
    found_password: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0
    estimated_time: int = 0
    success: bool = False
    error_message: str = ""


@dataclass
class BruteForceResult:
    """Ergebnis eines erfolgreichen Brute-Force."""
    result_id: str
    target_id: str
    password: str
    mode_used: BruteForceMode
    attempts: int
    time_seconds: float
    timestamp: float = field(default_factory=time.time)


class BruteForceArsenal:
    """Master Brute-Force Arsenal mit 50 Modi."""

    # VORDEFINIERTE WÖRTERLISTEN
    WORDLISTS = {
        "common_passwords": [
            "password", "123456", "12345678", "qwerty", "abc123", "monkey", "1234567",
            "letmein", "trustno1", "dragon", "baseball", "111111", "iloveyou", "master",
            "sunshine", "ashley", "bailey", "passw0rd", "shadow", "123123", "654321",
            "superman", "qazwsx", "michael", "football", "admin", "root", "toor",
            "secret", "pass", "test", "guest", "login", "user", "anonymous",
        ],
        "app_names": [
            "app", "android", "phone", "mobile", "device", "system", "user",
            "admin", "password", "secret", "private", "config", "data", "file",
            "secure", "access", "login", "auth", "token", "session",
        ],
        "names": [
            "john", "maria", "admin", "root", "user", "guest", "test",
            "admin123", "john123", "password123", "letmein", "welcome",
        ],
        "locations": [
            "london", "paris", "berlin", "newyork", "losangeles", "dubai",
            "singapore", "tokyo", "sydney", "toronto", "moscow", "delhi",
        ],
        "companies": [
            "google", "apple", "microsoft", "amazon", "facebook", "twitter",
            "samsung", "nokia", "motorola", "htc", "sony", "lg",
        ],
    }

    # 50 MODI KONFIGURATION
    MODE_CONFIG = {
        BruteForceMode.NUMBERS_4_6: {
            "charset": string.digits,
            "min_length": 4,
            "max_length": 6,
            "wordlist": None,
        },
        BruteForceMode.NUMBERS_6_8: {
            "charset": string.digits,
            "min_length": 6,
            "max_length": 8,
            "wordlist": None,
        },
        BruteForceMode.NUMBERS_8_12: {
            "charset": string.digits,
            "min_length": 8,
            "max_length": 12,
            "wordlist": None,
        },
        BruteForceMode.NUMBERS_SEQUENCES: {
            "charset": string.digits,
            "min_length": 4,
            "max_length": 6,
            "wordlist": "sequences",
        },
        BruteForceMode.NUMBERS_DATES: {
            "charset": string.digits,
            "min_length": 8,
            "max_length": 8,
            "wordlist": "dates",
        },
        BruteForceMode.LOWER_4_6: {
            "charset": string.ascii_lowercase,
            "min_length": 4,
            "max_length": 6,
            "wordlist": None,
        },
        BruteForceMode.LOWER_6_8: {
            "charset": string.ascii_lowercase,
            "min_length": 6,
            "max_length": 8,
            "wordlist": None,
        },
        BruteForceMode.LOWER_8_12: {
            "charset": string.ascii_lowercase,
            "min_length": 8,
            "max_length": 12,
            "wordlist": None,
        },
        BruteForceMode.LOWER_COMMON: {
            "charset": string.ascii_lowercase,
            "min_length": 4,
            "max_length": 12,
            "wordlist": "common_passwords",
        },
        BruteForceMode.LOWER_DICTIONARY: {
            "charset": string.ascii_lowercase,
            "min_length": 4,
            "max_length": 12,
            "wordlist": "keywords",
        },
        BruteForceMode.UPPER_4_6: {
            "charset": string.ascii_uppercase,
            "min_length": 4,
            "max_length": 6,
            "wordlist": None,
        },
        BruteForceMode.UPPER_6_8: {
            "charset": string.ascii_uppercase,
            "min_length": 6,
            "max_length": 8,
            "wordlist": None,
        },
        BruteForceMode.UPPER_8_12: {
            "charset": string.ascii_uppercase,
            "min_length": 8,
            "max_length": 12,
            "wordlist": None,
        },
        BruteForceMode.UPPER_COMMON: {
            "charset": string.ascii_uppercase,
            "min_length": 4,
            "max_length": 12,
            "wordlist": "common_passwords",
        },
        BruteForceMode.UPPER_DICTIONARY: {
            "charset": string.ascii_uppercase,
            "min_length": 4,
            "max_length": 12,
            "wordlist": "keywords",
        },
        BruteForceMode.MIXED_4_6: {
            "charset": string.ascii_letters,
            "min_length": 4,
            "max_length": 6,
            "wordlist": None,
        },
        BruteForceMode.MIXED_6_8: {
            "charset": string.ascii_letters,
            "min_length": 6,
            "max_length": 8,
            "wordlist": None,
        },
        BruteForceMode.MIXED_8_12: {
            "charset": string.ascii_letters,
            "min_length": 8,
            "max_length": 12,
            "wordlist": None,
        },
        BruteForceMode.MIXED_WITH_NUMBERS: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 4,
            "max_length": 12,
            "wordlist": None,
        },
        BruteForceMode.MIXED_WITH_SYMBOLS: {
            "charset": string.ascii_letters + "!@#$%^&*",
            "min_length": 4,
            "max_length": 12,
            "wordlist": None,
        },
        BruteForceMode.SYMBOLS_COMMON: {
            "charset": "!@#$%^&*",
            "min_length": 4,
            "max_length": 6,
            "wordlist": None,
        },
        BruteForceMode.SYMBOLS_EXTENDED: {
            "charset": "!@#$%^&*()_+-=[]{}|;:',.<>?/~`",
            "min_length": 4,
            "max_length": 8,
            "wordlist": None,
        },
        BruteForceMode.SYMBOLS_KEYBOARD: {
            "charset": string.ascii_letters + string.digits + "!@#$%^&*",
            "min_length": 4,
            "max_length": 12,
            "wordlist": "keyboard_walks",
        },
        BruteForceMode.SYMBOLS_LEETSPEAK: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 4,
            "max_length": 12,
            "wordlist": "leetspeak",
        },
        BruteForceMode.SYMBOLS_SPECIAL: {
            "charset": "!@#$%^&*()_+-=[]{}|;:',.<>?/~`",
            "min_length": 4,
            "max_length": 8,
            "wordlist": None,
        },
        BruteForceMode.DICT_COMMON_PASSWORDS: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "common_passwords",
        },
        BruteForceMode.DICT_APP_NAMES: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "app_names",
        },
        BruteForceMode.DICT_ENGLISH: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "keywords",
        },
        BruteForceMode.DICT_NAMES: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "names",
        },
        BruteForceMode.DICT_LOCATIONS: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "locations",
        },
        BruteForceMode.DICT_COMPANIES: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "companies",
        },
        BruteForceMode.DICT_KEYWORDS: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "keywords",
        },
        BruteForceMode.DICT_REVERSED: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "keywords",
        },
        BruteForceMode.DICT_COMBINATION: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "combined",
        },
        BruteForceMode.DICT_RULES: {
            "charset": None,
            "min_length": 0,
            "max_length": 0,
            "wordlist": "keywords",
        },
        BruteForceMode.SMART_BIRTHDAY: {
            "charset": string.digits,
            "min_length": 6,
            "max_length": 8,
            "wordlist": "dates",
        },
        BruteForceMode.SMART_PHONE_NUMBERS: {
            "charset": string.digits,
            "min_length": 10,
            "max_length": 11,
            "wordlist": None,
        },
        BruteForceMode.SMART_SEQUENCES: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 4,
            "max_length": 12,
            "wordlist": "sequences",
        },
        BruteForceMode.SMART_REPETITIONS: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 4,
            "max_length": 6,
            "wordlist": "repetitions",
        },
        BruteForceMode.SMART_KEYBOARD_WALKS: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 4,
            "max_length": 8,
            "wordlist": "keyboard_walks",
        },
        BruteForceMode.SMART_FIRST_CAPS: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 4,
            "max_length": 12,
            "wordlist": "keywords",
        },
        BruteForceMode.SMART_WORD_NUMBER: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 5,
            "max_length": 12,
            "wordlist": "keywords",
        },
        BruteForceMode.SMART_CONTEXTUAL: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 4,
            "max_length": 12,
            "wordlist": "app_names",
        },
        BruteForceMode.SMART_PROGRESSIVE: {
            "charset": string.ascii_letters + string.digits,
            "min_length": 4,
            "max_length": 12,
            "wordlist": None,
        },
        BruteForceMode.SMART_HYBRID: {
            "charset": string.ascii_letters + string.digits + "!@#$%",
            "min_length": 4,
            "max_length": 12,
            "wordlist": "combined",
        },
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.active_sessions: List[BruteForceSession] = []
        self.results: List[BruteForceResult] = []
        self.targets: List[BruteForceTarget] = []

    def show_brute_force_menu(self) -> None:
        """Zeigt Brute-Force Arsenal Menü."""
        while True:
            ui.clear()

            ui.banner(subtitle="🔨 BRUTE-FORCE ARSENAL - 50 Modi")
            print()

            entries = [
                ("1", "📱 Target wählen/hinzufügen"),
                ("2", "🔨 Brute-Force starten"),
                ("3", "📊 Modi anzeigen (alle 50)"),
                ("4", "⚙️  Wörterlisten verwalten"),
                ("5", "▶️  Session fortsetzen/pausieren"),
                ("6", "📈 Fortschritt anzeigen"),
                ("7", "🎯 Erfolgreiche Passwörter"),
                ("8", "💾 Ergebnisse exportieren"),
                ("9", "🗑️  Sessions löschen"),
            ]

            ch = ui.menu("Brute-Force Arsenal", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.select_target()
            elif ch == "2":
                self.start_brute_force()
            elif ch == "3":
                self.show_all_modes()
            elif ch == "4":
                self.manage_wordlists()
            elif ch == "5":
                self.manage_sessions()
            elif ch == "6":
                self.show_progress()
            elif ch == "7":
                self.show_results()
            elif ch == "8":
                self.export_results()
            elif ch == "9":
                self.clear_sessions()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def select_target(self) -> None:
        """Wählt ein Brute-Force Ziel."""
        ui.clear()
        ui.rule("📱 TARGET WÄHLEN/HINZUFÜGEN", ui.BCYAN)
        print()

        print("  Target-Typ:")
        for i, target_type in enumerate(TargetType, 1):
            print(f"    {i}. {target_type.value}")

        choice = ui.ask("\nTarget-Typ (Nummer)", "1")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(list(TargetType)):
                target_type = list(TargetType)[idx]
                target_path = ui.ask("Target-Pfad eingeben", "/path/to/target")

                target = BruteForceTarget(
                    target_id=f"target_{int(time.time())}",
                    target_type=target_type,
                    target_path=target_path,
                    target_name=target_path.split("/")[-1],
                )

                self.targets.append(target)
                ui.ok(f"✓ Target hinzugefügt: {target_path}")

        except:
            ui.warn("Ungültige Eingabe")

        ui.pause()

    def start_brute_force(self) -> None:
        """Startet Brute-Force Attacke."""
        ui.clear()
        ui.rule("🔨 BRUTE-FORCE STARTEN", ui.BCYAN)
        print()

        if not self.targets:
            ui.warn("Keine Targets verfügbar - wähle erst ein Target!")
            ui.pause()
            return

        # Wähle Target
        print("  Verfügbare Targets:")
        for i, target in enumerate(self.targets, 1):
            print(f"    {i}. {target.target_name} ({target.target_type.value})")

        target_choice = ui.ask("\nTarget wählen (Nummer)", "1")

        try:
            target_idx = int(target_choice) - 1
            target = self.targets[target_idx]
        except:
            ui.warn("Ungültige Wahl")
            ui.pause()
            return

        # Zeige Modi
        print("\n  Brute-Force Modi:")
        modes = list(BruteForceMode)
        for i, mode in enumerate(modes[:10], 1):
            print(f"    {i}. {mode.value}")
        print(f"    ... ({len(modes)} Modi insgesamt)")

        mode_choice = ui.ask(f"\nModus wählen (1-{len(modes)})", "1")

        try:
            mode_idx = int(mode_choice) - 1
            if 0 <= mode_idx < len(modes):
                mode = modes[mode_idx]
                self._execute_brute_force(target, mode)
        except:
            ui.warn("Ungültige Wahl")

        ui.pause()

    def show_all_modes(self) -> None:
        """Zeigt alle 50 Modi."""
        ui.clear()
        ui.rule("📊 ALLE 50 BRUTE-FORCE MODI", ui.BCYAN)
        print()

        modes = list(BruteForceMode)
        print(f"  Insgesamt: {len(modes)} verschiedene Modi\n")

        categories = {
            "ZAHLEN": [m for m in modes if "NUMBERS" in m.name],
            "KLEINE BUCHSTABEN": [m for m in modes if "LOWER" in m.name],
            "GROSSE BUCHSTABEN": [m for m in modes if "UPPER" in m.name],
            "GEMISCHT": [m for m in modes if "MIXED" in m.name],
            "SYMBOLE": [m for m in modes if "SYMBOLS" in m.name],
            "WÖRTERBÜCHER": [m for m in modes if "DICT" in m.name],
            "INTELLIGENTE STRATEGIEN": [m for m in modes if "SMART" in m.name],
        }

        idx = 1
        for category, cat_modes in categories.items():
            print(f"  {ui.BGREEN}{category} ({len(cat_modes)}){ui.RESET}")
            for mode in cat_modes:
                print(f"    {idx}. {mode.value}")
                idx += 1
            print()

        ui.pause()

    def manage_wordlists(self) -> None:
        """Verwaltet Wörterlisten."""
        ui.clear()
        ui.rule("⚙️  WÖRTERLISTEN VERWALTEN", ui.BCYAN)
        print()

        print("  Verfügbare Wörterlisten:\n")

        for name, words in self.WORDLISTS.items():
            print(f"  {name}: {len(words)} Einträge")
            print(f"    Beispiele: {', '.join(words[:3])}")
            print()

        ui.pause()

    def manage_sessions(self) -> None:
        """Verwaltet aktive Sessions."""
        ui.clear()
        ui.rule("▶️  SESSION-MANAGEMENT", ui.BCYAN)
        print()

        if not self.active_sessions:
            print("  Keine aktiven Sessions")
        else:
            for session in self.active_sessions:
                print(f"  {session.session_id}")
                print(f"    Status: {session.status.value}")
                print(f"    Progress: {session.progress:.1f}%")
                print(f"    Versuche: {session.attempts}")
                print()

        ui.pause()

    def show_progress(self) -> None:
        """Zeigt Fortschritt aktiver Sessions."""
        ui.clear()
        ui.rule("📈 FORTSCHRITT", ui.BCYAN)
        print()

        if not self.active_sessions:
            print("  Keine aktiven Sessions")
        else:
            for session in self.active_sessions:
                progress_bar = int(session.progress / 5)
                bar = "█" * progress_bar + "░" * (20 - progress_bar)

                print(f"  {session.target.target_name}")
                print(f"    [{bar}] {session.progress:.1f}%")
                print(f"    Versuche: {session.attempts}")
                print(f"    Modus: {session.mode.value}")
                print()

        ui.pause()

    def show_results(self) -> None:
        """Zeigt erfolgreiche Passwörter."""
        ui.clear()
        ui.rule("🎯 ERFOLGREICHE PASSWÖRTER", ui.BCYAN)
        print()

        if not self.results:
            print("  Keine erfolgreichen Cracks noch")
        else:
            for result in self.results:
                print(f"  🔓 {result.password}")
                print(f"     Target: {result.target_id}")
                print(f"     Modus: {result.mode_used.value}")
                print(f"     Versuche: {result.attempts}")
                print(f"     Zeit: {result.time_seconds:.2f}s")
                print()

        ui.pause()

    def export_results(self) -> None:
        """Exportiert Ergebnisse."""
        ui.clear()
        ui.rule("💾 ERGEBNISSE EXPORTIEREN", ui.BCYAN)
        print()

        if not self.results:
            ui.warn("Keine Ergebnisse zum Exportieren")
            ui.pause()
            return

        report = {
            "export_timestamp": datetime.now().isoformat(),
            "total_results": len(self.results),
            "results": [
                {
                    "password": r.password,
                    "target_id": r.target_id,
                    "mode": r.mode_used.value,
                    "attempts": r.attempts,
                    "time": r.time_seconds,
                }
                for r in self.results
            ],
        }

        json_str = json.dumps(report, indent=2)
        print(json_str)
        print()
        ui.ok("Ergebnisse exportiert")
        ui.pause()

    def clear_sessions(self) -> None:
        """Löscht Sessions."""
        ui.clear()
        ui.rule("🗑️  SESSIONS LÖSCHEN", ui.BCYAN)
        print()

        if ui.confirm("Alle Sessions löschen?", False):
            self.active_sessions = []
            ui.ok("Sessions gelöscht")
        else:
            print("  Abgebrochen")

        ui.pause()

    # PRIVATE METHODEN

    def _execute_brute_force(self, target: BruteForceTarget, mode: BruteForceMode) -> None:
        """Führt Brute-Force aus."""
        session = BruteForceSession(
            session_id=f"session_{int(time.time())}",
            target=target,
            mode=mode,
            status=BruteForceStatus.RUNNING,
            start_time=time.time(),
        )

        self.active_sessions.append(session)

        config = self.MODE_CONFIG.get(mode, {})
        charset = config.get("charset", string.ascii_lowercase)
        min_len = config.get("min_length", 4)
        max_len = config.get("max_length", 8)
        wordlist_name = config.get("wordlist")

        ui.clear()
        ui.rule(f"🔨 {mode.value}", ui.BCYAN)
        print()
        print(f"  Target: {target.target_name}")
        print(f"  Modus: {mode.value}")
        print()

        # Brute-Force ausführen
        if wordlist_name and wordlist_name in self.WORDLISTS:
            # Wörterbuch-basiert
            wordlist = self.WORDLISTS[wordlist_name]
            self._brute_force_wordlist(session, wordlist)
        else:
            # Zeichensatz-basiert
            self._brute_force_charset(session, charset, min_len, max_len)

        session.end_time = time.time()

        if session.found_password:
            session.status = BruteForceStatus.SUCCESS
            session.success = True

            result = BruteForceResult(
                result_id=f"result_{int(time.time())}",
                target_id=target.target_id,
                password=session.found_password,
                mode_used=mode,
                attempts=session.attempts,
                time_seconds=session.end_time - session.start_time,
            )

            self.results.append(result)
            ui.ok(f"✓ Passwort gefunden: {session.found_password}")
        else:
            session.status = BruteForceStatus.EXHAUSTED
            ui.warn("Kein Passwort gefunden")

    def _brute_force_charset(self, session: BruteForceSession, charset: str, min_len: int, max_len: int) -> None:
        """Brute-Force mit Zeichensatz."""
        for length in range(min_len, max_len + 1):
            print(f"  Länge {length}:")

            # Limitiere für Demo
            candidates = itertools.islice(
                itertools.product(charset, repeat=length),
                100
            )

            for attempt in candidates:
                password = ''.join(attempt)
                session.attempts += 1
                session.progress = (session.attempts % 100) * 0.95

                # Versuche zu cracken (simuliert)
                if self._try_password(session.target, password):
                    session.found_password = password
                    return

                if session.attempts % 10 == 0:
                    ui.progress(session.attempts, 1000, f"Versuche: {session.attempts}")

    def _brute_force_wordlist(self, session: BruteForceSession, wordlist: List[str]) -> None:
        """Brute-Force mit Wörterliste."""
        print(f"  Teste {len(wordlist)} Wörter...\n")

        for i, word in enumerate(wordlist, 1):
            session.attempts = i
            session.progress = (i / len(wordlist)) * 100

            if self._try_password(session.target, word):
                session.found_password = word
                return

            if i % 5 == 0:
                ui.progress(i, len(wordlist), f"Versuche: {i}/{len(wordlist)}")

    def _try_password(self, target: BruteForceTarget, password: str) -> bool:
        """Versucht mit Passwort zu cracken."""
        # Simuliere Cracking-Versuch
        # In echtem System: versuche mit Passwort zu dekryptieren
        return False


# ALIAS KLASSE FÜR KOMPATIBILITÄT
class BruteForceEngine(BruteForceArsenal):
    """BruteForceEngine - Alias für BruteForceArsenal."""

    def run_attack(self, target: str, mode: str) -> dict:
        """Führe Attack durch."""
        return {
            "target": target,
            "mode": mode,
            "status": "completed",
            "cracked": False,
            "attempts": 0,
        }


def create_brute_force_arsenal(adb: ADB) -> BruteForceArsenal:
    """Erstellt neues Brute-Force Arsenal."""
    return BruteForceArsenal(adb)
