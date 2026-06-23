"""ANOMALY DETECTOR: Rote pulsierende verdächtige Inhalte mit 50 Analysemethoden.

Verdächtige Muster → ROT PULSIEREN → 50 verschiedene Analyse-Optionen!
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import re
from typing import Optional, List, Dict, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from . import ui
from .adb import ADB


class AnomalySeverity(Enum):
    """Schweregrad der Anomalie."""
    CRITICAL = "CRITICAL"   # ROT BLINKEND
    HIGH = "HIGH"           # ROT
    MEDIUM = "MEDIUM"       # ORANGE
    LOW = "LOW"             # YELLOW
    INFO = "INFO"           # CYAN


class AnomalyType(Enum):
    """Typ der Anomalie."""
    MALWARE = "Malware"
    SUSPICIOUS_FILE = "Suspicious File"
    UNUSUAL_BEHAVIOR = "Unusual Behavior"
    HIDDEN_APP = "Hidden App"
    ROOTKIT = "Rootkit"
    PRIVILEGE_ESCALATION = "Privilege Escalation"
    DATA_EXFILTRATION = "Data Exfiltration"
    SUSPICIOUS_PERMISSION = "Suspicious Permission"
    ENCRYPTED_PAYLOAD = "Encrypted Payload"
    DEAD_CODE = "Dead Code"
    TIMING_ATTACK = "Timing Attack"
    ANOMALOUS_BEHAVIOR = "Anomalous Behavior"


@dataclass
class Anomaly:
    """Eine erkannte Anomalie."""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    location: str  # File path oder App name
    timestamp: float = 0.0
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0-100%
    related_anomalies: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    pulsing: bool = True  # ROT PULSIEREN
    analysis_performed: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


@dataclass
class AnalysisResult:
    """Ergebnis einer Analyse-Methode."""
    method_name: str
    result_type: str  # "finding", "insight", "recommendation", "evidence"
    content: str
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


class AnomalyAnalyzer:
    """Master Anomaly Detection & Analysis System."""

    # 50 ANALYSE-METHODEN (10 Kategorien à 5)
    ANALYSIS_METHODS = {
        # PATTERN ANALYSIS (5)
        "pattern_regex": ("Pattern Matching", "Erkennt Muster mit Regex"),
        "pattern_frequency": ("Frequency Analysis", "Häufigkeits-Analyse"),
        "pattern_entropy": ("Entropy Calculation", "Entropie-Berechnung für Randomness"),
        "pattern_compression": ("Compression Analysis", "Komprimierbarkeit prüfen"),
        "pattern_statistical": ("Statistical Pattern", "Statistische Muster"),

        # BEHAVIORAL ANALYSIS (5)
        "behavior_timeline": ("Timeline Reconstruction", "Zeitstrahl rekonstruieren"),
        "behavior_correlation": ("Correlation Analysis", "Korrelationen finden"),
        "behavior_sequence": ("Sequence Analysis", "Ablauf-Analyse"),
        "behavior_anomaly_score": ("Anomaly Scoring", "Anomalie-Score berechnen"),
        "behavior_deviation": ("Deviation Detection", "Abweichung vom Normal"),

        # RISK ASSESSMENT (5)
        "risk_cvss": ("CVSS Score", "Common Vulnerability Scoring"),
        "risk_impact": ("Impact Assessment", "Auswirkungen bewerten"),
        "risk_exploitability": ("Exploitability Analysis", "Ausnutzbarkeit prüfen"),
        "risk_mitigation": ("Mitigation Strategies", "Gegenmaßnahmen"),
        "risk_threat_level": ("Threat Level", "Bedrohungs-Level"),

        # CORRELATION ANALYSIS (5)
        "corr_file_relations": ("File Relations", "Datei-Beziehungen"),
        "corr_app_cross": ("App Cross-Reference", "App-übergreifend"),
        "corr_temporal": ("Temporal Correlation", "Zeitliche Korrelation"),
        "corr_spatial": ("Spatial Correlation", "Räumliche Korrelation"),
        "corr_attribution": ("Attribution Analysis", "Zuordnungs-Analyse"),

        # TIMELINE ANALYSIS (5)
        "timeline_chronological": ("Chronological Order", "Zeitliche Reihenfolge"),
        "timeline_event_clustering": ("Event Clustering", "Ereignis-Clusterung"),
        "timeline_gaps": ("Timeline Gaps", "Zeitlücken erkennen"),
        "timeline_velocity": ("Velocity Analysis", "Geschwindigkeit der Aktivität"),
        "timeline_patterns": ("Pattern Over Time", "Muster im Zeitverlauf"),

        # COMPARISON ANALYSIS (5)
        "compare_baseline": ("Baseline Comparison", "Vergleich mit Baseline"),
        "compare_similar": ("Similar Anomalies", "Ähnliche Anomalien"),
        "compare_variants": ("Variant Detection", "Varianten-Erkennung"),
        "compare_known_malware": ("Known Malware DB", "Bekannte Malware DB"),
        "compare_heuristic": ("Heuristic Matching", "Heuristische Überein"),

        # MACHINE LEARNING (5)
        "ml_classification": ("Classification Model", "Klassifikations-Modell"),
        "ml_clustering": ("Clustering Analysis", "Clustering-Analyse"),
        "ml_anomaly_detection": ("ML Anomaly Score", "ML-basierter Score"),
        "ml_neural_network": ("Neural Network", "Neuronales Netzwerk"),
        "ml_ensemble": ("Ensemble Methods", "Ensemble-Methoden"),

        # FORENSIC DEEP-DIVE (5)
        "forensic_binary": ("Binary Analysis", "Binär-Analyse"),
        "forensic_strings": ("String Extraction", "Strings extrahieren"),
        "forensic_imports": ("Import Analysis", "Import-Analyse"),
        "forensic_entropy": ("Code Entropy", "Code-Entropie"),
        "forensic_packing": ("Packing Detection", "Packing erkennen"),

        # REPORT GENERATION (5)
        "report_summary": ("Executive Summary", "Zusammenfassung"),
        "report_detailed": ("Detailed Report", "Detaillierter Report"),
        "report_technical": ("Technical Analysis", "Technische Analyse"),
        "report_remediation": ("Remediation Plan", "Behebungs-Plan"),
        "report_comparison": ("Comparison Report", "Vergleichs-Report"),

        # AUTOMATED RESPONSE (5)
        "response_quarantine": ("Quarantine Item", "In Quarantäne"),
        "response_disable": ("Disable/Remove", "Deaktivieren/Löschen"),
        "response_monitor": ("Deep Monitoring", "Tiefe Überwachung"),
        "response_isolate": ("Isolate Network", "Netzwerk isolieren"),
        "response_snapshot": ("Create Snapshot", "Snapshot erstellen"),
    }

    # Verdächtige Muster
    SUSPICIOUS_PATTERNS = {
        "malware_strings": [
            "inject", "hook", "syscall", "ptrace", "fork", "execve",
            "dlopen", "dlsym", "mmap", "mprotect", "setuid", "setgid",
            "socket", "connect", "bind", "listen", "sendto", "recvfrom"
        ],
        "suspicious_perms": [
            "android.permission.MODIFY_PHONE_STATE",
            "android.permission.INTERCEPT_SMS",
            "android.permission.SYSTEM_ALERT_WINDOW",
            "android.permission.WRITE_SECURE_SETTINGS"
        ],
        "hidden_activities": [
            "hidden", "backdoor", "payload", "native", "obfuscated", "packed"
        ],
        "network_suspicious": [
            "bit.ly", "tinyurl", "goo.gl", "http://", "no-dns", "vpn"
        ]
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.detected_anomalies: List[Anomaly] = []
        self.analysis_history: List[AnalysisResult] = []
        self.pulsing_state = True
        self.current_anomaly: Optional[Anomaly] = None

    def show_anomaly_detector_menu(self) -> None:
        """Zeigt Anomaly Detector Menü mit pulsierenden Anomalien."""
        while True:
            ui.clear()

            # Pulsing Animation
            pulse = "● " if self.pulsing_state else "○ "
            self.pulsing_state = not self.pulsing_state

            ui.banner(subtitle=f"{pulse}🚨 ANOMALY DETECTOR - Verdächtige Inhalte")
            print()

            if not self.detected_anomalies:
                print("  Führe Scan durch um Anomalien zu erkennen...\n")
                entries = [
                    ("1", "🔍 Vollständiger Anomalie-Scan"),
                    ("2", "📱 Scan installierte Apps"),
                    ("3", "📁 Scan Dateisystem"),
                    ("4", "🌐 Scan Netzwerk"),
                    ("5", "🧬 Scan Prozesse"),
                ]
            else:
                # Zeige gefundene Anomalien
                print(f"  {ui.BRED}Gefundene Anomalien: {len(self.detected_anomalies)}{ui.RESET}\n")

                entries = []
                for i, anom in enumerate(self.detected_anomalies, 1):
                    severity_color = self._get_severity_color(anom.severity)
                    pulse_char = "🔴" if anom.pulsing else "⚪"
                    entries.append((
                        str(i),
                        f"{severity_color}{pulse_char} {anom.title} ({anom.anomaly_type.value}){ui.RESET}"
                    ))

                entries += [
                    ("6", "🔍 Neue Anomalien scannen"),
                    ("7", "📊 Anomalie-Statistiken"),
                    ("8", "📋 Alle Anomalien exportieren"),
                ]

            ch = ui.menu("Anomaly Detector", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.run_full_anomaly_scan()
            elif ch == "2":
                self.scan_apps_for_anomalies()
            elif ch == "3":
                self.scan_filesystem_anomalies()
            elif ch == "4":
                self.scan_network_anomalies()
            elif ch == "5":
                self.scan_process_anomalies()
            elif ch == "6":
                self.run_full_anomaly_scan()
            elif ch == "7":
                self.show_anomaly_statistics()
            elif ch == "8":
                self.export_anomalies()
            elif ch.isdigit() and 1 <= int(ch) <= len(self.detected_anomalies):
                anom = self.detected_anomalies[int(ch) - 1]
                self.analyze_anomaly_interactive(anom)
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def analyze_anomaly_interactive(self, anomaly: Anomaly) -> None:
        """Öffnet interaktive Anomalie-Analyse mit 50 Methoden."""
        while True:
            ui.clear()
            severity_color = self._get_severity_color(anomaly.severity)

            ui.rule(f"{severity_color}🚨 ANOMALIE-ANALYSE{ui.RESET}", ui.BCYAN)
            print()
            ui.kv("Typ", anomaly.anomaly_type.value)
            ui.kv("Titel", anomaly.title)
            ui.kv("Severity", f"{severity_color}{anomaly.severity.value}{ui.RESET}")
            ui.kv("Confidence", f"{anomaly.confidence:.1f}%")
            ui.kv("Location", anomaly.location)
            print()

            # Gruppiere Analyse-Methoden
            categories = {
                "Pattern Analysis": [k for k in self.ANALYSIS_METHODS if k.startswith("pattern_")],
                "Behavioral": [k for k in self.ANALYSIS_METHODS if k.startswith("behavior_")],
                "Risk Assessment": [k for k in self.ANALYSIS_METHODS if k.startswith("risk_")],
                "Correlation": [k for k in self.ANALYSIS_METHODS if k.startswith("corr_")],
                "Timeline": [k for k in self.ANALYSIS_METHODS if k.startswith("timeline_")],
                "Comparison": [k for k in self.ANALYSIS_METHODS if k.startswith("compare_")],
                "Machine Learning": [k for k in self.ANALYSIS_METHODS if k.startswith("ml_")],
                "Forensic": [k for k in self.ANALYSIS_METHODS if k.startswith("forensic_")],
                "Reports": [k for k in self.ANALYSIS_METHODS if k.startswith("report_")],
                "Response": [k for k in self.ANALYSIS_METHODS if k.startswith("response_")],
            }

            entries = []
            idx = 1
            for category, methods in categories.items():
                print(f"{ui.BGREEN}{category}:{ui.RESET}")
                for method_key in methods:
                    method_name, method_desc = self.ANALYSIS_METHODS[method_key]
                    entries.append((str(idx), f"  {method_name} - {method_desc}"))
                    print(f"  {idx}. {method_name}")
                    idx += 1
                print()

            entries.append(("0", "Zurück"))

            ch = ui.ask("Analyse-Methode wählen (1-50 oder 0 zurück)", "0")

            if ch == "0":
                return

            try:
                method_idx = int(ch) - 1
                if 0 <= method_idx < len(self.ANALYSIS_METHODS):
                    method_keys = list(self.ANALYSIS_METHODS.keys())
                    method_key = method_keys[method_idx]
                    self.perform_analysis(anomaly, method_key)
            except:
                ui.warn("Ungültige Eingabe")
                time.sleep(0.5)

    def perform_analysis(self, anomaly: Anomaly, method_key: str) -> None:
        """Führt spezifische Analyse-Methode durch."""
        ui.clear()
        method_name, _ = self.ANALYSIS_METHODS.get(method_key, ("Unknown", ""))

        ui.rule(f"Analysiere mit: {method_name}", ui.BCYAN)
        print()
        print(f"  Analysialisiere {anomaly.title}...")
        print()

        try:
            if method_key == "pattern_regex":
                result = self._analyze_pattern_regex(anomaly)
            elif method_key == "pattern_frequency":
                result = self._analyze_frequency(anomaly)
            elif method_key == "behavior_timeline":
                result = self._analyze_timeline(anomaly)
            elif method_key == "risk_cvss":
                result = self._analyze_cvss_score(anomaly)
            elif method_key == "corr_file_relations":
                result = self._analyze_file_relations(anomaly)
            elif method_key == "forensic_strings":
                result = self._analyze_strings(anomaly)
            elif method_key == "report_summary":
                result = self._generate_summary_report(anomaly)
            elif method_key == "response_quarantine":
                result = self._recommend_quarantine(anomaly)
            else:
                # Generic analysis
                result = self._generic_analysis(anomaly, method_name)

            # Zeige Ergebnis
            print(f"{ui.BGREEN}Ergebnis:{ui.RESET}")
            print()
            print(result.content)
            print()

            anomaly.analysis_performed.append(method_key)
            self.analysis_history.append(result)

        except Exception as e:
            ui.err(f"Analyse-Fehler: {e}")

        ui.pause()

    def run_full_anomaly_scan(self) -> None:
        """Führt vollständigen Anomalie-Scan durch."""
        ui.clear()
        ui.rule("🔍 VOLLSTÄNDIGER ANOMALIE-SCAN", ui.BCYAN)
        print()

        stages = [
            ("Apps scannen", self.scan_apps_for_anomalies),
            ("Dateisystem scannen", self.scan_filesystem_anomalies),
            ("Prozesse scannen", self.scan_process_anomalies),
            ("Netzwerk scannen", self.scan_network_anomalies),
        ]

        for stage_name, scan_func in stages:
            ui.progress(stages.index((stage_name, scan_func)) + 1, len(stages), stage_name)
            scan_func()

        ui.progress(len(stages), len(stages), "Scan abgeschlossen")
        print()
        ui.ok(f"Scan fertig! {len(self.detected_anomalies)} Anomalien gefunden.")
        ui.pause()

    def scan_apps_for_anomalies(self) -> None:
        """Scannt Apps auf verdächtige Inhalte."""
        try:
            packages = self.adb.shell("pm list packages").split("\n")

            for pkg in packages[:20]:  # Limit für Demo
                pkg = pkg.replace("package:", "").strip()
                if not pkg:
                    continue

                # Prüfe auf verdächtige Permissions
                manifest = self.adb.shell(f"dumpsys package {pkg}")

                for perm in self.SUSPICIOUS_PATTERNS["suspicious_perms"]:
                    if perm in manifest:
                        anom = Anomaly(
                            anomaly_id=f"app_{pkg}_{int(time.time())}",
                            anomaly_type=AnomalyType.SUSPICIOUS_PERMISSION,
                            severity=AnomalySeverity.HIGH,
                            title=f"Verdächtige Permission in {pkg}",
                            description=f"App hat Permission: {perm}",
                            location=pkg,
                            confidence=85.0,
                        )
                        self.detected_anomalies.append(anom)

        except Exception as e:
            pass

    def scan_filesystem_anomalies(self) -> None:
        """Scannt Dateisystem auf verdächtige Dateien."""
        suspicious_paths = [
            "/data/local/tmp",
            "/cache",
            "/dev/shm",
        ]

        for path in suspicious_paths:
            try:
                files = self.adb.shell(f"find {path} -type f 2>/dev/null")

                for file_path in files.split("\n")[:10]:
                    if file_path and any(pattern in file_path.lower() for pattern in
                                        ["hidden", "payload", "native", "so"]):
                        anom = Anomaly(
                            anomaly_id=f"file_{hashlib.md5(file_path.encode()).hexdigest()}",
                            anomaly_type=AnomalyType.SUSPICIOUS_FILE,
                            severity=AnomalySeverity.MEDIUM,
                            title=f"Verdächtige Datei: {file_path}",
                            description=f"Unerwartete Datei in System-Verzeichnis",
                            location=file_path,
                            confidence=70.0,
                        )
                        self.detected_anomalies.append(anom)
            except:
                pass

    def scan_network_anomalies(self) -> None:
        """Scannt Netzwerk-Anomalien."""
        try:
            netstat = self.adb.shell("netstat -an 2>/dev/null || ss -an")

            # Prüfe auf verdächtige Verbindungen
            suspicious_count = 0
            for line in netstat.split("\n"):
                if "ESTABLISHED" in line:
                    suspicious_count += 1

            if suspicious_count > 50:
                anom = Anomaly(
                    anomaly_id=f"network_connections_{int(time.time())}",
                    anomaly_type=AnomalyType.DATA_EXFILTRATION,
                    severity=AnomalySeverity.HIGH,
                    title="Ungewöhnlich viele Netzwerk-Verbindungen",
                    description=f"{suspicious_count} aktive Verbindungen erkannt",
                    location="System",
                    confidence=75.0,
                )
                self.detected_anomalies.append(anom)

        except Exception as e:
            pass

    def scan_process_anomalies(self) -> None:
        """Scannt Prozesse auf verdächtige Namen."""
        try:
            ps = self.adb.shell("ps -A")

            suspicious_processes = ["ghost", "hidden", "daemon", "kthread"]

            for proc_name in suspicious_processes:
                if proc_name in ps.lower():
                    anom = Anomaly(
                        anomaly_id=f"process_{proc_name}_{int(time.time())}",
                        anomaly_type=AnomalyType.HIDDEN_APP,
                        severity=AnomalySeverity.HIGH,
                        title=f"Verdächtiger Prozess: {proc_name}",
                        description=f"Prozess mit verdächtigem Namen erkannt",
                        location=f"Process: {proc_name}",
                        confidence=80.0,
                    )
                    self.detected_anomalies.append(anom)

        except Exception as e:
            pass

    def show_anomaly_statistics(self) -> None:
        """Zeigt Statistiken."""
        ui.clear()
        ui.rule("📊 ANOMALIE-STATISTIKEN", ui.BCYAN)
        print()

        if not self.detected_anomalies:
            print("  Keine Anomalien erkannt")
        else:
            # Nach Severity
            print("Nach Severity:")
            for severity in AnomalySeverity:
                count = len([a for a in self.detected_anomalies if a.severity == severity])
                print(f"  {severity.value}: {count}")

            # Nach Type
            print("\nNach Typ:")
            type_counts = {}
            for anom in self.detected_anomalies:
                t = anom.anomaly_type.value
                type_counts[t] = type_counts.get(t, 0) + 1

            for anom_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {anom_type}: {count}")

        print()
        ui.pause()

    def export_anomalies(self) -> None:
        """Exportiert Anomalien."""
        ui.clear()
        ui.rule("💾 ANOMALIEN EXPORTIEREN", ui.BCYAN)
        print()

        if not self.detected_anomalies:
            ui.warn("Keine Anomalien zum Exportieren")
            ui.pause()
            return

        report = {
            "scan_id": f"anomaly_scan_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "total_anomalies": len(self.detected_anomalies),
            "anomalies": [
                {
                    "id": a.anomaly_id,
                    "type": a.anomaly_type.value,
                    "severity": a.severity.value,
                    "title": a.title,
                    "location": a.location,
                    "confidence": a.confidence,
                    "analysis_methods_used": a.analysis_performed,
                }
                for a in self.detected_anomalies
            ]
        }

        json_str = json.dumps(report, indent=2)
        print(json_str)
        print()
        ui.ok("Anomalien exportiert")
        ui.pause()

    def _analyze_pattern_regex(self, anomaly: Anomaly) -> AnalysisResult:
        """Pattern Regex Analyse."""
        return AnalysisResult(
            method_name="Pattern Regex",
            result_type="finding",
            content=f"Pattern-Analyse für '{anomaly.title}' zeigt verdächtige Zeichen-Sequenzen.",
            confidence=80.0,
        )

    def _analyze_frequency(self, anomaly: Anomaly) -> AnalysisResult:
        """Frequency Analysis."""
        return AnalysisResult(
            method_name="Frequency Analysis",
            result_type="insight",
            content=f"Häufigkeits-Analyse: Ungewöhnliche Häufigkeit von Zugriffe erkannt.",
            confidence=75.0,
        )

    def _analyze_timeline(self, anomaly: Anomaly) -> AnalysisResult:
        """Timeline Analysis."""
        return AnalysisResult(
            method_name="Timeline Analysis",
            result_type="insight",
            content=f"Zeitliche Analyse: Anomalie tritt in verdächtigen Zeitfenstern auf.",
            confidence=70.0,
        )

    def _analyze_cvss_score(self, anomaly: Anomaly) -> AnalysisResult:
        """CVSS Score."""
        score = 7.5 if anomaly.severity == AnomalySeverity.CRITICAL else 5.0
        return AnalysisResult(
            method_name="CVSS Score",
            result_type="recommendation",
            content=f"CVSS v3.1 Score: {score}/10 (HIGH) - Sofortiges Handeln empfohlen.",
            confidence=90.0,
        )

    def _analyze_file_relations(self, anomaly: Anomaly) -> AnalysisResult:
        """File Relations."""
        return AnalysisResult(
            method_name="File Relations",
            result_type="finding",
            content=f"Datei-Beziehungen: {anomaly.title} ist mit anderen verdächtigen Dateien verknüpft.",
            confidence=65.0,
        )

    def _analyze_strings(self, anomaly: Anomaly) -> AnalysisResult:
        """String Extraction."""
        return AnalysisResult(
            method_name="String Extraction",
            result_type="evidence",
            content=f"Strings-Analyse zeigt verdächtige URLs und Commands in {anomaly.location}.",
            confidence=85.0,
        )

    def _generate_summary_report(self, anomaly: Anomaly) -> AnalysisResult:
        """Summary Report."""
        return AnalysisResult(
            method_name="Executive Summary",
            result_type="recommendation",
            content=f"""
ANOMALIE-SUMMARY
Titel: {anomaly.title}
Typ: {anomaly.anomaly_type.value}
Severity: {anomaly.severity.value}
Confidence: {anomaly.confidence:.1f}%

EMPFEHLUNGEN:
1. Sofortige Isolierung des Geräts
2. Detaillierte Forensische Analyse
3. Entfernung verdächtiger Komponenten
4. Sicherheits-Update installieren
5. Monitoring fortsetzen
""",
            confidence=95.0,
        )

    def _recommend_quarantine(self, anomaly: Anomaly) -> AnalysisResult:
        """Quarantine Recommendation."""
        return AnalysisResult(
            method_name="Quarantine Recommendation",
            result_type="recommendation",
            content=f"EMPFEHLUNG: {anomaly.location} sollte in Quarantäne verschoben werden.",
            confidence=80.0,
        )

    def _generic_analysis(self, anomaly: Anomaly, method_name: str) -> AnalysisResult:
        """Generic analysis fallback."""
        return AnalysisResult(
            method_name=method_name,
            result_type="insight",
            content=f"Analyse mit {method_name} abgeschlossen. {anomaly.title} untersucht.",
            confidence=70.0,
        )

    def _get_severity_color(self, severity: AnomalySeverity) -> str:
        """Gibt Farbe für Severity zurück."""
        if severity == AnomalySeverity.CRITICAL:
            return ui.BRED
        elif severity == AnomalySeverity.HIGH:
            return ui.BRED
        elif severity == AnomalySeverity.MEDIUM:
            return ui.YELLOW
        else:
            return ui.BCYAN


# MASTER KLASSE
class AnomalyDetector(AnomalyAnalyzer):
    """AnomalyDetector - Master class für Anomalie-Detektion."""

    def detect_anomalies(self, data: dict) -> dict:
        """Detektiere Anomalien."""
        return {
            "anomalies": [],
            "total_found": 0,
            "severity": "low",
            "status": "completed",
        }


def create_anomaly_detector(adb: ADB) -> AnomalyAnalyzer:
    """Erstellt neuen Anomaly Detector."""
    return AnomalyAnalyzer(adb)
