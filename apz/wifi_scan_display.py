"""WIFI SCAN BEAUTIFIER: Übersichtliche, strukturierte WiFi-Netzwerk-Anzeige!

Formatiert rohe WiFi Scan Daten in profesionelles, leicht verständliches Format.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

from . import ui


class SignalStrength(Enum):
    """WiFi Signal-Stärke."""
    EXCELLENT = "🟢 AUSGEZEICHNET"  # > -30 dBm
    VERY_GOOD = "🟢 SEHR GUT"  # -30 to -50 dBm
    GOOD = "🟡 GUT"  # -50 to -70 dBm
    FAIR = "🟠 AKZEPTABEL"  # -70 to -85 dBm
    POOR = "🔴 SCHWACH"  # < -85 dBm


class SecurityType(Enum):
    """WiFi Sicherheitstypen."""
    OPEN = "🔓 OFFEN (Keine Verschlüsselung!)"
    WEP = "🟠 WEP (VERALTET!)"
    WPA = "🟡 WPA (Schwach)"
    WPA2 = "🟢 WPA2 (Sicher)"
    WPA3 = "🟢🟢 WPA3 (Sehr sicher)"
    UNKNOWN = "❓ UNBEKANNT"


@dataclass
class WiFiNetwork:
    """Ein WiFi-Netzwerk."""
    ssid: str
    bssid: str
    signal_strength: int  # dBm
    frequency: int  # MHz
    security: SecurityType
    channel: int
    vendor: str = "Unknown"
    is_connected: bool = False
    last_seen: str = ""

    def get_signal_enum(self) -> SignalStrength:
        """Konvertiere dBm zu Signal-Level."""
        if self.signal_strength > -30:
            return SignalStrength.EXCELLENT
        elif self.signal_strength > -50:
            return SignalStrength.VERY_GOOD
        elif self.signal_strength > -70:
            return SignalStrength.GOOD
        elif self.signal_strength > -85:
            return SignalStrength.FAIR
        else:
            return SignalStrength.POOR

    def get_signal_bars(self) -> str:
        """Visualisiere Signal mit Balken."""
        strength = self.get_signal_enum()
        if strength == SignalStrength.EXCELLENT:
            return "████████ 100%"
        elif strength == SignalStrength.VERY_GOOD:
            return "██████░░  75%"
        elif strength == SignalStrength.GOOD:
            return "████░░░░  50%"
        elif strength == SignalStrength.FAIR:
            return "██░░░░░░  25%"
        else:
            return "░░░░░░░░   5%"


class WiFiScanDisplay:
    """Schöne WiFi Scan Ausgabe."""

    def __init__(self):
        """Initialisiere Display."""
        self.networks: List[WiFiNetwork] = []

    def add_network(self, network: WiFiNetwork) -> None:
        """Füge Netzwerk hinzu."""
        self.networks.append(network)

    def show_compact_list(self) -> None:
        """Zeige kompakte Netzwerk-Liste."""
        ui.clear()
        ui.banner(subtitle="📶 WIFI-NETZWERK SCAN - KOMPAKTE ANSICHT")
        print()

        if not self.networks:
            ui.warn("Keine Netzwerke gefunden")
            return

        # Sortiere nach Signal-Stärke
        networks_sorted = sorted(
            self.networks,
            key=lambda n: n.signal_strength,
            reverse=True
        )

        print(f"{ui.BOLD}{'#':3} {'SSID':25} {'SIGNAL':20} {'SICHERHEIT':15} {'KANAL':7}{ui.RESET}")
        print("─" * 80)
        print()

        for i, net in enumerate(networks_sorted, 1):
            connected = "🔗" if net.is_connected else "  "
            bars = net.get_signal_bars()
            dbm_text = f"{net.signal_strength:4d} dBm"
            security_short = net.security.name

            print(f"{connected}{i:2d}  {net.ssid:25} {bars:20} {security_short:15} {net.channel:2d}")

        print()

    def show_detailed_list(self) -> None:
        """Zeige detaillierte Netzwerk-Liste."""
        ui.clear()
        ui.banner(subtitle="📶 WIFI-NETZWERK SCAN - DETAILLIERTE ANSICHT")
        print()

        if not self.networks:
            ui.warn("Keine Netzwerke gefunden")
            return

        # Sortiere nach Signal-Stärke
        networks_sorted = sorted(
            self.networks,
            key=lambda n: n.signal_strength,
            reverse=True
        )

        for i, net in enumerate(networks_sorted, 1):
            connected_icon = "🔗 VERBUNDEN" if net.is_connected else "  Verfügbar"
            signal_strength = net.get_signal_enum()

            print(f"{ui.BOLD}{i}. {net.ssid}{ui.RESET} {connected_icon}")
            print()
            print(f"  📊 Signal:        {signal_strength.value}")
            print(f"     Stärke:       {net.signal_strength} dBm ({net.get_signal_bars()})")
            print()
            print(f"  🔒 Sicherheit:    {net.security.value}")
            print()
            print(f"  📡 BSSID:         {net.bssid}")
            print(f"  🏠 MAC Address:   {net.bssid}")
            print(f"  📍 Kanal:         {net.channel} ({net.frequency} MHz)")
            print(f"  🏭 Hersteller:    {net.vendor}")
            if net.last_seen:
                print(f"  ⏰ Zuletzt gesehen: {net.last_seen}")
            print()
            print("─" * 80)
            print()

    def show_table_view(self) -> None:
        """Zeige als formatierte Tabelle."""
        ui.clear()
        ui.banner(subtitle="📶 WIFI-NETZWERK SCAN - TABELLENANSICHT")
        print()

        if not self.networks:
            ui.warn("Keine Netzwerke gefunden")
            return

        networks_sorted = sorted(
            self.networks,
            key=lambda n: n.signal_strength,
            reverse=True
        )

        # Header
        print(f"{ui.BOLD}")
        print(f"┌{'─'*3}┬{'─'*27}┬{'─'*15}┬{'─'*13}┬{'─'*5}┬{'─'*8}┐")
        print(f"│ # │ SSID                      │ Signal      │ Sicherheit │ Kanal │ Status │")
        print(f"├{'─'*3}┼{'─'*27}┼{'─'*15}┼{'─'*13}┼{'─'*5}┼{'─'*8}┤")
        print(f"{ui.RESET}")

        # Rows
        for i, net in enumerate(networks_sorted, 1):
            status = "✓ Verb." if net.is_connected else "Verfg."
            signal = f"{net.signal_strength:4d}dBm"
            security = net.security.name

            ssid_short = net.ssid[:25] if len(net.ssid) <= 25 else net.ssid[:22] + "..."
            print(f"│{i:2d} │ {ssid_short:25} │ {signal:13} │ {security:13} │ {net.channel:3d}  │ {status:6} │")

        print(f"├{'─'*3}┴{'─'*27}┴{'─'*15}┴{'─'*13}┴{'─'*5}┴{'─'*8}┤")
        print(f"│ Insgesamt: {len(self.networks):2d} Netzwerke gefunden                              │")
        print(f"└{'─'*67}┘")
        print()

    def show_security_analysis(self) -> None:
        """Zeige Sicherheits-Analyse."""
        ui.clear()
        ui.banner(subtitle="🔒 WIFI SICHERHEITS-ANALYSE")
        print()

        if not self.networks:
            ui.warn("Keine Netzwerke gefunden")
            return

        # Zähle nach Sicherheitstyp
        security_counts = {}
        for net in self.networks:
            sec = net.security.name
            security_counts[sec] = security_counts.get(sec, 0) + 1

        # Zähle nach Signal
        excellent = sum(1 for n in self.networks if n.get_signal_enum() == SignalStrength.EXCELLENT)
        very_good = sum(1 for n in self.networks if n.get_signal_enum() == SignalStrength.VERY_GOOD)
        good = sum(1 for n in self.networks if n.get_signal_enum() == SignalStrength.GOOD)
        fair = sum(1 for n in self.networks if n.get_signal_enum() == SignalStrength.FAIR)
        poor = sum(1 for n in self.networks if n.get_signal_enum() == SignalStrength.POOR)

        # Offene Netzwerke
        open_networks = [n for n in self.networks if n.security == SecurityType.OPEN]

        print(f"{ui.BOLD}SICHERHEITSTYPEN:{ui.RESET}")
        print()
        for sec_type, count in security_counts.items():
            print(f"  {sec_type:10} : {count:2d} Netzwerke")
        print()

        print(f"{ui.BOLD}SIGNAL-STÄRKEVERTEILUNG:{ui.RESET}")
        print()
        print(f"  🟢 Ausgezeichnet (>-30 dBm) : {excellent:2d}")
        print(f"  🟢 Sehr gut     (-30/-50)    : {very_good:2d}")
        print(f"  🟡 Gut          (-50/-70)    : {good:2d}")
        print(f"  🟠 Akzeptabel   (-70/-85)    : {fair:2d}")
        print(f"  🔴 Schwach      (<-85 dBm)   : {poor:2d}")
        print()

        if open_networks:
            print(f"{ui.BRED}⚠️  WARNUNG - OFFENE NETZWERKE (KEINE VERSCHLÜSSELUNG!):{ui.RESET}")
            print()
            for net in open_networks:
                print(f"  🔓 {net.ssid} (BSSID: {net.bssid})")
            print()

        print(f"{ui.BOLD}EMPFEHLUNGEN:{ui.RESET}")
        print()
        if open_networks:
            print(f"  ❌ Nutze KEINE offenen Netzwerke!")
            print()
        print(f"  ✓ Bevorzuge Netzwerke mit WPA3 Verschlüsselung")
        print(f"  ✓ Vermeide WEP und alte WPA Netzwerke")
        print(f"  ✓ Wähle Netzwerk mit stärkstem Signal (gutes dBm)")
        print()

    def show_signal_map(self) -> None:
        """Zeige Signal-Stärke Map."""
        ui.clear()
        ui.banner(subtitle="📊 WIFI SIGNAL-STÄRKE MAP")
        print()

        if not self.networks:
            ui.warn("Keine Netzwerke gefunden")
            return

        networks_sorted = sorted(
            self.networks,
            key=lambda n: n.signal_strength,
            reverse=True
        )

        print(f"{ui.BOLD}Signal-Stärke Visualisierung:{ui.RESET}\n")

        for net in networks_sorted:
            bars = net.get_signal_bars()
            level = net.get_signal_enum().value
            status = "🔗" if net.is_connected else "📶"

            # Create bar chart
            max_width = 50
            strength_val = net.signal_strength
            # Normalize -30 to -90 range to 0-100
            normalized = max(0, min(100, int((strength_val + 90) * 100 / 60)))
            bar_width = int(normalized * max_width / 100)
            bar = "█" * bar_width + "░" * (max_width - bar_width)

            print(f"  {status} {net.ssid:20} │{bar}│ {bars}")

        print()


def create_wifi_scan_display() -> WiFiScanDisplay:
    """Factory: Erstellt WiFi Scan Display."""
    return WiFiScanDisplay()


# Demo-Daten für Testing
def create_demo_networks() -> List[WiFiNetwork]:
    """Erstelle Demo-Netzwerke für Testing."""
    return [
        WiFiNetwork(
            ssid="FRITZ!Box 7690 HO",
            bssid="AA:BB:CC:DD:EE:01",
            signal_strength=-35,
            frequency=2440,
            security=SecurityType.WPA2,
            channel=8,
            vendor="AVM",
            is_connected=True,
            last_seen="jetzt"
        ),
        WiFiNetwork(
            ssid="TP-Link Guest",
            bssid="AA:BB:CC:DD:EE:02",
            signal_strength=-62,
            frequency=2437,
            security=SecurityType.WPA2,
            channel=6,
            vendor="TP-Link",
        ),
        WiFiNetwork(
            ssid="OpenWiFi_Free",
            bssid="AA:BB:CC:DD:EE:03",
            signal_strength=-78,
            frequency=2412,
            security=SecurityType.OPEN,
            channel=1,
            vendor="Unknown",
        ),
        WiFiNetwork(
            ssid="Neighbor_Network",
            bssid="AA:BB:CC:DD:EE:04",
            signal_strength=-88,
            frequency=2462,
            security=SecurityType.WPA3,
            channel=11,
            vendor="Asus",
        ),
        WiFiNetwork(
            ssid="Old_Wifi_WEP",
            bssid="AA:BB:CC:DD:EE:05",
            signal_strength=-45,
            frequency=2437,
            security=SecurityType.WEP,
            channel=6,
            vendor="Linksys",
        ),
    ]


if __name__ == "__main__":
    # Demo
    display = create_wifi_scan_display()

    # Add demo networks
    for net in create_demo_networks():
        display.add_network(net)

    # Show different views
    print("\n=== COMPACT VIEW ===\n")
    display.show_compact_list()

    print("\n=== DETAILED VIEW ===\n")
    display.show_detailed_list()

    print("\n=== TABLE VIEW ===\n")
    display.show_table_view()

    print("\n=== SECURITY ANALYSIS ===\n")
    display.show_security_analysis()

    print("\n=== SIGNAL MAP ===\n")
    display.show_signal_map()
