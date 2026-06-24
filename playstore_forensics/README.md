# playstore_forensics

Forensisches Analyse-Modul für Play-Store-Artefakte auf Android-Geräten.
Bestandteil von **AndroidPanzer** (Option 57 im Hauptmenü).

## Was es tut

| Funktion | Quelle | Root? |
|---|---|---|
| Installations-Historie | `frosting.db` / `dumpsys package` | optional |
| Suchverlauf | `suggestions.db` | erforderlich |
| App-Nutzungszeiten | `usagestats` XML | nein |
| APK-Tiefenanalyse | `aapt`/`strings`/`grep` on-device | nein |
| Permission-Matrix + AppOps | `dumpsys appops` | nein |
| Netzwerk-Forensik | `/proc/net`, `logcat`, `netstats` | optional |
| WAL/Journal-Recovery | SQLite WAL-Frames on-device | erforderlich |
| Slack-Space-Recovery | SQLite Freelist-Pages | erforderlich |
| Chain of Custody | SHA-256 + Autorisierungs-Log | — |

## Voraussetzungen

| Anforderung | Details |
|---|---|
| Python | **≥ 3.10** (Union-Types `\|`, `match`-Statements) |
| ADB | Im PATH (`adb devices` muss Gerät zeigen) |
| Android | **≥ 8.0 (API 26)** – `usagestats` XML-Format |
| Root (optional) | Magisk / KernelSU für `frosting.db`, WAL-Recovery, `suggestions.db` |
| `aapt`/`aapt2` | Auf dem Gerät (für APK-Manifest-Parser, Fallback: `grep`) |

## Unterstützte Geräte

- Alle Android 8.0–14 Geräte
- Samsung OneUI: `frosting.db` liegt unter `/data/data/com.android.vending/databases/`
- AOSP / Pixel: identische Pfade
- Android 12+: `usagestats` unter `/data/system/usagestats/` (Root nötig für direkten Zugriff)

## Verwendung

### Als AndroidPanzer-Modul (empfohlen)

```bash
python3 panzer.py
# → Option 57: PLAY STORE FORENSICS
```

### Als eigenständiges CLI

```bash
# Demo (kein Gerät nötig)
python3 -m playstore_forensics --demo

# Vollscan auf verbundenem Gerät
python3 -m playstore_forensics --full

# Nur Installations-Historie
python3 -m playstore_forensics --installs

# Ausgabe-Verzeichnis
python3 -m playstore_forensics --full --out /tmp/psf_output
```

### Als Python-Modul

```python
from playstore_forensics import menu, full_scan
from apz.adb import ADB

adb = ADB()
dev = adb.list_devices()[0]
st = {"is_root": adb.check_root()}

# Interaktives Menü
menu(adb, dev, st)

# Automatischer Vollscan
full_scan(adb, dev, st)
```

## Output-Dateien

Alle Ausgaben landen in `~/forensik/playstore/` (konfigurierbar via `config.py`):

| Datei | Inhalt |
|---|---|
| `psf_report_*.txt` | Vollständiger Textbericht |
| `psf_report_*.json` | Maschinenlesbar, verlustfreier Roundtrip via `ForensicReport.from_dict()` |
| `psf_timeline_*.txt` | Chronologische Ereignis-Timeline |
| `psf_anomalies_*.txt` | Anomalien (SIDELOAD, SUSPICIOUS_SEARCH, NIGHTTIME_ACTIVITY …) |
| `install_history.txt` | Reine Installations-Liste |
| `apk_deep_scan.txt` | APK-Tiefen-Ergebnisse (HIGH/CRITICAL) |
| `network_forensics.json` | Verbindungen, DNS, Anomalien |
| `permission_matrix.txt` | Per-App Permission-Scoring |
| `checkpoint_YYYYMMDD.json` | Checkpoint für Resume nach Abbruch |

Auth-Logs (ISO 27037): `~/.config/android-panzer/psf_auth_logs/auth_*.json`

## Rechtlicher Hinweis

Jeder Zugriff auf fremde Gerätedaten ist in Deutschland strafbar
(§§ 202a, 303a StGB). Das Modul verlangt beim Start eine explizite
Autorisierungs-Bestätigung und persistiert diese als JSON-Log.

Legitime Szenarien: eigenes Gerät, schriftliche Einwilligung,
behördlicher Auftrag, BYOD-Firmen-Audit.

## Architektur

```
playstore_forensics/
├── __init__.py          # Package-Bootstrap (sys.path, exports)
├── config.py            # Pfade, Konstanten, Known-Stores
├── models.py            # Dataclasses + BaseApkResult Protocol
├── parsers.py           # SQLite-Output → Dataclass (text-basiert)
├── extractor.py         # ADB-Extraktion → models
├── analyzer.py          # Anomalie-Engine + Statistiken
├── output.py            # Text/JSON/Timeline-Ausgabe
├── security.py          # Auth-Gate + Audit-Log (ISO 27037)
├── utils.py             # ADB-Dateizugriff, Timestamps, SQLite-Helper
├── apk_deep_scanner.py  # On-Device APK-Analyse (aapt + strings)
├── permission_matrix.py # AppOps + Permission-Scoring
├── network_forensics.py # /proc/net, logcat, netstats
├── wal_recovery.py      # WAL-Frame + Journal-Parser
├── slack_recovery.py    # SQLite Freelist-Recovery
├── main.py              # Menü-Integration + full_scan()
└── __main__.py          # Standalone CLI
```
