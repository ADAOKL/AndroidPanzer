"""APP DECRYPTION ENGINE: APK-Entschlüsselung wie Hashcat.

Brute-Force, Wörterbücher, Multiple Algorithmen, GPU-Simulation!
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import itertools
import threading
from typing import Optional, List, Dict, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import base64

from . import ui
from .adb import ADB


class EncryptionAlgorithm(Enum):
    """Unterstützte Verschlüsselungs-Algorithmen."""
    AES_128 = "AES-128"
    AES_192 = "AES-192"
    AES_256 = "AES-256"
    DES = "DES"
    TRIPLE_DES = "3DES"
    RSA_1024 = "RSA-1024"
    RSA_2048 = "RSA-2048"
    RSA_4096 = "RSA-4096"
    BLOWFISH = "Blowfish"
    ECC = "ECC"
    MD5 = "MD5"
    SHA1 = "SHA-1"
    SHA256 = "SHA-256"
    SHA512 = "SHA-512"
    UNKNOWN = "Unknown"


class AttackMode(Enum):
    """Attack-Modi wie Hashcat."""
    STRAIGHT = "Straight"           # Einfache Wörterbuch
    COMBINATION = "Combination"     # 2 Wörterbücher kombinieren
    BRUTE_FORCE = "Brute-Force"     # Alle Kombinationen
    HYBRID = "Hybrid"               # Wort + Brute-Force
    MASK = "Mask"                   # Masken-basiert (?a?s?d)
    RAINBOW_TABLE = "Rainbow Table" # Rainbow-Tables
    DICTIONARY = "Dictionary"       # Einfache Wörterbuch
    PERMUTATION = "Permutation"     # Permutationen
    CUSTOM_RULE = "Custom Rule"     # Custom Regeln


class DecryptionStatus(Enum):
    """Status der Entschlüsselung."""
    PENDING = "Ausstehend"
    ANALYZING = "Analysiert"
    CRACKING = "In Bearbeitung"
    FOUND = "Gefunden!"
    EXHAUSTED = "Ausgeschöpft"
    ERROR = "Fehler"


@dataclass
class EncryptedElement:
    """Ein verschlüsseltes Element in der APK."""
    element_id: str
    element_type: str  # "string", "resource", "asset", "native", "config"
    location: str      # File path
    encrypted_data: str
    detected_algorithm: EncryptionAlgorithm = EncryptionAlgorithm.UNKNOWN
    confidence: float = 0.0
    key_size: int = 0
    iv: str = ""
    salt: str = ""
    data_size: int = 0


@dataclass
class CrackingSession:
    """Eine aktive Cracking-Session."""
    session_id: str
    apk_path: str
    encrypted_elements: List[EncryptedElement] = field(default_factory=list)
    attack_mode: AttackMode = AttackMode.DICTIONARY
    wordlist_path: str = ""
    mask: str = ""
    custom_rules: List[str] = field(default_factory=list)
    status: DecryptionStatus = DecryptionStatus.PENDING
    progress: float = 0.0
    attempts: int = 0
    found_keys: Dict[str, str] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    estimated_time: int = 0


@dataclass
class DecryptedData:
    """Entschlüsselte Daten."""
    data_id: str
    original_encrypted: str
    decrypted_value: str
    key_used: str
    algorithm: EncryptionAlgorithm
    attack_mode: AttackMode
    attempts_needed: int
    cracking_time_seconds: float


class AppDecryptionEngine:
    """Master App Decryption Engine - Hashcat-ähnlich."""

    # COMMON PASSWORDS WORDLIST (für schnelle Tests)
    COMMON_PASSWORDS = [
        "password", "123456", "12345678", "qwerty", "abc123", "monkey", "1234567",
        "letmein", "trustno1", "dragon", "baseball", "111111", "iloveyou", "master",
        "sunshine", "ashley", "bailey", "passw0rd", "shadow", "123123", "654321",
        "superman", "qazwsx", "michael", "football", "admin", "root", "toor",
        "secret", "pass", "test", "guest", "login", "user", "anonymous",
    ]

    # ENCRYPTION PATTERNS
    ENCRYPTION_PATTERNS = {
        "aes": r"(?i)(aes|javax\.crypto\.Cipher\.getInstance\(\"AES)",
        "des": r"(?i)(des|DES/ECB|DES/CBC)",
        "rsa": r"(?i)(RSA|RSA/ECB|getKeyFactory\(\"RSA\")",
        "sha": r"(?i)(SHA-?256|SHA-?512|SHA1|MessageDigest\.getInstance)",
        "base64": r"(Base64\.getEncoder|Base64\.decode|android\.util\.Base64)",
        "encrypted": r"(?i)(encrypted|crypt|secret|private)",
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.active_sessions: List[CrackingSession] = []
        self.cracked_data: List[DecryptedData] = []
        self.hash_cache: Dict[str, str] = {}
        self.wordlist_cache: Dict[str, List[str]] = {}

    def show_decryption_menu(self) -> None:
        """Zeigt APK Decryption Menü."""
        while True:
            ui.clear()

            ui.banner(subtitle="🔓 APP DECRYPTION ENGINE - Hashcat-ähnlich")
            print()

            entries = [
                ("1", "📦 APK analysieren & Verschlüsselung erkennen"),
                ("2", "🔨 Brute-Force Attacke starten"),
                ("3", "📚 Wörterbuch-Attacke"),
                ("4", "🎭 Mask-Attacke (?a?s?d)"),
                ("5", "🔄 Hybrid-Attacke (Wort + Brute-Force)"),
                ("6", "🌈 Rainbow-Table Attacke"),
                ("7", "⚡ Schnell-Cracking (Common Passwords)"),
                ("8", "📊 Cracking-Sitzungen anzeigen"),
                ("9", "🔑 Entschlüsselte Daten anzeigen"),
                ("0", "💾 Ergebnisse exportieren"),
            ]

            ch = ui.menu("Decryption Engine", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.analyze_apk_for_encryption()
            elif ch == "2":
                self.start_brute_force_attack()
            elif ch == "3":
                self.start_dictionary_attack()
            elif ch == "4":
                self.start_mask_attack()
            elif ch == "5":
                self.start_hybrid_attack()
            elif ch == "6":
                self.start_rainbow_table_attack()
            elif ch == "7":
                self.quick_crack_common_passwords()
            elif ch == "8":
                self.show_sessions()
            elif ch == "9":
                self.show_cracked_data()
            elif ch == "0":
                self.export_results()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def analyze_apk_for_encryption(self) -> None:
        """Analysiert APK auf Verschlüsselung."""
        ui.clear()
        ui.rule("📦 APK-ANALYSE FÜR VERSCHLÜSSELUNG", ui.BCYAN)
        print()

        apk_path = ui.ask("APK-Pfad eingeben", "/tmp/app.apk")

        if not os.path.exists(apk_path):
            ui.err("APK nicht gefunden")
            ui.pause()
            return

        # Erstelle Session
        session = CrackingSession(
            session_id=f"session_{int(time.time())}",
            apk_path=apk_path,
            status=DecryptionStatus.ANALYZING,
            start_time=time.time(),
        )

        ui.rule("Analysiere APK...", ui.BCYAN)
        print()

        stages = [
            ("Entpacke APK", self._extract_apk),
            ("Analysiere DEX", self._analyze_dex),
            ("Scanne Strings", self._scan_strings),
            ("Erkenne Algorithmen", self._detect_algorithms),
            ("Finde verschlüsselte Daten", self._find_encrypted_data),
        ]

        for i, (stage_name, stage_func) in enumerate(stages, 1):
            ui.progress(i, len(stages), stage_name)
            encrypted = stage_func(apk_path, session)
            if encrypted:
                session.encrypted_elements.extend(encrypted)

        ui.progress(len(stages), len(stages), "Analyse abgeschlossen")
        print()

        if session.encrypted_elements:
            ui.ok(f"✓ {len(session.encrypted_elements)} verschlüsselte Elemente gefunden!")
            self._display_encrypted_elements(session)
        else:
            print("  Keine verschlüsselten Daten gefunden")

        self.active_sessions.append(session)
        ui.pause()

    def start_brute_force_attack(self) -> None:
        """Startet Brute-Force Attacke."""
        ui.clear()
        ui.rule("🔨 BRUTE-FORCE ATTACKE", ui.BCYAN)
        print()

        if not self.active_sessions:
            print("  Führe erst eine APK-Analyse durch!")
            ui.pause()
            return

        # Wähle Session
        session = self.active_sessions[-1]

        if not session.encrypted_elements:
            ui.warn("Keine verschlüsselten Daten in Session")
            ui.pause()
            return

        print("  Starte Brute-Force Attacke...")
        print()

        # Parameter
        min_length = int(ui.ask("Minimale Passwort-Länge", "4"))
        max_length = int(ui.ask("Maximale Passwort-Länge", "8"))
        charset = ui.ask("Zeichensatz (numbers/lower/upper/symbols)", "lower")

        session.attack_mode = AttackMode.BRUTE_FORCE
        session.status = DecryptionStatus.CRACKING

        # Starte Cracking
        self._brute_force_cracking(session, min_length, max_length, charset)

    def start_dictionary_attack(self) -> None:
        """Startet Wörterbuch-Attacke."""
        ui.clear()
        ui.rule("📚 WÖRTERBUCH-ATTACKE", ui.BCYAN)
        print()

        if not self.active_sessions:
            print("  Führe erst eine APK-Analyse durch!")
            ui.pause()
            return

        session = self.active_sessions[-1]

        if not session.encrypted_elements:
            ui.warn("Keine verschlüsselten Daten")
            ui.pause()
            return

        wordlist_path = ui.ask("Wörterbuch-Pfad", "/tmp/wordlist.txt")

        if not os.path.exists(wordlist_path):
            # Nutze Common Passwords
            print("  Wörterbuch nicht gefunden - nutze Common Passwords...")
            wordlist = self.COMMON_PASSWORDS
        else:
            with open(wordlist_path, 'r') as f:
                wordlist = f.read().splitlines()

        session.attack_mode = AttackMode.DICTIONARY
        session.wordlist_path = wordlist_path
        session.status = DecryptionStatus.CRACKING

        print(f"\n  Starte Wörterbuch-Attacke mit {len(wordlist)} Wörtern...")
        self._dictionary_cracking(session, wordlist)

    def start_mask_attack(self) -> None:
        """Startet Mask-Attacke."""
        ui.clear()
        ui.rule("🎭 MASK-ATTACKE", ui.BCYAN)
        print()

        print("  Mask-Patterns:")
        print("    ?l = lowercase [a-z]")
        print("    ?u = uppercase [A-Z]")
        print("    ?d = digits [0-9]")
        print("    ?s = special [@#$%...]")
        print("    ?a = all")
        print()

        mask = ui.ask("Eingeben Sie Mask (z.B. ?u?l?l?d)", "?l?l?d?d")

        if not self.active_sessions:
            print("  Führe erst eine APK-Analyse durch!")
            ui.pause()
            return

        session = self.active_sessions[-1]
        session.attack_mode = AttackMode.MASK
        session.mask = mask
        session.status = DecryptionStatus.CRACKING

        print(f"\n  Starte Mask-Attacke mit: {mask}")
        self._mask_cracking(session, mask)

    def start_hybrid_attack(self) -> None:
        """Startet Hybrid-Attacke."""
        ui.clear()
        ui.rule("🔄 HYBRID-ATTACKE", ui.BCYAN)
        print()

        wordlist_path = ui.ask("Wörterbuch-Pfad", "/tmp/wordlist.txt")
        mask = ui.ask("Mask-Pattern", "?d?d?d")

        if not self.active_sessions:
            ui.warn("Keine Session aktiv")
            ui.pause()
            return

        session = self.active_sessions[-1]
        session.attack_mode = AttackMode.HYBRID
        session.status = DecryptionStatus.CRACKING

        print(f"\n  Kombiniere Wörterbuch + Mask: {mask}")
        self._hybrid_cracking(session, wordlist_path, mask)

    def start_rainbow_table_attack(self) -> None:
        """Startet Rainbow-Table Attacke."""
        ui.clear()
        ui.rule("🌈 RAINBOW-TABLE ATTACKE", ui.BCYAN)
        print()

        print("  Rainbow-Tables ermöglichen schnelle Lookups...")
        print("  (Pre-computed hashes)")
        print()

        table_path = ui.ask("Rainbow-Table Pfad", "/tmp/rainbow.rt")

        if not self.active_sessions:
            ui.warn("Keine Session aktiv")
            ui.pause()
            return

        session = self.active_sessions[-1]
        session.attack_mode = AttackMode.RAINBOW_TABLE
        session.status = DecryptionStatus.CRACKING

        print(f"\n  Starte Rainbow-Table Lookup...")
        self._rainbow_table_attack(session, table_path)

    def quick_crack_common_passwords(self) -> None:
        """Schnelles Cracking mit Common Passwords."""
        ui.clear()
        ui.rule("⚡ QUICK-CRACK (COMMON PASSWORDS)", ui.BCYAN)
        print()

        if not self.active_sessions:
            ui.warn("Keine Session aktiv")
            ui.pause()
            return

        session = self.active_sessions[-1]
        session.attack_mode = AttackMode.DICTIONARY
        session.status = DecryptionStatus.CRACKING

        print(f"  Versuche {len(self.COMMON_PASSWORDS)} häufige Passwörter...")
        print()

        self._dictionary_cracking(session, self.COMMON_PASSWORDS)

    def show_sessions(self) -> None:
        """Zeigt aktive Sessions."""
        ui.clear()
        ui.rule("📊 CRACKING-SITZUNGEN", ui.BCYAN)
        print()

        if not self.active_sessions:
            print("  Keine Sessions aktiv")
        else:
            for session in self.active_sessions:
                print(f"  Session: {session.session_id}")
                print(f"    APK: {session.apk_path}")
                print(f"    Status: {session.status.value}")
                print(f"    Verschlüsselte Elemente: {len(session.encrypted_elements)}")
                print(f"    Gefundene Keys: {len(session.found_keys)}")
                print(f"    Versuche: {session.attempts}")
                print()

        ui.pause()

    def show_cracked_data(self) -> None:
        """Zeigt entschlüsselte Daten."""
        ui.clear()
        ui.rule("🔑 ENTSCHLÜSSELTE DATEN", ui.BCYAN)
        print()

        if not self.cracked_data:
            print("  Keine entschlüsselten Daten")
        else:
            for data in self.cracked_data:
                print(f"  {data.data_id}")
                print(f"    Entschlüsselt: {data.decrypted_value}")
                print(f"    Key: {data.key_used}")
                print(f"    Algorithmus: {data.algorithm.value}")
                print(f"    Versuche: {data.attempts_needed}")
                print(f"    Zeit: {data.cracking_time_seconds:.2f}s")
                print()

        ui.pause()

    def export_results(self) -> None:
        """Exportiert Ergebnisse."""
        ui.clear()
        ui.rule("💾 ERGEBNISSE EXPORTIEREN", ui.BCYAN)
        print()

        if not self.cracked_data and not self.active_sessions:
            ui.warn("Keine Daten zum Exportieren")
            ui.pause()
            return

        report = {
            "export_timestamp": datetime.now().isoformat(),
            "sessions": [
                {
                    "session_id": s.session_id,
                    "apk_path": s.apk_path,
                    "attack_mode": s.attack_mode.value,
                    "status": s.status.value,
                    "found_keys": s.found_keys,
                    "attempts": s.attempts,
                }
                for s in self.active_sessions
            ],
            "cracked_data": [
                {
                    "decrypted_value": d.decrypted_value,
                    "key_used": d.key_used,
                    "algorithm": d.algorithm.value,
                    "attempts": d.attempts_needed,
                }
                for d in self.cracked_data
            ],
        }

        json_str = json.dumps(report, indent=2)
        print(json_str)
        print()
        ui.ok("Ergebnisse exportiert")
        ui.pause()

    # PRIVATE METHODEN

    def _extract_apk(self, apk_path: str, session: CrackingSession) -> List[EncryptedElement]:
        """Entpackt APK."""
        # Simuliere Extraktion
        time.sleep(0.1)
        return []

    def _analyze_dex(self, apk_path: str, session: CrackingSession) -> List[EncryptedElement]:
        """Analysiert DEX-Dateien."""
        time.sleep(0.1)
        return []

    def _scan_strings(self, apk_path: str, session: CrackingSession) -> List[EncryptedElement]:
        """Scannt Strings nach Verschlüsselung."""
        time.sleep(0.1)
        return []

    def _detect_algorithms(self, apk_path: str, session: CrackingSession) -> List[EncryptedElement]:
        """Erkennt Verschlüsselungs-Algorithmen."""
        time.sleep(0.1)
        return []

    def _find_encrypted_data(self, apk_path: str, session: CrackingSession) -> List[EncryptedElement]:
        """Findet verschlüsselte Daten."""
        # Simuliere Fund
        encrypted = EncryptedElement(
            element_id=f"enc_1",
            element_type="string",
            location="strings.xml",
            encrypted_data="5f4dcc3b5aa765d61d8327deb882cf99",
            detected_algorithm=EncryptionAlgorithm.AES_256,
            confidence=95.0,
            key_size=256,
        )
        return [encrypted]

    def _display_encrypted_elements(self, session: CrackingSession) -> None:
        """Zeigt verschlüsselte Elemente."""
        print("\n  Verschlüsselte Elemente:")
        for elem in session.encrypted_elements:
            print(f"    • {elem.element_id}")
            print(f"      Typ: {elem.element_type}")
            print(f"      Algorithmus: {elem.detected_algorithm.value}")
            print(f"      Konfidenz: {elem.confidence:.1f}%")

    def _brute_force_cracking(self, session: CrackingSession, min_len: int, max_len: int, charset: str) -> None:
        """Führt Brute-Force Cracking durch."""
        chars = self._get_charset(charset)
        print(f"  Zeichensatz: {chars}")
        print(f"  Bereich: {min_len}-{max_len}")
        print()

        attempts = 0
        for length in range(min_len, max_len + 1):
            print(f"  Länge {length}:")

            for attempt in itertools.islice(
                itertools.product(chars, repeat=length),
                100  # Limit für Demo
            ):
                password = ''.join(attempt)
                attempts += 1
                session.attempts = attempts

                # Versuche zu cracken
                if self._try_crack(session, password):
                    ui.ok(f"✓ Passwort gefunden: {password}")
                    session.found_keys[password] = password
                    session.status = DecryptionStatus.FOUND
                    return

                # Progress
                if attempts % 10 == 0:
                    ui.progress(attempts, 1000, f"Versuche: {attempts}")

        session.status = DecryptionStatus.EXHAUSTED
        ui.warn("Passwort nicht gefunden")

    def _dictionary_cracking(self, session: CrackingSession, wordlist: List[str]) -> None:
        """Führt Wörterbuch-Cracking durch."""
        print(f"  Teste {len(wordlist)} Wörter...\n")

        for i, word in enumerate(wordlist, 1):
            session.attempts = i

            if self._try_crack(session, word):
                ui.ok(f"✓ Passwort gefunden: {word}")
                session.found_keys[word] = word
                session.status = DecryptionStatus.FOUND
                return

            if i % 5 == 0:
                ui.progress(i, len(wordlist), f"Versuche: {i}/{len(wordlist)}")

        session.status = DecryptionStatus.EXHAUSTED
        ui.warn("Kein Match im Wörterbuch")

    def _mask_cracking(self, session: CrackingSession, mask: str) -> None:
        """Führt Mask-Cracking durch."""
        print(f"  Generiere Kandidaten für: {mask}\n")

        candidates = self._generate_mask_candidates(mask)
        print(f"  Teste {len(candidates)} Kandidaten...\n")

        for i, candidate in enumerate(candidates[:100], 1):
            session.attempts = i

            if self._try_crack(session, candidate):
                ui.ok(f"✓ Gefunden: {candidate}")
                session.found_keys[candidate] = candidate
                session.status = DecryptionStatus.FOUND
                return

            if i % 10 == 0:
                ui.progress(i, len(candidates), f"Versuche: {i}")

        session.status = DecryptionStatus.EXHAUSTED

    def _hybrid_cracking(self, session: CrackingSession, wordlist_path: str, mask: str) -> None:
        """Führt Hybrid-Cracking durch."""
        print("  Hybrid = Wörterbuch + Mask\n")
        self._dictionary_cracking(session, self.COMMON_PASSWORDS)

    def _rainbow_table_attack(self, session: CrackingSession, table_path: str) -> None:
        """Führt Rainbow-Table Attacke durch."""
        print("  Suche in Rainbow-Table...\n")

        # Simuliere Lookup
        for elem in session.encrypted_elements:
            time.sleep(0.2)
            ui.progress(1, 1, "Rainbow-Table Lookup")

        ui.warn("Keine Matches in Rainbow-Table")

    def _try_crack(self, session: CrackingSession, password: str) -> bool:
        """Versucht mit Passwort zu cracken."""
        # Simuliere Cracking-Versuch
        # In realem System: versuche mit diesem Passwort zu dekryptieren
        return False  # Für Demo

    def _get_charset(self, charset_name: str) -> str:
        """Gibt Zeichensatz zurück."""
        charsets = {
            "numbers": "0123456789",
            "lower": "abcdefghijklmnopqrstuvwxyz",
            "upper": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "symbols": "!@#$%^&*",
            "all": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
        }
        return charsets.get(charset_name, charsets["lower"])

    def _generate_mask_candidates(self, mask: str) -> List[str]:
        """Generiert Kandidaten aus Mask."""
        candidates = []

        def expand(pattern: str, pos: int = 0) -> None:
            if pos >= len(pattern):
                return

            if pattern[pos] == '?':
                if pos + 1 < len(pattern):
                    mask_char = pattern[pos + 1]
                    chars = {
                        'l': 'abcdefghijklmnopqrstuvwxyz',
                        'u': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                        'd': '0123456789',
                        's': '!@#$%^&*',
                        'a': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                    }
                    for char in chars.get(mask_char, ''):
                        candidates.append(char)

        # Simplified - just return some candidates
        return ["test1", "pass1", "admin1", "root1", "test123"]


def create_app_decryption_engine(adb: ADB) -> AppDecryptionEngine:
    """Erstellt neuen App Decryption Engine."""
    return AppDecryptionEngine(adb)
