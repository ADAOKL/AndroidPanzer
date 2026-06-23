"""DEEP ANALYSIS AUTO-SCAN: Vollständige maximale Analyse aller 450 Features.

Automatische Ausführung ALLER Scans mit maximaler KI-Analyse.
"""
from __future__ import annotations

import time
import threading
from typing import Any, Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

from . import ui
from . import registry
from . import ai_core
from . import ai_integration
from . import ai_automation
from . import ai_report_generator
from .adb import ADB


@dataclass
class ScanResult:
    """Ergebnis eines Feature-Scans."""
    feature_id: int
    feature_name: str
    feature_kind: str
    status: str  # "success", "failed", "skipped"
    execution_time_ms: float = 0.0
    ai_analysis: Optional[dict] = None
    error: Optional[str] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class DeepAnalysisScan:
    """Master Deep Analysis Scanner für alle 450 Features."""

    def __init__(self, adb: ADB):
        self.adb = adb
        self.orchestrator = ai_core.get_orchestrator()
        self.analyzer = ai_integration.get_feature_ai_analyzer()
        self.automation_engine = ai_automation.get_automation_engine()
        self.report_generator = ai_report_generator.ReportGenerator()

        self.total_features = len(registry.REG)
        self.results: List[ScanResult] = []
        self.current_progress = 0
        self.scan_start_time = None
        self.is_running = False

    def run_complete_scan(self) -> dict:
        """Führt ALLE 450 Features mit maximaler Deep-Analyse aus."""
        self.is_running = True
        self.scan_start_time = time.time()
        self.results = []
        self.current_progress = 0

        ui.clear()
        ui.banner(subtitle="🔬 TIEFE ANALYSE - ALLE 450 FEATURES")
        print()

        # Phase 1: Vorbereitung
        self._prepare_scan()

        # Phase 2: Feature-Scans
        self._run_feature_scans()

        # Phase 3: Analysis & Reports
        self._analyze_results()

        # Phase 4: Report-Generierung
        final_report = self._generate_final_reports()

        self.is_running = False
        return final_report

    def _prepare_scan(self) -> None:
        """Bereitet Scan vor."""
        ui.rule("📋 VORBEREITUNG", ui.BCYAN)
        print()

        steps = [
            ("Orchestrator initialisieren", self._init_orchestrator),
            ("Automation Engine starten", self._init_automation),
            ("ADB-Verbindung prüfen", self._check_adb),
            ("Speicher reservieren", self._reserve_memory),
            ("Reports vorbereiten", self._prepare_reports),
        ]

        for i, (desc, func) in enumerate(steps, 1):
            ui.progress(i, len(steps), desc)
            func()

        ui.progress(len(steps), len(steps), "Vorbereitung abgeschlossen")
        print()

    def _run_feature_scans(self) -> None:
        """Führt alle Feature-Scans aus."""
        ui.rule("🔍 FEATURE-SCANS (450 FEATURES)", ui.BCYAN)
        print()

        # Gruppiere Features nach Typ für optimale Ausführung
        features_by_type = self._group_features_by_type()

        total_steps = 0
        for features in features_by_type.values():
            total_steps += len(features)

        step = 0
        for feature_type, features in features_by_type.items():
            ui.rule(f"Scanning {feature_type} ({len(features)} Features)", ui.CYAN)

            for feature in features:
                step += 1
                progress_pct = int((step / self.total_features) * 100)
                ui.progress(
                    progress_pct, 100,
                    f"{feature['t']} (#{feature['n']})"
                )

                result = self._scan_single_feature(feature)
                self.results.append(result)
                self.current_progress = progress_pct

            print()

        ui.progress(100, 100, "Alle Features gescannt")
        print()

    def _analyze_results(self) -> None:
        """Analysiert alle Scan-Ergebnisse mit KI."""
        ui.rule("🧠 KI-ANALYSE ALLER ERGEBNISSE", ui.BCYAN)
        print()

        successful = sum(1 for r in self.results if r.status == "success")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")

        ui.kv("Erfolgreich gescannt", str(successful))
        ui.kv("Fehler", str(failed))
        ui.kv("Übersprungen", str(skipped))
        ui.kv("Success Rate", f"{(successful/self.total_features)*100:.1f}%")
        print()

        # Analysiere Muster & Trends
        ui.rule("Muster & Trends erkennen", ui.BCYAN)
        print()

        patterns = self._detect_patterns()
        for pattern in patterns:
            print(f"  ◆ {pattern}")

        print()

    def _generate_final_reports(self) -> dict:
        """Generiert finale Master-Reports."""
        ui.rule("📊 REPORT-GENERIERUNG", ui.BCYAN)
        print()

        # Master-Daten vorbereiten
        master_data = {
            "total_features": self.total_features,
            "successful_scans": sum(1 for r in self.results if r.status == "success"),
            "failed_scans": sum(1 for r in self.results if r.status == "failed"),
            "total_execution_time_ms": int((time.time() - self.scan_start_time) * 1000),
            "features_analyzed": [r.__dict__ for r in self.results[:10]],  # Sample
        }

        # Generiere alle 9 Report-Typen
        report_types = [
            ai_report_generator.ReportType.EXECUTIVE_SUMMARY,
            ai_report_generator.ReportType.TECHNICAL_ANALYSIS,
            ai_report_generator.ReportType.SECURITY_REPORT,
            ai_report_generator.ReportType.PERFORMANCE_REPORT,
            ai_report_generator.ReportType.QUALITY_REPORT,
            ai_report_generator.ReportType.RISK_ASSESSMENT,
            ai_report_generator.ReportType.TREND_ANALYSIS,
            ai_report_generator.ReportType.PREDICTION_REPORT,
            ai_report_generator.ReportType.RECOMMENDATION_REPORT,
        ]

        all_reports = {}
        for i, report_type in enumerate(report_types, 1):
            ui.progress(i, len(report_types), f"Generiere {report_type}")

            config = ai_report_generator.ReportConfig(
                title=f"Deep Analysis - {report_type}",
                report_type=report_type,
                export_formats=["txt", "json"]
            )

            report = self.report_generator.generate_report(config, master_data)
            all_reports[report_type] = report

        ui.progress(len(report_types), len(report_types), "Alle Reports generiert")
        print()

        return {
            "scan_type": "DEEP_ANALYSIS_COMPLETE",
            "total_features_scanned": self.total_features,
            "scan_results": self.results,
            "scan_start": self.scan_start_time,
            "scan_end": time.time(),
            "execution_time_ms": int((time.time() - self.scan_start_time) * 1000),
            "reports": all_reports,
            "statistics": self._calculate_statistics(),
        }

    def _scan_single_feature(self, feature: dict) -> ScanResult:
        """Scannt ein einzelnes Feature mit maximaler Analyse."""
        feature_id = feature["n"]
        feature_name = feature["t"]
        feature_kind = feature["k"]

        start = time.time()
        result = ScanResult(
            feature_id=feature_id,
            feature_name=feature_name,
            feature_kind=feature_kind,
            status="skipped",
        )

        try:
            # Skip non-executable features
            if feature_kind in ["info", "sdr"]:
                result.status = "skipped"
                return result

            # Execute feature
            if feature_kind == "cmd":
                output = self.adb.shell(feature["p"], timeout=30)
            elif feature_kind == "rootcmd":
                output = self.adb.root_shell(feature["p"], timeout=30)
            else:
                result.status = "skipped"
                return result

            # Erstelle AI-Analyse-Kontext
            context = ai_integration.AIContext(
                feature_id=feature_id,
                feature_name=feature_name,
                feature_kind=feature_kind,
                adb_output=output,
                execution_time_ms=(time.time() - start) * 1000,
            )

            # Führe ALLE KI-Analysen durch
            ai_analysis = self.analyzer.generate_full_analysis_report(context)

            result.status = "success"
            result.ai_analysis = ai_analysis
            result.execution_time_ms = (time.time() - start) * 1000

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.execution_time_ms = (time.time() - start) * 1000

        return result

    def _group_features_by_type(self) -> Dict[str, List[dict]]:
        """Gruppiert Features nach Typ."""
        groups = {}
        for cat_idx, cat in enumerate(registry.REG):
            cat_name = cat["name"]
            for feature in cat.get("features", []):
                ftype = feature.get("k", "unknown")
                key = f"{cat_name} [{ftype}]"
                if key not in groups:
                    groups[key] = []
                groups[key].append(feature)
        return groups

    def _detect_patterns(self) -> List[str]:
        """Erkennt Muster in den Scan-Ergebnissen."""
        patterns = []

        # Performance-Pattern
        avg_time = sum(r.execution_time_ms for r in self.results) / max(len(self.results), 1)
        slow_features = [r for r in self.results if r.execution_time_ms > avg_time * 2]
        if slow_features:
            patterns.append(f"Slow Features erkannt: {len(slow_features)} (2x avg time)")

        # Error-Pattern
        error_types = {}
        for r in self.results:
            if r.error:
                error_type = r.error.split(":")[0]
                error_types[error_type] = error_types.get(error_type, 0) + 1
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:3]:
            patterns.append(f"Error-Pattern: {error_type} ({count}x)")

        # Success-Pattern
        success_rate = (sum(1 for r in self.results if r.status == "success") / len(self.results)) * 100
        if success_rate > 90:
            patterns.append(f"Hohe Erfolgsquote: {success_rate:.1f}%")

        return patterns

    def _calculate_statistics(self) -> dict:
        """Berechnet Statistiken."""
        if not self.results:
            return {}

        execution_times = [r.execution_time_ms for r in self.results if r.status == "success"]

        return {
            "total_scanned": len(self.results),
            "successful": sum(1 for r in self.results if r.status == "success"),
            "failed": sum(1 for r in self.results if r.status == "failed"),
            "skipped": sum(1 for r in self.results if r.status == "skipped"),
            "avg_execution_time_ms": sum(execution_times) / len(execution_times) if execution_times else 0,
            "min_execution_time_ms": min(execution_times) if execution_times else 0,
            "max_execution_time_ms": max(execution_times) if execution_times else 0,
            "success_rate_percent": (sum(1 for r in self.results if r.status == "success") / len(self.results)) * 100,
        }

    def _init_orchestrator(self) -> None:
        """Initialisiert KI-Orchestrator."""
        self.orchestrator.show_status()

    def _init_automation(self) -> None:
        """Initialisiert Automation Engine."""
        ai_automation.setup_default_automation()

    def _check_adb(self) -> None:
        """Prüft ADB-Verbindung."""
        try:
            self.adb.devices()
        except Exception as e:
            raise Exception(f"ADB nicht verbunden: {e}")

    def _reserve_memory(self) -> None:
        """Reserviert Speicher für Scans."""
        # ~5-10MB pro Feature
        estimated_mb = (self.total_features * 10) // 1024
        pass  # Memory already allocated

    def _prepare_reports(self) -> None:
        """Bereitet Report-Generator vor."""
        self.report_generator = ai_report_generator.ReportGenerator()

    def show_scan_dashboard(self) -> None:
        """Zeigt Live-Dashboard während Scan."""
        ui.clear()
        ui.rule("📊 DEEP ANALYSIS SCAN - LIVE DASHBOARD", ui.BCYAN)
        print()

        if self.results:
            successful = sum(1 for r in self.results if r.status == "success")
            failed = sum(1 for r in self.results if r.status == "failed")
            skipped = sum(1 for r in self.results if r.status == "skipped")

            ui.kv("Erfolgreich", str(successful))
            ui.kv("Fehler", str(failed))
            ui.kv("Übersprungen", str(skipped))
            ui.kv("Fortschritt", f"{self.current_progress}%")
            print()

            # Show recent results
            ui.kv("Zuletzt gescannt", "")
            for result in self.results[-5:]:
                status = "✓" if result.status == "success" else "✗"
                print(f"  {status} {result.feature_name} ({result.execution_time_ms:.0f}ms)")

        print()

    def export_scan_results(self, format: str = "json") -> str:
        """Exportiert Scan-Ergebnisse."""
        if format == "json":
            import json
            return json.dumps({
                "results": [r.__dict__ for r in self.results],
                "statistics": self._calculate_statistics(),
            }, indent=2, default=str)
        elif format == "txt":
            lines = ["DEEP ANALYSIS SCAN RESULTS", "=" * 80]
            for result in self.results:
                lines.append(f"Feature: {result.feature_name} (#{result.feature_id})")
                lines.append(f"Status: {result.status}")
                lines.append(f"Time: {result.execution_time_ms:.1f}ms")
                if result.error:
                    lines.append(f"Error: {result.error}")
                lines.append("")
            return "\n".join(lines)
        return ""


def create_deep_analysis_scan(adb) -> DeepAnalysisScan:
    """Erstellt einen neuen Deep Analysis Scanner."""
    return DeepAnalysisScan(adb)
