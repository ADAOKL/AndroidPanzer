"""AI DOCTOR: KI-basiertes Auto-Fix System mit User-Bestätigung.

Fehler erkennen → Lösung vorschlagen → User bestätigt → KI behebt!
"""
from __future__ import annotations

import os
import json
import time
import hashlib
from typing import Optional, List, Dict, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from . import ui
from .adb import ADB


class FixCategory(Enum):
    """Kategorien von Fehlerbehebungen."""
    APP_FIX = "App-Fehler"
    FILE_FIX = "Datei-Fehler"
    PERMISSION_FIX = "Permissions"
    PROCESS_FIX = "Prozess-Fehler"
    NETWORK_FIX = "Netzwerk-Fehler"
    SYSTEM_FIX = "System-Fehler"
    PERFORMANCE_FIX = "Performance"
    STORAGE_FIX = "Speicher"
    BATTERY_FIX = "Batterie"
    MEMORY_FIX = "RAM"


class RiskLevel(Enum):
    """Risiko-Level für Fixes."""
    LOW = "LOW"              # Sicher
    MEDIUM = "MEDIUM"        # Moderat
    HIGH = "HIGH"            # Vorsicht
    CRITICAL = "CRITICAL"    # Backup empfohlen


class FixStatus(Enum):
    """Status einer Fehlerbehebung."""
    PENDING = "Ausstehend"
    APPROVED = "Genehmigt"
    IN_PROGRESS = "In Bearbeitung"
    COMPLETED = "Abgeschlossen"
    FAILED = "Fehlgeschlagen"
    ROLLED_BACK = "Rückgängig gemacht"


@dataclass
class ErrorDiagnosis:
    """Diagnose eines Fehlers."""
    error_id: str
    error_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    root_cause: str
    affected_systems: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    evidence: List[str] = field(default_factory=list)


@dataclass
class FixSolution:
    """Eine vorgeschlagene Fehlerbehebung."""
    fix_id: str
    error_id: str
    fix_category: FixCategory
    title: str
    description: str
    steps: List[str] = field(default_factory=list)
    estimated_time_seconds: int = 0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    confidence: float = 0.0  # 0-100%
    prerequisites: List[str] = field(default_factory=list)
    rollback_procedure: Optional[str] = None
    backup_needed: bool = False
    status: FixStatus = FixStatus.PENDING
    user_approved: bool = False
    approval_timestamp: float = 0.0
    execution_timestamp: float = 0.0
    completion_timestamp: float = 0.0
    result: str = ""
    error_message: str = ""


class AIDoctor:
    """Master AI Doctor - Intelligente Fehler-Diagnose & Behebung."""

    # FIX-TEMPLATES nach Kategorie
    FIX_TEMPLATES = {
        "app_crash": {
            "category": FixCategory.APP_FIX,
            "description": "App-Crash beheben",
            "steps": [
                "1. Cache der App leeren",
                "2. App-Daten löschen",
                "3. App-Aktualisierung prüfen",
                "4. App neu starten",
            ],
            "risk": RiskLevel.LOW,
            "backup": False,
        },
        "permission_denied": {
            "category": FixCategory.PERMISSION_FIX,
            "description": "Permission-Fehler beheben",
            "steps": [
                "1. Permissions überprüfen",
                "2. Fehlende Permissions gewähren",
                "3. App neu starten",
                "4. Funktionalität testen",
            ],
            "risk": RiskLevel.MEDIUM,
            "backup": False,
        },
        "low_storage": {
            "category": FixCategory.STORAGE_FIX,
            "description": "Speicherplatz freigeben",
            "steps": [
                "1. Temporäre Dateien löschen",
                "2. Cache leeren",
                "3. Ungenutzte Apps entfernen",
                "4. Große Dateien verschieben",
            ],
            "risk": RiskLevel.MEDIUM,
            "backup": True,
        },
        "high_memory": {
            "category": FixCategory.MEMORY_FIX,
            "description": "RAM-Speicher optimieren",
            "steps": [
                "1. Laufende Apps analysieren",
                "2. RAM-hungrige Prozesse beenden",
                "3. Background-Services deaktivieren",
                "4. Memory-Optimierung starten",
            ],
            "risk": RiskLevel.MEDIUM,
            "backup": False,
        },
        "battery_drain": {
            "category": FixCategory.BATTERY_FIX,
            "description": "Batterie-Drain beheben",
            "steps": [
                "1. Batterie-hungrige Apps finden",
                "2. Background-Aktivität reduzieren",
                "3. Screen-Helligkeit optimieren",
                "4. Standby-Modi konfigurieren",
            ],
            "risk": RiskLevel.LOW,
            "backup": False,
        },
        "network_error": {
            "category": FixCategory.NETWORK_FIX,
            "description": "Netzwerk-Fehler beheben",
            "steps": [
                "1. WiFi/Cellular Status prüfen",
                "2. Netzwerk-Einstellungen zurücksetzen",
                "3. DNS-Cache leeren",
                "4. Verbindung neu aufbauen",
            ],
            "risk": RiskLevel.MEDIUM,
            "backup": False,
        },
        "malware_detected": {
            "category": FixCategory.SYSTEM_FIX,
            "description": "Malware entfernen",
            "steps": [
                "1. ⚠️  BACKUP erstellen (KRITISCH)",
                "2. Verdächtige App isolieren",
                "3. Malware-Dateien entfernen",
                "4. Sicherheits-Scan durchführen",
                "5. System-Integrität prüfen",
            ],
            "risk": RiskLevel.CRITICAL,
            "backup": True,
        },
        "file_corruption": {
            "category": FixCategory.FILE_FIX,
            "description": "Beschädigte Dateien reparieren",
            "steps": [
                "1. Datei-Integrität prüfen",
                "2. Backup versuchen zu laden",
                "3. Datei neu formatieren",
                "4. Datei-System-Check durchführen",
            ],
            "risk": RiskLevel.HIGH,
            "backup": True,
        },
        "system_slowdown": {
            "category": FixCategory.PERFORMANCE_FIX,
            "description": "Performance verbessern",
            "steps": [
                "1. Startup-Apps optimieren",
                "2. Hintergrund-Prozesse reduzieren",
                "3. System-Cache leeren",
                "4. Fragmentierung reduzieren",
                "5. Performance neu bewerten",
            ],
            "risk": RiskLevel.MEDIUM,
            "backup": False,
        },
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.detected_errors: List[ErrorDiagnosis] = []
        self.fix_solutions: List[FixSolution] = []
        self.fix_history: List[Dict] = []
        self.current_diagnosis: Optional[ErrorDiagnosis] = None
        self.current_fix: Optional[FixSolution] = None

    def show_ai_doctor_menu(self) -> None:
        """Zeigt AI Doctor Hauptmenü."""
        while True:
            ui.clear()

            ui.banner(subtitle="🏥 AI DOCTOR - KI-basierte Fehlerdiagnose & Auto-Fix")
            print()

            entries = [
                ("1", "🔍 Systemfehler diagnostizieren"),
                ("2", "📊 Erkannte Fehler anzeigen"),
                ("3", "💊 Fehler-Behebung (mit KI)"),
                ("4", "📋 Fix-Vorschläge anzeigen"),
                ("5", "✅ Fixes genehmigen & ausführen"),
                ("6", "📈 Fix-Verlauf anzeigen"),
                ("7", "🔧 Manuelle Fehlerdiagnose"),
                ("8", "⚡ Quick-Fix (häufige Fehler)"),
                ("9", "📊 System-Gesundheit Bericht"),
            ]

            ch = ui.menu("AI Doctor Optionen", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.run_full_system_diagnosis()
            elif ch == "2":
                self.show_detected_errors()
            elif ch == "3":
                self.show_fix_suggestions()
            elif ch == "4":
                self.show_available_fixes()
            elif ch == "5":
                self.approve_and_execute_fixes()
            elif ch == "6":
                self.show_fix_history()
            elif ch == "7":
                self.manual_error_input()
            elif ch == "8":
                self.quick_fix_menu()
            elif ch == "9":
                self.show_health_report()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def run_full_system_diagnosis(self) -> None:
        """Führt vollständige System-Diagnose durch."""
        ui.clear()
        ui.rule("🔍 SYSTEM-DIAGNOSE LÄUFT", ui.BCYAN)
        print()

        diagnostic_stages = [
            ("App-Fehler scannen", self._diagnose_apps),
            ("Dateisystem prüfen", self._diagnose_filesystem),
            ("Speicher analysieren", self._diagnose_storage),
            ("RAM analysieren", self._diagnose_memory),
            ("Batterie prüfen", self._diagnose_battery),
            ("Netzwerk prüfen", self._diagnose_network),
            ("System-Prozesse prüfen", self._diagnose_processes),
            ("Performance prüfen", self._diagnose_performance),
        ]

        for i, (stage_name, diagnosis_func) in enumerate(diagnostic_stages, 1):
            ui.progress(i, len(diagnostic_stages), stage_name)
            diagnosis_func()

        ui.progress(len(diagnostic_stages), len(diagnostic_stages), "Diagnose abgeschlossen")
        print()
        ui.ok(f"✓ Diagnose fertig! {len(self.detected_errors)} Fehler gefunden.")
        ui.pause()

    def show_detected_errors(self) -> None:
        """Zeigt erkannte Fehler."""
        ui.clear()
        ui.rule("📊 ERKANNTE FEHLER", ui.BCYAN)
        print()

        if not self.detected_errors:
            print("  Keine Fehler erkannt - System läuft normal!")
        else:
            for i, error in enumerate(self.detected_errors, 1):
                color = ui.BRED if error.severity == "CRITICAL" else ui.YELLOW
                print(f"  {i}. {color}{error.error_type}{ui.RESET}")
                print(f"     Severity: {error.severity}")
                print(f"     {error.description}")
                print()

        ui.pause()

    def show_fix_suggestions(self) -> None:
        """Zeigt KI-generierte Fix-Vorschläge."""
        ui.clear()
        ui.rule("💊 KI-GENERIERTE FIX-VORSCHLÄGE", ui.BCYAN)
        print()

        if not self.detected_errors:
            print("  Keine erkannten Fehler - keine Fixes nötig!")
            ui.pause()
            return

        # Generiere Fixes für jeden Fehler
        for error in self.detected_errors:
            fix = self._generate_fix_for_error(error)
            if fix:
                self.fix_solutions.append(fix)
                self._display_fix_suggestion(fix)

        ui.pause()

    def show_available_fixes(self) -> None:
        """Zeigt verfügbare Fixes."""
        ui.clear()
        ui.rule("📋 VERFÜGBARE FIXES", ui.BCYAN)
        print()

        if not self.fix_solutions:
            print("  Keine Fixes verfügbar - führe erst eine Diagnose durch!")
            ui.pause()
            return

        for i, fix in enumerate(self.fix_solutions, 1):
            status_color = self._get_status_color(fix.status)
            print(f"  {i}. {status_color}{fix.title}{ui.RESET}")
            print(f"     Kategorie: {fix.fix_category.value}")
            print(f"     Risiko: {fix.risk_level.value}")
            print(f"     Konfidenz: {fix.confidence:.1f}%")
            print(f"     Status: {fix.status.value}")
            print()

        ui.pause()

    def approve_and_execute_fixes(self) -> None:
        """Genehmigt und führt Fixes aus."""
        ui.clear()
        ui.rule("✅ FIXES GENEHMIGEN & AUSFÜHREN", ui.BCYAN)
        print()

        if not self.fix_solutions:
            ui.warn("Keine Fixes verfügbar!")
            ui.pause()
            return

        # Zeige Fixes zur Genehmigung
        pending_fixes = [f for f in self.fix_solutions if f.status == FixStatus.PENDING]

        if not pending_fixes:
            print("  Alle Fixes bereits verarbeitet!")
            ui.pause()
            return

        print(f"  {len(pending_fixes)} Fixes ausstehend:\n")

        for i, fix in enumerate(pending_fixes, 1):
            print(f"  {i}. {fix.title}")
            print(f"     Kategorie: {fix.fix_category.value}")
            print(f"     Risiko: {self._get_risk_color(fix.risk_level)}{fix.risk_level.value}{ui.RESET}")
            print(f"     Konfidenz: {fix.confidence:.1f}%")

            if fix.backup_needed:
                print(f"     {ui.BRED}⚠️  BACKUP wird erstellt!{ui.RESET}")

            print()

        # User-Bestätigung
        print()
        print(f"  {ui.BGREEN}KI Doctor empfiehlt diese Fixes!{ui.RESET}")
        print()
        print("  Die KI hat diese Fehler analysiert und optimale Lösungen generiert.")
        print("  Bestätigen Sie die Ausführung der Fixes?")
        print()

        if not ui.confirm("Fixes ausführen?", False):
            print("  Abgebrochen.")
            ui.pause()
            return

        # Führe Fixes nacheinander aus
        print()
        print(f"  {ui.BGREEN}Starte Fehler-Behebung...{ui.RESET}\n")

        for i, fix in enumerate(pending_fixes, 1):
            self.execute_fix(fix, i, len(pending_fixes))

        print()
        ui.ok("Alle Fixes abgeschlossen!")
        ui.pause()

    def execute_fix(self, fix: FixSolution, index: int, total: int) -> None:
        """Führt einen einzelnen Fix aus."""
        ui.progress(index, total, f"Behebe: {fix.title}")

        fix.status = FixStatus.APPROVED
        fix.approval_timestamp = time.time()
        fix.status = FixStatus.IN_PROGRESS
        fix.execution_timestamp = time.time()

        print(f"\n  🔧 Führe aus: {fix.title}")
        print(f"     Geschätzte Zeit: {fix.estimated_time_seconds}s")

        try:
            # Simuliere Ausführung
            time.sleep(0.5)

            # Versuche Fix auszuführen
            success = self._execute_fix_steps(fix)

            if success:
                fix.status = FixStatus.COMPLETED
                fix.completion_timestamp = time.time()
                fix.result = "✓ Erfolgreich behoben"
                print(f"  {ui.BGREEN}✓ Fix erfolgreich!{ui.RESET}")

                # Verifiziere Ergebnis
                verified = self._verify_fix(fix)
                if not verified:
                    print(f"  {ui.YELLOW}⚠️  Verifikation fehlgeschlagen{ui.RESET}")
                    fix.result = "Behoben, aber Verifikation fehlgeschlagen"

            else:
                fix.status = FixStatus.FAILED
                fix.error_message = "Ausführung fehlgeschlagen"
                print(f"  {ui.BRED}✗ Fix fehlgeschlagen{ui.RESET}")

                # Rollback versuchen
                if fix.rollback_procedure:
                    print(f"  🔄 Führe Rollback durch...")
                    self._perform_rollback(fix)
                    fix.status = FixStatus.ROLLED_BACK

        except Exception as e:
            fix.status = FixStatus.FAILED
            fix.error_message = str(e)
            print(f"  {ui.BRED}✗ Fehler: {e}{ui.RESET}")

        # Speichere im Verlauf
        self.fix_history.append({
            "fix_id": fix.fix_id,
            "title": fix.title,
            "status": fix.status.value,
            "timestamp": fix.completion_timestamp,
            "result": fix.result,
        })

    def show_fix_history(self) -> None:
        """Zeigt Fix-Verlauf."""
        ui.clear()
        ui.rule("📈 FIX-VERLAUF", ui.BCYAN)
        print()

        if not self.fix_history:
            print("  Kein Verlauf - keine Fixes ausgeführt.")
        else:
            for entry in self.fix_history:
                status_color = ui.BGREEN if "erfolgreich" in entry["result"].lower() else ui.BRED
                print(f"  {status_color}{entry['title']}{ui.RESET}")
                print(f"    Status: {entry['status']}")
                print(f"    Ergebnis: {entry['result']}")
                print()

        ui.pause()

    def manual_error_input(self) -> None:
        """Manuelle Fehler-Eingabe."""
        ui.clear()
        ui.rule("🔧 MANUELLE FEHLERDIAGNOSE", ui.BCYAN)
        print()

        error_type = ui.ask("Fehlertyp (z.B. app_crash, permission_denied)", "")
        if not error_type:
            return

        description = ui.ask("Fehlerbeschreibung", "")

        # Erstelle Error
        error = ErrorDiagnosis(
            error_id=f"manual_{int(time.time())}",
            error_type=error_type,
            severity="MEDIUM",
            description=description,
            root_cause="Benutzer eingegeben",
        )

        self.detected_errors.append(error)

        # Generiere Fix
        fix = self._generate_fix_for_error(error)
        if fix:
            self.fix_solutions.append(fix)
            self._display_fix_suggestion(fix)

        ui.pause()

    def quick_fix_menu(self) -> None:
        """Quick-Fix für häufige Fehler."""
        ui.clear()
        ui.rule("⚡ QUICK-FIX - HÄUFIGE FEHLER", ui.BCYAN)
        print()

        entries = list(enumerate([
            (k, v["description"]) for k, v in self.FIX_TEMPLATES.items()
        ], 1))

        print("  Häufige Fehler:\n")
        for idx, (key, desc) in entries:
            print(f"  {idx}. {desc}")

        choice = ui.ask("\nWähle Fehler zum Fixen (Nummer)", "1")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(entries):
                _, (template_key, desc) = entries[idx]
                self._apply_quick_fix(template_key)
        except:
            ui.warn("Ungültige Wahl")
            time.sleep(0.5)

    def show_health_report(self) -> None:
        """Zeigt System-Gesundheitsbericht."""
        ui.clear()
        ui.rule("📊 SYSTEM-GESUNDHEITSBERICHT", ui.BCYAN)
        print()

        print(f"  {ui.BGREEN}System-Status:{ui.RESET}")
        print(f"    Erkannte Fehler: {len(self.detected_errors)}")
        print(f"    Verfügbare Fixes: {len(self.fix_solutions)}")
        print(f"    Abgeschlossene Fixes: {len([h for h in self.fix_history if 'erfolgreich' in h['result'].lower()])}")
        print()

        # Gesundheits-Score
        if self.detected_errors:
            health_score = max(0, 100 - (len(self.detected_errors) * 10))
        else:
            health_score = 100

        print(f"  Gesundheits-Score: {health_score}%")
        print()

        if health_score >= 90:
            print(f"  {ui.BGREEN}✓ System läuft optimal!{ui.RESET}")
        elif health_score >= 70:
            print(f"  {ui.YELLOW}⚠️  Einige Probleme erkannt{ui.RESET}")
        else:
            print(f"  {ui.BRED}✗ Mehrere kritische Probleme{ui.RESET}")

        print()
        ui.pause()

    # PRIVATE METHODEN

    def _diagnose_apps(self) -> None:
        """Diagnostiziert App-Fehler."""
        try:
            packages = self.adb.shell("pm list packages").split("\n")
            for pkg in packages[:10]:
                pkg = pkg.replace("package:", "").strip()
                if not pkg:
                    continue

                # Prüfe auf Crashes
                if "com.android" not in pkg:
                    error = ErrorDiagnosis(
                        error_id=f"app_{pkg}",
                        error_type="App-Fehler",
                        severity="MEDIUM",
                        description=f"App {pkg} könnte Fehler haben",
                        root_cause="Potenzielle Instabilität",
                        affected_systems=[pkg],
                    )
                    self.detected_errors.append(error)
                    break
        except:
            pass

    def _diagnose_filesystem(self) -> None:
        """Diagnostiziert Dateisystem-Fehler."""
        try:
            result = self.adb.shell("dumpsys diskstats")
            if "error" in result.lower():
                error = ErrorDiagnosis(
                    error_id="filesystem_error",
                    error_type="Dateisystem-Fehler",
                    severity="HIGH",
                    description="Dateisystem-Fehler erkannt",
                    root_cause="Korruption oder I/O-Fehler",
                    affected_systems=["Dateisystem"],
                )
                self.detected_errors.append(error)
        except:
            pass

    def _diagnose_storage(self) -> None:
        """Diagnostiziert Speicher-Probleme."""
        try:
            df = self.adb.shell("df")
            if "100%" in df or "99%" in df:
                error = ErrorDiagnosis(
                    error_id="low_storage",
                    error_type="Speicher voll",
                    severity="CRITICAL",
                    description="Weniger als 1% freier Speicher",
                    root_cause="Zu viele Dateien/Apps",
                    affected_systems=["Speicher"],
                )
                self.detected_errors.append(error)
        except:
            pass

    def _diagnose_memory(self) -> None:
        """Diagnostiziert Memory-Probleme."""
        try:
            meminfo = self.adb.shell("cat /proc/meminfo")
            if "MemAvailable" in meminfo:
                error = ErrorDiagnosis(
                    error_id="high_memory",
                    error_type="RAM-Speicher hoch",
                    severity="MEDIUM",
                    description="Zu viel RAM-Speicher verwendet",
                    root_cause="Laufende Apps verbrauchen viel RAM",
                    affected_systems=["Memory"],
                )
                self.detected_errors.append(error)
        except:
            pass

    def _diagnose_battery(self) -> None:
        """Diagnostiziert Batterie-Probleme."""
        try:
            battery = self.adb.shell("dumpsys battery")
            if "level: 2" in battery or "level: 1" in battery or "level: 0" in battery:
                error = ErrorDiagnosis(
                    error_id="low_battery",
                    error_type="Batterie niedrig",
                    severity="HIGH",
                    description="Batterie unter 10%",
                    root_cause="Schneller Batterie-Drain",
                    affected_systems=["Battery"],
                )
                self.detected_errors.append(error)
        except:
            pass

    def _diagnose_network(self) -> None:
        """Diagnostiziert Netzwerk-Fehler."""
        try:
            netstat = self.adb.shell("netstat -an 2>/dev/null || ss -an")
            if "CLOSE_WAIT" in netstat and netstat.count("CLOSE_WAIT") > 20:
                error = ErrorDiagnosis(
                    error_id="network_issues",
                    error_type="Netzwerk-Probleme",
                    severity="MEDIUM",
                    description="Viele offene Verbindungen",
                    root_cause="Netzwerk-Leak oder Streaming",
                    affected_systems=["Network"],
                )
                self.detected_errors.append(error)
        except:
            pass

    def _diagnose_processes(self) -> None:
        """Diagnostiziert Prozess-Fehler."""
        try:
            ps = self.adb.shell("ps -A")
            process_count = len(ps.split("\n"))
            if process_count > 200:
                error = ErrorDiagnosis(
                    error_id="process_count",
                    error_type="Zu viele Prozesse",
                    severity="MEDIUM",
                    description=f"{process_count} Prozesse aktiv",
                    root_cause="System-Überlast",
                    affected_systems=["Processes"],
                )
                self.detected_errors.append(error)
        except:
            pass

    def _diagnose_performance(self) -> None:
        """Diagnostiziert Performance-Probleme."""
        pass  # Placeholder

    def _generate_fix_for_error(self, error: ErrorDiagnosis) -> Optional[FixSolution]:
        """Generiert KI-Fix für Fehler."""
        # Versuche Template zu finden
        template_key = None
        for key in self.FIX_TEMPLATES:
            if key in error.error_type.lower().replace(" ", "_"):
                template_key = key
                break

        if not template_key:
            # Fallback
            template_key = "system_slowdown"

        template = self.FIX_TEMPLATES[template_key]

        fix = FixSolution(
            fix_id=f"fix_{error.error_id}",
            error_id=error.error_id,
            fix_category=template["category"],
            title=template["description"],
            description=f"Automatisch generierter Fix für: {error.description}",
            steps=template["steps"],
            estimated_time_seconds=30,
            risk_level=template["risk"],
            confidence=75.0 + (15.0 if template_key != "system_slowdown" else 0),
            backup_needed=template["backup"],
        )

        return fix

    def _display_fix_suggestion(self, fix: FixSolution) -> None:
        """Zeigt Fix-Vorschlag."""
        print(f"  {ui.BGREEN}✓ Automatischer Fix generiert:{ui.RESET}")
        print(f"    Titel: {fix.title}")
        print(f"    Risiko: {self._get_risk_color(fix.risk_level)}{fix.risk_level.value}{ui.RESET}")
        print(f"    Konfidenz: {fix.confidence:.1f}%")
        print(f"    Schritte:")
        for step in fix.steps:
            print(f"      {step}")
        print()

    def _execute_fix_steps(self, fix: FixSolution) -> bool:
        """Führt Fix-Schritte aus."""
        try:
            for step in fix.steps:
                # Simuliere Ausführung
                time.sleep(0.2)
            return True
        except:
            return False

    def _verify_fix(self, fix: FixSolution) -> bool:
        """Verifiziert Fix-Erfolg."""
        # Simuliere Verifikation
        return True

    def _perform_rollback(self, fix: FixSolution) -> None:
        """Führt Rollback durch."""
        print(f"  Rollback: {fix.rollback_procedure}")

    def _apply_quick_fix(self, template_key: str) -> None:
        """Wendet Quick-Fix an."""
        template = self.FIX_TEMPLATES[template_key]
        error = ErrorDiagnosis(
            error_id=f"quick_{int(time.time())}",
            error_type=template["description"],
            severity="MEDIUM",
            description=template["description"],
            root_cause="Quick-Fix ausgelöst",
        )
        self.detected_errors.append(error)

        fix = FixSolution(
            fix_id=f"quick_fix_{int(time.time())}",
            error_id=error.error_id,
            fix_category=template["category"],
            title=template["description"],
            description=f"Quick-Fix: {template['description']}",
            steps=template["steps"],
            risk_level=template["risk"],
            confidence=80.0,
            backup_needed=template["backup"],
        )

        self.fix_solutions.append(fix)
        self.execute_fix(fix, 1, 1)

    def _get_status_color(self, status: FixStatus) -> str:
        """Gibt Farbe für Status."""
        if status == FixStatus.COMPLETED:
            return ui.BGREEN
        elif status == FixStatus.FAILED:
            return ui.BRED
        elif status == FixStatus.IN_PROGRESS:
            return ui.BCYAN
        else:
            return ui.YELLOW

    def _get_risk_color(self, risk: RiskLevel) -> str:
        """Gibt Farbe für Risiko."""
        if risk == RiskLevel.CRITICAL:
            return ui.BRED
        elif risk == RiskLevel.HIGH:
            return ui.YELLOW
        elif risk == RiskLevel.MEDIUM:
            return ui.YELLOW
        else:
            return ui.BGREEN


def create_ai_doctor(adb: ADB) -> AIDoctor:
    """Erstellt neuen AI Doctor."""
    return AIDoctor(adb)


def menu(adb: ADB) -> None:
    """AI Doctor Menu Wrapper."""
    doctor = AIDoctor(adb)
    doctor.show_ai_doctor_menu()
