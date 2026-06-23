"""Feature-spezifische Dashboards mit Analyse, Fortschritt & Ausgabe-Formatierung.

Für jede der 450 Funktionen generiert dieses Modul ein visuelles Terminal-Dashboard mit:
- Echtzeit-Fortschrittsanzeige (0-100%)
- Detaillierte Analyseergebnisse
- Fehlerbehandlung & Status-Rückmeldung
- Performance-Metriken
- Strukturierte Datenausgabe
"""
from __future__ import annotations

import sys
import time
from typing import Any, Callable, Optional

from . import ui


class FeatureDashboard:
    """Terminal-Dashboard für eine einzelne Funktion."""

    def __init__(self, feature_num: int, feature_title: str, feature_kind: str):
        self.num = feature_num
        self.title = feature_title
        self.kind = feature_kind
        self.start_time = time.time()
        self.progress = 0
        self.total_steps = 100
        self.results: dict[str, Any] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def render_header(self) -> None:
        """Rendert den Dashboard-Kopfbereich."""
        ui.clear()
        ui.rule(f"#{self.num:03d} · {self.title}", ui.CYAN)

        badge_map = {
            "cmd": ("ADB", ui.GREEN),
            "rootcmd": ("ROOT", ui.YELLOW),
            "ask": ("INPUT", ui.BCYAN),
            "fn": ("LIVE", ui.BGREEN),
            "info": ("INFO", ui.BLUE),
            "sdr": ("SDR/HW", ui.MAGENTA),
            "danger": ("⚠ DANGER", ui.RED),
        }

        badge_text, badge_color = badge_map.get(self.kind, ("UNKNOWN", ui.GREY))
        print(f"  {badge_color}{ui.BOLD}[{badge_text}]{ui.RESET} "
              f"{ui.GREY}Ausführungstyp: {self.kind}{ui.RESET}")
        print()

    def show_progress(self, step: int, total: int, label: str = "") -> None:
        """Zeigt einen Fortschrittsbalken an."""
        self.progress = int((step / max(total, 1)) * 100)
        percentage = self.progress

        # ASCII-Balken
        filled = int((percentage / 100) * 40)
        bar = f"{ui.BCYAN}{'█' * filled}{ui.GREY}{'░' * (40 - filled)}{ui.RESET}"

        sys.stdout.write(f"\r  {bar} {ui.BOLD}{percentage:3d}%{ui.RESET}")
        if label:
            sys.stdout.write(f"  {ui.GREY}{label[:40]}{ui.RESET}")
        sys.stdout.flush()

    def step_complete(self, step_name: str, success: bool = True,
                     data: Optional[dict] = None, error: Optional[str] = None) -> None:
        """Markiert einen Schritt als abgeschlossen."""
        if success:
            if data:
                self.results[step_name] = data
            print(f"\n  {ui.BGREEN}✓{ui.RESET} {step_name}")
        else:
            print(f"\n  {ui.BRED}✗{ui.RESET} {step_name}")
            if error:
                self.errors.append(f"{step_name}: {error}")
                print(f"    {ui.RED}{error}{ui.RESET}")

    def add_result(self, key: str, value: Any, label: str = "") -> None:
        """Fügt ein Analyseergebnis hinzu."""
        self.results[key] = value
        if label:
            val_str = str(value)[:60]
            print(f"  {ui.CYAN}{label:30}{ui.RESET} {ui.GREY}→{ui.RESET} {val_str}")

    def add_warning(self, message: str) -> None:
        """Fügt eine Warnung hinzu."""
        self.warnings.append(message)
        print(f"  {ui.BYELLOW}⚠{ui.RESET} {message}")

    def add_error(self, message: str) -> None:
        """Fügt einen Fehler hinzu."""
        self.errors.append(message)
        print(f"  {ui.BRED}✗{ui.RESET} {message}")

    def render_results_table(self) -> None:
        """Rendert eine Tabelle mit allen Analyseergebnissen."""
        if not self.results:
            return

        print()
        ui.rule("ANALYSEERGEBNISSE", ui.CYAN)

        for key, value in self.results.items():
            if isinstance(value, dict):
                print(f"  {ui.BOLD}{key}{ui.RESET}")
                for k, v in value.items():
                    print(f"    {ui.GREY}{k:25}{ui.RESET} {v}")
            elif isinstance(value, list):
                print(f"  {ui.BOLD}{key}{ui.RESET} ({len(value)} Einträge)")
                for item in value[:5]:
                    print(f"    • {item}")
                if len(value) > 5:
                    print(f"    {ui.GREY}... und {len(value) - 5} weitere{ui.RESET}")
            else:
                print(f"  {ui.CYAN}{key:25}{ui.RESET} {value}")

    def render_summary(self) -> None:
        """Rendert eine zusammenfassende Statistik."""
        elapsed = time.time() - self.start_time

        print()
        ui.rule("ZUSAMMENFASSUNG", ui.CYAN)

        print(f"  {ui.CYAN}Funktion{ui.RESET:30} #{self.num:03d}")
        print(f"  {ui.CYAN}Ausführungszeit{ui.RESET:30} {elapsed:.2f}s")
        print(f"  {ui.CYAN}Analyseergebnisse{ui.RESET:30} {len(self.results)} Datenpunkte")

        if self.warnings:
            print(f"  {ui.BYELLOW}⚠ Warnungen{ui.RESET:30} {len(self.warnings)}")

        if self.errors:
            print(f"  {ui.BRED}✗ Fehler{ui.RESET:30} {len(self.errors)}")
            for err in self.errors:
                print(f"    {ui.GREY}• {err}{ui.RESET}")
        else:
            print(f"  {ui.BGREEN}Status{ui.RESET:30} ✓ Erfolgreich")

    def render_complete(self) -> None:
        """Rendert die vollständige Dashboard-Ausgabe."""
        self.render_header()
        self.render_results_table()
        self.render_summary()
        print()


class MultiFeatureDashboard:
    """Dashboard für mehrere Funktionen mit Übersicht."""

    def __init__(self):
        self.dashboards: list[FeatureDashboard] = []
        self.total_success = 0
        self.total_warnings = 0
        self.total_errors = 0

    def add_feature(self, dashboard: FeatureDashboard) -> None:
        """Fügt ein Feature-Dashboard hinzu."""
        self.dashboards.append(dashboard)

        self.total_success += (1 if not dashboard.errors else 0)
        self.total_warnings += len(dashboard.warnings)
        self.total_errors += len(dashboard.errors)

    def render_overview(self) -> None:
        """Zeigt eine Übersicht aller Features."""
        ui.clear()
        ui.rule("FEATURE-AUSFÜHRUNGS-ÜBERSICHT", ui.YELLOW)

        total = len(self.dashboards)
        success_rate = (self.total_success / max(total, 1)) * 100

        print(f"  {ui.CYAN}Gesamt Features{ui.RESET:25} {total}")
        print(f"  {ui.BGREEN}Erfolgreich{ui.RESET:25} {self.total_success}")
        print(f"  {ui.BYELLOW}Warnungen{ui.RESET:25} {self.total_warnings}")
        print(f"  {ui.BRED}Fehler{ui.RESET:25} {self.total_errors}")
        print()

        # Erfolgsrate-Balken
        filled = int((success_rate / 100) * 50)
        bar = f"{ui.BGREEN}{'█' * filled}{ui.GREY}{'░' * (50 - filled)}{ui.RESET}"
        print(f"  Erfolgsrate: {bar} {ui.BOLD}{success_rate:.1f}%{ui.RESET}")
        print()


def create_dashboard(feature_num: int, feature_title: str,
                    feature_kind: str) -> FeatureDashboard:
    """Erstellt ein neues Feature-Dashboard."""
    return FeatureDashboard(feature_num, feature_title, feature_kind)


def run_feature_with_dashboard(dashboard: FeatureDashboard,
                               func: Callable) -> bool:
    """Führt eine Funktion mit Dashboard-Begleitung aus."""
    dashboard.render_header()

    try:
        dashboard.show_progress(0, 4, "Initialisierung…")
        time.sleep(0.2)

        dashboard.show_progress(1, 4, "Daten sammeln…")
        result = func(dashboard)
        time.sleep(0.2)

        dashboard.show_progress(2, 4, "Daten analysieren…")
        time.sleep(0.2)

        dashboard.show_progress(3, 4, "Formatieren…")
        time.sleep(0.1)

        dashboard.show_progress(4, 4, "Fertig")
        print()

        dashboard.render_complete()
        return not bool(dashboard.errors)

    except Exception as e:
        dashboard.add_error(str(e))
        dashboard.render_complete()
        return False


def menu(adb=None) -> None:
    """MultiFeatureDashboard Menu Wrapper."""
    obj = MultiFeatureDashboard(adb) if adb else MultiFeatureDashboard()
    obj.show_dashboard()

