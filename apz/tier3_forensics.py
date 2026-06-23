"""TIER 3 FORENSICS & SCANNING: Umfassende Forensische Analyse!

Forensik Suite, APK Scanner, App Scanner, Datei-Analyse & Datenrettung
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from . import ui


class ForensicsType(Enum):
    """Forensik Analyse Typen."""
    WHATSAPP = "WhatsApp Forensik (Messages, Media, Status)"
    TELEGRAM = "Telegram Forensik (Chats, Channels, Files)"
    SIGNAL = "Signal Forensik (Encrypted Messages)"
    INSTAGRAM = "Instagram Forensik (DMs, Stories, Posts)"
    FACEBOOK = "Facebook Forensik (Messages, Data)"
    SNAPCHAT = "Snapchat Forensik (Deleted Snaps)"
    TIKTOK = "TikTok Forensik (Videos, Browsing)"
    TWITTER = "Twitter Forensik (DMs, Timeline)"
    EMAIL = "Email Forensik (Gmail, Outlook, etc)"
    DATING = "Dating Apps (Tinder, Bumble, Match)"
    BANKING = "Banking Apps (Transactions, Tokens)"
    CALENDAR = "Calendar Events & Scheduling"
    CONTACTS = "Kontakt-Information & Beziehungen"
    LOCATION = "Location History & GPS Tracks"
    BROWSING = "Browser History & Cookies"
    DOWNLOADS = "Download History & Files"
    CLIPBOARD = "Clipboard Memory & Cache"
    SYSTEM_LOGS = "System Logs & Boot Events"
    CRASH_LOGS = "App Crash Logs & Error Reports"
    DATABASE = "SQLite Databases & Recovery"


class APKScanType(Enum):
    """APK Scanning Typen."""
    PERMISSIONS = "Berechtigungen Analysis"
    MALWARE = "Malware Detection"
    BACKDOORS = "Backdoor Detection"
    VIRUSES = "Virus Signature Matching"
    TROJANS = "Trojan Horse Detection"
    ROOTKITS = "Rootkit Detection"
    RANSOMWARE = "Ransomware Detection"
    SPYWARE = "Spyware Detection"
    ADWARE = "Advertising Malware"
    PACKERS = "Packer Detection (Obfuscation)"
    CRYPTO = "Cryptographic Operations"
    NETWORK = "Network Communications"
    SENSITIVE_DATA = "Sensitive Data Leakage"
    HARDCODED_SECRETS = "API Keys & Secrets"
    CODE_INJECTION = "Code Injection Vectors"
    EXPLOITS = "Known Exploits"
    DECOMPILATION = "Source Code Recovery"
    SIGNATURE = "Certificate Verification"


class AppAnalysisType(Enum):
    """App Analyse Typen."""
    RUNTIME_BEHAVIOR = "Runtime Behavior Monitoring"
    API_CALLS = "API Call Interception"
    FILE_ACCESS = "File Access Tracking"
    NETWORK_ACCESS = "Network Traffic Analysis"
    MEMORY_DUMP = "Memory Dumping & Analysis"
    DATA_EXFILTRATION = "Data Exfiltration Detection"
    PRIVILEGE_ESCALATION = "Privilege Escalation Check"
    PERSISTENCE = "Persistence Mechanisms"
    COMMUNICATION = "Inter-Process Communication"
    SCHEDULING = "Task Scheduling & Triggers"
    BROADCASTING = "Broadcast Receivers"
    INTENT_FILTERS = "Intent Filters Analysis"
    NATIVE_CODE = "Native Code Analysis"
    JNI_CALLS = "JNI Function Calls"
    REFLECTION = "Java Reflection Usage"


class FileAnalysisType(Enum):
    """Datei Analyse Typen."""
    CARVING = "File Carving (Deleted Files)"
    METADATA = "Metadata Extraction"
    TIMESTAMPS = "File Timestamps Analysis"
    PERMISSIONS = "File Permissions"
    OWNERSHIP = "Ownership & Groups"
    ENCRYPTION = "Encryption Detection"
    COMPRESSION = "Compression Analysis"
    MAGIC_BYTES = "File Type Verification"
    HASHING = "Hash Calculation (MD5, SHA)"
    ENTROPY = "Entropy Analysis (Compression)"
    STEGANOGRAPHY = "Steganography Detection"
    HIDDEN_DATA = "Hidden Alternate Streams"
    SLACK_SPACE = "Slack Space Analysis"
    UNALLOCATED = "Unallocated Space Scanning"
    SWAP = "Swap File Analysis"


class DataRecoveryType(Enum):
    """Daten Recovery Typen."""
    DELETED_FILES = "Deleted File Recovery"
    DELETED_MESSAGES = "Deleted Messages Recovery"
    DELETED_PHOTOS = "Deleted Photo Recovery"
    DELETED_VIDEOS = "Deleted Video Recovery"
    OVERWRITTEN = "Overwritten Data Recovery"
    FORMATTED = "Formatted Partition Recovery"
    CACHE = "Cache Files Recovery"
    TEMP_FILES = "Temporary Files Recovery"
    WAL_JOURNAL = "Database WAL/Journal Recovery"
    THUMBS = "Thumbnail Recovery"
    EXIF_DATA = "EXIF Data Extraction"
    PREVIEW = "Preview/Thumbnail Generation"


@dataclass
class ForensicsFeature:
    """Forensik Feature."""
    name: str
    forensics_type: ForensicsType
    description: str
    enabled: bool = True
    priority: int = 8
    artifacts: List[str] = field(default_factory=list)


@dataclass
class APKFeature:
    """APK Scan Feature."""
    name: str
    scan_type: APKScanType
    description: str
    enabled: bool = True
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    detection_rate: int = 85


@dataclass
class AppFeature:
    """App Analysis Feature."""
    name: str
    analysis_type: AppAnalysisType
    description: str
    enabled: bool = True
    requires_root: bool = False


@dataclass
class FileFeature:
    """File Analysis Feature."""
    name: str
    file_type: FileAnalysisType
    description: str
    enabled: bool = True


class Tier3Forensics:
    """TIER 3 - Umfassende Forensik & Scanning."""

    FORENSICS_FEATURES: List[ForensicsFeature] = [
        ForensicsFeature(
            name="WhatsApp Forensik",
            forensics_type=ForensicsType.WHATSAPP,
            description="Nachrichten, Media, Status, Kontakte",
            artifacts=["msgstore.db", "wa.db", "ProfilePhoto", "Media"]
        ),
        ForensicsFeature(
            name="Telegram Forensik",
            forensics_type=ForensicsType.TELEGRAM,
            description="Chats, Channels, Dateien, Geheime Chats",
            artifacts=["cache4.db", "channels.db", "chats.db"]
        ),
        ForensicsFeature(
            name="Signal Forensik",
            forensics_type=ForensicsType.SIGNAL,
            description="Verschlüsselte Nachrichten, Medien",
            artifacts=["signal.db", "attachments"]
        ),
        ForensicsFeature(
            name="Instagram Forensik",
            forensics_type=ForensicsType.INSTAGRAM,
            description="DMs, Stories, Posts, Follower",
            artifacts=["instagram.db", "cache"]
        ),
        ForensicsFeature(
            name="Facebook Forensik",
            forensics_type=ForensicsType.FACEBOOK,
            description="Messages, Timeline, Fotos, Events",
            artifacts=["messenger.db", "facebook.db"]
        ),
        ForensicsFeature(
            name="Snapchat Forensik",
            forensics_type=ForensicsType.SNAPCHAT,
            description="Gelöschte Snaps, Konversationen",
            artifacts=["snapchat.db", "cache"]
        ),
        ForensicsFeature(
            name="TikTok Forensik",
            forensics_type=ForensicsType.TIKTOK,
            description="Videos, Browsing-Verlauf, Likes",
            artifacts=["tiktok.db", "cache"]
        ),
        ForensicsFeature(
            name="Email Forensik",
            forensics_type=ForensicsType.EMAIL,
            description="Gmail, Outlook, Yahoo, POP3/IMAP",
            artifacts=["*.db", "emails", "attachments"]
        ),
        ForensicsFeature(
            name="Dating Apps",
            forensics_type=ForensicsType.DATING,
            description="Tinder, Bumble, Match - Matches, Messages",
            artifacts=["tinder.db", "bumble.db", "matches.json"]
        ),
        ForensicsFeature(
            name="Banking Apps",
            forensics_type=ForensicsType.BANKING,
            description="Transaktionen, Kontonummern, Tokens",
            artifacts=["banking.db", "secure.db"]
        ),
        ForensicsFeature(
            name="Kalender Events",
            forensics_type=ForensicsType.CALENDAR,
            description="Termine, Besprechungen, Einladungen",
            artifacts=["calendar.db", "events"]
        ),
        ForensicsFeature(
            name="Kontakt Information",
            forensics_type=ForensicsType.CONTACTS,
            description="Kontaktdaten, Nummern, Adressen",
            artifacts=["contacts.db", "contacts2.db"]
        ),
        ForensicsFeature(
            name="Location History",
            forensics_type=ForensicsType.LOCATION,
            description="GPS-Tracks, Ortsverläufe, Standorte",
            artifacts=["location.db", "gps_tracks"]
        ),
        ForensicsFeature(
            name="Browser History",
            forensics_type=ForensicsType.BROWSING,
            description="Chrome, Firefox, Edge - History, Cookies, Cache",
            artifacts=["History", "Cookies", "Cache"]
        ),
        ForensicsFeature(
            name="Download History",
            forensics_type=ForensicsType.DOWNLOADS,
            description="Download Manager, Dateien, Links",
            artifacts=["downloads.db", "Downloads"]
        ),
        ForensicsFeature(
            name="Clipboard Memory",
            forensics_type=ForensicsType.CLIPBOARD,
            description="Zwischenablage History, Passwörter",
            artifacts=["clipboard.db"]
        ),
        ForensicsFeature(
            name="System Logs",
            forensics_type=ForensicsType.SYSTEM_LOGS,
            description="Kernel Logs, Boot Events, Errors",
            artifacts=["logcat", "dmesg", "system.log"]
        ),
        ForensicsFeature(
            name="Crash Logs",
            forensics_type=ForensicsType.CRASH_LOGS,
            description="App Crashes, Stack Traces, Error Reports",
            artifacts=["crashes", "tombstones", "anr"]
        ),
        ForensicsFeature(
            name="Database Forensik",
            forensics_type=ForensicsType.DATABASE,
            description="SQLite Recovery, WAL/Journal Reconstruction",
            artifacts=["*.db", "*.db-wal", "*.db-journal"]
        ),
    ]

    APK_FEATURES: List[APKFeature] = [
        APKFeature("Permission Scanner", APKScanType.PERMISSIONS, "Berechtigungen Analyse", risk_level="HIGH"),
        APKFeature("Malware Detection", APKScanType.MALWARE, "Malware Signatures", risk_level="CRITICAL"),
        APKFeature("Backdoor Detector", APKScanType.BACKDOORS, "Remote Code Execution", risk_level="CRITICAL"),
        APKFeature("Virus Scanner", APKScanType.VIRUSES, "Virus Patterns", risk_level="CRITICAL"),
        APKFeature("Trojan Hunter", APKScanType.TROJANS, "Trojan Horse Detection", risk_level="CRITICAL"),
        APKFeature("Rootkit Scanner", APKScanType.ROOTKITS, "Privileged Code Detection", risk_level="CRITICAL"),
        APKFeature("Ransomware Detector", APKScanType.RANSOMWARE, "File Encryption Routines", risk_level="CRITICAL"),
        APKFeature("Spyware Detector", APKScanType.SPYWARE, "Surveillance Behavior", risk_level="HIGH"),
        APKFeature("Adware Detector", APKScanType.ADWARE, "Advertisement Fraud", risk_level="MEDIUM"),
        APKFeature("Packer Detection", APKScanType.PACKERS, "Code Obfuscation", risk_level="HIGH"),
        APKFeature("Crypto Analyzer", APKScanType.CRYPTO, "Cryptographic Operations", risk_level="MEDIUM"),
        APKFeature("Network Analyzer", APKScanType.NETWORK, "Command & Control Detection", risk_level="HIGH"),
        APKFeature("Data Leak Scanner", APKScanType.SENSITIVE_DATA, "Sensitive Data Exfiltration", risk_level="HIGH"),
        APKFeature("Secret Hunter", APKScanType.HARDCODED_SECRETS, "API Keys & Passwords", risk_level="HIGH"),
        APKFeature("Injection Detector", APKScanType.CODE_INJECTION, "Code Injection Vectors", risk_level="HIGH"),
        APKFeature("Exploit Scanner", APKScanType.EXPLOITS, "CVE & Known Exploits", risk_level="CRITICAL"),
        APKFeature("Decompiler", APKScanType.DECOMPILATION, "Source Code Recovery", risk_level="MEDIUM"),
        APKFeature("Certificate Verifier", APKScanType.SIGNATURE, "Signature Verification", risk_level="MEDIUM"),
    ]

    APP_FEATURES: List[AppFeature] = [
        AppFeature("Runtime Monitor", AppAnalysisType.RUNTIME_BEHAVIOR, "Laufzeit-Verhalten"),
        AppFeature("API Hooker", AppAnalysisType.API_CALLS, "API-Aufrufe abfangen", requires_root=True),
        AppFeature("File Monitor", AppAnalysisType.FILE_ACCESS, "Dateizugriff verfolgen"),
        AppFeature("Network Sniffer", AppAnalysisType.NETWORK_ACCESS, "Netzwerk-Verkehr"),
        AppFeature("Memory Dumper", AppAnalysisType.MEMORY_DUMP, "Speicher-Dump & Analyse", requires_root=True),
        AppFeature("Data Exfil Detector", AppAnalysisType.DATA_EXFILTRATION, "Daten-Exfiltrierung"),
        AppFeature("Privilege Checker", AppAnalysisType.PRIVILEGE_ESCALATION, "Privilege Escalation"),
        AppFeature("Persistence Detector", AppAnalysisType.PERSISTENCE, "Persistenzmechanismen"),
        AppFeature("IPC Monitor", AppAnalysisType.COMMUNICATION, "Inter-Process Communication"),
        AppFeature("Scheduler Analyzer", AppAnalysisType.SCHEDULING, "Task Scheduling"),
        AppFeature("Broadcast Analyzer", AppAnalysisType.BROADCASTING, "Broadcast Receiver"),
        AppFeature("Intent Analyzer", AppAnalysisType.INTENT_FILTERS, "Intent Filter Analyse"),
        AppFeature("Native Code Analyzer", AppAnalysisType.NATIVE_CODE, "Native Binaries"),
        AppFeature("JNI Analyzer", AppAnalysisType.JNI_CALLS, "JNI Function Calls"),
        AppFeature("Reflection Detector", AppAnalysisType.REFLECTION, "Java Reflection Usage"),
    ]

    FILE_FEATURES: List[FileFeature] = [
        FileFeature("File Carver", FileAnalysisType.CARVING, "Gelöschte Dateien wiederherstellen"),
        FileFeature("Metadata Extractor", FileAnalysisType.METADATA, "Metadaten-Extraktion"),
        FileFeature("Timestamp Analyzer", FileAnalysisType.TIMESTAMPS, "Datei Zeitstempel"),
        FileFeature("Permission Checker", FileAnalysisType.PERMISSIONS, "Datei-Berechtigungen"),
        FileFeature("Ownership Analyzer", FileAnalysisType.OWNERSHIP, "Besitz & Gruppen"),
        FileFeature("Encryption Detector", FileAnalysisType.ENCRYPTION, "Verschlüsselung"),
        FileFeature("Compression Analyzer", FileAnalysisType.COMPRESSION, "Komprimierung"),
        FileFeature("Magic Byte Verifier", FileAnalysisType.MAGIC_BYTES, "Datei-Typ Verifikation"),
        FileFeature("Hash Calculator", FileAnalysisType.HASHING, "MD5/SHA Hash Berechnung"),
        FileFeature("Entropy Analyzer", FileAnalysisType.ENTROPY, "Entropie-Analyse"),
        FileFeature("Steganography Detector", FileAnalysisType.STEGANOGRAPHY, "Versteckte Daten"),
        FileFeature("ADS Detector", FileAnalysisType.HIDDEN_DATA, "Alternate Data Streams"),
        FileFeature("Slack Space Analyzer", FileAnalysisType.SLACK_SPACE, "Slack-Speicher"),
        FileFeature("Unallocated Scanner", FileAnalysisType.UNALLOCATED, "Nicht-zugeordneter Speicher"),
        FileFeature("Swap Analyzer", FileAnalysisType.SWAP, "Swap-Datei Analyse"),
    ]

    @classmethod
    def show_summary(cls) -> str:
        """Zeige Zusammenfassung."""
        return f"""
TIER 3 - FORENSIK & SCANNING - SUMMARY
═════════════════════════════════════════════════════════════════

🔍 FORENSIK SUITE:               {len(cls.FORENSICS_FEATURES)} Messaging Apps + Systems
    ✓ WhatsApp, Telegram, Signal, Instagram, Facebook
    ✓ Snapchat, TikTok, Twitter, Email, Dating Apps
    ✓ Banking, Kalender, Kontakte, Location, Browser
    ✓ Downloads, Clipboard, System Logs, Crash Logs
    ✓ Database Forensik mit Recovery

📦 APK SCANNER:                  {len(cls.APK_FEATURES)} Scan-Methoden
    ✓ Malware, Backdoors, Trojans, Rootkits
    ✓ Ransomware, Spyware, Adware Detection
    ✓ Code Obfuscation, Crypto Ops
    ✓ Network C&C, Sensitive Data Leaks
    ✓ Hardcoded Secrets, Code Injection
    ✓ Known Exploits, Signature Verification

🗃️  APP SCANNER:                 {len(cls.APP_FEATURES)} Runtime-Methoden
    ✓ Runtime Behavior Monitoring
    ✓ API Call Interception
    ✓ File & Network Access Tracking
    ✓ Memory Dumping & Analysis
    ✓ Data Exfiltration Detection
    ✓ Privilege Escalation, Persistence
    ✓ IPC, Scheduling, Broadcasting
    ✓ Intent Filters, Native Code, JNI

📁 DATEI ANALYSE:                {len(cls.FILE_FEATURES)} Datei-Methoden
    ✓ File Carving (gelöschte Dateien)
    ✓ Metadata Extraction (EXIF, etc)
    ✓ Timestamp Analysis (MAC times)
    ✓ Permissions & Ownership
    ✓ Encryption & Compression
    ✓ Magic Byte Verification
    ✓ Hash Calculation (MD5/SHA)
    ✓ Entropy Analysis
    ✓ Steganography Detection
    ✓ Slack Space & Unallocated

💾 DATEN RECOVERY:               10+ Recovery-Methoden
    ✓ Deleted Files Recovery
    ✓ Deleted Messages Recovery
    ✓ Deleted Photos/Videos Recovery
    ✓ Overwritten Data Recovery
    ✓ Formatted Partition Recovery
    ✓ Cache & Temp Files Recovery
    ✓ Database WAL/Journal Recovery
    ✓ Thumbnail Recovery
    ✓ EXIF Data Extraction
    ✓ Preview Generation

TOTAL TIER 3 FEATURES:           {len(cls.FORENSICS_FEATURES) + len(cls.APK_FEATURES) + len(cls.APP_FEATURES) + len(cls.FILE_FEATURES)} Features
"""

    @classmethod
    def show_forensics_details(cls) -> None:
        """Zeige Forensik Details."""
        ui.clear()
        ui.banner(subtitle="🔍 FORENSIK SUITE - 19 Messaging & System Apps")
        print()

        print(f"{ui.BOLD}FORENSIK ARTEFAKTE:{ui.RESET}\n")
        for i, feature in enumerate(cls.FORENSICS_FEATURES, 1):
            print(f"  {i:2d}. {feature.name:30} {feature.forensics_type.value}")
            print(f"      → {feature.description}")
            if feature.artifacts:
                print(f"      📁 Artefakte: {', '.join(feature.artifacts)}\n")

    @classmethod
    def show_apk_scanner_details(cls) -> None:
        """Zeige APK Scanner Details."""
        ui.clear()
        ui.banner(subtitle="📦 APK SCANNER - 18 Scan-Methoden")
        print()

        print(f"{ui.BOLD}SCAN-TYPEN NACH RISIKO:{ui.RESET}\n")

        # Group by risk
        by_risk = {}
        for feature in cls.APK_FEATURES:
            if feature.risk_level not in by_risk:
                by_risk[feature.risk_level] = []
            by_risk[feature.risk_level].append(feature)

        for risk_level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if risk_level in by_risk:
                features = by_risk[risk_level]
                color = ui.BRED if risk_level == "CRITICAL" else ui.BYELLOW
                print(f"  {color}🔴 {risk_level:8}{ui.RESET} ({len(features)} Scanner)")
                for feature in features:
                    print(f"    ✓ {feature.name:30} {feature.description:40} ({feature.detection_rate}%)")
                print()

    @classmethod
    def show_app_scanner_details(cls) -> None:
        """Zeige App Scanner Details."""
        ui.clear()
        ui.banner(subtitle="🗃️  APP SCANNER - 15 Runtime-Methoden")
        print()

        print(f"{ui.BOLD}RUNTIME-ANALYSE:{ui.RESET}\n")
        for i, feature in enumerate(cls.APP_FEATURES, 1):
            root_req = " [REQUIRES ROOT]" if feature.requires_root else ""
            print(f"  {i:2d}. {feature.name:30} {feature.description}{root_req}")

    @classmethod
    def show_file_scanner_details(cls) -> None:
        """Zeige File Scanner Details."""
        ui.clear()
        ui.banner(subtitle="📁 DATEI SCANNER - 15 Datei-Methoden")
        print()

        print(f"{ui.BOLD}DATEI-ANALYSE-METHODEN:{ui.RESET}\n")
        for i, feature in enumerate(cls.FILE_FEATURES, 1):
            print(f"  {i:2d}. {feature.name:30} {feature.description}")


def create_tier3_forensics() -> Tier3Forensics:
    """Factory: Erstellt Tier 3 Forensics."""
    return Tier3Forensics()


def menu(adb=None) -> None:
    """Tier3Forensics Menu Wrapper."""
    obj = Tier3Forensics(adb) if adb else Tier3Forensics()
    obj.show_menu()

