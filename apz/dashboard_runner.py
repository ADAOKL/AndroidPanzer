"""Dashboard-Runner: Führt Features mit Dashboard-Begleitung aus.

Integriert mit main.py um jede Feature-Ausführung mit:
- Echtzeit-Fortschrittsbalken
- Detaillierter Analyse
- Strukturierter Ausgabe
zu versorgen.
"""
from __future__ import annotations

import time
from typing import Optional

from . import adb, ui
from .adb import ADB, Device
from .dashboard_feature import FeatureDashboard, create_dashboard
from .feature_analysis import analyze_feature_output


def run_cmd_feature(adb: ADB, dashboard: FeatureDashboard, command: str,
                    timeout: int = 60) -> bool:
    """Führt ein ADB-Kommando mit Dashboard aus."""
    dashboard.render_header()
    dashboard.show_progress(1, 4, "ADB-Verbindung…")

    try:
        dashboard.show_progress(2, 4, "Kommando ausführen…")
        start = time.time()
        output = adb.shell(command, timeout=timeout)
        elapsed = time.time() - start

        dashboard.show_progress(3, 4, "Ergebnisse analysieren…")
        time.sleep(0.1)

        dashboard.step_complete("ADB-Ausführung", True,
                               {'duration': f"{elapsed:.2f}s", 'size': f"{len(output)} Bytes"})

        if output:
            # Intelligent parse output
            analyze_feature_output(dashboard, output, "cmd", dashboard.title)
            dashboard.add_result('Raw_Output_Lines', len(output.split('\n')), 'Ausgabezeilen')

        dashboard.show_progress(4, 4, "Fertig")
        print()
        dashboard.render_complete()
        return True

    except Exception as e:
        dashboard.step_complete("ADB-Ausführung", False, error=str(e))
        dashboard.render_complete()
        return False


def run_rootcmd_feature(adb: ADB, dashboard: FeatureDashboard, command: str,
                       timeout: int = 60) -> bool:
    """Führt ein Root-Kommando mit Dashboard aus."""
    dashboard.render_header()

    if not adb.check_root():
        dashboard.add_warning("Root-Zugriff nicht verfügbar")
        ui.warn(dashboard.title + " benötigt Root-Rechte")
        dashboard.render_complete()
        return False

    dashboard.show_progress(1, 4, "Root-Zugriff prüfen…")
    time.sleep(0.1)

    try:
        dashboard.show_progress(2, 4, "Kommando ausführen (Root)…")
        start = time.time()
        output = adb.shell(command, timeout=timeout, root=True)
        elapsed = time.time() - start

        dashboard.show_progress(3, 4, "Analyse…")
        time.sleep(0.1)

        dashboard.step_complete("Root-Ausführung", True,
                               {'duration': f"{elapsed:.2f}s", 'privileged': 'yes'})

        if output:
            analyze_feature_output(dashboard, output, "rootcmd", dashboard.title)

        dashboard.show_progress(4, 4, "Fertig")
        print()
        dashboard.render_complete()
        return True

    except Exception as e:
        dashboard.step_complete("Root-Ausführung", False, error=str(e))
        dashboard.render_complete()
        return False


def run_interactive_feature(dashboard: FeatureDashboard,
                           handler_func: callable) -> bool:
    """Führt einen interaktiven Handler mit Dashboard aus."""
    dashboard.render_header()

    try:
        dashboard.show_progress(1, 3, "Handler initialisieren…")
        time.sleep(0.1)

        dashboard.show_progress(2, 3, "Interaktive Ausführung…")
        result = handler_func()

        dashboard.show_progress(3, 3, "Fertig")
        print()

        if result:
            dashboard.step_complete("Handler-Ausführung", True)
            dashboard.add_result('Result', result, 'Ergebnis')
        else:
            dashboard.step_complete("Handler-Ausführung", True)

        dashboard.render_complete()
        return True

    except Exception as e:
        dashboard.step_complete("Handler-Ausführung", False, error=str(e))
        dashboard.render_complete()
        return False


def run_info_feature(dashboard: FeatureDashboard, info_text: str) -> bool:
    """Zeigt Info-Text mit Dashboard an."""
    dashboard.render_header()

    dashboard.show_progress(1, 2, "Info vorbereiten…")
    time.sleep(0.1)

    dashboard.show_progress(2, 2, "Anzeigen…")
    print()

    # Format info text
    lines = info_text.split('\n')
    dashboard.add_result('Description', f"{len(lines)} Zeilen", 'Info-Länge')

    # Show info
    ui.info(info_text)
    print()

    dashboard.render_complete()
    return True


def run_ask_feature(dashboard: FeatureDashboard, prompt: str,
                   template: str, adb: ADB) -> bool:
    """Führt ein interaktives Input-Feature mit Dashboard aus."""
    dashboard.render_header()

    dashboard.show_progress(1, 4, "Input-Dialog vorbereiten…")
    time.sleep(0.1)

    # Get user input
    value = ui.ask(prompt)
    dashboard.add_result('User_Input', value, 'Benutzereingabe')

    if value or "{v}" not in template:
        dashboard.show_progress(2, 4, "Kommando zusammenstellen…")
        cmd = template.replace("{v}", value)
        dashboard.add_result('Prepared_Command', cmd[:80], 'Kommando')

        dashboard.show_progress(3, 4, "Ausführen…")
        try:
            output = adb.shell(cmd, timeout=60)
            dashboard.show_progress(4, 4, "Fertig")
            print()

            if output:
                analyze_feature_output(dashboard, output, "ask", dashboard.title)

            dashboard.step_complete("Ausführung", True)
        except Exception as e:
            dashboard.step_complete("Ausführung", False, error=str(e))
    else:
        dashboard.add_warning("Keine Eingabe – Übersprungen")

    dashboard.render_complete()
    return True


def run_danger_feature(dashboard: FeatureDashboard, description: str) -> bool:
    """Warnt vor destruktiven Operationen und zeigt Dashboard."""
    dashboard.render_header()

    dashboard.show_progress(1, 3, "Destruktive Warnung…")
    print()
    ui.danger(description)
    print()

    # Double confirmation
    if not ui.confirm("Wirklich ausführen?", False):
        dashboard.add_warning("Nutzer hat abgebrochen")
        dashboard.render_complete()
        return False

    dashboard.show_progress(2, 3, "Zweite Bestätigung…")
    if not ui.confirm("FINAL BESTÄTIGUNG – kann nicht rückgängig gemacht werden!", False):
        dashboard.add_warning("Nutzer hat zweite Bestätigung abgebrochen")
        dashboard.render_complete()
        return False

    dashboard.show_progress(3, 3, "Ausgeführt (!) ")
    print()
    dashboard.step_complete("Destruktive Operation", True)
    dashboard.render_complete()
    return True


def run_sdr_feature(dashboard: FeatureDashboard, description: str) -> bool:
    """Zeigt SDR/Hardware-Anforderungen."""
    dashboard.render_header()

    dashboard.show_progress(1, 2, "Hardware-Info laden…")
    print()
    ui.warn(description)
    print()

    dashboard.show_progress(2, 2, "Fertig")
    print()

    dashboard.add_result('Type', 'SDR/Hardware erforderlich', 'Feature-Typ')
    dashboard.add_warning("Benötigt spezielle Hardware: HackRF, USRP, bladeRF oder Diag-Port")
    dashboard.render_complete()
    return True


def create_feature_dashboard(feature_num: int, feature_title: str,
                            feature_kind: str) -> FeatureDashboard:
    """Erstellt ein Feature-Dashboard."""
    return create_dashboard(feature_num, feature_title, feature_kind)
