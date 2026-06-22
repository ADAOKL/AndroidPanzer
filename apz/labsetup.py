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
        "apt": ["open5gs", "osmo-bts", "osmo-bsc", "osmo-msc", "srsran"],
        "pip": [],
        "check": ["open5gs-mmed", "srsenb", "osmo-bts-trx"],
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


def _install_pkgs(apt, pip) -> None:
    if apt:
        cmd = "sudo apt-get update && sudo apt-get install -y " + " ".join(apt)
        ui.info(f"APT:\n   {cmd}")
        if ui.confirm("APT-Pakete installieren (sudo – fragt Passwort)?", False):
            try:
                subprocess.call(["bash", "-lc", cmd])
            except Exception as e:  # noqa: BLE001
                ui.err(f"APT fehlgeschlagen: {e}"); LOG.exception("labsetup apt", e)
    if pip:
        cmd = "pip3 install --user --upgrade " + " ".join(pip)
        ui.info(f"PIP:\n   {cmd}")
        if ui.confirm("PIP-Pakete installieren?", False):
            try:
                subprocess.call(["bash", "-lc", cmd])
            except Exception as e:  # noqa: BLE001
                ui.err(f"PIP fehlgeschlagen: {e}"); LOG.exception("labsetup pip", e)


def _install(tc) -> None:
    ui.rule(f"Installation: {tc['name']}", ui.YELLOW)
    if not tc.get("apt") and not tc.get("pip"):
        ui.info("Reines Hardware-Labor – keine Software zu installieren.")
        ui.pause(); return
    _install_pkgs(tc.get("apt", []), tc.get("pip", []))
    ui.pause()


def _install_all() -> None:
    """Installiert die Software ALLER Labore in einem Rutsch (aggregiert, dedupliziert)."""
    apt, pip = [], []
    for tc in TOOLCHAINS:
        for p in tc.get("apt", []):
            if p not in apt:
                apt.append(p)
        for p in tc.get("pip", []):
            if p not in pip:
                pip.append(p)
    ui.clear()
    ui.rule("ALLE Labor-Softwarepakete installieren", ui.YELLOW)
    ui.warn(f"{len(apt)} APT- und {len(pip)} PIP-Pakete. Das kann viel herunterladen (mehrere GB).")
    ui.info("APT: " + " ".join(apt))
    ui.info("PIP: " + " ".join(pip))
    print()
    if ui.confirm("Wirklich ALLES installieren?", False):
        _install_pkgs(apt, pip)
    ui.pause()


def _detail(tc) -> None:
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
    ui.info(f"{ui.BOLD}Software-Toolchain (Status):{ui.RESET}")
    for b in tc.get("check", []):
        ok = _have_bin(b)
        print(f"   {ui.BGREEN}✓{ui.RESET} {b}" if ok else f"   {ui.BRED}✗{ui.RESET} {b}  {ui.GREY}(fehlt){ui.RESET}")
    for p in tc.get("pip", []):
        ok = _have_pip(p)
        print(f"   {ui.BGREEN}✓{ui.RESET} pip:{p}" if ok else f"   {ui.BRED}✗{ui.RESET} pip:{p}  {ui.GREY}(fehlt){ui.RESET}")
    print()
    ui.warn(tc["note"])
    print()
    ch = ui.menu("Aktion", [
        ("1", "📦 Software-Toolchain installieren (apt/pip)"),
        ("2", "📋 Nur Installationsbefehle anzeigen"),
    ], back_label="Zurück")
    if ch == "1":
        _install(tc)
    elif ch == "2":
        if tc.get("apt"):
            print(f"   {ui.BCYAN}sudo apt-get install -y {' '.join(tc['apt'])}{ui.RESET}")
        if tc.get("pip"):
            print(f"   {ui.BCYAN}pip3 install --user {' '.join(tc['pip'])}{ui.RESET}")
        if not tc.get("apt") and not tc.get("pip"):
            print(f"   {ui.GREY}(reines Hardware-Labor – keine Software){ui.RESET}")
        ui.pause()


def menu(adb=None, dev=None, st=None, data=None) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🧪 Labor-Einrichtung – komplettes Forensik-/Security-Arsenal")
        ui.info("Software-Labore werden geprüft & installiert; hardwaregebundene Labore zeigen das nötige Gerät.\n")
        entries = [("A", f"{ui.BGREEN}{ui.BOLD}⬇ ALLE Software-Labore auf einmal installieren{ui.RESET}")]
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
        try:
            tc = TOOLCHAINS[int(ch) - 1]
        except (ValueError, IndexError):
            continue
        _detail(tc)
