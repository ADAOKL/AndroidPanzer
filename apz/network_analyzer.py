"""NETWORK ANALYZER: Umfassende Analyse aller Netzwerk-Interfaces.

SIM, WiFi, Cellular, Routing, DNS - Alles in einer Suite!
"""
from __future__ import annotations

import json
import time
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from . import ui
from .adb import ADB


class ConnectionType(Enum):
    """Verbindungstypen."""
    WIFI = "WiFi"
    CELLULAR_2G = "2G (EDGE/GPRS)"
    CELLULAR_3G = "3G (UMTS/HSPA)"
    CELLULAR_4G = "4G (LTE)"
    CELLULAR_5G = "5G NR"
    BLUETOOTH = "Bluetooth"
    UNKNOWN = "Unknown"


@dataclass
class SIMCardInfo:
    """SIM-Karten Informationen."""
    imsi: str = ""
    phone_number: str = ""
    operator_name: str = ""
    country_code: str = ""
    network_code: str = ""
    is_esim: bool = False
    sim_state: str = "READY"
    iccid: str = ""
    mnc: str = ""
    mcc: str = ""


@dataclass
class WiFiNetwork:
    """WiFi-Netzwerk Informationen."""
    ssid: str = ""
    bssid: str = ""
    frequency: int = 0
    signal_strength: int = 0  # dBm
    security: str = ""
    ip_address: str = ""
    gateway: str = ""
    dns1: str = ""
    dns2: str = ""
    connected: bool = False


@dataclass
class CellularInfo:
    """Mobilfunk-Verbindungsinformationen."""
    carrier_name: str = ""
    mcc: str = ""
    mnc: str = ""
    network_type: ConnectionType = ConnectionType.UNKNOWN
    signal_strength: int = 0  # dBm
    signal_bars: int = 0  # 0-4
    lac: str = ""  # Location Area Code
    cid: str = ""  # Cell ID
    is_roaming: bool = False


class NetworkAnalyzer:
    """Master Network Analyzer."""

    def __init__(self, adb: ADB):
        self.adb = adb
        self.sim_info = SIMCardInfo()
        self.current_wifi: Optional[WiFiNetwork] = None
        self.available_networks: List[WiFiNetwork] = []
        self.cellular_info = CellularInfo()
        self.network_history: List[Dict] = []

    def show_network_menu(self) -> None:
        """Zeigt Netzwerk-Analyzer Menü."""
        # PRÜFE GERÄT ZUERST
        if not self.adb or not hasattr(self.adb, 'shell'):
            ui.clear()
            ui.err("❌ FEHLER: Keine ADB-Verbindung!")
            print("\n  Bitte verbinde ein Android-Gerät per USB und versuche es erneut.")
            ui.pause()
            return

        try:
            while True:
                try:
                    ui.clear()
                    ui.banner(subtitle="🌐 NETWORK ANALYZER - SIM, WiFi, Cellular")
                    print()

                    entries = [
                        ("1", "📱 SIM-Karten Informationen"),
                        ("2", "📡 Cellular-Verbindung Details"),
                        ("3", "📶 WiFi-Netzwerke scannen"),
                        ("4", "🔗 Aktuelle WiFi-Verbindung"),
                        ("5", "🌍 Routing-Tabelle"),
                        ("6", "📍 DNS-Konfiguration"),
                        ("7", "⚡ Netzwerk-Speed Test"),
                        ("8", "📊 Netzwerk-Statistiken"),
                        ("9", "🔒 Netzwerk-Sicherheit"),
                        ("0", "📋 Netzwerk-Übersicht (All-in-One)"),
                    ]

                    ch = ui.menu("Netzwerk-Analyse Optionen", entries, back_label="Hauptmenü")
                    if ch in ("back", "quit"):
                        return

                    try:
                        if ch == "1":
                            self.analyze_sim()
                        elif ch == "2":
                            self.analyze_cellular()
                        elif ch == "3":
                            self.scan_wifi_networks()
                        elif ch == "4":
                            self.analyze_current_wifi()
                        elif ch == "5":
                            self.show_routing_table()
                        elif ch == "6":
                            self.analyze_dns()
                        elif ch == "7":
                            self.network_speed_test()
                        elif ch == "8":
                            self.show_network_stats()
                        elif ch == "9":
                            self.network_security_check()
                        elif ch == "0":
                            self.show_complete_overview()
                        else:
                            ui.warn("Ungültige Option")
                            time.sleep(0.5)
                    except Exception as e:
                        ui.err(f"❌ Fehler: {str(e)[:100]}")
                        ui.pause()
                except KeyboardInterrupt:
                    ui.warn("Unterbrochen")
                    return
                except Exception as e:
                    ui.err(f"❌ Menü-Fehler: {str(e)[:100]}")
                    ui.pause()
                    return
        except Exception as e:
            ui.err(f"❌ Kritischer Fehler: {str(e)[:100]}")
            ui.pause()
            return

    def analyze_sim(self) -> None:
        """Analysiert SIM-Kartendaten."""
        ui.clear()
        ui.rule("📱 SIM-KARTEN INFORMATIONEN", ui.BCYAN)
        print()

        try:
            # SIM-Status
            dumpsys = self.adb.shell("dumpsys iphonesubinfo")

            # Parse Daten
            lines = dumpsys.split("\n")
            for line in lines:
                if "IMSI" in line:
                    self.sim_info.imsi = line.split("=")[-1].strip() if "=" in line else ""
                if "Phone" in line:
                    self.sim_info.phone_number = line.split("=")[-1].strip() if "=" in line else ""
                if "ICC" in line:
                    self.sim_info.iccid = line.split("=")[-1].strip() if "=" in line else ""

            # Operator
            tel_manager = self.adb.shell("getprop gsm.nitz.time 2>/dev/null || echo ''")

            ui.kv("SIM Status", self.sim_info.sim_state)
            ui.kv("IMSI", self.sim_info.imsi or "N/A")
            ui.kv("Phone Number", self.sim_info.phone_number or "N/A")
            ui.kv("ICCID", self.sim_info.iccid or "N/A")

            # MCC/MNC (aus IMSI)
            if self.sim_info.imsi and len(self.sim_info.imsi) >= 6:
                mcc = self.sim_info.imsi[:3]
                mnc = self.sim_info.imsi[3:5]
                ui.kv("MCC (Land)", mcc)
                ui.kv("MNC (Netz)", mnc)

                # Land nachschlagen
                country = self._get_country_name(mcc)
                ui.kv("Land", country)

            ui.kv("eSIM", "Ja" if self.sim_info.is_esim else "Nein")

        except Exception as e:
            ui.err(f"SIM-Analyse Fehler: {e}")

        print()
        ui.pause()

    def analyze_cellular(self) -> None:
        """Analysiert Mobilfunk-Verbindung."""
        ui.clear()
        ui.rule("📡 CELLULAR-VERBINDUNG DETAILS", ui.BCYAN)
        print()

        try:
            # Telecom-Service Info
            tel_info = self.adb.shell("dumpsys telephony.registry")

            lines = tel_info.split("\n")
            carrier = "Unknown"
            network_type = "Unknown"
            signal = "-100 dBm"

            for line in lines:
                if "Carrier" in line:
                    carrier = line.split("=")[-1].strip() if "=" in line else "Unknown"
                if "NetworkType" in line:
                    network_type = line.split("=")[-1].strip() if "=" in line else "Unknown"
                if "SignalStrength" in line:
                    signal = line.split("=")[-1].strip() if "=" in line else "-100 dBm"

            ui.kv("Carrier/Operator", carrier)
            ui.kv("Netzwerk-Typ", network_type)
            ui.kv("Signal-Stärke", signal)

            # Roaming-Status
            roaming = self.adb.shell("getprop gsm.nitz.time")
            ui.kv("Roaming", "Ja" if "roaming" in roaming.lower() else "Nein")

            # Cell-Info
            cell_info = self.adb.shell("dumpsys telephony.registry | grep -i cell")
            if cell_info:
                ui.kv("Cell Information", cell_info[:50])

        except Exception as e:
            ui.err(f"Cellular-Analyse Fehler: {e}")

        print()
        ui.pause()

    def scan_wifi_networks(self) -> None:
        """Scannt verfügbare WiFi-Netzwerke."""
        ui.clear()
        ui.rule("📶 WiFi-NETZWERK SCAN", ui.BCYAN)
        print()

        try:
            print("  Scanne WiFi-Netzwerke...")

            # Starte Scan
            self.adb.shell("am startservice -n com.android.settings/.wifi.WifiScannerActivity")

            # Warte auf Ergebnisse
            time.sleep(2)

            # Lese Scan-Ergebnisse
            scan_results = self.adb.shell("dumpsys wifi")

            lines = scan_results.split("\n")
            networks = []

            for line in lines:
                if "BSSID" in line or "SSID" in line:
                    networks.append(line.strip())

            if networks:
                print("\n  Gefundene Netzwerke:")
                for i, network in enumerate(networks[:10], 1):
                    print(f"    {i}. {network[:60]}")
            else:
                print("  Keine Netzwerke gefunden")

            self.available_networks = networks

        except Exception as e:
            ui.err(f"WiFi-Scan Fehler: {e}")

        print()
        ui.pause()

    def analyze_current_wifi(self) -> None:
        """Analysiert aktuelle WiFi-Verbindung."""
        ui.clear()
        ui.rule("🔗 AKTUELLE WiFi-VERBINDUNG", ui.BCYAN)
        print()

        try:
            # WiFi-Info
            wifi_info = self.adb.shell("dumpsys wifi")

            lines = wifi_info.split("\n")
            for line in lines:
                if "SSID:" in line:
                    ssid = line.split(":")[-1].strip()
                    ui.kv("SSID", ssid)
                elif "BSSID:" in line:
                    bssid = line.split(":")[-1].strip()
                    ui.kv("BSSID (MAC)", bssid)
                elif "LinkSpeed:" in line:
                    speed = line.split(":")[-1].strip()
                    ui.kv("Link Speed", speed)
                elif "RSSI:" in line:
                    rssi = line.split(":")[-1].strip()
                    ui.kv("Signal (dBm)", rssi)

            # IP-Adresse
            ip_info = self.adb.shell("getprop dhcp.wlan0.ipaddress")
            if ip_info:
                ui.kv("IP-Adresse", ip_info)

            # Gateway
            gw = self.adb.shell("getprop dhcp.wlan0.gateway")
            if gw:
                ui.kv("Gateway", gw)

            # DNS
            dns1 = self.adb.shell("getprop dhcp.wlan0.dns1")
            dns2 = self.adb.shell("getprop dhcp.wlan0.dns2")
            if dns1:
                ui.kv("DNS 1", dns1)
            if dns2:
                ui.kv("DNS 2", dns2)

        except Exception as e:
            ui.err(f"WiFi-Analyse Fehler: {e}")

        print()
        ui.pause()

    def show_routing_table(self) -> None:
        """Zeigt Routing-Tabelle."""
        ui.clear()
        ui.rule("🌍 ROUTING-TABELLE", ui.BCYAN)
        print()

        try:
            routes = self.adb.shell("cat /proc/net/route")

            lines = routes.split("\n")
            print("  Routing-Einträge:")

            for line in lines[:15]:
                if line.strip():
                    print(f"  {line}")

        except Exception as e:
            ui.err(f"Routing-Fehler: {e}")

        print()
        ui.pause()

    def analyze_dns(self) -> None:
        """Analysiert DNS-Konfiguration."""
        ui.clear()
        ui.rule("📍 DNS-KONFIGURATION", ui.BCYAN)
        print()

        try:
            # System DNS
            dns1 = self.adb.shell("getprop net.dns1")
            dns2 = self.adb.shell("getprop net.dns2")
            dns3 = self.adb.shell("getprop net.dns3")
            dns4 = self.adb.shell("getprop net.dns4")

            ui.kv("DNS 1", dns1 or "N/A")
            ui.kv("DNS 2", dns2 or "N/A")
            ui.kv("DNS 3", dns3 or "N/A")
            ui.kv("DNS 4", dns4 or "N/A")

            # WiFi DNS
            wifi_dns1 = self.adb.shell("getprop dhcp.wlan0.dns1")
            wifi_dns2 = self.adb.shell("getprop dhcp.wlan0.dns2")

            ui.kv("WiFi DNS 1", wifi_dns1 or "N/A")
            ui.kv("WiFi DNS 2", wifi_dns2 or "N/A")

            # DNS-Resolution Test
            print("\n  DNS-Resolution Test:")
            result = self.adb.shell("nslookup google.com 8.8.8.8 2>&1 | head -5")
            if result:
                for line in result.split("\n")[:3]:
                    print(f"    {line}")

        except Exception as e:
            ui.err(f"DNS-Analyse Fehler: {e}")

        print()
        ui.pause()

    def network_speed_test(self) -> None:
        """Führt Netzwerk-Speed Test durch."""
        ui.clear()
        ui.rule("⚡ NETZWERK-SPEED TEST", ui.BCYAN)
        print()

        print("  Teste Download-Speed...")

        try:
            # Download-Test (1MB Datei)
            start = time.time()
            result = self.adb.shell(
                "curl -w '\\n%{speed_download}' -o /dev/null -s "
                "http://speedtest.ftp.otenet.gr/files/test1Mb.db 2>/dev/null"
            )
            elapsed = time.time() - start

            if result:
                lines = result.split("\n")
                if len(lines) > 1:
                    speed = float(lines[-1]) / 1024 / 1024  # Convert to MB/s
                    ui.kv("Download Speed", f"{speed:.2f} MB/s")
                    ui.kv("Latency", f"{elapsed*1000:.0f} ms")
            else:
                ui.warn("Keine Internet-Verbindung")

        except Exception as e:
            ui.err(f"Speed-Test Fehler: {e}")

        print()
        ui.pause()

    def show_network_stats(self) -> None:
        """Zeigt Netzwerk-Statistiken."""
        ui.clear()
        ui.rule("📊 NETZWERK-STATISTIKEN", ui.BCYAN)
        print()

        try:
            stats = self.adb.shell("cat /proc/net/dev")

            lines = stats.split("\n")
            print("  Interface-Statistiken (Top 5):")

            for line in lines[2:7]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) > 2:
                        interface = parts[0].rstrip(":")
                        rx_bytes = parts[1]
                        tx_bytes = parts[9]
                        print(f"    {interface}: RX={rx_bytes} TX={tx_bytes}")

        except Exception as e:
            ui.err(f"Statistik-Fehler: {e}")

        print()
        ui.pause()

    def network_security_check(self) -> None:
        """Prüft Netzwerk-Sicherheit."""
        ui.clear()
        ui.rule("🔒 NETZWERK-SICHERHEIT", ui.BCYAN)
        print()

        try:
            # Checklist
            checks = {
                "WiFi-Verschlüsselung": self._check_wifi_encryption(),
                "HTTPS-Verbindungen": self._check_https_usage(),
                "SSL-Pinning": self._check_ssl_pinning(),
                "VPN-Status": self._check_vpn_status(),
                "Firewall": self._check_firewall(),
                "DNS-Sicherheit": self._check_dns_security(),
            }

            for check_name, result in checks.items():
                status = "✓ Sicher" if result else "✗ Unsicher"
                color = ui.BGREEN if result else ui.BRED
                print(f"  {color}{status}{ui.RESET} {check_name}")

        except Exception as e:
            ui.err(f"Security-Check Fehler: {e}")

        print()
        ui.pause()

    def show_complete_overview(self) -> None:
        """Zeigt komplette Netzwerk-Übersicht."""
        ui.clear()
        ui.rule("📋 KOMPLETTE NETZWERK-ÜBERSICHT", ui.BCYAN)
        print()

        # SIM
        print("  📱 SIM-Karte:")
        print(f"    IMSI: {self.sim_info.imsi or 'N/A'}")
        print(f"    Status: {self.sim_info.sim_state}")

        # Cellular
        print("\n  📡 Mobilfunk:")
        print(f"    Netzwerk-Typ: {self.cellular_info.network_type.value}")
        print(f"    Signal: {self.cellular_info.signal_strength} dBm")
        print(f"    Roaming: {'Ja' if self.cellular_info.is_roaming else 'Nein'}")

        # WiFi
        print("\n  📶 WiFi:")
        print(f"    Verfügbare Netzwerke: {len(self.available_networks)}")

        # IP-Konfiguration
        print("\n  🔗 IP-Konfiguration:")
        ip = self.adb.shell("getprop dhcp.wlan0.ipaddress")
        gw = self.adb.shell("getprop dhcp.wlan0.gateway")
        print(f"    IP: {ip or 'N/A'}")
        print(f"    Gateway: {gw or 'N/A'}")

        # DNS
        print("\n  📍 DNS:")
        dns1 = self.adb.shell("getprop net.dns1")
        dns2 = self.adb.shell("getprop net.dns2")
        print(f"    DNS 1: {dns1 or 'N/A'}")
        print(f"    DNS 2: {dns2 or 'N/A'}")

        print()
        ui.pause()

    def _get_country_name(self, mcc: str) -> str:
        """Gibt Ländernamen für MCC zurück."""
        countries = {
            "310": "USA", "311": "USA", "312": "USA", "313": "USA",
            "310": "USA", "440": "Japan", "441": "Japan", "450": "Korea",
            "454": "Hong Kong", "455": "Macau", "460": "China",
            "466": "Taiwan", "605": "Australia", "631": "Australia",
        }
        return countries.get(mcc, "Unknown")

    def _check_wifi_encryption(self) -> bool:
        """Prüft WiFi-Verschlüsselung."""
        try:
            info = self.adb.shell("dumpsys wifi")
            return "WPA" in info or "WEP" in info
        except:
            return False

    def _check_https_usage(self) -> bool:
        """Prüft HTTPS-Nutzung."""
        try:
            traffic = self.adb.shell("dumpsys wifi")
            return "tls" in traffic.lower()
        except:
            return False

    def _check_ssl_pinning(self) -> bool:
        """Prüft SSL-Pinning."""
        try:
            result = self.adb.shell("grep -r 'pin' /data/system/")
            return bool(result)
        except:
            return False

    def _check_vpn_status(self) -> bool:
        """Prüft VPN-Status."""
        try:
            vpn_info = self.adb.shell("dumpsys connectivity | grep -i vpn")
            return "vpn" in vpn_info.lower()
        except:
            return False

    def _check_firewall(self) -> bool:
        """Prüft Firewall."""
        try:
            fw = self.adb.shell("iptables -L -n 2>/dev/null | wc -l")
            return int(fw) > 5
        except:
            return False

    def _check_dns_security(self) -> bool:
        """Prüft DNS-Sicherheit."""
        try:
            dns = self.adb.shell("getprop net.dns1")
            # DoH/DoT Provider
            secure_providers = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
            return any(provider in dns for provider in secure_providers)
        except:
            return False


def create_network_analyzer(adb: ADB) -> NetworkAnalyzer:
    """Erstellt neuen Network Analyzer."""
    return NetworkAnalyzer(adb)

def menu(adb=None) -> None:
    """NetworkAnalyzer Menu Wrapper."""
    obj = NetworkAnalyzer(adb) if adb else NetworkAnalyzer()
    obj.show_network_menu()
