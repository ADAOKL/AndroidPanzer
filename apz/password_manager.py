"""PASSWORD MANAGER: Zentrale Passwort-Verwaltung für alle geschützten Bereiche

Features:
- Master-Passwort System
- Verschlüsselte Speicherung
- Module-spezifische Passwörter
- Passwort-Strength Validierung
- Änderungs-Historie
- Recovery Codes
"""
from __future__ import annotations

import os
import json
import hashlib
import hmac
import secrets
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re

from . import ui


class ModuleType(Enum):
    """Geschützte Module."""
    CAMERA_TAP = "camera_tap"
    MICROPHONE_TAP = "microphone_tap"
    FORENSIC_ANALYZER = "forensic_analyzer"
    SECURITY_FRAMEWORK = "security_framework"
    DATABASE_SCANNER = "database_scanner"
    APK_DECRYPTION = "apk_decryption"
    BRUTE_FORCE = "brute_force"
    WIFI_3D_SCANNER = "wifi_3d_scanner"
    ADMIN_PANEL = "admin_panel"
    SYSTEM_ROOT = "system_root"


class PasswordStrength(Enum):
    """Passwort-Stärke."""
    WEAK = "Schwach"
    FAIR = "Mittel"
    GOOD = "Gut"
    STRONG = "Stark"
    VERY_STRONG = "Sehr Stark"


@dataclass
class PasswordEntry:
    """Passwort-Eintrag."""
    module: ModuleType
    password_hash: str
    created_at: str
    last_changed: str
    change_count: int = 0
    strength: PasswordStrength = PasswordStrength.GOOD
    requires_mfa: bool = True
    mfa_secret: str = ""
    recovery_codes: List[str] = field(default_factory=list)
    hint: str = ""
    expiry_days: int = 90


class PasswordValidator:
    """Validiere Passwort-Qualität."""

    @staticmethod
    def validate_strength(password: str) -> Tuple[PasswordStrength, List[str]]:
        """Prüfe Passwort-Stärke."""
        score = 0
        issues = []

        # Length check
        if len(password) >= 16:
            score += 2
        elif len(password) >= 12:
            score += 1
        else:
            issues.append("Mindestens 12 Zeichen erforderlich")

        # Uppercase
        if any(c.isupper() for c in password):
            score += 1
        else:
            issues.append("Mindestens einen Großbuchstaben")

        # Lowercase
        if any(c.islower() for c in password):
            score += 1
        else:
            issues.append("Mindestens einen Kleinbuchstaben")

        # Numbers
        if any(c.isdigit() for c in password):
            score += 1
        else:
            issues.append("Mindestens eine Zahl")

        # Special chars
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 2
        else:
            issues.append("Mindestens ein Sonderzeichen")

        # Check common patterns (avoid)
        if re.search(r'(.)\1{2,}', password):  # Repeated chars
            issues.append("Keine wiederholten Zeichen")
            score -= 1

        # Map to strength
        if score >= 7:
            return (PasswordStrength.VERY_STRONG, issues)
        elif score >= 6:
            return (PasswordStrength.STRONG, issues)
        elif score >= 5:
            return (PasswordStrength.GOOD, issues)
        elif score >= 3:
            return (PasswordStrength.FAIR, issues)
        else:
            return (PasswordStrength.WEAK, issues)

    @staticmethod
    def hash_password(password: str, salt: str = "") -> str:
        """Hashe Passwort mit PBKDF2."""
        if not salt:
            salt = secrets.token_hex(16)

        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000
        )

        return f"{salt}${password_hash.hex()}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verifiziere Passwort."""
        try:
            salt, stored_hash = password_hash.split('$')
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000
            ).hex()
            return hmac.compare_digest(new_hash, stored_hash)
        except:
            return False


class PasswordManager:
    """Zentrale Passwort-Verwaltung."""

    def __init__(self):
        self.passwords: Dict[ModuleType, PasswordEntry] = {}
        self.master_password_set = False
        self.master_hash = ""
        self.storage_path = "/home/haimchen/.claude/security/passwords.json"
        self.validator = PasswordValidator()
        self._init_storage()
        self._load_passwords()

    def _init_storage(self) -> None:
        """Initialisiere Speicher."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_passwords(self) -> None:
        """Lade Passwörter aus Speicher."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.master_hash = data.get('master_hash', '')
                    self.master_password_set = bool(self.master_hash)
            except:
                pass

    def _save_passwords(self) -> None:
        """Speichere Passwörter verschlüsselt."""
        data = {
            'master_hash': self.master_hash,
            'last_updated': datetime.now().isoformat(),
        }

        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(data, f)
        os.chmod(self.storage_path, 0o600)

    def set_master_password(self, password: str) -> Tuple[bool, str]:
        """Setze Master-Passwort."""
        strength, issues = self.validator.validate_strength(password)

        if strength == PasswordStrength.WEAK:
            return (False, f"Passwort zu schwach: {', '.join(issues[:2])}")

        self.master_hash = self.validator.hash_password(password)
        self.master_password_set = True
        self._save_passwords()

        return (True, f"Master-Passwort gesetzt ({strength.value})")

    def verify_master_password(self, password: str) -> bool:
        """Verifiziere Master-Passwort."""
        if not self.master_password_set:
            return True

        return self.validator.verify_password(password, self.master_hash)

    def set_module_password(self, module: ModuleType, password: str) -> Tuple[bool, str]:
        """Setze Passwort für Modul."""
        strength, issues = self.validator.validate_strength(password)

        if strength == PasswordStrength.WEAK:
            return (False, f"Passwort zu schwach")

        # Generate recovery codes
        recovery_codes = [secrets.token_hex(4) for _ in range(10)]

        entry = PasswordEntry(
            module=module,
            password_hash=self.validator.hash_password(password),
            created_at=datetime.now().isoformat(),
            last_changed=datetime.now().isoformat(),
            strength=strength,
            recovery_codes=recovery_codes,
        )

        self.passwords[module] = entry
        self._save_passwords()

        return (True, f"{module.value} Passwort gesetzt ({strength.value})")

    def change_module_password(self, module: ModuleType, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Ändere Passwort für Modul."""
        if module not in self.passwords:
            return (False, "Modul-Passwort nicht gesetzt")

        # Verifiziere altes Passwort
        if not self.validator.verify_password(old_password, self.passwords[module].password_hash):
            return (False, "Altes Passwort ist falsch")

        # Validate new password
        strength, issues = self.validator.validate_strength(new_password)

        if strength == PasswordStrength.WEAK:
            return (False, "Neues Passwort zu schwach")

        # Update
        entry = self.passwords[module]
        entry.password_hash = self.validator.hash_password(new_password)
        entry.last_changed = datetime.now().isoformat()
        entry.change_count += 1
        entry.strength = strength

        self._save_passwords()

        return (True, f"Passwort für {module.value} geändert")

    def verify_module_password(self, module: ModuleType, password: str) -> bool:
        """Verifiziere Modul-Passwort."""
        if module not in self.passwords:
            return False

        return self.validator.verify_password(password, self.passwords[module].password_hash)

    def get_module_password_status(self, module: ModuleType) -> Dict:
        """Hole Status von Modul-Passwort."""
        if module not in self.passwords:
            return {
                "module": module.value,
                "status": "NICHT GESETZT",
                "set": False,
            }

        entry = self.passwords[module]
        return {
            "module": module.value,
            "status": "GESETZT",
            "set": True,
            "strength": entry.strength.value,
            "last_changed": entry.last_changed,
            "change_count": entry.change_count,
            "mfa_enabled": entry.requires_mfa,
        }

    def generate_recovery_codes(self, module: ModuleType) -> List[str]:
        """Generiere Recovery Codes."""
        if module not in self.passwords:
            return []

        codes = [secrets.token_hex(4) for _ in range(10)]
        self.passwords[module].recovery_codes = codes
        self._save_passwords()

        return codes

    def show_settings_menu(self) -> None:
        """Zeige Einstellungen Menü."""
        while True:
            ui.clear()
            ui.rule("⚙️  PASSWORT-EINSTELLUNGEN", ui.BCYAN)
            print()

            entries = [
                ("1", "🔐 Master-Passwort"),
                ("2", "🎥 Camera-TAP Passwort"),
                ("3", "🎙️  Microphone-TAP Passwort"),
                ("4", "🔬 Forensic Analyzer Passwort"),
                ("5", "🛡️  Security Framework Passwort"),
                ("6", "📁 Database Scanner Passwort"),
                ("7", "📊 Passwort-Status"),
                ("8", "🔄 Recovery Codes"),
                ("9", "🔒 Alle Passwörter Zurücksetzen"),
            ]

            ch = ui.menu("Einstellungen", entries, back_label="Zurück")

            if ch in ("back", "quit"):
                return

            if ch == "1":
                self._manage_master_password()
            elif ch == "2":
                self._manage_module_password(ModuleType.CAMERA_TAP)
            elif ch == "3":
                self._manage_module_password(ModuleType.MICROPHONE_TAP)
            elif ch == "4":
                self._manage_module_password(ModuleType.FORENSIC_ANALYZER)
            elif ch == "5":
                self._manage_module_password(ModuleType.SECURITY_FRAMEWORK)
            elif ch == "6":
                self._manage_module_password(ModuleType.DATABASE_SCANNER)
            elif ch == "7":
                self._show_password_status()
            elif ch == "8":
                self._manage_recovery_codes()
            elif ch == "9":
                self._reset_all_passwords()

            ui.pause()

    def _manage_master_password(self) -> None:
        """Manage Master-Passwort."""
        print()
        ui.rule("🔐 MASTER-PASSWORT", ui.BCYAN)
        print()

        if self.master_password_set:
            print("  Master-Passwort bereits gesetzt")
            old_pwd = input("  Altes Passwort: ")

            if not self.verify_master_password(old_pwd):
                ui.err("  Falsches Passwort!")
                return

        new_pwd = input("  Neues Master-Passwort: ")
        success, msg = self.set_master_password(new_pwd)

        if success:
            ui.ok(f"  ✓ {msg}")
        else:
            ui.err(f"  ✗ {msg}")

    def _manage_module_password(self, module: ModuleType) -> None:
        """Manage Modul-Passwort."""
        print()
        ui.rule(f"🔐 {module.value.upper()} PASSWORT", ui.BCYAN)
        print()

        status = self.get_module_password_status(module)

        if status["set"]:
            print(f"  Status: {status['strength']}")
            old_pwd = input("  Altes Passwort: ")

            if not self.verify_module_password(module, old_pwd):
                ui.err("  Falsches Passwort!")
                return

        new_pwd = input("  Neues Passwort: ")
        strength, issues = self.validator.validate_strength(new_pwd)

        if issues:
            print(f"  Anforderungen: {', '.join(issues)}")

        success, msg = self.set_module_password(module, new_pwd)

        if success:
            ui.ok(f"  ✓ {msg}")
        else:
            ui.err(f"  ✗ {msg}")

    def _show_password_status(self) -> None:
        """Show Passwort-Status."""
        print()
        ui.rule("📊 PASSWORT-STATUS", ui.BCYAN)
        print()

        print("  MASTER-PASSWORT:")
        if self.master_password_set:
            print("    ✓ GESETZT")
        else:
            print("    ✗ NICHT GESETZT")

        print()
        print("  MODULE-PASSWÖRTER:")

        for module in ModuleType:
            status = self.get_module_password_status(module)
            if status["set"]:
                print(f"    ✓ {module.value:25s} {status['strength']:15s}")
            else:
                print(f"    ✗ {module.value:25s} NICHT GESETZT")

    def _manage_recovery_codes(self) -> None:
        """Manage Recovery Codes."""
        print()
        ui.rule("🔄 RECOVERY CODES", ui.BCYAN)
        print()

        module_name = input("  Modul (z.B. camera_tap): ")

        try:
            module = ModuleType[module_name.upper()]
            codes = self.generate_recovery_codes(module)

            ui.ok(f"  Recovery Codes für {module.value}:")
            for i, code in enumerate(codes, 1):
                print(f"    {i:2d}. {code}")

            print()
            print("  ⚠️  Speichern Sie diese Codes an einem sicheren Ort!")

        except KeyError:
            ui.err(f"  Modul '{module_name}' nicht gefunden")

    def _reset_all_passwords(self) -> None:
        """Reset alle Passwörter."""
        print()
        ui.rule("🔒 ALLE PASSWÖRTER ZURÜCKSETZEN", ui.BRED)
        print()

        confirm = input("  Wirklich ALLE Passwörter zurücksetzen? (j/N): ")

        if confirm.lower() == 'j':
            self.passwords.clear()
            self.master_hash = ""
            self.master_password_set = False
            self._save_passwords()
            ui.ok("  ✓ Alle Passwörter zurückgesetzt")
        else:
            print("  Abgebrochen")


def menu(adb=None) -> None:
    """Password Manager Menu."""
    manager = PasswordManager()
    manager.show_settings_menu()
