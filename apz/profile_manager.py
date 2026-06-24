"""PROFILE MANAGER: Profil-Auswahl & Management mit schöner UI!

Besseres Interface für Profil-Verwaltung mit visuellen Anzeigen.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Callable
from dataclasses import dataclass

from . import ui


@dataclass
class ProfileInfo:
    """Profil-Information für Display."""
    profile_id: str
    name: str
    keyword_count: int
    mode: str
    enabled: bool
    description: str = ""


class ProfileManager:
    """Profil-Verwaltungs-UI."""

    def __init__(self):
        """Initialisiere Profile Manager."""
        self.selected_profile: Optional[str] = None

    def show_profile_selector(self, profiles: Dict[str, any]) -> Optional[str]:
        """Zeige Profil-Auswahl mit schöner UI."""
        while True:
            ui.clear()
            ui.banner(subtitle="📋 PROFIL AUSWÄHLEN")
            print()

            if not profiles:
                ui.warn("Keine Profile verfügbar!")
                ui.pause()
                return None

            # Convert to list for indexing
            profile_list = list(profiles.items())

            # Header
            print(f"{ui.BOLD}{'#':3} {'NAME':20} {'KEYWORDS':10} {'MODUS':20} {'STATUS':{ui.RESET}}")
            print("─" * 80)
            print()

            for i, (pid, profile) in enumerate(profile_list, 1):
                # Get display info
                kw_count = len(profile.keywords) if hasattr(profile, 'keywords') else 0
                mode = profile.recording_mode.value[:18] if hasattr(profile, 'recording_mode') else "Unknown"
                enabled = profile.enabled if hasattr(profile, 'enabled') else True
                status = "✓ AKTIV" if enabled else "✗ INAKTIV"

                # Highlight selected
                selected = "→" if self.selected_profile == pid else " "

                print(f"{selected}{i:2d}  {profile.name:20} {kw_count:10d} {mode:20} {status}")

            print()
            print(f"{ui.BGREEN}{'='*80}{ui.RESET}")
            print()
            print("  OPTIONEN:")
            print(f"    {ui.BOLD}1-{len(profile_list)}{ui.RESET}    Profile wählen")
            print(f"    {ui.BOLD}N{ui.RESET}    Neues Profil erstellen")
            print(f"    {ui.BOLD}E{ui.RESET}    Profil bearbeiten")
            print(f"    {ui.BOLD}D{ui.RESET}    Profil löschen")
            print(f"    {ui.BOLD}Q{ui.RESET}    Zurück")
            print()

            choice = ui.ask(f"Auswahl (1-{len(profile_list)}, N/E/D, Q)", "Q").upper()

            # Handle numeric selection
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(profile_list):
                    selected_id, selected_profile = profile_list[idx]
                    self.selected_profile = selected_id
                    ui.ok(f"✓ {selected_profile.name} ausgewählt")
                    return selected_id
                else:
                    ui.warn("Ungültige Nummer")
            except ValueError:
                # Handle letter commands
                if choice == "Q":
                    return None
                elif choice == "N":
                    return self._create_new_profile()
                elif choice == "E":
                    if self.selected_profile:
                        self._edit_profile(self.selected_profile, profiles)
                    else:
                        ui.warn("Wähle erst ein Profil!")
                elif choice == "D":
                    if self.selected_profile:
                        self._delete_profile(self.selected_profile, profiles)
                    else:
                        ui.warn("Wähle erst ein Profil!")
                else:
                    ui.warn("Ungültige Eingabe")

            time.sleep(0.5)

    def show_profile_detail(self, profile_id: str, profile: any) -> None:
        """Zeige detaillierte Profil-Informationen."""
        ui.clear()
        ui.banner(subtitle=f"📖 PROFIL: {profile.name}")
        print()

        # Profile Info
        print(f"{ui.BOLD}PROFIL-INFORMATIONEN:{ui.RESET}\n")
        print(f"  Name:              {profile.name}")
        print(f"  ID:                {profile_id}")
        if hasattr(profile, 'description'):
            print(f"  Beschreibung:      {profile.description}")
        print()

        # Keywords
        kw_count = len(profile.keywords) if hasattr(profile, 'keywords') else 0
        print(f"{ui.BOLD}KEYWORDS ({kw_count}):{ui.RESET}\n")

        if hasattr(profile, 'keywords') and profile.keywords:
            for i, kw in enumerate(profile.keywords[:15], 1):
                status = "✓" if kw.enabled else "✗"
                print(f"  {status} {i:2d}. {kw.text:20} Priorität: {kw.priority}/10 Confidence: {int(kw.confidence_threshold*100)}%")
        else:
            print("  (Keine Keywords definiert)")

        print()

        # Settings
        print(f"{ui.BOLD}EINSTELLUNGEN:{ui.RESET}\n")
        if hasattr(profile, 'recording_mode'):
            print(f"  Recording-Modus:         {profile.recording_mode.value}")
        if hasattr(profile, 'pre_trigger_seconds'):
            print(f"  Sekunden VOR Keyword:    {profile.pre_trigger_seconds}s")
        if hasattr(profile, 'post_trigger_seconds'):
            print(f"  Sekunden NACH Keyword:   {profile.post_trigger_seconds}s")
        if hasattr(profile, 'min_keyword_gap_seconds'):
            print(f"  Min. Keyword-Abstand:    {profile.min_keyword_gap_seconds}s")
        if hasattr(profile, 'max_recording_duration'):
            print(f"  Max. Aufzeichnungsdauer: {profile.max_recording_duration}s")
        if hasattr(profile, 'confidence_threshold'):
            print(f"  Confidence Schwelle:     {int(profile.confidence_threshold*100)}%")

        print()
        ui.pause()

    def show_profile_menu(self, profile_id: str, profile: any) -> str:
        """Zeige Profil-Menü."""
        ui.clear()
        ui.banner(subtitle=f"⚙️  {profile.name}")
        print()

        print(f"  Profil: {ui.BOLD}{profile.name}{ui.RESET}")
        print(f"  ID: {profile_id}")
        print()

        print("  OPTIONEN:\n")
        print(f"    {ui.BOLD}1{ui.RESET}  Keywords verwalten")
        print(f"    {ui.BOLD}2{ui.RESET}  Einstellungen ändern")
        print(f"    {ui.BOLD}3{ui.RESET}  Profil-Details anzeigen")
        print(f"    {ui.BOLD}4{ui.RESET}  Recording starten")
        print(f"    {ui.BOLD}5{ui.RESET}  Profil duplizieren")
        print(f"    {ui.BOLD}6{ui.RESET}  Profil exportieren")
        print(f"    {ui.BOLD}7{ui.RESET}  Profil löschen")
        print(f"    {ui.BOLD}Q{ui.RESET}  Zurück")
        print()

        return ui.ask("Option (1-7, Q)", "Q").upper()

    def _create_new_profile(self) -> Optional[str]:
        """Erstelle neues Profil (Platzhalter)."""
        ui.warn("Neue Profile müssen im Keyword Recorder erstellt werden")
        ui.pause()
        return None

    def _edit_profile(self, profile_id: str, profiles: dict) -> None:
        """Bearbeite Profil (Platzhalter)."""
        ui.warn("Profil-Bearbeitung im Keyword Recorder")
        ui.pause()

    def _delete_profile(self, profile_id: str, profiles: dict) -> None:
        """Lösche Profil (Platzhalter)."""
        if ui.ask("Profil wirklich löschen?", "N") == "Y":
            ui.ok("Profil gelöscht")
        ui.pause()

    def show_quick_selector(self, profiles: Dict[str, any]) -> Optional[str]:
        """Schnelle Profil-Auswahl als Menü."""
        ui.clear()
        ui.banner(subtitle="📋 PROFIL WÄHLEN")
        print()

        if not profiles:
            ui.warn("Keine Profile verfügbar!")
            return None

        entries = []
        for pid, profile in profiles.items():
            kw_count = len(profile.keywords) if hasattr(profile, 'keywords') else 0
            desc = f"{profile.name} ({kw_count} Keywords)"
            entries.append((pid, desc))

        selection = ui.menu("Wähle Profil", entries, back_label="Zurück")

        if selection in ("back", "quit"):
            return None

        return selection


def create_profile_manager() -> ProfileManager:
    """Factory: Erstellt Profile Manager."""
    return ProfileManager()


# Für imports
import time
