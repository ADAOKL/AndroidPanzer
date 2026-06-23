"""Labor-Einrichtungs-Assistent – das komplette Forensik-/Security-Lab.

Richtet alle wichtigen Labore für mobile Forensik & Security ein:
Software-Toolchains (DFIR-Suiten, APK-Reverse, Traffic, Carving, SQLite, Imaging,
Krypto, EXIF/Geo) sowie die hardwaregebundenen Labore (SDR, SIM-Smartcard,
Test-Mobilfunknetz, EDL/BROM, DPA/Seitenkanal, Satellit, JTAG/Chip-Off).

Pro Fähigkeit: nötige HARDWARE, OPEN-SOURCE-SOFTWARE, Installationsstatus,
Ein-Klick-Installation (apt/pip). Reine Einrichtung von Standard-Open-Source-
Werkzeugen auf dem eigenen Analyse-PC. Sende-/TX-fähige Funkfunktionen sind
genehmigungspflichtig – nur in abgeschirmter Umgebung.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess

from . import ui
from .util import LOG

# Jede Fähigkeit: hw (physisch nötig), apt/pip (Software), check (Prüf-Binaries), use (wofür).
TOOLCHAINS = [
    # ---------- reine Software-Labore (auf Kali meist verfügbar) ----------
    {
        "key": "dfir", "name": "Mobile-Forensik-Suite (ALEAPP/Autopsy/Plaso)",
        "use": "Artefakt-Parsing, Super-Timeline, Fall-Auswertung",
        "hw": [],
        "apt": ["sleuthkit", "autopsy", "plaso", "python3-pip", "default-jdk"],
        "pip": ["aleapp", "ileapp", "andriller"],
        "check": ["tsk_recover", "log2timeline.py", "aleapp", "andriller"],
        "note": "ALEAPP wertet Android-Artefakte (Apps/Standort/Verlauf) aus; Plaso baut Super-Timelines.",
    },
    {
        "key": "apk", "name": "APK-Analyse & Reverse-Engineering",
        "use": "Statik/Dynamik: apktool, jadx, frida, objection, radare2",
        "hw": [],
        "apt": ["apktool", "dex2jar", "jadx", "radare2", "default-jdk"],
        "pip": ["frida-tools", "objection", "apkleaks", "androguard"],
        "check": ["apktool", "jadx", "frida", "r2", "objection"],
        "note": "frida/objection für Laufzeit-Hooks (SSL-Unpin, Krypto-Keys), jadx/apktool für Code.",
    },
    {
        "key": "traffic", "name": "Traffic-Interception & Netzwerk",
        "use": "HTTPS-Klartext (mitmproxy+Frida), PCAP (wireshark), Scan (nmap)",
        "hw": [],
        "apt": ["mitmproxy", "wireshark", "tshark", "nmap", "tcpdump"],
        "pip": ["mitmproxy", "frida-tools"],
        "check": ["mitmdump", "tshark", "nmap", "tcpdump"],
        "note": "Mit Frida-SSL-Unpinning wird auch gepinnter App-Traffic im Klartext lesbar.",
    },
    {
        "key": "carving", "name": "Datei-Carving & Datenrettung",
        "use": "Gelöschtes aus Images bergen: foremost/scalpel/photorec/binwalk",
        "hw": [],
        "apt": ["foremost", "scalpel", "testdisk", "binwalk", "bulk-extractor", "ddrescue"],
        "pip": [],
        "check": ["foremost", "scalpel", "photorec", "binwalk", "bulk_extractor"],
        "note": "photorec/foremost carven Medien aus Roh-Images; bulk_extractor zieht E-Mails/URLs/Kreditkarten.",
    },
    {
        "key": "sqlite", "name": "SQLite-/DB-Forensik (gelöschte Zeilen)",
        "use": "WAL/Journal-Carving, msgstore/contacts2-Auswertung",
        "hw": [],
        "apt": ["sqlite3", "sqlitebrowser", "sqlcipher"],
        "pip": [],
        "check": ["sqlite3", "sqlitebrowser", "sqlcipher"],
        "note": "sqlcipher entschlüsselt Signal-/verschlüsselte DBs; 'sqlite3 .recover' birgt gelöschte Zeilen.",
    },
    {
        "key": "imaging", "name": "Disk-Imaging & Beweissicherung",
        "use": "Bitgenaue Images (E01/dd) + Hash-Verifikation",
        "hw": ["optional: Hardware-Write-Blocker für externe Medien"],
        "apt": ["ewf-tools", "dc3dd", "guymager", "android-sdk-platform-tools"],
        "pip": [],
        "check": ["ewfacquire", "dc3dd", "guymager", "adb"],
        "note": "ewfacquire/guymager erzeugen E01 mit eingebetteten Hashes (gerichtsfest).",
    },
    {
        "key": "crypto", "name": "Krypto- & Passwort-Recovery",
        "use": "Backup-/Keystore-/Hash-Cracking",
        "hw": ["empfohlen: GPU (CUDA/OpenCL) für hashcat"],
        "apt": ["hashcat", "john", "hashid"],
        "pip": [],
        "check": ["hashcat", "john", "hashid"],
        "note": "Für ADB-Backups (abe) & Krypto-Container – nur eigene/autorisierte Daten.",
    },
    {
        "key": "exif", "name": "EXIF / Geo / Medien-Metadaten",
        "use": "Foto-GPS, Kameramodell, Zeitstempel, Routen",
        "hw": [],
        "apt": ["libimage-exiftool-perl", "gpsbabel", "ffmpeg"],
        "pip": ["exifread"],
        "check": ["exiftool", "gpsbabel", "ffprobe"],
        "note": "exiftool zieht GPS/Geräte-Metadaten aus Bildern/Videos; gpsbabel konvertiert Routen.",
    },
    # ---------- hardwaregebundene Labore ----------
    {
        "key": "sdr", "name": "SDR & Funkanalyse (Empfang)",
        "use": "Sek. 21/23/43/44 – Signal-/Funk-Analyse",
        "hw": ["RTL-SDR (Empfang, günstig)", "HackRF/USRP/BladeRF (auch TX – nur autorisiert)",
               "Antennen; für TEMPEST: abgeschirmte Kammer + Spektrumanalysator"],
        "apt": ["gnuradio", "gqrx-sdr", "rtl-sdr", "hackrf", "soapysdr-tools", "inspectrum"],
        "pip": [],
        "check": ["gnuradio-companion", "gqrx", "rtl_test", "hackrf_info"],
        "note": "Empfang unkritisch. Senden/Stören ist genehmigungspflichtig (Schirmkammer).",
    },
    {
        "key": "corenet", "name": "Test-Mobilfunknetz (Open5GS/srsRAN/Osmocom)",
        "use": "Sek. 32/33/36/39 – Netz-/Baseband-Tests",
        "hw": ["SDR mit TX (USRP B210/BladeRF)", "abgeschirmte Kammer (Faraday)", "Test-SIMs (sysmoUSIM)"],
        "apt": ["osmo-bts", "osmo-bsc", "osmo-msc"],
        "pip": [],
        "manual": [
            ("open5gs",  "https://open5gs.org/open5gs/docs/guide/01-quickstart/ – eigenes Repository"),
            ("srsran",   "https://github.com/srsran/srsRAN_Project – aus Quellen kompilieren"),
        ],
        "check": ["osmo-bts-trx"],
        "note": "NIEMALS in öffentliche Netze senden – nur isoliertes Eigen-Testnetz, mit Genehmigung.",
    },
    {
        "key": "sim", "name": "SIM/eUICC-Smartcard-Forensik (pySim)",
        "use": "Sek. 18/40 – SIM-Dateisystem/Applets/APDU",
        "hw": ["PC/SC-Smartcard-Reader (ACR38/Omnikey)", "für Interposer: SIMtrace2"],
        "apt": ["pcscd", "pcsc-tools", "libpcsclite-dev", "swig"],
        "pip": ["pyscard", "pySim"],
        "check": ["pcsc_scan", "pySim-read.py", "pySim-shell.py"],
        "note": "Nur an eigenen/autorisierten SIMs. Ki-Extraktion (DPA) bleibt Hardware-Labor.",
    },
    {
        "key": "simtrace", "name": "SIM-Sniffer / APDU-Mitschnitt (SIMtrace2)",
        "use": "Sek. 34 – APDU-Klartext zwischen Telefon & SIM",
        "hw": ["SIMtrace2-Board (Osmocom) als Interposer"],
        "apt": ["libosmocore-dev", "libusb-1.0-0-dev"],
        "pip": [],
        "check": ["simtrace2-list"],
        "note": "Physischer Hardware-Interposer zwingend – Software allein genügt nicht.",
    },
    {
        "key": "lowlevel", "name": "Low-Level Flash / EDL / BROM",
        "use": "Sek. 30/45 – NVRAM/EFS, Unbrick, Chipset-Recovery",
        "hw": ["USB-Kabel; ggf. EDL-Testpoint / Deep-Flash-Kabel"],
        "apt": ["android-sdk-platform-tools", "python3-pip", "python3-serial"],
        "pip": ["edl", "mtkclient"],
        "check": ["edl", "mtk"],
        "note": "NVRAM/EFS-Schreiben ist hochriskant (IMEI-/Netz-Tod). Nur eigene Geräte.",
    },
    {
        "key": "dpa", "name": "Power-/Seitenkanal-Analyse (DPA)",
        "use": "Sek. 24 – Ki-Extraktion (Profi-Labor)",
        "hw": ["Oszilloskop/Logic-Analyzer am Chip", "ChipWhisperer (Seitenkanal-Rig)"],
        "apt": ["sigrok-cli", "pulseview"],
        "pip": ["chipwhisperer"],
        "check": ["sigrok-cli", "pulseview"],
        "note": "Ki via Differential Power Analysis ist reine Hardware-/Profi-Laborarbeit.",
    },
    {
        "key": "sat", "name": "Satelliten / Orbit-Validierung",
        "use": "Sek. 22/42 – NTN-Anti-Spoofing",
        "hw": ["SDR + LNB/Antenne für die Sat-/NTN-Bänder (Empfang)"],
        "apt": ["gpredict"],
        "pip": ["skyfield"],
        "check": ["gpredict"],
        "note": "Orbit-Validierung gegen TLE-Bahndaten; Empfang passiv.",
    },
    {
        "key": "jtag", "name": "JTAG / Chip-Off / UART (Hardware-Recovery)",
        "use": "Physische Extraktion bei gebrickten/gesperrten Geräten",
        "hw": ["JTAG-Adapter (RIFF/Easy-JTAG/OpenOCD)", "Chip-Off-Station (Hot-Air, eMMC/UFS-Reader)",
               "UART-Adapter (USB-TTL)"],
        "apt": ["openocd", "minicom", "picocom", "flashrom"],
        "pip": [],
        "check": ["openocd", "minicom", "flashrom"],
        "note": "Letzte Instanz bei toter Software – erfordert Löt-/Hardware-Equipment.",
    },
    # ---------- 33 neue Labore (18–50) ----------
    {
        "key": "osint", "name": "OSINT-Toolkit (theHarvester/recon-ng/sherlock)",
        "use": "E-Mail/Username/Domain OSINT; sherlock sucht Username auf 400+ Plattformen",
        "hw": [],
        "apt": ["recon-ng", "theharvester", "libimage-exiftool-perl", "nmap"],
        "pip": ["sherlock-project", "holehe", "maigret"],
        "check": ["recon-ng", "theHarvester", "sherlock"],
        "note": "E-Mail/Username/Domain OSINT; sherlock sucht Username auf 400+ Plattformen.",
    },
    {
        "key": "wifi", "name": "WiFi-Pentesting (aircrack-ng/kismet/hcxtools)",
        "use": "WPA2-Handshake-Capture + hashcat-Cracking – nur eigene/autorisierte Netzwerke",
        "hw": ["WLAN-Adapter mit Monitor-Mode (z.B. Alfa AWUS036ACH)"],
        "apt": ["aircrack-ng", "kismet", "cowpatty", "hcxdumptool", "hcxtools"],
        "pip": [],
        "check": ["aircrack-ng", "kismet", "hcxdumptool"],
        "note": "Nur eigene/autorisierte Netzwerke – WPA2-Handshake-Capture + hashcat-Cracking.",
    },
    {
        "key": "bluetooth", "name": "Bluetooth-Analyse (ubertooth/bluez/bettercap)",
        "use": "BT-Classic-Sniffing (Ubertooth) + BLE-Enumeration (bluepy)",
        "hw": ["Ubertooth One (BT-Sniffing)", "optional: BLE-Dongle (CSR8510)"],
        "apt": ["ubertooth", "bluetooth", "bluez", "bluez-tools"],
        "pip": ["bettercap", "bluepy"],
        "check": ["ubertooth-util", "hcitool", "bluetoothctl"],
        "note": "Ubertooth snifft BT-Classic; bluepy für BLE-Enumeration.",
    },
    {
        "key": "nfc", "name": "NFC/RFID-Analyse (libnfc/proxmark3)",
        "use": "MIFARE-Forensik, APDU-Analyse – nur eigene Karten",
        "hw": ["ACR122U NFC-Reader", "Proxmark3 (RFID-Cloning/Analyse)"],
        "apt": ["libnfc-bin", "libnfc-dev", "pcsc-tools"],
        "pip": [],
        "check": ["nfc-scan-device", "pcsc_scan"],
        "note": "Nur eigene Karten analysieren; proxmark3 für MIFARE-Forensik.",
    },
    {
        "key": "memory", "name": "Memory-Forensik (Volatility3/LiME)",
        "use": "RAM-Akquisition (LiME) + Prozess/Artefakt-Analyse (Volatility3)",
        "hw": [],
        "apt": ["build-essential", "linux-headers-generic", "python3-pip"],
        "pip": ["volatility3", "yara-python"],
        "check": ["vol3"],
        "note": "LiME lädt ein Kernel-Modul zur RAM-Akquisition; Volatility3 analysiert die Dumps.",
    },
    {
        "key": "stego", "name": "Steganographie-Erkennung (steghide/zsteg/stegseek)",
        "use": "Versteckte Daten in Bildern/Audio erkennen und extrahieren",
        "hw": [],
        "apt": ["steghide", "stegosuite"],
        "pip": ["stegseek"],
        "check": ["steghide"],
        "note": "Erkennt in Bildern/Audio versteckte Daten; zsteg für PNG/BMP.",
    },
    {
        "key": "malware", "name": "Malware-Analyse (YARA/ClamAV/androguard)",
        "use": "IOC-Matching, statische Android-Malware-Analyse, Antiviren-Scan",
        "hw": [],
        "apt": ["yara", "clamav", "clamav-daemon", "radare2"],
        "pip": ["androguard", "yara-python", "pefile", "capstone"],
        "check": ["yara", "clamscan", "r2"],
        "note": "YARA-Regeln für IOC-Matching; androguard für statische Android-Malware-Analyse.",
    },
    {
        "key": "netscanner", "name": "Netzwerk-Scanner (nmap/masscan/scapy)",
        "use": "Host-Discovery, Port-Scan, ARP-Scan, Paket-Crafting",
        "hw": [],
        "apt": ["nmap", "masscan", "netcat-openbsd", "arp-scan", "nbtscan", "whois", "dnsutils"],
        "pip": ["python-nmap", "scapy"],
        "check": ["nmap", "masscan", "nc", "arp-scan"],
        "note": "masscan scannt das gesamte Internet in Minuten; nmap für detaillierte Einzel-Hosts.",
    },
    {
        "key": "webapp", "name": "Web-App-Testing (sqlmap/nikto/gobuster/hydra)",
        "use": "SQLi, Directory-Bruteforce, Nikto-Scan – nur eigene/autorisierte Ziele",
        "hw": [],
        "apt": ["sqlmap", "nikto", "dirb", "gobuster", "wfuzz", "hydra"],
        "pip": ["requests", "httpx", "beautifulsoup4"],
        "check": ["sqlmap", "nikto", "gobuster", "hydra"],
        "note": "Nur gegen eigene/autorisierte Ziele; BurpSuite Community Edition separat herunterladen.",
    },
    {
        "key": "reversing", "name": "Binär-Reverse-Engineering (GDB/pwntools/Ghidra)",
        "use": "Disassembly, Debugging, Exploit-Entwicklung, ROP-Chains",
        "hw": [],
        "apt": ["gdb", "gdbserver", "ltrace", "strace", "default-jdk"],
        "pip": ["pwntools", "ropgadget", "capstone", "keystone-engine"],
        "check": ["gdb", "ltrace", "strace"],
        "note": "Ghidra (NSA, FOSS) separat von ghidra.re herunterladen; pwntools für Exploit-Dev.",
    },
    {
        "key": "browser_forensics", "name": "Browser-Forensik (hindsight/dumpzilla)",
        "use": "Chrome-LevelDB-Verlauf, Firefox-Profile, gespeicherte Passwörter",
        "hw": [],
        "apt": ["python3-pip"],
        "pip": ["hindsight", "dumpzilla"],
        "check": ["hindsight"],
        "note": "hindsight rekonstruiert Chrome-Verlauf aus LevelDB; dumpzilla für Firefox-Profile.",
    },
    {
        "key": "email_forensics", "name": "E-Mail-Forensik (pff-tools/mail-parser)",
        "use": "Outlook PST/OST, EML/MBOX-Parsing, Anhang-Extraktion",
        "hw": [],
        "apt": ["libpff-dev", "pff-tools", "thunderbird", "python3-pip"],
        "pip": ["mail-parser", "extract-msg"],
        "check": ["pffexport", "thunderbird"],
        "note": "pffexport liest Outlook PST/OST; mail-parser parst EML/MBOX-Dateien.",
    },
    {
        "key": "timeline_tools", "name": "Timeline-Analyse (mactime/timesketch/plaso)",
        "use": "Super-Timeline aus Artefakten – CSV/HTML + interaktives Timesketch",
        "hw": [],
        "apt": ["sleuthkit", "plaso", "python3-pip"],
        "pip": ["timesketch-import-client"],
        "check": ["mactime", "log2timeline.py"],
        "note": "log2timeline → plaso-Datei → mactime/timesketch für interaktive Super-Timeline.",
    },
    {
        "key": "android_emu", "name": "Android-Emulation (Waydroid/AVD)",
        "use": "App-Analyse ohne physisches Gerät – Waydroid (LXC) oder AVD",
        "hw": [],
        "apt": ["waydroid", "python3-pip", "default-jdk"],
        "pip": [],
        "check": ["waydroid"],
        "note": "Waydroid läuft Android in einem LXC-Container auf Linux; ideal für App-Analyse ohne Gerät.",
    },
    {
        "key": "firmware", "name": "Firmware-Analyse (binwalk/firmwalker/ubi-reader)",
        "use": "Firmware-Images entpacken, Dateisystem extrahieren, Secrets suchen",
        "hw": [],
        "apt": ["binwalk", "squashfs-tools", "mtd-utils"],
        "pip": ["ubi-reader", "firmwalker"],
        "check": ["binwalk", "unsquashfs"],
        "note": "binwalk entpackt Firmware-Images automatisch; firmwalker sucht nach Passwörtern/Schlüsseln.",
    },
    {
        "key": "exploit_dev", "name": "Exploit-Entwicklung (pwntools/angr/ROPgadget)",
        "use": "Buffer-Overflow, ROP-Chains, symbolische Ausführung – nur CTF/eigene Systeme",
        "hw": [],
        "apt": ["gdb", "python3-pip", "build-essential", "libc6-dev-i386"],
        "pip": ["pwntools", "angr", "ropgadget", "one_gadget"],
        "check": ["gdb", "ROPgadget"],
        "note": "Für CTF/Sicherheitsforschung; nur gegen eigene/autorisierte Systeme.",
    },
    {
        "key": "fuzzing", "name": "Fuzzing (AFL++/honggfuzz/boofuzz)",
        "use": "Coverage-guided Fuzzing (AFL++), Netzwerkprotokoll-Fuzzing (boofuzz)",
        "hw": [],
        "apt": ["afl++"],
        "pip": ["pythonfuzz", "boofuzz"],
        "manual": [
            ("honggfuzz", "https://github.com/google/honggfuzz – aus Quellen kompilieren (make)"),
            ("radamsa",   "https://gitlab.com/akihe/radamsa – aus Quellen (make install)"),
        ],
        "check": ["afl-fuzz"],
        "note": "AFL++ ist state-of-the-art Coverage-guided Fuzzer; boofuzz für Netzwerkprotokolle.",
    },
    {
        "key": "hash_tools", "name": "Hash & Integritäts-Tools (hashdeep/ssdeep/md5deep)",
        "use": "Kryptographische + Fuzzy-Hashes für Beweissicherung und Ähnlichkeitssuche",
        "hw": [],
        "apt": ["hashdeep", "ssdeep", "md5deep"],
        "pip": ["tlsh-hash", "pyssdeep"],
        "check": ["hashdeep", "ssdeep", "md5deep"],
        "note": "ssdeep/tlsh erkennen ähnliche (nicht identische) Dateien via Fuzzy-Hashing.",
    },
    {
        "key": "strings_analysis", "name": "String-Analyse (FLOSS/strings/bulk_extractor)",
        "use": "Strings aus Binaries, deobfuskierte Strings (FLOSS), Bulk-Extraktion",
        "hw": [],
        "apt": ["binutils", "bulk-extractor"],
        "pip": ["flare-floss"],
        "check": ["strings", "bulk_extractor", "floss"],
        "note": "FLOSS (FireEye) deobfuskiert Strings aus Malware-Binaries automatisch.",
    },
    {
        "key": "ios_forensics", "name": "iOS-Forensik (libimobiledevice/ifuse)",
        "use": "iPhone-Backup/Geräteinfo ohne iTunes – nur eigene Geräte",
        "hw": [],
        "apt": ["libimobiledevice-utils", "ideviceinstaller", "ifuse", "usbmuxd"],
        "pip": ["ioscopy"],
        "check": ["ideviceinfo", "ideviceinstaller", "ifuse"],
        "note": "libimobiledevice liest iPhone-Backup/Geräteinfo ohne iTunes; nur eigene Geräte.",
    },
    {
        "key": "docker_forensics", "name": "Container/Docker-Forensik (trivy/dive/syft)",
        "use": "Docker-Image-CVE-Scan, Layer-Analyse, SBOM-Erstellung",
        "hw": [],
        "apt": ["docker.io", "docker-compose"],
        "pip": ["trivy", "syft"],
        "check": ["docker", "trivy", "dive"],
        "note": "trivy scannt Docker-Images auf CVEs; dive analysiert Layer-Inhalt; syft erstellt SBOM.",
    },
    {
        "key": "reporting", "name": "Report-Erstellung (pandoc/LaTeX/python-docx)",
        "use": "Forensik-Reports in PDF/DOCX/HTML aus Markdown/Templates",
        "hw": [],
        "apt": ["pandoc", "texlive-base", "texlive-latex-recommended", "libreoffice-writer"],
        "pip": ["python-docx", "reportlab", "weasyprint"],
        "check": ["pandoc", "pdflatex", "soffice"],
        "note": "pandoc konvertiert Markdown→PDF/DOCX; reportlab für programmatische PDF-Erstellung.",
    },
    {
        "key": "vm_analysis", "name": "VM/Snapshot-Analyse (QEMU/libguestfs)",
        "use": "VMDK/VHD/QCOW2 konvertieren + mounten ohne Boot",
        "hw": [],
        "apt": ["qemu-utils", "libguestfs-tools", "guestmount"],
        "pip": ["libvirt-python"],
        "check": ["qemu-img", "guestmount", "virt-ls"],
        "note": "qemu-img konvertiert VMDK/VHD/QCOW2; libguestfs mountet VM-Images ohne Boot.",
    },
    {
        "key": "social_osint", "name": "Social-Media-OSINT (instaloader/yt-dlp/gallery-dl)",
        "use": "Instagram-Archive, Video-Beweise (YouTube/TikTok), Foto-Downloads",
        "hw": [],
        "apt": ["python3-pip"],
        "pip": ["instaloader", "yt-dlp", "gallery-dl"],
        "check": ["instaloader", "yt-dlp"],
        "note": "instaloader archiviert Instagram-Profile; yt-dlp für Video-Beweise (YouTube/TikTok etc.).",
    },
    {
        "key": "cloud_forensics", "name": "Cloud-Forensik (aws-cli/azure-cli/gcloud)",
        "use": "CloudTrail-Logs, S3-Bucket-Forensik, Azure Activity Logs",
        "hw": [],
        "apt": ["python3-pip", "curl"],
        "pip": ["awscli", "azure-cli", "boto3", "google-cloud-storage"],
        "check": ["aws", "az", "gcloud"],
        "note": "Für Cloud-Trail-Logs, S3-Bucket-Forensik, Azure Activity Logs.",
    },
    {
        "key": "android_debug", "name": "Android Runtime-Debug (frida/objection/adb)",
        "use": "Syscall-Tracing, SSL-Unpinning, Runtime-Hooks via Frida/Objection",
        "hw": [],
        "apt": ["android-sdk-platform-tools", "python3-pip"],
        "pip": ["frida-tools", "objection", "apkleaks"],
        "check": ["adb", "frida", "objection"],
        "note": "strace/ltrace werden via adb push auf das Gerät gebracht für Syscall-Tracing.",
    },
    {
        "key": "vpn_analysis", "name": "VPN/Proxy-Analyse (openvpn/wireguard/proxychains)",
        "use": "Traffic durch VPN/Proxy leiten, WireGuard-Config-Analyse",
        "hw": [],
        "apt": ["openvpn", "wireguard-tools", "proxychains4"],
        "pip": ["mitmproxy"],
        "check": ["openvpn", "wg", "proxychains4", "mitmdump"],
        "note": "proxychains4 leitet beliebige Tools durch SOCKS/HTTP-Proxy für Netzwerkanalyse.",
    },
    {
        "key": "decompiler", "name": "Decompiler-Suite (jadx/cfr/uncompyle6)",
        "use": "Java/Kotlin-Decompilierung (jadx), Python-Bytecode (uncompyle6)",
        "hw": [],
        "apt": ["default-jdk", "jadx"],
        "pip": ["pycdas", "uncompyle6"],
        "check": ["jadx"],
        "note": "jadx ist der beste Android-Decompiler (Java+Kotlin); cfr/procyon als Fallback für komplexen Code.",
    },
    {
        "key": "rootkit_detect", "name": "Rootkit-Erkennung (rkhunter/chkrootkit/lynis)",
        "use": "Analyse-PC auf Rootkits/Backdoors prüfen – Forensik-System sauber halten",
        "hw": [],
        "apt": ["rkhunter", "chkrootkit", "lynis", "aide"],
        "pip": [],
        "check": ["rkhunter", "chkrootkit", "lynis"],
        "note": "Für den Analyse-PC selbst – stellt sicher dass das Forensik-System unverseucht ist.",
    },
    {
        "key": "antiforensics", "name": "Anti-Forensik-Erkennung (sleuthkit/dc3dd/plaso)",
        "use": "Timestamp-Manipulation, sparse files, hidden partitions erkennen",
        "hw": [],
        "apt": ["sleuthkit", "dc3dd"],
        "pip": ["dfvfs", "plaso"],
        "check": ["fsstat", "icat"],
        "note": "Erkennt $MACTIMES-Manipulation, sparse files, hidden partitions in forensischen Images.",
    },
    {
        "key": "password_audit", "name": "Passwort-Audit (john/hashcat/crunch/cewl)",
        "use": "Wortlisten-Cracking, Wortlisten-Generierung, Hash-Identifikation",
        "hw": ["empfohlen: GPU (CUDA/OpenCL) für hashcat"],
        "apt": ["john", "hashcat", "crunch", "cewl", "wordlists"],
        "pip": ["passlib"],
        "check": ["john", "hashcat", "crunch", "cewl"],
        "note": "crunch generiert Wortlisten; cewl extrahiert Wörter aus Webseiten für zielgerichtetes Cracking.",
    },
    {
        "key": "python_venv", "name": "Python-Forensik-venv (isolierte pip-Umgebung)",
        "use": "Saubere venv unter ~/panzer_venv – alle pip-Tools konfliktfrei installieren",
        "hw": [],
        "apt": ["python3-venv", "python3-pip", "python3-dev", "build-essential"],
        "pip": [],
        "check": ["python3", "pip3"],
        "note": "Richtet eine isolierte venv unter ~/panzer_venv ein – alle pip-Pakete landen dort sauber getrennt.",
    },
    {
        "key": "incident_response", "name": "Incident-Response (volatility/yara/osquery)",
        "use": "Schnelle Triage – Prozesse, Netzwerkverbindungen, Persistenz-Mechanismen live analysieren",
        "hw": [],
        "apt": ["yara", "sysstat", "lsof", "tcpdump"],
        "pip": ["volatility3", "yara-python"],
        "manual": [
            ("osquery", "https://osquery.io/downloads/ – offizielles .deb von osquery.io"),
        ],
        "check": ["yara", "tcpdump", "lsof"],
        "note": "osquery (manual .deb) stellt SQL-API auf Systemzustand bereit; volatility3 für RAM-Triage.",
    },
    {
        "key": "update_tools", "name": "Self-Update & Tool-Maintenance (apt/pip/git)",
        "use": "Alle Tools aktuell halten, Abhängigkeitskonflikte erkennen",
        "hw": [],
        "apt": ["git", "curl", "wget", "unzip", "p7zip-full"],
        "pip": ["pip-check", "pipdeptree"],
        "check": ["git", "curl", "wget"],
        "note": "Hält alle installierten Tools aktuell; pipdeptree zeigt Abhängigkeitskonflikte.",
    },
]


def _have_bin(name: str) -> bool:
    return shutil.which(name) is not None


def _have_pip(mod: str) -> bool:
    cand = mod.replace("-", "_").lower()
    for n in (cand, cand.split("_")[0]):
        try:
            if importlib.util.find_spec(n) is not None:
                return True
        except (ImportError, ValueError, ModuleNotFoundError):
            pass
    return False


def _status(tc) -> tuple[int, int]:
    bins = tc.get("check", [])
    if bins:
        return sum(1 for b in bins if _have_bin(b)), len(bins)
    pips = tc.get("pip", [])
    return sum(1 for p in pips if _have_pip(p)), len(pips)


def _apt_available(pkg: str) -> bool:
    """Prüft ob ein APT-Paket im Repo existiert (apt-cache show)."""
    return subprocess.call(
        ["apt-cache", "show", pkg],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ) == 0


def _pip_via_venv(packages: list[str]) -> bool:
    """Installiert pip-Pakete in ~/panzer_venv (venv-first Strategie)."""
    import os, sys
    venv_path = os.path.expanduser("~/panzer_venv")
    venv_pip = os.path.join(venv_path, "bin", "pip")
    venv_python = os.path.join(venv_path, "bin", "python3")
    if not os.path.isfile(venv_python):
        ui.info("Erstelle ~/panzer_venv …")
        if subprocess.call([sys.executable, "-m", "venv", venv_path]) != 0:
            return False
        subprocess.call([venv_python, "-m", "pip", "install", "--upgrade", "pip"],
                        stdout=subprocess.DEVNULL)
    ui.info(f"  pip install via ~/panzer_venv …")
    return subprocess.call([venv_pip, "install", "--upgrade"] + packages) == 0


def _install_pkgs(apt: list, pip_pkgs: list, manual: list | None = None) -> None:
    # ── APT ──────────────────────────────────────────────────────────────────
    if apt:
        print()
        ui.info(f"{ui.BOLD}APT-Pakete prüfen ({len(apt)}):{ui.RESET}")
        available, missing = [], []
        for pkg in apt:
            if _apt_available(pkg):
                available.append(pkg)
                print(f"  {ui.BGREEN}✓{ui.RESET} {pkg}")
            else:
                missing.append(pkg)
                print(f"  {ui.GREY}✗{ui.RESET} {pkg}  {ui.BRED}(nicht in Repo – übersprungen){ui.RESET}")
        if missing:
            ui.warn(f"{len(missing)} Paket(e) nicht im APT-Repo: {', '.join(missing)}")
        if available and ui.confirm(f"  {len(available)} verfügbare APT-Pakete installieren?", False):
            try:
                cmd = "sudo apt-get install -y " + " ".join(available)
                subprocess.call(["bash", "-lc", cmd])
            except Exception as e:  # noqa: BLE001
                ui.err(f"APT fehlgeschlagen: {e}"); LOG.exception("labsetup apt", e)

    # ── PIP via venv ─────────────────────────────────────────────────────────
    if pip_pkgs:
        print()
        ui.info(f"{ui.BOLD}PIP-Pakete (via ~/panzer_venv):{ui.RESET}")
        print(f"  {ui.GREY}{' '.join(pip_pkgs)}{ui.RESET}")
        if ui.confirm(f"  {len(pip_pkgs)} pip-Pakete in ~/panzer_venv installieren?", False):
            ok = _pip_via_venv(pip_pkgs)
            if not ok:
                ui.warn("venv fehlgeschlagen – Fallback: pip3 --break-system-packages")
                subprocess.call(
                    ["pip3", "install", "--break-system-packages", "--upgrade"] + pip_pkgs
                )

    # ── Manuelle Install-Hinweise ─────────────────────────────────────────────
    if manual:
        print()
        ui.rule("⚠ MANUELLE INSTALLATION ERFORDERLICH", ui.BYELLOW)
        for name, url in manual:
            print(f"  {ui.BYELLOW}▸{ui.RESET} {ui.BOLD}{name}{ui.RESET}")
            print(f"     {ui.GREY}{url}{ui.RESET}")
        print()


def _install(tc) -> None:
    ui.clear()
    ui.rule(f"Installation: {tc['name']}", ui.YELLOW)
    if not tc.get("apt") and not tc.get("pip") and not tc.get("manual"):
        ui.info("Reines Hardware-Labor – keine Software zu installieren.")
        ui.pause(); return
    _install_pkgs(tc.get("apt", []), tc.get("pip", []), tc.get("manual"))
    ui.pause()


def _setup_venv() -> None:
    """Richtet ~/panzer_venv ein und installiert alle pip-Pakete der 50 Labore hinein."""
    import os
    import sys
    venv_path = os.path.expanduser("~/panzer_venv")
    ui.clear()
    ui.rule("Python-Forensik-venv einrichten", ui.CYAN)
    ui.info(f"venv-Pfad: {venv_path}")
    print()
    # Prüfen ob venv schon existiert
    venv_python = os.path.join(venv_path, "bin", "python3")
    if os.path.isfile(venv_python):
        ui.ok("venv existiert bereits.")
    else:
        ui.info("Erstelle venv …")
        if subprocess.call([sys.executable, "-m", "venv", venv_path]) != 0:
            ui.err("Konnte venv nicht erstellen! Stelle sicher, dass python3-venv installiert ist.")
            ui.pause()
            return

    # Alle pip-Pakete aus allen 50 Toolchains sammeln
    all_pip = []
    for tc in TOOLCHAINS:
        for p in tc.get("pip", []):
            if p and p not in all_pip:
                all_pip.append(p)

    ui.info(f"Installiere {len(all_pip)} pip-Pakete in die venv …")
    print(f"   {ui.GREY}{' '.join(all_pip)}{ui.RESET}")
    print()
    if not ui.confirm(f"Alle {len(all_pip)} pip-Pakete in ~/panzer_venv installieren?", False):
        ui.pause()
        return

    # Erst pip upgraden
    subprocess.call([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
    # Dann alle Pakete installieren
    result = subprocess.call([venv_python, "-m", "pip", "install"] + all_pip)
    if result == 0:
        ui.ok("venv vollständig eingerichtet!")
        ui.info(f"Aktivieren mit:  source {venv_path}/bin/activate")
    else:
        ui.warn("Einige Pakete konnten nicht installiert werden (apt-Abhängigkeiten fehlen evtl.).")
    ui.pause()


def _install_all() -> None:
    """Installiert die Software ALLER Labore in einem Rutsch (aggregiert, dedupliziert)."""
    apt, pip_pkgs, manual = [], [], []
    for tc in TOOLCHAINS:
        for p in tc.get("apt", []):
            if p not in apt:
                apt.append(p)
        for p in tc.get("pip", []):
            if p not in pip_pkgs:
                pip_pkgs.append(p)
        for entry in tc.get("manual", []):
            if entry not in manual:
                manual.append(entry)
    ui.clear()
    ui.rule(f"Alle {len(TOOLCHAINS)} Labor-Softwarepakete installieren", ui.YELLOW)
    print()
    # Built-in Status anzeigen
    from . import builtin_tools
    ui.rule("✅ BEREITS BUILT-IN (kein Install nötig)", ui.BGREEN)
    for cap in builtin_tools.BUILTIN_CAPABILITIES.values():
        print(f"  {ui.BGREEN}✓{ui.RESET} {cap['name']}")
    print()
    ui.rule(f"📦 SOFTWARE INSTALLATION", ui.YELLOW)
    ui.warn(f"{len(apt)} APT- und {len(pip_pkgs)} PIP-Pakete. Das kann viel herunterladen (mehrere GB).")
    if manual:
        ui.warn(f"{len(manual)} Pakete erfordern MANUELLE Installation (kein APT-Repo).")
    print()
    if ui.confirm("Wirklich ALLES installieren (apt+pip)?", False):
        _install_pkgs(apt, pip_pkgs, manual)
    elif manual:
        ui.rule("⚠ Manuelle Install-Hinweise", ui.BYELLOW)
        for name, url in manual:
            print(f"  {ui.BYELLOW}▸{ui.RESET} {ui.BOLD}{name}{ui.RESET}  →  {ui.GREY}{url}{ui.RESET}")
    ui.pause()


def _detail(tc) -> None:
    from . import builtin_tools
    ui.clear()
    ui.rule(tc["name"], ui.CYAN)
    ui.kv("Zweck", tc.get("use", ""))
    print()
    hw = tc.get("hw", [])
    if hw:
        ui.info(f"{ui.BOLD}Benötigte Hardware (physisch – nicht durch Software ersetzbar):{ui.RESET}")
        for h in hw:
            print(f"   {ui.BYELLOW}▸{ui.RESET} {h}")
    else:
        ui.ok("Reine Software – keine Spezial-Hardware nötig.")
    print()

    # Built-in Fähigkeiten anzeigen wenn vorhanden
    builtin_keys = {
        "apk": ["apk_analyse", "hash_calc"],
        "sqlite": ["sqlite_forensik"],
        "carving": ["file_carving"],
        "strings_analysis": ["string_extract", "email_extract", "url_extract"],
        "crypto": ["hash_analyze", "hash_calc"],
        "netscanner": ["port_scan"],
        "exif": ["timeline"],
    }
    bkeys = builtin_keys.get(tc.get("key", ""), [])
    if bkeys:
        print(f"  {ui.BGREEN}▶ BUILT-IN (sofort verfügbar – kein Install):{ui.RESET}")
        for bk in bkeys:
            cap = builtin_tools.BUILTIN_CAPABILITIES.get(bk)
            if cap:
                print(f"     {ui.BGREEN}✓{ui.RESET} {cap['name']}")
        print()

    ui.info(f"{ui.BOLD}Software-Toolchain (Installations-Status):{ui.RESET}")
    for b in tc.get("check", []):
        ok = _have_bin(b)
        print(f"   {ui.BGREEN}✓{ui.RESET} {b}" if ok else f"   {ui.BRED}✗{ui.RESET} {b}  {ui.GREY}(fehlt){ui.RESET}")
    for p in tc.get("pip", []):
        ok = _have_pip(p)
        print(f"   {ui.BGREEN}✓{ui.RESET} pip:{p}" if ok else f"   {ui.BRED}✗{ui.RESET} pip:{p}  {ui.GREY}(fehlt){ui.RESET}")
    manual = tc.get("manual", [])
    if manual:
        print()
        print(f"   {ui.BYELLOW}⚠ Manuelle Installation nötig:{ui.RESET}")
        for name, url in manual:
            print(f"   {ui.BYELLOW}▸{ui.RESET} {ui.BOLD}{name}{ui.RESET}  →  {ui.GREY}{url}{ui.RESET}")
    print()
    ui.warn(tc["note"])
    print()
    action_entries = [
        ("1", "📦 Software-Toolchain installieren (apt+pip via venv)"),
        ("2", "📋 Nur Installationsbefehle anzeigen"),
        ("3", "⚙️  Fähigkeiten-Status (Built-in + extern)"),
    ]
    if tc.get("key") == "python_venv":
        action_entries.append(("4", "🐍 Python-venv ~/panzer_venv einrichten (alle pip-Pakete)"))
    ch = ui.menu("Aktion", action_entries, back_label="Zurück")
    if ch == "1":
        _install(tc)
    elif ch == "2":
        print()
        if tc.get("apt"):
            print(f"   {ui.BCYAN}# APT (Pakete die im Repo sind):{ui.RESET}")
            print(f"   {ui.BCYAN}sudo apt-get install -y {' '.join(tc['apt'])}{ui.RESET}")
        if tc.get("pip"):
            print(f"   {ui.BCYAN}# PIP via venv (Kali-kompatibel):{ui.RESET}")
            print(f"   {ui.BCYAN}source ~/panzer_venv/bin/activate && pip install {' '.join(tc['pip'])}{ui.RESET}")
        if manual:
            print(f"   {ui.BYELLOW}# Manuelle Installation:{ui.RESET}")
            for name, url in manual:
                print(f"   {ui.BYELLOW}# {name}: {url}{ui.RESET}")
        if not tc.get("apt") and not tc.get("pip"):
            print(f"   {ui.GREY}(reines Hardware-Labor – keine Software){ui.RESET}")
        ui.pause()
    elif ch == "3":
        builtin_tools.show_capability_status()
    elif ch == "4" and tc.get("key") == "python_venv":
        _setup_venv()


def auto_pip_preflight(quiet: bool = False) -> list[str]:
    """Installiert ALLE pip-Pakete aus allen Toolchains automatisch in ~/panzer_venv.

    Wird beim Start aufgerufen (quiet=True = kein Benutzerdialog, nur Status-Ausgabe).
    Gibt Liste der fehlgeschlagenen Pakete zurück.
    """
    import os
    import sys

    venv_path = os.path.expanduser("~/panzer_venv")
    venv_python = os.path.join(venv_path, "bin", "python3")
    venv_pip = os.path.join(venv_path, "bin", "pip")

    # Alle pip-Pakete aus allen Toolchains sammeln (dedupliziert)
    all_pip: list[str] = []
    for tc in TOOLCHAINS:
        for p in tc.get("pip", []):
            if p and p not in all_pip:
                all_pip.append(p)

    if not all_pip:
        return []

    # venv erstellen falls nicht vorhanden
    if not os.path.isfile(venv_python):
        if not quiet:
            ui.info("Erstelle ~/panzer_venv für pip-Vorab-Installation …")
        rc = subprocess.call(
            [sys.executable, "-m", "venv", venv_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if rc != 0:
            if not quiet:
                ui.err("venv-Erstellung fehlgeschlagen. Installiere python3-venv: sudo apt install python3-venv")
            return all_pip
        subprocess.call(
            [venv_pip, "install", "--upgrade", "pip"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # Prüfen welche Pakete noch fehlen
    missing: list[str] = []
    for pkg in all_pip:
        spec_name = pkg.replace("-", "_").split("[")[0]
        found = False
        for n in (spec_name, spec_name.split("_")[0]):
            try:
                if importlib.util.find_spec(n) is not None:
                    found = True
                    break
            except (ImportError, ValueError, ModuleNotFoundError):
                pass
        if not found:
            missing.append(pkg)

    if not missing:
        if not quiet:
            ui.ok(f"Alle {len(all_pip)} pip-Pakete bereits installiert.")
        return []

    if not quiet:
        ui.info(f"Installiere {len(missing)} fehlende pip-Pakete in ~/panzer_venv …")
        print(f"  {ui.GREY}{' '.join(missing[:10])}{'…' if len(missing) > 10 else ''}{ui.RESET}")

    # Installation (in Batches à 20 für bessere Fehlertoleranz)
    failed: list[str] = []
    batch_size = 20
    for i in range(0, len(missing), batch_size):
        batch = missing[i : i + batch_size]
        rc = subprocess.call(
            [venv_pip, "install", "--upgrade"] + batch,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.DEVNULL if quiet else None,
        )
        if rc != 0:
            # Einzeln versuchen um schlechte Pakete zu isolieren
            for pkg in batch:
                rc2 = subprocess.call(
                    [venv_pip, "install", "--upgrade", pkg],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if rc2 != 0:
                    failed.append(pkg)

    if not quiet:
        installed_count = len(missing) - len(failed)
        if installed_count > 0:
            ui.ok(f"✓ {installed_count} Pakete installiert.")
        if failed:
            ui.warn(f"✗ {len(failed)} Pakete fehlgeschlagen (Abhängigkeiten fehlen): {', '.join(failed)}")

    return failed


def menu(adb=None, dev=None, st=None, data=None) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle=f"🧪 Labor-Einrichtung – {len(TOOLCHAINS)} Labore – komplettes Forensik-/Security-Arsenal")
        ui.info("Software-Labore werden geprüft & installiert; hardwaregebundene Labore zeigen das nötige Gerät.\n")
        entries = [
            ("A", f"{ui.BGREEN}{ui.BOLD}⬇ ALLE Software-Labore auf einmal installieren{ui.RESET}"),
            ("P", f"{ui.BMAGENTA}{ui.BOLD}⚡ PIP VORAB-INSTALL – Alle Pip-Pakete sofort in venv laden{ui.RESET}"),
            ("B", f"{ui.BCYAN}{ui.BOLD}⚙ BUILT-IN TOOLS – Fähigkeiten-Status (kein Install){ui.RESET}"),
        ]
        for i, tc in enumerate(TOOLCHAINS, 1):
            have, total = _status(tc)
            sw = bool(tc.get("apt") or tc.get("pip"))
            if not sw:
                badge = f"{ui.MAGENTA}[HW]{ui.RESET}"
            elif have == total and total:
                badge = f"{ui.BGREEN}[{have}/{total}]{ui.RESET}"
            elif have:
                badge = f"{ui.BYELLOW}[{have}/{total}]{ui.RESET}"
            else:
                badge = f"{ui.BRED}[{have}/{total}]{ui.RESET}"
            entries.append((str(i), f"{badge} {tc['name']}  {ui.GREY}→ {tc.get('use','')}{ui.RESET}"))
        ch = ui.menu("Labor wählen", entries, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "a":
            _install_all()
            continue
        if ch == "p":
            ui.clear()
            ui.rule("⚡ PIP VORAB-INSTALLATION", ui.BMAGENTA)
            all_pip = []
            for tc in TOOLCHAINS:
                for p in tc.get("pip", []):
                    if p and p not in all_pip:
                        all_pip.append(p)
            ui.info(f"Gefunden: {len(all_pip)} Pip-Pakete aus {len(TOOLCHAINS)} Toolchains")
            print(f"  {ui.GREY}{' '.join(all_pip)}{ui.RESET}\n")
            if ui.confirm(f"Alle {len(all_pip)} Pakete jetzt in ~/panzer_venv installieren?", True):
                failed = auto_pip_preflight(quiet=False)
                if not failed:
                    ui.ok("Alle Pakete erfolgreich installiert!")
                else:
                    ui.warn(f"{len(failed)} Pakete konnten nicht installiert werden:\n  {', '.join(failed)}")
            ui.pause()
            continue
        if ch == "b":
            from . import builtin_tools
            builtin_tools.show_capability_status()
            continue
        try:
            tc = TOOLCHAINS[int(ch) - 1]
        except (ValueError, IndexError):
            continue
        _detail(tc)
