"""ADVANCED 3D ROOM VISUALIZATION: Professionelle 3D-Raumdarstellungen!

Mehrere Ansicht-Modi:
  • Top-Down 2D Floor Plan
  • Isometrische 3D-Ansicht
  • ASCII 3D mit Oberflächen
  • Signal Heatmap 3D
  • Bewegungs-Trajektorie
"""
from __future__ import annotations

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from . import ui


@dataclass
class AccessPoint3D:
    """Access Point mit 3D-Koordinaten."""
    name: str
    x: float
    y: float
    z: float
    signal_strength: int  # dBm


@dataclass
class Position3D:
    """Eine 3D Position."""
    x: float
    y: float
    z: float
    timestamp: float = 0.0


class RoomVisualization:
    """Professionelle 3D Raum Visualisierung."""

    def __init__(self, room_width: float = 6.5, room_height: float = 3.0, room_depth: float = 8.2):
        """Initialisiere mit Raum-Dimensionen."""
        self.room_width = room_width
        self.room_height = room_height
        self.room_depth = room_depth
        self.access_points: List[AccessPoint3D] = []
        self.person_position: Optional[Position3D] = None
        self.trajectory: List[Position3D] = []

    def add_access_point(self, name: str, x: float, y: float, z: float, signal: int) -> None:
        """Füge Access Point hinzu."""
        self.access_points.append(AccessPoint3D(name, x, y, z, signal))

    def set_person_position(self, x: float, y: float, z: float) -> None:
        """Setze Person Position."""
        self.person_position = Position3D(x, y, z)

    def add_to_trajectory(self, x: float, y: float, z: float) -> None:
        """Füge Position zur Trajektorie hinzu."""
        self.trajectory.append(Position3D(x, y, z))

    def show_topdown_2d(self) -> None:
        """Zeige Top-Down 2D Floor Plan."""
        ui.clear()
        ui.banner(subtitle="🗺️  TOP-DOWN ANSICHT (2D Floor Plan)")
        print()

        print(f"  Raum: {self.room_width}m x {self.room_depth}m\n")

        # Zeichne Raum-Rahmen
        width_chars = int(self.room_width * 3)
        depth_chars = int(self.room_depth * 2)

        print(f"  ┌{'─' * (width_chars + 2)}┐")

        # Grid für das Zeichnen
        grid = [[' ' for _ in range(width_chars + 2)] for _ in range(depth_chars)]

        # Zeichne APs
        for ap in self.access_points:
            x = int((ap.x / self.room_width) * (width_chars))
            y = int((ap.y / self.room_depth) * (depth_chars))
            if 0 <= x < width_chars and 0 <= y < depth_chars:
                grid[y][x] = '●'

        # Zeichne Person
        if self.person_position:
            px = int((self.person_position.x / self.room_width) * (width_chars))
            py = int((self.person_position.y / self.room_depth) * (depth_chars))
            if 0 <= px < width_chars and 0 <= py < depth_chars:
                grid[py][px] = '◆'

        # Zeige Grid
        for row in grid:
            print(f"  │{''.join(row)}│")

        print(f"  └{'─' * (width_chars + 2)}┘")
        print()

        # Legende
        print(f"  {ui.BOLD}LEGENDE:{ui.RESET}")
        print(f"    ● = Access Point")
        print(f"    ◆ = Person Position")
        print()

        # Signal-Info
        if self.access_points:
            print(f"  {ui.BOLD}ACCESS POINTS:{ui.RESET}")
            for ap in self.access_points:
                signal_bars = self._get_signal_bars(ap.signal_strength)
                print(f"    {ap.name:10} Position({ap.x:.1f}, {ap.y:.1f})  Signal: {signal_bars} {ap.signal_strength}dBm")
        print()

        ui.pause()

    def show_isometric_3d(self) -> None:
        """Zeige Isometrische 3D-Ansicht."""
        ui.clear()
        ui.banner(subtitle="🎲 ISOMETRISCHE 3D-ANSICHT")
        print()

        print(f"  Raum-Dimensionen: {self.room_width}m x {self.room_depth}m x {self.room_height}m\n")

        # Vereinfachte isometrische Zeichnung
        print(f"       {ui.BOLD}Z (Höhe){ui.RESET}")
        print(f"       ▲")
        print(f"    {self.room_height:.1f}m ┌─────────────────────────┐")
        print(f"       │                     │")
        print(f"    1.7m├─────●───────────────┤ {ui.BOLD}Person ({self.person_position.x if self.person_position else '?':.1f}m){ui.RESET}")
        print(f"       │     │                 │")
        print(f"    0.0m└─────┴─────────────────┴──►")
        print(f"           {self.room_width:.1f}m    X")
        print()

        # APs Position
        print(f"  {ui.BOLD}ACCESS POINTS - 3D POSITIONEN:{ui.RESET}")
        for ap in self.access_points:
            print(f"    {ap.name:10} X:{ap.x:5.1f}m  Y:{ap.y:5.1f}m  Z:{ap.z:5.1f}m  Signal:{ap.signal_strength}dBm")
        print()

        if self.person_position:
            print(f"  {ui.BOLD}PERSON POSITION:{ui.RESET}")
            print(f"    X:{self.person_position.x:5.1f}m  Y:{self.person_position.y:5.1f}m  Z:{self.person_position.z:5.1f}m")
        print()

        ui.pause()

    def show_ascii_3d_detailed(self) -> None:
        """Zeige detaillierte ASCII 3D-Ansicht mit Oberflächen."""
        ui.clear()
        ui.banner(subtitle="🏠 DETAILLIERTE 3D ASCII-ANSICHT")
        print()

        print(f"  {ui.BOLD}RAUM STRUKTUR:{ui.RESET}\n")

        # Zeichne 3D-Raum mit Oberflächen
        lines = [
            "        Z",
            "        ▲",
            f"   {self.room_height:.1f}m ┌─────────────────────┐",
            "        │  ◢◣                  │",
            "        │   ◢Person◣           │",
            f" {self.room_height/2:.1f}m ├─────◢◣───────────────┤",
            "        │     ◢◣                │",
            "    0.0m└─────────────────────┴──► Y",
            f"         0    {self.room_width:.1f}m    X",
        ]

        for line in lines:
            print(f"  {line}")

        print()

        # 3D Koordinaten-Info
        print(f"  {ui.BOLD}WAND-POSITIONEN:{ui.RESET}")
        print(f"    X-Wand (links):    x=0.0m,    y=[0..{self.room_depth:.1f}m],  z=[0..{self.room_height:.1f}m]")
        print(f"    X-Wand (rechts):   x={self.room_width:.1f}m,  y=[0..{self.room_depth:.1f}m],  z=[0..{self.room_height:.1f}m]")
        print(f"    Y-Wand (vorne):    y=0.0m,    x=[0..{self.room_width:.1f}m],  z=[0..{self.room_height:.1f}m]")
        print(f"    Y-Wand (hinten):   y={self.room_depth:.1f}m,  x=[0..{self.room_width:.1f}m],  z=[0..{self.room_height:.1f}m]")
        print()

        ui.pause()

    def show_signal_heatmap_3d(self) -> None:
        """Zeige Signal-Stärke Heatmap in 3D."""
        ui.clear()
        ui.banner(subtitle="🌡️  SIGNAL-STÄRKE HEATMAP 3D")
        print()

        print(f"  {ui.BOLD}SIGNAL-STÄRKE VERTEILUNG IM RAUM:{ui.RESET}\n")

        # Erstelle einfaches Heatmap-Grid
        if not self.access_points:
            print("  Keine Access Points definiert!")
            ui.pause()
            return

        # Berechne durchschnittliche Signal-Stärke pro Bereich
        grid_width = 8
        grid_depth = 6

        for y_idx in range(grid_depth):
            line = "  "
            for x_idx in range(grid_width):
                x = (x_idx / grid_width) * self.room_width
                y = (y_idx / grid_depth) * self.room_depth

                # Berechne durchschnittliche Signal-Stärke zu allen APs
                distances = []
                for ap in self.access_points:
                    dist = math.sqrt((x - ap.x)**2 + (y - ap.y)**2)
                    distances.append(dist if dist > 0 else 0.1)

                # Signalstärke basierend auf Distanz (einfaches Modell)
                avg_signal = sum([ap.signal_strength + 40 - 20 * math.log10(d) for ap, d in zip(self.access_points, distances)]) / len(self.access_points)

                # Farbcode
                if avg_signal > -50:
                    char = "█"
                    color = ui.BGREEN
                elif avg_signal > -60:
                    char = "▓"
                    color = ui.BYELLOW
                elif avg_signal > -75:
                    char = "▒"
                    color = ui.BYELLOW
                else:
                    char = "░"
                    color = ui.BRED

                line += f"{color}{char}{ui.RESET} "

            print(line)

        print()
        print(f"  {ui.BGREEN}█{ui.RESET} Sehr stark (> -50dBm)")
        print(f"  {ui.BYELLOW}▓{ui.RESET} Stark (-50 bis -60dBm)")
        print(f"  {ui.BYELLOW}▒{ui.RESET} Moderat (-60 bis -75dBm)")
        print(f"  {ui.BRED}░{ui.RESET} Schwach (< -75dBm)")
        print()

        ui.pause()

    def show_trajectory(self) -> None:
        """Zeige Bewegungs-Trajektorie."""
        ui.clear()
        ui.banner(subtitle="📍 BEWEGUNGS-TRAJEKTORIE")
        print()

        if not self.trajectory:
            print("  Keine Trajektorie-Daten verfügbar!")
            ui.pause()
            return

        print(f"  {ui.BOLD}BEWEGUNGS-VERLAUF ({len(self.trajectory)} Positionen):{ui.RESET}\n")

        # Top-Down Trajektorie
        width_chars = int(self.room_width * 3)
        depth_chars = int(self.room_depth * 2)

        grid = [[' ' for _ in range(width_chars + 2)] for _ in range(depth_chars)]

        # Zeichne Trajektorie
        for i, pos in enumerate(self.trajectory):
            x = int((pos.x / self.room_width) * (width_chars))
            y = int((pos.y / self.room_depth) * (depth_chars))
            if 0 <= x < width_chars and 0 <= y < depth_chars:
                if i == 0:
                    grid[y][x] = '●'  # Start
                elif i == len(self.trajectory) - 1:
                    grid[y][x] = '★'  # Ende
                else:
                    grid[y][x] = '•'  # Pfad

        # Zeichne Rahmen
        print(f"  ┌{'─' * (width_chars + 2)}┐")
        for row in grid:
            print(f"  │{''.join(row)}│")
        print(f"  └{'─' * (width_chars + 2)}┘")
        print()

        print(f"  {ui.BOLD}TRAJEKTORIE-STATISTIKEN:{ui.RESET}")
        print(f"    Start-Position:    ({self.trajectory[0].x:.1f}, {self.trajectory[0].y:.1f}, {self.trajectory[0].z:.1f})")
        print(f"    End-Position:      ({self.trajectory[-1].x:.1f}, {self.trajectory[-1].y:.1f}, {self.trajectory[-1].z:.1f})")

        # Berechne Distanz
        total_distance = 0
        for i in range(1, len(self.trajectory)):
            p1 = self.trajectory[i-1]
            p2 = self.trajectory[i]
            dist = math.sqrt((p2.x-p1.x)**2 + (p2.y-p1.y)**2 + (p2.z-p1.z)**2)
            total_distance += dist

        print(f"    Gesamtstrecke:     {total_distance:.1f}m")
        print(f"    Positionen:        {len(self.trajectory)}")
        print()

        ui.pause()

    @staticmethod
    def _get_signal_bars(signal_dbm: int) -> str:
        """Konvertiere dBm zu Balken."""
        if signal_dbm > -50:
            return "████ Ausgezeichnet"
        elif signal_dbm > -60:
            return "███░ Sehr Gut"
        elif signal_dbm > -70:
            return "██░░ Gut"
        elif signal_dbm > -80:
            return "█░░░ Schwach"
        else:
            return "░░░░ Sehr Schwach"


def create_room_visualization(width: float = 6.5, height: float = 3.0, depth: float = 8.2) -> RoomVisualization:
    """Factory: Erstellt RoomVisualization."""
    return RoomVisualization(width, height, depth)
