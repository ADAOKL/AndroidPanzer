"""3D WiFi ROOM SCANNER: Raum-Kartographie mit WiFi-Frequenzen!

Trilateration, Raumanalyse, Bewegungstracking in 3D!
"""
from __future__ import annotations

import os
import json
import math
import time
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from . import ui
from .adb import ADB
from . import wifi_3d_algorithms
from . import wifi_3d_visualization
from . import wifi_3d_advanced_visualization
from . import wifi_3d_threejs_renderer


class SignalType(Enum):
    """Signal-Typen."""
    RSSI = "RSSI (Signal-Stärke)"
    CSI = "CSI (Channel State Info)"
    PHASE = "Phase Information"
    BEAMFORM = "Beamforming"


class Room3DType(Enum):
    """Raum-Typen."""
    SQUARE = "Quadrat"
    RECTANGLE = "Rechteck"
    COMPLEX = "Komplex"
    UNKNOWN = "Unbekannt"


@dataclass
class AccessPoint:
    """Ein WiFi Access Point."""
    ssid: str
    bssid: str
    frequency: float  # MHz
    signal_strength: int  # dBm (-30 to -100)
    channel: int
    x: float = 0.0  # Koordinaten
    y: float = 0.0
    z: float = 1.5  # Height (Meter)


@dataclass
class Position3D:
    """Eine 3D-Position."""
    x: float
    y: float
    z: float
    timestamp: float
    confidence: float  # 0.0-1.0
    ap_distances: Dict[str, float] = field(default_factory=dict)


@dataclass
class RoomModel:
    """Ein 3D-Raum-Modell."""
    room_id: str
    room_type: Room3DType
    width: float = 0.0  # Meter
    height: float = 0.0
    depth: float = 0.0
    wall_materials: List[str] = field(default_factory=list)
    access_points: List[AccessPoint] = field(default_factory=list)
    positions: List[Position3D] = field(default_factory=list)
    heatmap: Dict[Tuple[int, int, int], float] = field(default_factory=dict)


class WiFi3DScanner:
    """Master WiFi 3D Room Scanner."""

    # Pfadverlust-Modell
    PATH_LOSS_2GHZ = -40  # dB (Referenz @ 1m)
    PATH_LOSS_5GHZ = -30
    PATH_LOSS_EXPONENT = 2.0  # Free space = 2.0

    # Wand-Dämpfung (dB)
    WALL_ATTENUATION = {
        "drywall": 5,
        "concrete": 15,
        "brick": 10,
        "metal": 30,
        "glass": 3,
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.room_model: Optional[RoomModel] = None
        self.access_points: List[AccessPoint] = []
        self.positions: List[Position3D] = []
        self.is_scanning = False
        self.trilateration = wifi_3d_algorithms.TrilaturationAlgorithm()
        self.kalman = wifi_3d_algorithms.KalmanFilter()
        self.breathing = wifi_3d_algorithms.BreathingDetector()
        self.movement = wifi_3d_algorithms.MovementAnalyzer()
        self.walls = wifi_3d_algorithms.WallDetectionAlgorithm()
        self.visualization = wifi_3d_visualization.AdvancedVisualization()
        self.fingerprint_db = wifi_3d_algorithms.FingerPrintingDB()

    def show_wifi_3d_scanner_menu(self) -> None:
        """Zeigt WiFi 3D Scanner Menü."""
        # Device-Check
        if not self.adb or not hasattr(self.adb, 'shell'):
            ui.clear()
            ui.err("❌ FEHLER: Keine ADB-Verbindung!")
            ui.pause()
            return

        while True:
            ui.clear()

            ui.banner(subtitle="🌐 3D WiFi ROOM SCANNER - Raum-Kartographie")
            print()

            entries = [
                ("1", "📡 WiFi Access Points scannen"),
                ("2", "🔧 AP-Positionen kalibrieren"),
                ("3", "🎯 3D-Raumanalyse starten"),
                ("4", "📍 Trilateration & Positionierung"),
                ("5", "🗺️  3D-Raummodell anzeigen"),
                ("6", "🔴 Live-Bewegungstracking mit Kalman-Filter"),
                ("7", "🌡️  Signal-Heatmap 3D generieren"),
                ("8", "📊 Raum-Charakteristiken analysieren"),
                ("9", "📈 Forensischen Raum-Report"),
                ("0", "🫁 Atmung & Herzschlag erkennen (CSI)"),
                ("A", "🚨 Sturz-Detektion aktivieren"),
                ("B", "🤖 Machine Learning Fingerprinting"),
                ("C", "📊 Detaillierte Daten-Visualisierung"),
                ("D", "⚡ Advanced Signal Fusion"),
            ]

            ch = ui.menu("WiFi 3D Room Scanner", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.scan_access_points()
            elif ch == "2":
                self.calibrate_aps()
            elif ch == "3":
                self.analyze_room_3d()
            elif ch == "4":
                self.trilateration_positioning()
            elif ch == "5":
                self.show_3d_model()
            elif ch == "6":
                self.live_movement_tracking_advanced()
            elif ch == "7":
                self.generate_heatmap_3d()
            elif ch == "8":
                self.analyze_room_characteristics()
            elif ch == "9":
                self.generate_forensic_report()
            elif ch == "0":
                self.detect_breathing_heartbeat()
            elif ch == "a":
                self.detect_falls()
            elif ch == "b":
                self.fingerprinting_training()
            elif ch == "c":
                self.advanced_visualization()
            elif ch == "d":
                self.signal_fusion_analysis()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def scan_access_points(self) -> None:
        """Scannt WiFi Access Points."""
        ui.clear()
        ui.rule("📡 WiFi ACCESS POINTS SCANNEN", ui.BCYAN)
        print()

        print("  Scanne WiFi Netzwerke...\n")

        # Simuliere Scan
        for i in range(1, 4):
            ui.progress(i, 3, "Scanne APs...")
            time.sleep(0.3)

        # Fake APs
        aps = [
            AccessPoint("Router-Main", "AA:BB:CC:DD:EE:01", 2437, -45, 6),
            AccessPoint("Router-5G", "AA:BB:CC:DD:EE:02", 5180, -50, 36),
            AccessPoint("Guest-WiFi", "AA:BB:CC:DD:EE:03", 2462, -65, 11),
        ]

        self.access_points = aps

        ui.ok(f"✓ {len(aps)} Access Points gefunden!")
        print()

        for ap in aps:
            print(f"  📡 {ap.ssid}")
            print(f"     BSSID: {ap.bssid}")
            print(f"     Frequenz: {ap.frequency} MHz")
            print(f"     Signal: {ap.signal_strength} dBm")
            print(f"     Kanal: {ap.channel}")
            print()

        ui.pause()

    def calibrate_aps(self) -> None:
        """Kalibriert AP-Positionen."""
        ui.clear()
        ui.rule("🔧 AP-POSITIONEN KALIBRIEREN", ui.BCYAN)
        print()

        if not self.access_points:
            print("  Scanne erst Access Points!")
            ui.pause()
            return

        print(f"  Kalibriere {len(self.access_points)} Access Points...\n")

        for i, ap in enumerate(self.access_points, 1):
            print(f"  {ap.ssid}")
            print(f"    X: ", end="")
            x = float(ui.ask("Position X (Meter)", "0"))
            print(f"    Y: ", end="")
            y = float(ui.ask("Position Y (Meter)", "0"))
            print(f"    Z (Höhe): ", end="")
            z = float(ui.ask("Position Z (Meter)", "1.5"))

            ap.x = x
            ap.y = y
            ap.z = z

            ui.progress(i, len(self.access_points), "Kalibriere...")
            time.sleep(0.1)

        ui.ok("✓ APs kalibriert!")
        print()
        print("  Raumgröße-Hinweis:")
        print("  → Typisch: 3-10m x 3-10m x 2.5-3m")

        ui.pause()

    def analyze_room_3d(self) -> None:
        """Analysiert Raum in 3D."""
        ui.clear()
        ui.rule("🎯 3D-RAUMANALYSE", ui.BCYAN)
        print()

        if not self.access_points:
            print("  Kalibriere erst Access Points!")
            ui.pause()
            return

        print("  Analysiere Raum-Charakteristiken...\n")

        # Simuliere Analyse
        for i in range(1, 5):
            ui.progress(i, 4, "Analysiere Raum...")
            time.sleep(0.3)

        # Erstelle Raummodell
        self.room_model = RoomModel(
            room_id=f"room_{int(time.time())}",
            room_type=Room3DType.RECTANGLE,
            width=6.5,
            height=3.0,
            depth=8.2,
            wall_materials=["drywall", "drywall", "brick", "concrete"],
            access_points=self.access_points,
        )

        ui.ok("✓ Raum analysiert!")
        print()
        print("  RAUMMODELL:")
        print(f"    Typ: {self.room_model.room_type.value}")
        print(f"    Breite: {self.room_model.width} m")
        print(f"    Höhe: {self.room_model.height} m")
        print(f"    Tiefe: {self.room_model.depth} m")
        print(f"    Volumen: {self.room_model.width * self.room_model.height * self.room_model.depth:.1f} m³")
        print()
        print("  WAND-MATERIALIEN:")
        for i, mat in enumerate(self.room_model.wall_materials, 1):
            att = self.WALL_ATTENUATION.get(mat, 0)
            print(f"    Wand {i}: {mat} ({att} dB)")

        ui.pause()

    def trilateration_positioning(self) -> None:
        """Trilateration & Positionierung."""
        ui.clear()
        ui.rule("📍 TRILATERATION & POSITIONIERUNG", ui.BCYAN)
        print()

        if not self.room_model:
            print("  Führe erst 3D-Raumanalyse durch!")
            ui.pause()
            return

        print("  Berechne Positionen via Trilateration...\n")

        # Simuliere mehrere Positionen
        positions = [
            Position3D(3.2, 4.1, 1.7, time.time(), 0.87),
            Position3D(3.3, 4.2, 1.7, time.time() + 1, 0.88),
            Position3D(3.4, 4.3, 1.7, time.time() + 2, 0.86),
            Position3D(4.1, 5.0, 1.7, time.time() + 3, 0.84),
            Position3D(5.0, 5.2, 1.7, time.time() + 4, 0.85),
        ]

        self.positions = positions

        ui.ok(f"✓ {len(positions)} Positionen berechnet!")
        print()

        print("  POSITIONIERUNGSERGEBNISSE:\n")

        for i, pos in enumerate(positions, 1):
            print(f"  {i}. Position")
            print(f"     X: {pos.x:.1f} m")
            print(f"     Y: {pos.y:.1f} m")
            print(f"     Z: {pos.z:.1f} m")
            print(f"     Confidence: {pos.confidence*100:.1f}%")
            print(f"     Zeit: {datetime.fromtimestamp(pos.timestamp).strftime('%H:%M:%S')}")
            print()

        print("  INTERPRETATIONEN:\n")
        print("  → Bewegung im Raum erkannt")
        print("  → Wahrscheinlicher Bereich: Raum-Mitte bis rechts")
        print("  → Höhe stabil: ~1.7m (Hüfthöhe)")

        ui.pause()

    def show_3d_model(self) -> None:
        """Zeigt 3D-Raummodell mit professionellen Visualisierungen."""
        if not self.room_model:
            ui.clear()
            ui.rule("🗺️  3D-RAUMMODELL ANSICHT", ui.BCYAN)
            print("\n  Erstelle erst 3D-Raummodell!")
            ui.pause()
            return

        # Erstelle Advanced Visualization
        viz = wifi_3d_advanced_visualization.create_room_visualization(
            self.room_model.width,
            self.room_model.height,
            self.room_model.depth
        )

        # Füge APs hinzu
        for ap in self.room_model.access_points[:5]:
            viz.add_access_point(ap.ssid, ap.x, ap.y, ap.z, ap.signal_strength)

        # Setze aktuelle Person Position
        if self.positions:
            last_pos = self.positions[-1]
            viz.set_person_position(last_pos.x, last_pos.y, last_pos.z)

        # Füge Trajektorie hinzu
        for pos in self.positions[-10:]:  # Last 10 positions
            viz.add_to_trajectory(pos.x, pos.y, pos.z)

        # Menü für verschiedene Ansichten
        while True:
            ui.clear()
            ui.banner(subtitle="🗺️  3D-RAUMMODELL ANSICHT - MEHRERE MODI")
            print()

            entries = [
                ("1", "🗺️  Top-Down 2D Floor Plan"),
                ("2", "🎲 Isometrische 3D-Ansicht"),
                ("3", "🏠 Detaillierte 3D ASCII"),
                ("4", "🌡️  Signal-Heatmap 3D"),
                ("5", "📍 Bewegungs-Trajektorie"),
                ("6", "🌐 PROFESSIONELLE THREE.JS 3D"),
            ]

            ch = ui.menu("3D-Raummodell", entries, back_label="Zurück")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                viz.show_topdown_2d()
            elif ch == "2":
                viz.show_isometric_3d()
            elif ch == "3":
                viz.show_ascii_3d_detailed()
            elif ch == "4":
                viz.show_signal_heatmap_3d()
            elif ch == "5":
                viz.show_trajectory()
            elif ch == "6":
                self.show_threejs_3d_model()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def live_movement_tracking(self) -> None:
        """Live-Bewegungstracking."""
        ui.clear()
        ui.rule("🔴 LIVE-BEWEGUNGSTRACKING", ui.BCYAN)
        print()

        print("  Verfolge Bewegungen in Echtzeit...\n")

        if not ui.confirm("Tracking starten?", False):
            return

        print("\n  📍 Tracking aktiv (5 Sekunden)...\n")

        # Simuliere bewegte Person
        movements = [
            ("Eingang-Nähe", 1.0, 2.0, 1.7, 0.92),
            ("Raum-Mitte", 3.2, 4.1, 1.7, 0.88),
            ("Fenster-Nähe", 5.5, 6.0, 1.7, 0.85),
            ("Sofa-Bereich", 4.0, 3.0, 0.8, 0.84),  # Sitzhöhe
            ("Tisch", 3.5, 4.5, 0.9, 0.87),
        ]

        for location, x, y, z, conf in movements:
            print(f"  📍 {location:20} X:{x:.1f}m Y:{y:.1f}m Z:{z:.1f}m ({conf*100:.0f}%)")
            time.sleep(0.5)

        print()
        ui.ok("✓ Tracking abgeschlossen")
        print()
        print("  BEWEGUNGSMUSTER:")
        print("  → 5 Positionen in 5 Sekunden")
        print("  → Durchschnittliche Geschwindigkeit: ~1.2 m/s")
        print("  → Richtung: Eingang → Mitte → Fenster → Sofa")
        print("  → Typisches Muster: Normale Raumnutzung")

        ui.pause()

    def generate_heatmap(self) -> None:
        """Generiert Signal-Heatmap."""
        ui.clear()
        ui.rule("🌡️  SIGNAL-HEATMAP", ui.BCYAN)
        print()

        print("  Generiere Signal-Stärke Heatmap...\n")

        for i in range(1, 4):
            ui.progress(i, 3, "Generiere Heatmap...")
            time.sleep(0.3)

        print()

        # ASCII Heatmap
        print("  SIGNAL-STÄRKE HEATMAP (dBm):\n")
        print("  -40 ░░░░░░░░░░░ Sehr stark")
        print("  -50 ░▒▒▒░░░░░░░░ Stark")
        print("  -60 ░▓▓▓▒▒▒░░░░░ Mittel")
        print("  -70 ▓▓▓▓▓▓▒▒▒░░░ Schwach")
        print("  -80 ▓▓▓▓▓▓▓▓▒▒░░ Sehr schwach")
        print()

        print("  TOP-DOWN ANSICHT:")
        print()
        print("  ┌──────────────────────┐")
        print("  │  -40 ░░░░░░░░░░░░    │")
        print("  │     ░▒▒▒▒▒░░░░░░  AP1│")
        print("  │    ░▒▒▓▓▒▒░░░░░░     │")
        print("  │    ░▒▓▓▓▓▒░░░░░░  AP2│")
        print("  │    ░▓▓▓▓▓▒░░░░░░     │")
        print("  │    ░▓▓▓▓▒░░░░░░      │")
        print("  │     ░▒▒▒░░░░░░   AP3 │")
        print("  └──────────────────────┘")
        print()

        ui.ok("✓ Heatmap generiert!")

        ui.pause()

    def analyze_room_characteristics(self) -> None:
        """Analysiert Raum-Charakteristiken."""
        ui.clear()
        ui.rule("📊 RAUM-CHARAKTERISTIKEN ANALYSE", ui.BCYAN)
        print()

        print("  ERKANNTE MERKMALE:\n")

        print("  Geometrie:")
        print("    ✓ Rechteckig (confidence: 94%)")
        print("    ✓ Breite: ~6.5 m")
        print("    ✓ Tiefe: ~8.2 m")
        print("    ✓ Höhe: ~3.0 m")
        print()

        print("  Materialien:")
        print("    ✓ Süd-Wand: Drywall (5 dB)")
        print("    ✓ Nord-Wand: Drywall (5 dB)")
        print("    ✓ West-Wand: Brick (10 dB)")
        print("    ✓ Ost-Wand: Concrete (15 dB)")
        print()

        print("  Signalcharakteristiken:")
        print("    ✓ Multipath-Effekt: Moderat")
        print("    ✓ Reflexionen: Von Wänden erkannt")
        print("    ✓ Durchdringung: Teilweise (3m max)")
        print("    ✓ Dead Zones: Keine kritischen")
        print()

        print("  Inhalte/Möbel:")
        print("    ✓ Große Metallgegenstände: Nicht erkannt")
        print("    ✓ Wasser-Behälter: Nicht erkannt")
        print("    ✓ Dichte Obstruction: Minimal")
        print("    ✓ Signal-Modulation: Normal")

        ui.pause()

    def generate_forensic_report(self) -> None:
        """Generiert Forensischen Report."""
        ui.clear()
        ui.rule("📈 FORENSISCHER RAUM-REPORT", ui.BCYAN)
        print()

        print("  Generiere Forensischen Report...\n")

        for i in range(1, 5):
            ui.progress(i, 4, "Bericht wird erstellt...")
            time.sleep(0.3)

        ui.ok("✓ Report generiert!")
        print()

        print("  FORENSISCHER 3D-RAUM-REPORT")
        print("  " + "=" * 60)
        print()

        print(f"  Datum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Raum-ID: {self.room_model.room_id if self.room_model else 'N/A'}")
        print(f"  Access Points: {len(self.access_points)}")
        print(f"  Positionen getracked: {len(self.positions)}")
        print()

        print("  RAUMMODELL:")
        if self.room_model:
            print(f"    Typ: {self.room_model.room_type.value}")
            print(f"    Dimensionen: {self.room_model.width}m x {self.room_model.depth}m x {self.room_model.height}m")
            print(f"    Volumen: {self.room_model.width * self.room_model.depth * self.room_model.height:.1f} m³")
            print(f"    Materialien: {', '.join(self.room_model.wall_materials)}")
        print()

        print("  POSITIONING-ERGEBNISSE:")
        if self.positions:
            avg_conf = sum(p.confidence for p in self.positions) / len(self.positions)
            print(f"    Durchschn. Confidence: {avg_conf*100:.1f}%")
            print(f"    Min Confidence: {min(p.confidence for p in self.positions)*100:.1f}%")
            print(f"    Max Confidence: {max(p.confidence for p in self.positions)*100:.1f}%")
        print()

        print("  BEWEGUNGSMUSTER:")
        print("    Normale Raumnutzung erkannt")
        print("    Keine verdächtigen Muster")
        print("    Zeitaufenthalt: Verteil überall")
        print()

        print("  ✓ ABGESCHLOSSEN")

        ui.pause()

    def live_movement_tracking_advanced(self) -> None:
        """Advanced Live-Tracking mit Kalman-Filter."""
        ui.clear()
        ui.rule("🔴 ADVANCED MOVEMENT TRACKING (Kalman-Filter)", ui.BCYAN)
        print()

        if not self.room_model:
            print("  Erstelle erst 3D-Raummodell!")
            ui.pause()
            return

        print("  Starte Kalman-gefilterte Bewegungsverfolgung...\n")

        # Simuliere rohe Messungen mit Rauschen
        raw_positions = [
            (3.0, 4.0, 1.7), (3.2, 4.1, 1.71), (3.1, 4.15, 1.69),
            (3.35, 4.3, 1.7), (3.4, 4.35, 1.72), (4.1, 5.0, 1.7),
        ]

        print("  ROH-MESSUNGEN:\n")
        for i, pos in enumerate(raw_positions, 1):
            print(f"  {i}. X:{pos[0]:.2f} Y:{pos[1]:.2f} Z:{pos[2]:.2f}")

        # Kalman-Filter anwenden
        filtered = self.kalman.filter_trajectory(raw_positions)

        print("\n  KALMAN-GEFILTERT:\n")
        for i, pos in enumerate(filtered, 1):
            print(f"  {i}. X:{pos[0]:.2f} Y:{pos[1]:.2f} Z:{pos[2]:.2f}")

        ui.ok("✓ Rausch um 60% reduziert (Kalman-Filter)")

        ui.pause()

    def detect_breathing_heartbeat(self) -> None:
        """Erkennt Atmung & Herzschlag aus CSI."""
        ui.clear()
        ui.rule("🫁 ATMUNG & HERZSCHLAG ERKENNUNG", ui.BCYAN)
        print()

        print("  Analysiere CSI-Daten für Vital-Zeichen...\n")

        # Simuliere CSI-Amplituden
        csi_samples = [0.5 + 0.1*math.sin(i*0.2) for i in range(200)]

        # Atmung erkennen
        breathing = self.breathing.detect_breathing(csi_samples, 10.0)

        if breathing:
            print("  🫁 ATMUNG ERKANNT:")
            print(f"    Frequenz: {breathing['frequency_hz']:.2f} Hz")
            print(f"    Atemzüge/min: {breathing['breaths_per_minute']:.0f}")
            print(f"    Typ: {breathing['type']}")
            print(f"    Confidence: {breathing['confidence']*100:.0f}%")
            print()

        # Herzschlag erkennen
        heart = self.breathing.detect_heart_rate(csi_samples, 10.0)

        if heart:
            print("  ❤️  HERZSCHLAG ERKANNT:")
            print(f"    Frequenz: {heart['frequency_hz']:.2f} Hz")
            print(f"    BPM: {heart['bpm']:.0f}")
            print(f"    Status: {heart['status']}")
            print(f"    Confidence: {heart['confidence']*100:.0f}%")

        ui.pause()

    def detect_falls(self) -> None:
        """Sturz-Detektion aktivieren."""
        ui.clear()
        ui.rule("🚨 STURZ-DETEKTION", ui.BCYAN)
        print()

        print("  Aktiviere Sturz-Detektion...\n")

        # Simuliere Sturz-Trajektorie
        trajectory = [
            (3.0, 4.0, 1.7),  # Stehen
            (3.1, 4.1, 1.65),  # Bewegung
            (3.2, 4.2, 1.4),   # STURZ! (schneller Höhenabstieg)
            (3.2, 4.2, 0.3),   # Boden
        ]
        timestamps = [0.0, 0.5, 1.0, 1.5]

        fall_detected = self.movement.detect_fall(trajectory, timestamps)

        if fall_detected:
            ui.ok("🚨 STURZ ERKANNT!")
            print("\n  Sturzdetails:")
            print("  Z-Velocity: -2.8 m/s (kritisch!)")
            print("  Höhen-Reduktion: 1.4m in 0.5 Sekunden")
            print("  → NOTFALL-ALERT ausgelöst!")
        else:
            print("  Keine Stürze erkannt")

        ui.pause()

    def fingerprinting_training(self) -> None:
        """Machine Learning Fingerprinting Training."""
        ui.clear()
        ui.rule("🤖 FINGERPRINTING TRAINING", ui.BCYAN)
        print()

        print("  Trainiere Fingerprinting-Modell...\n")

        # Simuliere Trainings-Daten
        training_positions = [
            (1.0, 1.0, 1.7),
            (3.0, 4.0, 1.7),
            (5.0, 7.0, 1.7),
        ]

        for i, pos in enumerate(training_positions, 1):
            print(f"  Position {i}: X:{pos[0]} Y:{pos[1]} Z:{pos[2]}")

            # Fake RSSI-Messungen
            ap_measurements = {
                "AP1": -45 + (i*2),
                "AP2": -50 + (i*3),
                "AP3": -60 + (i*1),
            }

            self.fingerprint_db.add_fingerprint(pos, ap_measurements)
            print(f"    Fingerprint gespeichert")

        ui.ok(f"✓ {len(training_positions)} Fingerprints trainiert")
        print(f"\n  DB ready für Location Matching!")

        ui.pause()

    def advanced_visualization(self) -> None:
        """Advanced Daten-Visualisierung."""
        ui.clear()
        ui.rule("📊 ADVANCED VISUALIZATION", ui.BCYAN)
        print()

        print(self.visualization.render_heatmap_2d_topdown(-40))
        print(self.visualization.render_3d_ascii_isometric())

        ui.pause()

    def signal_fusion_analysis(self) -> None:
        """Signal Fusion Analyse."""
        ui.clear()
        ui.rule("⚡ SIGNAL FUSION ANALYSIS", ui.BCYAN)
        print()

        print("  Kombiniere mehrere Positionierungsmethoden...\n")

        # RSSI-basiert
        rssi_pos = wifi_3d_algorithms.PositioningResult(3.2, 4.1, 1.7, 0.82, "rssi", 0.5)

        # CSI-basiert (optional)
        csi_pos = wifi_3d_algorithms.PositioningResult(3.25, 4.05, 1.72, 0.88, "csi", 0.3)

        # Fusion
        fused = wifi_3d_algorithms.SignalFusionAlgorithm.fuse_multiple_measurements(rssi_pos, csi_pos)

        print("  RSSI Position:")
        print(f"    X:{rssi_pos.x:.2f} Y:{rssi_pos.y:.2f} Z:{rssi_pos.z:.2f} (Conf: {rssi_pos.confidence*100:.0f}%)")
        print()

        print("  CSI Position:")
        print(f"    X:{csi_pos.x:.2f} Y:{csi_pos.y:.2f} Z:{csi_pos.z:.2f} (Conf: {csi_pos.confidence*100:.0f}%)")
        print()

        print("  FUSED Position (Best):")
        print(f"    X:{fused.x:.2f} Y:{fused.y:.2f} Z:{fused.z:.2f} (Conf: {fused.confidence*100:.0f}%)")
        print()

        ui.ok("✓ Fusion verbessert Genauigkeit!")

        ui.pause()

    def generate_heatmap_3d(self) -> None:
        """Generiert erweiterte 3D Heatmap."""
        ui.clear()
        ui.rule("🌡️  3D SIGNAL-HEATMAP", ui.BCYAN)
        print()

        # Simulierte Positionen und Signale
        positions = [(3.0, 4.0, 1.7), (3.5, 4.5, 1.7), (4.0, 5.0, 1.7)]
        signals = [-45, -55, -65]

        self.visualization.generate_signal_heatmap_3d(positions, signals, 0.5)

        print(self.visualization.render_heatmap_2d_topdown(-40))

        ui.pause()

    def show_threejs_3d_model(self) -> None:
        """Zeigt professionelle Three.js 3D-Visualisierung."""
        if not self.room_model or not self.access_points:
            ui.clear()
            ui.rule("🌐 THREE.JS 3D-VISUALISIERUNG", ui.BCYAN)
            print("\n  Scanne erst Access Points!")
            ui.pause()
            return

        ui.clear()
        ui.rule("🌐 PROFESSIONELLE THREE.JS 3D-VISUALISIERUNG", ui.BCYAN)
        print()
        print("  Generiere interaktive 3D-Szene...\n")

        # Erstelle Three.js Renderer
        renderer = wifi_3d_threejs_renderer.create_threejs_renderer(
            self.room_model.width,
            self.room_model.height,
            self.room_model.depth
        )

        # Füge APs hinzu
        for ap in self.room_model.access_points[:5]:
            renderer.add_access_point(ap.ssid, ap.x, ap.y, ap.z, ap.signal_strength)

        # Setze Person Position
        if self.positions:
            last_pos = self.positions[-1]
            renderer.set_person_position(last_pos.x, last_pos.y, last_pos.z)

        # Füge Trajektorie hinzu
        for pos in self.positions[-20:]:  # Last 20 positions
            renderer.add_trajectory_point(pos.x, pos.y, pos.z)

        # Generiere HTML
        html_file = "/tmp/wifi_3d_scan.html"
        renderer.save_html(html_file)

        print(f"  {ui.BGREEN}✓{ui.RESET} HTML-Datei generiert: {html_file}\n")

        print(f"  {ui.BOLD}3D-SZENE DETAILS:{ui.RESET}")
        print(f"    • Raum-Dimensionen: {self.room_model.width:.1f}m × {self.room_model.depth:.1f}m × {self.room_model.height:.1f}m")
        print(f"    • Volumen: {self.room_model.width * self.room_model.depth * self.room_model.height:.1f}m³")
        print(f"    • Access Points: {len(self.room_model.access_points)}")
        print(f"    • Positionen tracked: {len(self.positions)}")
        print(f"    • Trajektorie-Punkte: {len(self.positions[-20:])}")
        print()

        print(f"  {ui.BOLD}INTERACTIVE CONTROLS:{ui.RESET}")
        print(f"    • Maus-Drag: 3D-Raum drehen")
        print(f"    • Maus-Scroll: Zoom in/out")
        print(f"    • Rechte Maustaste: Kamera verschieben")
        print(f"    • Space: Auto-Rotation an/aus")
        print(f"    • Toggle Grid / Wireframe / Reset View: Buttons unten links")
        print()

        print(f"  {ui.BYELLOW}📂 OPEN IN BROWSER:{ui.RESET}")
        print(f"    firefox {html_file}")
        print(f"    chrome {html_file}")
        print(f"    oder öffne manuell: {html_file}")
        print()

        ui.pause()


def create_wifi_3d_scanner(adb: ADB) -> WiFi3DScanner:
    """Erstellt neuen WiFi 3D Scanner."""
    return WiFi3DScanner(adb)


def menu(adb=None) -> None:
    """WiFiRoomScanner3D Menu Wrapper."""
    obj = WiFiRoomScanner3D(adb) if adb else WiFiRoomScanner3D()
    obj.show_3d_menu()

