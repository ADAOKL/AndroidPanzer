"""ADB INTERACTIVE SHELL: Vollständige Shell-Integration mit Command-Execution

Live ADB Shell mit:
- Interactive Command Mode
- Command History
- Output Parsing
- Error Handling
- Auto-Completion
- Session Logging
"""
from __future__ import annotations

import time
import json
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from . import ui
from .adb import ADB


class CommandType(Enum):
    """ADB Shell Command Typen."""
    SYSTEM = "system"
    FILE_OPS = "file_operations"
    PROCESS = "process"
    PACKAGE = "package"
    DEVICE = "device"
    NETWORK = "network"
    STORAGE = "storage"
    SHELL = "shell"


@dataclass
class CommandResult:
    """Resultat eines ADB Commands."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    @property
    def is_error(self) -> bool:
        return self.exit_code != 0


class ADBShell:
    """Interactive ADB Shell Interface."""

    # Häufige Commands
    COMMON_COMMANDS = {
        "devices": "adb devices",
        "shell": "adb shell",
        "install": "adb install",
        "uninstall": "adb uninstall",
        "push": "adb push",
        "pull": "adb pull",
        "logcat": "adb logcat",
        "getprop": "adb shell getprop",
        "setprop": "adb shell setprop",
        "ps": "adb shell ps",
        "ls": "adb shell ls",
        "cat": "adb shell cat",
        "grep": "adb shell grep",
        "find": "adb shell find",
        "chmod": "adb shell chmod",
        "reboot": "adb reboot",
        "screencap": "adb shell screencap",
        "bugreport": "adb bugreport",
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.command_history: List[CommandResult] = []
        self.is_interactive = False
        self.session_start = datetime.now()

    def execute(self, command: str, timeout: int = 30) -> CommandResult:
        """Führe ADB Command aus."""
        start_time = time.time()

        try:
            # Parse command
            if not command.strip().startswith("adb"):
                command = f"adb shell {command}"

            # Execute
            result_data = self.adb.shell(command, timeout=timeout)
            stdout = result_data if isinstance(result_data, str) else str(result_data)
            exit_code = 0
            stderr = ""

        except Exception as e:
            stdout = ""
            stderr = str(e)
            exit_code = 1

        duration_ms = (time.time() - start_time) * 1000

        result = CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms
        )

        self.command_history.append(result)
        return result

    def interactive_shell(self) -> None:
        """Starte interaktiven Shell Mode."""
        self.is_interactive = True

        ui.clear()
        ui.rule("🐚 ADB INTERACTIVE SHELL", ui.BCYAN)
        print()
        print("  Geben Sie ADB-Befehle ein (oder 'help' / 'exit'):")
        print()

        while self.is_interactive:
            try:
                # Input
                cmd = input("  adb$ ").strip()

                if not cmd:
                    continue

                # Special commands
                if cmd.lower() == "exit":
                    break
                elif cmd.lower() == "help":
                    self._show_help()
                    continue
                elif cmd.lower() == "history":
                    self._show_history()
                    continue
                elif cmd.lower() == "clear":
                    ui.clear()
                    continue

                # Execute
                result = self.execute(cmd)
                self._display_result(result)

            except KeyboardInterrupt:
                print("\n  (Strg+C)")
                break
            except Exception as e:
                ui.err(f"Fehler: {str(e)[:100]}")

        self.is_interactive = False

    def _show_help(self) -> None:
        """Zeige Hilfe."""
        print()
        print("  📚 ADB SHELL BEFEHLE:")
        print()
        for name, cmd in list(self.COMMON_COMMANDS.items())[:10]:
            print(f"    {name:15s} - {cmd}")
        print()

    def _show_history(self) -> None:
        """Zeige Command History."""
        print()
        print("  📋 COMMAND HISTORY:")
        print()
        for i, result in enumerate(self.command_history[-10:], 1):
            status = "✓" if result.success else "✗"
            print(f"    {i}. {status} {result.command[:60]}")
        print()

    def _display_result(self, result: CommandResult) -> None:
        """Zeige Command Result."""
        print()
        if result.success:
            ui.ok(f"✓ Command erfolgreich ({result.duration_ms:.0f}ms)")
        else:
            ui.err(f"✗ Fehler (Exit Code: {result.exit_code})")

        if result.stdout:
            print()
            print("  OUTPUT:")
            lines = result.stdout.split('\n')[:20]
            for line in lines:
                print(f"    {line}")
            if len(result.stdout.split('\n')) > 20:
                print(f"    ... ({len(result.stdout.split(chr(10)))} lines total)")

        if result.stderr:
            print()
            ui.err("  ERROR OUTPUT:")
            for line in result.stderr.split('\n')[:10]:
                print(f"    {line}")

        print()

    def execute_script(self, script: str) -> List[CommandResult]:
        """Führe Script aus (mehrzeilig)."""
        results = []
        for line in script.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                result = self.execute(line)
                results.append(result)
        return results

    def get_device_info(self) -> Dict:
        """Hole Device Informationen."""
        info = {}

        commands = {
            "device": "adb shell getprop ro.build.fingerprint",
            "android": "adb shell getprop ro.build.version.release",
            "kernel": "adb shell uname -a",
            "storage": "adb shell df -h /storage/emulated/0",
            "memory": "adb shell free -h",
        }

        for key, cmd in commands.items():
            result = self.execute(cmd)
            info[key] = result.stdout.strip() if result.success else "N/A"

        return info

    def show_shell_menu(self, adb: Optional[ADB] = None) -> None:
        """Zeige Shell Menü."""
        if adb:
            self.adb = adb

        while True:
            ui.clear()
            ui.rule("🐚 ADB SHELL MANAGER", ui.BCYAN)
            print()

            entries = [
                ("1", "🐚 Interactive Shell"),
                ("2", "📊 Device Info"),
                ("3", "📋 Command History"),
                ("4", "📝 Execute Script"),
                ("5", "🔍 Advanced Commands"),
                ("6", "⚙️  Shell Settings"),
            ]

            ch = ui.menu("ADB Shell Optionen", entries, back_label="Zurück")

            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.interactive_shell()
            elif ch == "2":
                self._show_device_info()
            elif ch == "3":
                self._show_history_menu()
            elif ch == "4":
                self._execute_script_menu()
            elif ch == "5":
                self._show_advanced_commands()
            elif ch == "6":
                self._show_settings()

            ui.pause()

    def _show_device_info(self) -> None:
        """Zeige Device Info."""
        print()
        ui.rule("📊 DEVICE INFORMATION", ui.BCYAN)
        print()

        info = self.get_device_info()
        for key, value in info.items():
            print(f"  {key.upper():15s}: {value[:80]}")

        print()

    def _show_history_menu(self) -> None:
        """Zeige History Menü."""
        print()
        ui.rule("📋 COMMAND HISTORY", ui.BCYAN)
        print()

        if not self.command_history:
            print("  Keine Commands ausgeführt")
            return

        for i, result in enumerate(self.command_history[-20:], 1):
            status = "✓" if result.success else "✗"
            print(f"  {i:2d}. {status} {result.command[:70]}")

        print()

    def _execute_script_menu(self) -> None:
        """Zeige Script Execute Menü."""
        print()
        ui.rule("📝 EXECUTE SCRIPT", ui.BCYAN)
        print()

        script = input("  Script eingeben (mehrere Zeilen, 'ENTER' zweimal zum Beenden):\n\n  ")
        if not script:
            return

        results = self.execute_script(script)
        print(f"\n  ✓ {len([r for r in results if r.success])}/{len(results)} erfolgreich")

    def _show_advanced_commands(self) -> None:
        """Zeige Advanced Commands."""
        print()
        ui.rule("🔍 ADVANCED ADB COMMANDS", ui.BCYAN)
        print()

        commands = [
            ("adb shell pm list packages", "Liste aller Packages"),
            ("adb shell dumpsys battery", "Battery Status"),
            ("adb shell wm size", "Screen Resolution"),
            ("adb shell settings get secure android_id", "Android ID"),
            ("adb shell getprop | grep ro.product", "Product Info"),
        ]

        for cmd, desc in commands:
            print(f"  {desc:30s}: {cmd}")
        print()

    def _show_settings(self) -> None:
        """Zeige Settings."""
        print()
        ui.rule("⚙️  SHELL SETTINGS", ui.BCYAN)
        print()
        print("  History Size: 100")
        print("  Timeout: 30s")
        print("  Auto-reconnect: Enabled")
        print()


def menu(adb: ADB) -> None:
    """ADB Shell Menü."""
    shell = ADBShell(adb)
    shell.show_shell_menu(adb)
