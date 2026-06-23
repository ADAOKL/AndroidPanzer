"""Zentrales Live-Fortschrittsbalken-System für ALLE 54 Module + Submodule.

Wird automatisch im Dispatch (main.py) und optional in Submodul-Operationen genutzt.
Kein Anfassen einzelner Modul-Dateien nötig.
"""
from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from typing import Callable, Generator

from . import ui

BAR_LEN = 38
FILLED  = "▰"
EMPTY   = "▱"


# ─── Kern-Klasse ──────────────────────────────────────────────────────────────

class LiveBar:
    """Live-Fortschrittsbalken der bei jedem Modul-Start erscheint.

    Verwendung als Context-Manager:
        with LiveBar("APK-SCANNER", 5) as bar:
            bar.step("Manifest laden")
            bar.step("DEX analysieren")
            ...

    Oder einzeilig über run_steps().
    """

    def __init__(self, title: str, total: int, color: str = ui.BCYAN):
        self.title  = title
        self.total  = max(1, total)
        self.color  = color
        self._step  = 0
        self._start = 0.0
        self._label = ""

    def __enter__(self) -> "LiveBar":
        self._start = time.monotonic()
        print(f"\n{self.color}{ui.BOLD}▶  {self.title}{ui.RESET}")
        self._draw(0, "Initialisiere …")
        return self

    def __exit__(self, *_) -> None:
        self._draw(self.total, "Abgeschlossen")
        elapsed = time.monotonic() - self._start
        print(f"\n  {ui.BGREEN}✓ {self.title}  ({elapsed:.1f}s){ui.RESET}\n")

    def step(self, label: str = "") -> None:
        """Nächsten Schritt melden und Balken aktualisieren."""
        self._step = min(self._step + 1, self.total)
        self._draw(self._step, label)

    def update(self, n: int, label: str = "") -> None:
        """Balken auf Position n setzen."""
        self._step = min(n, self.total)
        self._draw(self._step, label)

    def _draw(self, step: int, label: str) -> None:
        pct    = min(step / self.total, 1.0)
        filled = int(BAR_LEN * pct)
        bar    = FILLED * filled + EMPTY * (BAR_LEN - filled)
        elapsed = time.monotonic() - self._start
        sys.stdout.write(
            f"\r  {self.color}│{bar}│{ui.RESET}"
            f" {pct*100:5.1f}%  {label:<30}  {elapsed:4.1f}s"
        )
        sys.stdout.flush()


# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def run_steps(title: str, steps: list[str], delay: float = 0.06,
              color: str = ui.BCYAN) -> None:
    """Führt eine feste Schritt-Liste mit LiveBar durch.

    Typische Nutzung:
        run_steps("FORENSIK SUITE", ["ADB-Verbindung prüfen",
                                     "Artefakt-Liste laden",
                                     "Analyse starten"])
    """
    with LiveBar(title, len(steps), color) as bar:
        for step in steps:
            bar.step(step)
            time.sleep(delay)


@contextmanager
def scan_bar(title: str, total: int,
             color: str = ui.BCYAN) -> Generator[LiveBar, None, None]:
    """Context-Manager für laufende Scans innerhalb von Modulen.

    Verwendung:
        with scan_bar("APK-Analyse", 120) as bar:
            for i, apk in enumerate(apk_list, 1):
                bar.update(i, apk.name)
                analyse(apk)
    """
    with LiveBar(title, total, color) as bar:
        yield bar


def dispatch_bar(nr: int, name: str, steps: list[str],
                 fn: Callable, *args, **kwargs):
    """Zeigt Lade-Bar für ein Hauptmenü-Modul und ruft fn(*args) auf.

    Wird von _numeric_main_menu für alle 54 Module automatisch genutzt.
    """
    run_steps(f"[{nr:02d}] {name}", steps)
    return fn(*args, **kwargs)


# ─── Modul-Initialisierungs-Schritte (für alle 54 Hauptmenü-Punkte) ───────────
# Format: choice_str → (init_steps_liste)
# Diese Schritte erscheinen als Ladebalken BEVOR das Modul öffnet.

MODULE_INIT_STEPS: dict[str, list[str]] = {
    "1":  ["Deep-Analysis-Engine laden", "450 Feature-Scanner vorbereiten",
           "KI-Modelle initialisieren", "ADB-Kanal öffnen"],
    "2":  ["Gerätedaten abrufen", "Dashboard-Renderer starten", "Live-Metriken laden"],
    "3":  ["45 Kategorien laden", "Feature-Matrix aufbauen", "Menü rendern"],
    "4":  ["Einstellungs-Manager laden", "Theme-Profile lesen", "UI initialisieren"],
    "5":  ["Konfigurations-Datei lesen", "Einstellungs-Fenster öffnen"],
    "6":  ["Mikrofon-Subsystem initialisieren", "Audio-Puffer vorbereiten",
           "Keyword-Engine laden", "Recording-Thread starten"],
    "7":  ["Kamera-Subsystem initialisieren", "Video-Puffer vorbereiten",
           "Screenshot-Engine laden", "ADB-Kamera-Tunnel öffnen"],
    "8":  ["Netzwerk-Interfaces scannen", "SIM-Slot-Status abrufen",
           "WiFi-Adapter prüfen", "Cellular-Layer initialisieren"],
    "9":  ["Forensik-Suite laden", "Artefakt-Definitionen lesen",
           "ADB-Forensik-Kanal öffnen", "Parser-Registry initialisieren"],
    "10": ["APK-Scanner laden", "Signature-Datenbank öffnen",
           "DEX-Parser initialisieren", "Manifest-Checker starten"],
    "11": ["App-Datenbank laden", "Permissions-Matrix aufbauen",
           "Tiefen-Analyse-Engine bereit"],
    "12": ["Dateisystem-Explorer laden", "ADB-Shell-Kanal öffnen",
           "Verzeichnisbaum initialisieren"],
    "13": ["Daten-Forensik-Engine laden", "Datenrettungs-Algorithmen initialisieren",
           "gelöschte-Daten-Scanner bereit"],
    "14": ["Tiefe Engine laden", "frida-Brücke initialisieren",
           "Laufzeit-Hooks vorbereiten", "Objection-Layer starten"],
    "15": ["Fall-Datenbank öffnen", "Case-Manager initialisieren",
           "Beweise-Registry laden"],
    "16": ["Report-Generator laden", "Template-Engine initialisieren",
           "Export-Verzeichnis prüfen"],
    "17": ["Modus-Erkennung starten", "USB-Zustand lesen",
           "ADB/Fastboot-Switcher initialisieren"],
    "18": ["Custom-Firmware-Scanner laden", "LineageOS-Daten abrufen",
           "TWRP-Versionen prüfen", "Flash-Engine bereit"],
    "19": ["Rootkit-Scanner laden", "Kernel-Signaturen laden",
           "System-Integrität prüfen", "ADB-Root-Kanal öffnen"],
    "20": ["Root-Tools laden", "Magisk-Prüfung starten",
           "Exploit-Datenbank laden", "Root-Diagnose initialisieren"],
    "21": ["Akquisitions-Engine laden", "E01-Writer initialisieren",
           "Hashing-Subsystem starten", "ADB-Pull-Kanal öffnen"],
    "22": ["Entschlüsselungs-Engine laden", "Hashcat-Brücke initialisieren",
           "Keystore-Analyse starten"],
    "23": ["Brute-Force-Engine laden", "50 Angriffs-Strategien initialisieren",
           "Wordlist-Manager bereit"],
    "24": ["WiFi-Handshake-Catcher laden", "Aircrack-Brücke initialisieren",
           "Monitor-Mode prüfen"],
    "25": ["DNS-Guardian laden", "Blocklist-Datenbank öffnen",
           "Filter-Engine initialisieren", "Monitor starten"],
    "26": ["Tracker-System laden", "IP-Geo-Datenbank öffnen",
           "Phone-Tracker initialisieren"],
    "27": ["Intelligente Engine laden", "ML-Modelle initialisieren",
           "KI-Analyse-Pipeline starten"],
    "28": ["Datenbank-Scanner laden", "SQLite-Parser initialisieren",
           "WAL-Analyse-Engine starten"],
    "29": ["Lab-Manager laden", "venv-Status prüfen",
           "Docker-Umgebung erkennen"],
    "30": ["3D-WiFi-Scanner laden", "Raum-Kartographie initialisieren",
           "Signal-Stärken-Mapper starten"],
    "31": ["Adult-Activity-Detector laden", "Klassifizierungs-Modell laden",
           "Detektion-Engine initialisieren"],
    "32": ["Anomalie-Detektor laden", "Baseline-Profile lesen",
           "ROT-Puls-Engine initialisieren"],
    "33": ["KI-Arzt laden", "Diagnose-Modelle initialisieren",
           "Auto-Fix-Engine bereit"],
    "34": ["Forensik-Analyse laden", "Audio-Analyse-Engine initialisieren",
           "Aktivitäts-Detektor starten"],
    "35": ["Security-Framework laden", "Enterprise-Richtlinien lesen",
           "Sicherheits-Scanner initialisieren"],
    "36": ["Passwort-Manager laden", "verschlüsselte Datenbank öffnen",
           "Passwort-Analyse-Engine starten"],
    "37": ["Audio-Playback laden", "Medien-Bibliothek scannen",
           "Player-Engine initialisieren"],
    "38": ["ADB-Shell laden", "interaktive Shell initialisieren",
           "Pty-Kanal öffnen"],
    "39": ["Auto-Root-Engine laden", "Exploit-Kaskade initialisieren",
           "Datenrettungs-Module laden", "Root-Strategie wählen"],
    "40": ["Keyword-Recorder laden", "Audio-Engine initialisieren",
           "Keyword-Datenbank öffnen"],
    "41": ["Auto-Rescue laden", "Flash-Kaskade initialisieren",
           "Recovery-Profile lesen", "ADB/Fastboot prüfen"],
    "42": ["Bootloop-Monitor laden", "USB-Event-Listener starten",
           "Zyklus-Detektor initialisieren"],
    "43": ["OSINT-Toolkit laden", "IP-Lookup-APIs initialisieren",
           "Username-Checker laden", "KI-Analyst bereit"],
    "44": ["KI-ADB-Shell laden", "Ollama-Verbindung prüfen",
           "LLM-Kontext initialisieren", "ADB-Brücke öffnen"],
    "45": ["Samsung-Tools laden", "Odin-Protokoll initialisieren",
           "TWRP-Datenbank laden", "Knox-Status prüfen"],
    "46": ["Mediatek-Root laden", "mtkclient-Brücke initialisieren",
           "BROM-Protokoll bereit", "EDL-Erkennung starten"],
    "47": ["Hersteller-Tools laden", "Xiaomi-Bootloader-Modul",
           "Pixel-Fastboot-Modul", "OnePlus/Huawei-Modul"],
    "48": ["Mobilfunk-Monitor laden", "Zellen-Datenbank öffnen",
           "IMSI-Catcher-Detektor initialisieren"],
    "49": ["Labor-Einrichtung laden", "50 Toolchain-Profile lesen",
           "Installations-Status prüfen"],
    "50": ["Deep-Forensik laden", "Timeline-Engine initialisieren",
           "Geo-Map-Modul starten", "Radio-History-Parser bereit"],
    "51": ["Telefon-OSINT laden", "Carrier-Lookup-API initialisieren",
           "Reputation-Datenbank öffnen", "Social-Media-Suche bereit"],
    "52": ["Google-Konten-Scanner laden", "dumpsys-Parser initialisieren",
           "10 FRP-Methoden vorbereiten", "SQLite-Forensik-Kanal öffnen"],
    "53": ["Konto-Scanner laden", "Samsung/Microsoft/Social APIs",
           "30 Konto-Typen registrieren", "Deep-Scan-Engine bereit"],
    "54": ["FRP-Scanner laden", "10 Erkennungsmethoden initialisieren",
           "Settings-Secure-Kanal öffnen", "FRP-Partition-Reader bereit"],
    "55": ["SIM-Toolkit laden", "35 Kategorien · 350 Features initialisieren",
           "SIM-Modell-Datenbank öffnen (1FF–5FF · eSIM-Chips · Test-SIMs)",
           "ADB SIM-Subsystem-Kanal öffnen", "IMSI-Catcher-Detektor bereit"],
}

DEFAULT_STEPS = ["Modul laden", "Initialisieren", "Starten"]


def get_steps(choice: str) -> list[str]:
    """Gibt die Initialisierungs-Schritte für einen Menü-Eintrag zurück."""
    return MODULE_INIT_STEPS.get(choice, DEFAULT_STEPS)
