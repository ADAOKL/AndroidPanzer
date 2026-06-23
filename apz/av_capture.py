"""AUDIO-VIDEO CAPTURE SYSTEM: FFmpeg + V4L2 + SoundDevice

Professionelle Live-Kamera & Mikrofon-Erfassung mit:
- FFmpeg Video-Streaming (USB-Kameras)
- V4L2 Kamera-Konfiguration
- SoundDevice Audio-Streaming
- Audio/Video Synchronisation
- Motion Detection
"""
from __future__ import annotations

import os
import sys
import json
import time
import subprocess
import threading
import tempfile
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# Optionale Dependencies
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


class CameraFormat(Enum):
    """V4L2 Kamera-Formate."""
    MJPEG = "MJPEG"
    YUYV = "YUYV"
    RGB24 = "RGB24"
    H264 = "H264"


@dataclass
class CameraInfo:
    """Informationen über eine erkannte Kamera."""
    device_path: str
    device_name: str
    index: int
    formats: List[str] = field(default_factory=list)
    resolutions: List[Tuple[int, int]] = field(default_factory=list)
    active: bool = False


@dataclass
class AudioInfo:
    """Informationen über Audio-Geräte."""
    device_id: int
    device_name: str
    sample_rate: int = 16000
    channels: int = 1
    active: bool = False


class V4L2Controller:
    """V4L2 Kamera-Kontrolle (für Linux)."""

    def __init__(self):
        self.cameras: List[CameraInfo] = []
        self.has_v4l2 = self._check_v4l2_tools()

    def _check_v4l2_tools(self) -> bool:
        """Prüfe ob v4l2-ctl verfügbar ist."""
        try:
            result = subprocess.run(
                ["which", "v4l2-ctl"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False

    def list_devices(self) -> List[CameraInfo]:
        """Finde alle V4L2 Kameras."""
        if not self.has_v4l2:
            return []

        try:
            result = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True,
                text=True,
                timeout=5
            )

            cameras = []
            lines = result.stdout.split("\n")
            current_name = ""
            device_count = 0

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("*") or ":" in line:
                    current_name = line.replace("*", "").strip()
                elif "/dev/video" in line:
                    device_path = line.split()[0]
                    camera = CameraInfo(
                        device_path=device_path,
                        device_name=current_name or f"Camera {device_count}",
                        index=device_count
                    )
                    cameras.append(camera)
                    device_count += 1

            self.cameras = cameras
            return cameras
        except Exception as e:
            return []

    def get_formats(self, device_path: str) -> List[str]:
        """Hole unterstützte Formate für Kamera."""
        if not self.has_v4l2:
            return []

        try:
            result = subprocess.run(
                ["v4l2-ctl", "-d", device_path, "--list-formats-ext"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.split("\n")[:10]
        except:
            return []

    def set_resolution(self, device_path: str, width: int, height: int) -> bool:
        """Setze Kamera-Auflösung."""
        if not self.has_v4l2:
            return False

        try:
            subprocess.run(
                ["v4l2-ctl", "-d", device_path, "-v", f"width={width},height={height}"],
                capture_output=True,
                timeout=5
            )
            return True
        except:
            return False


class FFmpegCapture:
    """FFmpeg-basiertes Video-Capture."""

    def __init__(self, device_path: str = "/dev/video0", resolution: Tuple[int, int] = (1920, 1080), fps: int = 30):
        self.device_path = device_path
        self.resolution = resolution
        self.fps = fps
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.frame_count = 0

    def start_stream(self, output_path: Optional[str] = None) -> bool:
        """Starte FFmpeg Stream."""
        try:
            width, height = self.resolution

            cmd = [
                "ffmpeg",
                "-f", "v4l2",
                "-i", self.device_path,
                "-vf", f"fps={self.fps}",
                "-s", f"{width}x{height}",
                "-pix_fmt", "yuv420p",
            ]

            if output_path:
                cmd.append(output_path)
            else:
                cmd.extend(["-f", "null", "-"])

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL
            )

            self.is_running = True
            return True
        except Exception as e:
            return False

    def stop_stream(self) -> bool:
        """Stoppe FFmpeg Stream."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                self.is_running = False
                return True
            except:
                self.process.kill()
                self.is_running = False
                return False
        return False

    def is_healthy(self) -> bool:
        """Prüfe ob Stream läuft."""
        if not self.process:
            return False
        return self.process.poll() is None


class AudioCapture:
    """Audio-Capture mit SoundDevice."""

    def __init__(self, device_id: int = None, sample_rate: int = 16000, channels: int = 1):
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.stream: Optional[sd.InputStream] = None
        self.is_running = False
        self.audio_buffer = []
        self.has_sounddevice = HAS_SOUNDDEVICE

    def list_devices(self) -> List[AudioInfo]:
        """Liste verfügbare Audio-Geräte."""
        if not self.has_sounddevice:
            return []

        devices = []
        try:
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                if device.get("max_input_channels", 0) > 0:
                    audio_info = AudioInfo(
                        device_id=i,
                        device_name=device.get("name", f"Device {i}"),
                        sample_rate=int(device.get("default_samplerate", 16000)),
                        channels=min(1, device.get("max_input_channels", 1))
                    )
                    devices.append(audio_info)
            return devices
        except Exception as e:
            return []

    def start_capture(self) -> bool:
        """Starte Audio-Capture."""
        if not self.has_sounddevice:
            return False

        try:
            self.stream = sd.InputStream(
                device=self.device_id,
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=4096
            )
            self.stream.start()
            self.is_running = True
            return True
        except Exception as e:
            return False

    def stop_capture(self) -> bool:
        """Stoppe Audio-Capture."""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                self.is_running = False
                return True
            except:
                return False
        return False

    def read_audio(self) -> Optional[Tuple]:
        """Lese Audio-Daten."""
        if not self.stream or not self.is_running:
            return None

        try:
            data, overflow = self.stream.read(4096)
            return (data, overflow)
        except Exception as e:
            return None


class MotionDetector:
    """Motion Detection für Video."""

    def __init__(self, threshold: int = 30):
        self.threshold = threshold
        self.prev_frame = None
        self.has_opencv = HAS_OPENCV

    def detect_motion(self, frame) -> Tuple[bool, float]:
        """Erkenne Bewegung in Frame."""
        if not self.has_opencv or frame is None:
            return (False, 0.0)

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if self.prev_frame is None:
                self.prev_frame = gray
                return (False, 0.0)

            frame_delta = cv2.absdiff(self.prev_frame, gray)
            thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)[1]

            motion_percentage = (cv2.countNonZero(thresh) / thresh.size) * 100

            self.prev_frame = gray

            return (motion_percentage > 1.0, motion_percentage)
        except Exception as e:
            return (False, 0.0)


class AVRecorder:
    """Audio-Video Synchronisiertes Recording."""

    def __init__(self):
        self.v4l2_controller = V4L2Controller()
        self.ffmpeg_capture: Optional[FFmpegCapture] = None
        self.audio_capture: Optional[AudioCapture] = None
        self.motion_detector = MotionDetector()
        self.is_recording = False
        self.start_time = 0.0
        self.recording_thread: Optional[threading.Thread] = None

    def initialize(self, video_device: str = "/dev/video0", audio_device: Optional[int] = None) -> bool:
        """Initialisiere A/V Recording."""
        try:
            self.ffmpeg_capture = FFmpegCapture(device_path=video_device)
            self.audio_capture = AudioCapture(device_id=audio_device)
            return True
        except Exception as e:
            return False

    def start_recording(self, output_file: str) -> bool:
        """Starte A/V Recording."""
        if not self.ffmpeg_capture:
            return False

        try:
            if not self.ffmpeg_capture.start_stream(output_file):
                return False

            if self.audio_capture:
                if not self.audio_capture.start_capture():
                    self.ffmpeg_capture.stop_stream()
                    return False

            self.is_recording = True
            self.start_time = time.time()
            return True
        except Exception as e:
            return False

    def stop_recording(self) -> Dict:
        """Stoppe A/V Recording."""
        stats = {
            "duration": time.time() - self.start_time if self.is_recording else 0,
            "video_ok": False,
            "audio_ok": False,
        }

        if self.ffmpeg_capture:
            stats["video_ok"] = self.ffmpeg_capture.stop_stream()

        if self.audio_capture:
            stats["audio_ok"] = self.audio_capture.stop_capture()

        self.is_recording = False
        return stats

    def get_status(self) -> Dict:
        """Hole Recording-Status."""
        if not self.is_recording:
            return {"status": "stopped"}

        elapsed = time.time() - self.start_time
        return {
            "status": "recording",
            "elapsed": elapsed,
            "video_healthy": self.ffmpeg_capture.is_healthy() if self.ffmpeg_capture else False,
            "audio_running": self.audio_capture.is_running if self.audio_capture else False,
        }


def create_av_recorder() -> AVRecorder:
    """Factory für AVRecorder."""
    return AVRecorder()
