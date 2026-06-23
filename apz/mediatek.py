"""MediaTek Root/Flash/Forensik-Suite (mtkclient · BROM-Exploit) — MAXIMAL AUSGEBAUT.

Der MTK-BROM-Exploit (kamakiri/hashimoto/amonet) erlaubt Lesen/Schreiben JEDER
Partition OHNE Bootloader-Unlock – Bootloader-Unlock via seccfg oft OHNE Datenverlust.

Automatische mtkclient-Installation via ~/panzer_venv wenn nicht vorhanden.

Funktionen:
  Auto-Root · Bootloader-Unlock/Lock · Partition-Dump · Voll-Backup · Flashen
  FRP-Bypass · NVRAM-Backup/Restore · Preloader-Dump · Scatter-Analyse
  Engineer-Mode · Chip-Erkennung · Blink-Diagnose · DRAM-Test · Testpoint-Guide
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time

from . import ui, usb
from .util import LOG, outdir

WORK = os.path.expanduser("~/Schreibtisch/Androidpanzer/mediatek")
OUT  = outdir("mediatek")

# ── MTK-SoC Datenbank ─────────────────────────────────────────────────────────
MTK_SOCS: dict[str, dict] = {
    # Dimensity (5G)
    "mt6983": {"name": "Dimensity 9000",   "arch": "Cortex-X2", "process": "4nm TSMC",    "5g": True},
    "mt6895": {"name": "Dimensity 8100",   "arch": "Cortex-A78", "process": "5nm TSMC",   "5g": True},
    "mt6891": {"name": "Dimensity 1100",   "arch": "Cortex-A77", "process": "6nm TSMC",   "5g": True},
    "mt6877": {"name": "Dimensity 900",    "arch": "Cortex-A78", "process": "6nm TSMC",   "5g": True},
    "mt6873": {"name": "Dimensity 800",    "arch": "Cortex-A76", "process": "7nm TSMC",   "5g": True},
    "mt6853": {"name": "Dimensity 720",    "arch": "Cortex-A76", "process": "7nm TSMC",   "5g": True},
    "mt6833": {"name": "Dimensity 700",    "arch": "Cortex-A76", "process": "7nm TSMC",   "5g": True},
    # Helio G (Gaming)
    "mt6769": {"name": "Helio G85",        "arch": "Cortex-A75", "process": "12nm TSMC",  "5g": False},
    "mt6768": {"name": "Helio G80",        "arch": "Cortex-A75", "process": "12nm TSMC",  "5g": False},
    "mt6785": {"name": "Helio G90T",       "arch": "Cortex-A76", "process": "12nm TSMC",  "5g": False},
    "mt6781": {"name": "Helio G96",        "arch": "Cortex-A76", "process": "12nm TSMC",  "5g": False},
    # Helio P (Performance)
    "mt6771": {"name": "Helio P60/P70",    "arch": "Cortex-A73", "process": "12nm TSMC",  "5g": False},
    "mt6765": {"name": "Helio P35",        "arch": "Cortex-A53", "process": "12nm TSMC",  "5g": False},
    "mt6762": {"name": "Helio P22",        "arch": "Cortex-A53", "process": "12nm TSMC",  "5g": False},
    # Helio X (High-End Legacy)
    "mt6799": {"name": "Helio X30",        "arch": "Cortex-A72", "process": "10nm TSMC",  "5g": False},
    "mt6797": {"name": "Helio X20/X25",    "arch": "Cortex-A72", "process": "20nm TSMC",  "5g": False},
    "mt6795": {"name": "Helio X10",        "arch": "Cortex-A53", "process": "28nm TSMC",  "5g": False},
    # Legacy
    "mt6750": {"name": "MT6750",           "arch": "Cortex-A53", "process": "28nm",        "5g": False},
    "mt6735": {"name": "MT6735",           "arch": "Cortex-A53", "process": "28nm",        "5g": False},
    "mt6580": {"name": "MT6580",           "arch": "Cortex-A7",  "process": "28nm",        "5g": False},
    "mt6572": {"name": "MT6572",           "arch": "Cortex-A7",  "process": "40nm",        "5g": False},
}

# ── BROM-Exploit Kompatibilitätsliste ─────────────────────────────────────────
BROM_COMPATIBLE: dict[str, dict] = {
    "mt6580":  {"exploit": "amonet",     "testpoint": "nötig",    "notes": "TP am Preloader-NAND"},
    "mt6735":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Vol+Vol- meist ausreichend"},
    "mt6737":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": ""},
    "mt6750":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": ""},
    "mt6752":  {"exploit": "kamakiri",   "testpoint": "nein",     "notes": "einfach"},
    "mt6755":  {"exploit": "kamakiri",   "testpoint": "nein",     "notes": ""},
    "mt6757":  {"exploit": "kamakiri",   "testpoint": "nein",     "notes": ""},
    "mt6763":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": ""},
    "mt6765":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Helio P35"},
    "mt6768":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Helio G80"},
    "mt6769":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Helio G85"},
    "mt6771":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Helio P60/P70"},
    "mt6781":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Helio G96"},
    "mt6785":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Helio G90T"},
    "mt6797":  {"exploit": "kamakiri",   "testpoint": "nein",     "notes": "Helio X20"},
    "mt6799":  {"exploit": "kamakiri",   "testpoint": "nein",     "notes": "Helio X30"},
    "mt6833":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Dimensity 700"},
    "mt6853":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Dimensity 720"},
    "mt6873":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Dimensity 800"},
    "mt6877":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Dimensity 900"},
    "mt6891":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Dimensity 1100"},
    "mt6895":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Dimensity 8100"},
    "mt6983":  {"exploit": "hashimoto",  "testpoint": "manchmal", "notes": "Dimensity 9000"},
}


# ── mtkclient Auto-Install ─────────────────────────────────────────────────────

def _w(*sub) -> str:
    p = os.path.join(WORK, *sub)
    os.makedirs(os.path.dirname(p) if os.path.splitext(p)[1] else p, exist_ok=True)
    return p


def _venv_pip() -> str | None:
    venv = os.path.expanduser("~/panzer_venv/bin/pip")
    return venv if os.path.isfile(venv) else None


def _venv_python() -> str | None:
    venv = os.path.expanduser("~/panzer_venv/bin/python3")
    return venv if os.path.isfile(venv) else None


def _have_mtk() -> str | None:
    # 1. Prüfe venv
    venv_mtk = os.path.expanduser("~/panzer_venv/bin/mtk")
    if os.path.isfile(venv_mtk):
        return venv_mtk
    # 2. System-PATH
    p = shutil.which("mtk")
    if p:
        return p
    # 3. usb.tool_path Fallback
    try:
        from . import usb as _usb
        t = _usb.tool_path("mtk")
        if t:
            return t
    except Exception:  # noqa: BLE001
        pass
    return None


def _auto_install_mtkclient() -> bool:
    """Installiert mtkclient automatisch in ~/panzer_venv."""
    ui.rule("🔧 mtkclient Auto-Install", ui.CYAN)
    venv_path = os.path.expanduser("~/panzer_venv")
    venv_python = os.path.join(venv_path, "bin", "python3")

    # venv erstellen wenn nötig
    if not os.path.isfile(venv_python):
        ui.info("Erstelle ~/panzer_venv …")
        if subprocess.call([sys.executable, "-m", "venv", venv_path]) != 0:
            ui.err("python3-venv fehlt: sudo apt install python3-venv"); return False
        subprocess.call([venv_python, "-m", "pip", "install", "--upgrade", "pip"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ui.ok("venv erstellt.")

    # mtkclient + Abhängigkeiten installieren
    ui.info("Installiere mtkclient (kann 1-2 Minuten dauern) …")
    deps = ["mtkclient", "pyusb", "pyserial", "colorama", "pycryptodome"]
    pip = os.path.join(venv_path, "bin", "pip")
    rc = subprocess.call([pip, "install", "--upgrade"] + deps)
    if rc == 0:
        ui.ok("mtkclient erfolgreich installiert in ~/panzer_venv!")
        ui.info("Neustart des Tools empfohlen damit venv-mtk gefunden wird.")
        return True
    else:
        ui.warn("pip install fehlgeschlagen – versuche --break-system-packages …")
        rc2 = subprocess.call(["pip3", "install", "--break-system-packages", "mtkclient"])
        if rc2 == 0:
            ui.ok("mtkclient (system) installiert.")
            return True
        ui.err("Installation fehlgeschlagen. Manuell: pip install mtkclient")
        return False


def mtk(args: list[str], timeout: int = 600, stream: bool = True) -> tuple[int, str]:
    """mtkclient-Aufruf mit venv-Unterstützung."""
    mtk_bin = _have_mtk() or "mtk"
    cmd = [mtk_bin] + args
    if not stream:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return p.returncode, (p.stdout + p.stderr).strip()
        except subprocess.TimeoutExpired:
            return 124, "Timeout"
        except Exception as e:  # noqa: BLE001
            return 1, str(e)
    out = []
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.rstrip()
            print(f"   {line}")
            out.append(line)
        proc.wait(timeout=timeout)
        return proc.returncode, "\n".join(out)
    except subprocess.TimeoutExpired:
        proc.kill(); return 124, "\n".join(out)
    except KeyboardInterrupt:
        proc.kill(); return 130, "\n".join(out)
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def _need_mtk() -> bool:
    """Prüft ob mtkclient vorhanden – bietet Auto-Install an."""
    if _have_mtk():
        return True
    ui.warn("mtkclient nicht gefunden!")
    print()
    print(f"  {ui.BCYAN}mtkclient{ui.RESET} ist nötig für alle BROM/MTK-Operationen.")
    print(f"  Es wird in {ui.BOLD}~/panzer_venv{ui.RESET} installiert (isoliert, kein sudo).")
    print()
    if ui.confirm("mtkclient JETZT automatisch installieren?", True):
        ok = _auto_install_mtkclient()
        if ok and _have_mtk():
            return True
    ui.info("Danach Gerät in BROM-Modus (Hilfe: Menü ?).")
    ui.pause()
    return False


# ── Chip-Erkennung ────────────────────────────────────────────────────────────

def _detect_chip(adb) -> str:
    """Erkennt den MTK-Chipsatz."""
    try:
        hw = adb.getprop("ro.hardware") or ""
        board = adb.getprop("ro.board.platform") or ""
        chip = (hw or board).lower().strip()
        if chip:
            return chip
        # Fallback: /proc/cpuinfo
        cpuinfo = adb.shell("cat /proc/cpuinfo 2>/dev/null | grep -i 'hardware\\|machine' | head -n 2")
        m = re.search(r"(?:Hardware|machine)\s*:\s*(\S+)", cpuinfo, re.IGNORECASE)
        if m:
            return m.group(1).lower()
    except Exception:  # noqa: BLE001
        pass
    return ""


def _chip_info(chip: str) -> dict:
    """Gibt SoC-Infos und BROM-Kompatibilität zurück."""
    chip_lower = chip.lower()
    soc = next((v for k, v in MTK_SOCS.items() if k in chip_lower), {})
    brom = next((v for k, v in BROM_COMPATIBLE.items() if k in chip_lower), {})
    return {"soc": soc, "brom": brom}


# ── ADB-basierte MTK-Diagnose ─────────────────────────────────────────────────

def chip_info(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("MTK Chip-Erkennung & SoC-Info", ui.CYAN)
    chip = _detect_chip(adb) or data.get("platform", "") or data.get("hardware", "")
    info = _chip_info(chip)
    soc  = info["soc"]
    brom = info["brom"]
    print()
    ui.kv("Erkannter Chip",  chip or "unbekannt")
    if soc:
        ui.kv("SoC-Name",    soc.get("name", "—"))
        ui.kv("Architektur", soc.get("arch", "—"))
        ui.kv("Prozess",     soc.get("process", "—"))
        ui.kv("5G",          "JA" if soc.get("5g") else "NEIN")
    if brom:
        print()
        ui.rule("BROM-Exploit Kompatibilität", ui.BYELLOW)
        ui.kv("Exploit",     brom.get("exploit", "—"))
        ui.kv("Testpoint",   brom.get("testpoint", "—"))
        ui.kv("Hinweise",    brom.get("notes", "—"))
    else:
        ui.warn("Chip nicht in BROM-Kompatibilitätsliste – manuell prüfen!")
    print()
    # Alle getprop MTK-relevanten Werte
    ui.rule("MTK getprop-Werte", ui.GREY)
    props = adb.shell("getprop | grep -iE 'mediatek|mtk|helio|dimensity|hardware|platform' | head -n 30")
    print(props or "  (keine MTK-Props gefunden)")
    ui.pause()


def nvram_backup(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("NVRAM/EFS Backup (MTK)", ui.CYAN)
    is_root = bool(st.get("is_root"))
    out_dir = _w("nvram")
    lines = []
    print()
    ui.info("Suche MTK-NVRAM-Verzeichnisse …")
    # Bekannte MTK-NVRAM-Pfade
    nvram_paths = [
        "/mnt/vendor/nvdata", "/mnt/vendor/nvram",
        "/nvdata", "/nvram",
        "/dev/block/by-name/nvdata",
        "/dev/block/by-name/nvram",
        "/data/nvram",
    ]
    for path in nvram_paths:
        exists = adb.shell(f"ls {path} 2>/dev/null | head -n 3", root=is_root)
        if exists.strip():
            status = f"{ui.BGREEN}✓{ui.RESET}"
            lines.append(path)
        else:
            status = f"{ui.GREY}✗{ui.RESET}"
        print(f"  {status}  {path}")
    print()
    if not lines:
        ui.warn("Keine NVRAM-Verzeichnisse gefunden. Root nötig? → Menü 20")
        ui.pause(); return
    if ui.confirm(f"NVRAM von {len(lines)} Pfad(en) sichern?", True):
        for path in lines:
            ui.info(f"Ziehe {path} …")
            dest = os.path.join(out_dir, path.replace("/", "_").lstrip("_"))
            os.makedirs(dest, exist_ok=True)
            adb.raw(["pull", path, dest], timeout=120)
        ui.ok(f"NVRAM gesichert → {out_dir}")
    ui.pause()


def nvram_restore(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("NVRAM Restore (MTK) – GEFÄHRLICH", ui.BRED)
    ui.warn("Falsche NVRAM-Daten können IMEI, Netzwerk und Kalibrierung zerstören!")
    if not ui.confirm("Verstanden – trotzdem fortfahren?", False):
        return
    src = ui.ask("Pfad zum NVRAM-Backup-Verzeichnis").strip()
    src = os.path.expanduser(src) if src else ""
    if not src or not os.path.isdir(src):
        ui.err("Verzeichnis nicht gefunden."); ui.pause(); return
    dest = ui.ask("Ziel-Pfad auf Gerät (z.B. /mnt/vendor/nvdata)").strip()
    if not dest:
        return
    ui.danger(f"Schreibe {src} → {dest}")
    if ui.confirm("Jetzt zurückschreiben?", False):
        adb.raw(["push", src, dest], timeout=300)
        ui.ok("Restore abgeschlossen. Neustart empfohlen.")
    ui.pause()


def preloader_dump(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Preloader dumpen (via ADB + BROM)", ui.CYAN)
    is_root = bool(st.get("is_root"))
    out = _w("dumps", "preloader.img")
    print()
    ui.info("Methode 1: ADB (Root nötig)")
    # Versuche via ADB
    preloader_nodes = [
        "/dev/block/by-name/preloader",
        "/dev/block/by-name/preloader_a",
        "/dev/block/by-name/lk",
        "/dev/block/mmcblk0boot0",
    ]
    done = False
    for node in preloader_nodes:
        exists = adb.shell(f"ls {node} 2>/dev/null", root=is_root)
        if exists.strip():
            ui.info(f"Lese {node} …")
            tmp = "/sdcard/preloader_dump.img"
            adb.shell(f"dd if={node} of={tmp} bs=1M 2>/dev/null", root=is_root, timeout=120)
            adb.raw(["pull", tmp, out], timeout=60)
            if os.path.isfile(out):
                ui.ok(f"Preloader-Dump: {out}  ({os.path.getsize(out):,} Bytes)")
                done = True
                break
    if not done:
        ui.warn("Via ADB nicht möglich – BROM-Methode empfohlen.")
        if _need_mtk():
            ui.info("Dumpe via BROM (mtk r preloader) …")
            mtk(["r", "preloader", out], timeout=300)
            if os.path.isfile(out):
                ui.ok(f"Preloader-Dump: {out}")
            else:
                ui.err("Dump fehlgeschlagen.")
    ui.pause()


def scatter_analyze(adb, dev, st, data) -> None:
    """Generiert eine Scatter-ähnliche Partitions-Übersicht aus dem Gerät."""
    ui.clear(); ui.rule("Scatter-Analyse / Partitionstabelle", ui.CYAN)
    is_root = bool(st.get("is_root"))
    print()
    # Methode 1: /dev/block/by-name
    ui.info("Partitionen via /dev/block/by-name …")
    block_by_name = adb.shell("ls -la /dev/block/by-name/ 2>/dev/null", root=is_root)
    # Methode 2: cat /proc/partitions
    proc_parts = adb.shell("cat /proc/partitions 2>/dev/null")
    # Methode 3: printgpt via mtk
    gpt_output = ""
    if _have_mtk():
        ui.info("Lese GPT via mtkclient …")
        _, gpt_output = mtk(["printgpt"], timeout=180, stream=False)
    lines = ["# SCATTER-ANALYSE", f"# {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    if block_by_name.strip():
        lines += ["== /dev/block/by-name ==", block_by_name, ""]
    if proc_parts.strip():
        lines += ["== /proc/partitions ==", proc_parts, ""]
    if gpt_output.strip():
        lines += ["== GPT (mtkclient printgpt) ==", gpt_output, ""]
    body = "\n".join(lines) + "\n"
    out = _w("scatter_analysis.txt")
    with open(out, "w") as f:
        f.write(body)
    ui.show_report(body, "Scatter-Analyse", out)
    ui.pause()


def frp_bypass_mtk(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("FRP-Bypass (MTK via seccfg/BROM)", ui.BRED)
    ui.warn("FRP-Bypass nur an eigenen Geräten oder mit ausdrücklicher Genehmigung!")
    if not ui.confirm("Ich bestätige: dies ist mein eigenes Gerät oder ich bin autorisiert.", False):
        return
    print()
    ui.rule("Methode 1: ADB-basiert (wenn ADB aktiv)", ui.CYAN)
    frp_methods = [
        ("FRP-Partition löschen",
         "dd if=/dev/zero of=/dev/block/by-name/frp bs=512 count=2048 2>/dev/null || "
         "dd if=/dev/zero of=/dev/block/by-name/config bs=512 count=2048 2>/dev/null"),
        ("FRP-Flag via Settings",
         "content insert --uri content://settings/global --bind name:s:frp_credential_handle --bind value:s:"),
        ("FRP via Persist löschen",
         "rm -f /data/misc/adb/adb_keys 2>/dev/null; "
         "settings put global setup_wizard_has_run 1"),
    ]
    is_root = bool(st.get("is_root"))
    for name, cmd in frp_methods:
        print(f"  {ui.BCYAN}▸{ui.RESET} {name}")
        result = adb.shell(cmd, root=is_root)
        print(f"    {ui.GREY}{result[:80] if result else '(kein Output)'}{ui.RESET}")
    print()
    ui.rule("Methode 2: BROM seccfg (ohne ADB)", ui.CYAN)
    if _need_mtk():
        ui.info("seccfg unlock löscht FRP auf vielen MTK-Geräten.")
        if ui.confirm("seccfg unlock via BROM ausführen?", False):
            mtk(["da", "seccfg", "unlock"], timeout=300)
            ui.ok("seccfg unlock ausgeführt. Gerät neu starten.")
    ui.pause()


def engineer_mode(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("MTK Engineer Mode", ui.CYAN)
    print()
    ui.info("Startet MTK-interne Diagnose-Apps via Intent …")
    engineer_intents = [
        ("Engineer Mode (Haupt)",      "com.mediatek.engineermode/.EngineerMode"),
        ("CDS Info",                   "com.mediatek.CDS_INFO/.TestingActivity"),
        ("Network Signaling Logger",   "com.mediatek.networksignallogger/.MainActivity"),
        ("Log2SD / MTK Logger",        "com.mediatek.mtklogger/.MainActivity"),
        ("SIM Toolkits Debug",         "com.mediatek.simtoolkit/.MainActivity"),
        ("APN Test",                   "com.mediatek.apn.test/.MainActivity"),
        ("WiFi Engineer Mode",         "com.mediatek.wlantest/.MainActivity"),
    ]
    for name, component in engineer_intents:
        print(f"  {ui.BCYAN}▸{ui.RESET} {name}")
    print()
    sel = input(f"  {ui.BOLD}Nr. starten (1-{len(engineer_intents)}, leer=Abbruch): {ui.RESET}").strip()
    if not sel:
        return
    try:
        name, comp = engineer_intents[int(sel) - 1]
        ui.info(f"Starte {name} …")
        result = adb.shell(f"am start -n {comp}")
        print(f"  {result}")
    except (ValueError, IndexError):
        ui.err("Ungültige Auswahl.")
    print()
    # Geheimcodes
    ui.rule("MTK Geheimcodes (im Wähler eingeben)", ui.GREY)
    codes = [
        ("*#*#3646633#*#*", "Engineer Mode"),
        ("*#*#837#*#*",     "MTK Logger"),
        ("*#*#4636#*#*",    "Phone Info / Testing"),
        ("*#*#225#*#*",     "Calendar Storage"),
        ("*#*#8351#*#*",    "Voice Dialer Log"),
        ("*#*#7594#*#*",    "Power Off direkt"),
        ("*#07#",           "SAR/HAC-Test"),
    ]
    for code, name in codes:
        print(f"  {ui.BYELLOW}{code:20}{ui.RESET}  {name}")
    ui.pause()


def dram_test(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("DRAM / Speicher-Test (MTK)", ui.CYAN)
    is_root = bool(st.get("is_root"))
    print()
    ui.info("RAM-Informationen abrufen …")
    # RAM-Info
    ram_total = adb.shell("cat /proc/meminfo | grep MemTotal")
    ram_free  = adb.shell("cat /proc/meminfo | grep MemAvailable")
    ram_type  = adb.shell("getprop ro.product.ram 2>/dev/null || "
                          "dumpsys meminfo | grep 'Total RAM' | head -n 1")
    ui.kv("RAM gesamt",  ram_total.strip())
    ui.kv("RAM frei",    ram_free.strip())
    ui.kv("RAM-Typ",     ram_type.strip() or "unbekannt")
    print()
    # LPDDR-Typ aus getprop
    ddr = adb.shell("getprop | grep -iE 'ddr|lpddr|ram.size' | head -n 5")
    if ddr.strip():
        print(ddr)
    # MTK-spezifisch: DRAM-Status via /proc/hps
    hps = adb.shell("cat /sys/kernel/hps/enabled 2>/dev/null; cat /sys/kernel/hps/cur_loads 2>/dev/null")
    if hps.strip():
        print(f"\n  HPS (Hotplug Scheduler):\n  {hps}")
    # Speicher-Stress (kurzfristig)
    ui.info("Kurz-Stresstest: Allocate 100MB …")
    stress = adb.shell("dd if=/dev/urandom bs=1M count=100 of=/dev/null 2>&1 | tail -n 1", timeout=30)
    print(f"  {stress}")
    ui.ok("DRAM-Test abgeschlossen.")
    ui.pause()


def brom_mode_guide(adb, dev, st, data) -> None:
    chip = _detect_chip(adb) or data.get("platform", "")
    brom_info = _chip_info(chip).get("brom", {})
    ui.clear(); ui.rule("BROM-Modus Anleitung", ui.CYAN)
    print()
    if chip:
        ui.kv("Erkannter Chip", chip)
        exploit = brom_info.get("exploit", "unbekannt")
        testpoint = brom_info.get("testpoint", "unbekannt")
        ui.kv("Exploit-Typ",   exploit)
        ui.kv("Testpoint",     testpoint)
        notes = brom_info.get("notes", "")
        if notes:
            ui.kv("Hinweise",  notes)
    print()
    ui.rule("Standard-Methode (Vol-Keys)", ui.BYELLOW)
    for step in [
        "1. Gerät vollständig ausschalten (Power Off)",
        "2. Vol-Hoch UND Vol-Runter gleichzeitig gedrückt halten",
        "3. USB-Kabel zum PC einstecken (Tasten weiter halten)",
        "4. Ca. 3-5 Sekunden warten bis mtkclient 'Device found' meldet",
        "5. Tasten loslassen",
        "",
        "Alternative: Akku entfernen → USB einstecken (wenn Akku herausnehmbar)",
    ]:
        print(f"   {step}")
    print()
    ui.rule("Testpoint-Methode (wenn Vol-Keys nicht funktionieren)", ui.BRED)
    for step in [
        "Benötigt Hardware-Öffnung des Geräts!",
        "1. Gerät öffnen, Mainboard freilegen",
        "2. Testpoint auf dem PCB identifizieren (nahe NAND/eMMC oder Preloader-Chip)",
        "3. Mit Metallpinzette/Draht Testpoint kurz mit GND verbinden",
        "4. Gleichzeitig USB einstecken",
        "5. Pinzette erst loslassen wenn mtkclient verbindet",
        "",
        "Testpoint-Koordinaten: https://forum.xda-developers.com → Gerätemodell suchen",
    ]:
        print(f"   {step}")
    print()
    ui.rule("USB-Treiber (Linux)", ui.GREY)
    for line in [
        "sudo apt install android-sdk-platform-tools",
        "# udev-Regel für MTK-BROM:",
        'echo \'SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666", GROUP="plugdev"\' | sudo tee /etc/udev/rules.d/99-mtk.rules',
        "sudo udevadm control --reload-rules && sudo udevadm trigger",
    ]:
        print(f"   {ui.BCYAN}{line}{ui.RESET}")
    ui.pause()


def mtk_adb_diagnostics(adb, dev, st, data) -> None:
    """Umfassende MTK-spezifische ADB-Diagnose."""
    ui.clear(); ui.rule("MTK ADB-Volldiagnose", ui.CYAN)
    is_root = bool(st.get("is_root"))
    out_lines = [f"# MTK VOLLDIAGNOSE\n# {time.strftime('%Y-%m-%d %H:%M:%S')}\n"]
    checks = [
        ("Chip",          "getprop ro.hardware"),
        ("Board",         "getprop ro.board.platform"),
        ("Baseband",      "getprop gsm.version.baseband"),
        ("MTK Build",     "getprop ro.mediatek.version.release"),
        ("MTK Platform",  "getprop ro.mediatek.platform"),
        ("MTK Chip",      "getprop ro.mediatek.chip_ver"),
        ("Preloader",     "getprop ro.boot.hardware"),
        ("RAM-Type",      "getprop ro.product.board"),
        ("CPU-ABI",       "getprop ro.product.cpu.abi"),
        ("Bootloader",    "getprop ro.bootloader"),
        ("Bootmode",      "getprop ro.boot.mode"),
        ("MTK Logger",    "getprop persist.mtklog.bootmtklog"),
        ("Engineer Mode", "getprop ro.build.type"),
        ("Secure Boot",   "getprop ro.boot.verifiedbootstate"),
        ("FRP Lock",      "getprop ro.boot.flash.locked"),
        ("SELinux",       "getenforce 2>/dev/null"),
        ("Verity",        "getprop ro.boot.veritymode"),
        ("ADB Auth",      "getprop service.adb.tcp.port"),
        ("MTK-Logger",    "getprop debug.emd.mux"),
    ]
    print()
    for label, cmd in checks:
        val = adb.shell(cmd).strip() or "—"
        ui.kv(f"{label:<20}", val)
        out_lines.append(f"{label}: {val}")
    print()
    # MTK-spezifische Prozesse
    ui.rule("MTK-Prozesse", ui.GREY)
    procs = adb.shell("ps -A 2>/dev/null | grep -iE 'mtk|mediatek|md_'  | head -n 15")
    print(procs or "  (keine MTK-Prozesse sichtbar)")
    out_lines.append(f"\nMTK-Prozesse:\n{procs}")
    # MTK-Partitionen
    ui.rule("MTK-Partitionen", ui.GREY)
    parts = adb.shell(
        "ls /dev/block/by-name/ 2>/dev/null | grep -iE 'nvram|nvdata|preloader|mba|"
        "modem|md1|seccfg|frp|persist|cache|vendor_boot' | head -n 20",
        root=is_root
    )
    print(parts or "  (nicht lesbar ohne Root)")
    out_lines.append(f"\nMTK-Partitionen:\n{parts}")
    # Export
    out_file = os.path.join(OUT, f"mtk_diagnostics_{int(time.time())}.txt")
    with open(out_file, "w") as f:
        f.write("\n".join(out_lines))
    ui.ok(f"Diagnose → {out_file}")
    ui.pause()


def partition_manager(adb, dev, st, data) -> None:
    """Interaktiver Partitions-Manager."""
    ui.clear(); ui.rule("Partitions-Manager (ADB + mtkclient)", ui.CYAN)
    is_root = bool(st.get("is_root"))
    # Alle Partitionen auflisten
    parts_raw = adb.shell("ls -la /dev/block/by-name/ 2>/dev/null", root=is_root)
    parts = re.findall(r"(\S+)\s*->\s*(\S+)", parts_raw)
    if not parts:
        ui.warn("Keine Partitionen per by-name lesbar. Root nötig?")
        # BROM-Fallback
        if _have_mtk() and ui.confirm("Partitionstabelle via mtkclient lesen?", False):
            mtk(["printgpt"], timeout=180)
        ui.pause(); return
    print()
    for i, (name, link) in enumerate(parts[:50], 1):
        print(f"  {ui.CYAN}{i:3d}{ui.RESET}  {name:<25}  {ui.GREY}{link}{ui.RESET}")
    print()
    sel = input(f"  {ui.BOLD}Partition wählen (Nr.) oder Name: {ui.RESET}").strip()
    if not sel:
        return
    if sel.isdigit():
        try:
            part_name, _ = parts[int(sel) - 1]
        except IndexError:
            ui.err("Ungültig."); ui.pause(); return
    else:
        part_name = sel
    # Aktionen für gewählte Partition
    print()
    ch = ui.menu(f"Aktion für: {part_name}", [
        ("1", "📖 Lesen / Dumpen (via ADB dd)"),
        ("2", "📖 Lesen / Dumpen (via mtkclient BROM)"),
        ("3", "📝 Flashen (via mtkclient BROM)"),
        ("4", "🔍 Hex-Dump erste 512 Bytes"),
        ("5", "📊 Größe anzeigen"),
    ], back_label="Zurück")
    if ch == "1":
        out = os.path.join(OUT, f"{part_name}.img")
        ui.info(f"dd → {out}")
        node = f"/dev/block/by-name/{part_name}"
        tmp = f"/sdcard/{part_name}_dump.img"
        adb.shell(f"dd if={node} of={tmp} 2>&1", root=True, timeout=300)
        adb.raw(["pull", tmp, out], timeout=120)
        if os.path.isfile(out):
            ui.ok(f"Dump: {out}  ({os.path.getsize(out):,} Bytes)")
        else:
            ui.err("Fehlgeschlagen.")
    elif ch == "2":
        if _need_mtk():
            out = os.path.join(OUT, f"{part_name}.img")
            mtk(["r", part_name, out], timeout=600)
            ui.ok(f"Dump: {out}") if os.path.isfile(out) else ui.err("Fehlgeschlagen.")
    elif ch == "3":
        if _need_mtk():
            img = os.path.expanduser(ui.ask("Pfad zum Image").strip())
            if os.path.isfile(img):
                ui.danger(f"Schreibe {img} → {part_name}")
                if ui.confirm("Jetzt flashen?", False):
                    mtk(["w", part_name, img], timeout=600)
    elif ch == "4":
        node = f"/dev/block/by-name/{part_name}"
        hexdump = adb.shell(f"dd if={node} bs=512 count=1 2>/dev/null | xxd 2>/dev/null || "
                            f"dd if={node} bs=512 count=1 2>/dev/null | od -A x -t x1z", root=True)
        print(f"\n{hexdump[:2000]}")
    elif ch == "5":
        node = f"/dev/block/by-name/{part_name}"
        size = adb.shell(f"blockdev --getsize64 {node} 2>/dev/null", root=True)
        print(f"  Größe: {size.strip() or '?'} Bytes")
    ui.pause()


def log_capture(adb, dev, st, data) -> None:
    """MTK-spezifische Log-Erfassung."""
    ui.clear(); ui.rule("MTK Log-Erfassung", ui.CYAN)
    print()
    ch = ui.menu("Log-Typ", [
        ("1", "📻 Radio/Baseband-Log (Modem)"),
        ("2", "🔋 MTK Logger / ADB Logcat"),
        ("3", "💥 Kernel-Crash-Log (mtk_pmlk)"),
        ("4", "🛡️  SELinux-Denials"),
        ("5", "📡 Telephony-Events"),
        ("6", "🔧 MTK-Proprietary Log (mobile_log)"),
    ], back_label="Zurück")
    out_base = _w("logs")
    if ch == "1":
        out = os.path.join(out_base, "radio.log")
        ui.info("Erfasse Radio-Log (30 Sekunden) …")
        adb.shell(f"logcat -b radio -d > /sdcard/radio.log 2>/dev/null")
        adb.raw(["pull", "/sdcard/radio.log", out], timeout=60)
        ui.ok(f"Radio-Log: {out}")
    elif ch == "2":
        out = os.path.join(out_base, "mtk_logcat.log")
        ui.info("Erfasse Logcat (alle Buffer) …")
        log = adb.shell("logcat -d -b all | head -n 2000")
        with open(out, "w") as f:
            f.write(log)
        ui.ok(f"Logcat: {out}")
    elif ch == "3":
        ui.info("Kernel-Crash-Log (mtk_pmlk) …")
        crash = adb.shell("cat /sys/fs/pstore/dmesg-ramoops-0 2>/dev/null || "
                          "cat /proc/last_kmsg 2>/dev/null | tail -n 100")
        out = os.path.join(out_base, "kernel_crash.log")
        with open(out, "w") as f:
            f.write(crash or "(kein Crash-Log)")
        ui.ok(f"Crash-Log: {out}")
    elif ch == "4":
        denials = adb.shell("dmesg 2>/dev/null | grep avc | tail -n 50")
        print(denials or "Keine SELinux-Denials")
    elif ch == "5":
        tel = adb.shell("logcat -d -s TelephonyManager:V PhoneInterfaceManager:V | tail -n 100")
        out = os.path.join(out_base, "telephony.log")
        with open(out, "w") as f:
            f.write(tel)
        ui.ok(f"Telephony-Log: {out}")
    elif ch == "6":
        mobile_log = adb.shell("ls /sdcard/mtklog/ 2>/dev/null; ls /sdcard/mobile_log/ 2>/dev/null")
        print(mobile_log or "MTK mobile_log nicht gefunden (ggf. Engineer Mode aktivieren)")
    ui.pause()


def imei_tools(adb, dev, st, data) -> None:
    """IMEI-Diagnose und MTK-spezifische IMEI-Tools."""
    ui.clear(); ui.rule("IMEI-Tools (MTK)", ui.CYAN)
    is_root = bool(st.get("is_root"))
    print()
    # IMEI lesen
    imei1 = adb.shell("service call iphonesubinfo 1 s16 com.android.phone 2>/dev/null | "
                      "grep -oP \"'[^']+'\" | tr -d \"'\\n\" 2>/dev/null")
    if not imei1 or len(imei1.strip()) < 10:
        imei1 = adb.shell("getprop gsm.device.hardware.imei 2>/dev/null || "
                          "getprop ro.ril.oem.imei 2>/dev/null")
    imei2 = adb.shell("service call iphonesubinfo 1 i32 1 s16 com.android.phone 2>/dev/null | "
                      "grep -oP \"'[^']+'\" | tr -d \"'\\n\" 2>/dev/null")
    ui.kv("IMEI Slot 1", imei1.strip() or "—")
    ui.kv("IMEI Slot 2", imei2.strip() or "— (Dual-SIM?)")
    # Luhn-Validierung
    def luhn_check(imei: str) -> bool:
        digits = [int(d) for d in imei if d.isdigit()]
        if len(digits) != 15:
            return False
        total = 0
        for i, d in enumerate(digits):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        return total % 10 == 0
    clean1 = re.sub(r"[^0-9]", "", imei1)
    if len(clean1) == 15:
        valid = luhn_check(clean1)
        print(f"  Luhn-Prüfung: {ui.BGREEN}✓ GÜLTIG{ui.RESET}" if valid
              else f"  Luhn-Prüfung: {ui.BRED}✗ UNGÜLTIG{ui.RESET}")
        # TAC / Hersteller
        tac = clean1[:8]
        ui.kv("TAC (Gerätehersteller)", tac)
    print()
    # NVRAM-IMEI (Root)
    if is_root:
        ui.rule("NVRAM-IMEI (Root)", ui.GREY)
        nvram_imei = adb.shell(
            "cat /mnt/vendor/nvram/APCFG/APRDEB/IMEI 2>/dev/null | strings | head -n 2 || "
            "cat /nvdata/APCFG/APRDEB/IMEI 2>/dev/null | strings | head -n 2",
            root=True
        )
        print(nvram_imei or "  (NVRAM-IMEI nicht lesbar)")
    ui.pause()


def mtk_deep_flash_guide(adb, dev, st, data) -> None:
    """Erweiterte Anleitung für Deep Flash / Preloader-Reparatur."""
    chip = _detect_chip(adb) or data.get("platform", "")
    ui.clear(); ui.rule("Deep Flash / Preloader-Reparatur", ui.BRED)
    print()
    ui.warn("ACHTUNG: Falscher Preloader oder SPFlashtool-Image kann das Gerät PERMANENT bricken!")
    print()
    for step in [
        f"Chipsatz:  {chip or 'unbekannt – manuell ermitteln!'}",
        "",
        "1. SPFlashtool (Download-Tool) für MTK:",
        "   → github.com/fastbootguy/SP-Flash-Tool-source",
        "   Download über: spflashtool.com (veraltet) oder XDA",
        "",
        "2. Scatter-Datei beschaffen:",
        "   a) Von einer passenden ROM (TWRP-Download, Stock-ROM)",
        "   b) Oder mit mtkclient aus Gerät auslesen: mtk printgpt > scatter.txt",
        "",
        "3. Preloader-Reparatur via mtkclient (BROM-Modus):",
        "   mtk w preloader preloader.img",
        "   # Für A/B-Geräte:",
        "   mtk w preloader_a preloader.img",
        "   mtk w preloader_b preloader.img",
        "",
        "4. Vollständiger Flash (alle Partitionen):",
        "   mtk wl <ordner-mit-images>",
        "",
        "5. Spezielle Flags nach dem Flash:",
        "   mtk da seccfg unlock  (Bootloader freischalten)",
        "   mtk reset             (Gerät neu starten)",
        "",
        "Ressourcen:",
        "  https://github.com/bkerler/mtkclient",
        "  https://xdaforums.com → Modell suchen → Development",
    ]:
        print(f"   {ui.GREY}{step}{ui.RESET}")
    ui.pause()


def pip_autoinstall_all(adb, dev, st, data) -> None:
    """Installiert ALLE pip-Pakete aller 50 Labore in ~/panzer_venv."""
    ui.clear(); ui.rule("PIP AUTO-INSTALL – ALLE Pakete vorinstallieren", ui.BGREEN)
    print()
    # Lade Paketliste aus labsetup
    try:
        from . import labsetup
        all_pip = []
        for tc in labsetup.TOOLCHAINS:
            for p in tc.get("pip", []):
                if p and p not in all_pip:
                    all_pip.append(p)
    except Exception:  # noqa: BLE001
        # Hardcoded Fallback
        all_pip = [
            "mtkclient", "frida-tools", "objection", "apkleaks", "androguard",
            "mitmproxy", "volatility3", "yara-python", "pefile", "capstone",
            "pwntools", "ropgadget", "keystone-engine", "scapy", "python-nmap",
            "aleapp", "ileapp", "andriller", "exifread", "pyserial", "pyusb",
            "pyscard", "sherlock-project", "holehe", "maigret", "instaloader",
            "yt-dlp", "awscli", "boto3", "python-docx", "reportlab",
            "timesketch-import-client", "pip-check", "pipdeptree", "passlib",
            "boofuzz", "pythonfuzz", "flare-floss", "hindsight", "mail-parser",
            "extract-msg", "colorama", "pycryptodome", "requests", "httpx",
            "beautifulsoup4",
        ]
    venv_path = os.path.expanduser("~/panzer_venv")
    venv_python = os.path.join(venv_path, "bin", "python3")
    venv_pip = os.path.join(venv_path, "bin", "pip")
    print(f"  {ui.BOLD}{len(all_pip)} pip-Pakete werden in ~/panzer_venv installiert.{ui.RESET}")
    print(f"  Pakete: {ui.GREY}{' '.join(all_pip[:15])} …{ui.RESET}")
    print()
    if not ui.confirm(f"Alle {len(all_pip)} Pakete jetzt installieren?", True):
        return
    # venv erstellen
    if not os.path.isfile(venv_python):
        ui.info("Erstelle ~/panzer_venv …")
        if subprocess.call([sys.executable, "-m", "venv", venv_path]) != 0:
            ui.err("python3-venv fehlt: sudo apt install python3-venv")
            ui.pause(); return
        subprocess.call([venv_python, "-m", "pip", "install", "--upgrade", "pip"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Pakete in Batches installieren
    BATCH = 10
    failed = []
    for i in range(0, len(all_pip), BATCH):
        batch = all_pip[i:i+BATCH]
        ui.info(f"Installiere Batch {i//BATCH+1}: {', '.join(batch)}")
        rc = subprocess.call([venv_pip, "install", "--upgrade"] + batch)
        if rc != 0:
            failed.extend(batch)
    print()
    if failed:
        ui.warn(f"{len(failed)} Pakete fehlgeschlagen: {', '.join(failed)}")
        ui.info("Versuche fehlgeschlagene einzeln …")
        for pkg in failed:
            subprocess.call([venv_pip, "install", "--upgrade", pkg])
    ui.ok(f"Installation abgeschlossen! venv: {venv_path}")
    ui.info(f"Aktivieren: source {venv_path}/bin/activate")
    ui.pause()


# ===================================================================== #
#  Menü
# ===================================================================== #
def menu(adb, dev, st, data: dict) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🔶 MediaTek Suite · BROM · Root · Flash · Forensik · MAXIMAL")
        chip = _detect_chip(adb) or data.get("platform", "") or data.get("hardware", "")
        chip_inf = _chip_info(chip)
        soc_name = chip_inf["soc"].get("name", "") if chip_inf["soc"] else ""
        ui.kv("Chip",      f"{chip}  {ui.GREY}({soc_name}){ui.RESET}" if soc_name else chip or "—")
        ui.kv("Gerät",     f"{data.get('brand','')} {data.get('model','')}")
        ui.kv("mtkclient", f"{ui.BGREEN}✓ {_have_mtk()}{ui.RESET}" if _have_mtk()
               else f"{ui.BRED}✗ fehlt – Auto-Install via Option P{ui.RESET}")
        print()
        ch = ui.menu("Aktionen", [
            # ── Root & Flash ──────────────────────────────────────────
            ("1",  f"{ui.BGREEN}{ui.BOLD}🚀 AUTO-ROOT (Magisk via BROM, meist OHNE Wipe){ui.RESET}"),
            ("2",  "🔓 Bootloader entsperren (seccfg unlock, ohne Wipe)"),
            ("3",  "🔒 Bootloader sperren (seccfg lock)"),
            # ── Partition & Backup ────────────────────────────────────
            ("4",  "📖 Partitionstabelle (printgpt + scatter-Analyse)"),
            ("5",  "📤 Einzelne Partition dumpen"),
            ("6",  "💾 Voll-Backup ALLER Partitionen"),
            ("7",  "📥 Partition flashen (write)"),
            ("8",  "🗂️  Interaktiver Partitions-Manager"),
            # ── Spezial-Dumps ─────────────────────────────────────────
            ("9",  "🔧 Preloader dumpen (ADB dd + BROM)"),
            ("10", "💽 NVRAM/EFS Backup (MTK /nvdata /nvram)"),
            ("11", "🔄 NVRAM Restore – GEFÄHRLICH"),
            # ── Diagnose ─────────────────────────────────────────────
            ("12", "🧪 Chip-Erkennung & SoC-Info (Helio/Dimensity)"),
            ("13", "📊 MTK ADB-Volldiagnose (Props/Prozesse/Partitionen)"),
            ("14", "🧠 DRAM / Speicher-Test"),
            ("15", "📱 Engineer Mode / Geheimcodes"),
            ("16", "📜 IMEI-Tools (Slot1/2, Luhn, NVRAM-IMEI)"),
            # ── Sicherheit ────────────────────────────────────────────
            ("17", "🛡️  FRP-Bypass (seccfg + ADB-Methoden)"),
            ("18", "↩  vbmeta verity deaktivieren + zurückschreiben"),
            # ── Logs ─────────────────────────────────────────────────
            ("19", "📋 Log-Erfassung (Radio/Baseband/Crash/SELinux)"),
            # ── Info & Anleitungen ────────────────────────────────────
            ("20", "📡 BROM-Modus Anleitung (Vol-Keys / Testpoint)"),
            ("21", "🔥 Deep Flash / Preloader-Reparatur Guide"),
            ("22", "↻  Gerät zurücksetzen (mtk reset)"),
            # ── System ───────────────────────────────────────────────
            ("P",  f"{ui.BGREEN}{ui.BOLD}⬇  PIP AUTO-INSTALL – ALLE Pakete vorinstallieren{ui.RESET}"),
            ("?",  "ℹ  Voraussetzungen & BROM-Anleitung"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return

        dispatch = {
            "1":  auto_root,
            "2":  unlock,
            "3":  lock,
            "4":  scatter_analyze,
            "5":  dump_part,
            "6":  full_backup,
            "7":  flash_part,
            "8":  partition_manager,
            "9":  preloader_dump,
            "10": nvram_backup,
            "11": nvram_restore,
            "12": chip_info,
            "13": mtk_adb_diagnostics,
            "14": dram_test,
            "15": engineer_mode,
            "16": imei_tools,
            "17": frp_bypass_mtk,
            "18": fix_vbmeta,
            "19": log_capture,
            "20": brom_mode_guide,
            "21": mtk_deep_flash_guide,
            "22": reset_dev,
            "p":  pip_autoinstall_all,
            "?":  show_help,
        }
        fn = dispatch.get(ch)
        if fn:
            try:
                fn(adb, dev, st, data)
            except Exception as e:  # noqa: BLE001
                ui.err(f"Fehler: {e}")
                LOG.exception("mediatek", e)
                ui.pause()


def show_help(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("MediaTek BROM – Voraussetzungen & Hilfe", ui.CYAN)
    print()
    for line in [
        "INSTALLATION:",
        "  Drücke P im Menü → Auto-Install aller pip-Pakete in ~/panzer_venv",
        "  Oder manuell:  pip install mtkclient",
        "                 source ~/panzer_venv/bin/activate",
        "",
        "BROM-MODUS:",
        "  1. Gerät ausschalten",
        "  2. Vol-Hoch + Vol-Runter halten",
        "  3. USB einstecken → warten bis mtkclient verbindet",
        "",
        "EXPLOIT-TYPEN:",
        "  kamakiri  – kein Testpoint nötig (ältere Chips)",
        "  hashimoto – manchmal Testpoint (neuere Chips)",
        "  amonet    – Testpoint fast immer nötig (sehr alte Chips)",
        "",
        "USB-TREIBER (Kali Linux):",
        '  echo \'SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", MODE="0666"\' | sudo tee /etc/udev/rules.d/99-mtk.rules',
        "  sudo udevadm control --reload-rules",
        "",
        "RESSOURCEN:",
        "  https://github.com/bkerler/mtkclient",
        "  https://github.com/topjohnwu/Magisk",
        "  https://xdaforums.com → Gerät suchen",
    ]:
        print(f"   {ui.GREY}{line}{ui.RESET}")
    ui.pause()


def _need_mtk() -> bool:
    if _have_mtk():
        return True
    ui.warn("mtkclient nicht gefunden!")
    print()
    print(f"  Drücke {ui.BOLD}P{ui.RESET} im Menü für automatische Installation in ~/panzer_venv.")
    print(f"  Oder: {ui.BCYAN}pip install mtkclient{ui.RESET}")
    print()
    if ui.confirm("mtkclient JETZT automatisch installieren?", True):
        if _auto_install_mtkclient():
            return bool(_have_mtk())
    ui.pause()
    return False


def unlock(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Bootloader entsperren (seccfg)", ui.CYAN)
    if not _need_mtk():
        return
    ui.warn("Entsperrt den Bootloader. Auf vielen MTK-Geräten OHNE Datenverlust – nicht garantiert!")
    if not ui.confirm("'mtk da seccfg unlock' ausführen (Gerät im BROM)?", False):
        return
    rc, _ = mtk(["da", "seccfg", "unlock"], timeout=300)
    (ui.ok if rc == 0 else ui.err)("Unlock " + ("OK – am Gerät bestätigen, dann neu starten." if rc == 0 else "FEHLGESCHLAGEN."))
    ui.pause()


def lock(adb, dev, st, data) -> None:
    if not _need_mtk():
        return
    if ui.confirm("Bootloader sperren (mtk da seccfg lock)?", False):
        mtk(["da", "seccfg", "lock"], timeout=300)
    ui.pause()


def dump_part(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Partition dumpen", ui.CYAN)
    if not _need_mtk():
        return
    part = ui.ask("Partition (z.B. boot, vbmeta, recovery, userdata, nvdata)")
    if not part:
        return
    out = os.path.join(OUT, f"{part}.img")
    rc, _ = mtk(["r", part, out], timeout=1200)
    (ui.ok if os.path.isfile(out) else ui.err)(f"Dump: {out}" if os.path.isfile(out) else "Dump fehlgeschlagen.")
    ui.pause()


def full_backup(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Voll-Backup aller Partitionen", ui.CYAN)
    if not _need_mtk():
        return
    out = _w("full_dump")
    ui.warn("Liest ALLE Partitionen – kann sehr groß sein & Stunden dauern.")
    if ui.confirm("Starten?", False):
        mtk(["rl", out], timeout=7200)
        ui.ok(f"Backup-Ordner: {out}")
    ui.pause()


def flash_part(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Partition flashen", ui.CYAN)
    if not _need_mtk():
        return
    part = ui.ask("Ziel-Partition (z.B. boot, recovery, vbmeta)")
    img = os.path.expanduser(ui.ask("Pfad zum Image"))
    if not part or not os.path.isfile(img):
        ui.err("Partition/Datei ungültig."); ui.pause(); return
    ui.danger(f"Schreibe {img} → {part}. Falsches Image kann hart bricken!")
    if ui.confirm("Wirklich flashen?", False):
        rc, _ = mtk(["w", part, img], timeout=1200)
        (ui.ok if rc == 0 else ui.err)("Geflasht." if rc == 0 else "Fehlgeschlagen.")
    ui.pause()


def fix_vbmeta(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("vbmeta verity deaktivieren", ui.CYAN)
    if not _need_mtk():
        return
    out = os.path.join(OUT, "vbmeta.img")
    ui.info("Lese vbmeta …")
    mtk(["r", "vbmeta", out], timeout=300)
    if not os.path.isfile(out):
        ui.err("vbmeta nicht lesbar."); ui.pause(); return
    # Flags setzen: disable-verity + disable-verification
    try:
        with open(out, "rb+") as f:
            data_bytes = bytearray(f.read())
        # Byte 123 (flags offset in vbmeta header)
        if len(data_bytes) > 128:
            data_bytes[123] = 3  # bit 0: disable-verity, bit 1: disable-verification
            with open(out, "wb") as f:
                f.write(data_bytes)
            ui.ok("Flags gesetzt (disable-verity + disable-verification).")
        else:
            ui.warn("vbmeta zu klein – möglicherweise falsches Image.")
    except Exception as e:  # noqa: BLE001
        ui.err(str(e))
    if ui.confirm("Zurückschreiben (mtk w vbmeta)?", False):
        mtk(["w", "vbmeta", out], timeout=300)
    ui.pause()


def reset_dev(adb, dev, st, data) -> None:
    if _have_mtk():
        mtk(["reset"], timeout=30)
    ui.pause()


def auto_root(adb, dev, st, data) -> None:
    ui.clear(); ui.banner(subtitle="🚀 MediaTek Auto-Root (Magisk via BROM)")
    if not _need_mtk():
        return
    ui.info("Ablauf: seccfg unlock → boot dumpen → on-device patchen → vbmeta → zurückschreiben.")
    ui.warn("Gerät muss im BROM-Modus sein (Hilfe: Menü 20). Für on-device Patchen kurz normal booten.")
    if not ui.confirm("Auto-Root starten?", False):
        return

    try:
        from .samsung import (_disable_vbmeta, _download_magisk_apk,
                              _extract_magisk_bins, _patch_boot_ondevice)
    except ImportError:
        ui.err("samsung.py fehlt – Magisk-Patch nicht möglich."); ui.pause(); return

    # 1) Unlock
    ui.rule("1 · Bootloader entsperren (seccfg)", ui.CYAN)
    if ui.confirm("seccfg unlock?", True):
        mtk(["da", "seccfg", "unlock"], timeout=300)

    # 2) Dumps
    ui.rule("2 · boot.img & vbmeta.img lesen (BROM)", ui.CYAN)
    boot = os.path.join(OUT, "boot.img")
    vb   = os.path.join(OUT, "vbmeta.img")
    mtk(["r", "boot", boot], timeout=600)
    mtk(["r", "vbmeta", vb], timeout=300)
    if not os.path.isfile(boot):
        ui.err("boot.img nicht lesbar."); ui.pause(); return
    ui.ok(f"boot.img: {boot}")

    # 3) Magisk
    ui.rule("3 · Magisk APK vorbereiten", ui.CYAN)
    apk = _download_magisk_apk()
    if not apk:
        ui.pause(); return
    ui.info("Gerät NORMAL booten (entsperrter BL) → ADB aktivieren → ENTER")
    ui.pause("Wenn Gerät gebootet & ADB erreichbar: ENTER")
    abi = adb.getprop("ro.product.cpu.abi") or "arm64-v8a"
    mdir = _extract_magisk_bins(apk, abi)
    adb.raw(["install", "-r", apk], timeout=120)

    # 4) On-device patchen
    ui.rule("4 · boot.img on-device patchen", ui.CYAN)
    patched = _patch_boot_ondevice(adb, dev, boot, mdir)
    if not patched:
        ui.err("Patchen fehlgeschlagen."); ui.pause(); return

    # 5) vbmeta
    if os.path.isfile(vb):
        try:
            with open(vb, "rb+") as f:
                b = bytearray(f.read())
            if len(b) > 128:
                b[123] = 3
                with open(vb, "wb") as f:
                    f.write(b)
            ui.ok("vbmeta verity deaktiviert.")
        except Exception:  # noqa: BLE001
            pass

    # 6) Zurück in BROM
    ui.rule("5 · In BROM zurück → flashen", ui.CYAN)
    ui.info("Gerät wieder in BROM-Modus (Anleitung: Menü 20).")
    ui.pause("Wenn BROM bereit: ENTER")
    ui.danger(f"Schreibe boot{' + vbmeta' if os.path.isfile(vb) else ''} zurück.")
    if ui.confirm("Flashen?", False):
        mtk(["w", "boot", patched], timeout=600)
        if os.path.isfile(vb):
            mtk(["w", "vbmeta", vb], timeout=300)
        mtk(["reset"], timeout=30)
        ui.ok("Fertig! Gerät startet. Magisk-App öffnen → Direct Install. 🎉")
    ui.pause()
