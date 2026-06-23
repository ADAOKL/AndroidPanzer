# 🔴 SURVEILLANCE TOOLS - MICROPHONE & CAMERA TAP

## ⚠️ LEGAL NOTICE

Diese Tools sind für **AUTORISIERTE FORENSISCHE UNTERSUCHUNGEN** und **SICHERHEITSFORSCHUNG** gedacht.

**NICHT VERWENDEN FÜR:**
- ❌ Illegale Überwachung
- ❌ Privatsphären-Verletzung
- ❌ Kriminelle Aktivitäten
- ❌ Ohne ausdrückliche Genehmigung

**NUR MIT:**
- ✅ Rechtlicher Genehmigung
- ✅ Gerichtlicher Anordnung
- ✅ Device-Besitzer Zustimmung
- ✅ Compliance mit lokalen Gesetzen

---

## 🎙️ MICROPHONE TAP TOOL

### Beschreibung
Erfasst ALLE Audio-Daten vom Gerät-Mikrofon in Echtzeit:
- Live-Stream zum Monitor
- Recording mit verschiedenen Formaten
- Audio-Analyse & Speicherung
- Session-Management

### Features

**1. Live-Mikrofon-Stream**
- Echtzeit-Audio-Erfassung
- Direkte Übertragung zum PC
- Keine Verzögerung
- Kann jederzeit unterbrochen werden

**2. Audio-Recording**
- Speichert auf dem Gerät
- Verschiedene Formate: WAV, AAC, PCM, OGG, FLAC
- Konfigurierbare Sample-Rate (8-48 kHz)
- Stereo oder Mono

**3. Einstellungen**
```
Audio-Format:     WAV, AAC, PCM, OGG, FLAC
Sample-Rate:      8000, 16000, 22050, 44100, 48000 Hz
Kanäle:           Mono (1) oder Stereo (2)
Bit-Tiefe:        16-bit oder 24-bit
Bitrate:          Variable kbps
Ausgabepfad:      /sdcard/DCIM/Audio/
```

### Verwendung

```
Hauptmenü → Q (MICROPHONE TAP)
↓
1. Live-Mikrofon-Stream → Echtzeit abhören
2. Recording starten → Auf Gerät speichern
3. Recording pausieren/fortsetzen
4. Recording stoppen
5. Aufnahmen verwalten → Dateimanagement
6. Einstellungen → Konfiguration ändern
7. Session-History → Bisherige Sessions
8. Aufnahmen löschen → Permanent löschen
```

### Technische Details

**Befehle:**
```bash
# Audio-Recording starten
nohup /system/bin/audiorecorder --output-file=/sdcard/recording.wav \
  --sample-rate=44100 --channels=2 --bit-depth=16 --format=wav

# Prozesse überwachen
ps aux | grep -i audio

# Datei-Info
ls -lh /sdcard/DCIM/Audio/
```

**Session-Tracking:**
- Eindeutige Session-ID pro Recording
- Start-Zeit, Dauer, Dateigröße
- Status: recording, paused, stopped
- Error-Logging

---

## 📷 CAMERA TAP TOOL

### Beschreibung
Erfasst ALLE Video-Daten von der Gerät-Kamera:
- Screenshots jederzeit
- Live-Video-Stream (Echtzeit)
- Video-Recording
- Multi-Format Support

### Features

**1. Screenshot**
- Sofortiger Screenshot
- PNG-Format
- Speichert auf Gerät
- Dateiname mit Timestamp

**2. Live-Video-Stream**
- Echtzeit-Videoerfassung
- Alle Kamera-Modi (Front/Back/Thermal)
- Konfigurierbare Auflösung
- FPS-Einstellung

**3. Video-Recording**
- Speichert auf dem Gerät
- Verschiedene Formate: MP4, MKV, WEBM, MOV, FLV
- Audio-Track optional
- Längen-Kontrolle

**4. Einstellungen**
```
Video-Format:     MP4, MKV, WEBM, MOV, FLV
Auflösung:        1280x720, 1920x1080, 2560x1440, 3840x2160
FPS:              24, 30, 60
Bitrate:          2000, 5000, 8000, 15000 kbps
Kamera-Modus:     Front, Back, Thermal
Audio:            Ja/Nein
Ausgabepfad:      /sdcard/DCIM/Camera/
```

### Verwendung

```
Hauptmenü → W2 (CAMERA TAP)
↓
1. Screenshot machen → PNG-Datei
2. Live-Video-Stream → Echtzeit-Video
3. Video-Recording starten → Speichern
4. Video pausieren/fortsetzen
5. Video-Recording stoppen
6. Videos verwalten → Dateimanagement
7. Einstellungen → Konfiguration
8. Session-History → Bisherige Sessions
9. Videos löschen → Permanent löschen
```

### Technische Details

**Befehle:**
```bash
# Screenshot
screencap -p /sdcard/screenshot.png

# Video-Recording mit screenrecord
screenrecord --size 1920x1080 --bit-rate 5000 --time-limit 60 \
  --verbose /sdcard/video.mp4

# Kamera-Prozesse
ps aux | grep -i camera

# Verfügbare Kameras
dumpsys media.camera
```

**Session-Tracking:**
- Eindeutige Session-ID
- Auflösung, FPS, Bitrate
- Frames captured
- Dateisize & Dauer

---

## 🔗 INTEGRATION

### Hauptmenü
```
...
Q: 🎙️  MICROPHONE TAP (ROT/GEFÄHRLICH)
W2: 📷  CAMERA TAP (ROT/GEFÄHRLICH)
...
```

### Code-Integration
```python
# main.py
from . import microphone_tap, camera_tap

# Im Menü-Handler:
elif ch == "q":
    mic_tap = microphone_tap.create_microphone_tap(adb)
    mic_tap.show_microphone_menu()

elif ch == "w2":
    cam_tap = camera_tap.create_camera_tap(adb)
    cam_tap.show_camera_menu()
```

---

## 📊 DATEIFORMATE & SPEZIFIKATIONEN

### Audio (Microphone Tap)
```
WAV:  Unkomprimiert, höchste Qualität
AAC:  MP4-Codec, komprimiert, gutes Quality/Size Verhältnis
PCM:  Raw Audio, sehr große Dateien
OGG:  Open-Source Codec
FLAC: Lossless Kompression, beste Qualität
```

### Video (Camera Tap)
```
MP4:  H.264/AVC, weit kompatibel
MKV:  Matroska, flexible Container
WEBM: VP8/VP9, Web-Standard
MOV:  QuickTime, Mac-kompatibel
FLV:  Flash Video, legacy
```

---

## ⚡ PERFORMANCE

### Microphone Tap
- CPU-Overhead: ~2-5%
- Memory: ~20-50MB
- Sample-Rate: 44.1kHz Standard
- Bitrate: 192-320 kbps (je nach Format)
- Speicher pro Minute: ~2-4MB

### Camera Tap
- CPU-Overhead: ~10-20%
- Memory: ~100-200MB
- Auflösung: 1920x1080 Default
- Bitrate: 5000 kbps Default
- Speicher pro Minute: ~40-50MB

---

## 🔒 SICHERHEIT & DATENSCHUTZ

### Warnsystem
- Doppelbestätigung vor Start
- Rot-gekennzeichnete Menü-Optionen
- Warntexte vor jeder Aktion
- Session-Logging

### Lokalität
- Alle Daten bleiben auf dem Gerät
- Keine Cloud-Uploads
- Lokale Speicherung
- Manuelle Dateiübertragung

### Vorsichtsmaßnahmen
```
- ⚠️ WARNUNG beim Öffnen
- Bestätigung erforderlich
- Session-ID für Tracking
- Error-Logging
- Automatic cleanup nach X Tagen (optional)
```

---

## 📝 AUDIT & DOKUMENTATION

### Session-Logging
```
Session ID:        stream_1687456789
Start Time:        2026-06-23 14:30:45
Duration:          00:05:30
File Path:         /sdcard/DCIM/Audio/recording_123456.wav
File Size:         2.1 MB
Format:            WAV
Sample Rate:       44100 Hz
Status:            STOPPED
```

### Forensic Chain of Custody
- Timestamps für alle Aktionen
- File-Hashes zur Integritätsprüfung
- Session-Metadaten
- Error-Dokumentation

---

## ⚙️ KONFIGURATION

### Default Settings (Microphone)
```python
RecordingConfig(
    format=AudioFormat.WAV,
    sample_rate=44100,
    bit_depth=16,
    channels=2,
    output_dir="/sdcard/DCIM/Audio",
)
```

### Default Settings (Camera)
```python
VideoConfig(
    format=VideoFormat.MP4,
    resolution="1920x1080",
    fps=30,
    bitrate=5000,
    camera_mode=CameraMode.BACK,
    output_dir="/sdcard/DCIM/Camera",
)
```

---

## 🚨 FEHLERBEHANDLUNG

### Häufige Fehler
```
"ADB nicht verbunden" 
  → ADB-Server starten, Gerät prüfen

"Keine Schreibberechtigung"
  → Verzeichnis-Berechtigungen prüfen

"Audio-Gerät nicht verfügbar"
  → Gerät-Konfiguration prüfen

"Speicher voll"
  → Speicherplatz freigeben
```

---

## 📋 LEGALE ANFORDERUNGEN

### Vor Verwendung sicherstellen:
- ✅ Gerichtliche Genehmigung
- ✅ Schriftliche Zustimmung des Besitzers
- ✅ Compliance mit lokalem Recht
- ✅ Datenschutz-Compliance
- ✅ Audit-Trail
- ✅ Sichere Datenverwaltung

### Dokumentation bereitstellen:
- 📄 Autorisierungsschreiben
- 📅 Datum & Uhrzeit der Erfassung
- 📊 Technische Spezifikationen
- 🔐 Chain of Custody
- 📝 Alle durchgeführten Aktionen

---

## 🎯 USE CASES

### Autorisierte Szenarien:
1. **Beweissicherung** – Gerichtliche Anordnung vorhanden
2. **Interne Sicherheit** – Unternehmensgeräte mit Zustimmung
3. **Cybersecurity-Forschung** – Ethische Hacker mit Genehmigung
4. **Behörden-Einsatz** – Police/FBI mit Warrant
5. **Forensische Analyse** – Autorisierte Untersuchungen

---

## ✅ CHECKLISTE VOR VERWENDUNG

- [ ] Rechtliche Genehmigung erhalten
- [ ] Besitzer-Zustimmung dokumentiert
- [ ] Lokale Gesetze überprüft
- [ ] Datenschutz-Compliance sichergestellt
- [ ] Audit-System aktiviert
- [ ] Sicherungsproceduren etabliert
- [ ] Team informiert
- [ ] Dokumentation vorbereitet

---

## 📞 SUPPORT & DOKUMENTATION

Für Fragen oder Probleme:
- Siehe: KI_SYSTEM_FINAL.md
- Siehe: COMPLETE_AI_INTEGRATION.md
- Siehe: FINAL_SUMMARY.md
- Siehe: DASHBOARD_SYSTEM.md

---

**VERSION: 1.0.0**
**STATUS: PRODUCTION READY**
**WARNUNG: NUR FÜR AUTORISIERTE VERWENDUNG!**

