"""KATEGORIEN-ANZEIGE: Alle 45 Kategorien detailliert anzeigen!"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from . import ui


@dataclass
class Category:
    """Eine Kategorie."""
    name: str
    description: str
    feature_count: int
    priority: str


class CategoryDisplay:
    """Zeigt alle 45 Kategorien."""

    CATEGORIES: List[Category] = [
        Category("Audio Analysis", "Tonanalyse & Audio-Processing", 20, "HIGH"),
        Category("Video Analysis", "Videoanalyse & Bildverarbeitung", 15, "HIGH"),
        Category("Network Security", "Netzwerk-Sicherheit & WiFi", 18, "HIGH"),
        Category("Malware Detection", "Malware-Erkennung & APK-Analyse", 22, "CRITICAL"),
        Category("Forensic Recovery", "Forensische Datenrettung", 25, "CRITICAL"),
        Category("Encryption", "Verschlüsselung & Decryption", 18, "HIGH"),
        Category("System Analysis", "System-Analyse & Deep Scanning", 30, "CRITICAL"),
        Category("App Monitoring", "App-Überwachung & Runtime", 20, "HIGH"),
        Category("Data Extraction", "Daten-Extraktion & Backup", 24, "CRITICAL"),
        Category("File System", "Dateisystem-Analyse & Explorer", 18, "HIGH"),
        Category("Database Analysis", "Datenbank-Analyse & Clone", 16, "MEDIUM"),
        Category("Rootkit Detection", "Rootkit & Kernel-Level Threats", 15, "CRITICAL"),
        Category("Device Rooting", "Device-Rooting & Jailbreak", 20, "HIGH"),
        Category("Brute Force", "Brute-Force & Password Attacks", 50, "HIGH"),
        Category("WiFi Security", "WiFi-Sicherheit & Handshake", 22, "HIGH"),
        Category("DNS Security", "DNS-Überwachung & Filtering", 18, "MEDIUM"),
        Category("IP Tracking", "IP & Phone-Tracking", 20, "MEDIUM"),
        Category("Geolocation", "Geolocation & Mapping", 15, "MEDIUM"),
        Category("Adult Content", "Adult-Content Detection", 26, "MEDIUM"),
        Category("Anomaly Detection", "Anomalie-Erkennung & Alerts", 45, "HIGH"),
        Category("AI/ML Features", "Künstliche Intelligenz & ML", 35, "HIGH"),
        Category("Automation", "Automatisierung & Scripting", 25, "MEDIUM"),
        Category("Report Generation", "Report-Generierung & Export", 18, "MEDIUM"),
        Category("Case Management", "Fall-Management & Database", 20, "MEDIUM"),
        Category("Lab Setup", "Labor-Setup & venv Management", 16, "LOW"),
        Category("3D Visualization", "3D-Visualisierung & Rendering", 25, "MEDIUM"),
        Category("Keyword Detection", "Keyword-Basierte Erkennung", 148, "HIGH"),
        Category("Audio Patterns", "Audio-Pattern Recognition", 120, "HIGH"),
        Category("Signal Processing", "Signal-Verarbeitung & Analysis", 30, "MEDIUM"),
        Category("Trilateration", "WiFi-Trilateration & Positioning", 12, "HIGH"),
        Category("Kalman Filtering", "Kalman-Filter & Smoothing", 8, "MEDIUM"),
        Category("Movement Tracking", "Bewegungs-Tracking & Analysis", 15, "MEDIUM"),
        Category("Wall Detection", "Wand-Erkennung & Material", 10, "MEDIUM"),
        Category("Signal Fusion", "Signal-Fusion & Optimization", 12, "HIGH"),
        Category("Fingerprinting", "ML-Fingerprinting & Matching", 20, "MEDIUM"),
        Category("APK Decryption", "APK-Analyse & Decryption", 18, "CRITICAL"),
        Category("Permission Analysis", "Berechtigungs-Analyse", 15, "HIGH"),
        Category("Code Analysis", "Code-Analyse & Decompilation", 25, "MEDIUM"),
        Category("Network Traffic", "Netzwerk-Traffic & Packet Capture", 20, "HIGH"),
        Category("Security Audit", "Sicherheits-Audit & Verification", 30, "HIGH"),
        Category("Threat Intelligence", "Threat Intelligence & Indicators", 35, "HIGH"),
        Category("Device Identification", "Geräte-ID & Fingerprinting", 18, "MEDIUM"),
        Category("Cross Correlation", "Kreuz-Korrelation & Analysis", 40, "HIGH"),
        Category("Predictive Analytics", "Vorhersage-Analytik & Trends", 25, "MEDIUM"),
        Category("Custom Firmware", "Custom-Firmware & Modding", 22, "MEDIUM"),
    ]

    @classmethod
    def show_all_categories(cls) -> None:
        """Zeige alle Kategorien."""
        ui.clear()
        ui.banner(subtitle="📋 ALLE 45 KATEGORIEN - DETAILLIERT")
        print()

        print(f"  {ui.BOLD}KATEGORIEN-ÜBERSICHT:{ui.RESET}\n")

        critical = [c for c in cls.CATEGORIES if c.priority == "CRITICAL"]
        high = [c for c in cls.CATEGORIES if c.priority == "HIGH"]
        medium = [c for c in cls.CATEGORIES if c.priority == "MEDIUM"]
        low = [c for c in cls.CATEGORIES if c.priority == "LOW"]

        # CRITICAL
        print(f"  {ui.BRED}🔴 CRITICAL ({len(critical)}):{ui.RESET}")
        for cat in critical:
            print(f"    • {cat.name:35} - {cat.feature_count:2d} Features")
            print(f"      {cat.description}")
        print()

        # HIGH
        print(f"  {ui.BYELLOW}🟠 HIGH ({len(high)}):{ui.RESET}")
        for cat in high:
            print(f"    • {cat.name:35} - {cat.feature_count:2d} Features")
        print()

        # MEDIUM
        print(f"  {ui.BGREEN}🟡 MEDIUM ({len(medium)}):{ui.RESET}")
        for cat in medium:
            print(f"    • {cat.name:35} - {cat.feature_count:2d} Features")
        print()

        # LOW
        print(f"  🟢 LOW ({len(low)}):")
        for cat in low:
            print(f"    • {cat.name:35} - {cat.feature_count:2d} Features")
        print()

        total_features = sum(c.feature_count for c in cls.CATEGORIES)
        print(f"  {ui.BOLD}TOTAL FEATURES: {total_features}{ui.RESET}")
        print()

        ui.pause()


def create_category_display() -> CategoryDisplay:
    """Factory: Erstellt CategoryDisplay."""
    return CategoryDisplay()
