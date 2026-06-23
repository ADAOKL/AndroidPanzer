# 🌐 3D WiFi ROOM SCANNER - TECHNISCHE ERKLÄRUNG

**Frage:** "Kann man Raum in 3D analysieren mit WiFi Frequenzen?"  
**Antwort:** ✅ **JA! Mit Trilateration, RSSI-Mapping und CSI-Analyse!**

---

## 🎯 KERNKONZEPT - WIE ES FUNKTIONIERT

### 1️⃣ **TRILATERATION** (Grundprinzip)

```
3 oder mehr Access Points + Signal-Stärke = Position

     AP1 (0, 0, 2m)          Signal: -45 dBm
            ◆                    ↓
        ╱   ╲                Entfernung: ~5m
       ╱  X  ╲               (berechnet)
      ╱       ╲
     ◆         ◆            AP2: -50 dBm → 7m
    AP2        AP3           AP3: -55 dBm → 8m

Position X (3.2, 4.1, 1.7) = Schnittmenge der 3 Kreise!
```

### FORMEL - PFADVERLUST MODELL (Path Loss)

```
RSSI[dBm] = TX_POWER[dBm] - PATH_LOSS[dB]

PATH_LOSS[dB] = PL0 + 10·n·log₁₀(d)

Wobei:
  PL0 = Referenzdämpfung bei 1m
  n = Pfadverlust-Exponent (typisch 2.0-4.0)
  d = Entfernung in Metern

Beispiel:
  RSSI = -40 dBm (Referenz @1m)
  Signal gemessen = -60 dBm
  
  -60 = -40 - 20·log₁₀(d)
  -20 = -20·log₁₀(d)
  d = 10^1 = 10 Meter
```

---

## 📡 SIGNAL-TYPEN FÜR RAUMANALYSE

### RSSI (Received Signal Strength Indicator)
```
Einfach & Standard:
  ✓ Alle WiFi-Geräte unterstützen
  ✓ -30 dBm = Sehr nah (< 1m)
  ✓ -50 dBm = Nah (3-5m)
  ✓ -70 dBm = Mittel (10-15m)
  ✓ -100 dBm = Weit/schwach

Praktisch:
  Android ADB: adb shell dumpsys wifi
  Liest RSSI für alle APs
  Update-Frequenz: ~1-2 Sekunden
```

### CSI (Channel State Information)
```
Advanced - mehr Details:
  ✓ MIMO Subcarrier-Information
  ✓ Phase-Information (Winkel)
  ✓ Amplituden aller Subcarrier
  ✓ Multipath-Propagation sichtbar
  ✓ Noch bessere Positionierung

Verfügbarkeit:
  ✓ Intel WiFi (Linux)
  ✓ MediaTek Chips (einige Android)
  ✓ Breitcom Chips (schwierig)
  
Genauigkeit: 0.5-2 Meter (vs 3-5m bei RSSI)
```

---

## 🔬 TRILATERATION ALGORITHM

### Schritt 1: Entfernungen berechnen (RSSI → m)

```python
def rssi_to_distance(rssi, freq):
    """RSSI in Entfernung umrechnen."""
    
    if freq < 2500:  # 2.4 GHz
        PL0 = -40  # dBm @ 1m
    else:  # 5 GHz
        PL0 = -30
    
    # Pfadverlust Modell
    path_loss = rssi - PL0
    exponent = 2.0  # Free space
    
    # Entfernung in Metern
    distance = 10 ** (path_loss / (10 * exponent))
    return distance
```

### Schritt 2: Trilateration (3+ Kreise schneiden)

```python
def trilaterate_3d(ap1, ap2, ap3, d1, d2, d3):
    """
    3 APs mit Entfernungen → 3D Position
    
    AP = (x, y, z)
    d = Entfernung zu AP
    
    Löse 3 Gleichungen:
      (x - AP1.x)² + (y - AP1.y)² + (z - AP1.z)² = d1²
      (x - AP2.x)² + (y - AP2.y)² + (z - AP2.z)² = d2²
      (x - AP3.x)² + (y - AP3.y)² + (z - AP3.z)² = d3²
    """
    
    # Numerisch lösen (Least Squares)
    position = solve_least_squares(
        ap1, ap2, ap3,
        d1, d2, d3
    )
    
    return position  # (x, y, z)
```

### Schritt 3: Mehrere Samples mitteln (Kalman-Filter)

```python
def kalman_filter_position(measurements):
    """
    Mehrere Messungen → geglättete Trajectory
    
    Messung 1: (3.1, 4.0, 1.7) ± 0.5m
    Messung 2: (3.2, 4.1, 1.7) ± 0.5m
    Messung 3: (3.3, 4.2, 1.7) ± 0.5m
    
    Mit Kalman-Filter:
    Gefilterte 1: (3.10, 4.00, 1.70) ± 0.3m (besser!)
    Gefilterte 2: (3.20, 4.10, 1.70) ± 0.3m
    Gefilterte 3: (3.30, 4.20, 1.70) ± 0.3m
    """
    
    filtered = []
    for measurement in measurements:
        prediction = predict_next_position()
        filtered_pos = kalman_update(prediction, measurement)
        filtered.append(filtered_pos)
    
    return filtered  # Glatte Kurve
```

---

## 🗺️ RAUM-REKONSTRUKTION

### Wall Detection (Wand-Erkennung)

```
Signal-Reflexionen deuten auf Wände hin!

Freiraum (Free Space):
  RSSI = -40 - 20·log₁₀(d)
  Vorhersehbar

Mit Wand (1 Reflection):
  RSSI = -40 - 20·log₁₀(d) - WALL_ATT
  
  Drywall: -5 dB
  Brick: -10 dB
  Concrete: -15 dB
  Metal: -30 dB
```

### Algorithmus:

```python
def detect_walls():
    """Erkenne Wände durch Signal-Anomalien."""
    
    wall_locations = []
    
    for direction in [0, 90, 180, 270]:  # 4 Richtungen
        baseline = measure_signal_at_direction(direction, 1m)
        
        for distance in range(2, 10):
            signal = measure_signal_at_direction(direction, distance)
            
            expected = baseline - 20 * log10(distance)
            actual = signal
            
            # Signal schlechter als erwartet?
            if (actual - expected) < -5:
                # WAHRSCHEINLICH WAND!
                wall_locations.append({
                    "direction": direction,
                    "distance": distance,
                    "attenuation": expected - actual,
                })
    
    return wall_locations
```

### Raumgröße bestimmen:

```python
def estimate_room_dimensions(wall_locations):
    """Aus Wand-Positionen → Raum-Größe."""
    
    # Finde min/max Entfernungen pro Richtung
    north_wall = min(w["distance"] for w in wall_locations if w["direction"] == 0)
    east_wall = min(w["distance"] for w in wall_locations if w["direction"] == 90)
    south_wall = min(w["distance"] for w in wall_locations if w["direction"] == 180)
    west_wall = min(w["distance"] for w in wall_locations if w["direction"] == 270)
    
    # Breite & Tiefe
    width = east_wall + west_wall
    depth = north_wall + south_wall
    
    # Höhe: Aus Decken-Reflexion (CSI nutzen)
    # Oder: Typische 2.5-3.0m annehmen
    height = 3.0
    
    return {
        "width": width,
        "depth": depth,
        "height": height,
        "volume": width * depth * height,
    }
```

---

## 🎯 ADVANCED FEATURES - BEWEGUNGSTRACKING

### Menschen-Erkennung

```
CSI (Channel State Information) zeigt:
  ✓ Person bewegt sich → Phase ändert sich
  ✓ Mehrere Personen → Multipath verstärkt
  ✓ Atmung erkennbar → periodische CSI-Schwankung

Algorithmus:
  1. CSI kontinuierlich lesen
  2. FFT-Analyse (Frequency Domain)
  3. Peak bei 0.3-0.5 Hz → Atmung
  4. Peak bei 0.5-5 Hz → Bewegung
```

### Geste-Erkennung

```
WiFi-basiertes Gesture Recognition:

  WIFI Signal
      ▲
      │  ╱╲      ← Welle ändert sich
      │╱  ╲
      │    ╲╱
      └─────────► Zeit

  Muster:
    Welle links → Mensch hebt rechte Hand
    Welle rechts → Mensch hebt linke Hand
    Schnelle Änderung → Schnelle Bewegung
```

---

## 📊 GENAUIGKEIT & LIMITIERUNGEN

```
METHOD               GENAUIGKEIT    KOSTEN    HINDERNIS
─────────────────────────────────────────────────────────
RSSI (3 APs)        3-5 Meter      €0        Einfach
RSSI + Filter       2-3 Meter      €0        Gut
CSI (Intel)         0.5-1 Meter    €0*       Sehr gut
CSI (MediaTek)      1-2 Meter      €0*       Mittel
Fingerprinting      0.5-1 Meter    €(DB)     Braucht Kalibrierung
Sensor Fusion       0.5 Meter      €0        Am besten

* = Nicht alle Geräte unterstützen CSI
```

---

## 🔧 PRAKTISCHE IMPLEMENTIERUNG - ANDROID

### ADB-Befehle für WiFi-Daten:

```bash
# RSSI aller APs
adb shell dumpsys wifi | grep "SSID\|rssi"

# Detaillierte WiFi-Info
adb shell iw dev wlan0 link

# Scan mit RSSI
adb shell "iw event" | grep "new station"

# CSI-Dump (wenn verfügbar)
adb shell cat /sys/kernel/debug/ieee80211/phy0/netdev:wlan0/csi
```

### Python-Code Integration:

```python
class WiFi3DScanner:
    
    def read_rssi_from_adb(self):
        """Lese WiFi Signal-Stärken vom Gerät."""
        output = self.adb.shell("dumpsys wifi")
        
        aps = {}
        for line in output.split("\n"):
            if "SSID:" in line:
                ssid = line.split("SSID: ")[1]
            if "rssi" in line:
                rssi = int(line.split("rssi:")[1].split()[0])
                aps[ssid] = rssi
        
        return aps
    
    def calculate_positions(self, ap_rssi):
        """RSSI → Positionen via Trilateration."""
        
        # Kalibrierte AP-Positionen
        aps = [
            {"name": "AP1", "pos": (0, 0, 2)},
            {"name": "AP2", "pos": (6.5, 0, 2)},
            {"name": "AP3", "pos": (3.2, 8.2, 2)},
        ]
        
        # RSSI → Entfernung
        distances = []
        for ap in aps:
            rssi = ap_rssi.get(ap["name"], -100)
            dist = self.rssi_to_distance(rssi)
            distances.append(dist)
        
        # Trilateration
        position = self.trilaterate_3d(aps, distances)
        
        return position  # (x, y, z, confidence)
```

---

## 🚀 VERWENDUNG IM TOOL

```
Hauptmenü
  └─ W3D (3D WiFi Room Scanner)
     ├─ 1. WiFi APs scannen
     ├─ 2. AP-Positionen kalibrieren (Schritt 1: Wichtig!)
     ├─ 3. 3D-Raumanalyse starten
     ├─ 4. Trilateration & Positionierung
     ├─ 5. 3D-Raummodell anzeigen
     ├─ 6. Live-Bewegungstracking
     ├─ 7. Signal-Heatmap generieren
     ├─ 8. Raum-Charakteristiken analysieren
     └─ 9. Forensischen Raum-Report
```

---

## 💡 PRAKTISCHE ANWENDUNGEN

### Szenario 1: Forensische Raumrekonstruktion
```
Fall: Einbruch mit Gewalt
Frage: Wo war der Täter im Raum?

Methode:
  1. 3 WiFi APs in den Raum bringen
  2. Historisches WiFi-Log von Sicherheitskamera auslesen
  3. Camera zeigt Täter-Position alle 1s
  4. WiFi-Signale von dieser Zeit auslesen
  5. Trilateration durchführen
  6. 3D-Trajectory des Täters rekonstruieren
  
Genauigkeit: ±1-2 Meter (gut für Forensik)
```

### Szenario 2: Aktivitäts-Überwachung
```
Wohnung mit verstecktem Täter?

Echtzeit-Tracking:
  ✓ WiFi-Signal kontinuierlich messen
  ✓ Position alle 0.5 Sekunden berechnen
  ✓ Atemmuster erkannt (CSI)
  ✓ Gesten erkannt (CSI)
  ✓ Bestätigt: Person im Raum!
  
Alert: "Person erkannt im Schlafzimmer"
```

### Szenario 3: Raum-Kartographie
```
Neuer Tatort - Raum unbekannt

WiFi-Scanner:
  ✓ 3 APs positioniert
  ✓ Wand-Detektion durchgeführt
  ✓ Raum-Größe: 6.5m x 8.2m x 3.0m
  ✓ Material: Drywall (S), Brick (W), Concrete (O)
  ✓ Fenster erkannt (wenig Reflexion)
  ✓ Metall-Objekt erkannt (starke Reflexion)
  
Report: "Rechteckiger Raum, ~50m², Möbel-Hindernisse"
```

---

## ✅ ZUSAMMENFASSUNG

```
3D WiFi ROOM SCANNER:

✓ Nutzt Standard-WiFi Signal-Messungen
✓ RSSI = Entfernung (Path Loss Modell)
✓ 3+ APs = Trilateration in 3D
✓ Wall Detection via Signal-Anomalien
✓ Room Size aus Wand-Positionen
✓ Movement Tracking mit CSI (optional)
✓ Genauigkeit: 1-3 Meter (realistisch)

FORENSISCHE ANWENDUNGEN:
  • Täter-Position rekonstruieren
  • Bewegungsmuster analysieren
  • Versteckte Personen finden
  • Raumgeometrie kartographieren
  • Aktivitäts-Timeline erstellen

→ PROFESSIONELLES WERKZEUG FÜR FORENSISCHE ANALYSE!
```

---

**🎉 3D WiFi Room Scanner ist ein revolutionäres Werkzeug für Raumanalyse & Forensik!**

