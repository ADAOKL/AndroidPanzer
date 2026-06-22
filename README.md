# 🛡 ANDROID PANZER

All-in-One Terminal-Tool für Android-**Diagnose, -Steuerung, -Security & -Forensik** über ADB.
Erkennt ein angeschlossenes Gerät automatisch, fasst sofort die wichtigsten Kennzahlen
zusammen und bietet danach ein logisch gegliedertes Menü mit **450 Funktionen in 45 Kategorien**.

```
python3 panzer.py
```

## Voraussetzungen
- **Python 3.8+** (keine externen Pakete nötig – reines Standard-Python)
- **adb** (Android platform-tools) im `PATH`
- Am Gerät: **USB-Debugging** aktiv (Entwickleroptionen) und am PC **autorisiert**
- Optional: **fastboot** (für Bootloader-/Flash-Funktionen), **Root** (für Tiefenzugriff)

## Ablauf
1. **Auto-Erkennung** – wartet aktiv auf ein Gerät, behandelt „unauthorized".
2. **Auto-Analyse / Dashboard** – Hardware, Android/Build, SELinux, Bootloader-Lock,
   Slot A/B, Akku (Bar/Temp/Spannung), RAM, Speicher, Display, Netz, SIM, **Root-Status**.
3. **Hauptmenü**:
   - `K` – Alle 45 Kategorien (die kompletten 450 Funktionen)
   - `R` – **Root-Status & Rooting-Assistent** (prüft Root, schätzt Aufwand/Risiko,
     sammelt modellspezifische Fakten, listet benötigte Dateien und führt – nach
     Bestätigung – den geführten Magisk-Ablauf aus). **Neu – Hintergrund-Vorbereitung:**
     sobald ein Gerät erkannt wird, löst ein Hintergrund-Thread die passenden
     Download-Links auf (Magisk-APK via GitHub, platform-tools, hersteller-spezifische
     Firmware-/boot.img-Quelle) und hält sie bereit. Option `A` (**AUTO-ROOT**) lädt sie
     dann auf Nachfrage (HTTPS + SHA-256), entpackt ZIPs automatisch, installiert die
     Magisk-App, bringt das Gerät – falls nötig – in Fastboot, patcht das boot.img
     on-device und flasht es. Bei **jedem** Schritt stehen die nötigen
     **Konto-/FRP-/Neustart-Hinweise** (Google-/Hersteller-Konto angemeldet lassen vs.
     abmelden, wann gewiped wird, wann neu zu starten ist). Destruktive Schritte nur
     nach ausdrücklicher Bestätigung. Enthält eine
     **Root-/Bootloader-Tiefen-Diagnose** (Option 4) mit 7 read-only Modulen +
     konsolidierter Risiko-Matrix, lückenlos & zeitgestempelt nach `diagnostics/`:
     (1) `ro.boot.*`-Eigenschafts-Matrix, (2) Bootloader-Lock/Knox/AVB,
     (3) Magisk-Architektur (App-UI vs. echtes `su`), (4) dm-verity/Partitions-RW,
     (5) **Persist/Metadata-Integrität** (FRP-Gegenprüfung), (6) **OEM-/Cloud-Sperren**
     (Knox Guard, Mi Cloud, gebundene Konten), (7) **Flash-Geometrie + EFS/IMEI-Schutz**.
     Strikt read-only – führt **keine** FRP-/Partitions-Löschungen oder Sperr-Umgehungen
     aus, sondern liefert nur die Entscheidungsgrundlage (ohne IMEI-/EFS-Risiko).
   - `V` – **VOLLANALYSE**: vollständige forensische Akquise über **45 Sektionen** in
     4 Teilen (OS/Dateisystem/Apps · SIM/eSIM/eUICC · Baseband/Signal/RF ·
     Labor-Exploitation). Jede Sektion trägt einen **ehrlichen Status** – `✅ erhoben`
     (real per ADB), `🟡 eingeschränkt`, `🔑 Root nötig`, `📡 SDR/HW nötig`,
     `🧪 Labor nötig`. Read-only; Hardware-/Labor-Verfahren (SIM-Ki-DPA, IMSI-Catcher,
     Open5GS, TEMPEST, Baseband-Exploits …) werden **dokumentiert, nicht erfunden**.
     Ergebnis ist ein konsolidierter Gesamtbericht (Text/Markdown), der über `E`
     zusätzlich als HTML/JSON + SHA-256-Manifest exportierbar ist.
   - `S` – **Forensischer Deep-Scan**: versteckte Apps, verborgene Launcher-Icons,
     Zweit-/Gast-/Work-Profile, sideloaded Apps, deinstallierte Datenreste,
     Accessibility-/Device-Admin-Rechte, Nutzungs-/Install-Verlauf
   - `F` – **Daten-Forensik & Wiederherstellung**: Konten (auch Spuren gelöschter),
     Anrufliste, SMS, Kontakte, Browser-Verläufe, Social-Media/Messenger, komplettes
     Medien-Inventar (Bilder/Videos/Audio mit Zeitstempeln), Sprachnachrichten,
     Play-Store-Historie, Wiederherstellbarkeits-Check – **alles mit Datum/Uhrzeit**
   - `U` – **App-Inventar · Architektur-/Spyware-Anomalien · Export**: scannt **alle**
     installierten Apps (System + Drittanbieter) in wenigen ADB-Aufrufen, markiert
     auffällige Apps **rot** und nennt dahinter knapp *was* auffällig ist und den
     *Verdacht* (Fremd-CPU-Architektur, sideloaded/DEBUGGABLE/TEST-ONLY, System-Namens-
     Maskerade, aktive Accessibility/Device-Admin/Notification-Listener, Stalkerware-
     Rechte-Kombi, versteckt ohne Launcher-Icon, bekannte Stalkerware). Auswahl je App
     per **Leertaste** (↑/↓, `a` alle, `n` keine, `i` invertieren, `d` Details, `f` nur
     Auffällige), danach **vollständiger Export** der gewählten *oder* aller Apps
     (alle APK-Splits + Metadaten + SHA-256, `_INDEX.tsv` für VirusTotal-Abgleich).
   - `A` – **APK-Analyse · App-Risiko-Inventar · IOC-Scan**: Offline-Statik-Analyse
     gezogener APKs (eigener Binär-AndroidManifest-Parser → Paket/Version/Rechte,
     Signatur, native Libs, DEX-IOC-Strings, SHA-256+VirusTotal-Link),
     risikobewertetes App-Ranking und ein geräteweiter IOC-Sweep
     (hosts-Hijack, Accessibility/Device-Admin/Notification-Listener, Stalkerware)
   - `E` – **Report & Export**: ein einheitlicher Gesamtbericht über *alle* Funde als
     **HTML + Markdown + JSON** plus **SHA-256-Manifest** (mit `sha256sum -c` prüfbar,
     inkl. Integritäts-Verifikation)
   - `Y` – **Automatischer Modus-Wechsel**: bringt das Gerät selbsttätig in den
     benötigten Modus – **Download-Modus** (Samsung Odin/Heimdall), **Fastboot/
     Bootloader**, **Recovery**, **ADB-Sideload** oder zurück ins **System**. Wo
     möglich per `adb reboot <ziel>` / `fastboot reboot` (keine Tastenkombi nötig);
     sonst wird die exakte physische Tastenfolge genannt. In jedem Fall wartet das
     Tool aktiv, bis das Gerät im Zielmodus erkannt wird (statt fester Wartezeit).
     Wird auch in den Root-/Flash-Abläufen automatisch genutzt (z.B. „vor dem
     Flashen automatisch in Fastboot/Download bringen").
   - `J` – **Custom-Firmware/ROMs fürs Gerät anzeigen**: ermittelt anhand des
     Codenamens live, was flashbar ist – **LineageOS** (offizielle Builds via API
     mit Version/Datum/Größe/Download-Link), **TWRP** (alle Versionen) sowie direkte
     Einstiege zu OrangeFox/PixelExperience/crDroid/XDA. Read-only Übersicht, im
     Terminal angezeigt und gespeichert.
   - `L` – Live Mobilfunk-Zellen-/IMSI-Catcher-Monitor
   - `C` – eigenes ADB-Shell-Kommando
   - `X` – **ROOT-ARSENAL** *(erscheint nur, wenn der Erstscan Root erkennt:
     echtes su/Magisk/KernelSU **oder** adb-root/„Fakeroot")* – siehe unten

## 🔓 ROOT-ARSENAL (nur bei erkanntem Root)
Vollständig funktionsfähig, echt – keine Simulation. Vier Bereiche:

**A · Tiefe Daten-Extraktion**
- Komplette App-Daten jeder App (`/data/data/<pkg>` → DBs + shared_prefs als TAR)
- Messenger-Chats (WhatsApp `msgstore.db`, Telegram `cache4.db`, Signal, Messenger, Viber)
- Browser komplett: Verlauf + Downloads + Logins + Autofill (Chromium/Gecko, lokal via `sqlite3`)
- Gespeicherte Logins/Autofill
- **WLAN-Passwörter im Klartext** (`WifiConfigStore.xml` / `wpa_supplicant.conf`)
- **Konten inkl. Residuen GELÖSCHTER/abgemeldeter** (`accounts_ce.db` + Freelist + Logout-Events)
- Zwischenablage- & Benachrichtigungs-Historie (`--noredact`)

**B · Echte Datenwiederherstellung**
- Gelöschte SQLite-Datensätze: `sqlite3 .recover` + **Freelist/Unallocated-String-Carving** + WAL/Journal
- Gelöschte Bilder aus `.thumbnails`
- Papierkorb / `.trashed-*` (Android 11+)
- Gelöschte Chats/SMS aus WAL & Journal carven
- App-Cache-Medien-Carving (Snapchat/Insta-Vorschauen etc.)

**C · Backdoor-/Spyware-/Rootkit-Scan („bd-Scan")**
- SUID/SGID & versteckte `su`-Binaries an ungewöhnlichen Orten
- Persistenz: init.d, post-fs-data.d, Magisk-Module, Xposed/`app_process`-Hijack, BOOT_COMPLETED-Autostarts
- Offene LISTEN-Ports (Reverse-Shell-Indikatoren) + aktive Verbindungen
- Spyware/Stalkerware: Accessibility-Keylogger, Device-Admin, Notification-Listener, Frida/Xposed-Prozesse, Apps mit kritischer Rechte-Kombi (Audio+Standort+SMS+Kontakte) & versteckt
- System-Integrität: `hosts`-Hijack, fremde/neuere System-APKs, SELinux-Permissive, kürzlich geänderte System-Binaries

**D · System & Partitionen**
- Partition als Raw-Image (`dd`) sichern & ziehen
- NVRAM/EFS-Backup (IMEI/Funk-Kalibrierung)
- Komplettes `/data` als TAR
- `/system` RW mounten

## Funktions-Kennzeichnung (ehrlich, kein Fake)
| Badge | Bedeutung |
|-------|-----------|
| `[ADB]`     | direkt über ADB ausführbar |
| `[LIVE]`    | interaktiv / Live-Stream |
| `[ROOT]`    | benötigt Root (su) – Fallback wird angeboten |
| `[SDR/HW]`  | benötigt Software-Defined-Radio / Diag-Port / Smartcard-Reader |
| `[INFO]`    | erklärt, was real nötig wäre (nicht in reinem ADB machbar) |
| `[GEFAHR]`  | destruktiv/irreversibel – nur mit bewusster Bestätigung |

**Verteilung:** 206 direkt per ADB · 34 Root · 102 SDR/Hardware · 75 Info · 33 Gefahr.

## Wichtige Hinweise
- Nur für **eigene oder autorisiert untersuchte Geräte** verwenden.
- Ohne Root verhindert Androids App-Sandbox + FBE-Verschlüsselung das Lesen fremder
  App-Datenbanken und echtes Carving gelöschter Dateien – das Tool sagt das offen,
  statt Daten zu erfinden.
- Funk-Exploits, IMEI/IMSI-Spoofing, SIM-Klonen u. ä. sind in reiner Software auf
  Stock-Geräten nicht durchführbar; diese Punkte sind dokumentiert, nicht gefälscht.

## Ausgaben
Berichte/Exports landen unter:
- `out/` – Screenshots, Recordings, Pulls, App-Listen, UI-Dumps
- `forensik/` – Konten, Anrufe, SMS, Medien-Inventar, Browser, Play-Store usw.
- `forensik_full/` – Gesamtberichte der 45-Sektionen-Vollanalyse (Text/Markdown)
- `diagnostics/` – Root-/Bootloader-Tiefen-Diagnose-Logs
- `apkscan/` – APK-Statik-Analysen, Risiko-Inventar, IOC-Scan
- `reports/` – Gesamtberichte (HTML/MD/JSON) + `MANIFEST_*.sha256`
- `logs/` – ein Lauf-Logfile pro Start (Fehler werden protokolliert statt verschluckt)
- `root_checklist_*.txt`, `forensic_scan.txt`

## Struktur
```
panzer.py            Launcher
apz/
  adb.py             ADB-Wrapper, Geräteerkennung, Root-Check
  ui.py              ANSI-UI (Banner, Menüs, Pager) – ohne Abhängigkeiten
  dashboard.py       Auto-Analyse & Dashboard
  rooting.py         Root-Status + Rooting-Assistent (Auto-Root-Option)
  rootprep.py        Hintergrund-Root-Vorbereitung (Link-Auflösung) + Auto-Root-Flow
  modeswitch.py      Automatischer Modus-Wechsel (Download/Fastboot/Recovery/System)
  customfw.py        Custom-Firmware/Recovery fürs Gerät (LineageOS-API, TWRP) anzeigen
  appscan.py         App-Inventar: Anomalie-Markierung + Leertaste-Auswahl + Export
  forensics.py       Deep-Scan (versteckte Apps/Profile/Icons)
  dataforensics.py   Daten-Forensik & Wiederherstellung
  registry.py        450 Funktionen / 45 Kategorien
  handlers.py        interaktive Handler (Input, Transfer, Monitore)
  acquire.py         Vollanalyse: 45-Sektionen-Forensik-Akquise → Gesamtbericht
  apkscan.py         APK-Statik-Analyse (eigener AXML-Parser), Risk-Scoring, IOC-Scan
  report.py          einheitlicher HTML/MD/JSON-Report + SHA-256-Manifest
  util.py            zentrale Helfer: sichere Shell-Quoting, Validierung, Logging, Hashing
  main.py            Menüführung & Dispatch
```

## Sicherheit & Robustheit
- **Command-Injection-Schutz:** Alle gerätebezogenen Werte (Paketnamen, Pfade,
  Eingaben) werden vor der Einbettung in `adb shell`-Kommandos mit `shlex.quote`
  abgesichert (`apz/util.shq`). Ein Regressionstest verhindert neue ungesicherte
  Stellen.
- **Fehler-Transparenz:** Statt Fehler stillschweigend zu verschlucken, schreibt das
  Tool ein Lauf-Logfile (`logs/`). „Keine Daten" und „Zugriff verweigert" bleiben
  unterscheidbar – wichtig für forensische Aussagekraft.

## Entwicklung & Tests
```
pip install pytest           # einzige Test-Abhängigkeit
python3 -m pytest            # 50 Unit-Tests (Parser, AXML, Report, Vollanalyse, Quoting) – ohne Gerät
```
Die Tests nutzen einen **Mock-ADB** (kein echtes Gerät nötig) und prüfen u.a. den
binären AndroidManifest-Parser gegen eine echte APK, die Report-/Manifest-Erzeugung,
die Timestamp-/Content-Provider-Parser sowie das sichere Shell-Quoting.
Konfiguration in `pyproject.toml` (pytest + ruff).
