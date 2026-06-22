"""Samsung Root/Flash-Suite (Smartphone · Tablet · Watch) – Heimdall/Odin + Magisk.

Vollautomatischer Ablauf, soweit technisch möglich (physische Tastenkombis bleiben
manuell). Funktionen:

  1) AUTO-ROOT (Magisk):   Firmware holen (samloader) → AP-Tar → boot.img extrahieren
                            → on-device mit magiskboot patchen (ohne Root!) → vbmeta
                            verity deaktivieren → via heimdall flashen.
  2) TWRP-FLASHER:         Recovery-Image via heimdall flashen.
  3) MAGISK-MODUL-FLASHER: .zip-Modul installieren (root: magisk --install-module,
                            sonst via TWRP-Sideload).

Benötigt: heimdall (apt install heimdall-flash), optional samloader (pip install
samloader) für Auto-Firmware. lz4 zum Entpacken der AP-Images.

Hinweis Watch: Wear-OS-Watches (Galaxy Watch4+) gehen wie Phones; ältere Tizen-
Watches sind NICHT Magisk-rootbar (anderes OS).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

from . import ui, usb
from .util import human_size, safe_download, safe_extract_member, safe_join

WORK = os.path.expanduser("~/Schreibtisch/Androidpanzer/samsung")


def _w(*sub) -> str:
    p = os.path.join(WORK, *sub)
    os.makedirs(os.path.dirname(p) if os.path.splitext(p)[1] else p, exist_ok=True)
    return p


def _have(t: str) -> bool:
    from . import usb
    return usb.tool_path(t) is not None


def heimdall(args: list[str], timeout: int = 600) -> tuple[int, str]:
    try:
        from . import usb
        p = subprocess.run([usb.tool_path("heimdall") or "heimdall"] + args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, f"Timeout nach {timeout}s"
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


# ===================================================================== #
#  Menü
# ===================================================================== #
def menu(adb, dev, st, data: dict) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🔱 Samsung Root/Flash-Suite (Odin/Heimdall + Magisk)")
        ui.kv("Modell", f"{data.get('brand','')} {data.get('model','')} ({data.get('device','')})")
        ui.kv("Android/Build", f"{data.get('android','')} · {data.get('build','')}")
        ui.kv("heimdall (PC)", f"{ui.BGREEN}{usb.tool_path('heimdall')}{ui.RESET}" if _have("heimdall")
              else f"{ui.BRED}fehlt → sudo apt install heimdall-flash{ui.RESET}")
        ui.kv("samfirm.js", f"{ui.BGREEN}ok{ui.RESET}" if _samfirm_bin()
              else f"{ui.GREY}optional → npm i samfirm{ui.RESET}")
        ui.kv("samloader", f"{ui.BGREEN}ok{ui.RESET}" if _have("samloader")
              else f"{ui.GREY}optional → pip install samloader{ui.RESET}")
        ui.kv("lz4", f"{ui.BGREEN}ok{ui.RESET}" if _have("lz4") else f"{ui.BRED}fehlt{ui.RESET}")
        ui.kv("Modus", usb.mode_badge(dev.mode))
        ch = ui.menu("Aktionen", [
            ("1", f"{ui.BGREEN}{ui.BOLD}🚀 AUTO-ROOT (Magisk, vollautomatisch){ui.RESET}"),
            ("2", "📥 Stock-Firmware herunterladen (samloader)"),
            ("3", f"{ui.BCYAN}{ui.BOLD}🟢 TWRP VOLLAUTOMATISCH (alle Versionen finden → laden → entpacken → flashen){ui.RESET}"),
            ("4", "🧩 Magisk-Modul installieren (.zip)"),
            ("5", "🔍 Download-Modus erkennen (heimdall detect + print-pit)"),
            ("6", "↻ In Download-Modus neu starten"),
            ("7", f"{ui.BCYAN}🌐 Custom-Firmware/ROMs aus dem Internet anzeigen (LineageOS/TWRP/…){ui.RESET}"),
            ("?", "ℹ Voraussetzungen & Anleitung"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        from . import customfw
        {"1": auto_root, "2": download_firmware, "3": flash_twrp, "4": flash_module,
         "5": detect_download, "6": reboot_download,
         "7": customfw.show_custom_firmware, "?": show_help}.get(
            ch, lambda *a: None)(adb, dev, st, data)


def show_help(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Samsung-Root – Voraussetzungen", ui.CYAN)
    for l in [
        "1. Entwickleroptionen: 7× auf 'Build-Nummer' tippen.",
        "2. 'OEM-Entsperren' aktivieren (Pflicht!). Fehlt der Schalter → Konto/SIM 7 Tage warten.",
        "3. Bootloader entsperren: Aus → Vol-Hoch + Vol-Runter + USB an PC → im Warnscreen",
        "   lange Vol-Hoch halten zum Entsperren (LÖSCHT ALLE DATEN, Knox = 0x1 dauerhaft).",
        "4. Download-Modus: Aus → Vol-Hoch + Vol-Runter + USB-Kabel.",
        "5. heimdall installieren: sudo apt install heimdall-flash",
        "6. Optional Firmware-Auto-Download: pip install samloader",
        "",
        "Watch-Hinweis: Galaxy Watch4+ (Wear OS) = wie Phone. Tizen-Watches NICHT rootbar.",
    ]:
        print(f"   {ui.GREY}{l}{ui.RESET}")
    ui.pause()


def detect_download(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Download-Modus erkennen", ui.CYAN)
    if not _have("heimdall"):
        ui.err("heimdall fehlt: sudo apt install heimdall-flash"); ui.pause(); return
    rc, o = heimdall(["detect"], timeout=15)
    if "detected" in o.lower():
        ui.ok("Gerät im Download-Modus erkannt.")
        rc, pit = heimdall(["print-pit", "--no-reboot"], timeout=30)
        parts = re.findall(r"Partition Name:\s*(\S+)", pit)
        ui.kv("Partitionen", ", ".join(parts[:20]) + (" …" if len(parts) > 20 else ""))
        _w()  # ensure dir
        open(os.path.join(WORK, "pit.txt"), "w").write(pit)
        ui.info(f"PIT gespeichert: {os.path.join(WORK,'pit.txt')}")
    else:
        ui.warn("Kein Download-Modus erkannt. Gerät: Aus → Vol-Hoch+Vol-Runter+USB.")
        ui.info(o[:200])
    ui.pause()


def reboot_download(adb, dev, st, data) -> None:
    if dev.adb_capable:
        usb.adb_cmd(["reboot", "download"]); ui.ok("Reboot in Download-Modus ausgelöst.")
    else:
        ui.info("Manuell: Gerät aus → Vol-Hoch + Vol-Runter + USB-Kabel einstecken.")
    ui.pause()


# ===================================================================== #
#  Firmware-Download (samloader)
# ===================================================================== #
def _adb_reachable() -> bool:
    """True nur, wenn ein normal gebootetes ADB-Gerät da ist (NICHT im Download-Modus)."""
    return usb.adb_serial() is not None


def _auto_detect_model(adb, data) -> str:
    """Erkennt das Modell. Ruft adb NUR auf, wenn wirklich ein ADB-Gerät da ist
    (im Download-Modus würde getprop sonst ewig in wait-for-device hängen)."""
    if data.get("model"):
        m = data["model"].strip()
        if m.upper().startswith(("SM-", "GT-", "SC-", "SCV")):
            return m
    if _adb_reachable():
        for prop in ("ro.product.model", "ro.product.vendor.model"):
            v = adb.getprop(prop).strip()
            if v.upper().startswith(("SM-", "GT-", "SC-", "SCV")):
                return v
    return (data.get("model") or "").strip()


def _auto_detect_csc(adb) -> str:
    """Erkennt die CSC/Region – nur bei erreichbarem ADB-Gerät (sonst leer)."""
    if not _adb_reachable():
        return ""
    for prop in ("ro.csc.sales_code", "ril.sales_code", "ro.csc.country_code",
                 "ro.csc.omcnw_code", "persist.omc.sales_code"):
        v = adb.getprop(prop).strip()
        if v and len(v) >= 3 and v.isalpha():
            return v.upper()
    omc = adb.shell("cat /efs/sales_code 2>/dev/null; getprop | grep -i sales_code")
    m = re.search(r"\b([A-Z]{3})\b", omc)
    return m.group(1) if m else ""


def _samfirm_bin() -> str | None:
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools-node", "node_modules", ".bin", "samfirm")
    return p if os.path.isfile(p) else (shutil.which("samfirm"))


def download_firmware(adb, dev, st, data) -> str | None:
    ui.clear(); ui.rule("Stock-Firmware – Auto-Suche & Download", ui.CYAN)
    out = _w("firmware")
    # Bereits geladene Firmware automatisch erkennen & verwenden (kein Pfad-Tippen,
    # kein erneuter Download). Sucht im Firmware-Ordner und in ~/Downloads.
    existing = _find_ap(out) or _newest_local_ap(data, adb)
    if existing and os.path.isfile(existing):
        ui.ok(f"Bereits geladene Firmware automatisch erkannt: {os.path.basename(existing)}")
        ui.kv("Pfad", existing, key_w=8)
        if ui.confirm("Diese AP-Datei verwenden (kein erneuter Download)?", True):
            return _resolve_firmware(existing, out) if not existing.endswith((".tar", ".tar.md5")) else existing
    samfirm = _samfirm_bin()
    have_samloader = _have("samloader")
    if not samfirm and not have_samloader:
        ui.err("Kein Downloader: samfirm.js (npm i samfirm) oder samloader (pip) installieren.")
        ui.pause(); return None

    # Modell/CSC ermitteln (im Download-Modus OHNE adb → Abfrage)
    model = _auto_detect_model(adb, data)
    region = _auto_detect_csc(adb)
    if not _adb_reachable():
        ui.info("Gerät nicht per ADB erreichbar (Download-Modus) – Modell/Region bitte eingeben.")
    ui.kv("Modell", model or "—")
    ui.kv("CSC/Region", region or "—")
    if not model:
        model = ui.ask("Modell (z.B. SM-G970F)", model)
    if not model:
        ui.warn("Kein Modell."); ui.pause(); return None
    if not region:
        region = ui.ask("CSC/Region (z.B. VD2, DBT, EUX) – leer = auto", "")

    out = _w("firmware")
    candidates = ([region] if region else []) + \
        [c for c in ("VD2", "DBT", "EUX", "XEF", "BTU", "OXM", "XEO") if c != region]

    # --- Transparenz: ZUERST ermitteln & ANZEIGEN, was geladen wird -----------
    sl = ""
    if have_samloader:
        from . import usb
        sl = usb.tool_path("samloader") or "samloader"
    planned_ver, planned_csc = "", ""
    if sl:
        ui.info("Ermittle neueste passende Firmware (samloader checkupdate) …")
        planned_ver, planned_csc = _latest_version(sl, model, candidates)
        if planned_csc:                       # ermittelte Region nach vorne ziehen
            candidates = [planned_csc] + [c for c in candidates if c != planned_csc]

    ui.rule("Geplanter Download – das wird geladen", ui.YELLOW)
    ui.kv("Modell", model, key_w=18)
    ui.kv("Region / CSC", planned_csc or region or (candidates[0] if candidates else "?"), key_w=18)
    ui.kv("Firmware-Version", planned_ver or "(neueste – wird beim Laden bestimmt)", key_w=18)
    ui.kv("Downloader", "samfirm.js" if samfirm else "samloader", key_w=18)
    ui.kv("Speicherort", out, key_w=18)
    ui.kv("Größe / Dauer", "ca. 3–6 GB · mehrere Minuten (je nach Verbindung)", key_w=18)
    if not ui.confirm("Diesen Download jetzt starten?", True):
        ui.info("Download abgebrochen."); ui.pause(); return None

    # --- PRIMÄR: samfirm.js (zuverlässiger, lädt + entschlüsselt automatisch) ---
    if samfirm:
        ui.info(f"samfirm.js: lade {model} ({planned_ver or 'neueste'}) … (mehrere GB)")
        for csc in candidates:
            print(f"   {ui.GREY}→ Region {csc} …{ui.RESET}")
            rc, o = _run([samfirm, "-m", model, "-r", csc], timeout=7200, cwd=out)
            ap = _find_ap(out)
            if ap:
                ui.ok(f"AP-Datei: {ap}")
                ui.pause(); return ap
            if "not found" not in o.lower() and rc == 0:
                break
            print(f"   {ui.GREY}✗ {csc}{ui.RESET}")
        ui.warn("samfirm fand/lud nichts – versuche samloader-Fallback …")

    # --- FALLBACK: samloader (Version bereits ermittelt) ----------------------
    if sl and planned_ver:
        ui.info(f"samloader: lade {planned_ver}  (Region {planned_csc}) …")
        _run([sl, "-m", model, "-r", planned_csc, "download", "-v", planned_ver, "-O", out, "-D"], timeout=7200)
        ap = _find_ap(out)
        if ap:
            ui.ok(f"AP-Datei: {ap}"); ui.pause(); return ap

    # --- Beide Auto-Downloader gescheitert: ehrlich + manueller Weg -----------
    return _manual_firmware(model, region, out)


def _manual_firmware(model: str, region: str, out: str) -> str | None:
    ui.warn("Automatischer Download nicht möglich.")
    ui.info("Samsung hat die FUS-Server-Verschlüsselung geändert → samloader UND samfirm "
            "scheitern aktuell beide am 'bad decrypt' (kein Tool-Fehler, Samsung-seitig).")
    print()
    ui.rule("Manueller Download (einmalig, dann verarbeitet das Tool alles weiter)", ui.CYAN)
    for l in [f"1. Firmware für {model} (Region {region or 'VD2/DBT'}) laden bei:",
              "   • https://samfw.com/firmware/" + model,
              "   • https://www.sammobile.com/samsung/galaxy/firmware/  (kostenlos, langsam)",
              "   • Frija/Bifrost (Windows-Tools) falls vorhanden",
              "2. Die heruntergeladene .zip (enthält AP/BL/CP/CSC) hier angeben –",
              "   das Tool extrahiert AP automatisch und patcht/flasht weiter."]:
        print(f"   {ui.GREY}{l}{ui.RESET}")
    print()
    # vorhandene Downloads automatisch suchen
    cand = _scan_firmware_files(model)
    if cand:
        ui.info("Gefundene Firmware-Dateien:")
        for i, c in enumerate(cand, 1):
            print(f"  {ui.CYAN}{i}{ui.RESET}  {c}")
        sel = ui.ask("Nr wählen (oder leer für eigenen Pfad)", "1")
        if sel.isdigit() and 1 <= int(sel) <= len(cand):
            return _resolve_firmware(cand[int(sel) - 1], out)
    p = ui.ask("Pfad zur Firmware (.zip / AP_*.tar.md5 / Ordner) – leer = abbrechen")
    p = os.path.expanduser(p) if p else ""
    if p and os.path.exists(p):
        return _resolve_firmware(p, out)
    ui.pause(); return None


def _latest_version(sl: str, model: str, candidates: list[str]) -> tuple[str, str]:
    """Neueste Firmware-Version je Region via 'samloader checkupdate' → (version, csc)."""
    for csc in candidates:
        rc, o = _run([sl, "-m", model, "-r", csc, "checkupdate"], timeout=60)
        cand = o.strip().splitlines()[-1] if o.strip() else ""
        if cand and "/" in cand:
            return cand, csc
    return "", ""


def _newest_local_ap(data: dict | None, adb) -> str | None:
    """Neueste bereits lokal vorhandene Firmware (AP-tar bevorzugt, sonst .zip)."""
    model = (data or {}).get("model", "") or ""
    cands = _scan_firmware_files(model)
    aps = [c for c in cands if os.path.basename(c).startswith("AP_")
           and c.endswith((".tar", ".tar.md5"))]
    pool = aps or cands
    if not pool:
        return None
    try:
        return max(pool, key=os.path.getmtime)
    except OSError:
        return pool[0]


def _scan_firmware_files(model: str) -> list[str]:
    import glob
    res = []
    for base in (os.path.expanduser("~/Downloads"), _w("firmware"), os.getcwd()):
        for pat in (f"*{model}*.zip", "AP_*.tar.md5", f"*{model}*.tar*", "*.zip"):
            res += glob.glob(os.path.join(base, pat))
    # nur plausible Firmware-Dateien, dedupe
    return list(dict.fromkeys(f for f in res if os.path.getsize(f) > 50_000_000))[:8]


def _resolve_firmware(path: str, out: str) -> str | None:
    """Macht aus zip/tar/Ordner eine nutzbare AP-Datei."""
    if os.path.isdir(path):
        return _find_ap(path)
    if path.endswith(".zip"):
        try:
            with zipfile.ZipFile(path) as z:
                ap = next((n for n in z.namelist() if os.path.basename(n).startswith("AP_")), None)
                if not ap:
                    ui.warn("Keine AP-Datei in der ZIP gefunden."); return None
                info = z.getinfo(ap)
                target = safe_join(out, ap)                 # Zip-Slip-sicher (nur Pfad)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                ui.info(f"Entpacke {os.path.basename(ap)} ({human_size(info.file_size)}) …")
                done = 0
                with z.open(ap) as src, open(target, "wb") as dst:   # streamen + %-Balken
                    while True:
                        chunk = src.read(1 << 20)
                        if not chunk:
                            break
                        dst.write(chunk); done += len(chunk)
                        ui.progress_bytes(done, info.file_size, "entpacke AP")
                ui.ok(f"Entpackt: {target}")
                return target
        except Exception as e:  # noqa: BLE001
            ui.err(str(e)); return None
    if "AP_" in os.path.basename(path):
        return path
    ui.warn("Datei ist keine erkennbare Firmware (AP/zip).")
    return None


def _find_ap(d: str) -> str | None:
    if not d or not os.path.isdir(d):
        return None
    for root, _, files in os.walk(d):
        for f in files:
            if f.startswith("AP_") and (f.endswith(".tar.md5") or f.endswith(".tar")):
                return os.path.join(root, f)
    return None


def _find_ap_anywhere(model: str) -> str | None:
    for base in (_w("firmware"), os.path.expanduser("~/Downloads"), os.getcwd()):
        ap = _find_ap(os.path.join(base, model)) or _find_ap(base)
        if ap:
            return ap
    return None


# ===================================================================== #
#  AUTO-ROOT
# ===================================================================== #
def auto_root(adb, dev, st, data) -> None:
    ui.clear(); ui.banner(subtitle="🚀 Samsung Auto-Root (Magisk) – vollautomatisch")
    locked = (adb.getprop("ro.boot.flash.locked") or "").strip()
    if locked in ("1", "true"):
        ui.danger("Bootloader GESPERRT (flash.locked=1) – Flashen erst nach dem Entsperren möglich.")
        ui.info("Entsperren: Entwickleroptionen → 'OEM-Entsperren' AN, dann Download-Modus → Vol-Hoch lang halten.")
        ui.info("Das Entsperren LÖSCHT ALLE DATEN und trippt Knox dauerhaft (irreversibel).")
        if not ui.confirm("Trotzdem fortfahren (Download/Patch vorbereiten, Flash erst nach Unlock)?", False):
            return
    else:
        ui.ok("Bootloader scheint entsperrt – ein Magisk-Flash darauf wipet NICHT erneut.")
        ui.danger("Knox ist/bleibt beim entsperrten Gerät dauerhaft getrippt (Pay/Pass/Secure Folder tot).")
    if not ui.confirm("Verstanden und vollautomatischen Magisk-Root starten?", False):
        return
    for need, hint in [("heimdall", "sudo apt install heimdall-flash"), ("lz4", "sudo apt install lz4")]:
        if not _have(need):
            ui.err(f"{need} fehlt: {hint}"); ui.pause(); return

    # 1) AP-Tar besorgen – VOLLAUTOMATISCH: vorhandene erkennen, sonst laden.
    #    Zeigt vor dem Download transparent an, WAS geladen wird (Modell/Region/Version).
    ui.rule("1 · Firmware (AP-Tar) – automatisch", ui.CYAN)
    ui.info("Firmware wird automatisch gewählt: bereits geladene wird erkannt und verwendet,")
    ui.info("sonst zeigt das Tool Modell/Region/Version an und lädt per samfirm/samloader.")
    ui.info("(Eigene Firmware? Einfach .zip/AP_*.tar.md5 nach samsung/firmware/ oder ~/Downloads legen.)")
    ap = download_firmware(adb, dev, st, data) or ""
    if not ap or not os.path.isfile(ap):
        ui.err("Keine AP-Datei verfügbar."); ui.pause(); return

    # 2) boot.img + vbmeta.img extrahieren
    ui.rule("2 · boot.img & vbmeta.img extrahieren", ui.CYAN)
    boot = _extract_from_ap(ap, "boot.img")
    vbmeta = _extract_from_ap(ap, "vbmeta.img")
    if not boot:
        ui.err("boot.img nicht in AP gefunden."); ui.pause(); return
    ui.ok(f"boot.img: {boot}")
    if vbmeta:
        ui.ok(f"vbmeta.img: {vbmeta}")

    # 3) Magisk-APK holen + magiskboot extrahieren
    ui.rule("3 · Magisk vorbereiten", ui.CYAN)
    if not dev.adb_capable:
        ui.err("Fürs Patchen muss das Gerät normal gebootet & per ADB erreichbar sein "
               "(zum on-device-Patchen). Bitte normal starten, USB-Debugging an.")
        ui.pause(); return
    apk = _download_magisk_apk()
    if not apk:
        ui.pause(); return
    abi = adb.getprop("ro.product.cpu.abi") or "arm64-v8a"
    mdir = _extract_magisk_bins(apk, abi)
    if not mdir:
        ui.err("magiskboot konnte nicht aus der APK extrahiert werden."); ui.pause(); return
    usb.adb_cmd(["install", "-r", apk], timeout=120)  # Magisk-App gleich mitinstallieren

    # 4) On-device patchen (ohne Root – magiskboot läuft als shell)
    ui.rule("4 · boot.img patchen (on-device)", ui.CYAN)
    patched = _patch_boot_ondevice(adb, dev, boot, mdir)
    if not patched:
        ui.err("Patchen fehlgeschlagen – Logs siehe oben. Fallback: boot.img in Magisk-App patchen.")
        ui.pause(); return
    ui.ok(f"Gepatchtes boot: {patched}")

    # 5) vbmeta verity deaktivieren
    if vbmeta:
        ui.rule("5 · vbmeta verity deaktivieren", ui.CYAN)
        _disable_vbmeta(vbmeta)
        ui.ok("vbmeta-Flags auf disable-verity/verification gesetzt.")

    # 6) Flashen via heimdall (Download-Modus)
    ui.rule("6 · Flashen (Download-Modus)", ui.CYAN)
    from . import modeswitch
    ok, _ = modeswitch.ensure(adb, dev, "download")   # automatisch + warten bis erkannt
    if not ok:
        ui.err("Download-Modus nicht erreicht – Flash abgebrochen."); ui.pause(); return
    rc, o = heimdall(["detect"], timeout=15)           # heimdall final gegenbestätigen
    if "detected" not in o.lower():
        ui.warn("heimdall meldet (noch) kein Gerät – kurz warten/Kabel prüfen und erneut versuchen.")
        ui.pause()
        rc, o = heimdall(["detect"], timeout=15)
        if "detected" not in o.lower():
            ui.err("Kein Download-Modus über heimdall erkannt – Flash abgebrochen."); ui.pause(); return
    args = ["flash", "--BOOT", patched]
    if vbmeta:
        args += ["--VBMETA", vbmeta]
    else:
        ui.warn("Keine vbmeta.img in der AP – neuere Samsung-Builds verweigern sonst evtl. den Start.")
        ui.info("Bei Bootloop trotz korrektem boot: zusätzlich eine vbmeta_disabled.tar flashen (AVB-Verify aus).")
    # KEIN --no-reboot: heimdall startet das Gerät direkt aus der Flash-Session neu.
    # Das ist zuverlässiger als die manuelle Tastenkombi und löst bei Samsung den
    # sauberen ersten Magisk-Boot aus (magiskd initialisiert dann /data/adb).
    ui.danger(f"Flashe:  heimdall {' '.join(args)}   (Gerät startet danach AUTOMATISCH neu)")
    if not ui.confirm("Jetzt flashen? (Bootloader muss ENTSPERRT sein)", False):
        return
    rc, o = heimdall(args, timeout=600)
    ui.pager(o, "heimdall flash")
    if rc != 0:
        ui.err("Flash fehlgeschlagen.")
        if "protocol initialisation" in o.lower():
            _heimdall_protocol_help(args)
        ui.pause(); return

    ui.ok("✅ Geflasht – das Gerät startet jetzt AUTOMATISCH ins System (erster Magisk-Boot).")
    ui.rule("7 · Erster Magisk-Boot · Root abschließen", ui.CYAN)
    for ln in [
        "1) Das Gerät rebootet selbst ins System (erster Magisk-Boot dauert 2–5 Min).",
        "2) BOOTLOOP (Endlosschleife)? → Vol-Hoch+Power → Recovery → 'Wipe data/Factory reset'.",
        "3) Falls Magisk dann 'N/A': Magisk-App -> 'Direct Install' -> Reboot.",
        "4) Knox-Bit ist dauerhaft 0x1: Samsung Pay/Pass/Secure Folder bleiben tot (irreversibel).",
    ]:
        print(f"   {ui.GREY}{ln}{ui.RESET}")
    if ui.confirm("Auf den Boot warten und Root automatisch prüfen?", True):
        _verify_root_after(adb, dev)
    ui.pause()


def _verify_root_after(adb, dev) -> None:
    """Wartet auf den Android-Boot und prüft, ob Root (su) aktiv ist."""
    from . import modeswitch
    ui.info("Warte auf normalen Android-Boot …")
    ok, _ = modeswitch.ensure(adb, dev, "system")
    if not ok:
        ui.warn("Gerät (noch) nicht per ADB erreichbar – nach dem Boot im Hauptmenü 'R' erneut prüfen.")
        return
    adb.raw(["wait-for-device"], timeout=60)
    rid = adb.shell("su -c id 2>/dev/null").strip()
    if "uid=0" in rid:
        ui.ok(f"✅ ROOT AKTIV: {rid}")
        ui.info("Alle [ROOT]-Funktionen sind jetzt freigeschaltet (Hauptmenü → X · ROOT-ARSENAL).")
    else:
        ui.warn("Noch kein Root über su. Magisk-App öffnen → 'Direct Install', dann Gerät neu starten.")
        ui.info("Danach im Hauptmenü 'R' (oder Gerät neu wählen) erneut prüfen.")


# ===================================================================== #
#  TWRP-Flasher
# ===================================================================== #
def _dl_progress(url: str, dst: str) -> None:
    """Lädt *url* nach *dst* mit Prozent-/MB-Fortschrittsanzeige."""
    def hook(block, bsize, total):
        done = block * bsize
        if total > 0:
            pct = min(100, done * 100 // total)
            sys.stdout.write(f"\r   {ui.NEON}⟳{ui.RESET} {pct:3d}%  "
                             f"{done // 1048576} / {total // 1048576} MB")
        else:
            sys.stdout.write(f"\r   {ui.NEON}⟳{ui.RESET} {done // 1048576} MB")
        sys.stdout.flush()
    urllib.request.urlretrieve(url, dst, hook)
    print()


def _twrp_candidates(data, adb) -> list[str]:
    """Leitet mögliche TWRP-Gerätecodenamen aus den Geräte-Properties ab."""
    g = adb.getprop
    raw = [data.get("device", ""), g("ro.product.device"), g("ro.product.vendor.device"),
           g("ro.vendor.product.device"), g("ro.product.name"), g("ro.build.product")]
    cands: list[str] = []
    for v in raw:
        v = (v or "").strip().lower()
        if not v:
            continue
        # Regionssuffixe (xx/dd/zt/zs/zh/ks/…) entfernen, lte-Varianten ergänzen
        stripped = re.sub(r"(xx|dd|zt|zs|zh|ks|kx|oxm|ojv)$", "", v)
        for c in (v, stripped, stripped + "lte", stripped + "ltexx",
                  stripped.replace("lte", ""), v + "lte"):
            c = c.strip()
            if c and c not in cands:
                cands.append(c)
    return cands


_BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _http_get(u: str, timeout: int = 25) -> str:
    return urllib.request.urlopen(urllib.request.Request(
        u, headers={"User-Agent": _BROWSER_UA}), timeout=timeout).read().decode("utf-8", "replace")


def _http_download(url: str, dst: str, referer: str | None = None, label: str = "") -> int:
    """Streamt *url* → *dst* mit %-Fortschritt. Sendet optional einen Referer
    (TWRP-Hotlink-Schutz liefert die Binärdatei NUR mit passendem Referer)."""
    hdr = {"User-Agent": _BROWSER_UA, "Accept": "application/octet-stream,*/*"}
    if referer:
        hdr["Referer"] = referer
    done = 0
    with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=120) as r:
        total = int(r.headers.get("Content-Length") or 0)
        with open(dst, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk); done += len(chunk)
                ui.progress_bytes(done, total, label)
    return done


def _twrp_all(codes: list[str]) -> list[dict]:
    """Listet ALLE verfügbaren TWRP-Images (alle Versionen) für die Codenamen.

    Liefert je Eintrag {code, version, fname, page_url, fileurl, kind}. Bricht beim
    ERSTEN Codename mit Treffern ab (vermeidet Dubletten anderer Regionscodes).
    """
    from urllib.parse import urljoin
    for code in codes:
        try:
            html = _http_get(f"https://dl.twrp.me/{code}/")
        except Exception:  # noqa: BLE001
            continue
        pages = [p for p in re.findall(r'href="([^"]+\.img(?:\.tar)?\.html)"', html) if "twrp-" in p.lower()]
        if not pages:
            continue
        base = f"https://dl.twrp.me/{code}/"
        items, seen = [], set()
        for p in pages:                         # Listing ist newest-first
            page_url = urljoin(base, p)
            fileurl = page_url[:-5]              # '.html' weg → echte Datei
            fname = os.path.basename(fileurl)
            if fname in seen:
                continue
            seen.add(fname)
            m = re.search(r"twrp-([\d.]+_\d+-\d+)-", fname)
            items.append({"code": code, "version": m.group(1) if m else "?", "fname": fname,
                          "page_url": page_url, "fileurl": fileurl,
                          "kind": "tar" if fname.endswith(".tar") else "img"})
        if items:
            return items
    return []


def _twrp_fetch(it: dict) -> str | None:
    """Lädt EIN TWRP-Image (Referer-Hotlink-Schutz, %-Balken) und prüft die Größe."""
    dst = _w("images", it["fname"])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isfile(dst) and os.path.getsize(dst) > 10_000_000:
        ui.ok(f"Bereits vorhanden: {dst}"); return dst
    ui.info(f"Lade {it['fname']} …")
    try:
        _http_download(it["fileurl"], dst, referer=it["page_url"], label=it["fname"])
    except Exception as e:  # noqa: BLE001
        ui.err(f"Download fehlgeschlagen: {e}"); return None
    size = os.path.getsize(dst) if os.path.isfile(dst) else 0
    if size > 10_000_000:
        ui.ok(f"TWRP geladen: {dst}  ({size // 1048576} MB)"); return dst
    ui.warn(f"Datei zu klein ({size} B) – keine echte Image-Datei, verwerfe.")
    try:
        os.remove(dst)
    except OSError:
        pass
    return None


def _download_twrp(data, adb) -> str | None:
    """Sucht ALLE TWRP-Versionen (dl.twrp.me), zeigt sie und lädt die gewählte
    (ENTER = neueste) per Referer-Hotlink-Schutz mit %-Fortschritt."""
    codes = _twrp_candidates(data, adb)
    ui.info("Suche ALLE TWRP-Versionen für: " + ", ".join(codes[:8]))
    items = _twrp_all(codes)
    if not items:
        ui.err("Kein offizielles TWRP für diesen Codename gefunden.")
        ui.info("Manuell: twrp.me/Devices/ → Gerät suchen, .img.tar laden, Pfad hier angeben.")
        return None
    ui.rule(f"{len(items)} TWRP-Image(s) gefunden ({items[0]['code']})", ui.YELLOW)
    for i, it in enumerate(items[:20], 1):
        tag = f"{ui.BCYAN}.tar{ui.RESET}" if it["kind"] == "tar" else f"{ui.GREY}.img{ui.RESET}"
        print(f"  {ui.CYAN}{i:>2}{ui.RESET}  TWRP {it['version']:<10} {tag}  {ui.GREY}{it['fname']}{ui.RESET}")
    sel = ui.ask("Nr. wählen (ENTER = neueste, .tar bevorzugen)", "1").strip()
    if sel.isdigit() and 1 <= int(sel) <= len(items):
        chosen = items[int(sel) - 1]
    else:
        chosen = next((it for it in items if it["kind"] == "tar"), items[0])   # neueste .tar
    return _twrp_fetch(chosen)


def _extract_any_img(tar: str) -> str | None:
    """Extrahiert die erste *.img(.lz4) aus einem TWRP-.img.tar."""
    out = _w("images")
    try:
        with tarfile.open(tar) as tf:
            member = next((m for m in tf.getmembers()
                           if m.name.endswith((".img", ".img.lz4"))), None)
            if not member:
                return None
            src = safe_extract_member(tf, member, out)   # Tar-Slip-sicher
    except Exception:  # noqa: BLE001
        return None
    if src.endswith(".lz4"):
        dst = src[:-4]
        rc, _ = _run(["lz4", "-d", "-f", src, dst], timeout=120)
        return dst if os.path.isfile(dst) else None
    return src


def flash_twrp(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("TWRP-Recovery flashen", ui.CYAN)
    if not _have("heimdall"):
        ui.err("heimdall fehlt: sudo apt install heimdall-flash"); ui.pause(); return
    ui.info(f"{ui.BGREEN}ENTER = VOLLAUTOMATISCH{ui.RESET}: alle TWRP-Versionen für "
            f"'{data.get('model', '')}' finden → wählen/neueste → laden → entpacken → flashen.")
    ui.info("Oder eigenen Pfad zu .img/.tar eingeben.")
    p = ui.ask("Pfad zur TWRP .img/.tar (leer/ENTER = vollautomatisch)").strip()
    if not p or p.lower() == "a":
        p = _download_twrp(data, adb)
        if not p:
            ui.pause(); return
    else:
        p = os.path.expanduser(p)
        if not os.path.isfile(p):
            ui.err("Datei nicht gefunden."); ui.pause(); return
    img = p
    if p.endswith((".tar", ".tar.md5")):
        img = _extract_recovery_tar(p) or _extract_any_img(p)
        if not img:
            ui.err("Konnte recovery/Image aus TAR nicht extrahieren."); ui.pause(); return
    from . import modeswitch
    ok, _ = modeswitch.ensure(adb, dev, "download")
    if not ok:
        ui.err("Download-Modus nicht erreicht."); ui.pause(); return
    rc, o = heimdall(["detect"], timeout=15)
    if "detected" not in o.lower():
        ui.warn("heimdall sieht (noch) kein Gerät – kurz warten / Kabel direkt am PC.")
        ui.pause(); rc, o = heimdall(["detect"], timeout=15)
        if "detected" not in o.lower():
            ui.err("Kein Download-Modus über heimdall erkannt."); ui.pause(); return
    ui.danger("RECOVERY wird überschrieben.")
    if ui.confirm("heimdall flash --RECOVERY ausführen?", False):
        rc, o = heimdall(["flash", "--RECOVERY", img, "--no-reboot"], timeout=300)
        ui.pager(o, "TWRP flash")
        if rc == 0:
            ui.ok("TWRP geflasht! SOFORT in Recovery booten (Vol-Hoch+Power direkt nach Trennen), "
                  "sonst überschreibt Stock-OS das Recovery wieder.")
        elif "protocol initialisation" in o.lower():
            _heimdall_protocol_help(["flash", "--RECOVERY", img, "--no-reboot"])
    ui.pause()


def _heimdall_protocol_help(retry_args: list | None = None) -> None:
    """Erklärt 'Protocol initialisation failed!' und bietet optional einen frischen
    Retry mit *retry_args* (die fehlgeschlagenen heimdall-Argumente) an."""
    ui.crit("heimdall: 'Protocol initialisation failed!' – der Download-Modus-Handshake schlug fehl.")
    for ln in [
        "Das ist KEIN Fehler des Images/Tools – der Download-Modus ist in einem hängenden Zustand.",
        "Häufigste Ursachen:",
        "  • Eine vorherige heimdall-/Odin-Sitzung wurde nicht sauber beendet (z.B. detect/print-pit).",
        "  • Ein zweites heimdall-/adb-Fenster hält dasselbe USB-Gerät.",
        "  • USB-Hub oder wackeliges Kabel – direkt an einen PC-Port stecken.",
        "",
        "So behebst du es:",
        "  1) Am Gerät: Vol-Runter + Power ~7–10 s halten → Neustart.",
        "  2) DANN frisch in den Download-Modus: Vol-Hoch + Vol-Runter halten + USB einstecken.",
        "  3) Sicherstellen, dass KEIN weiteres heimdall-Fenster offen ist.",
    ]:
        print(f"   {ui.GREY}{ln}{ui.RESET}")
    if retry_args and ui.confirm("Gerät neu im Download-Modus? Flash JETZT erneut versuchen?", False):
        rc, o = heimdall(retry_args, timeout=600)
        ui.pager(o, "heimdall flash (Retry)")
        if rc == 0:
            ui.ok("Flash erfolgreich (Retry).")
        elif "protocol initialisation" in o.lower():
            ui.err("Weiterhin Protocol-Fehler → bitte Gerät & Kabel physisch neu verbinden, dann erneut.")


# ===================================================================== #
#  Magisk-Modul-Flasher
# ===================================================================== #
def flash_module(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Magisk-Modul installieren", ui.CYAN)
    z = ui.ask("Pfad zur Modul-.zip")
    z = os.path.expanduser(z or "")
    if not os.path.isfile(z):
        ui.err("ZIP nicht gefunden."); ui.pause(); return
    if st.get("is_root"):
        ui.info("Root erkannt → Installation via magisk --install-module.")
        usb.adb_cmd(["push", z, "/data/local/tmp/module.zip"], timeout=120)
        rc, o = usb.adb_cmd(["shell", "su", "-c", "magisk --install-module /data/local/tmp/module.zip"], timeout=120)
        ui.pager(o or "(ok)", "magisk --install-module")
        if "Done" in o or rc == 0:
            ui.ok("Modul installiert. Neustart nötig.")
            if ui.confirm("Jetzt neu starten?", True):
                usb.adb_cmd(["reboot"])
    else:
        ui.warn("Kein Root → Installation via TWRP-Sideload.")
        ui.info("Gerät in TWRP booten → Advanced → ADB Sideload (Wischen).")
        if ui.confirm("Jetzt in Recovery (TWRP) neu starten?", False):
            usb.adb_cmd(["reboot", "recovery"]); time.sleep(8)
        ui.pause("Wenn TWRP-Sideload aktiv: ENTER")
        rc, o = usb.adb_cmd(["sideload", z], timeout=300)
        ui.pager(o, "adb sideload")
    ui.pause()


# ===================================================================== #
#  Helfer
# ===================================================================== #
def _run(args: list[str], timeout: int = 120, cwd: str | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "Timeout"
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def _extract_from_ap(ap_tar: str, want: str) -> str | None:
    """Extrahiert z.B. boot.img(.lz4) aus dem AP-Tar und dekomprimiert es."""
    out = _w("images")
    try:
        with tarfile.open(ap_tar) as tf:
            member = next((m for m in tf.getmembers()
                           if m.name in (want, want + ".lz4")), None)
            if not member:
                return None
            src = safe_extract_member(tf, member, out)   # Tar-Slip-sicher
    except Exception:  # noqa: BLE001
        return None
    if src.endswith(".lz4"):
        dst = src[:-4]
        rc, _ = _run(["lz4", "-d", "-f", src, dst], timeout=120)
        if rc != 0 or not os.path.isfile(dst):
            # python-lz4 Fallback
            try:
                import lz4.frame
                with open(src, "rb") as f, open(dst, "wb") as o:
                    o.write(lz4.frame.decompress(f.read()))
            except Exception:  # noqa: BLE001
                return None
        return dst
    return src


def _extract_recovery_tar(tar: str) -> str | None:
    return _extract_from_ap(tar, "recovery.img")


def _download_magisk_apk() -> str | None:
    ui.info("Hole neueste Magisk-APK von GitHub …")
    try:
        api = "https://api.github.com/repos/topjohnwu/Magisk/releases/latest"
        data = urllib.request.urlopen(urllib.request.Request(
            api, headers={"User-Agent": "panzer"}), timeout=20).read().decode()
        urls = re.findall(r'"browser_download_url":\s*"([^"]+\.apk)"', data)
        if not urls:
            ui.err("Keine APK im Release gefunden."); return None
        # Stabile Release-APK bevorzugen (nicht Debug)
        url = next((u for u in urls if re.search(r"Magisk-v|release", u, re.I) and "debug" not in u.lower()),
                   urls[0])
        dst = _w(os.path.basename(url))
        if not os.path.isfile(dst):
            sha = safe_download(url, dst)        # HTTPS erzwungen + Integritäts-Check
            ui.ok(f"Magisk-APK geladen · SHA-256: {sha}")
            ui.info("Hash gegen github.com/topjohnwu/Magisk/releases prüfen, bevor du flashst.")
        else:
            from .util import sha256_file
            ui.ok(f"Magisk-APK (vorhanden) · SHA-256: {sha256_file(dst)}")
        return dst
    except Exception as e:  # noqa: BLE001
        ui.err(f"Download fehlgeschlagen: {e}")
        ui.info("Manuell laden: github.com/topjohnwu/Magisk/releases")
        return None


def _extract_magisk_bins(apk: str, abi: str) -> str | None:
    """Extrahiert magiskboot/magiskinit/magisk + boot_patch.sh aus der APK."""
    mdir = _w("magisk_bins")
    for f in os.listdir(mdir) if os.path.isdir(mdir) else []:
        os.remove(os.path.join(mdir, f))
    try:
        with zipfile.ZipFile(apk) as z:
            names = z.namelist()
            # native libs lib<name>.so → <name>
            for libname, out in [("libmagiskboot.so", "magiskboot"),
                                 ("libmagiskinit.so", "magiskinit"),
                                 ("libmagisk.so", "magisk"),        # neue Versionen (Einzelbinary)
                                 ("libmagisk64.so", "magisk64"),    # ältere Versionen
                                 ("libmagisk32.so", "magisk32"),
                                 ("libmagiskpolicy.so", "magiskpolicy"),
                                 ("libbusybox.so", "busybox"),
                                 ("libinit-ld.so", "init-ld")]:
                cand = next((n for n in names if n.endswith(f"/{abi}/{libname}")), None)
                if not cand:  # andere ABI als Fallback
                    cand = next((n for n in names if n.endswith(f"/{libname}")), None)
                if cand:
                    with z.open(cand) as s, open(os.path.join(mdir, out), "wb") as o:
                        o.write(s.read())
            # Skripte aus assets
            for asset in ("boot_patch.sh", "util_functions.sh", "addon.d.sh", "stub.apk"):
                cand = next((n for n in names if n.endswith(f"assets/{asset}")), None)
                if cand:
                    with z.open(cand) as s, open(os.path.join(mdir, asset), "wb") as o:
                        o.write(s.read())
        if not os.path.isfile(os.path.join(mdir, "magiskboot")):
            return None
        return mdir
    except Exception:  # noqa: BLE001
        return None


def _patch_boot_ondevice(adb, dev, boot: str, mdir: str) -> str | None:
    """Pusht magisk-Binaries + boot.img, führt boot_patch.sh aus, holt new-boot.img."""
    rdir = "/data/local/tmp/magisk"
    usb.adb_cmd(["shell", "rm", "-rf", rdir], timeout=20)
    usb.adb_cmd(["shell", "mkdir", "-p", rdir], timeout=20)
    # Binaries + Skripte pushen
    for f in os.listdir(mdir):
        usb.adb_cmd(["push", os.path.join(mdir, f), f"{rdir}/{f}"], timeout=120)
    usb.adb_cmd(["push", boot, f"{rdir}/boot.img"], timeout=180)
    # ausführbar + patchen
    rc, o = usb.adb_cmd(["shell",
        f"cd {rdir} && chmod -R 0755 . && "
        f"KEEPVERITY=true KEEPFORCEENCRYPT=true sh boot_patch.sh {rdir}/boot.img 2>&1"], timeout=180)
    print("   " + "\n   ".join(o.splitlines()[-12:]))
    # Ergebnisdatei finden (Magisk-Versionen nennen sie new-boot.img)
    _, listing = usb.adb_cmd(["shell", f"ls {rdir}"], timeout=10)
    out = next((n for n in ("new-boot.img", "magisk_patched.img") if n in listing), None)
    if not out:
        return None
    local = os.path.join(WORK, "images", "magisk_patched_boot.img")
    os.makedirs(os.path.dirname(local), exist_ok=True)
    usb.adb_cmd(["pull", f"{rdir}/{out}", local], timeout=120)
    return local if os.path.isfile(local) and os.path.getsize(local) > 0 else None


def _disable_vbmeta(vbmeta: str) -> None:
    """Setzt im AVB-vbmeta-Header die Flags disable-verity+disable-verification (0x03)."""
    try:
        with open(vbmeta, "r+b") as f:
            data = f.read()
            if data[:4] != b"AVB0":
                return
            # flags = 32-bit big-endian an Offset 123 (0x7B) im Header
            f.seek(123)
            f.write(b"\x03")
    except Exception:  # noqa: BLE001
        pass
