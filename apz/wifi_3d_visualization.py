"""3D WiFi VISUALIZATION: Erweiterte Visualisierung & Analyse-Reports!

3D Point Clouds, Heatmaps, Trajectories, Energie-Analyse!
"""
from __future__ import annotations

import time
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from . import ui


@dataclass
class HeatmapCell:
    """Heatmap-Zelle."""
    x: int
    y: int
    z: int
    signal_strength: float
    activity_count: int
    temperature: float  # 0.0-1.0


class AdvancedVisualization:
    """Advanced 3D Visualisierung & Analysis."""

    def __init__(self, room_width: float = 6.5, room_depth: float = 8.2, room_height: float = 3.0):
        """Initialisiere Visualisierungssystem."""
        self.room_width = room_width
        self.room_depth = room_depth
        self.room_height = room_height
        self.heatmap_grid: Dict[Tuple[int, int, int], HeatmapCell] = {}
        self.trajectories: List[List[Tuple[float, float, float]]] = []

    def generate_signal_heatmap_3d(
        self,
        positions: List[Tuple[float, float, float]],
        signal_strengths: List[float],
        cell_size: float = 0.5
    ) -> Dict[Tuple[int, int, int], float]:
        """
        Generiere 3D Signal-Strength Heatmap.

        Diskretisiere Raum in Zellen und interpoliere Signalstärke.
        """
        heatmap = {}

        # Grid-Zellen
        cells_x = int(self.room_width / cell_size)
        cells_y = int(self.room_depth / cell_size)
        cells_z = int(self.room_height / cell_size)

        for cx in range(cells_x):
            for cy in range(cells_y):
                for cz in range(cells_z):
                    # Zell-Mittelpunkt
                    grid_x = cx * cell_size + cell_size/2
                    grid_y = cy * cell_size + cell_size/2
                    grid_z = cz * cell_size + cell_size/2

                    # Interpoliere Signal (Inverse Distance Weighting)
                    signal = 0.0
                    total_weight = 0.0

                    for pos, strength in zip(positions, signal_strengths):
                        distance = math.sqrt((grid_x-pos[0])**2 + (grid_y-pos[1])**2 + (grid_z-pos[2])**2)

                        if distance < 0.1:
                            signal = strength
                            break

                        weight = 1.0 / (distance + 0.1)
                        signal += strength * weight
                        total_weight += weight

                    if total_weight > 0:
                        signal /= total_weight

                    heatmap[(cx, cy, cz)] = signal

        self.heatmap_grid = heatmap
        return heatmap

    def render_heatmap_2d_topdown(self, max_value: float = -40) -> str:
        """Rendere 2D Heatmap (Top-Down View)."""
        output = "\n  SIGNAL-STÄRKE HEATMAP (Top-Down, Z=1.7m)\n\n"

        cells_x = int(self.room_width / 0.5)
        cells_y = int(self.room_depth / 0.5)

        # ASCII-Art mit Intensitäts-Leveln
        output += "  "
        for cy in range(cells_y):
            for cx in range(cells_x):
                key = (cx, cy, int(1.7/0.5))
                if key in self.heatmap_grid:
                    strength = self.heatmap_grid[key]
                    # Normalisiere zu 0-8
                    level = int(8 * (max_value - strength) / 60)
                    level = max(0, min(8, level))
                    chars = "░▒▓█"
                    char = chars[level // 2]
                else:
                    char = "·"
                output += char
            output += "\n  "

        return output

    def render_3d_ascii_isometric(self) -> str:
        """Rendere 3D Isometrische Ansicht (ASCII)."""
        output = "\n  3D ISOMETRISCHE ANSICHT\n\n"

        output += "     Z (Höhe)\n"
        output += "     ▲\n"
        output += f"     │ {self.room_height}m ┌─────────────────┐\n"
        output += "     │      │ AP3         │\n"
        output += "   1.7m├─────●─────┼─────────┤ Person\n"
        output += "     │      │                 │\n"
        output += "     │      │ AP1             │\n"
        output += "     └──────┴─────────────────► Y(Tiefe)\n"
        output += f"            X(Breite={self.room_width}m)\n"

        return output

    def render_floor_plan_detailed(
        self,
        positions: Optional[List[Tuple[float, float, float]]] = None,
        aps: Optional[List[Tuple[str, float, float]]] = None
    ) -> str:
        """Detaillierter Grundriss mit Personen & APs."""
        output = "\n  DETAILLIERTER GRUNDRISS\n\n"

        # ASCII-Grid
        width_chars = 40
        depth_chars = 30

        grid = [['·' for _ in range(width_chars)] for _ in range(depth_chars)]

        # Wände
        for x in range(width_chars):
            grid[0][x] = '─'
            grid[-1][x] = '─'
        for y in range(depth_chars):
            grid[y][0] = '│'
            grid[y][-1] = '│'

        # Ecken
        grid[0][0] = '┌'
        grid[0][-1] = '┐'
        grid[-1][0] = '└'
        grid[-1][-1] = '┘'

        # Access Points
        if aps:
            for name, x, y in aps:
                px = int((x / self.room_width) * width_chars)
                py = int((y / self.room_depth) * depth_chars)
                if 0 < px < width_chars-1 and 0 < py < depth_chars-1:
                    grid[py][px] = '◆'

        # Positionen
        if positions:
            for x, y, z in positions:
                px = int((x / self.room_width) * width_chars)
                py = int((y / self.room_depth) * depth_chars)
                if 0 < px < width_chars-1 and 0 < py < depth_chars-1:
                    grid[py][px] = '●'

        # Rendere
        output += "  ┌" + "─" * (width_chars-2) + "┐\n"
        for row in grid:
            output += "  │" + "".join(row) + "│\n"
        output += "  └" + "─" * (width_chars-2) + "┘\n"

        return output

    def generate_trajectory_animation(
        self,
        trajectory: List[Tuple[float, float, float]],
        num_frames: int = 10
    ) -> List[str]:
        """
        Generiere Animations-Frames für Trajektorie.

        ASCII-basierte Bewegungsanimation.
        """
        frames = []
        positions_sampled = self._sample_trajectory(trajectory, num_frames)

        for i, pos in enumerate(positions_sampled):
            frame = f"\n  FRAME {i+1}/{len(positions_sampled)}\n\n"
            frame += f"  Position: X={pos[0]:.1f}m Y={pos[1]:.1f}m Z={pos[2]:.1f}m\n"

            # Einfache ASCII-Darstellung
            x_norm = int((pos[0] / self.room_width) * 20)
            y_norm = int((pos[1] / self.room_depth) * 20)

            frame += "\n  "
            for y in range(20):
                for x in range(20):
                    if x == x_norm and y == y_norm:
                        frame += "●"
                    elif x == 0 or x == 19 or y == 0 or y == 19:
                        frame += "█"
                    else:
                        frame += "·"
                frame += "\n  "

            frames.append(frame)

        return frames

    def _sample_trajectory(
        self,
        trajectory: List[Tuple[float, float, float]],
        num_samples: int
    ) -> List[Tuple[float, float, float]]:
        """Sample Trajektorie für Animation."""
        if len(trajectory) <= num_samples:
            return trajectory

        indices = [int(i * len(trajectory) / num_samples) for i in range(num_samples)]
        return [trajectory[i] for i in indices]

    def generate_velocity_profile(
        self,
        trajectory: List[Tuple[float, float, float]],
        timestamps: List[float]
    ) -> str:
        """Generiere Geschwindigkeits-Profil."""
        output = "\n  GESCHWINDIGKEITS-PROFIL\n\n"

        velocities = []
        for i in range(1, len(trajectory)):
            pos1 = trajectory[i-1]
            pos2 = trajectory[i]
            dt = timestamps[i] - timestamps[i-1]

            if dt > 0:
                dist = math.sqrt((pos2[0]-pos1[0])**2 + (pos2[1]-pos1[1])**2)
                v = dist / dt
                velocities.append(v)

        if velocities:
            max_v = max(velocities)
            min_v = min(velocities)
            avg_v = sum(velocities) / len(velocities)

            output += f"  Min Geschwindigkeit: {min_v:.2f} m/s\n"
            output += f"  Max Geschwindigkeit: {max_v:.2f} m/s\n"
            output += f"  Ø Geschwindigkeit:   {avg_v:.2f} m/s\n\n"

            # ASCII-Balken
            output += "  Zeitverlauf:\n"
            for i, v in enumerate(velocities[:30]):  # Max 30 Samples
                bar_length = int(20 * v / max_v) if max_v > 0 else 0
                output += f"  {i:2d}: {'█' * bar_length}\n"

        return output

    def generate_activity_timeline(
        self,
        activities: List[Dict],  # [{"time": t, "activity": type, "confidence": conf}, ...]
        duration_seconds: int = 300
    ) -> str:
        """Generiere Aktivitäts-Timeline."""
        output = "\n  AKTIVITÄTS-TIMELINE\n\n"

        # Gruppiere nach Zeit
        time_slots = {}
        slot_duration = 10  # 10 Sekunden pro Slot

        for activity in activities:
            slot = int(activity["time"] / slot_duration)
            if slot not in time_slots:
                time_slots[slot] = []
            time_slots[slot].append(activity)

        # Rendere
        max_slots = duration_seconds // slot_duration

        output += "  "
        for slot in range(max_slots):
            if slot in time_slots:
                acts = time_slots[slot]
                # Symbol basierend auf häufigster Aktivität
                if any(a["activity"] == "RUNNING" for a in acts):
                    char = "▓"
                elif any(a["activity"] in ["NORMAL_WALK", "FAST_WALK"] for a in acts):
                    char = "▒"
                elif any(a["activity"] == "SITTING" for a in acts):
                    char = "░"
                else:
                    char = "·"
            else:
                char = " "

            output += char

            if (slot + 1) % 30 == 0:
                output += f"  {(slot+1)*slot_duration}s\n  "

        output += f"\n\n  ▓ Running  ▒ Walking  ░ Sitting  · Idle\n"

        return output

    def generate_statistical_summary(
        self,
        trajectory: List[Tuple[float, float, float]],
        timestamps: List[float],
        activities: Optional[List[Dict]] = None
    ) -> str:
        """Generiere statistische Zusammenfassung."""
        output = "\n  STATISTISCHE ANALYSE\n\n"

        if not trajectory:
            return output

        # Raumabdeckung
        x_coords = [p[0] for p in trajectory]
        y_coords = [p[1] for p in trajectory]
        z_coords = [p[2] for p in trajectory]

        output += "  POSITIONIERUNG:\n"
        output += f"    X-Range: {min(x_coords):.1f} - {max(x_coords):.1f} m (Span: {max(x_coords)-min(x_coords):.1f}m)\n"
        output += f"    Y-Range: {min(y_coords):.1f} - {max(y_coords):.1f} m (Span: {max(y_coords)-min(y_coords):.1f}m)\n"
        output += f"    Z-Range: {min(z_coords):.1f} - {max(z_coords):.1f} m (Span: {max(z_coords)-min(z_coords):.1f}m)\n\n"

        # Bewegung
        total_distance = 0.0
        for i in range(1, len(trajectory)):
            p1 = trajectory[i-1]
            p2 = trajectory[i]
            dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)
            total_distance += dist

        duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        avg_speed = total_distance / duration if duration > 0 else 0

        output += "  BEWEGUNG:\n"
        output += f"    Gesamt-Distanz: {total_distance:.1f} m\n"
        output += f"    Dauer: {duration:.0f} Sekunden\n"
        output += f"    Ø Geschwindigkeit: {avg_speed:.2f} m/s\n\n"

        # Aufenthaltsort (Zentroid pro Bereich)
        output += "  AUFENTHALTSANALYSE:\n"
        output += f"    Mittelpunkt: X={sum(x_coords)/len(x_coords):.1f} Y={sum(y_coords)/len(y_coords):.1f}\n"
        output += f"    Raumabdeckung: {(max(x_coords)-min(x_coords)) * (max(y_coords)-min(y_coords)) / (self.room_width * self.room_depth) * 100:.1f}%\n"

        if activities:
            output += f"\n  AKTIVITÄTEN:\n"
            activity_counts = {}
            for act in activities:
                act_type = act.get("activity", "UNKNOWN")
                activity_counts[act_type] = activity_counts.get(act_type, 0) + 1

            for act_type, count in sorted(activity_counts.items(), key=lambda x: x[1], reverse=True):
                output += f"    {act_type}: {count}x\n"

        return output


class ForensicReportGenerator:
    """Forensischer Report-Generator."""

    @staticmethod
    def generate_complete_forensic_report(
        room_model: Dict,
        trajectory: List[Tuple[float, float, float]],
        timestamps: List[float],
        signal_measurements: Dict,
        detected_activities: List[Dict],
        wall_analysis: Optional[Dict] = None
    ) -> str:
        """Generiere komplett forensischen Report."""
        report = "\n" + "=" * 70 + "\n"
        report += "FORENSISCHER 3D-WiFi RAUM-ANALYSE REPORT\n"
        report += "=" * 70 + "\n\n"

        from datetime import datetime
        report += f"Erstellt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # RAUMMODELL
        report += "1. RAUMMODELL\n"
        report += "-" * 70 + "\n"
        if room_model:
            report += f"Breite: {room_model.get('width', 'N/A')} m\n"
            report += f"Tiefe: {room_model.get('depth', 'N/A')} m\n"
            report += f"Höhe: {room_model.get('height', 'N/A')} m\n"
            report += f"Volumen: {room_model.get('volume', 'N/A')} m³\n"
        report += "\n"

        # POSITIONIERUNG
        report += "2. POSITIONIERUNGS-ERGEBNISSE\n"
        report += "-" * 70 + "\n"
        if trajectory:
            report += f"Positionen aufgezeichnet: {len(trajectory)}\n"
            report += f"Zeitspanne: {(timestamps[-1]-timestamps[0] if timestamps else 0):.1f} Sekunden\n"

            x_coords = [p[0] for p in trajectory]
            y_coords = [p[1] for p in trajectory]
            report += f"X-Bereich: {min(x_coords):.1f} - {max(x_coords):.1f} m\n"
            report += f"Y-Bereich: {min(y_coords):.1f} - {max(y_coords):.1f} m\n"
        report += "\n"

        # AKTIVITÄTEN
        report += "3. ERKANNTE AKTIVITÄTEN\n"
        report += "-" * 70 + "\n"
        if detected_activities:
            for act in detected_activities[:10]:
                report += f"{act.get('activity', 'N/A')} ({act.get('confidence', 0)*100:.0f}%) @ {act.get('time', 0):.1f}s\n"
        report += "\n"

        # SIGNALANALYSE
        report += "4. SIGNALANALYSE\n"
        report += "-" * 70 + "\n"
        if signal_measurements:
            report += f"Access Points gemessen: {len(signal_measurements)}\n"
            for ap, rssi in list(signal_measurements.items())[:5]:
                report += f"  {ap}: {rssi} dBm\n"
        report += "\n"

        report += "=" * 70 + "\n"
        report += "ENDE REPORT\n"
        report += "=" * 70 + "\n"

        return report
