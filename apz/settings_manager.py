"""EINSTELLUNGEN-MANAGER: Konfiguration & System-Settings!"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from . import ui


@dataclass
class Setting:
    """Eine Einstellung."""
    name: str
    description: str
    value: Any
    value_type: str  # "bool", "int", "string", "choice"
    choices: list = None


class SettingsManager:
    """Verwaltet alle Einstellungen."""

    def __init__(self):
        """Initialisiere Settings."""
        self.settings: Dict[str, Setting] = {
            "theme": Setting("UI Theme", "Dark/Light/Custom", "dark", "choice", ["dark", "light", "custom"]),
            "language": Setting("Sprache", "Deutsch/English", "deutsch", "choice", ["deutsch", "english"]),
            "verbose": Setting("Verbose Output", "Detaillierte Ausgabe", True, "bool"),
            "audio_quality": Setting("Audio Qualität", "Sample Rate", 44100, "choice", [16000, 44100, 48000]),
            "video_quality": Setting("Video Qualität", "Resolution", "1080p", "choice", ["480p", "720p", "1080p", "4k"]),
            "autoplay": Setting("Auto-Play", "Automatisches Abspielen", False, "bool"),
            "save_history": Setting("Verlauf speichern", "Chat-Verlauf", True, "bool"),
            "encryption": Setting("Verschlüsselung", "Sichere Übertragung", True, "bool"),
            "timeout": Setting("Timeout", "Sekunden", 30, "int"),
            "max_threads": Setting("Max Threads", "Parallel Tasks", 8, "int"),
            "api_endpoint": Setting("API Endpoint", "Server URL", "https://api.local", "string"),
            "debug_mode": Setting("Debug Mode", "Detailliertes Debugging", False, "bool"),
        }

    def show_settings(self) -> None:
        """Zeige alle Einstellungen."""
        ui.clear()
        ui.banner(subtitle="⚙️  EINSTELLUNGEN - KONFIGURATION")
        print()

        print(f"  {ui.BOLD}SYSTEM-EINSTELLUNGEN:{ui.RESET}\n")

        for i, (key, setting) in enumerate(self.settings.items(), 1):
            print(f"  {i:2d}. {setting.name:25} = {str(setting.value):30}")
            print(f"      {setting.description}")
            if setting.choices:
                print(f"      Optionen: {', '.join(map(str, setting.choices))}")
            print()

        ui.pause()

    def edit_setting(self, key: str, value: Any) -> bool:
        """Bearbeite eine Einstellung."""
        if key in self.settings:
            self.settings[key].value = value
            return True
        return False

    def get_setting(self, key: str) -> Any:
        """Hole eine Einstellung."""
        if key in self.settings:
            return self.settings[key].value
        return None

    def export_settings(self) -> Dict[str, Any]:
        """Exportiere alle Einstellungen."""
        return {key: setting.value for key, setting in self.settings.items()}

    def import_settings(self, data: Dict[str, Any]) -> None:
        """Importiere Einstellungen."""
        for key, value in data.items():
            if key in self.settings:
                self.settings[key].value = value


def create_settings_manager() -> SettingsManager:
    """Factory: Erstellt SettingsManager."""
    return SettingsManager()

def menu(adb=None) -> None:
    """SettingsManager Menu Wrapper."""
    obj = SettingsManager(adb) if adb else SettingsManager()
    obj.show_settings()
