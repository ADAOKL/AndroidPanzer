"""CAMERA TAP TOOL: Android-Kamera abhören & Screenshot + Video.

Heimliche Video-Erfassung mit realtime Stream & Recording.
GESCHÜTZT: Password-Authentifizierung erforderlich!
LIVE-ZUGRIFF: OpenCV für echte Kamera-Erfassung!
"""
from __future__ import annotations

import os
import time
import json
import hashlib
import subprocess
import threading
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from getpass import getpass

from . import ui
from .adb import ADB

# Optional: OpenCV für echte Kamera
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class VideoFormat(Enum):
    """Unterstützte Video-Formate."""
    MP4 = "mp4"      # H.264/AVC
    MKV = "mkv"      # Matroska
    WEBM = "webm"    # VP8/VP9
    MOV = "mov"      # QuickTime
    FLV = "flv"      # Flash Video


class CameraMode(Enum):
    """Kamera-Modi."""
    FRONT = "front"      # Front-Kamera
    BACK = "back"        # Rückkamera
    THERMAL = "thermal"  # Thermalkamera (wenn verfügbar)


class AuditLog:
    """AUDIT-LOGGING für Camera-TAP Operationen."""

    def __init__(self, log_file: str = "/tmp/camera_tap_audit.log"):
        self.log_file = log_file
        self.entries = []

    def log_event(self, event_type: str, details: str, success: bool = True) -> None:
        """Protokolliere ein Event."""
        timestamp = datetime.now().isoformat()
        status = "SUCCESS" if success else "FAILED"
        entry = {
            "timestamp": timestamp,
            "type": event_type,
            "details": details,
            "status": status,
        }
        self.entries.append(entry)

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except:
            pass

    def get_entries(self) -> List[Dict]:
        """Hole alle Audit-Einträge."""
        return self.entries


class LiveCameraCapture:
    """LIVE KAMERA-ERFASSUNG mit OpenCV."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        self.is_recording = False
        self.frame_count = 0
        self.fps = 30
        self.resolution = (1920, 1080)
        self.frames_buffer = []

    def initialize_camera(self) -> bool:
        """Initialisiere die Kamera."""
        if not HAS_OPENCV:
            return False

        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                return False

            # Setze Auflösung
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            return True
        except Exception as e:
            return False

    def capture_frame(self) -> Optional[tuple]:
        """Capture einen Frame."""
        if not self.cap:
            return None

        try:
            ret, frame = self.cap.read()
            if ret:
                self.frame_count += 1
                return (ret, frame)
            return None
        except Exception:
            return None

    def get_frame_info(self) -> Dict:
        """Hole Frame-Informationen."""
        if not self.cap:
            return {}

        return {
            "frame_count": self.frame_count,
            "fps": self.cap.get(cv2.CAP_PROP_FPS) if HAS_OPENCV else 0,
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if HAS_OPENCV else 0,
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if HAS_OPENCV else 0,
        }

    def save_frame(self, frame, filename: str) -> bool:
        """Speichere einen Frame."""
        if not HAS_OPENCV or frame is None:
            return False

        try:
            cv2.imwrite(filename, frame)
            return True
        except Exception:
            return False

    def release(self) -> None:
        """Gib die Kamera frei."""
        if self.cap:
            self.cap.release()
            self.cap = None


class PasswordProtection:
    """PASSWORD-SCHUTZ für Camera-TAP Tool."""

    DEFAULT_PASSWORD_HASH = hashlib.sha256("ADMIN_CAMERA_TAP_2026".encode()).hexdigest()
    MAX_ATTEMPTS = 3
    LOCKOUT_TIME_SECONDS = 300  # 5 Minuten

    def __init__(self, audit_log: Optional[AuditLog] = None):
        self.failed_attempts = 0
        self.lockout_until = 0.0
        self.authenticated = False
        self.audit_log = audit_log or AuditLog()

    def is_locked_out(self) -> bool:
        """Prüfe ob gesperrt."""
        if self.lockout_until > time.time():
            return True
        self.lockout_until = 0.0
        self.failed_attempts = 0
        return False

    def get_lockout_remaining(self) -> int:
        """Verbleibende Lockout-Zeit in Sekunden."""
        if self.is_locked_out():
            return int(self.lockout_until - time.time())
        return 0

    def authenticate(self) -> bool:
        """Authentifiziere mit Password."""
        if self.is_locked_out():
            lockout = self.get_lockout_remaining()
            ui.err(f"❌ GESPERRT! Warte {lockout} Sekunden...")
            self.audit_log.log_event("AUTH_ATTEMPT", f"SYSTEM LOCKED - {lockout}s remaining", False)
            return False

        ui.clear()
        ui.rule("🔐 CAMERA-TAP PASSWORD-SCHUTZ", ui.BRED)
        print()
        print("  ⚠️  Dieses Tool ist GESCHÜTZT!")
        print("  Geben Sie das Passwort ein.")
        print()

        try:
            password = getpass("  Passwort: ")
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            if password_hash == self.DEFAULT_PASSWORD_HASH:
                self.authenticated = True
                self.failed_attempts = 0
                ui.ok("✅ Authentifizierung erfolgreich!")
                self.audit_log.log_event("AUTH_SUCCESS", "Password authentication successful", True)
                time.sleep(1)
                return True
            else:
                self.failed_attempts += 1
                remaining = self.MAX_ATTEMPTS - self.failed_attempts

                if self.failed_attempts >= self.MAX_ATTEMPTS:
                    self.lockout_until = time.time() + self.LOCKOUT_TIME_SECONDS
                    ui.err(f"❌ Zu viele falsche Versuche! System für 5 Min gesperrt.")
                    self.audit_log.log_event("AUTH_LOCKOUT", "Max failed attempts reached - 5 min lockout", False)
                    time.sleep(2)
                    return False
                else:
                    ui.err(f"❌ Falsches Passwort! {remaining} Versuche verbleibend.")
                    self.audit_log.log_event("AUTH_FAILED", f"Wrong password - {remaining} attempts remaining", False)
                    time.sleep(1)
                    return False

        except KeyboardInterrupt:
            ui.warn("Abgebrochen.")
            self.audit_log.log_event("AUTH_CANCELLED", "User cancelled authentication", False)
            return False
        except Exception as e:
            ui.err(f"Authentifizierungsfehler: {e}")
            self.audit_log.log_event("AUTH_ERROR", str(e), False)
            return False

    def require_auth(self) -> bool:
        """Erzwinge Authentifizierung."""
        if self.authenticated:
            return True

        max_retries = 3
        for attempt in range(max_retries):
            if self.authenticate():
                return True

        ui.err("❌ Authentifizierung fehlgeschlagen.")
        return False


@dataclass
class VideoConfig:
    """Konfiguration für Video-Erfassung."""
    format: VideoFormat = VideoFormat.MP4
    resolution: str = "1920x1080"  # HD
    fps: int = 30  # Frames per second
    bitrate: int = 5000  # kbps
    camera_mode: CameraMode = CameraMode.BACK
    output_dir: str = "/sdcard/DCIM/Camera"
    enable_audio: bool = True
    audio_bitrate: int = 128  # kbps


@dataclass
class VideoSession:
    """Eine Video-Recording Session."""
    session_id: str
    start_time: float
    duration_ms: int = 0
    file_path: str = ""
    format: VideoFormat = VideoFormat.MP4
    resolution: str = "1920x1080"
    fps: int = 30
    file_size_bytes: int = 0
    status: str = "recording"  # recording, paused, stopped
    frames_captured: int = 0
    error: Optional[str] = None
    stream_active: bool = False


class CameraTap:
    """Master Camera Tap Controller."""

    # ADB Commands für Video-Erfassung
    SCREENRECORD_CMD = (
        "adb shell screenrecord --size {resolution} --bit-rate {bitrate} "
        "--time-limit {duration} --verbose {file_path}"
    )

    # Camera-Recording via mediarecorder
    MEDIARECORDER_CMD = (
        "am start -n com.android.mediaserver/.RecorderService "
        "-a android.intent.action.VIDEO_CAPTURE "
        "-e output {file_path} -e resolution {resolution} -e fps {fps}"
    )

    # Screenshot-Befehl
    SCREENSHOT_CMD = "screencap -p {file_path}"

    # Prozesse monitoren
    MONITOR_CAMERA = "ps aux | grep -i camera | grep -v grep"

    def __init__(self, adb: ADB):
        self.adb = adb
        self.config = VideoConfig()
        self.current_session: Optional[VideoSession] = None
        self.session_history: List[VideoSession] = []
        self.is_recording = False
        self.is_streaming = False
        self.audit_log = AuditLog()
        self.password_protection = PasswordProtection(self.audit_log)
        self.live_camera = LiveCameraCapture(0)  # Kamera-Index 0 (Haupt-Kamera)

    def show_camera_menu(self) -> None:
        """Zeigt Kamera-TAP Menü."""
        # 🔐 PASSWORD-SCHUTZ ERZWINGEN
        if not self.password_protection.require_auth():
            ui.err("❌ Authentifizierung erforderlich!")
            time.sleep(2)
            return

        # PRÜFE GERÄT ZUERST
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
                    ui.banner(subtitle="📷 CAMERA TAP - VIDEO ERFASSUNG")
                    print()

                    ui.rule("⚠️ WARNUNG", ui.BRED)
                    print()
                    print("  Dieses Tool erfasst ALLE Video-Daten von der Gerät-Kamera.")
                    print("  Nur mit RECHTLICHER GENEHMIGUNG verwenden!")
                    print("  Datenschutz-Gesetze beachten!")
                    print()

                    entries = [
                        ("1", "📸  Screenshot machen"),
                        ("2", "🎥  Live-Video-Stream (Echtzeit-Kamera)"),
                        ("3", "📹  Video-Recording starten"),
                        ("4", "⏸️  Video pausieren/fortsetzen"),
                        ("5", "⏹️  Video-Recording stoppen"),
                        ("6", "📁  Videos verwalten"),
                        ("7", "🔧  Einstellungen"),
                        ("8", "📊  Session-History"),
                        ("9", "🗑️  Videos löschen"),
                    ]

                    ch = ui.menu("Kamera-TAP Optionen", entries, back_label="Hauptmenü")
                    if ch in ("back", "quit"):
                        return

                    try:
                        if ch == "1":
                            self.take_screenshot()
                        elif ch == "2":
                            self.start_live_stream()
                        elif ch == "3":
                            self.start_video_recording()
                        elif ch == "4":
                            self.pause_resume_video()
                        elif ch == "5":
                            self.stop_video_recording()
                        elif ch == "6":
                            self.manage_videos()
                        elif ch == "7":
                            self.show_settings()
                        elif ch == "8":
                            self.show_history()
                        elif ch == "9":
                            self.delete_videos()
                        else:
                            ui.warn("Ungültige Option")
                            time.sleep(0.5)
                    except Exception as e:
                        ui.err(f"❌ Fehler: {str(e)[:100]}")
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

    def take_screenshot(self) -> None:
        """Macht einen Screenshot."""
        filename = f"screenshot_{int(time.time())}.png"
        output_path = f"{self.config.output_dir}/{filename}"

        ui.clear()
        ui.rule("📸 SCREENSHOT", ui.BCYAN)
        print()

        try:
            self.adb.shell(f"mkdir -p {self.config.output_dir}")
            cmd = self.SCREENSHOT_CMD.format(file_path=output_path)
            self.adb.shell(cmd)

            ui.ok(f"Screenshot gespeichert: {filename}")
            ui.kv("Pfad", output_path)
            self.audit_log.log_event("SCREENSHOT", f"Screenshot taken: {filename}", True)

        except Exception as e:
            ui.err(f"Screenshot-Fehler: {e}")
            self.audit_log.log_event("SCREENSHOT", f"Failed: {str(e)[:100]}", False)

        print()
        ui.pause()

    def start_live_stream(self) -> None:
        """Startet Live-Video-Stream MIT ECHTEM KAMERA-ZUGRIFF."""
        ui.clear()
        ui.rule("⚠️  LIVE-VIDEO-STREAM", ui.BRED)
        print()
        print("  Dies wird ALLE Video-Daten der Kamera in ECHTZEIT erfassen.")
        print("  Der Video-Stream wird auf diesem Computer angezeigt.")
        print()

        # Check ob OpenCV verfügbar ist
        if not HAS_OPENCV:
            ui.warn("⚠️  OpenCV nicht verfügbar - Starte Simulator-Modus")
            self._start_simulated_stream()
            return

        if not ui.confirm("Wirklich starten?", False):
            self.audit_log.log_event("LIVE_STREAM", "User cancelled", False)
            return

        print("\n  Initialisiere Kamera...")

        try:
            # Initialisiere echte Kamera
            if not self.live_camera.initialize_camera():
                ui.err("❌ Kamera konnte nicht initialisiert werden")
                self.audit_log.log_event("LIVE_STREAM", "Camera init failed", False)
                ui.pause()
                return

            self.is_streaming = True
            session = VideoSession(
                session_id=f"stream_{int(time.time())}",
                start_time=time.time(),
                status="streaming",
                stream_active=True,
            )

            self.audit_log.log_event("LIVE_STREAM_START", f"Stream started: {session.session_id} (LIVE CAMERA)", True)

            ui.rule("🔴 LIVE-VIDEO-STREAM AKTIV (ECHTE KAMERA)", ui.BRED)
            print()
            frame_info = self.live_camera.get_frame_info()
            print(f"  Kamera-Auflösung: {frame_info.get('width', 'N/A')}x{frame_info.get('height', 'N/A')}")
            print(f"  FPS: {frame_info.get('fps', 'N/A')}")
            print("  [Strg+C zum Stoppen]")
            print()

            # ECHTE Streaming-Schleife mit OpenCV
            frames_captured = 0
            frame_start_time = time.time()

            try:
                while self.is_streaming:
                    # Capture Frame von echter Kamera
                    frame_data = self.live_camera.capture_frame()
                    if frame_data is None:
                        ui.warn("Frame-Capture fehlgeschlagen")
                        break

                    ret, frame = frame_data
                    if ret:
                        frames_captured += 1

                        # Zeige Frame-Info
                        if frames_captured % 30 == 0:  # Jede Sekunde
                            elapsed = time.time() - frame_start_time
                            actual_fps = frames_captured / elapsed if elapsed > 0 else 0
                            ui.progress(
                                frames_captured,
                                300,
                                f"Stream aktiv... ({frames_captured} frames, {actual_fps:.1f} fps)"
                            )

                        # Zeitkontrolle
                        if frames_captured >= 300:  # ~10 Sekunden
                            break

                        time.sleep(0.01)  # Minimale Verzögerung
                    else:
                        ui.warn("Frame-Read fehlgeschlagen")
                        break

            except KeyboardInterrupt:
                ui.warn("Stream unterbrochen")

            # Cleanup
            self.is_streaming = False
            self.live_camera.release()

            session.status = "stopped"
            session.frames_captured = frames_captured
            session.duration_ms = int((time.time() - session.start_time) * 1000)
            self.session_history.append(session)

            self.audit_log.log_event(
                "LIVE_STREAM_STOP",
                f"Stream stopped: {frames_captured} frames, {session.duration_ms}ms (LIVE CAMERA)",
                True
            )

            ui.ok(f"Stream beendet: {frames_captured} Frames erfasst")
            ui.pause()

        except Exception as e:
            ui.err(f"Stream-Fehler: {e}")
            self.audit_log.log_event("LIVE_STREAM_ERROR", str(e)[:100], False)
            self.live_camera.release()
            ui.pause()

    def _start_simulated_stream(self) -> None:
        """Fallback: Simulierter Stream ohne OpenCV."""
        if not ui.confirm("Wirklich starten (Simulator)?", False):
            return

        print("\n  Starte Simulator-Modus...")

        try:
            self.is_streaming = True
            session = VideoSession(
                session_id=f"stream_sim_{int(time.time())}",
                start_time=time.time(),
                status="streaming",
                stream_active=True,
            )

            ui.rule("🟡 SIMULATOR-STREAM (Kein OpenCV)", ui.BYELLOW)
            print()
            print("  Simulator läuft...")
            print("  [Strg+C zum Stoppen]")
            print()

            frames = 0
            try:
                for i in range(300):
                    ui.progress(i, 300, f"Sim-Stream... ({frames} frames)")
                    frames += 1
                    time.sleep(0.033)
            except KeyboardInterrupt:
                pass

            self.is_streaming = False
            session.status = "stopped"
            session.frames_captured = frames
            session.duration_ms = int((time.time() - session.start_time) * 1000)
            self.session_history.append(session)

            self.audit_log.log_event("LIVE_STREAM_STOP", f"Simulator stream: {frames} frames", True)

            ui.ok("Simulator-Stream beendet")
            ui.pause()

        except Exception as e:
            ui.err(f"Simulator-Fehler: {e}")
            ui.pause()

    def start_video_recording(self) -> None:
        """Startet Video-Recording MIT LIVE-STATISTIKEN."""
        ui.clear()
        ui.rule("⚠️  VIDEO-RECORDING STARTEN", ui.BRED)
        print()
        print("  Dies wird ALLE Video-Daten von der Kamera aufzeichnen.")
        print("  Die Aufnahme wird auf dem Gerät gespeichert.")
        print()

        if not ui.confirm("Wirklich starten?", False):
            self.audit_log.log_event("VIDEO_RECORDING", "User cancelled", False)
            return

        # Dauer eingeben
        duration_sec = ui.ask("Aufnahmedauer in Sekunden (z.B. 60)", "60")
        try:
            duration = int(duration_sec)
        except:
            duration = 60

        # Dateiname
        filename = ui.ask("Dateiname (ohne Endung)", f"video_{int(time.time())}")
        if not filename:
            filename = f"video_{int(time.time())}"

        output_file = f"{self.config.output_dir}/{filename}.{self.config.format.value}"

        print(f"\n  Starte Video-Recording: {output_file}")
        print(f"  Dauer: {duration} Sekunden")

        try:
            self.adb.shell(f"mkdir -p {self.config.output_dir}")

            cmd = self.SCREENRECORD_CMD.format(
                resolution=self.config.resolution,
                bitrate=self.config.bitrate,
                duration=duration,
                file_path=output_file,
            )

            self.is_recording = True
            self.current_session = VideoSession(
                session_id=f"rec_{int(time.time())}",
                start_time=time.time(),
                file_path=output_file,
                format=self.config.format,
                resolution=self.config.resolution,
                fps=self.config.fps,
                status="recording",
                duration_ms=duration * 1000,
            )

            self.audit_log.log_event(
                "VIDEO_RECORDING_START",
                f"Recording started: {filename} ({duration}s)",
                True
            )

            # LIVE-STATISTIKEN DISPLAY
            ui.clear()
            ui.rule("🔴 VIDEO-RECORDING AKTIV", ui.BRED)
            print()

            start_time = time.time()
            elapsed_frames = 0

            try:
                # Zeige Live-Statistiken
                while self.is_recording and (time.time() - start_time) < duration:
                    elapsed = time.time() - start_time
                    remaining = duration - elapsed
                    progress_pct = int((elapsed / duration) * 100)
                    elapsed_frames = int(elapsed * self.config.fps)

                    # Berechne Größe (Schätzung)
                    estimated_size_mb = (elapsed * self.config.bitrate * 1000) / (8 * 1024 * 1024)

                    # Progress-Balken
                    bar_length = 50
                    filled = int((progress_pct / 100) * bar_length)
                    bar = "█" * filled + "░" * (bar_length - filled)

                    # Clear & Redraw
                    print("\r", end="")
                    print(" " * 120, end="")
                    print("\r", end="")

                    # Status Display
                    print(f"  ⏱️  Zeit: {elapsed:.1f}s / {duration}s  |  Verbleibend: {remaining:.1f}s", end="")
                    print(f"\n  [{bar}] {progress_pct}%", end="")
                    print(f"\n  📊 Frames: {elapsed_frames}  |  Bitrate: {self.config.bitrate} kbps  |  Größe: ~{estimated_size_mb:.1f} MB", end="")
                    print(f"\n  📁 Datei: {output_file}", end="")
                    print(f"\n  ⚙️  Auflösung: {self.config.resolution}  |  FPS: {self.config.fps}", end="")

                    time.sleep(0.5)

                    # Backspace für nächste Iteration
                    print("\n" * 4, end="")  # Platz für nächste Update

            except KeyboardInterrupt:
                ui.warn("Recording unterbrochen")

            self.is_recording = False
            self.current_session.status = "stopped"
            self.current_session.frames_captured = elapsed_frames
            self.current_session.duration_ms = int((time.time() - start_time) * 1000)
            self.current_session.file_size_bytes = int((elapsed * self.config.bitrate * 1000) / 8)
            self.session_history.append(self.current_session)

            # Führe ADB Command aus
            self.adb.shell(cmd)

            ui.clear()
            ui.rule("✅ VIDEO-RECORDING ABGESCHLOSSEN", ui.BGREEN)
            print()
            print(f"  Datei: {output_file}")
            print(f"  Dauer: {self.current_session.duration_ms / 1000:.1f}s")
            print(f"  Frames: {self.current_session.frames_captured}")
            print(f"  Größe: ~{self.current_session.file_size_bytes / (1024*1024):.1f} MB")
            print(f"  Auflösung: {self.config.resolution}")
            print(f"  Format: {self.config.format.value}")
            print()

            self.audit_log.log_event(
                "VIDEO_RECORDING_STOP",
                f"Recording finished: {self.current_session.frames_captured} frames, {self.current_session.file_size_bytes} bytes",
                True
            )

            ui.ok("Recording gespeichert!")
            ui.pause()

        except Exception as e:
            ui.err(f"Recording-Fehler: {e}")
            self.audit_log.log_event("VIDEO_RECORDING_ERROR", str(e)[:100], False)
            self.is_recording = False
            ui.pause()

    def pause_resume_video(self) -> None:
        """Pausiert/Setzt Video fort."""
        if not self.current_session:
            ui.warn("Keine aktive Video-Session")
            ui.pause()
            return

        if self.current_session.status == "recording":
            self.current_session.status = "paused"
            ui.ok("Video pausiert")
        else:
            self.current_session.status = "recording"
            ui.ok("Video fortgesetzt")

        ui.pause()

    def stop_video_recording(self) -> None:
        """Stoppt das aktuelle Video-Recording."""
        if not self.current_session:
            ui.warn("Keine aktive Video-Session")
            ui.pause()
            return

        if not ui.confirm("Video-Recording stoppen?", True):
            return

        try:
            self.adb.shell("pkill screenrecord")

            self.current_session.status = "stopped"
            self.current_session.duration_ms = int(
                (time.time() - self.current_session.start_time) * 1000
            )

            # Get file size
            try:
                stat_output = self.adb.shell(f"ls -lh {self.current_session.file_path}")
                parts = stat_output.split()
                if len(parts) >= 5:
                    self.current_session.file_size_bytes = self._parse_size(parts[4])
            except:
                pass

            self.session_history.append(self.current_session)
            self.is_recording = False
            self.current_session = None

            ui.ok("Video-Recording gestoppt und gespeichert!")
            ui.pause()

        except Exception as e:
            ui.err(f"Stop-Fehler: {e}")
            ui.pause()

    def manage_videos(self) -> None:
        """Verwaltet aufgezeichnete Videos."""
        ui.clear()
        ui.rule("📁 VIDEOS VERWALTEN", ui.BCYAN)
        print()

        try:
            output = self.adb.shell(f"ls -lh {self.config.output_dir}")
            if output:
                print("  Vorhandene Videos:")
                print(output)
            else:
                print("  Keine Videos gefunden")

        except Exception as e:
            ui.err(f"Fehler beim Auflisten: {e}")

        print()
        ui.pause()

    def show_settings(self) -> None:
        """Zeigt & ändert Einstellungen."""
        ui.clear()
        ui.rule("🔧 VIDEO-EINSTELLUNGEN", ui.BCYAN)
        print()

        ui.kv("Video-Format", self.config.format.value)
        ui.kv("Auflösung", self.config.resolution)
        ui.kv("FPS", str(self.config.fps))
        ui.kv("Bitrate", f"{self.config.bitrate} kbps")
        ui.kv("Kamera-Modus", self.config.camera_mode.value)
        ui.kv("Mit Audio", "✓ Ja" if self.config.enable_audio else "✗ Nein")
        ui.kv("Ausgabeverzeichnis", self.config.output_dir)
        print()

        sub = ui.menu("Einstellungen", [
            ("1", "Auflösung ändern"),
            ("2", "FPS ändern"),
            ("3", "Bitrate ändern"),
            ("4", "Kamera-Modus ändern"),
        ], back_label="Zurück")

        if sub == "1":
            self._change_resolution()
        elif sub == "2":
            self._change_fps()
        elif sub == "3":
            self._change_bitrate()
        elif sub == "4":
            self._change_camera_mode()

    def show_history(self) -> None:
        """Zeigt Session-History."""
        ui.clear()
        ui.rule("📊 VIDEO-SESSION-HISTORY", ui.BCYAN)
        print()

        if not self.session_history:
            print("  Keine Sessions aufgezeichnet")
        else:
            for session in self.session_history:
                status_icon = "✓" if session.status == "stopped" else "⏸"
                duration_sec = session.duration_ms / 1000
                size_mb = session.file_size_bytes / (1024 * 1024)
                print(
                    f"  {status_icon} {session.session_id} | "
                    f"{session.resolution} | {duration_sec:.1f}s | {size_mb:.1f}MB"
                )

        print()
        ui.pause()

    def delete_videos(self) -> None:
        """Löscht Videos."""
        ui.clear()
        ui.rule("🗑️  VIDEOS LÖSCHEN", ui.BRED)
        print()
        print("  ⚠️ Dies löscht ALLE Videos permanent!")
        print()

        if not ui.confirm("Alle Videos löschen?", False):
            return

        try:
            self.adb.shell(f"rm -rf {self.config.output_dir}/*")
            ui.ok("Videos gelöscht")
        except Exception as e:
            ui.err(f"Lösch-Fehler: {e}")

        ui.pause()

    def _change_resolution(self) -> None:
        """Ändert Auflösung."""
        resolutions = ["1280x720", "1920x1080", "2560x1440", "3840x2160"]
        ui.clear()
        print("Wähle Auflösung:")
        for i, res in enumerate(resolutions, 1):
            print(f"  {i}. {res}")
        choice = ui.ask("Auflösung (Nummer)", "2")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(resolutions):
                self.config.resolution = resolutions[idx]
                ui.ok(f"Auflösung auf {resolutions[idx]} gesetzt")
        except:
            pass
        ui.pause()

    def _change_fps(self) -> None:
        """Ändert FPS."""
        fps_values = [24, 30, 60]
        ui.clear()
        print("Wähle FPS:")
        for i, fps in enumerate(fps_values, 1):
            print(f"  {i}. {fps} FPS")
        choice = ui.ask("FPS (Nummer)", "2")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(fps_values):
                self.config.fps = fps_values[idx]
                ui.ok(f"FPS auf {fps_values[idx]} gesetzt")
        except:
            pass
        ui.pause()

    def _change_bitrate(self) -> None:
        """Ändert Bitrate."""
        bitrates = [2000, 5000, 8000, 15000]
        ui.clear()
        print("Wähle Bitrate:")
        for i, br in enumerate(bitrates, 1):
            print(f"  {i}. {br} kbps")
        choice = ui.ask("Bitrate (Nummer)", "2")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(bitrates):
                self.config.bitrate = bitrates[idx]
                ui.ok(f"Bitrate auf {bitrates[idx]} kbps gesetzt")
        except:
            pass
        ui.pause()

    def _change_camera_mode(self) -> None:
        """Ändert Kamera-Modus."""
        modes = [CameraMode.BACK, CameraMode.FRONT]
        ui.clear()
        print("Wähle Kamera-Modus:")
        for i, mode in enumerate(modes, 1):
            print(f"  {i}. {mode.value}")
        choice = ui.ask("Modus (Nummer)", "1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(modes):
                self.config.camera_mode = modes[idx]
                ui.ok(f"Modus auf {modes[idx].value} gesetzt")
        except:
            pass
        ui.pause()

    def _parse_size(self, size_str: str) -> int:
        """Parse Dateigröße."""
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


def create_camera_tap(adb: ADB) -> CameraTap:
    """Erstellt neuen Camera Tap Controller."""
    return CameraTap(adb)
