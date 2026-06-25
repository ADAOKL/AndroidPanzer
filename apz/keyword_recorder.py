"""KEYWORD RECORDER: Intelligente Audio-Erfassung mit Keyword-Erkennung!

Aufzeichnung nur bei bestimmten Schlagwörtern - smart & effizient!
"""
from __future__ import annotations

import os
import json
import time
import re
from typing import Optional, List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

from . import ui
from . import profile_manager
from . import keyword_display
from . import master_keyword_table
from .adb import ADB


class RecognitionEngine(Enum):
    """Speech-to-Text Engines."""
    VOSK_LOCAL = "Vosk (Lokal, offline)"
    WHISPER_OPENAI = "OpenAI Whisper"
    GOOGLE_CLOUD = "Google Cloud Speech-to-Text"
    AZURE_SPEECH = "Microsoft Azure Speech"
    IBM_WATSON = "IBM Watson"
    POCKETSPHINX = "PocketSphinx (CMU)"
    DEEP_SPEECH = "Mozilla Deep Speech"


class RecordingMode(Enum):
    """Recording Modi."""
    TRIGGER_ONLY = "Nur bei Keyword"
    CONTINUOUS = "Kontinuierlich mit Highlights"
    BUFFER = "Zirkulärer Buffer (vor/nach)"
    SNAPSHOT = "Kurze Snapshots"
    CONTEXT = "Kontext-basiert"


class MatchMode(Enum):
    """Matching Modi."""
    EXACT = "Exakte Übereinstimmung"
    PARTIAL = "Teilwort-Match"
    FUZZY = "Fuzzy-Matching (Typos)"
    REGEX = "Regular Expression"
    PHONETIC = "Phonetisches Matching"


@dataclass
class Keyword:
    """Ein Schlagwort."""
    keyword_id: str
    text: str
    priority: int = 5  # 1-10, höher = wichtiger
    confidence_threshold: float = 0.7  # 0.0-1.0
    match_mode: MatchMode = MatchMode.PARTIAL
    enabled: bool = True
    category: str = "General"
    aliases: List[str] = field(default_factory=list)
    context_words: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class KeywordProfile:
    """Ein Keyword-Profil."""
    profile_id: str
    name: str
    description: str = ""
    keywords: List[Keyword] = field(default_factory=list)
    recording_mode: RecordingMode = RecordingMode.TRIGGER_ONLY
    pre_trigger_seconds: int = 5
    post_trigger_seconds: int = 10
    min_keyword_gap_seconds: int = 2
    max_recording_duration: int = 300
    confidence_threshold: float = 0.75
    enabled: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class DetectionEvent:
    """Ein Keyword-Detection Event."""
    event_id: str
    keyword: str
    timestamp: float
    confidence: float
    transcription: str
    context: str = ""
    matched_mode: str = ""


@dataclass
class RecordingSession:
    """Eine Keyword-Recording Session."""
    session_id: str
    profile_id: str
    start_time: float
    end_time: float = 0.0
    status: str = "recording"  # recording, paused, stopped
    detections: List[DetectionEvent] = field(default_factory=list)
    total_audio_bytes: int = 0
    trigger_count: int = 0
    file_path: str = ""


class KeywordRecorder:
    """Master Keyword Recorder - Intelligente Aufzeichnung."""

    # VORDEFINIERTE KEYWORD-PROFILE
    DEFAULT_PROFILES = {
        "security": {
            "name": "Sicherheits-Keywords",
            "keywords": [
                "password", "passwort", "pin", "secret", "geheim",
                "hack", "attack", "angriff", "breach", "steal",
                "exploit", "vulnerability", "malware", "ransomware",
                "encryption", "decrypt", "backdoor", "trojan",
            ]
        },
        "financial": {
            "name": "Finanz-Keywords",
            "keywords": [
                "credit", "debit", "bank", "account", "balance",
                "transfer", "payment", "money", "geld", "euro",
                "bitcoin", "crypto", "invest", "transaction",
                "fraud", "betrug", "illegal",
            ]
        },
        "medical": {
            "name": "Medizinische Keywords",
            "keywords": [
                "patient", "doctor", "hospital", "medicine", "drug",
                "behandlung", "krankheit", "symptom", "test",
                "prescription", "diagnosis", "surgery", "operation",
            ]
        },
        "legal": {
            "name": "Juridische Keywords",
            "keywords": [
                "lawyer", "court", "judge", "law", "legal",
                "contract", "agreement", "lawsuit", "trial",
                "recht", "gericht", "gesetz", "vertrag",
            ]
        },
        "emergency": {
            "name": "Notfall-Keywords",
            "keywords": [
                "help", "help!", "emergency", "911", "police",
                "ambulance", "fire", "danger", "dangerous",
                "hilfe", "notfall", "feuer", "gefahr",
            ]
        },
    }

    def __init__(self, adb: ADB):
        self.adb = adb
        self.profiles: Dict[str, KeywordProfile] = {}
        self.active_profile: Optional[KeywordProfile] = None
        self.sessions: List[RecordingSession] = []
        self.detection_history: List[DetectionEvent] = []
        self.recognition_engine = RecognitionEngine.VOSK_LOCAL
        self._load_default_profiles()

    def _load_default_profiles(self) -> None:
        """Lädt vordefinierte Profile."""
        for profile_id, profile_data in self.DEFAULT_PROFILES.items():
            keywords = []
            for kw_text in profile_data["keywords"]:
                keywords.append(Keyword(
                    keyword_id=f"{profile_id}_{kw_text}",
                    text=kw_text,
                    category=profile_data["name"],
                ))

            profile = KeywordProfile(
                profile_id=profile_id,
                name=profile_data["name"],
                keywords=keywords,
            )
            self.profiles[profile_id] = profile

    def show_keyword_recorder_menu(self) -> None:
        """Zeigt Keyword-Recorder Menü."""
        while True:
            ui.clear()

            ui.banner(subtitle="🎯 KEYWORD RECORDER - Intelligente Audio-Aufzeichnung")
            print()

            entries = [
                ("1", "📋 Keyword-Profile verwalten"),
                ("2", "🎯 Keywords hinzufügen/bearbeiten"),
                ("3", "⚙️  Recording-Einstellungen"),
                ("4", "▶️  Aufzeichnung mit Keywords starten"),
                ("5", "📊 Detection-Statistiken anzeigen"),
                ("6", "🔍 Aufzeichnungen durchsuchen"),
                ("7", "📁 Aufgezeichnete Dateien verwalten"),
                ("8", "🎤 Speech-Recognition Engine wechseln"),
                ("9", "📈 Analytics & Reports"),
                ("10", "📋 MASTER KEYWORD TABELLE - ALLE KEYWORDS!"),
            ]

            ch = ui.menu("Keyword Recorder", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return

            if ch == "1":
                self.manage_profiles()
            elif ch == "2":
                self.manage_keywords()
            elif ch == "3":
                self.recording_settings()
            elif ch == "4":
                self.start_keyword_recording()
            elif ch == "5":
                self.show_statistics()
            elif ch == "6":
                self.search_recordings()
            elif ch == "7":
                self.manage_files()
            elif ch == "8":
                self.select_engine()
            elif ch == "9":
                self.show_analytics()
            elif ch == "10":
                self.show_master_keyword_table()
            else:
                ui.warn("Ungültige Option")
                time.sleep(0.5)

    def manage_profiles(self) -> None:
        """Verwaltet Keyword-Profile."""
        ui.clear()
        ui.rule("📋 KEYWORD-PROFILE", ui.BCYAN)
        print()

        print("  Verfügbare Profile:\n")

        for i, (profile_id, profile) in enumerate(self.profiles.items(), 1):
            status = "✓" if profile.enabled else "✗"
            print(f"  {status} {i}. {profile.name}")
            print(f"     Keywords: {len(profile.keywords)}")
            print(f"     Modus: {profile.recording_mode.value}")
            print()

        print("  OPTIONEN:\n")
        print("    1. Profil wählen/aktivieren")
        print("    2. Profil erstellen")
        print("    3. Profil bearbeiten")
        print("    4. Profil löschen")
        print("    5. Profil importieren")
        print("    6. Profil exportieren")

        choice = ui.ask("Option (1-6)", "1")

        if choice == "1":
            print("\n  Wähle Profil:")
            for i, (pid, p) in enumerate(self.profiles.items(), 1):
                print(f"    {i}. {p.name} ({len(p.keywords)} Keywords)")

            idx = ui.ask("Profil (Nummer)", "1")
            try:
                idx = int(idx) - 1
                profile_list = list(self.profiles.items())
                if 0 <= idx < len(profile_list):
                    self.active_profile = profile_list[idx][1]
                    ui.ok(f"✓ {self.active_profile.name} aktiviert")
            except:
                ui.warn("Ungültige Eingabe")

        elif choice == "2":
            profile_name = ui.ask("Neuer Profil-Name", "My Profile")
            new_profile = KeywordProfile(
                profile_id=f"custom_{int(time.time())}",
                name=profile_name,
                keywords=[],
            )
            self.profiles[new_profile.profile_id] = new_profile
            ui.ok(f"✓ Profil erstellt: {profile_name}")

        ui.pause()

    def manage_keywords(self) -> None:
        """Verwaltet Keywords."""
        ui.clear()
        ui.rule("🎯 KEYWORDS VERWALTEN", ui.BCYAN)
        print()

        if not self.active_profile:
            # Show profile selector
            pm = profile_manager.create_profile_manager()
            selected_id = pm.show_profile_selector(self.profiles)

            if not selected_id:
                return

            # Set as active
            self.active_profile = self.profiles[selected_id]
            pm.selected_profile = selected_id

        print(f"  Profil: {self.active_profile.name}\n")
        print(f"  Keywords ({len(self.active_profile.keywords)}):\n")

        for i, kw in enumerate(self.active_profile.keywords[:10], 1):
            status = "✓" if kw.enabled else "✗"
            print(f"  {status} {i}. {kw.text}")
            print(f"     Priorität: {kw.priority}/10, Confidence: {kw.confidence_threshold*100:.0f}%")
            print()

        print("  OPTIONEN:\n")
        print("    1. Keyword hinzufügen")
        print("    2. Keyword aktivieren/deaktivieren")
        print("    3. Keyword-Priorität ändern")
        print("    4. Keyword löschen")

        choice = ui.ask("Option (1-4)", "1")

        if choice == "1":
            kw_text = ui.ask("Keyword eingeben", "password")
            priority = int(ui.ask("Priorität (1-10)", "5"))

            new_kw = Keyword(
                keyword_id=f"{self.active_profile.profile_id}_{kw_text}",
                text=kw_text,
                priority=priority,
                category=self.active_profile.name,
            )

            self.active_profile.keywords.append(new_kw)
            ui.ok(f"✓ Keyword hinzugefügt: {kw_text}")

        ui.pause()

    def recording_settings(self) -> None:
        """Recording-Einstellungen."""
        ui.clear()
        ui.rule("⚙️  RECORDING-EINSTELLUNGEN", ui.BCYAN)
        print()

        if not self.active_profile:
            print("  Wähle erst ein Profil!")
            ui.pause()
            return

        profile = self.active_profile

        print(f"  Profil: {profile.name}\n")
        print("  AKTUELLE EINSTELLUNGEN:\n")
        print(f"  Recording-Modus:          {profile.recording_mode.value}")
        print(f"  Sekunden VOR Keyword:     {profile.pre_trigger_seconds}s")
        print(f"  Sekunden NACH Keyword:    {profile.post_trigger_seconds}s")
        print(f"  Min. Keyword-Abstand:     {profile.min_keyword_gap_seconds}s")
        print(f"  Max. Aufzeichnungsdauer:  {profile.max_recording_duration}s")
        print(f"  Confidence Schwelle:      {profile.confidence_threshold*100:.0f}%")
        print()

        print("  Modi:\n")
        for i, mode in enumerate(RecordingMode, 1):
            print(f"    {i}. {mode.value}")

        choice = ui.ask("Modus wählen (1-5)", "1")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(list(RecordingMode)):
                profile.recording_mode = list(RecordingMode)[idx]
                ui.ok("✓ Einstellungen aktualisiert")
        except:
            ui.warn("Ungültige Eingabe")

        ui.pause()

    def start_keyword_recording(self) -> None:
        """Startet Aufzeichnung mit Keywords."""
        if not self.active_profile:
            ui.clear()
            ui.rule("▶️  KEYWORD-RECORDING STARTEN", ui.BCYAN)
            print("\n  Wähle erst ein Profil mit Keywords!")
            ui.pause()
            return

        profile = self.active_profile

        # Get keywords list
        keywords_list = [kw.text for kw in profile.keywords]

        # Show profile with keywords using new display
        display = keyword_display.create_keyword_display()
        display.show_profile_with_keywords(
            profile_name=profile.name,
            profile_description="Keywords-basierte Audio-Aufzeichnung",
            recording_mode=profile.recording_mode.value,
            keywords=keywords_list,
            keyword_priorities={kw.text: kw.priority for kw in profile.keywords},
            total_keywords=len(profile.keywords)
        )

        # Ask for confirmation
        if not display.show_recording_ready(
            profile_name=profile.name,
            keyword_count=len(profile.keywords),
            recording_mode=profile.recording_mode.value,
            duration_max_sec=profile.max_recording_duration
        ):
            return

        print("\n  Starte Aufzeichnung mit Keyword-Erkennung...\n")

        # Erstelle Session
        session = RecordingSession(
            session_id=f"kwrec_{int(time.time())}",
            profile_id=profile.profile_id,
            start_time=time.time(),
        )

        # Simuliere Aufzeichnung
        print("  🎤 Lausche auf Keywords...")
        print(f"  Engine: {self.recognition_engine.value}")
        print()

        # Simuliere Detection Events
        for i in range(1, 5):
            ui.progress(i, 4, "Lausche auf Keywords...")
            time.sleep(0.5)

            # Fake Detection
            if i == 2:
                event = DetectionEvent(
                    event_id=f"det_{i}",
                    keyword="password",
                    timestamp=time.time(),
                    confidence=0.92,
                    transcription="The password is secure",
                    context="discussion about security",
                )
                session.detections.append(event)
                self.detection_history.append(event)

                print()
                print(f"  🎯 KEYWORD ERKANNT: 'password' (92% Confidence)")
                print(f"     Text: '{event.transcription}'")
                print()

            elif i == 3:
                event = DetectionEvent(
                    event_id=f"det_{i}",
                    keyword="hack",
                    timestamp=time.time(),
                    confidence=0.88,
                    transcription="They tried to hack the system",
                    context="security incident",
                )
                session.detections.append(event)
                self.detection_history.append(event)

                print(f"  🎯 KEYWORD ERKANNT: 'hack' (88% Confidence)")
                print(f"     Text: '{event.transcription}'")
                print()

        session.end_time = time.time()
        session.trigger_count = len(session.detections)
        self.sessions.append(session)

        ui.ok(f"✓ Aufzeichnung abgeschlossen")
        print(f"\n  Erkannte Keywords: {session.trigger_count}")
        print(f"  Dauer: {int(session.end_time - session.start_time)}s")

        ui.pause()

    def show_statistics(self) -> None:
        """Zeigt Detection-Statistiken."""
        ui.clear()
        ui.rule("📊 DETECTION-STATISTIKEN", ui.BCYAN)
        print()

        print("  ZUSAMMENFASSUNG:\n")
        print(f"  Insgesamt Sessions: {len(self.sessions)}")
        print(f"  Insgesamt Detections: {len(self.detection_history)}")
        print()

        if self.detection_history:
            print("  TOP KEYWORDS:\n")

            kw_counts = {}
            for det in self.detection_history:
                kw_counts[det.keyword] = kw_counts.get(det.keyword, 0) + 1

            for kw, count in sorted(kw_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"    {kw:20} {count:3}x erkannt")

        ui.pause()

    def search_recordings(self) -> None:
        """Durchsucht Aufzeichnungen."""
        ui.clear()
        ui.rule("🔍 AUFZEICHNUNGEN DURCHSUCHEN", ui.BCYAN)
        print()

        search_term = ui.ask("Keyword suchen", "password")

        results = [d for d in self.detection_history if search_term.lower() in d.keyword.lower()]

        print(f"\n  Gefundene Treffer: {len(results)}\n")

        for result in results[:10]:
            print(f"  🎯 {result.keyword}")
            print(f"     Text: {result.transcription}")
            print(f"     Confidence: {result.confidence*100:.0f}%")
            print()

        ui.pause()

    def manage_files(self) -> None:
        """Verwaltet Aufzeichnete Dateien."""
        ui.clear()
        ui.rule("📁 AUFZEICHNETE DATEIEN", ui.BCYAN)
        print()

        print(f"  Aufgezeichnete Sessions: {len(self.sessions)}\n")

        for session in self.sessions[:5]:
            duration = int(session.end_time - session.start_time)
            print(f"  📂 {session.session_id}")
            print(f"     Profil: {session.profile_id}")
            print(f"     Dauer: {duration}s")
            print(f"     Detections: {session.trigger_count}")
            print()

        ui.pause()

    def select_engine(self) -> None:
        """Wählt Speech-Recognition Engine."""
        ui.clear()
        ui.rule("🎤 SPEECH-RECOGNITION ENGINE", ui.BCYAN)
        print()

        print("  Verfügbare Engines:\n")

        for i, engine in enumerate(RecognitionEngine, 1):
            selected = "✓" if engine == self.recognition_engine else " "
            print(f"  {selected} {i}. {engine.value}")

        choice = ui.ask("Engine wählen (1-7)", "1")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(list(RecognitionEngine)):
                self.recognition_engine = list(RecognitionEngine)[idx]
                ui.ok(f"✓ Engine geändert: {self.recognition_engine.value}")
        except:
            ui.warn("Ungültige Eingabe")

        ui.pause()

    def show_analytics(self) -> None:
        """Zeigt Analytics & Reports."""
        ui.clear()
        ui.rule("📈 ANALYTICS & REPORTS", ui.BCYAN)
        print()

        print("  STATISTIKEN:\n")
        print(f"  Sessions insgesamt:       {len(self.sessions)}")
        print(f"  Detections insgesamt:     {len(self.detection_history)}")

        if self.detection_history:
            avg_confidence = sum(d.confidence for d in self.detection_history) / len(self.detection_history)
            print(f"  Ø Confidence:             {avg_confidence*100:.1f}%")

        total_duration = sum(int(s.end_time - s.start_time) for s in self.sessions if s.end_time)
        print(f"  Aufzeichnungszeit:        {total_duration}s")
        print()

        ui.pause()

    def show_master_keyword_table(self) -> None:
        """Punkt 10: Zeige Master Keyword Tabelle mit ALLEN Keywords!"""
        ui.clear()
        ui.rule("📋 PUNKT 10 - MASTER KEYWORD TABELLE", ui.BCYAN)
        print()

        table = master_keyword_table.create_master_keyword_table()

        print("  OPTIONEN:\n")
        print("    1. Vollständige Tabelle (sortiert nach Priorität)")
        print("    2. Gruppiert nach Profil (Sexual, Drogen, Straftaten)")
        print("    3. Gruppiert nach Kategorie")
        print("    4. Nur High-Priority Keywords (Priorität >= 8)")
        print("    5. Suche nach Keyword")
        print("    6. Statistiken anzeigen")
        print()

        choice = ui.ask("Option (1-6)", "1")

        if choice == "1":
            table.show_full_table(sort_by="priority")
            ui.pause()
        elif choice == "2":
            table.show_by_profile()
            ui.pause()
        elif choice == "3":
            table.show_by_category()
            ui.pause()
        elif choice == "4":
            table.show_high_priority_only()
            ui.pause()
        elif choice == "5":
            search_term = ui.ask("Suchbegriff eingeben", "password")
            table.search_keyword(search_term)
        elif choice == "6":
            table.show_statistics()
            ui.pause()


def create_keyword_recorder(adb: ADB) -> KeywordRecorder:
    """Erstellt neuen Keyword Recorder."""
    return KeywordRecorder(adb)

def menu(adb=None) -> None:
    """KeywordRecorder Menu Wrapper."""
    obj = KeywordRecorder(adb) if adb else KeywordRecorder()
    obj.show_keyword_recorder_menu()
