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
        """Interaktives Menü für erweiterte ADB-Befehle nach Kategorie."""
        while True:
            ui.clear()
            ui.rule("🔍 ADVANCED ADB COMMANDS", ui.BCYAN)
            ch = ui.menu("Kategorie", [
                ("1",  "📦 Package-Manager    (install/uninstall/disable/list)"),
                ("2",  "🌐 Netzwerk-Diagnose  (ss, ip, netstat, ping, wifi)"),
                ("3",  "⚙  Prozess-Manager    (ps, top, kill)"),
                ("4",  "🔑 Root-Befehle       (su, setenforce, mount)"),
                ("5",  "🗄  Datei-Operationen  (ls, find, stat, dd)"),
                ("6",  "📊 System-Info        (props, dumpsys, uname, cpu)"),
                ("7",  "📱 App-Steuerung      (am start/stop/broadcast)"),
                ("8",  "🔋 Energie & Akku     (battery, wakelock, doze)"),
                ("9",  "🎵 Medien & Display   (screencap, screenrecord, wm)"),
                ("10", "🔐 Sicherheit         (Android ID, encryption, keystore)"),
            ], back_label="Zurück")
            if ch in ("back", "quit"):
                return
            self._run_category(ch)

    def _run_category(self, cat: str) -> None:
        """Führt Befehle einer Kategorie aus."""
        cats = {
            "1": [
                ("pm list packages -3",                 "Drittanbieter-Apps"),
                ("pm list packages -d",                 "Deaktivierte Apps"),
                ("pm list packages -s",                 "System-Apps"),
                ("pm list packages -U",                 "Apps mit UID"),
                ("pm list packages --user 0",           "User-0-Apps"),
            ],
            "2": [
                ("ip -4 addr",                          "IPv4-Adressen"),
                ("ip route",                            "Routing-Tabelle"),
                ("ss -tnp 2>/dev/null | head -30",      "TCP-Verbindungen"),
                ("netstat -tulnp 2>/dev/null | head -20", "Ports offen"),
                ("dumpsys wifi 2>/dev/null | grep -E 'SSID|rssi|ipAddress' | head -10", "WLAN-Status"),
                ("cat /proc/net/tcp 2>/dev/null | head -20", "/proc/net/tcp"),
            ],
            "3": [
                ("ps -A 2>/dev/null | head -40",        "Alle Prozesse"),
                ("ps -A 2>/dev/null | wc -l",           "Prozess-Anzahl"),
                ("top -n 1 -b 2>/dev/null | head -30",  "Top-Prozesse"),
                ("cat /proc/meminfo 2>/dev/null | head -20", "Speicher-Info"),
                ("cat /proc/cpuinfo 2>/dev/null | head -30",  "CPU-Info"),
            ],
            "4": [
                ("su -c 'id' 2>/dev/null",              "Root-Test (id)"),
                ("su -c 'getenforce' 2>/dev/null",       "SELinux-Status"),
                ("su -c 'cat /proc/net/tcp6' 2>/dev/null | head -20", "TCP6-Verbindungen (root)"),
                ("su -c 'ls /data/data' 2>/dev/null | head -20", "App-Daten (root)"),
            ],
            "5": [
                ("ls -la /sdcard/ 2>/dev/null | head -20", "SD-Card Inhalt"),
                ("find /sdcard/ -name '*.apk' 2>/dev/null | head -10", "APKs auf SD"),
                ("df -h 2>/dev/null",                   "Speicher-Übersicht"),
                ("ls /data/data 2>/dev/null | wc -l",   "App-Ordner /data/data"),
            ],
            "6": [
                ("getprop | grep ro.product 2>/dev/null", "Produkt-Props"),
                ("getprop | grep ro.build 2>/dev/null", "Build-Props"),
                ("dumpsys battery 2>/dev/null | head -20", "Batterie-Info"),
                ("uname -a 2>/dev/null",                "Kernel-Version"),
                ("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null", "CPU-Frequenz"),
            ],
            "7": [
                ("am start -n com.android.settings/.Settings 2>/dev/null", "Einstellungen öffnen"),
                ("am start -a android.intent.action.VIEW -d 'https://google.de' 2>/dev/null", "Browser öffnen"),
                ("am force-stop com.android.chrome 2>/dev/null",  "Chrome beenden"),
                ("am broadcast -a android.intent.action.AIRPLANE_MODE 2>/dev/null", "Flugmodus-Broadcast"),
            ],
            "8": [
                ("dumpsys battery 2>/dev/null",         "Voll-Batteriestatus"),
                ("dumpsys deviceidle 2>/dev/null | grep -E 'enabled|light|deep' | head -10", "Doze-Status"),
                ("dumpsys power 2>/dev/null | grep -E 'mWakefulness|mHolding|Wake Lock' | head -15", "Wakelock-Status"),
                ("settings get global low_power 2>/dev/null",  "Energiesparmodus"),
            ],
            "9": [
                ("wm size 2>/dev/null && wm density 2>/dev/null", "Display-Größe & DPI"),
                ("screencap -p /sdcard/screenshot.png 2>/dev/null && echo 'OK'", "Screenshot machen"),
                ("screenrecord --time-limit 10 /sdcard/rec.mp4 2>/dev/null &", "10s Aufnahme (BG)"),
                ("settings get system brightness 2>/dev/null", "Helligkeit"),
            ],
            "10": [
                ("settings get secure android_id 2>/dev/null",  "Android-ID"),
                ("getprop ro.crypto.state 2>/dev/null",         "Verschlüsselung"),
                ("getprop ro.boot.verifiedbootstate 2>/dev/null", "Verified Boot"),
                ("settings get secure user_setup_complete 2>/dev/null", "Setup abgeschlossen"),
                ("pm list features | grep fingerprint 2>/dev/null", "Fingerprint-Feature"),
            ],
        }
        entries = cats.get(cat, [])
        if not entries:
            return
        while True:
            ui.clear()
            options = [(str(i), f"{desc:35s}  {ui.GREY}{cmd[:50]}{ui.RESET}")
                       for i, (cmd, desc) in enumerate(entries, 1)]
            ch2 = ui.menu("Befehl ausführen", options, back_label="Zurück")
            if ch2 in ("back", "quit"):
                return
            try:
                idx = int(ch2) - 1
                cmd, desc = entries[idx]
                ui.info(f"Ausführen: {cmd}")
                result = self.execute(cmd, timeout=15)
                self._display_result(result)
                ui.pause()
            except (ValueError, IndexError):
                pass

    def _show_settings(self) -> None:
        """Interaktive Shell-Settings."""
        while True:
            ui.clear()
            ui.rule("⚙️  SHELL SETTINGS", ui.BCYAN)
            print(f"\n  Session-Start: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Commands in History: {len(self.command_history)}")
            print()
            ch = ui.menu("Einstellung", [
                ("1", "📊 Session-Statistik"),
                ("2", "🗑  History löschen"),
                ("3", "💾 History als JSON exportieren"),
                ("4", "⏱  Timeout ändern"),
            ], back_label="Zurück")
            if ch in ("back", "quit"):
                return
            if ch == "1":
                self._session_stats()
            elif ch == "2":
                if ui.confirm("History wirklich löschen?", False):
                    self.command_history.clear()
                    ui.ok("History gelöscht.")
            elif ch == "3":
                self._export_history()
            elif ch == "4":
                val = ui.ask("Neuer Timeout in Sekunden (1-120)")
                try:
                    t = int(val)
                    if 1 <= t <= 120:
                        ui.ok(f"Timeout → {t}s (gilt für nächste Befehle)")
                except ValueError:
                    pass
            ui.pause()

    def _session_stats(self) -> None:
        """Session-Statistiken."""
        print()
        total = len(self.command_history)
        ok_cnt = sum(1 for r in self.command_history if r.success)
        fail_cnt = total - ok_cnt
        avg_ms = (sum(r.duration_ms for r in self.command_history) / total) if total else 0
        ui.kv("Befehle gesamt", str(total))
        ui.kv("Erfolgreich", f"{ok_cnt} ({ok_cnt*100//total if total else 0}%)")
        ui.kv("Fehlgeschlagen", str(fail_cnt))
        ui.kv("Ø Ausführungszeit", f"{avg_ms:.0f}ms")
        if self.command_history:
            slowest = max(self.command_history, key=lambda r: r.duration_ms)
            ui.kv("Langsamster", f"{slowest.command[:50]} ({slowest.duration_ms:.0f}ms)")

    def _export_history(self) -> None:
        """History als JSON speichern."""
        import os
        out = os.path.expanduser(
            f"~/Schreibtisch/Androidpanzer/adb_shell/history_{self.session_start.strftime('%Y%m%d_%H%M%S')}.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        data = [{"cmd": r.command, "exit": r.exit_code, "stdout": r.stdout[:500],
                 "ms": r.duration_ms, "ts": r.timestamp}
                for r in self.command_history]
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        ui.ok(f"Exportiert: {out}")

    def _logcat_stream(self) -> None:
        """Live-Logcat (max 200 Zeilen, dann Pause)."""
        import subprocess as sp
        ui.clear()
        ui.rule("📋 LOGCAT LIVE", ui.BCYAN)
        print(f"  {ui.GREY}Filter: [leer = alle | E = nur Errors | TAG:V = bestimmtes Tag]{ui.RESET}\n")
        filt = ui.ask("Filter (leer = alle, 'E' = Errors, 'q' = abbrechen)").strip()
        if filt.lower() == "q":
            return
        args = ["adb", "logcat", "-v", "time"]
        if filt.upper() == "E":
            args += ["*:E"]
        elif filt:
            args += [filt]
        ui.info("Logcat läuft … STRG+C zum Beenden\n")
        try:
            proc = sp.Popen(args, stdout=sp.PIPE, stderr=sp.DEVNULL, text=True)
            count = 0
            for line in proc.stdout:  # type: ignore
                lvl = line[19:20] if len(line) > 20 else ""
                col = {
                    "E": ui.BRED, "W": ui.BYELLOW, "I": ui.BGREEN,
                    "D": ui.GREY, "F": ui.BLOOD
                }.get(lvl, ui.RESET)
                print(f"{col}{line.rstrip()}{ui.RESET}")
                count += 1
                if count >= 500:
                    ui.warn("500 Zeilen – Pausiert (Enter = weiter, q = Ende)")
                    if input().lower() == "q":
                        break
                    count = 0
        except KeyboardInterrupt:
            pass
        finally:
            try:
                proc.terminate()
            except Exception:
                pass

    def _root_shell(self) -> None:
        """Root-Shell via su (falls vorhanden)."""
        ui.clear()
        ui.rule("🔑 ROOT SHELL (su)", ui.BYELLOW)
        test = self.adb.shell("su -c 'id' 2>/dev/null").strip()
        if "root" not in test.lower():
            ui.err("Kein Root-Zugriff (su nicht gefunden oder verweigert).")
            ui.info("Magisk, SuperSU oder KernelSU installieren.")
            ui.pause(); return
        ui.ok(f"Root verfügbar: {test}")
        print(f"\n  {ui.GREY}Root-Befehle eingeben (ohne 'su -c'). 'exit' beendet.{ui.RESET}\n")
        while True:
            try:
                cmd = input("  root# ").strip()
                if not cmd:
                    continue
                if cmd.lower() == "exit":
                    break
                out = self.adb.shell(f"su -c '{cmd}' 2>&1").strip()
                if out:
                    print(f"\n{ui.GREY}{out[:1000]}{ui.RESET}\n")
            except KeyboardInterrupt:
                break

    def _app_manager(self) -> None:
        """App-Manager – installieren, deinstallieren, aktivieren/deaktivieren."""
        while True:
            ui.clear()
            ui.rule("📱 APP-MANAGER", ui.BCYAN)
            ch = ui.menu("Aktion", [
                ("1", "📋 Alle Apps auflisten    (pm list packages)"),
                ("2", "🗑  App deinstallieren"),
                ("3", "🚫 App deaktivieren       (pm disable-user)"),
                ("4", "✅ App aktivieren         (pm enable)"),
                ("5", "📦 APK installieren       (adb install)"),
                ("6", "🔍 App-Info               (dumpsys package)"),
            ], back_label="Zurück")
            if ch in ("back", "quit"):
                return
            if ch == "1":
                result = self.execute("pm list packages -3 2>/dev/null")
                self._display_result(result)
            elif ch == "2":
                pkg = ui.ask("Paketname (z.B. com.example.app)").strip()
                if pkg:
                    result = self.execute(f"pm uninstall --user 0 {pkg} 2>&1")
                    self._display_result(result)
            elif ch == "3":
                pkg = ui.ask("Paketname").strip()
                if pkg:
                    result = self.execute(f"pm disable-user --user 0 {pkg} 2>&1")
                    self._display_result(result)
            elif ch == "4":
                pkg = ui.ask("Paketname").strip()
                if pkg:
                    result = self.execute(f"pm enable {pkg} 2>&1")
                    self._display_result(result)
            elif ch == "5":
                path = ui.ask("Pfad zur APK-Datei (lokal auf diesem PC)").strip()
                if path:
                    import subprocess as sp
                    ui.info(f"Installiere: {path}")
                    sp.run(["adb", "install", "-r", path])
            elif ch == "6":
                pkg = ui.ask("Paketname").strip()
                if pkg:
                    result = self.execute(f"dumpsys package {pkg} 2>/dev/null")
                    self._display_result(result)
            ui.pause()

    def show_shell_menu(self, adb: Optional[ADB] = None) -> None:
        """Zeige Shell Menü – maximal ausgebaut."""
        if adb:
            self.adb = adb

        while True:
            ui.clear()
            ui.rule("🐚 ADB SHELL MANAGER", ui.BCYAN)
            print()

            entries = [
                ("1",  "🐚 Interactive Shell       (freie Befehlseingabe)"),
                ("2",  "📊 Device Info             (Props, RAM, CPU, Storage)"),
                ("3",  "📋 Command History         (letzte 20 Befehle)"),
                ("4",  "📝 Script ausführen        (mehrzeiliges ADB-Script)"),
                ("5",  "🔍 Erweiterte Befehle      (Pakete, Netz, Prozesse, Root …)"),
                ("6",  "⚙️  Shell-Einstellungen    (Stats, Export, Timeout)"),
                ("7",  "📋 Logcat Live             (Echtzeit-Gerätelog)"),
                ("8",  "🔑 Root-Shell              (su-Befehle, falls Root vorhanden)"),
                ("9",  "📱 App-Manager             (install/uninstall/disable)"),
                ("10", "💾 ADB pull                (Datei/Ordner vom Gerät ziehen)"),
                ("11", "📤 ADB push                (Datei aufs Gerät schieben)"),
                ("12", "📸 Screenshot              (screencap → auf PC ziehen)"),
            ]

            ch = ui.menu("ADB Shell Optionen", entries, back_label="Zurück")

            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.interactive_shell()
            elif ch == "2":
                self._show_device_info()
                ui.pause()
            elif ch == "3":
                self._show_history_menu()
                ui.pause()
            elif ch == "4":
                self._execute_script_menu()
                ui.pause()
            elif ch == "5":
                self._show_advanced_commands()
            elif ch == "6":
                self._show_settings()
            elif ch == "7":
                self._logcat_stream()
                ui.pause()
            elif ch == "8":
                self._root_shell()
                ui.pause()
            elif ch == "9":
                self._app_manager()
            elif ch == "10":
                src = ui.ask("Pfad auf dem Gerät (z.B. /sdcard/DCIM)").strip()
                dst = ui.ask("Ziel auf diesem PC (z.B. ./backup/)").strip() or "."
                if src:
                    import subprocess as sp
                    sp.run(["adb", "pull", src, dst])
                ui.pause()
            elif ch == "11":
                src = ui.ask("Lokale Datei (Pfad auf diesem PC)").strip()
                dst = ui.ask("Ziel auf dem Gerät (z.B. /sdcard/)").strip() or "/sdcard/"
                if src:
                    import subprocess as sp
                    sp.run(["adb", "push", src, dst])
                ui.pause()
            elif ch == "12":
                self.adb.shell("screencap -p /sdcard/_apz_screenshot.png 2>/dev/null")
                import subprocess as sp
                sp.run(["adb", "pull", "/sdcard/_apz_screenshot.png", "."])
                self.adb.shell("rm /sdcard/_apz_screenshot.png 2>/dev/null")
                ui.ok("Screenshot gespeichert: ./_apz_screenshot.png")
                ui.pause()


def menu(adb: ADB) -> None:
    """ADB Shell Menü."""
    shell = ADBShell(adb)
    shell.show_shell_menu(adb)
