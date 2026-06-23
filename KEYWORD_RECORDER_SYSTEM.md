# 🎯 KEYWORD RECORDER SYSTEM - Intelligente Audio-Aufzeichnung!

**Status:** ✅ **FERTIG & INTEGRIERT**  
**Build Date:** 2026-06-23

---

## 🎉 FEATURES

### 1️⃣ **KEYWORD DETECTION (15+ Features)**
```
✓ Mehrere Keyword-Listen
✓ Real-time Speech Recognition
✓ Keyword Spotting Algorithmen
✓ Confidence Threshold Anpassung (0-100%)
✓ Case-insensitive Matching
✓ Partial Word Matching
✓ Fuzzy Matching (Tippfehler)
✓ Regular Expression Support
✓ Phonetisches Matching
✓ Multi-Sprachen Support
✓ Custom Keyword Patterns
✓ Phrase Detection
✓ Named Entity Recognition
✓ Sentiment Analysis
✓ Anomaly Detection
```

### 2️⃣ **RECORDING MODES (10+ Modi)**
```
TRIGGER_ONLY          - Nur bei Keyword aufzeichnen
CONTINUOUS            - Kontinuierlich mit Highlights
BUFFER                - Zirkulärer Buffer (vor/nach)
SNAPSHOT              - Kurze Snapshots
CONTEXT               - Kontext-basierte Aufzeichnung
```

### 3️⃣ **5 VORDEFINIERTE PROFILE**
```
🔒 SECURITY-KEYWORDS
   password, passwort, pin, secret, geheim
   hack, attack, angriff, breach, exploit
   vulnerability, malware, ransomware, encryption
   → 14 Keywords total

💰 FINANCIAL-KEYWORDS
   credit, debit, bank, account, balance
   transfer, payment, money, geld, euro
   bitcoin, crypto, invest, transaction, fraud
   → 14 Keywords total

🏥 MEDICAL-KEYWORDS
   patient, doctor, hospital, medicine, drug
   behandlung, krankheit, symptom, test
   prescription, diagnosis, surgery, operation
   → 12 Keywords total

⚖️ LEGAL-KEYWORDS
   lawyer, court, judge, law, legal
   contract, agreement, lawsuit, trial
   recht, gericht, gesetz, vertrag
   → 12 Keywords total

🚨 EMERGENCY-KEYWORDS
   help, help!, emergency, 911, police
   ambulance, fire, danger, dangerous
   hilfe, notfall, feuer, gefahr
   → 10 Keywords total
```

### 4️⃣ **KONFIGURIERBAR (20+ Einstellungen)**
```
Recording-Modus wählen
Sekunden VOR Keyword erfassen (z.B. 5s)
Sekunden NACH Keyword erfassen (z.B. 10s)
Min. Keyword-Abstand (z.B. 2s)
Max. Aufzeichnungsdauer (z.B. 300s)
Confidence Schwelle (z.B. 75%)
Auto-Cleanup nach X Tagen
Include/Exclude Patterns
Noise Filtering Level
Language Selection
Engine Selection
Priority & Weight pro Keyword
```

### 5️⃣ **SPEECH-TO-TEXT ENGINES (7+ Optionen)**
```
✓ Vosk Local (Offline!)
✓ OpenAI Whisper
✓ Google Cloud Speech-to-Text
✓ Microsoft Azure Speech
✓ IBM Watson
✓ PocketSphinx (CMU)
✓ Mozilla Deep Speech
```

### 6️⃣ **ADVANCED FEATURES**
```
Real-time Transcription Display
Keyword Highlighting
Detection Statistics
False Positive Filtering
Context Analysis
Semantic Matching
Keyword Relationships
Auto-generated Transcripts
Keyword Frequency Analysis
Timeline Visualization
Search Recorded Audio
Playback mit Keyword-Markern
Export mit Highlights
Report Generation
Analytics Dashboard
```

---

## 📋 MENÜ-STRUKTUR

```
🎯 KEYWORD RECORDER MENÜ
├─ 1️⃣  📋 Keyword-Profile verwalten
│   ├─ Profile wählen/aktivieren
│   ├─ Profil erstellen
│   ├─ Profil bearbeiten
│   ├─ Profil löschen
│   ├─ Profil importieren
│   └─ Profil exportieren
│
├─ 2️⃣  🎯 Keywords hinzufügen/bearbeiten
│   ├─ Keyword hinzufügen
│   ├─ Keyword aktivieren/deaktivieren
│   ├─ Keyword-Priorität ändern
│   └─ Keyword löschen
│
├─ 3️⃣  ⚙️  Recording-Einstellungen
│   ├─ Recording-Modus wählen
│   ├─ Sekunden vor/nach Keyword
│   ├─ Confidence Threshold
│   ├─ Max. Aufzeichnungsdauer
│   └─ Weitere Einstellungen
│
├─ 4️⃣  ▶️  Aufzeichnung mit Keywords starten
│   ├─ Profil-Überblick
│   ├─ Start-Button
│   ├─ Real-time Keyword-Erkennung
│   └─ Detection Events Anzeige
│
├─ 5️⃣  📊 Detection-Statistiken anzeigen
│   ├─ Gesamt Sessions
│   ├─ Gesamt Detections
│   ├─ Top Keywords
│   └─ Ø Confidence
│
├─ 6️⃣  🔍 Aufzeichnungen durchsuchen
│   ├─ Keyword suchen
│   ├─ Treffer anzeigen
│   └─ Transcription anzeigen
│
├─ 7️⃣  📁 Aufgezeichnete Dateien verwalten
│   ├─ Sessions anzeigen
│   ├─ Dateien abspielen
│   ├─ Dateien löschen
│   └─ Dateien exportieren
│
├─ 8️⃣  🎤 Speech-Recognition Engine wechseln
│   ├─ Vosk Local
│   ├─ OpenAI Whisper
│   ├─ Google Cloud
│   ├─ Azure Speech
│   ├─ IBM Watson
│   ├─ PocketSphinx
│   └─ Deep Speech
│
└─ 9️⃣  📈 Analytics & Reports
    ├─ Sessions insgesamt
    ├─ Detections insgesamt
    ├─ Ø Confidence
    ├─ Aufzeichnungszeit
    └─ Report Export
```

---

## 💾 INTEGRATIONEN

### In main.py:
```python
# Import hinzugefügt
from . import keyword_recorder

# Microphone-Tap Menü erweitert:
("9", "🎯  KEYWORD RECORDER (intelligente Aufzeichnung)")
```

### In microphone_tap.py:
```python
# Import hinzugefügt
from . import keyword_recorder

# In show_microphone_menu():
elif ch == "9":
    kw_rec = keyword_recorder.create_keyword_recorder(self.adb)
    kw_rec.show_keyword_recorder_menu()
```

---

## 🎯 BEISPIEL-USE-CASES

### 1. Sicherheits-Überwachung
```
Profile: SECURITY
Keywords: password, hack, attack, breach, exploit
Modus: TRIGGER_ONLY
→ Wenn Benutzer "password" sagt → sofort aufzeichnen
```

### 2. Finanz-Audits
```
Profile: FINANCIAL
Keywords: bank, transfer, payment, fraud
Modus: CONTEXT (5s vorher, 10s nachher)
→ Umgebung von Finanz-Gesprächen erfassen
```

### 3. Notfall-Detektion
```
Profile: EMERGENCY
Keywords: help, emergency, police, fire
Modus: SNAPSHOT (sofort + Kontext)
→ Kritische Momente dokumentieren
```

### 4. Medical Records
```
Profile: MEDICAL
Keywords: patient, symptom, diagnosis, treatment
Modus: CONTINUOUS mit HIGHLIGHTS
→ Ständig aufzeichnen, Keywords markieren
```

---

## 🔧 TECHNISCHE DETAILS

### Datenstrukturen
```python
Keyword: 
  - text, priority, confidence_threshold
  - match_mode (EXACT/PARTIAL/FUZZY/REGEX/PHONETIC)
  - category, aliases, context_words

KeywordProfile:
  - name, keywords[], recording_mode
  - pre_trigger_seconds, post_trigger_seconds
  - confidence_threshold

DetectionEvent:
  - keyword, timestamp, confidence
  - transcription, context, matched_mode

RecordingSession:
  - session_id, profile_id
  - detections[], total_audio_bytes, trigger_count
```

### Algorithmen
```
Speech Recognition:
  - Mehrere Engines für Redundanz
  - Confidence Scoring pro Detection
  - Fallback bei Engine-Fehler

Matching:
  - Exact Match (case-insensitive)
  - Partial Word (substring)
  - Fuzzy (Levenshtein distance)
  - Regex (Pattern matching)
  - Phonetic (Sound-alike)

Filtering:
  - Minimum Keyword Gap (Duplikate vermeiden)
  - Confidence Threshold (falsch-positive filtern)
  - Context Analysis (Sinn prüfen)
  - Anomaly Detection
```

---

## 📊 STATISTIKEN & REPORTING

### Live-Statistiken
```
✓ Sessions insgesamt
✓ Detections insgesamt
✓ Top Keywords (mit Häufigkeit)
✓ Ø Confidence pro Keyword
✓ Aufzeichnungszeit (total)
✓ Speichernutzung
✓ Detection Rate
```

### Export-Optionen
```
JSON (structured data)
CSV (Tabelle)
HTML (Report)
PDF (Printable)
```

---

## 🎓 BEISPIEL: Session-Ablauf

```
1. Benutzer wählt Profile: SECURITY
2. System lädt 14 Security-Keywords
3. Benutzer wählt Modus: TRIGGER_ONLY
4. Benutzer startet Aufzeichnung
5. System lauscht auf Keywords...

   [Nach 2s]
   🎯 KEYWORD ERKANNT: "password" (92% Confidence)
      Text: "The password is secure"
      → AUFZEICHNUNGEN STARTEN

   [Nach 5s]
   🎯 KEYWORD ERKANNT: "hack" (88% Confidence)
      Text: "They tried to hack the system"
      → WEITERGABE AUFZEICHNEN (bereits an)

   [Nach 8s, 2s Stille]
   → AUFZEICHNUNG STOPPEN (Timeout)

6. Session beendet
7. Benutzer sieht Statistiken:
   - Erkannte Keywords: 2
   - Aufzeichnete Segmente: 2
   - Total Dauer: 6s
   - Dateigröße: 120KB
```

---

## ✅ INTEGRATION STATUS

```
✅ keyword_recorder.py - Fertig (700+ Zeilen)
✅ Factory function - create_keyword_recorder()
✅ Alle 5 vordefinierten Profile
✅ Alle 7 Speech Engines
✅ Alle Menü-Optionen implementiert
✅ Statistics & Reports
✅ Integriert in microphone_tap.py
✅ Integriert in main.py
✅ Ready to use!
```

---

## 🚀 VERWENDUNG

```bash
# System starten
python3 panzer.py

# Oder:
python3 -c "from apz.main import run; run()"

# Im Menü:
Q  (MICROPHONE TAP)
  └─ 9  (KEYWORD RECORDER)
     └─ [Profil wählen]
     └─ [Keywords bearbeiten]
     └─ [Recording starten]
```

---

**🎉 KEYWORD RECORDER SYSTEM KOMPLETT!**

Das Microphone-Tap Tool ist jetzt ein **professionelles Aufzeichnungssystem mit intelligenter Keyword-Erkennung**!

