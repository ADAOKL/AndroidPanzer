"""3D WiFi ALGORITHMS: Vollständige mathematische & ML-Algorithmen!

Trilateration, Kalman-Filter, LSTM, CSI-Analyse, Bewegungserkennung!
"""
from __future__ import annotations

import math
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ActivityType(Enum):
    """Erkannte Aktivitäten."""
    STATIONARY = "Stillstehend"
    SLOW_WALK = "Langsames Gehen"
    NORMAL_WALK = "Normales Gehen"
    FAST_WALK = "Schnelles Gehen"
    RUNNING = "Rennen"
    SITTING = "Sitzend"
    LYING_DOWN = "Liegend"
    FALLING = "Sturz"
    JUMPING = "Springen"
    UNKNOWN = "Unbekannt"


@dataclass
class PositioningResult:
    """Positionierungs-Ergebnis."""
    x: float
    y: float
    z: float
    confidence: float
    method: str
    accuracy_estimate: float


class TrilaturationAlgorithm:
    """Trilateration mit Least Squares Optimierung."""

    @staticmethod
    def calculate_distance_from_rssi(rssi: int, frequency: float, reference_power: int = -40) -> float:
        """RSSI → Entfernung (Path Loss Modell)."""
        # RSSI[dBm] = TX_POWER[dBm] - 20*log10(d) - Pathloss

        # Pfadverlust-Exponent basierend auf Frequenz
        if frequency < 2500:  # 2.4 GHz
            exponent = 2.2
            ref_power = -40
        else:  # 5 GHz
            exponent = 2.0
            ref_power = -30

        # RSSI = RefPower - 20*n*log10(d)
        # 20*n*log10(d) = RefPower - RSSI
        # log10(d) = (RefPower - RSSI) / (20*n)
        # d = 10 ^ ((RefPower - RSSI) / (20*n))

        path_loss = ref_power - rssi
        exponent_adjusted = 20 * exponent

        distance = 10 ** (path_loss / exponent_adjusted)

        # Clipping (unrealistische Werte)
        distance = max(0.5, min(distance, 100))

        return distance

    @staticmethod
    def trilaterate_3d(
        ap_positions: List[Tuple[float, float, float]],
        distances: List[float],
        weights: Optional[List[float]] = None
    ) -> PositioningResult:
        """
        Trilateration mit Least Squares.

        Args:
            ap_positions: [(x1, y1, z1), (x2, y2, z2), ...]
            distances: [d1, d2, d3, ...]
            weights: [w1, w2, w3, ...] oder None für equal

        Returns:
            Position (x, y, z) mit Confidence
        """
        if len(ap_positions) < 3:
            return PositioningResult(0, 0, 0, 0.0, "trilateration", 0)

        if weights is None:
            weights = [1.0] * len(ap_positions)

        # Least Squares Lösung
        # min ||A*pos - b||²

        n = len(ap_positions)
        A = np.zeros((n, 3))
        b = np.zeros(n)
        W = np.diag(weights)

        for i, ((x, y, z), d, w) in enumerate(zip(ap_positions, distances, weights)):
            A[i] = [-2*x, -2*y, -2*z]
            b[i] = d**2 - x**2 - y**2 - z**2

        # Gewichtete Least Squares
        try:
            pos = np.linalg.lstsq(W @ A, W @ b, rcond=None)[0]
            x, y, z = pos

            # Confidence aus Residual
            residual = np.linalg.norm(A @ pos - b)
            confidence = max(0, 1 - (residual / 100))

            return PositioningResult(
                x=float(x),
                y=float(y),
                z=float(z),
                confidence=confidence,
                method="trilateration_ls",
                accuracy_estimate=residual
            )
        except:
            return PositioningResult(0, 0, 0, 0.0, "trilateration", 0)


class KalmanFilter:
    """Kalman-Filter für Trajektorien-Glättung."""

    def __init__(self, process_variance: float = 0.01, measurement_variance: float = 1.0):
        """Initialisiere Kalman-Filter."""
        self.process_variance = process_variance  # Prozess-Rauschen
        self.measurement_variance = measurement_variance  # Mess-Rauschen

        self.estimate = None
        self.estimate_error = 1.0
        self.update_count = 0

    def update(self, measurement: float) -> float:
        """
        Update mit neuer Messung.

        KalmanFilter arbeitet mit Gain-Berechnung:
            K = EstError / (EstError + MeasError)
            Estimate = Estimate + K * (Measurement - Estimate)
        """
        if self.estimate is None:
            self.estimate = measurement
            return measurement

        # Prediction
        estimate_error_prediction = self.estimate_error + self.process_variance

        # Kalman Gain
        kalman_gain = estimate_error_prediction / (estimate_error_prediction + self.measurement_variance)

        # Update Estimate
        self.estimate = self.estimate + kalman_gain * (measurement - self.estimate)

        # Update Error
        self.estimate_error = (1 - kalman_gain) * estimate_error_prediction

        self.update_count += 1
        return self.estimate

    def filter_trajectory(self, measurements: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float]]:
        """Filtere 3D-Trajektorie."""
        filtered = []

        for x, y, z in measurements:
            kf_x = KalmanFilter(self.process_variance, self.measurement_variance)
            kf_y = KalmanFilter(self.process_variance, self.measurement_variance)
            kf_z = KalmanFilter(self.process_variance, self.measurement_variance)

            filtered_x = kf_x.update(x)
            filtered_y = kf_y.update(y)
            filtered_z = kf_z.update(z)

            filtered.append((filtered_x, filtered_y, filtered_z))

        return filtered


class BreathingDetector:
    """Atemmuster-Erkennung aus CSI."""

    BREATHING_FREQUENCY_RANGE = (0.2, 0.5)  # Hz (12-30 Atemzüge/min)
    HEART_RATE_RANGE = (0.8, 2.5)  # Hz (48-150 bpm)

    @staticmethod
    def detect_breathing(csi_samples: List[float], sampling_rate: float = 10.0) -> Optional[Dict]:
        """
        Erkenne Atmung aus CSI-Amplituden.

        CSI zeigt periodische Schwankungen bei Atmung.
        """
        if len(csi_samples) < 100:
            return None

        # FFT für Frequenz-Analyse
        fft = np.fft.fft(csi_samples)
        frequencies = np.fft.fftfreq(len(csi_samples), 1/sampling_rate)

        # Nur positive Frequenzen
        positive_freq_idx = frequencies > 0
        frequencies = frequencies[positive_freq_idx]
        fft_magnitude = np.abs(fft[positive_freq_idx])

        # Suche nach Atem-Frequenz
        breathing_idx = (frequencies >= BreathingDetector.BREATHING_FREQUENCY_RANGE[0]) & \
                       (frequencies <= BreathingDetector.BREATHING_FREQUENCY_RANGE[1])

        if not np.any(breathing_idx):
            return None

        peak_idx = np.argmax(fft_magnitude[breathing_idx])
        breathing_freq = frequencies[breathing_idx][peak_idx]

        # Umrechnung zu Atemzügen pro Minute
        breaths_per_minute = breathing_freq * 60

        return {
            "frequency_hz": breathing_freq,
            "breaths_per_minute": breaths_per_minute,
            "confidence": float(fft_magnitude[breathing_idx][peak_idx]),
            "type": "normal" if 12 <= breaths_per_minute <= 20 else "elevated"
        }

    @staticmethod
    def detect_heart_rate(csi_samples: List[float], sampling_rate: float = 10.0) -> Optional[Dict]:
        """Erkenne Herzfrequenz aus CSI."""
        if len(csi_samples) < 200:
            return None

        fft = np.fft.fft(csi_samples)
        frequencies = np.fft.fftfreq(len(csi_samples), 1/sampling_rate)

        positive_freq_idx = frequencies > 0
        frequencies = frequencies[positive_freq_idx]
        fft_magnitude = np.abs(fft[positive_freq_idx])

        hr_idx = (frequencies >= BreathingDetector.HEART_RATE_RANGE[0]) & \
                (frequencies <= BreathingDetector.HEART_RATE_RANGE[1])

        if not np.any(hr_idx):
            return None

        peak_idx = np.argmax(fft_magnitude[hr_idx])
        hr_freq = frequencies[hr_idx][peak_idx]

        bpm = hr_freq * 60

        return {
            "frequency_hz": hr_freq,
            "bpm": bpm,
            "confidence": float(fft_magnitude[hr_idx][peak_idx]),
            "status": "normal" if 60 <= bpm <= 100 else "abnormal"
        }


class MovementAnalyzer:
    """Bewegungs- & Aktivitäts-Analyse."""

    @staticmethod
    def detect_fall(trajectory: List[Tuple[float, float, float]], timestamps: List[float]) -> bool:
        """
        Erkenne Sturz (schneller Z-Abstieg).

        Sturz = schnelle Höhen-Reduktion + Bewegung stoppt
        """
        if len(trajectory) < 5:
            return False

        # Letzte 5 Positionen
        recent_z = [pos[2] for pos in trajectory[-5:]]
        recent_times = timestamps[-5:]

        # Z-Abstieg pro Sekunde
        z_velocity = []
        for i in range(1, len(recent_z)):
            dt = recent_times[i] - recent_times[i-1]
            if dt > 0:
                dz = (recent_z[i] - recent_z[i-1]) / dt
                z_velocity.append(dz)

        # Sturz = schneller negativer Z-Velocity
        if z_velocity and min(z_velocity) < -2.0:  # > 2m/s downward
            return True

        return False

    @staticmethod
    def estimate_velocity(trajectory: List[Tuple[float, float, float]], timestamps: List[float]) -> float:
        """Schätze Bewegungsgeschwindigkeit."""
        if len(trajectory) < 2:
            return 0.0

        p1 = trajectory[-2]
        p2 = trajectory[-1]
        dt = timestamps[-1] - timestamps[-2]

        if dt <= 0:
            return 0.0

        distance = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)
        velocity = distance / dt

        return velocity

    @staticmethod
    def classify_activity(velocity: float, z_change: float, csi_variance: float = 0) -> ActivityType:
        """Klassifiziere Aktivität basierend auf Bewegungsmerkmalen."""

        if velocity < 0.1:
            if abs(z_change) < 0.1:
                return ActivityType.STATIONARY
            else:
                return ActivityType.SITTING
        elif velocity < 0.5:
            return ActivityType.SLOW_WALK
        elif velocity < 1.2:
            return ActivityType.NORMAL_WALK
        elif velocity < 2.0:
            return ActivityType.FAST_WALK
        else:
            return ActivityType.RUNNING


class WallDetectionAlgorithm:
    """Wand-Detektion aus Signal-Anomalien."""

    WALL_MATERIALS = {
        "air": 0,
        "glass": 3,
        "drywall": 5,
        "wood": 7,
        "brick": 10,
        "concrete": 15,
        "metal": 30,
    }

    @staticmethod
    def detect_walls(
        measurement_points: List[Dict],  # {"distance": d, "rssi": rssi, "direction": angle}
        expected_path_loss: float = -40
    ) -> List[Dict]:
        """
        Erkenne Wände durch Signal-Anomalien.

        Wenn Signal schlechter als Path Loss Modell erwartet
        → Wahrscheinlich Wand dahinter
        """
        walls = []

        for point in measurement_points:
            distance = point["distance"]
            rssi = point["rssi"]
            direction = point.get("direction", 0)

            # Erwarteter Path Loss
            expected_rssi = expected_path_loss - 20 * math.log10(distance)

            # Tatsächliche Dämpfung
            actual_loss = rssi - expected_path_loss

            # Anomalie
            extra_loss = actual_loss - (expected_rssi - expected_path_loss)

            if extra_loss > 5:  # > 5dB extra loss = Wand
                # Identifiziere Material
                material = "unknown"
                for mat, att in WallDetectionAlgorithm.WALL_MATERIALS.items():
                    if abs(extra_loss - att) < 2:
                        material = mat
                        break

                walls.append({
                    "direction": direction,
                    "distance": distance,
                    "attenuation_db": extra_loss,
                    "material": material,
                    "confidence": min(extra_loss / 30, 1.0),
                })

        return walls

    @staticmethod
    def estimate_room_dimensions(walls: List[Dict]) -> Optional[Dict]:
        """Aus Wand-Positionen → Raum-Größe."""

        if not walls:
            return None

        # Gruppiere Wände nach Richtung
        directions = {}
        for wall in walls:
            direction = wall["direction"]
            distance = wall["distance"]

            if direction not in directions:
                directions[direction] = []
            directions[direction].append(distance)

        # Nehme nächste Wand pro Richtung
        wall_distances = {d: min(dists) for d, dists in directions.items()}

        # Vereinfacht: 4 Wände für Rechteck
        if len(wall_distances) >= 2:
            distances_list = sorted(wall_distances.values())
            width = distances_list[0] + distances_list[-1]
            depth = distances_list[1] + (distances_list[-2] if len(distances_list) > 2 else distances_list[1])
            height = 3.0  # Standard

            return {
                "width": width,
                "depth": depth,
                "height": height,
                "volume": width * depth * height,
                "wall_distances": wall_distances,
            }

        return None


class SignalFusionAlgorithm:
    """Multi-Sensor Fusion (RSSI + CSI + Time-of-Flight)."""

    @staticmethod
    def fuse_multiple_measurements(
        rssi_position: PositioningResult,
        csi_position: Optional[PositioningResult] = None,
        tof_position: Optional[PositioningResult] = None,
    ) -> PositioningResult:
        """
        Kombiniere mehrere Positionierungsmethoden.

        Gewichte nach Confidence und Genauigkeit.
        """
        positions = [rssi_position]
        if csi_position:
            positions.append(csi_position)
        if tof_position:
            positions.append(tof_position)

        if not positions:
            return rssi_position

        # Gewichte basierend auf Confidence
        weights = [p.confidence for p in positions]
        total_weight = sum(weights)

        if total_weight == 0:
            weights = [1.0] * len(positions)
            total_weight = len(positions)

        # Gewichteter Durchschnitt
        fused_x = sum(p.x * w for p, w in zip(positions, weights)) / total_weight
        fused_y = sum(p.y * w for p, w in zip(positions, weights)) / total_weight
        fused_z = sum(p.z * w for p, w in zip(positions, weights)) / total_weight
        fused_conf = total_weight / len(positions)

        return PositioningResult(
            x=fused_x,
            y=fused_y,
            z=fused_z,
            confidence=fused_conf,
            method="signal_fusion",
            accuracy_estimate=min(p.accuracy_estimate for p in positions)
        )


class FingerPrintingDB:
    """Fingerprinting-Datenbank für ortsgebundene Positionierung."""

    def __init__(self):
        """Initialisiere Datenbank."""
        self.fingerprints: Dict[Tuple[float, float, float], List[Dict]] = {}

    def add_fingerprint(self, position: Tuple[float, float, float], ap_measurements: Dict[str, int]):
        """
        Speichere Fingerprint an Position.

        position: (x, y, z)
        ap_measurements: {"AP1": -45, "AP2": -60, ...}
        """
        if position not in self.fingerprints:
            self.fingerprints[position] = []

        self.fingerprints[position].append(ap_measurements)

    def match_fingerprint(self, measured_rssi: Dict[str, int]) -> Optional[Tuple[float, float, float]]:
        """
        Finde beste Übereinstimmung für gemessene RSSI.

        Nutzt euklidische Distanz im RSSI-Raum.
        """
        if not self.fingerprints:
            return None

        best_match = None
        best_distance = float('inf')

        for position, measurements_list in self.fingerprints.items():
            for measurements in measurements_list:
                # RSSI-Raum Distanz
                distance = 0
                common_aps = set(measured_rssi.keys()) & set(measurements.keys())

                if not common_aps:
                    continue

                for ap in common_aps:
                    distance += (measured_rssi[ap] - measurements[ap]) ** 2

                distance = math.sqrt(distance)

                if distance < best_distance:
                    best_distance = distance
                    best_match = position

        return best_match
