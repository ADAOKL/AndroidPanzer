"""AUTO ROOT ENGINE: Automatisches Rooting + Daten-Wiederherstellung

Umfassendes System:
- Multi-Method Auto Rooting
- ADB Shell Integration
- Recovery Mode Handling
- Data Recovery & Restoration
- Backup Management
- System Partition Manipulation
- Exploit Chain Execution
"""
from __future__ import annotations

import os
import time
import subprocess
import json
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from . import ui
from .adb import ADB


class RootMethod(Enum):
    """Rooting-Methoden."""
    MAGISK = "Magisk (Universal)"
    SUPERSU = "SuperSU (Legacy)"
    PHROOT = "phh's Superuser"
    LINEAGE = "LineageOS Root"
    CUSTOM_EXPLOIT = "Custom Exploit Chain"
    ADB_PRIVILEGE = "ADB Privilege Escalation"
    KERNEL_EXPLOIT = "Kernel Vulnerability"
    BOOTLOADER_UNLOCK = "Bootloader Unlock"


class RootStatus(Enum):
    """Root-Status."""
    NOT_ROOTED = "Not Rooted"
    PARTIALLY_ROOTED = "Partially Rooted"
    FULLY_ROOTED = "Fully Rooted"
    ROOTING = "Rooting in Progress"
    ROOT_FAILED = "Root Failed"


class RecoveryMode(Enum):
    """Recovery-Modi."""
    STOCK = "Stock Recovery"
    TWRP = "TWRP (Team Win)"
    CWM = "CWM (Clockwork)"
    LINEAGE = "LineageOS Recovery"
    CUSTOM = "Custom Recovery"


@dataclass
class RootExploit:
    """Root-Exploit Definition."""
    name: str
    method: RootMethod
    target_versions: List[str]
    required_tools: List[str]
    steps: List[str]
    success_rate: float
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class DeviceInfo:
    """Geräte-Informationen."""
    device_id: str
    manufacturer: str
    model: str
    android_version: str
    build_number: str
    kernel_version: str
    is_rooted: bool = False
    root_method: Optional[RootMethod] = None
    recovery_mode: Optional[RecoveryMode] = None
    bootloader_locked: bool = True


@dataclass
class BackupEntry:
    """Backup-Eintrag."""
    backup_id: str
    timestamp: str
    device_model: str
    app_data: Dict = field(default_factory=dict)
    system_files: List[str] = field(default_factory=list)
    databases: List[str] = field(default_factory=list)
    size_mb: float = 0.0


class RootExploitDatabase:
    """Datenbank mit Root-Exploits."""

    EXPLOITS = [
        RootExploit(
            name="Magisk v27.0",
            method=RootMethod.MAGISK,
            target_versions=["5.0+"],
            required_tools=["adb", "fastboot"],
            steps=["adb reboot bootloader", "fastboot flash magisk.img"],
            success_rate=0.98,
            risk_level="LOW"
        ),
        RootExploit(
            name="CVE-2021-1048 (Pixel Exclusive)",
            method=RootMethod.KERNEL_EXPLOIT,
            target_versions=["11-12"],
            required_tools=["adb", "exploit_binary"],
            steps=["adb push exploit /data/", "adb shell /data/exploit"],
            success_rate=0.95,
            risk_level="MEDIUM"
        ),
        RootExploit(
            name="Bootloader Unlock (OEM Unlock)",
            method=RootMethod.BOOTLOADER_UNLOCK,
            target_versions=["5.0+"],
            required_tools=["adb", "fastboot"],
            steps=["adb reboot bootloader", "fastboot flashing unlock"],
            success_rate=0.90,
            risk_level="HIGH"
        ),
        RootExploit(
            name="ADB Root Access (Debug Bridge)",
            method=RootMethod.ADB_PRIVILEGE,
            target_versions=["5.0-6.0"],
            required_tools=["adb"],
            steps=["adb root", "adb remount"],
            success_rate=0.85,
            risk_level="LOW"
        ),
    ]

    @classmethod
    def get_exploits_for_version(cls, version: str) -> List[RootExploit]:
        """Hole Exploits für Android-Version."""
        matching = []
        for exploit in cls.EXPLOITS:
            for target in exploit.target_versions:
                if target == "5.0+" and float(version.split('.')[0]) >= 5:
                    matching.append(exploit)
                    break
                elif target in version:
                    matching.append(exploit)
                    break
        return matching


class AutoRootEngine:
    """Master Auto Rooting Engine."""

    def __init__(self, adb: ADB):
        self.adb = adb
        self.device_info: Optional[DeviceInfo] = None
        self.root_status = RootStatus.NOT_ROOTED
        self.backups: List[BackupEntry] = []
        self.backup_dir = "/tmp/android_panzer_backups"
        os.makedirs(self.backup_dir, exist_ok=True)

    def detect_device(self) -> Optional[DeviceInfo]:
        """Erkenne Geräte-Informationen."""
        try:
            result = self.adb.shell("getprop ro.build.fingerprint")
            fingerprint = result if result else "Unknown"

            device_id = self.adb.shell("getprop ro.serialno") or "unknown_device"
            manufacturer = self.adb.shell("getprop ro.product.manufacturer") or "Unknown"
            model = self.adb.shell("getprop ro.product.model") or "Unknown"
            android_version = self.adb.shell("getprop ro.build.version.release") or "Unknown"
            build_number = self.adb.shell("getprop ro.build.id") or "Unknown"
            kernel_version = self.adb.shell("uname -r") or "Unknown"

            # Prüfe ob geroot
            is_rooted = self._check_root_status()

            self.device_info = DeviceInfo(
                device_id=device_id,
                manufacturer=manufacturer,
                model=model,
                android_version=android_version,
                build_number=build_number,
                kernel_version=kernel_version,
                is_rooted=is_rooted,
            )

            return self.device_info
        except Exception as e:
            ui.err(f"Geräte-Erkennung fehlgeschlagen: {e}")
            return None

    def _check_root_status(self) -> bool:
        """Prüfe ob Gerät geroot ist."""
        try:
            result = self.adb.shell("su -c 'echo root'")
            return "root" in result.lower() if result else False
        except:
            return False

    def get_available_exploits(self) -> List[RootExploit]:
        """Hole verfügbare Exploits für Gerät."""
        if not self.device_info:
            return []

        exploits = RootExploitDatabase.get_exploits_for_version(
            self.device_info.android_version
        )

        # Sortiere nach Success-Rate
        exploits.sort(key=lambda x: x.success_rate, reverse=True)
        return exploits

    def auto_root(self) -> Tuple[bool, str]:
        """Führe automatisches Rooting aus."""
        if not self.device_info:
            if not self.detect_device():
                return (False, "Geräte-Erkennung fehlgeschlagen")

        # Prüfe ob bereits geroot
        if self.device_info.is_rooted:
            return (True, "Gerät ist bereits geroot!")

        exploits = self.get_available_exploits()
        if not exploits:
            return (False, "Keine Exploits für dieses Gerät verfügbar")

        # Versuche jeden Exploit
        for i, exploit in enumerate(exploits, 1):
            ui.ok(f"\n[{i}/{len(exploits)}] Versuche: {exploit.name}")

            success = self._execute_exploit(exploit)
            if success:
                self.root_status = RootStatus.FULLY_ROOTED
                return (True, f"✓ Rooting erfolgreich mit {exploit.name}")

            ui.warn(f"  ✗ {exploit.name} fehlgeschlagen")

        return (False, "Alle Rooting-Methoden fehlgeschlagen")

    def _execute_exploit(self, exploit: RootExploit) -> bool:
        """Führe Exploit aus."""
        try:
            for step in exploit.steps:
                ui.ok(f"  → {step}")
                result = self.adb.shell(step)
                time.sleep(0.5)

            # Verifiziere
            time.sleep(1)
            return self._check_root_status()
        except:
            return False

    def backup_data(self) -> Tuple[bool, str]:
        """Backup aller Daten."""
        if not self.device_info:
            return (False, "Gerät nicht erkannt")

        backup_id = f"backup_{int(time.time())}"
        backup_path = f"{self.backup_dir}/{backup_id}"
        os.makedirs(backup_path, exist_ok=True)

        ui.ok("Starte Daten-Backup...")

        try:
            # Backup App-Daten
            ui.ok("  • Sichere App-Daten...")
            self.adb.shell(f"adb backup -apk -shared -all -f {backup_path}/apps.ab")

            # Backup System-Dateien
            ui.ok("  • Sichere System-Dateien...")
            self.adb.shell(f"adb pull /system {backup_path}/system")

            # Backup Datenbanken
            ui.ok("  • Sichere Datenbanken...")
            self.adb.shell(f"adb pull /data/data {backup_path}/data")

            backup = BackupEntry(
                backup_id=backup_id,
                timestamp=datetime.now().isoformat(),
                device_model=self.device_info.model,
                size_mb=self._calculate_backup_size(backup_path),
            )

            self.backups.append(backup)
            return (True, f"Backup erstellt: {backup_id}")

        except Exception as e:
            return (False, f"Backup-Fehler: {e}")

    def restore_data(self, backup_id: str) -> Tuple[bool, str]:
        """Stelle Daten aus Backup wieder her."""
        backup_path = f"{self.backup_dir}/{backup_id}"

        if not os.path.exists(backup_path):
            return (False, f"Backup {backup_id} nicht gefunden")

        ui.ok(f"Stelle Daten aus {backup_id} wieder her...")

        try:
            # Restore App-Daten
            if os.path.exists(f"{backup_path}/apps.ab"):
                ui.ok("  • Stelle Apps wieder her...")
                self.adb.shell(f"adb restore {backup_path}/apps.ab")

            # Restore System-Dateien (wenn geroot)
            if self.device_info.is_rooted:
                ui.ok("  • Stelle System-Dateien wieder her...")
                self.adb.shell(f"adb push {backup_path}/system /system")

            # Restore Datenbanken
            if os.path.exists(f"{backup_path}/data"):
                ui.ok("  • Stelle Datenbanken wieder her...")
                self.adb.shell(f"adb push {backup_path}/data /data/data")

            return (True, "Daten-Wiederherstellung abgeschlossen")

        except Exception as e:
            return (False, f"Wiederherstellungs-Fehler: {e}")

    def _calculate_backup_size(self, path: str) -> float:
        """Berechne Backup-Größe."""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total += os.path.getsize(filepath)
        return total / (1024 * 1024)

    def show_auto_root_menu(self) -> None:
        """Zeige Auto Root Menü."""
        while True:
            ui.clear()
            ui.rule("🔓 AUTO ROOT ENGINE", ui.BRED)
            print()

            entries = [
                ("1", "📱 Geräte erkennen"),
                ("2", "🔓 Auto-Root starten"),
                ("3", "📊 Root-Status prüfen"),
                ("4", "💾 Daten-Backup"),
                ("5", "♻️  Daten wiederherstellen"),
                ("6", "📋 Verfügbare Exploits"),
                ("7", "🔍 Erweiterte Optionen"),
                ("8", "🛠️  ADB Shell Integration"),
            ]

            ch = ui.menu("Auto Root Optionen", entries, back_label="Zurück")

            if ch in ("back", "quit"):
                return

            if ch == "1":
                self._detect_device_menu()
            elif ch == "2":
                self._auto_root_menu()
            elif ch == "3":
                self._check_status_menu()
            elif ch == "4":
                self._backup_menu()
            elif ch == "5":
                self._restore_menu()
            elif ch == "6":
                self._show_exploits_menu()
            elif ch == "7":
                self._advanced_options()
            elif ch == "8":
                self._adb_shell_integration()

            ui.pause()

    def _detect_device_menu(self) -> None:
        """Detect Device Menü."""
        print()
        ui.rule("📱 GERÄTE-ERKENNUNG", ui.BCYAN)
        print()

        print("  Erkenne Gerät...")
        device = self.detect_device()

        if device:
            print()
            ui.ok("✓ Gerät erkannt!")
            print(f"  • Hersteller:     {device.manufacturer}")
            print(f"  • Modell:         {device.model}")
            print(f"  • Android:        {device.android_version}")
            print(f"  • Build:          {device.build_number}")
            print(f"  • Kernel:         {device.kernel_version}")
            print(f"  • Geroot:         {'JA ✓' if device.is_rooted else 'NEIN ✗'}")
        else:
            ui.err("✗ Geräte-Erkennung fehlgeschlagen")

    def _auto_root_menu(self) -> None:
        """Auto Root Menü."""
        print()
        ui.rule("🔓 AUTO ROOT STARTEN", ui.BRED)
        print()

        if ui.confirm("Wirklich rooten? Dies kann Daten löschen!", False):
            success, msg = self.auto_root()

            if success:
                ui.ok(f"✓ {msg}")
            else:
                ui.err(f"✗ {msg}")

    def _check_status_menu(self) -> None:
        """Status Menü."""
        print()
        ui.rule("📊 ROOT STATUS", ui.BCYAN)
        print()

        if not self.device_info:
            self.detect_device()

        if self.device_info:
            status = "✓ GEROOT" if self.device_info.is_rooted else "✗ NICHT GEROOT"
            print(f"  Status: {status}")
            print(f"  Gerät: {self.device_info.model}")
            print(f"  Android: {self.device_info.android_version}")
        else:
            ui.err("Gerät nicht erkannt")

    def _backup_menu(self) -> None:
        """Backup Menü."""
        print()
        ui.rule("💾 DATEN-BACKUP", ui.BCYAN)
        print()

        success, msg = self.backup_data()

        if success:
            ui.ok(f"✓ {msg}")
        else:
            ui.err(f"✗ {msg}")

    def _restore_menu(self) -> None:
        """Restore Menü."""
        print()
        ui.rule("♻️  DATEN-WIEDERHERSTELLUNG", ui.BCYAN)
        print()

        if not self.backups:
            print("  Keine Backups verfügbar")
            return

        print("  Verfügbare Backups:")
        for i, backup in enumerate(self.backups, 1):
            print(f"    {i}. {backup.backup_id} ({backup.size_mb:.1f}MB)")

        try:
            choice = int(ui.ask("Backup wählen", "1"))
            if 1 <= choice <= len(self.backups):
                backup = self.backups[choice - 1]
                success, msg = self.restore_data(backup.backup_id)

                if success:
                    ui.ok(f"✓ {msg}")
                else:
                    ui.err(f"✗ {msg}")
        except ValueError:
            ui.err("Ungültige Eingabe")

    def _show_exploits_menu(self) -> None:
        """Zeige Exploits."""
        print()
        ui.rule("📋 VERFÜGBARE EXPLOITS", ui.BCYAN)
        print()

        if not self.device_info:
            self.detect_device()

        exploits = self.get_available_exploits()

        if exploits:
            for i, exploit in enumerate(exploits, 1):
                print(f"  {i}. {exploit.name}")
                print(f"     Erfolgsrate: {exploit.success_rate*100:.0f}%")
                print(f"     Risiko: {exploit.risk_level}")
        else:
            print("  Keine Exploits für dieses Gerät")

    def _advanced_options(self) -> None:
        """Advanced Options."""
        print()
        ui.rule("🔍 ERWEITERTE OPTIONEN", ui.BCYAN)
        print()
        print("  Optionen:")
        print("    • Bootloader freischalten")
        print("    • Recovery-Modus wechseln")
        print("    • Partition bearbeiten")
        print("    • System-Dateien modifizieren")

    def _adb_shell_integration(self) -> None:
        """ADB Shell Integration."""
        print()
        ui.rule("🛠️  ADB SHELL INTEGRATION", ui.BCYAN)
        print()
        print("  Führe direkte Shell-Befehle aus:")
        cmd = ui.ask("Befehl", "").strip()

        if cmd:
            result = self.adb.shell(cmd)
            print(f"\n  Output:\n  {result}")


def menu(adb: ADB) -> None:
    """Auto Root Engine Menu."""
    engine = AutoRootEngine(adb)
    engine.show_auto_root_menu()
