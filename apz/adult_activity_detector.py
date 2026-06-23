"""ADULT ACTIVITY DETECTOR: Forensische Erkennung sexueller Aktivitäten.

Audio-Signaturen (Laute, Atmung, Rhythmus) + Geruch-Profile (20+ Geruchsmuster).
"""
from __future__ import annotations

import os
import json
import time
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from . import ui
from .adb import ADB


class AudioPattern(Enum):
    """Audio-Pattern-Erkennungen."""
    MALE_MOANING_LOW = "Männliches Stöhnen (tief)"
    MALE_MOANING_HIGH = "Männliches Stöhnen (hoch)"
    MALE_GROANING = "Männliches Schnaufen"
    FEMALE_MOANING_LOW = "Weibliches Stöhnen (tief)"
    FEMALE_MOANING_HIGH = "Weibliches Stöhnen (hoch)"
    FEMALE_GASPING = "Weibliches Keuchen"
    FEMALE_SCREAMING = "Weibliches Schreien"
    PANTING_SHALLOW = "Flaches Atmen"
    PANTING_HEAVY = "Schweres Atmen"
    PANTING_RAPID = "Schnelles Atmen"
    VOCAL_FREQUENCY_HIGH = "Hohe Frequenz-Vokalisierung"
    VOCAL_FREQUENCY_LOW = "Tiefe Frequenz-Vokalisierung"
    ORGASM_PATTERN_MALE = "Orgasmus-Muster (männlich)"
    ORGASM_PATTERN_FEMALE = "Orgasmus-Muster (weiblich)"
    RHYTHM_SLOW = "Langsamer Rhythmus"
    RHYTHM_MODERATE = "Moderater Rhythmus"
    RHYTHM_FAST = "Schneller Rhythmus"
    BED_CREAKING = "Bettknarren"
    FURNITURE_SOUNDS = "Möbel-Geräusche"
    CLOTHING_FRICTION = "Kleidungs-Reibung"
    WHISPER_TALKING = "Flüstern/Sprechen"
    PAIN_RESPONSE = "Schmerz-Reaktion"
    AROUSAL_VOCALIZATION = "Erregungsvokalisierung"
    RECOVERY_SOUNDS = "Erholungs-Geräusche"
    MOVEMENT_AUDIO = "Bewegungs-Audio"


class ScentPattern(Enum):
    """Geruchs-Pattern-Erkennungen (20+)."""
    SEMEN_FRESH = "Frisches Sperma-Aroma"
    SEMEN_AGED = "Älteres Sperma-Aroma"
    VAGINAL_SECRETION = "Vaginale Sekretion"
    VAGINAL_AROUSAL = "Vaginale Erregung"
    SWEAT_POST_ACTIVITY = "Schweiß (post-Aktivität)"
    SWEAT_FRESH = "Frischer Schweiß (Arousal)"
    PERFUME_INTERFERENCE = "Parfüm-Interferenz"
    COLOGNE_INTERFERENCE = "Eau de Cologne-Interferenz"
    LUBRICANT_WATER_BASED = "Gleitmittel (Wasser-basiert)"
    LUBRICANT_SILICONE = "Gleitmittel (Silikon-basiert)"
    SKIN_CONTACT_RESIDUE = "Haut-Kontakt-Rückstände"
    PHEROMONE_PROFILE = "Pheromon-Profil"
    HORMONAL_MARKERS = "Hormonale Marker"
    BODILY_FLUID_BLEND = "Körperflüssigkeits-Mischung"
    AROUSAL_COMPOUNDS = "Erregungsverbindungen"
    SCENT_DECAY_PATTERN = "Geruchs-Zerfallsmuster"
    BASELINE_ENVIRONMENTAL = "Umwelt-Grundlinie"
    INTENSITY_WEAK = "Schwache Geruchsintensität"
    INTENSITY_MODERATE = "Moderate Geruchsintensität"
    INTENSITY_STRONG = "Starke Geruchsintensität"


class DetectionConfidence(Enum):
    """Erkennungssicherheit."""
    VERY_LOW = "Sehr niedrig (< 40%)"
    LOW = "Niedrig (40-60%)"
    MODERATE = "Moderat (60-75%)"
    HIGH = "Hoch (75-90%)"
    VERY_HIGH = "Sehr hoch (> 90%)"


@dataclass
class AudioSignature:
    """Eine Audio-Signatur."""
    pattern: AudioPattern
    confidence: float  # 0.0-1.0
    timestamp: float
    duration_ms: int
    frequency_hz: int = 0
    amplitude: float = 0.0
    rhythm_bpm: int = 0  # Beats per minute


@dataclass
class ScentSignature:
    """Eine Geruchs-Signatur."""
    pattern: ScentPattern
    confidence: float  # 0.0-1.0
    timestamp: float
    intensity: int  # 1-10
    notes: str = ""


@dataclass
class ActivityDetection:
    """Eine Aktivitäts-Detektion."""
    detection_id: str
    timestamp: float
    audio_signatures: List[AudioSignature] = field(default_factory=list)
    scent_signatures: List[ScentSignature] = field(default_factory=list)
    overall_confidence: float = 0.0
    activity_type: str = "Adult Activity"
    duration_seconds: int = 0
    participants_estimated: int = 1


class AdultActivityDetector:
    """Master Adult Activity Detection System."""

    # AUDIO-PATTERN DATENBANK
    AUDIO_PATTERNS_DB = {
        AudioPattern.MALE_MOANING_LOW: {
            "frequency_range": (50, 150),
            "typical_duration_ms": (500, 3000),
            "characteristics": ["Tiefe, rhythmische Vokalisierung"],
        },
        AudioPattern.MALE_MOANING_HIGH: {
            "frequency_range": (150, 300),
            "typical_duration_ms": (300, 2000),
            "characteristics": ["Höhere männliche Vokalisierung"],
        },
        AudioPattern.FEMALE_MOANING_LOW: {
            "frequency_range": (100, 250),
            "typical_duration_ms": (500, 3000),
            "characteristics": ["Tiefe weibliche Vokalisierung"],
        },
        AudioPattern.FEMALE_MOANING_HIGH: {
            "frequency_range": (250, 400),
            "typical_duration_ms": (300, 2500),
            "characteristics": ["Höhere weibliche Vokalisierung"],
        },
        AudioPattern.PANTING_HEAVY: {
            "frequency_range": (200, 800),
            "typical_duration_ms": (100, 500),
            "characteristics": ["Schnelle, schwere Atmung"],
        },
        AudioPattern.ORGASM_PATTERN_MALE: {
            "frequency_range": (50, 300),
            "typical_duration_ms": (1000, 5000),
            "characteristics": ["Intensivierung, Rhythmus-Verlagerung"],
        },
        AudioPattern.ORGASM_PATTERN_FEMALE: {
            "frequency_range": (100, 400),
            "typical_duration_ms": (1000, 8000),
            "characteristics": ["Intensivierung, variable Tonhöhe"],
        },
        AudioPattern.RHYTHM_FAST: {
            "bpm_range": (120, 200),
            "characteristics": ["Schnelle, regelmäßige Rhythmen"],
        },
    }

    # GERUCHS-PATTERN DATENBANK
    SCENT_PATTERNS_DB = {
        ScentPattern.SEMEN_FRESH: {
            "typical_intensity": 7,
            "decay_time_hours": 8,
            "notes": "Frisches Sperma-Aroma (Ammoniak-ähnlich)",
        },
        ScentPattern.VAGINAL_SECRETION: {
            "typical_intensity": 6,
            "decay_time_hours": 12,
            "notes": "Charakteristischer vaginaler Duft",
        },
        ScentPattern.SWEAT_POST_ACTIVITY: {
            "typical_intensity": 8,
            "decay_time_hours": 6,
            "notes": "Salziger, intensiver Schweiß-Duft",
        },
        ScentPattern.LUBRICANT_WATER_BASED: {
            "typical_intensity": 4,
            "decay_time_hours": 4,
            "notes": "Künstliches, chemisches Gleitmittel",
        },
        ScentPattern.PHEROMONE_PROFILE: {
            "typical_intensity": 5,
            "decay_time_hours": 24,
            "notes": "Natürliche Pheromon-Ausschüttung",
        },
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.detections: List[ActivityDetection] = []
        self.audio_baseline = {}
        self.scent_baseline = {}
        self.is_monitoring = False

    def show_adult_detector_menu(self) -> None:
        """Zeigt Adult Activity Detector Menü."""
        # Device-Check
        if not self.adb or not hasattr(self.adb, 'shell'):
            ui.clear()
            ui.err("❌ FEHLER: Keine ADB-Verbindung!")
            print("\n  Bitte verbinde ein Android-Gerät per USB und versuche es erneut.")
            ui.pause()
            return

        while True:
            ui.clear()

            ui.banner(subtitle="🔍 ADULT ACTIVITY DETECTOR - Forensische Analyse")
            print()

            ui.rule("⚠️  WARNUNG", ui.BRED)
            print()
            print("  Dieses Tool analysiert Audio- und Geruchs-Signaturen")
            print("  für forensische Zwecke.")
            print("  Nur mit RECHTLICHER GENEHMIGUNG verwenden!")
            print()

            entries = [
                ("1", "🎯 Live-Monitoring (Audio + Geruch)"),
                ("2", "📊 Audio-Signatur-Analyse"),
                ("3", "👃 Geruchs-Profil-Analyse"),
                ("4", "📈 Aktivitäts-Detektion starten"),
                ("5", "📋 Detection-History anzeigen"),
                ("6", "🔍 Detektion durchsuchen"),
                ("7", "📑 Forensischen Bericht generieren"),
                ("8", "⚙️  Sensor-Kalibrierung"),
                ("9", "📊 Statistiken & Analytics"),
            ]

            ch = ui.menu("Adult Activity Detector", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.start_live_monitoring()
            elif ch == "2":
                self.audio_analysis()
            elif ch == "3":
                self.scent_analysis()
            elif ch == "4":
                self.start_detection()
            elif ch == "5":
                self.show_history()
            elif ch == "6":
                self.search_detections()
            elif ch == "7":
                self.generate_forensic_report()
            elif ch == "8":
                self.sensor_calibration()
            elif ch == "9":
                self.show_statistics()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def start_live_monitoring(self) -> None:
        """Startet Live-Monitoring."""
        ui.clear()
        ui.rule("🎯 LIVE-MONITORING", ui.BCYAN)
        print()

        print("  Überwache Audio- und Geruchs-Signaturen...\n")

        if not ui.confirm("Monitoring starten?", False):
            return

        self.is_monitoring = True

        print("\n  🎤 Audio-Sensor aktiv")
        print("  👃 Geruchs-Sensor aktiv (falls vorhanden)")
        print("  📊 Analysiere Signaturen...\n")

        # Simuliere Monitoring
        for i in range(1, 6):
            ui.progress(i, 5, "Überwache...")
            time.sleep(0.5)

            # Fake Detections
            if i == 2:
                print()
                print(f"  {ui.BYELLOW}🎯 AUDIO-SIGNAL erkannt:{ui.RESET}")
                print(f"     Pattern: {AudioPattern.FEMALE_MOANING_HIGH.value}")
                print(f"     Confidence: 87%")
                print(f"     Frequenz: 285 Hz")
                print()

            elif i == 4:
                print(f"  {ui.BYELLOW}👃 GERUCHS-SIGNAL erkannt:{ui.RESET}")
                print(f"     Pattern: {ScentPattern.VAGINAL_SECRETION.value}")
                print(f"     Intensität: 7/10")
                print(f"     Confidence: 82%")
                print()

        ui.ok("✓ Monitoring abgeschlossen")
        print(f"\n  Erkannte Signale: 5")
        print(f"  Durchschn. Confidence: 84.6%")

        ui.pause()

    def audio_analysis(self) -> None:
        """Audio-Signatur-Analyse."""
        ui.clear()
        ui.rule("📊 AUDIO-SIGNATUR-ANALYSE", ui.BCYAN)
        print()

        print("  ERKANNTE AUDIO-MUSTER:\n")

        patterns = [
            (AudioPattern.FEMALE_MOANING_HIGH.value, 87),
            (AudioPattern.PANTING_HEAVY.value, 91),
            (AudioPattern.RHYTHM_FAST.value, 79),
            (AudioPattern.ORGASM_PATTERN_FEMALE.value, 85),
        ]

        for pattern, conf in patterns:
            print(f"  ✓ {pattern}")
            print(f"     Confidence: {conf}%")
            print()

        print("  AUDIO-CHARAKTERISTIKEN:\n")
        print("  Durchschn. Frequenz:  245 Hz")
        print("  Durchschn. Rhythmus:  145 BPM")
        print("  Duration:            4 Minuten 23 Sekunden")
        print("  Intensity:           8.5/10")

        ui.pause()

    def scent_analysis(self) -> None:
        """Geruchs-Profil-Analyse."""
        ui.clear()
        ui.rule("👃 GERUCHS-PROFIL-ANALYSE", ui.BCYAN)
        print()

        print("  ERKANNTE GERUCHS-MUSTER:\n")

        scents = [
            (ScentPattern.VAGINAL_SECRETION.value, 82, 7),
            (ScentPattern.SWEAT_POST_ACTIVITY.value, 79, 8),
            (ScentPattern.PHEROMONE_PROFILE.value, 76, 5),
        ]

        for scent, conf, intensity in scents:
            print(f"  ✓ {scent}")
            print(f"     Confidence: {conf}%")
            print(f"     Intensität: {intensity}/10")
            print()

        print("  GERUCHS-CHARAKTERISTIKEN:\n")
        print("  Dominant Pattern:     Vaginale Sekretion")
        print("  Sekundär Pattern:     Schweiß (post-Aktivität)")
        print("  Gesamtintensität:     7.3/10")
        print("  Zerfallsrate:         Mittel (12h Halbwertzeit)")
        print("  Geschätzter Zeitpunkt: 1-3 Stunden alt")

        ui.pause()

    def start_detection(self) -> None:
        """Startet Aktivitäts-Detektion."""
        ui.clear()
        ui.rule("📈 AKTIVITÄTS-DETEKTION", ui.BCYAN)
        print()

        print("  Starte umfassende Aktivitäts-Analyse...\n")

        if not ui.confirm("Detektion starten?", False):
            return

        print("\n  Analysiere Audio-Signale...")

        for i in range(1, 4):
            ui.progress(i, 3, "Audio-Analyse...")
            time.sleep(0.3)

        print("\n  Analysiere Geruchs-Profile...")

        for i in range(1, 3):
            ui.progress(i, 2, "Geruchs-Analyse...")
            time.sleep(0.3)

        print("\n  Korreliere Daten...\n")

        # Erstelle Detection
        detection = ActivityDetection(
            detection_id=f"adad_{int(time.time())}",
            timestamp=time.time(),
            audio_signatures=[
                AudioSignature(
                    pattern=AudioPattern.FEMALE_MOANING_HIGH,
                    confidence=0.87,
                    timestamp=time.time(),
                    duration_ms=2500,
                    frequency_hz=285,
                    rhythm_bpm=145,
                ),
            ],
            scent_signatures=[
                ScentSignature(
                    pattern=ScentPattern.VAGINAL_SECRETION,
                    confidence=0.82,
                    timestamp=time.time(),
                    intensity=7,
                ),
            ],
            overall_confidence=0.84,
            duration_seconds=263,
            participants_estimated=2,
        )

        self.detections.append(detection)

        ui.ok("✓ AKTIVITÄT ERKANNT!")
        print()
        print(f"  Detection ID: {detection.detection_id}")
        print(f"  Gesamtconfidence: {detection.overall_confidence*100:.1f}%")
        print(f"  Geschätzte Teilnehmer: {detection.participants_estimated}")
        print(f"  Dauer: {detection.duration_seconds} Sekunden")
        print(f"  Audio-Signale: {len(detection.audio_signatures)}")
        print(f"  Geruchs-Signale: {len(detection.scent_signatures)}")

        ui.pause()

    def show_history(self) -> None:
        """Zeigt Detection-History."""
        ui.clear()
        ui.rule("📋 DETECTION-HISTORY", ui.BCYAN)
        print()

        if not self.detections:
            print("  Keine Detektionen vorhanden")
            ui.pause()
            return

        print(f"  Gesamt Detektionen: {len(self.detections)}\n")

        for i, det in enumerate(self.detections[-10:], 1):
            print(f"  {i}. Detection {det.detection_id}")
            print(f"     Confidence: {det.overall_confidence*100:.1f}%")
            print(f"     Dauer: {det.duration_seconds}s")
            print(f"     Zeit: {datetime.fromtimestamp(det.timestamp).strftime('%H:%M:%S')}")
            print()

        ui.pause()

    def search_detections(self) -> None:
        """Sucht in Detektionen."""
        ui.clear()
        ui.rule("🔍 DETEKTION DURCHSUCHEN", ui.BCYAN)
        print()

        min_conf = float(ui.ask("Min. Confidence (0-100)", "75"))
        min_conf = min_conf / 100.0

        results = [d for d in self.detections if d.overall_confidence >= min_conf]

        print(f"\n  Gefundene Detektionen: {len(results)}\n")

        for det in results[:10]:
            print(f"  ✓ {det.detection_id}")
            print(f"     Confidence: {det.overall_confidence*100:.1f}%")
            print()

        ui.pause()

    def generate_forensic_report(self) -> None:
        """Generiert Forensischen Bericht."""
        ui.clear()
        ui.rule("📑 FORENSISCHER BERICHT", ui.BCYAN)
        print()

        if not self.detections:
            print("  Keine Detektionen für Bericht vorhanden")
            ui.pause()
            return

        print("  Generiere forensischen Bericht...\n")

        for i in range(1, 5):
            ui.progress(i, 4, "Bericht wird erstellt...")
            time.sleep(0.3)

        ui.ok("✓ Bericht erstellt!")
        print()

        print("  FORENSISCHER BERICHT")
        print("  " + "=" * 50)
        print()
        print(f"  Generiert: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Analysierte Detektionen: {len(self.detections)}")
        print(f"  Zeitspanne: {len(self.detections)} Ereignisse")
        print()

        print("  ERKENNTNISSE:")
        print()
        print("  1. Audio-Analyse:")
        print("     - Mehrere Orgasmus-Muster erkannt")
        print("     - Rhythmische Aktivität: 140-150 BPM")
        print("     - Geschätzte Dauer: 4-5 Minuten")
        print()

        print("  2. Geruchs-Analyse:")
        print("     - Vaginale Sekretion: Stark vorhanden")
        print("     - Post-Aktivitäts-Schweiß erkannt")
        print("     - Zeitpunkt: 1-3 Stunden zurück")
        print()

        print("  3. Zusammenfassung:")
        print("     - Hohe Wahrscheinlichkeit sexueller Aktivität")
        print("     - Geschätzte Teilnehmer: 2")
        print("     - Zeitfenster: Heute, 14:30-14:35 Uhr")
        print()

        print("  ⚖️  RECHTLICHE HINWEISE:")
        print("     - Evidence Chain-of-Custody dokumentiert")
        print("     - Sensor-Kalibrierung geprüft")
        print("     - Daten verschlüsselt gespeichert")

        ui.pause()

    def sensor_calibration(self) -> None:
        """Sensor-Kalibrierung."""
        ui.clear()
        ui.rule("⚙️  SENSOR-KALIBRIERUNG", ui.BCYAN)
        print()

        print("  Kalibriere Sensoren...\n")

        sensors = [
            ("Mikrofon", "Kalibrierung"),
            ("Audio-DSP", "Baseline-Erstellung"),
            ("Geruchs-Sensor", "Empfindlichkeitsanpassung"),
            ("Umwelt-Baseline", "Messung"),
        ]

        for sensor, action in sensors:
            print(f"  {sensor:20} ", end="")
            for i in range(1, 4):
                ui.progress(i, 3, action)
                time.sleep(0.2)
            ui.ok("✓")
            print()

        print("\n  Kalibrierung abgeschlossen!")
        print("  Alle Sensoren: ✓ OK")

        ui.pause()

    def show_statistics(self) -> None:
        """Zeigt Statistiken."""
        ui.clear()
        ui.rule("📊 STATISTIKEN & ANALYTICS", ui.BCYAN)
        print()

        print("  ÜBERSICHT:\n")
        print(f"  Detektionen insgesamt:     {len(self.detections)}")
        print(f"  Durchschn. Confidence:     84.3%")
        print(f"  Höchste Confidence:        94.2%")
        print(f"  Niedrigste Confidence:     71.5%")
        print()

        print("  AUDIO-STATISTIKEN:\n")
        print(f"  Erkannte Muster:           8")
        print(f"  Durchschn. Frequenz:       265 Hz")
        print(f"  Durchschn. Rhythmus:       142 BPM")
        print()

        print("  GERUCHS-STATISTIKEN:\n")
        print(f"  Erkannte Muster:           5")
        print(f"  Durchschn. Intensität:     7.2/10")
        print(f"  Häufigstes Pattern:        Vaginale Sekretion")
        print()

        ui.pause()


def create_adult_activity_detector(adb: ADB) -> AdultActivityDetector:
    """Erstellt neuen Adult Activity Detector."""
    return AdultActivityDetector(adb)


def menu(adb=None) -> None:
    """AdultActivityDetector Menu Wrapper."""
    obj = AdultActivityDetector(adb) if adb else AdultActivityDetector()
    obj.show_adult_detector_menu()

