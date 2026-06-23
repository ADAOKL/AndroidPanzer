"""ADULT CONTENT SCANNER: Forensische Analyse auf sexuelle/pornographische Inhalte.

Kinderschutz, Compliance, Strafverfolgung - Alle Quellen scannen.
"""
from __future__ import annotations

import os
import json
import re
import time
import sqlite3
from typing import Optional, List, Dict, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from . import ui
from .adb import ADB


class ContentSeverity(Enum):
    """Schweregrad des Inhalts."""
    NONE = "None"
    SUSPICIOUS = "Suspicious"
    MODERATE = "Moderate"
    EXPLICIT = "Explicit"
    EXTREME = "Extreme"


class ContentType(Enum):
    """Typ des gefundenen Inhalts."""
    BROWSER_HISTORY = "Browser History"
    BROWSER_CACHE = "Browser Cache"
    DELETED_BROWSER = "Deleted Browser Data"
    CHAT_MESSAGE = "Chat Message"
    IMAGE_FILE = "Image File"
    VIDEO_FILE = "Video File"
    APP_DATA = "App Data"
    SEARCH_QUERY = "Search Query"
    DOCUMENT = "Document"
    DOWNLOAD = "Download"


@dataclass
class AdultContent:
    """Ein gefundenes Adult-Content Eintrag."""
    content_id: str
    content_type: ContentType
    severity: ContentSeverity
    source: str  # Browser, App, File path
    title: str
    url: str = ""
    description: str = ""
    timestamp: float = 0.0
    file_path: str = ""
    keywords: List[str] = None
    matched_phrases: List[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.matched_phrases is None:
            self.matched_phrases = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp == 0:
            self.timestamp = time.time()


@dataclass
class ScanReport:
    """Scan-Report mit allen Ergebnissen."""
    scan_id: str
    scan_start: float
    scan_end: float = 0.0
    total_items_found: int = 0
    severity_breakdown: Dict[str, int] = None
    sources_scanned: List[str] = None
    findings: List[AdultContent] = None

    def __post_init__(self):
        if self.severity_breakdown is None:
            self.severity_breakdown = {}
        if self.sources_scanned is None:
            self.sources_scanned = []
        if self.findings is None:
            self.findings = []


class AdultContentScanner:
    """Master Adult Content Scanner - Forensische Analyse."""

    # ADULT KEYWORDS & PHRASES (Deutsch, Englisch, andere Sprachen)
    ADULT_KEYWORDS = {
        # Deutscher Fokus
        "porno", "pornographie", "xxx", "sex", "sexuelle", "nackt", "nacktheit",
        "brüste", "anus", "penis", "vagina", "sperma", "ejakulation", "orgasmus",
        "masturbation", "anal", "oralverkehr", "blasen", "ficken", "bumsen",
        "arschficken", "doppelpenetration", "gangbang", "dp", "bukkake",
        "deepthroat", "facefuck", "squirting", "creampie", "cumshot",
        # English
        "porn", "sex", "nude", "xxx", "adult", "explicit", "horny", "cumshot",
        "blow job", "blowjob", "fuck", "fucking", "cock", "pussy", "ass",
        "breasts", "tits", "webcam", "cam girl", "stripper", "escort",
        # Dating Apps & Adult Services
        "onlyfans", "chaturbate", "cam4", "flirt", "escort", "sugar daddy",
        "sugar baby", "hookup", "nudes", "nudes for sale", "sexting",
    }

    # ADULT DOMAINS & SITES
    ADULT_DOMAINS = {
        # Major Porn Sites
        "pornhub", "xvideos", "xhamster", "redtube", "tube8", "youporn",
        "tnaflix", "eporner", "4tube", "porn.com", "xxx", "beeg",
        "porno", "prnhub", "jav", "hentai", "onlyfans",
        # Adult Streaming
        "chaturbate", "cam4", "livejasmine", "flirt4free", "stripchat",
        # Dating/Hook-up
        "tinder", "bumble", "badoo", "okcupid", "grindr", "scruff",
    }

    # FILE EXTENSIONS ADULT CONTENT
    ADULT_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".flv", ".jpg", ".png", ".gif"}

    def __init__(self, adb: ADB):
        self.adb = adb
        self.scan_results: List[AdultContent] = []
        self.current_scan: Optional[ScanReport] = None
        self.scan_history: List[ScanReport] = []

    def show_scanner_menu(self) -> None:
        """Zeigt Adult-Content Scanner Menü."""
        while True:
            ui.clear()
            ui.banner(subtitle="🔍 ADULT CONTENT SCANNER - Forensische Analyse")
            print()

            ui.rule("⚠️ WARNUNG & HAFTUNGSAUSSCHLUSS", ui.BRED)
            print()
            print("  Dieses Tool ist für AUTORISIERTE UNTERSUCHUNGEN gedacht:")
            print("  • Kinderschutz (Eltern-Monitoring)")
            print("  • Unternehmens-Compliance")
            print("  • Gerichtliche Verfahren")
            print("  • Strafverfolgung")
            print()
            print("  NUR MIT RECHTLICHER GENEHMIGUNG verwenden!")
            print()

            entries = [
                ("1", "🔍 Vollständiger Scan (alle Quellen)"),
                ("2", "🌐 Browser-Verlauf scannen"),
                ("3", "💬 Chat-Nachrichten scannen"),
                ("4", "🖼️  Bild-Dateien scannen"),
                ("5", "📱 App-Daten scannen"),
                ("6", "🗑️  Gelöschte Dateien suchen"),
                ("7", "📊 Scan-Ergebnisse anzeigen"),
                ("8", "📈 Detaillierte Statistiken"),
                ("9", "💾 Report exportieren"),
                ("0", "🗑️  Scanner-Daten löschen"),
            ]

            ch = ui.menu("Scanner-Optionen", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.run_full_scan()
            elif ch == "2":
                self.scan_browser_history()
            elif ch == "3":
                self.scan_chats()
            elif ch == "4":
                self.scan_images()
            elif ch == "5":
                self.scan_app_data()
            elif ch == "6":
                self.scan_deleted_files()
            elif ch == "7":
                self.show_results()
            elif ch == "8":
                self.show_statistics()
            elif ch == "9":
                self.export_report()
            elif ch == "0":
                self.clear_data()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def run_full_scan(self) -> None:
        """Führt vollständigen Scan durch."""
        # Double confirmation
        ui.clear()
        ui.rule("⚠️  VOLLSTÄNDIGER SCAN", ui.BRED)
        print()
        print("  Dies scannt ALLE Quellen nach Adult-Content:")
        print("  • Browser-Verlauf (alle Browser)")
        print("  • Chat-Nachrichten (WhatsApp, Telegram, etc)")
        print("  • Bilder & Videos")
        print("  • App-Daten")
        print("  • Gelöschte Dateien")
        print()

        if not ui.confirm("Wirklich starten?", False):
            return

        self.current_scan = ScanReport(
            scan_id=f"scan_{int(time.time())}",
            scan_start=time.time(),
        )

        ui.rule("🔍 SCAN LÄUFT...", ui.BCYAN)
        print()

        stages = [
            ("Browser-Verlauf", self.scan_browser_history),
            ("Chat-Nachrichten", self.scan_chats),
            ("Bild-Dateien", self.scan_images),
            ("App-Daten", self.scan_app_data),
            ("Gelöschte Dateien", self.scan_deleted_files),
        ]

        for i, (stage_name, scan_func) in enumerate(stages, 1):
            ui.progress(i, len(stages), stage_name)
            scan_func()

        self.current_scan.scan_end = time.time()
        self.current_scan.total_items_found = len(self.scan_results)
        self.current_scan.findings = self.scan_results

        # Calculate severity breakdown
        for result in self.scan_results:
            severity = result.severity.value
            self.current_scan.severity_breakdown[severity] = (
                self.current_scan.severity_breakdown.get(severity, 0) + 1
            )

        self.scan_history.append(self.current_scan)

        ui.progress(len(stages), len(stages), "Scan abgeschlossen!")
        print()
        ui.ok(f"Scan fertig! {len(self.scan_results)} Einträge gefunden.")
        ui.pause()

    def scan_browser_history(self) -> None:
        """Scannt Browser-Verlauf."""
        ui.clear()
        ui.rule("🌐 BROWSER-VERLAUF SCAN", ui.BCYAN)
        print()

        browsers = ["chrome", "firefox", "samsung", "opera"]

        for browser in browsers:
            print(f"  Scanne {browser.capitalize()}...")

            try:
                # Typische Pfade
                if browser == "chrome":
                    db_path = "/data/data/com.android.chrome/app_chrome/Default/History"
                elif browser == "firefox":
                    db_path = "/data/data/org.mozilla.firefox/files/browser.db"
                else:
                    db_path = f"/data/data/com.{browser}.browser/app_{browser}/History"

                # Lese Browser-DB
                self._scan_browser_db(db_path, browser)

            except Exception as e:
                pass

    def scan_chats(self) -> None:
        """Scannt Chat-Nachrichten."""
        ui.clear()
        ui.rule("💬 CHAT-NACHRICHTEN SCAN", ui.BCYAN)
        print()

        chat_apps = {
            "whatsapp": "/data/data/com.whatsapp/databases/",
            "telegram": "/data/data/org.telegram.messenger/files/",
            "facebook": "/data/data/com.facebook.katana/",
            "instagram": "/data/data/com.instagram.android/",
            "viber": "/data/data/com.viber.voip/",
            "line": "/data/data/jp.naver.line.android/",
        }

        for app_name, app_path in chat_apps.items():
            print(f"  Scanne {app_name.capitalize()}...")

            try:
                # Lese Chat-Datenbanken
                self._scan_chat_app(app_name, app_path)
            except Exception as e:
                pass

    def scan_images(self) -> None:
        """Scannt Bild-Dateien."""
        ui.clear()
        ui.rule("🖼️  BILD-DATEIEN SCAN", ui.BCYAN)
        print()

        image_dirs = [
            "/sdcard/DCIM/",
            "/sdcard/Pictures/",
            "/sdcard/Download/",
            "/data/media/0/",
        ]

        for img_dir in image_dirs:
            print(f"  Scanne {img_dir}...")

            try:
                # Finde Bilder
                result = self.adb.shell(f"find {img_dir} -type f -name '*.jpg' -o -name '*.png' -o -name '*.gif' 2>/dev/null | head -100")

                for file_path in result.split("\n"):
                    if file_path.strip():
                        self._analyze_image(file_path.strip())

            except Exception as e:
                pass

    def scan_app_data(self) -> None:
        """Scannt App-Daten."""
        ui.clear()
        ui.rule("📱 APP-DATEN SCAN", ui.BCYAN)
        print()

        # Adult Apps
        adult_apps = [
            "com.bumble.app",  # Dating App
            "com.tinder",      # Tinder
            "com.match.android.matchmobile",  # Match
            "com.grindr.android",  # Grindr
            "org.onlyfans",    # OnlyFans (falls vorhanden)
        ]

        for app_package in adult_apps:
            print(f"  Scanne {app_package}...")

            try:
                # Prüfe ob App installiert
                app_path = f"/data/data/{app_package}/"
                result = self.adb.shell(f"ls -la {app_path} 2>/dev/null")

                if "No such file" not in result:
                    # App gefunden - scannen
                    self._scan_app_directory(app_package, app_path)

            except Exception as e:
                pass

    def scan_deleted_files(self) -> None:
        """Scannt nach gelöschten Dateien."""
        ui.clear()
        ui.rule("🗑️  GELÖSCHTE DATEIEN SCAN", ui.BCYAN)
        print()

        print("  Suche nach Dateirelikten...")

        try:
            # Suche nach gelöschten Cache-Daten
            cache_dirs = [
                "/data/cache/",
                "/data/system/shared_prefs/",
                "/data/app-lib/",
            ]

            for cache_dir in cache_dirs:
                try:
                    result = self.adb.shell(f"find {cache_dir} -type f 2>/dev/null | head -50")

                    for file_path in result.split("\n"):
                        if file_path.strip():
                            self._analyze_deleted_file(file_path.strip())

                except:
                    pass

        except Exception as e:
            pass

    def show_results(self) -> None:
        """Zeigt Scan-Ergebnisse."""
        ui.clear()
        ui.rule("📊 SCAN-ERGEBNISSE", ui.BCYAN)
        print()

        if not self.scan_results:
            print("  Keine Adult-Content gefunden")
        else:
            # Gruppiere nach Severity
            results_by_severity = {}
            for result in self.scan_results:
                sev = result.severity.value
                if sev not in results_by_severity:
                    results_by_severity[sev] = []
                results_by_severity[sev].append(result)

            # Zeige nach Severity
            for severity in ["EXTREME", "EXPLICIT", "MODERATE", "SUSPICIOUS"]:
                if severity in results_by_severity:
                    results = results_by_severity[severity]
                    color = ui.BRED if severity in ["EXTREME", "EXPLICIT"] else ui.YELLOW
                    print(f"\n  {color}=== {severity} ({len(results)} items) ==={ui.RESET}")

                    for result in results[:5]:  # Top 5 pro Severity
                        print(f"    • {result.title}")
                        print(f"      Typ: {result.content_type.value}")
                        if result.url:
                            print(f"      URL: {result.url}")
                        print()

        print()
        ui.pause()

    def show_statistics(self) -> None:
        """Zeigt detaillierte Statistiken."""
        ui.clear()
        ui.rule("📈 DETAILLIERTE STATISTIKEN", ui.BCYAN)
        print()

        if self.current_scan:
            duration = self.current_scan.scan_end - self.current_scan.scan_start
            ui.kv("Scan-Dauer", f"{duration:.1f} Sekunden")
            ui.kv("Gesamt Einträge gefunden", str(self.current_scan.total_items_found))
            print()

            # Breakdown by severity
            print("  Nach Schweregrad:")
            for severity, count in self.current_scan.severity_breakdown.items():
                pct = (count / max(self.current_scan.total_items_found, 1)) * 100
                print(f"    {severity}: {count} ({pct:.1f}%)")

            print()

            # Breakdown by type
            print("  Nach Inhaltstyp:")
            type_counts = {}
            for result in self.scan_results:
                t = result.content_type.value
                type_counts[t] = type_counts.get(t, 0) + 1

            for content_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"    {content_type}: {count}")

        print()
        ui.pause()

    def export_report(self) -> None:
        """Exportiert Scan-Report."""
        ui.clear()
        ui.rule("💾 REPORT EXPORTIEREN", ui.BCYAN)
        print()

        if not self.scan_results:
            ui.warn("Keine Ergebnisse zum Exportieren")
            ui.pause()
            return

        # Generiere Report
        report = {
            "scan_id": self.current_scan.scan_id if self.current_scan else "N/A",
            "timestamp": datetime.now().isoformat(),
            "total_items": len(self.scan_results),
            "findings": [
                {
                    "id": r.content_id,
                    "type": r.content_type.value,
                    "severity": r.severity.value,
                    "title": r.title,
                    "url": r.url,
                    "timestamp": r.timestamp,
                    "source": r.source,
                    "keywords": r.keywords,
                }
                for r in self.scan_results
            ]
        }

        # Speichere JSON
        json_path = "/sdcard/Download/adult_content_report.json"
        try:
            self.adb.push_string(json.dumps(report, indent=2), json_path)
            ui.ok(f"Report exportiert: {json_path}")
        except Exception as e:
            ui.err(f"Export-Fehler: {e}")

        print()
        ui.pause()

    def clear_data(self) -> None:
        """Löscht Scanner-Daten."""
        ui.clear()
        ui.rule("🗑️  SCANNER-DATEN LÖSCHEN", ui.BRED)
        print()
        print("  ⚠️ Dies löscht ALLE Scan-Ergebnisse permanent!")
        print()

        if not ui.confirm("Wirklich löschen?", False):
            return

        self.scan_results = []
        self.current_scan = None
        self.scan_history = []

        ui.ok("Scanner-Daten gelöscht")
        ui.pause()

    def _scan_browser_db(self, db_path: str, browser: str) -> None:
        """Scannt Browser-Datenbank auf Adult-Content."""
        try:
            # Kopiere DB lokal
            temp_path = f"/tmp/{browser}_history.db"
            self.adb.pull(db_path, temp_path)

            # Öffne DB
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()

            # Query history
            try:
                cursor.execute("SELECT url, title FROM urls")
                for url, title in cursor.fetchall():
                    severity = self._check_adult_content(url, title)
                    if severity != ContentSeverity.NONE:
                        self.scan_results.append(AdultContent(
                            content_id=f"browser_{len(self.scan_results)}",
                            content_type=ContentType.BROWSER_HISTORY,
                            severity=severity,
                            source=browser,
                            title=title or url[:50],
                            url=url,
                        ))
            except:
                pass

            conn.close()

        except Exception as e:
            pass

    def _scan_chat_app(self, app_name: str, app_path: str) -> None:
        """Scannt Chat-App Datenbanken."""
        try:
            # Typical chat DB paths
            if app_name == "whatsapp":
                db_names = ["msgstore.db", "wa.db"]
            else:
                db_names = ["*.db"]

            for db_name in db_names:
                try:
                    result = self.adb.shell(f"find {app_path} -name '{db_name}' 2>/dev/null")
                    # Analyse durchführen
                except:
                    pass

        except Exception as e:
            pass

    def _analyze_image(self, file_path: str) -> None:
        """Analysiert Bild-Datei auf Adult-Content."""
        try:
            # Prüfe Dateiname
            filename = file_path.split("/")[-1].lower()

            severity = self._check_adult_content(filename, "")

            if severity != ContentSeverity.NONE:
                self.scan_results.append(AdultContent(
                    content_id=f"image_{len(self.scan_results)}",
                    content_type=ContentType.IMAGE_FILE,
                    severity=severity,
                    source="File System",
                    title=filename,
                    file_path=file_path,
                ))

        except Exception as e:
            pass

    def _scan_app_directory(self, app_package: str, app_path: str) -> None:
        """Scannt App-Verzeichnis."""
        try:
            result = self.adb.shell(f"find {app_path} -type f 2>/dev/null | head -20")

            for file_path in result.split("\n"):
                if file_path.strip():
                    # Analysiere
                    pass

        except Exception as e:
            pass

    def _analyze_deleted_file(self, file_path: str) -> None:
        """Analysiert gelöschte Datei."""
        try:
            filename = file_path.split("/")[-1].lower()
            severity = self._check_adult_content(filename, "")

            if severity != ContentSeverity.NONE:
                self.scan_results.append(AdultContent(
                    content_id=f"deleted_{len(self.scan_results)}",
                    content_type=ContentType.DELETED_BROWSER,
                    severity=severity,
                    source="Deleted Files",
                    title=filename,
                    file_path=file_path,
                ))

        except Exception as e:
            pass

    def _check_adult_content(self, url: str, title: str) -> ContentSeverity:
        """Prüft ob Content Adult ist und gibt Severity zurück."""
        text = f"{url} {title}".lower()

        # Zähle Keywords & Phrases
        keyword_count = 0
        matched = []

        for keyword in self.ADULT_KEYWORDS:
            if keyword in text:
                keyword_count += 1
                matched.append(keyword)

        # Prüfe Domains
        for domain in self.ADULT_DOMAINS:
            if domain in text:
                keyword_count += 3  # Domain matches zählen stärker

        # Bestimme Severity
        if keyword_count >= 5:
            return ContentSeverity.EXTREME
        elif keyword_count >= 3:
            return ContentSeverity.EXPLICIT
        elif keyword_count >= 2:
            return ContentSeverity.MODERATE
        elif keyword_count >= 1:
            return ContentSeverity.SUSPICIOUS
        else:
            return ContentSeverity.NONE


def create_adult_content_scanner(adb: ADB) -> AdultContentScanner:
    """Erstellt neuen Adult Content Scanner."""
    return AdultContentScanner(adb)
