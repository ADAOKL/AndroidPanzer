"""Universelle Geräteerkennung – jedes Android-Gerät, egal in welchem Modus.

Kanäle:
  • adb       → Normal (device), Recovery, Sideload, Unauthorized, Offline
  • fastboot  → Bootloader / Fastbootd
  • lsusb     → EDL (Qualcomm 9008), MediaTek Preloader/BROM, Samsung Download
                (Odin) sowie „Handy steckt, aber USB-Debugging aus" (MTP/Laden)

Liefert eine vereinheitlichte Geräteliste mit erkanntem Modus und passendem
Werkzeug-Hinweis je Modus.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time

from . import ui
from .adb import ADB, Device

# --- Bekannte Android-USB-Hersteller (VID → Name) ------------------------
ANDROID_VENDORS = {
    "18d1": "Google/Pixel", "04e8": "Samsung", "2717": "Xiaomi", "2a70": "OnePlus/Oppo",
    "22d9": "Oppo/Realme", "12d1": "Huawei", "1004": "LG", "0fce": "Sony",
    "22b8": "Motorola", "0b05": "Asus", "0bb4": "HTC", "17ef": "Lenovo",
    "19d2": "ZTE", "2d95": "Vivo", "05c6": "Qualcomm", "0e8d": "MediaTek",
    "1bbb": "TCL/Alcatel", "2916": "Yota", "0489": "Fairphone/Foxconn", "1f3a": "Allwinner",
    "2207": "Rockchip", "10a9": "LG/Pantech", "109b": "Hisense", "271d": "Nokia/HMD",
}

# --- Spezial-Modi: (vid,pid) → (Modus, externes Tool) --------------------
SPECIAL_MODES = {
    "05c6:9008": ("edl", "EDL/9008 – Tools: edl (bkerler) / QFIL / qdl + passender Firehose-Loader"),
    "05c6:900e": ("edl", "EDL-Variante – edl/QFIL"),
    "05c6:9006": ("edl", "EDL (QDLoader 9006) – edl/QFIL"),
    "0fff:0fff": ("edl", "EDL (Sahara) – edl/QFIL"),
    "0e8d:0003": ("mtk-brom", "MediaTek BROM – Tool: mtkclient"),
    "0e8d:2000": ("mtk-preloader", "MediaTek Preloader – Tool: mtkclient / SP Flash Tool"),
    "0e8d:2001": ("mtk-preloader", "MediaTek Preloader – mtkclient / SP Flash Tool"),
    "04e8:685d": ("odin", "Samsung Download-Modus – Tools: heimdall (Linux) / Odin (Windows)"),
    "04e8:68c3": ("odin", "Samsung Download (Kies) – heimdall / Odin"),
    "1004:633e": ("lg-dl", "LG Download-Modus – LGUP / uppercut"),
}

# --- Fastboot-Produkt-IDs (zur Klassifizierung aus lsusb) ----------------
FASTBOOT_PIDS = {"18d1:4ee0", "18d1:d00d", "0fce:0dde"}

# VIDs, die (fast) ausschließlich für Smartphones genutzt werden → generischer
# „Debugging aus"-Treffer ist hier zuverlässig. Hersteller wie Foxconn(0489),
# Samsung(04e8), Qualcomm(05c6), MediaTek(0e8d), Lenovo(17ef) bauen auch
# Bluetooth/WLAN/Monitore – die werden NUR bei Android-Hinweis im Text erkannt.
STRICT_PHONE_VIDS = {"18d1", "2717", "2a70", "22d9", "22b8", "0fce", "2d95",
                     "271d", "19d2", "0bb4", "2916", "1bbb"}


import os as _os

# Zusätzliche Tool-Pfade: dedizierter venv des Projekts (mtk, samloader, heimdall …)
_TOOLS_VENV = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                           "tools-venv", "bin")


def tool_path(bin_: str) -> str | None:
    """Findet ein Tool im PATH ODER im projekteigenen tools-venv/bin."""
    p = shutil.which(bin_)
    if p:
        return p
    cand = _os.path.join(_TOOLS_VENV, bin_)
    return cand if _os.path.isfile(cand) else None


def have(bin_: str) -> bool:
    return tool_path(bin_) is not None


# ===================================================================== #
#  Roh-USB-Enumeration
# ===================================================================== #
def list_usb() -> list[dict]:
    if not have("lsusb"):
        return []
    try:
        out = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001
        return []
    res = []
    for line in out.splitlines():
        m = re.search(r"ID ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s*(.*)$", line)
        if not m:
            continue
        vid, pid, desc = m.group(1).lower(), m.group(2).lower(), m.group(3).strip()
        res.append({"vid": vid, "pid": pid, "vidpid": f"{vid}:{pid}", "desc": desc})
    return res


def classify(u: dict) -> dict | None:
    """Bestimmt, ob es ein Android-Gerät ist + Modus + Tool-Hinweis."""
    vidpid = u["vidpid"]
    vid = u["vid"]
    desc = u["desc"]
    low = desc.lower()
    # 1) exakte Spezial-Modi (EDL/MTK/Odin/…)
    if vidpid in SPECIAL_MODES:
        mode, tool = SPECIAL_MODES[vidpid]
        return {"mode": mode, "tool": tool, "vendor": ANDROID_VENDORS.get(vid, desc or vid)}
    # 2) Fastboot über lsusb erkannt
    if vidpid in FASTBOOT_PIDS or "fastboot" in low:
        return {"mode": "fastboot", "tool": "fastboot", "vendor": ANDROID_VENDORS.get(vid, desc or vid)}
    # 3) Eindeutiger Android-Hinweis im Text → Datenmodus (Debugging evtl. aus)
    if any(k in low for k in ("android", " mtp", "_mtp", "adb interface")) and vid in ANDROID_VENDORS:
        return {"mode": "usb", "tool": "adb", "vendor": ANDROID_VENDORS[vid]}
    # 4) Reiner Telefon-Hersteller (VID nicht mit PC-Peripherie geteilt) → nodebug
    if vid in STRICT_PHONE_VIDS:
        return {"mode": "nodebug", "tool": "", "vendor": ANDROID_VENDORS.get(vid, desc or vid)}
    # sonst: kein eindeutiges Android-Gerät (z.B. Foxconn-BT, Samsung-Monitor) → ignorieren
    return None


# ===================================================================== #
#  Fastboot
# ===================================================================== #
def fastboot_devices() -> list[Device]:
    if not have("fastboot"):
        return []
    try:
        out = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001
        return []
    devs = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] in ("fastboot", "fastbootd"):
            devs.append(Device(serial=parts[0], state="fastboot", mode="fastboot",
                               channel="fastboot", model="(Fastboot-Modus)"))
    return devs


def fb(args: list[str], serial: str | None = None, timeout: int = 30) -> tuple[int, str]:
    cmd = ["fastboot"] + (["-s", serial] if serial else []) + args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, f"Timeout nach {timeout}s"
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def adb_serial() -> str | None:
    if not have("adb"):
        return None
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return None
    for line in out.splitlines()[1:]:
        p = line.split()
        if len(p) >= 2 and p[1] in ("device", "recovery", "sideload"):
            return p[0]
    return None


def adb_cmd(args: list[str], timeout: int = 15) -> tuple[int, str]:
    try:
        p = subprocess.run(["adb"] + args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, f"Timeout nach {timeout}s"
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def device_booted() -> bool:
    """True, wenn ein Gerät vollständig in Android gebootet ist."""
    s = adb_serial()
    if not s:
        return False
    rc, out = adb_cmd(["-s", s, "shell", "getprop", "sys.boot_completed"], timeout=6)
    return out.strip() == "1"


# ===================================================================== #
#  Vereinheitlichte Erkennung
# ===================================================================== #
def detect_all() -> list[Device]:
    devices: list[Device] = []

    # 1) ADB-Kanal
    state_to_mode = {"device": "adb", "recovery": "recovery", "sideload": "sideload",
                     "unauthorized": "unauthorized", "offline": "offline"}
    for d in ADB.list_devices():
        d.mode = state_to_mode.get(d.state, d.state)
        d.channel = "adb"
        devices.append(d)
    adb_or_fb = len(devices) > 0

    # 2) Fastboot-Kanal
    fbs = fastboot_devices()
    devices += fbs
    if fbs:
        adb_or_fb = True

    # 3) lsusb-Kanal (fängt alles ab, was adb/fastboot NICHT sehen)
    for u in list_usb():
        c = classify(u)
        if not c:
            continue
        mode = c["mode"]
        # Spezial-Modi immer zeigen (eigene PIDs, keine Kollision)
        if mode in ("edl", "mtk-brom", "mtk-preloader", "odin", "lg-dl"):
            devices.append(Device(serial="", state=mode, mode=mode, channel="usb",
                                  model=f"{c['vendor']} ({mode})", tool=c["tool"],
                                  vidpid=u["vidpid"], desc=u["desc"]))
        elif mode == "fastboot":
            if not fbs:  # nur wenn fastboot-Treiber es nicht schon gemeldet hat
                devices.append(Device(serial="", state="fastboot", mode="fastboot",
                                      channel="usb", model=c["vendor"], vidpid=u["vidpid"], desc=u["desc"]))
        else:  # usb / nodebug → nur wenn adb/fastboot GAR NICHTS gefunden hat
            if not adb_or_fb:
                m = "nodebug" if mode == "nodebug" else "usb"
                devices.append(Device(serial="", state=m, mode=m, channel="usb",
                                      model=c["vendor"], vidpid=u["vidpid"], desc=u["desc"]))
    return devices


def wait_for_any(on_tick=None) -> Device | None:
    """Wartet, bis irgendein Gerät in irgendeinem Modus auftaucht."""
    tick = 0
    while True:
        devs = detect_all()
        if devs:
            return devs[0] if len(devs) == 1 else _pick(devs)
        if on_tick:
            on_tick(tick)
        tick += 1
        time.sleep(1.5)


def _pick(devs: list[Device]) -> Device:
    ui.rule("Mehrere Geräte erkannt", ui.YELLOW)
    for i, d in enumerate(devs, 1):
        print(f"  {ui.CYAN}{i}{ui.RESET}  {mode_badge(d.mode)}  {d.label}")
    sel = ui.ask("Gerät wählen", "1")
    try:
        return devs[int(sel) - 1]
    except (ValueError, IndexError):
        return devs[0]


# ===================================================================== #
#  Darstellung & Modus-Handler
# ===================================================================== #
def mode_badge(mode: str) -> str:
    m = {
        "adb": f"{ui.BGREEN}[ADB · bereit]{ui.RESET}",
        "recovery": f"{ui.BYELLOW}[RECOVERY]{ui.RESET}",
        "sideload": f"{ui.BYELLOW}[SIDELOAD]{ui.RESET}",
        "unauthorized": f"{ui.BRED}[NICHT AUTORISIERT]{ui.RESET}",
        "offline": f"{ui.GREY}[OFFLINE]{ui.RESET}",
        "fastboot": f"{ui.MAGENTA}[FASTBOOT/BOOTLOADER]{ui.RESET}",
        "edl": f"{ui.BRED}[EDL · Qualcomm 9008]{ui.RESET}",
        "mtk-brom": f"{ui.BRED}[MTK BROM]{ui.RESET}",
        "mtk-preloader": f"{ui.MAGENTA}[MTK PRELOADER]{ui.RESET}",
        "odin": f"{ui.MAGENTA}[SAMSUNG DOWNLOAD]{ui.RESET}",
        "lg-dl": f"{ui.MAGENTA}[LG DOWNLOAD]{ui.RESET}",
        "nodebug": f"{ui.BYELLOW}[USB-DEBUGGING AUS]{ui.RESET}",
        "usb": f"{ui.CYAN}[USB · Datenmodus]{ui.RESET}",
    }
    return m.get(mode, f"[{mode.upper()}]")


def fastboot_menu(dev: Device) -> None:
    info_cache = {"data": None}

    def get_info(force=False):
        if info_cache["data"] is None or force:
            _, info_cache["data"] = fb(["getvar", "all"], dev.serial or None, timeout=12)
        return info_cache["data"] or ""

    try:
        _fastboot_menu_loop(dev, get_info)
    except KeyboardInterrupt:
        print()
        ui.warn("Fastboot-Menü abgebrochen.")


def _fastboot_menu_loop(dev: Device, get_info) -> None:
    from . import rescue
    while True:
        ui.clear()
        ui.banner(subtitle=f"Fastboot/Bootloader · {dev.label}")
        info = get_info()
        unlocked = re.search(r"unlocked:\s*(\S+)", info)
        product = re.search(r"product:\s*(\S+)", info)
        slot = re.search(r"current-slot:\s*(\S+)", info)
        ui.kv("Produkt", product.group(1) if product else "—")
        ui.kv("Bootloader entsperrt", (unlocked.group(1) if unlocked else "unbekannt"))
        ui.kv("Aktiver Slot", slot.group(1) if slot else "—")
        ch = ui.menu("Fastboot-Aktionen", [
            ("Z", f"{ui.BGREEN}{ui.BOLD}🚑 AUTO-RESCUE – 20 Versuche automatisch{ui.RESET}"),
            ("1", "Alle Variablen anzeigen (getvar all)"),
            ("2", "Slot-Status (A/B)"),
            ("3", "Bootloader ENTSPERREN (flashing unlock) – WIPED"),
            ("4", "Bootloader sperren (flashing lock)"),
            ("5", "Image temporär booten (fastboot boot <img>)"),
            ("6", "Partition flashen (fastboot flash <part> <img>)"),
            ("7", "Neustart → System"),
            ("8", "Neustart → Bootloader / Fastbootd / Recovery"),
        ], back_label="Geräteauswahl")
        if ch in ("back", "quit"):
            return
        s = dev.serial or None
        if ch == "z":
            rescue.auto_rescue(dev)
            get_info(force=True)
        elif ch == "1":
            ui.pager(get_info(force=True), "getvar all"); ui.pause()
        elif ch == "2":
            _, cur = fb(["getvar", "current-slot"], s)
            _, hasab = fb(["getvar", "slot-count"], s)
            ui.pager(f"{cur}\n{hasab}", "Slots"); ui.pause()
        elif ch == "3":
            ui.danger("ENTSPERREN LÖSCHT ALLE DATEN. Am Gerät mit Lautstärke/Power bestätigen.")
            if ui.confirm("fastboot flashing unlock ausführen?", False):
                rc, o = fb(["flashing", "unlock"], s, timeout=60)
                if rc != 0:
                    rc, o = fb(["oem", "unlock"], s, timeout=60)
                ui.pager(o, "unlock"); ui.pause()
        elif ch == "4":
            if ui.confirm("fastboot flashing lock?", False):
                _, o = fb(["flashing", "lock"], s, timeout=60); ui.pager(o, "lock"); ui.pause()
        elif ch == "5":
            img = ui.ask("Pfad zum boot/recovery-Image")
            import os
            if img and os.path.isfile(os.path.expanduser(img)):
                _, o = fb(["boot", os.path.expanduser(img)], s, timeout=120); ui.pager(o, "boot"); ui.pause()
        elif ch == "6":
            part = ui.ask("Partition (z.B. boot, init_boot, recovery, vbmeta)")
            img = ui.ask("Pfad zum Image")
            import os
            if part and img and os.path.isfile(os.path.expanduser(img)):
                ui.danger(f"flash {part} – falsches Image = Bootloop!")
                if ui.confirm("Wirklich flashen?", False):
                    _, o = fb(["flash", part, os.path.expanduser(img)], s, timeout=300)
                    ui.pager(o, f"flash {part}"); ui.pause()
        elif ch == "7":
            fb(["reboot"], s); ui.ok("Neustart ausgelöst."); ui.pause(); return
        elif ch == "8":
            sub = ui.menu("Ziel", [("a", "bootloader"), ("b", "fastboot (fastbootd)"),
                                   ("c", "recovery")], back_label="Zurück")
            tgt = {"a": "bootloader", "b": "fastboot", "c": "recovery"}.get(sub)
            if tgt:
                fb(["reboot", tgt], s); ui.ok(f"Neustart → {tgt}"); ui.pause()


def mode_info(dev: Device) -> None:
    """Infoschirm für Modi, die NICHT über adb/fastboot bedienbar sind."""
    ui.clear()
    ui.banner(subtitle=f"Erkannt: {mode_badge(dev.mode)}")
    ui.kv("Gerät", dev.label)
    ui.kv("USB-ID", dev.vidpid or "—")
    print()
    if dev.mode in ("edl", "mtk-brom", "mtk-preloader", "odin", "lg-dl"):
        ui.warn("Dieser Modus spricht KEIN adb/fastboot – er braucht ein Spezial-Tool:")
        ui.info(dev.tool or "Spezial-Flash-Tool nötig.")
        print()
        guide = {
            "edl": ["EDL (Emergency Download, Qualcomm 9008):",
                    "  • Auslesen/Flashen nur mit signiertem Firehose-Loader (programmer.mbn) für genau dein Modell",
                    "  • Linux:  edl (bkerler)  →  edl printgpt / edl rl dump/  / edl w <part> <img>",
                    "  • GUI/Windows: QFIL (Qualcomm), QPST",
                    "  • Verlassen:  edl reset   (oder Akku-Trick)"],
            "mtk-brom": ["MediaTek BROM (Boot-ROM):",
                         "  • Tool: mtkclient  →  python mtk r boot boot.img  /  python mtk w …",
                         "  • Voll-Dump:  python mtk rl dump/",
                         "  • Verlassen:  Gerät neu starten / Akku"],
            "mtk-preloader": ["MediaTek Preloader:",
                              "  • mtkclient oder SP Flash Tool (scatter-Datei nötig)",
                              "  • Achtung: korrektes scatter/DA für dein Modell verwenden"],
            "odin": ["Samsung Download-Modus (Odin):",
                     "  • Linux:  heimdall print-pit  /  heimdall flash --<PARTITION> <img>",
                     "  • Windows: Odin (AP/BL/CP/CSC .tar.md5)",
                     "  • Verlassen:  Lautstärke-runter + Power gedrückt halten"],
            "lg-dl": ["LG Download-Modus:",
                      "  • LGUP (mit DLL) oder uppercut; .kdz/.tot-Firmware"],
        }.get(dev.mode, [])
        for line in guide:
            print(f"   {ui.GREY}{line}{ui.RESET}")
        # Direkt ins passende Flash-/Root-Modul springen
        if dev.mode in ("mtk-brom", "mtk-preloader") and ui.confirm(
                "\nMediaTek-Modul (mtkclient: dumpen/unlock/root) jetzt öffnen?", True):
            from . import mediatek
            from .adb import ADB
            mediatek.menu(ADB(), dev, {"is_root": False}, {"platform": dev.desc})
            return
        if dev.mode == "odin" and ui.confirm(
                "\nSamsung-Modul (heimdall: TWRP/Firmware flashen) jetzt öffnen?", True):
            from . import samsung
            from .adb import ADB
            samsung.menu(ADB(), dev, {"is_root": False}, {"brand": "samsung"})
            return
        ui.info("\nDas Panzer-Tool arbeitet sonst über adb – für diesen Modus die obigen Tools nutzen.")
    elif dev.mode in ("nodebug", "usb"):
        ui.warn("Ein Android-Gerät steckt am USB, aber es ist KEIN adb-Zugriff möglich "
                "(USB-Debugging aus oder reiner Datenmodus).")
        print()
        ui.info("So aktivierst du adb:")
        for line in [
            "1. Einstellungen → Über das Telefon → 7× auf 'Build-Nummer' tippen (Entwickleroptionen freischalten)",
            "2. Einstellungen → System → Entwickleroptionen → 'USB-Debugging' EIN",
            "3. USB-Modus auf 'Dateiübertragung (MTP)' stellen",
            "4. Am Handy den RSA-Dialog 'Diesem Computer vertrauen' bestätigen",
        ]:
            print(f"   {ui.GREY}{line}{ui.RESET}")
        ui.info("\nDanach erneut scannen – das Gerät erscheint dann als [ADB · bereit].")
    elif dev.mode == "unauthorized":
        ui.warn("USB-Debugging ist an, aber dieser PC ist nicht autorisiert.")
        ui.info("Am Handy den RSA-Schlüssel-Dialog mit 'Zulassen' bestätigen, dann neu scannen.")
    elif dev.mode == "offline":
        ui.warn("Gerät ist 'offline' – Kabel neu stecken oder 'adb kill-server' + neu scannen.")
    ui.pause()
