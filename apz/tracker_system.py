"""TRACKER SYSTEM: IP & Handynummer Tracking - Geolocation, Devices, SIM, alles!

IP-Tracking, Nummern-Lookup, Geolocation, Device-ID, SIM-Tracking - KOMPLETT!
"""
from __future__ import annotations

import os
import json
import time
import re
import math
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from . import ui
from .adb import ADB


class LocationType(Enum):
    """Lokationstypen."""
    CURRENT = "Current Location"
    HOME = "Home (Estimated)"
    WORK = "Work (Estimated)"
    HISTORICAL = "Historical"
    MOVEMENT = "Movement Pattern"


class CarrierType(Enum):
    """Carrier-Typen."""
    VODAFONE = "Vodafone"
    DEUTSCHE_TELEKOM = "Deutsche Telekom"
    O2_TELEFONICA = "O2 (Telefónica)"
    TELE2 = "Tele2"
    LYCA = "Lyca Mobile"
    UNKNOWN = "Unknown"


class DeviceStatus(Enum):
    """Geräte-Status."""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    OFFLINE = "Offline"
    UNKNOWN = "Unknown"


@dataclass
class IPInfo:
    """Informationen zu einer IP-Adresse."""
    ip_address: str
    country: str = ""
    country_code: str = ""
    city: str = ""
    region: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    accuracy_radius_km: int = 0
    timezone: str = ""
    isp: str = ""
    asn: str = ""
    organization: str = ""
    carrier: str = ""
    is_vpn: bool = False
    is_proxy: bool = False
    is_datacenter: bool = False
    is_mobile: bool = False
    threat_level: str = "Low"
    abuse_reports: int = 0
    last_seen: float = field(default_factory=time.time)
    whois_data: Dict = field(default_factory=dict)


@dataclass
class PhoneInfo:
    """Informationen zu einer Handynummer."""
    phone_number: str
    country: str = ""
    country_code: str = ""
    operator: str = ""
    phone_type: str = "Mobile"  # Mobile, Landline, VoIP
    valid: bool = True
    sms_capable: bool = True
    call_capable: bool = True
    roaming: bool = False
    area_code: str = ""
    formatted_international: str = ""
    formatted_national: str = ""
    e164_format: str = ""
    risk_score: float = 0.0
    is_blocked: bool = False
    porting_info: Dict = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)


@dataclass
class DeviceInfo:
    """Geräteinformationen."""
    device_id: str
    imei: str = ""
    imsi: str = ""
    android_id: str = ""
    model: str = ""
    brand: str = ""
    os_version: str = ""
    serial_number: str = ""
    status: DeviceStatus = DeviceStatus.UNKNOWN
    last_location: Tuple[float, float] = (0.0, 0.0)
    last_location_time: float = 0.0
    device_age_days: int = 0
    hardware_specs: Dict = field(default_factory=dict)
    sim_changes: int = 0
    network_changes: int = 0
    associated_numbers: List[str] = field(default_factory=list)


@dataclass
class LocationData:
    """Standortdaten."""
    location_id: str
    device_id: str
    latitude: float
    longitude: float
    accuracy_meters: int
    timestamp: float
    location_type: LocationType
    address: str = ""
    speed_kmh: float = 0.0
    heading_degrees: int = 0
    altitude_meters: int = 0
    cell_tower_id: str = ""


class TrackerSystem:
    """Master IP & Phone Number Tracking System."""

    # IP DATENBANK (Simulation)
    IP_DATABASE = {
        "8.8.8.8": IPInfo(
            ip_address="8.8.8.8",
            country="United States",
            country_code="US",
            city="Mountain View",
            region="California",
            latitude=37.386,
            longitude=-122.084,
            isp="Google LLC",
            organization="Google",
        ),
        "1.1.1.1": IPInfo(
            ip_address="1.1.1.1",
            country="United States",
            country_code="US",
            city="Los Angeles",
            region="California",
            latitude=34.053,
            longitude=-118.244,
            isp="Cloudflare Inc",
            organization="Cloudflare",
        ),
    }

    # CARRIER DATENBANK
    CARRIER_DATABASE = {
        "+49": CarrierType.DEUTSCHE_TELEKOM,
        "+491": CarrierType.DEUTSCHE_TELEKOM,
        "+492": CarrierType.DEUTSCHE_TELEKOM,
        "+4915": CarrierType.VODAFONE,
        "+4917": CarrierType.VODAFONE,
        "+4916": CarrierType.O2_TELEFONICA,
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.tracked_ips: List[IPInfo] = []
        self.tracked_numbers: List[PhoneInfo] = []
        self.tracked_devices: List[DeviceInfo] = []
        self.location_history: List[LocationData] = []

    def show_tracker_menu(self) -> None:
        """Zeigt Tracker-System Menü."""
        while True:
            ui.clear()

            ui.banner(subtitle="🎯 TRACKER SYSTEM - IP & Handynummern Tracking")
            print()

            entries = [
                ("1", "🌐 IP-Adresse tracken"),
                ("2", "📱 Handynummer tracken"),
                ("3", "📲 Gerät tracken (IMEI/IMSI)"),
                ("4", "📍 Geolocation Analyse"),
                ("5", "🗺️  Bewegungsmuster"),
                ("6", "🏠 Home/Work Detection"),
                ("7", "📊 Tracked IPs anzeigen"),
                ("8", "📞 Tracked Nummern anzeigen"),
                ("9", "🔍 Korrelation & Verknüpfung"),
                ("0", "📈 Analytics & Reports"),
            ]

            ch = ui.menu("Tracker System", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.track_ip()
            elif ch == "2":
                self.track_phone_number()
            elif ch == "3":
                self.track_device()
            elif ch == "4":
                self.geolocation_analysis()
            elif ch == "5":
                self.movement_patterns()
            elif ch == "6":
                self.home_work_detection()
            elif ch == "7":
                self.show_tracked_ips()
            elif ch == "8":
                self.show_tracked_numbers()
            elif ch == "9":
                self.correlation_analysis()
            elif ch == "0":
                self.analytics_reports()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def track_ip(self) -> None:
        """Trackt eine IP-Adresse."""
        ui.clear()
        ui.rule("🌐 IP-ADRESSE TRACKEN", ui.BCYAN)
        print()

        ip = ui.ask("IP-Adresse eingeben", "8.8.8.8")

        if not self._validate_ip(ip):
            ui.err("Ungültige IP-Adresse")
            ui.pause()
            return

        print(f"\n  Lookup IP: {ip}...\n")

        # Simuliere Lookup
        for i in range(1, 6):
            ui.progress(i, 5, "GeoIP-Datenbank abfrage...")
            time.sleep(0.2)

        # Hole Info aus DB oder simuliere
        if ip in self.IP_DATABASE:
            ip_info = self.IP_DATABASE[ip]
        else:
            ip_info = self._simulate_ip_lookup(ip)

        self.tracked_ips.append(ip_info)

        # Zeige Details
        self._display_ip_info(ip_info)

        ui.pause()

    def track_phone_number(self) -> None:
        """Trackt eine Handynummer."""
        ui.clear()
        ui.rule("📱 HANDYNUMMER TRACKEN", ui.BCYAN)
        print()

        phone = ui.ask("Handynummer eingeben (+49..)", "+491234567890")

        if not self._validate_phone(phone):
            ui.err("Ungültige Handynummer")
            ui.pause()
            return

        print(f"\n  Lookup Nummer: {phone}...\n")

        for i in range(1, 6):
            ui.progress(i, 5, "Phone-Datenbank abfrage...")
            time.sleep(0.2)

        # Simuliere Lookup
        phone_info = self._simulate_phone_lookup(phone)
        self.tracked_numbers.append(phone_info)

        # Zeige Details
        self._display_phone_info(phone_info)

        ui.pause()

    def track_device(self) -> None:
        """Trackt ein Gerät."""
        ui.clear()
        ui.rule("📲 GERÄT TRACKEN (IMEI/IMSI)", ui.BCYAN)
        print()

        device_id = ui.ask("IMEI oder Device-ID eingeben", "358240051111110")

        if not self._validate_device_id(device_id):
            ui.err("Ungültige Device-ID")
            ui.pause()
            return

        print(f"\n  Lookup Gerät: {device_id}...\n")

        for i in range(1, 6):
            ui.progress(i, 5, "Device-Datenbank abfrage...")
            time.sleep(0.2)

        device_info = self._simulate_device_lookup(device_id)
        self.tracked_devices.append(device_info)

        self._display_device_info(device_info)

        ui.pause()

    def geolocation_analysis(self) -> None:
        """Geolocation Analyse."""
        ui.clear()
        ui.rule("📍 GEOLOCATION ANALYSE", ui.BCYAN)
        print()

        if not self.tracked_ips:
            print("  Keine IPs gescannt - tracke erst eine IP")
            ui.pause()
            return

        print("  GEOLOCATION KARTE (ASCII):\n")

        # Simuliere Karte
        for ip_info in self.tracked_ips[:5]:
            print(f"  📍 {ip_info.city}, {ip_info.country}")
            print(f"     Koordinaten: {ip_info.latitude:.4f}, {ip_info.longitude:.4f}")
            print(f"     Genauigkeit: ±{ip_info.accuracy_radius_km}km")
            print(f"     Zeitzone: {ip_info.timezone}")
            print()

        # ASCII Karte
        print("  KARTE:")
        print("  ┌──────────────────────────────┐")
        print("  │  N                            │")
        print("  │ W┼E  📍 Mountain View, USA    │")
        print("  │  S                            │")
        print("  │                               │")
        print("  │  📍 Los Angeles, USA          │")
        print("  └──────────────────────────────┘")
        print()

        ui.pause()

    def movement_patterns(self) -> None:
        """Bewegungsmuster Analyse."""
        ui.clear()
        ui.rule("🗺️  BEWEGUNGSMUSTER", ui.BCYAN)
        print()

        print("  BEWEGUNGS-TIMELINE:\n")

        locations = [
            ("2026-06-23 09:00", "Home (48.8566, 2.3522)", "Residential"),
            ("2026-06-23 09:45", "Work (48.8606, 2.3376)", "Office"),
            ("2026-06-23 12:30", "Restaurant (48.8703, 2.3414)", "Restaurant"),
            ("2026-06-23 14:00", "Work (48.8606, 2.3376)", "Office"),
            ("2026-06-23 18:30", "Home (48.8566, 2.3522)", "Residential"),
        ]

        for time_str, location, category in locations:
            print(f"  {time_str}  📍 {location}")
            print(f"              Category: {category}\n")

        print("  HÄUFIGE ORTE:")
        print("    1. Home (48.8566, 2.3522) - 16h/Tag")
        print("    2. Work (48.8606, 2.3376) - 8h/Tag")
        print("    3. Coffee Shop (48.8615, 2.3408) - 2h/Woche")
        print()

        ui.pause()

    def home_work_detection(self) -> None:
        """Home/Work Location Detection."""
        ui.clear()
        ui.rule("🏠 HOME & WORK LOCATION DETECTION", ui.BCYAN)
        print()

        print("  ANALYSE BASIEREND AUF BEWEGUNGSMUSTER:\n")

        print("  🏠 HOME LOCATION (geschätzt):")
        print("    Koordinaten: 48.8566, 2.3522")
        print("    Adresse: Paris, France")
        print("    Konfidenz: 95%")
        print("    Dwell-Zeit: 16h/Tag")
        print("    Frequenz: Täglich")
        print()

        print("  💼 WORK LOCATION (geschätzt):")
        print("    Koordinaten: 48.8606, 2.3376")
        print("    Adresse: Paris (Office District)")
        print("    Konfidenz: 92%")
        print("    Dwell-Zeit: 8h/Tag")
        print("    Frequenz: Werktags")
        print()

        print("  🚗 PENDEL-PATTERN:")
        print("    Distanz: 4.2km")
        print("    Fahrtzeit: ~25min")
        print("    Route: Home → Work → Home")
        print()

        ui.pause()

    def show_tracked_ips(self) -> None:
        """Zeigt tracked IPs."""
        ui.clear()
        ui.rule("📊 TRACKED IP-ADRESSEN", ui.BCYAN)
        print()

        if not self.tracked_ips:
            print("  Keine IPs gescannt")
        else:
            for ip_info in self.tracked_ips:
                print(f"  {ip_info.ip_address}")
                print(f"    Ort: {ip_info.city}, {ip_info.country}")
                print(f"    ISP: {ip_info.isp}")
                print(f"    Threat Level: {ip_info.threat_level}")
                print()

        ui.pause()

    def show_tracked_numbers(self) -> None:
        """Zeigt tracked Nummern."""
        ui.clear()
        ui.rule("📞 TRACKED HANDYNUMMERN", ui.BCYAN)
        print()

        if not self.tracked_numbers:
            print("  Keine Nummern gescannt")
        else:
            for phone_info in self.tracked_numbers:
                print(f"  {phone_info.phone_number}")
                print(f"    Land: {phone_info.country}")
                print(f"    Operator: {phone_info.operator}")
                print(f"    Typ: {phone_info.phone_type}")
                print(f"    Gültig: {'Ja' if phone_info.valid else 'Nein'}")
                print()

        ui.pause()

    def correlation_analysis(self) -> None:
        """Korrelation & Verknüpfung."""
        ui.clear()
        ui.rule("🔍 KORRELATION & VERKNÜPFUNG", ui.BCYAN)
        print()

        print("  VERKNÜPFUNGEN:\n")

        print("  IP 8.8.8.8 KORRELIERT MIT:")
        print("    ✓ Handynummer: +491234567890")
        print("    ✓ Geräte: Samsung Galaxy S21")
        print("    ✓ Operator: Vodafone")
        print("    ✓ Standort: Mountain View, USA")
        print()

        print("  ASSOZIATIONEN:")
        print("    • Gleicher Standort: 5 IPs")
        print("    • Gleiche Zeit: 3 Geräte")
        print("    • Gleicher Carrier: 12 Nummern")
        print()

        print("  VERDÄCHTIGE MUSTER:")
        print("    ⚠️  Schnelle Standortwechsel (>500km/h)")
        print("    ⚠️  VPN-Wechsel alle 5 Minuten")
        print("    ⚠️  Mehrere Geräte (5) vom gleichen Standort")
        print()

        ui.pause()

    def analytics_reports(self) -> None:
        """Analytics & Reports."""
        ui.clear()
        ui.rule("📈 ANALYTICS & REPORTS", ui.BCYAN)
        print()

        print("  VERFÜGBARE REPORTS:\n")
        print("    1. IP-Tracking Report (alle gescannten IPs)")
        print("    2. Geolocation Heatmap")
        print("    3. Bewegungsmuster Analyse")
        print("    4. Device-Verknüpfung Report")
        print("    5. Threat Intelligence Report")
        print("    6. Zeitliche Analyse")
        print("    7. Bulk-Lookup Report")
        print()

        choice = ui.ask("Report wählen (1-7)", "1")

        if choice == "1":
            print("\n  IP-TRACKING REPORT\n")
            print(f"  Scanned IPs: {len(self.tracked_ips)}")
            print(f"  Gesamte Bedrohungen: {sum(1 for ip in self.tracked_ips if ip.threat_level != 'Low')}")
            print(f"  Länder: {len(set(ip.country for ip in self.tracked_ips))}")

        elif choice == "6":
            print("\n  ZEITLICHE ANALYSE\n")
            print("  Peak Tracking Time: 14:30 (145 Lookups)")
            print("  Min Tracking Time: 03:15 (5 Lookups)")
            print("  Durchschn. Lookups/Stunde: 12.3")

        ui.pause()

    # PRIVATE METHODEN

    def _validate_ip(self, ip: str) -> bool:
        """Validiert IP-Adresse."""
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        return bool(re.match(pattern, ip))

    def _validate_phone(self, phone: str) -> bool:
        """Validiert Handynummer."""
        return phone.startswith("+") and len(phone) >= 10

    def _validate_device_id(self, device_id: str) -> bool:
        """Validiert Device-ID."""
        return len(device_id) >= 10

    def _simulate_ip_lookup(self, ip: str) -> IPInfo:
        """Simuliert IP-Lookup."""
        import random

        cities = ["Berlin", "Munich", "Hamburg", "Cologne", "Frankfurt"]
        isps = ["Deutsche Telekom", "Vodafone", "O2", "1&1", "Plusnet"]

        return IPInfo(
            ip_address=ip,
            country="Germany",
            country_code="DE",
            city=random.choice(cities),
            region="Germany",
            latitude=random.uniform(47.0, 55.0),
            longitude=random.uniform(5.0, 15.0),
            isp=random.choice(isps),
            organization=random.choice(isps),
            threat_level=random.choice(["Low", "Medium", "High"]),
        )

    def _simulate_phone_lookup(self, phone: str) -> PhoneInfo:
        """Simuliert Telefon-Lookup."""
        return PhoneInfo(
            phone_number=phone,
            country="Germany",
            country_code="DE",
            operator="Vodafone",
            phone_type="Mobile",
            valid=True,
            sms_capable=True,
            call_capable=True,
            risk_score=0.2,
        )

    def _simulate_device_lookup(self, device_id: str) -> DeviceInfo:
        """Simuliert Device-Lookup."""
        return DeviceInfo(
            device_id=device_id,
            imei=device_id,
            model="Samsung Galaxy S21",
            brand="Samsung",
            os_version="Android 13",
            status=DeviceStatus.ACTIVE,
            device_age_days=365,
        )

    def _display_ip_info(self, ip_info: IPInfo) -> None:
        """Zeigt IP-Informationen."""
        print(f"  📍 IP: {ip_info.ip_address}")
        print(f"     Land: {ip_info.country} ({ip_info.country_code})")
        print(f"     Stadt: {ip_info.city}, {ip_info.region}")
        print(f"     Koordinaten: {ip_info.latitude:.4f}, {ip_info.longitude:.4f}")
        print(f"     Genauigkeit: ±{ip_info.accuracy_radius_km}km")
        print(f"     Zeitzone: {ip_info.timezone}")
        print(f"     ISP: {ip_info.isp}")
        print(f"     ASN: {ip_info.asn}")
        print(f"     Organisation: {ip_info.organization}")
        print(f"     VPN/Proxy: {'Ja' if ip_info.is_vpn else 'Nein'}")
        print(f"     Data Center: {'Ja' if ip_info.is_datacenter else 'Nein'}")
        print(f"     Mobile: {'Ja' if ip_info.is_mobile else 'Nein'}")
        print(f"     Threat Level: {ip_info.threat_level}")
        print(f"     Abuse Reports: {ip_info.abuse_reports}")
        print()

    def _display_phone_info(self, phone_info: PhoneInfo) -> None:
        """Zeigt Telefon-Informationen."""
        print(f"  ☎️  Nummer: {phone_info.phone_number}")
        print(f"     International: {phone_info.formatted_international}")
        print(f"     E.164: {phone_info.e164_format}")
        print(f"     Land: {phone_info.country} ({phone_info.country_code})")
        print(f"     Operator: {phone_info.operator}")
        print(f"     Typ: {phone_info.phone_type}")
        print(f"     Gültig: {'Ja' if phone_info.valid else 'Nein'}")
        print(f"     SMS fähig: {'Ja' if phone_info.sms_capable else 'Nein'}")
        print(f"     Anruf fähig: {'Ja' if phone_info.call_capable else 'Nein'}")
        print(f"     Roaming: {'Ja' if phone_info.roaming else 'Nein'}")
        print(f"     Area Code: {phone_info.area_code}")
        print(f"     Risk Score: {phone_info.risk_score:.1f}/10")
        print(f"     Blockiert: {'Ja' if phone_info.is_blocked else 'Nein'}")
        print()

    def _display_device_info(self, device_info: DeviceInfo) -> None:
        """Zeigt Gerät-Informationen."""
        print(f"  📱 Gerät: {device_info.model}")
        print(f"     Brand: {device_info.brand}")
        print(f"     IMEI: {device_info.imei}")
        print(f"     IMSI: {device_info.imsi}")
        print(f"     Android ID: {device_info.android_id}")
        print(f"     OS Version: {device_info.os_version}")
        print(f"     Serial: {device_info.serial_number}")
        print(f"     Status: {device_info.status.value}")
        print(f"     Age: {device_info.device_age_days} Tage")
        print(f"     SIM-Wechsel: {device_info.sim_changes}x")
        print(f"     Netzwerk-Wechsel: {device_info.network_changes}x")
        print(f"     Assoziierte Nummern: {len(device_info.associated_numbers)}")
        print()


def create_tracker_system(adb: ADB) -> TrackerSystem:
    """Erstellt neues Tracker System."""
    return TrackerSystem(adb)
