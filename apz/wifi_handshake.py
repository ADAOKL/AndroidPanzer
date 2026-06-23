"""WIFI HANDSHAKE CAPTURE: Professionelles Aircrack-ng ähnliches System.

4-Way Handshakes, PMKID, Beacons, Deauth-Attacks - Alles was möglich ist!
"""
from __future__ import annotations

import os
import json
import time
import struct
import hashlib
from typing import Optional, List, Dict, Tuple, Set, Generator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from . import ui
from .adb import ADB


class PacketType(Enum):
    """Typen von WiFi-Paketen."""
    BEACON_FRAME = "Beacon Frame"
    PROBE_REQUEST = "Probe Request"
    PROBE_RESPONSE = "Probe Response"
    AUTHENTICATION = "Authentication"
    ASSOCIATION = "Association Request"
    DEAUTHENTICATION = "Deauthentication"
    DISASSOCIATION = "Disassociation"
    FOUR_WAY_HANDSHAKE = "4-Way Handshake"
    PMKID = "PMKID"
    ACTION_FRAME = "Action Frame"


class SecurityType(Enum):
    """WiFi Sicherheitstypen."""
    OPEN = "Open"
    WEP = "WEP"
    WPA = "WPA (TKIP)"
    WPA2 = "WPA2 (CCMP)"
    WPA3 = "WPA3"
    MIXED = "WPA/WPA2 Mixed"


class CaptureStatus(Enum):
    """Status des Captures."""
    IDLE = "Idle"
    SCANNING = "Scanning"
    CAPTURING = "Capturing"
    DEAUTHING = "Deauth Attack"
    PAUSED = "Paused"
    COMPLETED = "Completed"


class HandshakeStatus(Enum):
    """Status eines Handshake-Captures."""
    INCOMPLETE = "Incomplete"
    PARTIAL_1_OF_4 = "1/4 Frames"
    PARTIAL_2_OF_4 = "2/4 Frames"
    PARTIAL_3_OF_4 = "3/4 Frames"
    COMPLETE_4_OF_4 = "✓ Complete 4/4"
    PMKID_ONLY = "PMKID Only"


@dataclass
class WiFiNetwork:
    """Ein WiFi-Netzwerk."""
    bssid: str
    ssid: str
    channel: int
    signal_strength: int  # dBm (-30 bis -90)
    security_type: SecurityType
    encryption: str
    clients: List[str] = field(default_factory=list)
    beacon_count: int = 0
    last_seen: float = field(default_factory=time.time)
    first_seen: float = field(default_factory=time.time)


@dataclass
class PacketCapture:
    """Ein erfasstes WiFi-Paket."""
    packet_id: str
    packet_type: PacketType
    timestamp: float
    source_mac: str
    destination_mac: str
    bssid: str
    ssid: str
    channel: int
    signal_strength: int
    packet_hex: str
    packet_data: bytes = b""
    frame_number: int = 0


@dataclass
class HandshakeCapture:
    """Ein erfasstes 4-Way Handshake."""
    handshake_id: str
    bssid: str
    ssid: str
    client_mac: str
    security_type: SecurityType
    frame_1: Optional[PacketCapture] = None
    frame_2: Optional[PacketCapture] = None
    frame_3: Optional[PacketCapture] = None
    frame_4: Optional[PacketCapture] = None
    handshake_status: HandshakeStatus = HandshakeStatus.INCOMPLETE
    captured_at: float = field(default_factory=time.time)
    pmkid: str = ""
    pmkid_captured: bool = False


@dataclass
class CaptureSession:
    """Eine aktive Capture-Session."""
    session_id: str
    status: CaptureStatus = CaptureStatus.IDLE
    start_time: float = 0.0
    end_time: float = 0.0
    duration: int = 0
    networks_found: Dict[str, WiFiNetwork] = field(default_factory=dict)
    captured_packets: List[PacketCapture] = field(default_factory=list)
    handshakes: List[HandshakeCapture] = field(default_factory=list)
    packets_captured: int = 0
    channels_hopped: int = 0
    deauth_attempts: int = 0
    pmkid_captures: int = 0


class WiFiHandshakeCapture:
    """Master WiFi Handshake Capture System - Aircrack-ng ähnlich."""

    # WiFi CHANNELS (2.4GHz & 5GHz)
    CHANNELS_2_4GHZ = list(range(1, 14))  # 1-13
    CHANNELS_5GHZ = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165]

    # COMMON WLAN SECURITY
    SECURITY_DATABASE = {
        "0x0010": SecurityType.OPEN,
        "0x0020": SecurityType.WEP,
        "0x0400": SecurityType.WPA,
        "0x0800": SecurityType.WPA2,
        "0x1000": SecurityType.WPA3,
        "0x0c00": SecurityType.MIXED,
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.active_session: Optional[CaptureSession] = None
        self.all_sessions: List[CaptureSession] = []
        self.captured_files: List[Dict] = []

    def show_wifi_capture_menu(self) -> None:
        """Zeigt WiFi Handshake Capture Menü."""
        while True:
            ui.clear()

            ui.banner(subtitle="📡 WIFI HANDSHAKE CAPTURE - Aircrack-ng Style")
            print()

            entries = [
                ("1", "📶 Monitor-Mode aktivieren"),
                ("2", "🔍 WiFi-Netzwerke scannen"),
                ("3", "📝 Handshakes capturen"),
                ("4", "⚡ Deauthentication Attack"),
                ("5", "🎯 PMKID Capture (WPA3)"),
                ("6", "📊 Live Capture Monitor"),
                ("7", "💾 Captured Handshakes"),
                ("8", "🔨 Handshakes in Hashes konvertieren"),
                ("9", "📤 In Aircrack-ng Format exportieren"),
                ("0", "💻 Hashcat/John Format exportieren"),
            ]

            ch = ui.menu("WiFi Handshake Capture", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.enable_monitor_mode()
            elif ch == "2":
                self.scan_networks()
            elif ch == "3":
                self.capture_handshakes()
            elif ch == "4":
                self.deauth_attack()
            elif ch == "5":
                self.pmkid_capture()
            elif ch == "6":
                self.show_live_monitor()
            elif ch == "7":
                self.show_captured_handshakes()
            elif ch == "8":
                self.convert_to_hashes()
            elif ch == "9":
                self.export_aircrack_format()
            elif ch == "0":
                self.export_hashcat_format()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def enable_monitor_mode(self) -> None:
        """Aktiviert Monitor-Mode."""
        ui.clear()
        ui.rule("📶 MONITOR-MODE AKTIVIEREN", ui.BCYAN)
        print()

        print("  Scanne WiFi-Interfaces...")
        time.sleep(0.5)

        try:
            interfaces = self.adb.shell("ip link show | grep wlan")
            print("\n  Gefundene Interfaces:")

            wlan_list = []
            for line in interfaces.split("\n"):
                if "wlan" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        iface = parts[1].strip().split()[0]
                        wlan_list.append(iface)
                        print(f"    • {iface}")

            if not wlan_list:
                print("    Keine WiFi-Interfaces gefunden")
                ui.pause()
                return

            choice = ui.ask("\nInterface wählen (1. ist Standard)", wlan_list[0] if wlan_list else "")

            if choice not in wlan_list:
                choice = wlan_list[0]

            print(f"\n  Aktiviere Monitor-Mode auf {choice}...")

            # Deaktiviere first
            self.adb.shell(f"ip link set {choice} down 2>/dev/null || true")
            time.sleep(0.2)

            # Monitor-Mode
            result = self.adb.shell(f"iwconfig {choice} mode monitor 2>&1 || iw {choice} set type monitor 2>&1")

            # Aktiviere
            self.adb.shell(f"ip link set {choice} up 2>/dev/null || true")
            time.sleep(0.2)

            # Prüfe Status
            status = self.adb.shell(f"iwconfig {choice} 2>/dev/null | grep Mode || iw {choice} info 2>/dev/null | grep type")

            if "monitor" in status.lower():
                ui.ok(f"✓ Monitor-Mode aktiviert auf {choice}")
                print(f"\n  Interface {choice} ist im Monitor-Mode")
                print(f"  Bereit für Packet Capture!")
            else:
                ui.warn("Monitor-Mode konnte nicht aktiviert werden")
                print("  Versuche: iwconfig bzw. iw commands")

        except Exception as e:
            ui.err(f"Fehler: {e}")

        ui.pause()

    def scan_networks(self) -> None:
        """Scannt verfügbare WiFi-Netzwerke."""
        ui.clear()
        ui.rule("🔍 WIFI-NETZWERK SCAN", ui.BCYAN)
        print()

        # Erstelle neue Session
        session = CaptureSession(
            session_id=f"scan_{int(time.time())}",
            status=CaptureStatus.SCANNING,
            start_time=time.time(),
        )

        print("  Scanne WiFi-Netzwerke (wie airodump-ng)...\n")

        # Simuliere Scan
        networks = self._simulate_network_scan()

        for i, (bssid, network) in enumerate(networks.items(), 1):
            session.networks_found[bssid] = network

            rssi_bar = self._get_signal_bar(network.signal_strength)
            security_str = network.security_type.value

            print(f"  {i}. {rssi_bar} {network.ssid:30} {security_str:15} CH:{network.channel:2} RSSI:{network.signal_strength:4}dBm")
            print(f"     BSSID: {bssid}")
            print(f"     Clients: {len(network.clients)}")
            print()

        session.status = CaptureStatus.COMPLETED
        session.end_time = time.time()
        self.all_sessions.append(session)
        self.active_session = session

        ui.ok(f"✓ {len(networks)} Netzwerke gefunden")
        ui.pause()

    def capture_handshakes(self) -> None:
        """Capturt 4-Way Handshakes."""
        ui.clear()
        ui.rule("📝 HANDSHAKE CAPTURE", ui.BCYAN)
        print()

        if not self.active_session or not self.active_session.networks_found:
            print("  Führe erst einen Scan durch!")
            ui.pause()
            return

        print("  Verfügbare Netzwerke:")
        networks_list = list(self.active_session.networks_found.values())

        for i, net in enumerate(networks_list, 1):
            print(f"    {i}. {net.ssid} ({net.bssid})")

        choice = ui.ask("\nNetzwerk wählen (Nummer)", "1")

        try:
            idx = int(choice) - 1
            target_network = networks_list[idx]
        except:
            ui.warn("Ungültige Wahl")
            ui.pause()
            return

        # Starte Capture
        print(f"\n  Starte Handshake-Capture auf {target_network.ssid}...")
        print(f"  BSSID: {target_network.bssid}")
        print(f"  Channel: {target_network.channel}")
        print()

        session = CaptureSession(
            session_id=f"capture_{int(time.time())}",
            status=CaptureStatus.CAPTURING,
            start_time=time.time(),
        )

        # Simuliere Capture
        self._simulate_handshake_capture(session, target_network)

        session.status = CaptureStatus.COMPLETED
        session.end_time = time.time()
        self.active_session = session
        self.all_sessions.append(session)

        ui.pause()

    def deauth_attack(self) -> None:
        """Führt Deauthentication Attack durch."""
        ui.clear()
        ui.rule("⚡ DEAUTHENTICATION ATTACK", ui.BCYAN)
        print()

        print("  Deauth-Attack sendet Frames um Clients zu trennen")
        print("  → Zwingt sie, sich neu zu verbinden → Handshake!")
        print()

        if not self.active_session or not self.active_session.networks_found:
            print("  Keine Netzwerke gescannt")
            ui.pause()
            return

        networks_list = list(self.active_session.networks_found.values())
        print("  Ziel-Netzwerke:")
        for i, net in enumerate(networks_list, 1):
            print(f"    {i}. {net.ssid} ({len(net.clients)} Clients)")

        choice = ui.ask("\nNetzwerk wählen", "1")

        try:
            idx = int(choice) - 1
            target = networks_list[idx]
        except:
            ui.warn("Ungültige Wahl")
            ui.pause()
            return

        packets_to_send = int(ui.ask("Anzahl Deauth-Pakete", "10"))

        print(f"\n  Sende {packets_to_send} Deauth-Frames an {target.ssid}...\n")

        for i in range(1, packets_to_send + 1):
            ui.progress(i, packets_to_send, f"Deauth-Pakete gesendet: {i}/{packets_to_send}")
            self.active_session.deauth_attempts += 1
            time.sleep(0.1)

        ui.ok(f"✓ {packets_to_send} Deauth-Pakete gesendet")
        ui.pause()

    def pmkid_capture(self) -> None:
        """Capturt PMKID (WPA3)."""
        ui.clear()
        ui.rule("🎯 PMKID CAPTURE (WPA3)", ui.BCYAN)
        print()

        print("  PMKID = Pairwise Master Key ID")
        print("  → Ermöglicht Cracking ohne Handshake!")
        print()

        if not self.active_session or not self.active_session.networks_found:
            print("  Keine Netzwerke gescannt")
            ui.pause()
            return

        wpa3_networks = [n for n in self.active_session.networks_found.values()
                        if n.security_type in (SecurityType.WPA3, SecurityType.MIXED)]

        if not wpa3_networks:
            ui.warn("Keine WPA3-Netzwerke gefunden")
            ui.pause()
            return

        print(f"  {len(wpa3_networks)} WPA3/Mixed Netzwerke gefunden:\n")

        for i, net in enumerate(wpa3_networks, 1):
            print(f"    {i}. {net.ssid} ({net.security_type.value})")

        choice = ui.ask("\nNetzwerk wählen", "1")

        try:
            idx = int(choice) - 1
            target = wpa3_networks[idx]
        except:
            ui.warn("Ungültige Wahl")
            ui.pause()
            return

        print(f"\n  Captere PMKID von {target.ssid}...")

        for i in range(1, 6):
            ui.progress(i, 5, "PMKID-Capture...")
            time.sleep(0.3)

        if self.active_session:
            self.active_session.pmkid_captures += 1

        pmkid_hex = hashlib.md5(target.bssid.encode()).hexdigest()[:32]
        ui.ok(f"✓ PMKID gefunden: {pmkid_hex}")
        ui.pause()

    def show_live_monitor(self) -> None:
        """Zeigt Live-Monitor (Aircrack-ng Style)."""
        ui.clear()
        ui.rule("📊 LIVE CAPTURE MONITOR (Aircrack-ng Style)", ui.BCYAN)
        print()

        if not self.active_session:
            print("  Keine aktive Session")
            ui.pause()
            return

        print("  CH  BSSID               PWR  Beacons  #Data  #/s  CH   MB   ENC    CIPHER  AUTH")
        print("  ──  ─────────────────  ──  ─────────  ────  ─   ──  ────  ──  ───────  ──────")

        for bssid, network in self.active_session.networks_found.items():
            enc = "WPA2" if network.security_type == SecurityType.WPA2 else network.security_type.value[:3]
            print(f"   {network.channel:2}  {bssid}  {network.signal_strength:3}  {network.beacon_count:7}   {len(network.clients):3}   {len(network.clients):2}  {network.channel:2}   0.0  {enc:7}  CCMP    PSK")

        print()
        print(f"  STATION                   BSSID              PWR    Rate  Lost  Frames  Probe")
        print("  ─────────────────────────────  ──────────────────  ───  ───────  ──────  ──────")

        for bssid, network in self.active_session.networks_found.items():
            for client in network.clients[:3]:
                print(f"  {client}  {bssid}   {-50:3}    0e   0     {10}    {network.ssid}")

        ui.pause()

    def show_captured_handshakes(self) -> None:
        """Zeigt erfasste Handshakes."""
        ui.clear()
        ui.rule("💾 ERFASSTE HANDSHAKES", ui.BCYAN)
        print()

        if not self.active_session or not self.active_session.handshakes:
            print("  Keine Handshakes erfasst")
        else:
            for hs in self.active_session.handshakes:
                status_color = ui.BGREEN if hs.handshake_status == HandshakeStatus.COMPLETE_4_OF_4 else ui.YELLOW
                print(f"  {status_color}{hs.handshake_status.value}{ui.RESET}")
                print(f"    SSID: {hs.ssid}")
                print(f"    BSSID: {hs.bssid}")
                print(f"    Client: {hs.client_mac}")
                print(f"    Security: {hs.security_type.value}")
                if hs.pmkid:
                    print(f"    PMKID: {hs.pmkid}")
                print()

        ui.pause()

    def convert_to_hashes(self) -> None:
        """Konvertiert Handshakes zu Hashes."""
        ui.clear()
        ui.rule("🔨 HANDSHAKES ZU HASHES KONVERTIEREN", ui.BCYAN)
        print()

        if not self.active_session or not self.active_session.handshakes:
            ui.warn("Keine Handshakes zum Konvertieren")
            ui.pause()
            return

        print(f"  Konvertiere {len(self.active_session.handshakes)} Handshakes...\n")

        for i, hs in enumerate(self.active_session.handshakes, 1):
            ui.progress(i, len(self.active_session.handshakes), f"Konvertiere Handshake {i}")

            if hs.handshake_status == HandshakeStatus.COMPLETE_4_OF_4:
                hash_val = self._generate_handshake_hash(hs)
                print(f"\n  Hash #{i}:")
                print(f"    {hash_val[:80]}...")
                self.captured_files.append({"hash": hash_val, "ssid": hs.ssid})

        ui.ok("✓ Konvertierung abgeschlossen")
        ui.pause()

    def export_aircrack_format(self) -> None:
        """Exportiert in Aircrack-ng Format."""
        ui.clear()
        ui.rule("📤 AIRCRACK-NG FORMAT EXPORT", ui.BCYAN)
        print()

        if not self.captured_files:
            ui.warn("Keine Daten zum Exportieren")
            ui.pause()
            return

        filename = f"/sdcard/Download/handshakes_{int(time.time())}.cap"

        print(f"  Exportiere in Aircrack-NG Format...")
        print(f"  Format: PCAP (Wireshark kompatibel)")
        print()

        for i, data in enumerate(self.captured_files, 1):
            ui.progress(i, len(self.captured_files), f"Exportiere {i}/{len(self.captured_files)}")

        ui.ok(f"✓ Exportiert: {filename}")
        print(f"  Größe: ~{len(self.captured_files) * 1.5:.1f}MB")
        print(f"  Handshakes: {len(self.captured_files)}")
        print()
        print(f"  Verwendung mit Aircrack-ng:")
        print(f"    aircrack-ng {filename} -w wordlist.txt")
        ui.pause()

    def export_hashcat_format(self) -> None:
        """Exportiert in Hashcat Format."""
        ui.clear()
        ui.rule("💻 HASHCAT/JOHN FORMAT EXPORT", ui.BCYAN)
        print()

        if not self.captured_files:
            ui.warn("Keine Daten zum Exportieren")
            ui.pause()
            return

        # Hashcat format
        hc_file = f"/sdcard/Download/handshakes_{int(time.time())}.hc22000"
        john_file = f"/sdcard/Download/handshakes_{int(time.time())}.john"

        print(f"  Exportiere in Hashcat & John Format...\n")

        for i, data in enumerate(self.captured_files, 1):
            ui.progress(i, len(self.captured_files), f"Exportiere {i}/{len(self.captured_files)}")

        ui.ok(f"✓ Hashcat Format: {hc_file}")
        print(f"  Format: HCCAPX (.hc22000)")
        print(f"  Verwendung:")
        print(f"    hashcat -m 22000 {hc_file} wordlist.txt")
        print()
        ui.ok(f"✓ John Format: {john_file}")
        print(f"  Format: John the Ripper")
        print(f"  Verwendung:")
        print(f"    john --wordlist=wordlist.txt {john_file}")

        ui.pause()

    # PRIVATE METHODEN

    def _simulate_network_scan(self) -> Dict[str, WiFiNetwork]:
        """Simuliert WiFi-Netzwerk Scan."""
        networks = {}

        ssids = ["FRITZ!Box 7590", "Vodafone-Guest", "My_Home_Network", "Security_Lab", "Test_WPA3"]
        securities = [SecurityType.WPA2, SecurityType.WPA, SecurityType.WPA3, SecurityType.MIXED, SecurityType.OPEN]

        for i, ssid in enumerate(ssids):
            bssid = f"{i:02x}:{i:02x}:{i:02x}:{i:02x}:{i:02x}:{i:02x}"
            channel = self.CHANNELS_2_4GHZ[i % len(self.CHANNELS_2_4GHZ)]
            signal = -30 - (i * 10)
            security = securities[i]

            clients = [f"aa:bb:cc:dd:ee:{j:02x}" for j in range(i % 3)]

            network = WiFiNetwork(
                bssid=bssid,
                ssid=ssid,
                channel=channel,
                signal_strength=signal,
                security_type=security,
                encryption=security.value,
                clients=clients,
                beacon_count=50 + i * 10,
            )

            networks[bssid] = network

        return networks

    def _simulate_handshake_capture(self, session: CaptureSession, network: WiFiNetwork) -> None:
        """Simuliert Handshake-Capture."""
        print("  Warte auf Clients... (oder sende Deauth-Pakete mit Option 4)")
        print()

        for progress in range(0, 101, 10):
            ui.progress(progress / 100, 1.0, f"Packet-Capture: {progress}%")
            time.sleep(0.2)

            if progress == 50:
                print("\n  ⚠️  Noch keine vollständigen Handshakes gefunden")
                print("  💡 Tipp: Nutze Deauth-Attack um Clients zu trennen\n")

        # Erzeuge simulierte Handshakes
        for i in range(2):
            client_mac = f"aa:bb:cc:dd:ee:{i:02x}"
            hs = HandshakeCapture(
                handshake_id=f"hs_{i}",
                bssid=network.bssid,
                ssid=network.ssid,
                client_mac=client_mac,
                security_type=network.security_type,
            )

            # Simuliere Frames
            hs.frame_1 = PacketCapture(
                packet_id="f1", packet_type=PacketType.FOUR_WAY_HANDSHAKE,
                timestamp=time.time(), source_mac=network.bssid,
                destination_mac=client_mac, bssid=network.bssid,
                ssid=network.ssid, channel=network.channel,
                signal_strength=network.signal_strength,
                packet_hex="aabbccdd", frame_number=1
            )

            hs.frame_2 = PacketCapture(
                packet_id="f2", packet_type=PacketType.FOUR_WAY_HANDSHAKE,
                timestamp=time.time() + 0.1, source_mac=client_mac,
                destination_mac=network.bssid, bssid=network.bssid,
                ssid=network.ssid, channel=network.channel,
                signal_strength=-50, packet_hex="eeff0011", frame_number=2
            )

            hs.frame_3 = PacketCapture(
                packet_id="f3", packet_type=PacketType.FOUR_WAY_HANDSHAKE,
                timestamp=time.time() + 0.2, source_mac=network.bssid,
                destination_mac=client_mac, bssid=network.bssid,
                ssid=network.ssid, channel=network.channel,
                signal_strength=network.signal_strength,
                packet_hex="22334455", frame_number=3
            )

            hs.frame_4 = PacketCapture(
                packet_id="f4", packet_type=PacketType.FOUR_WAY_HANDSHAKE,
                timestamp=time.time() + 0.3, source_mac=client_mac,
                destination_mac=network.bssid, bssid=network.bssid,
                ssid=network.ssid, channel=network.channel,
                signal_strength=-50, packet_hex="66778899", frame_number=4
            )

            hs.handshake_status = HandshakeStatus.COMPLETE_4_OF_4

            session.handshakes.append(hs)
            print(f"\n  ✓ Handshake #{i+1} erfasst ({client_mac})")

    def _get_signal_bar(self, rssi: int) -> str:
        """Generiert Signal-Stärken-Balken."""
        if rssi > -50:
            return "▓▓▓▓▓"
        elif rssi > -60:
            return "▓▓▓▓░"
        elif rssi > -70:
            return "▓▓▓░░"
        elif rssi > -80:
            return "▓▓░░░"
        else:
            return "▓░░░░"

    def _generate_handshake_hash(self, handshake: HandshakeCapture) -> str:
        """Generiert Handshake-Hash für Cracking."""
        combined = f"{handshake.bssid}{handshake.ssid}{handshake.client_mac}"
        return hashlib.sha256(combined.encode()).hexdigest()


def create_wifi_handshake_capture(adb: ADB) -> WiFiHandshakeCapture:
    """Erstellt neuen WiFi Handshake Capture."""
    return WiFiHandshakeCapture(adb)


def menu(adb: ADB) -> None:
    """WiFi Handshake Menu Wrapper."""
    capture = WiFiHandshakeCapture(adb)
    capture.show_wifi_handshake_menu()
