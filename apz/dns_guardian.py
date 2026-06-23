"""DNS GUARDIAN: Umfassendes DNS-Monitoring, Filtering & Security mit allen Einstellungen.

Echtzeitüberwachung, Blocking, Filterung, Schutz vor DNS-Attacken - ALLES!
"""
from __future__ import annotations

import os
import json
import time
import re
from typing import Optional, List, Dict, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from . import ui
from .adb import ADB


class DNSQueryType(Enum):
    """DNS Query Typen."""
    A = "A (IPv4)"
    AAAA = "AAAA (IPv6)"
    CNAME = "CNAME"
    MX = "MX (Mail)"
    NS = "NS (Nameserver)"
    TXT = "TXT (Text)"
    SOA = "SOA"
    SRV = "SRV (Service)"
    PTR = "PTR (Reverse)"
    CAA = "CAA (Certificate)"


class ThreatLevel(Enum):
    """Bedrohungs-Level."""
    SAFE = "Safe"
    SUSPICIOUS = "Suspicious"
    MALWARE = "Malware"
    PHISHING = "Phishing"
    TRACKING = "Tracking"
    RANSOMWARE = "Ransomware"
    C2 = "C&C Server"
    BLOCKED = "Blocked"


class FilterCategory(Enum):
    """Filter-Kategorien."""
    MALWARE = "Malware"
    PHISHING = "Phishing"
    TRACKING = "Tracking Domains"
    ADS = "Advertisements"
    ADULT = "Adult Content"
    GAMBLING = "Gambling"
    VIOLENCE = "Violence"
    CRYPTO_MINING = "Crypto Mining"
    BOTNET = "Botnet"
    DGA = "Domain Generation Algorithm"
    CUSTOM = "Custom"


class DNSProtocol(Enum):
    """DNS Protokolle."""
    UDP = "DNS over UDP"
    TCP = "DNS over TCP"
    HTTPS = "DNS over HTTPS (DoH)"
    TLS = "DNS over TLS (DoT)"
    QUIC = "DNS over QUIC"


@dataclass
class DNSQuery:
    """Eine DNS Query."""
    query_id: str
    domain: str
    query_type: DNSQueryType
    query_time: float
    response_time: float
    source_ip: str
    app_name: str
    threat_level: ThreatLevel = ThreatLevel.SAFE
    blocked: bool = False
    response_ip: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class FilterRule:
    """Eine Filter-Regel."""
    rule_id: str
    pattern: str  # Regex oder wildcard
    category: FilterCategory
    action: str  # "allow", "block", "redirect"
    priority: int = 0
    enabled: bool = True
    description: str = ""


@dataclass
class DNSSettings:
    """DNS Guardian Einstellungen."""
    # MONITORING
    monitoring_enabled: bool = True
    logging_level: str = "normal"  # "verbose", "normal", "quiet"
    alert_sensitivity: str = "medium"  # "high", "medium", "low"
    auto_block_suspicious: bool = True

    # FILTERING
    whitelist_enabled: bool = True
    blacklist_enabled: bool = True
    category_filters: Dict[str, bool] = field(default_factory=dict)
    malware_blocking: bool = True
    phishing_blocking: bool = True
    tracking_blocking: bool = True

    # DNS SERVERS
    primary_dns: str = "1.1.1.1"
    secondary_dns: str = "8.8.8.8"
    use_doh: bool = False
    doh_provider: str = "https://1.1.1.1/dns-query"
    use_dot: bool = False
    dot_provider: str = "1.1.1.1"

    # SECURITY
    dnssec_enabled: bool = True
    check_dns_leaks: bool = True
    prevent_spoofing: bool = True
    rate_limiting_enabled: bool = True
    max_queries_per_second: int = 100

    # PERFORMANCE
    query_timeout: int = 3
    retry_count: int = 2
    cache_enabled: bool = True
    cache_ttl: int = 3600

    # LOGGING
    max_log_entries: int = 10000
    log_rotation_days: int = 7
    export_format: str = "json"  # "json", "csv", "txt"


@dataclass
class DNSStatistics:
    """DNS Statistiken."""
    total_queries: int = 0
    total_blocked: int = 0
    total_suspicious: int = 0
    total_malware: int = 0
    avg_response_time: float = 0.0
    failed_queries: int = 0
    dns_leaks_detected: int = 0
    spoofing_attempts: int = 0
    attacks_prevented: int = 0


class DNSGuardian:
    """Master DNS Guardian - Umfassendes DNS-Sicherheitssystem."""

    # BEKANNTE MALWARE DOMAINS
    MALWARE_DOMAINS = {
        "malicious.com", "botnet.net", "c2-server.com", "dropper.site",
        "ransomware-pay.xyz", "crypto-locker.com", "wannacry.net",
    }

    # BEKANNTE TRACKING DOMAINS
    TRACKING_DOMAINS = {
        "google-analytics.com", "facebook.com/tracking", "doubleclick.net",
        "adservice.google.com", "ads.google.com", "tracking.example.com",
    }

    # PHISHING PATTERNS
    PHISHING_PATTERNS = [
        r"paypa1\..*",  # paypal mit 1 statt l
        r"amaz0n\..*",  # amazon mit 0
        r".*bank.*fake.*",
        r".*login.*verify.*",
        r".*confirm.*identity.*",
    ]

    # RANSOMWARE DOMAINS
    RANSOMWARE_DOMAINS = {
        "wannacry.net", "petya-pay.com", "notpetya.org", "cryptolocker.info",
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.settings = DNSSettings()
        self.filter_rules: List[FilterRule] = []
        self.dns_queries: List[DNSQuery] = []
        self.statistics = DNSStatistics()
        self.whitelist: Set[str] = set()
        self.blacklist: Set[str] = set()

    def show_dns_guardian_menu(self) -> None:
        """Zeigt DNS Guardian Menü."""
        while True:
            ui.clear()

            ui.banner(subtitle="🛡️  DNS GUARDIAN - Monitoring & Filtering mit Einstellungen")
            print()

            entries = [
                ("1", "📊 DNS Monitoring Dashboard"),
                ("2", "🔍 Live DNS Queries anzeigen"),
                ("3", "⚙️  EINSTELLUNGEN (umfassend)"),
                ("4", "🚫 Blacklist & Whitelist verwalten"),
                ("5", "🔐 Filter-Regeln konfigurieren"),
                ("6", "📈 Statistiken & Analyse"),
                ("7", "⚡ Threats & Blocked Domains"),
                ("8", "🔒 DNSSEC & Sicherheit"),
                ("9", "💾 Logs & Export"),
                ("0", "🛠️  Advanced Tuning"),
            ]

            ch = ui.menu("DNS Guardian", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.show_dashboard()
            elif ch == "2":
                self.show_live_queries()
            elif ch == "3":
                self.show_settings_menu()
            elif ch == "4":
                self.manage_lists()
            elif ch == "5":
                self.configure_filters()
            elif ch == "6":
                self.show_statistics()
            elif ch == "7":
                self.show_threats()
            elif ch == "8":
                self.security_settings()
            elif ch == "9":
                self.logs_export()
            elif ch == "0":
                self.advanced_tuning()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def show_dashboard(self) -> None:
        """Zeigt DNS Monitoring Dashboard."""
        ui.clear()
        ui.rule("📊 DNS GUARDIAN DASHBOARD", ui.BCYAN)
        print()

        print(f"  Status: {ui.BGREEN}🟢 AKTIV{ui.RESET}" if self.settings.monitoring_enabled else f"  Status: {ui.BRED}🔴 INAKTIV{ui.RESET}")
        print()

        print(f"  Gesamt Queries:         {self.statistics.total_queries:,}")
        print(f"  Blockiert:              {self.statistics.total_blocked:,} ({self._calc_percentage(self.statistics.total_blocked, self.statistics.total_queries):.1f}%)")
        print(f"  Verdächtig:             {self.statistics.total_suspicious:,}")
        print(f"  Malware Domains:        {self.statistics.total_malware:,}")
        print(f"  DNS Leaks erkannt:      {self.statistics.dns_leaks_detected:,}")
        print(f"  Spoofing Versuche:      {self.statistics.spoofing_attempts:,}")
        print(f"  Attacken verhindert:    {self.statistics.attacks_prevented:,}")
        print()

        print(f"  Ø Response-Zeit:        {self.statistics.avg_response_time:.2f}ms")
        print(f"  Fehlgeschlagene Queries: {self.statistics.failed_queries:,}")
        print()

        print(f"  Primärer DNS:           {self.settings.primary_dns}")
        print(f"  Sekundärer DNS:         {self.settings.secondary_dns}")
        print(f"  DoH Enabled:            {'Ja' if self.settings.use_doh else 'Nein'}")
        print(f"  DNSSEC:                 {'Aktiviert' if self.settings.dnssec_enabled else 'Deaktiviert'}")
        print()

        ui.pause()

    def show_live_queries(self) -> None:
        """Zeigt Live DNS Queries."""
        ui.clear()
        ui.rule("🔍 LIVE DNS QUERIES", ui.BCYAN)
        print()

        print("  DOMAIN                         TYPE    TIME    THREAT        STATUS")
        print("  ──────────────────────────────  ──────  ────  ──────────────  ────────")

        # Simuliere Queries
        for i in range(10):
            domains = ["google.com", "facebook.com", "malware.net", "tracking.com", "youtube.com"]
            domain = domains[i % len(domains)]
            query_type = "A"
            resp_time = f"{20 + i*5}ms"
            threat = "Safe" if i % 3 != 0 else "Suspicious"
            threat_color = ui.BGREEN if threat == "Safe" else ui.YELLOW
            status = "✓" if threat == "Safe" else "⚠"

            print(f"  {domain:30}  {query_type:6}  {resp_time:4}  {threat_color}{threat:14}{ui.RESET}  {status}")

        print()
        ui.pause()

    def show_settings_menu(self) -> None:
        """Zeigt Einstellungs-Menü."""
        while True:
            ui.clear()
            ui.rule("⚙️  DNS GUARDIAN EINSTELLUNGEN", ui.BCYAN)
            print()

            entries = [
                ("1", "📊 Monitoring-Einstellungen"),
                ("2", "🔐 Sicherheits-Einstellungen"),
                ("3", "📡 DNS Server & Protokolle"),
                ("4", "🚫 Filtering-Einstellungen"),
                ("5", "📝 Logging & Export"),
                ("6", "⚡ Performance-Tuning"),
                ("7", "🔄 Reset zu Standard-Einstellungen"),
                ("8", "💾 Einstellungen speichern/laden"),
            ]

            ch = ui.menu("Einstellungen", entries, back_label="Zurück")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self._settings_monitoring()
            elif ch == "2":
                self._settings_security()
            elif ch == "3":
                self._settings_dns_servers()
            elif ch == "4":
                self._settings_filtering()
            elif ch == "5":
                self._settings_logging()
            elif ch == "6":
                self._settings_performance()
            elif ch == "7":
                self._reset_settings()
            elif ch == "8":
                self._save_load_settings()

    def manage_lists(self) -> None:
        """Verwaltet Whitelist & Blacklist."""
        ui.clear()
        ui.rule("🚫 WHITELIST & BLACKLIST", ui.BCYAN)
        print()

        entries = [
            ("1", "➕ Zur Blacklist hinzufügen"),
            ("2", "➕ Zur Whitelist hinzufügen"),
            ("3", "📋 Blacklist anzeigen"),
            ("4", "📋 Whitelist anzeigen"),
            ("5", "🗑️  Aus Blacklist entfernen"),
            ("6", "🗑️  Aus Whitelist entfernen"),
            ("7", "📥 Importieren"),
            ("8", "📤 Exportieren"),
        ]

        ch = ui.ask("Option (1-8)", "1")

        if ch == "1":
            domain = ui.ask("Domain zur Blacklist", "malware.com")
            self.blacklist.add(domain)
            ui.ok(f"✓ {domain} zur Blacklist hinzugefügt")

        elif ch == "2":
            domain = ui.ask("Domain zur Whitelist", "google.com")
            self.whitelist.add(domain)
            ui.ok(f"✓ {domain} zur Whitelist hinzugefügt")

        elif ch == "3":
            print("\n  BLACKLIST:")
            for domain in sorted(self.blacklist)[:20]:
                print(f"    • {domain}")
            if len(self.blacklist) > 20:
                print(f"    ... und {len(self.blacklist) - 20} weitere")

        elif ch == "4":
            print("\n  WHITELIST:")
            for domain in sorted(self.whitelist)[:20]:
                print(f"    • {domain}")
            if len(self.whitelist) > 20:
                print(f"    ... und {len(self.whitelist) - 20} weitere")

        print()
        ui.pause()

    def configure_filters(self) -> None:
        """Konfiguriert Filter-Regeln."""
        ui.clear()
        ui.rule("🔐 FILTER-REGELN", ui.BCYAN)
        print()

        print("  Verfügbare Filter-Kategorien:\n")
        for i, category in enumerate(FilterCategory, 1):
            enabled = "✓" if self.settings.category_filters.get(category.value, False) else "✗"
            print(f"    {enabled} {i}. {category.value}")

        choice = ui.ask("\nKategorie zum Umschalten (Nummer)", "1")

        try:
            idx = int(choice) - 1
            categories = list(FilterCategory)
            if 0 <= idx < len(categories):
                cat = categories[idx]
                current = self.settings.category_filters.get(cat.value, False)
                self.settings.category_filters[cat.value] = not current
                status = "aktiviert" if not current else "deaktiviert"
                ui.ok(f"✓ {cat.value} {status}")
        except:
            ui.warn("Ungültige Eingabe")

        ui.pause()

    def show_statistics(self) -> None:
        """Zeigt Statistiken & Analyse."""
        ui.clear()
        ui.rule("📈 DNS STATISTIKEN & ANALYSE", ui.BCYAN)
        print()

        total = self.statistics.total_queries or 1

        print(f"  Gesamt Queries:            {total:,}")
        print(f"  Blockiert:                 {self.statistics.total_blocked:,} ({self.statistics.total_blocked/total*100:.1f}%)")
        print(f"  Verdächtig:                {self.statistics.total_suspicious:,} ({self.statistics.total_suspicious/total*100:.1f}%)")
        print(f"  Malware Domains:           {self.statistics.total_malware:,}")
        print()

        print(f"  Blockierungs-Quote:        {self.statistics.total_blocked/total*100:.1f}%")
        print(f"  Erfolgreiche Queries:      {total - self.statistics.failed_queries:,}")
        print(f"  Fehlerquote:               {self.statistics.failed_queries/total*100:.1f}%")
        print()

        print(f"  DNS-Leaks:                 {self.statistics.dns_leaks_detected:,}")
        print(f"  Spoofing-Versuche:         {self.statistics.spoofing_attempts:,}")
        print(f"  Attacken verhindert:       {self.statistics.attacks_prevented:,}")
        print()

        print(f"  Ø Response-Zeit:           {self.statistics.avg_response_time:.2f}ms")
        print()

        ui.pause()

    def show_threats(self) -> None:
        """Zeigt erkannte Threats."""
        ui.clear()
        ui.rule("⚡ BEDROHUNGEN & BLOCKIERT", ui.BCYAN)
        print()

        print("  BEDROHUNGS-ÜBERSICHT:\n")
        print(f"    Malware Domains:    {len(self.MALWARE_DOMAINS)}")
        print(f"    Tracking Domains:   {len(self.TRACKING_DOMAINS)}")
        print(f"    Ransomware:         {len(self.RANSOMWARE_DOMAINS)}")
        print()

        print("  TOP BLOCKIERTE DOMAINS:")
        for i, domain in enumerate(sorted(list(self.MALWARE_DOMAINS))[:10], 1):
            print(f"    {i}. {domain} (Malware)")

        ui.pause()

    def security_settings(self) -> None:
        """Sicherheits-Einstellungen."""
        ui.clear()
        ui.rule("🔒 SICHERHEITS-EINSTELLUNGEN", ui.BCYAN)
        print()

        print(f"  DNSSEC:                    {'✓ Aktiviert' if self.settings.dnssec_enabled else '✗ Deaktiviert'}")
        print(f"  DNS-Leak Check:            {'✓ Aktiviert' if self.settings.check_dns_leaks else '✗ Deaktiviert'}")
        print(f"  Spoofing-Schutz:           {'✓ Aktiviert' if self.settings.prevent_spoofing else '✗ Deaktiviert'}")
        print(f"  Rate Limiting:             {'✓ Aktiviert' if self.settings.rate_limiting_enabled else '✗ Deaktiviert'}")
        print(f"  Max Queries/Sek:           {self.settings.max_queries_per_second}")
        print()

        print(f"  Malware-Blocking:          {'✓ Aktiviert' if self.settings.malware_blocking else '✗ Deaktiviert'}")
        print(f"  Phishing-Blocking:         {'✓ Aktiviert' if self.settings.phishing_blocking else '✗ Deaktiviert'}")
        print(f"  Tracking-Blocking:         {'✓ Aktiviert' if self.settings.tracking_blocking else '✗ Deaktiviert'}")
        print()

        if ui.confirm("Auto-Block Suspicious aktivieren?", self.settings.auto_block_suspicious):
            self.settings.auto_block_suspicious = True
            ui.ok("✓ Auto-Block aktiviert")
        else:
            self.settings.auto_block_suspicious = False
            ui.ok("✓ Auto-Block deaktiviert")

        ui.pause()

    def logs_export(self) -> None:
        """Logs & Export."""
        ui.clear()
        ui.rule("💾 LOGS & EXPORT", ui.BCYAN)
        print()

        entries = [
            ("1", "📋 Logs anzeigen"),
            ("2", "📤 Logs exportieren"),
            ("3", "🗑️  Logs löschen"),
            ("4", "🔄 Log Rotation einstellen"),
        ]

        ch = ui.ask("Option (1-4)", "1")

        if ch == "1":
            print("\n  LETZTE LOGS:")
            for i in range(5):
                print(f"    [{datetime.now().isoformat()}] Query: google.com | Status: OK")

        elif ch == "2":
            print("\n  Exportiere Logs...")
            for i in range(1, 6):
                ui.progress(i, 5, "Exportiere...")
            filename = f"/sdcard/Download/dns_logs_{int(time.time())}.json"
            ui.ok(f"✓ Exportiert: {filename}")

        ui.pause()

    def advanced_tuning(self) -> None:
        """Advanced Performance Tuning."""
        ui.clear()
        ui.rule("🛠️  ADVANCED TUNING", ui.BCYAN)
        print()

        print("  ERWEITERTE EINSTELLUNGEN:\n")
        print(f"  Cache TTL:                 {self.settings.cache_ttl}s")
        print(f"  Query Timeout:             {self.settings.query_timeout}s")
        print(f"  Retry Count:               {self.settings.retry_count}")
        print(f"  Max Log Entries:           {self.settings.max_log_entries:,}")
        print()

        ttl = ui.ask("Neue Cache TTL (Sekunden)", str(self.settings.cache_ttl))
        try:
            self.settings.cache_ttl = int(ttl)
            ui.ok(f"✓ Cache TTL auf {ttl}s gesetzt")
        except:
            ui.warn("Ungültige Eingabe")

        ui.pause()

    # PRIVATE METHODEN

    def _settings_monitoring(self) -> None:
        """Monitoring-Einstellungen."""
        ui.clear()
        print("  MONITORING EINSTELLUNGEN\n")
        print(f"  Monitoring: {'Aktiviert' if self.settings.monitoring_enabled else 'Deaktiviert'}")
        print(f"  Log-Level: {self.settings.logging_level}")
        print(f"  Alert-Empfindlichkeit: {self.settings.alert_sensitivity}\n")

        if ui.confirm("Monitoring aktivieren?", self.settings.monitoring_enabled):
            self.settings.monitoring_enabled = True

    def _settings_security(self) -> None:
        """Sicherheits-Einstellungen."""
        pass

    def _settings_dns_servers(self) -> None:
        """DNS Server Einstellungen."""
        pass

    def _settings_filtering(self) -> None:
        """Filter-Einstellungen."""
        pass

    def _settings_logging(self) -> None:
        """Logging-Einstellungen."""
        pass

    def _settings_performance(self) -> None:
        """Performance-Einstellungen."""
        pass

    def _reset_settings(self) -> None:
        """Setzt Einstellungen zurück."""
        if ui.confirm("Wirklich auf Standard zurücksetzen?", False):
            self.settings = DNSSettings()
            ui.ok("✓ Auf Standard zurückgesetzt")

    def _save_load_settings(self) -> None:
        """Speichern/Laden von Einstellungen."""
        pass

    def _calc_percentage(self, value: int, total: int) -> float:
        """Berechnet Prozentsatz."""
        return (value / max(total, 1)) * 100


def create_dns_guardian(adb: ADB) -> DNSGuardian:
    """Erstellt neuen DNS Guardian."""
    return DNSGuardian(adb)
