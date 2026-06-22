"""Bootloop-Live-Monitor.

Beobachtet die USB-Enumerations-Zyklen eines bootloopenden Geräts in Echtzeit –
ohne dass ADB dauerhaft verfügbar sein muss. Misst T_cycle, klassifiziert die
Fehlerquelle (Hardware-/Bootloader-/Kernel-/OS-Loop), erkennt thermisch vs.
logisch und versucht im flüchtigen ADB-Fenster Logs zu greifen.

Datenquellen:
  • lsusb-Polling (~0.3 s) → erkennt An-/Abstecken in JEDEM Modus (auch EDL/MTK/Odin)
  • optional udevadm-Event-Stream → präzise Kernel-Enumerations-Events live
  • beim adb-Fenster: schneller logcat(crash/system)- + dmesg-Grab
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
import time

from . import ui, usb

OUT = os.path.expanduser("~/Schreibtisch/Androidpanzer/bootloop")
POLL = 0.3  # Sekunden – Edge-Präzision ~±300 ms (für sekundenlange Zyklen reichlich)


def _o() -> str:
    os.makedirs(OUT, exist_ok=True)
    return OUT


# --------------------------------------------------------------------- #
#  Klassifikation
# --------------------------------------------------------------------- #
def classify_cycle(sec: float) -> tuple[str, str]:
    """Ordnet eine Zyklusdauer einer Fehlerklasse zu (Schwellen aus dem Handbuch)."""
    if sec < 3:
        return (ui.pulse("🔴 KRITISCHER HARDWARE-LOOP"),
                "PMIC/Akku-Controller (BMS), klemmender Power-Button oder Kurzschluss")
    if sec < 15:
        return (f"{ui.BYELLOW}🟠 BOOTLOADER-LOOP{ui.RESET}",
                "Kernel-Verifikation (dm-verity)/Signatur scheitert → Hard-Reset")
    if sec < 30:
        return (f"{ui.YELLOW}🟡 KERNEL/EARLY-BOOT{ui.RESET}",
                "Kernel lädt, scheitert vor der Laufzeitumgebung (Treiber/Init/Mount)")
    return (f"{ui.BGREEN}🟢 ANDROID-OS-LOOP{ui.RESET}",
            "Zygote/SystemServer crasht – bestes Szenario für Cache-/Safe-Mode-Rettung")


def analyze_pattern(cycles: list[float]) -> str:
    """Thermisch (schrumpfend) vs. logisch (konstant) vs. unregelmäßig."""
    if len(cycles) < 3:
        return f"{ui.GREY}… mehr Zyklen für Muster nötig{ui.RESET}"
    last = cycles[-3:]
    a, b, c = last
    # streng fallend um je >15 % → thermisch
    if a > b > c and (c < a * 0.7):
        return (f"{ui.BRED}THERMISCH{ui.RESET} – Zyklen werden kürzer "
                f"({a:.1f}s→{b:.1f}s→{c:.1f}s): CPU/PMIC überhitzt (Lötstellen/Wärmeleitpaste)")
    spread = (max(last) - min(last)) / max(last)
    if spread < 0.15:
        return (f"{ui.BYELLOW}LOGISCH/KONSTANT{ui.RESET} – Takt stabil "
                f"(~{sum(last)/3:.1f}s): reiner Softwarefehler")
    return f"{ui.WHITE}UNREGELMÄSSIG{ui.RESET} – Spread {spread*100:.0f}% (Wackelkontakt? Kabel?)"


def _spark(cycles: list[float]) -> str:
    if not cycles:
        return ""
    blocks = "▁▂▃▄▅▆▇█"
    mx = max(cycles) or 1
    return "".join(blocks[min(7, int(c / mx * 7))] for c in cycles[-40:])


# --------------------------------------------------------------------- #
#  Präsenz-Erkennung (eine lsusb-Abfrage pro Tick)
# --------------------------------------------------------------------- #
# VID:PID → Modus-Klartext (für präzise Boot-Beobachtung)
_VIDPID_MODE = {
    "04e8:685d": "DOWNLOAD/Odin", "04e8:685c": "DOWNLOAD/Odin", "04e8:68c3": "DOWNLOAD/Kies",
    "04e8:6860": "Android (MTP)", "04e8:6866": "Android", "04e8:686c": "Android (ADB)",
    "18d1:4ee7": "Android (ADB)", "18d1:4ee0": "FASTBOOT", "18d1:d00d": "FASTBOOT",
    "05c6:9008": "EDL/9008", "0e8d:0003": "MTK-BROM", "0e8d:2000": "MTK-Preloader",
}
_IFCLASS = {"02": "Serial-CDC", "0a": "Serial-Data", "06": "MTP/PTP", "08": "Storage",
            "ff": "ADB/Vendor", "03": "HID", "e0": "Wireless"}


def _sysfs_detail(devpath: str) -> dict:
    """Liest aus /sys, ALS WAS ein Gerät gerade enumeriert (Modus-Erkennung live)."""
    base = f"/sys/bus/usb/devices/{devpath}"
    if not os.path.isdir(base):
        return {}

    def rd(f):
        try:
            return open(os.path.join(base, f)).read().strip()
        except OSError:
            return ""
    vid, pid = rd("idVendor"), rd("idProduct")
    vidpid = f"{vid}:{pid}" if vid else ""
    # Interface-Klassen → was kann das Gerät gerade
    ifaces = []
    try:
        for d in sorted(os.listdir(base)):
            if d.startswith(devpath + ":"):
                c = ""
                try:
                    c = open(os.path.join(base, d, "bInterfaceClass")).read().strip()
                except OSError:
                    pass
                if c:
                    ifaces.append(_IFCLASS.get(c, f"0x{c}"))
    except OSError:
        pass
    mode = _VIDPID_MODE.get(vidpid, "")
    if not mode and "Serial" in " ".join(ifaces):
        mode = "DOWNLOAD?"
    if not mode and "ADB/Vendor" in ifaces:
        mode = "Android (ADB)"
    if not mode and "MTP/PTP" in ifaces:
        mode = "Android (MTP)"
    return {"vidpid": vidpid, "product": rd("product"), "manufacturer": rd("manufacturer"),
            "serial": rd("serial"), "speed": rd("speed"), "ifaces": ifaces, "mode": mode or "?"}


def _presence() -> dict | None:
    """Gibt das erste erkannte Gerät zurück. Für den Bootloop-Monitor BEWUSST
    großzügig: jedes bekannte Hersteller-VID zählt (auch ohne 'android' im Text),
    plus alle adb/fastboot/EDL/MTK/Odin-Modi."""
    for u in usb.list_usb():
        c = usb.classify(u)
        if c:
            return {"mode": c["mode"], "vendor": c["vendor"], "vidpid": u["vidpid"], "tool": c.get("tool", "")}
        # Fallback: bekanntes Hersteller-VID reicht im Bootloop-Kontext
        if u["vid"] in usb.ANDROID_VENDORS:
            return {"mode": "usb", "vendor": usb.ANDROID_VENDORS[u["vid"]],
                    "vidpid": u["vidpid"], "tool": ""}
    return None


def _adb_serial() -> str | None:
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=4).stdout
    except Exception:  # noqa: BLE001
        return None
    for line in out.splitlines()[1:]:
        p = line.split()
        if len(p) >= 2 and p[1] in ("device", "recovery", "sideload"):
            return p[0]
    return None


# --------------------------------------------------------------------- #
#  Log-Grab im flüchtigen ADB-Fenster (Thread, nicht blockierend)
# --------------------------------------------------------------------- #
def _grab_logs(tag: str) -> None:
    serial = _adb_serial()
    if not serial:
        return
    base = ["adb", "-s", serial]
    grabbed = []
    try:
        # 1) Crash-/System-Logcat (gepufferte Historie -d = dump, sofort)
        lc = subprocess.run(base + ["logcat", "-b", "crash,system,main", "-d", "-t", "300"],
                            capture_output=True, text=True, timeout=4).stdout
        if lc.strip():
            grabbed.append("===== LOGCAT (crash/system) =====\n" + lc)
        # 2) Kernel-Log
        dm = subprocess.run(base + ["shell", "dmesg"], capture_output=True, text=True, timeout=4).stdout
        if dm.strip():
            grabbed.append("===== DMESG =====\n" + dm)
    except Exception:  # noqa: BLE001
        pass
    if not grabbed:
        return
    full = "\n\n".join(grabbed)
    path = os.path.join(_o(), f"loggrab_{tag}.txt")
    open(path, "w", encoding="utf-8", errors="replace").write(full)
    # fatale Zeilen heuristisch herausziehen
    hits = _fatal_lines(full)
    print(f"\n   {ui.BCYAN}⚡ ADB-Fenster erwischt! Logs gegrabbt → {path}{ui.RESET}")
    for h in hits[:8]:
        print("   " + ui.pulse(f"‼ {h[:120]}"))


FATAL_RX = re.compile(
    r"FATAL EXCEPTION|ANR in|signal \d+ \(SIG|backtrace:|Fatal signal|"
    r"OOM|lowmemorykiller|EXT4-fs error|f2fs.*(error|bug)|"
    r"kernel panic|Kernel panic|verity|dm-verity|"
    r"bootloader|SystemServer.*crash|Zygote.*(died|crash)|"
    r"over.?current|device descriptor.*fail|error -(71|110|62)",
    re.I)


def _fatal_lines(text: str) -> list[str]:
    seen, out = set(), []
    for line in text.splitlines():
        if FATAL_RX.search(line):
            key = line.strip()[:80]
            if key not in seen:
                seen.add(key)
                out.append(line.strip())
    return out


# --------------------------------------------------------------------- #
#  Optionaler udevadm-Event-Stream (präzise Kernel-Enumeration, live)
# --------------------------------------------------------------------- #
def _udev_thread(stop: threading.Event) -> None:
    if not usb.have("udevadm"):
        return
    try:
        proc = subprocess.Popen(
            ["udevadm", "monitor", "--kernel", "--subsystem-match=usb", "--property"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except Exception:  # noqa: BLE001
        return
    try:
        for line in proc.stdout:  # type: ignore
            if stop.is_set():
                break
            l = line.strip()
            if not l.startswith("KERNEL"):
                continue
            action = l.split()[1] if len(l.split()) > 1 else ""
            if action not in ("add", "remove"):
                continue
            # NUR Top-Level-Geräteereignisse (Pfad endet auf usbN/N-N, KEIN :1.x-Interface)
            m = re.search(r"/(usb\d+|\d+-[\d.]+)\s*\(usb\)$", l)
            if not m or ":" in m.group(1):
                continue
            col = ui.BGREEN if action == "add" else ui.BRED
            sym = "＋" if action == "add" else "－"
            devp = m.group(1)
            extra = ""
            if action == "add":
                d = _sysfs_detail(devp)
                if d:
                    extra = (f"  {ui.BCYAN}{d['mode']}{ui.RESET}  {ui.GREY}{d['vidpid']} "
                             f"{d.get('product','')} [{'/'.join(d['ifaces'])}]{ui.RESET}")
            print(f"   {col}[udev {sym}]{ui.RESET} {ui.GREY}{devp}{ui.RESET}{extra}")
    except Exception:  # noqa: BLE001
        pass
    finally:
        proc.terminate()


# --------------------------------------------------------------------- #
#  Haupt-Monitor
# --------------------------------------------------------------------- #
def monitor() -> None:
    ui.clear()
    ui.banner(subtitle="📉 Bootloop-Live-Monitor")
    ui.info("Beobachtet USB-Enumerations-Zyklen in Echtzeit. Gerät jetzt einstecken "
            "(oder ein-/ausschalten). STRG+C beendet.\n")
    use_udev = usb.have("udevadm")
    ui.kv("Polling", f"{POLL*1000:.0f} ms (lsusb)")
    ui.kv("udev-Events", "an" if use_udev else f"{ui.GREY}aus (udevadm fehlt){ui.RESET}")
    ui.kv("Klassen", "<3s Hardware · 3-15s Bootloader · 15-30s Kernel · >30s OS")
    print(f"{ui.BLOOD}{'─'*(ui.width()-1)}{ui.RESET}")

    stop = threading.Event()
    if use_udev:
        threading.Thread(target=_udev_thread, args=(stop,), daemon=True).start()

    present = False
    t_on = 0.0
    last_off = 0.0
    last_vidpid = ""
    cycles: list[float] = []
    appear = 0

    try:
        while True:
            dev = _presence()
            now = time.monotonic()
            ts = time.strftime("%H:%M:%S") + f".{int((now%1)*1000):03d}"
            cur_present = dev is not None

            if cur_present and not present:                      # ── steigende Flanke
                present = True
                t_on = now
                appear += 1
                gap = f"  (war {now-last_off:.2f}s aus)" if last_off else ""
                print(f"{ui.BGREEN}● {ts}  VERBUNDEN{ui.RESET}  "
                      f"{usb.mode_badge(dev['mode'])} {dev['vendor']} {ui.GREY}{dev['vidpid']}{ui.RESET}{gap}")
                last_vidpid = dev["vidpid"]
                # ADB-Fenster? Log-Grab im Thread (blockiert die Schleife nicht)
                if dev["mode"] in ("usb", "adb", "recovery", "sideload"):
                    threading.Thread(target=_grab_logs, args=(f"{appear}",), daemon=True).start()

            elif not cur_present and present:                    # ── fallende Flanke
                present = False
                last_off = now
                cyc = now - t_on
                cycles.append(cyc)
                cls, reason = classify_cycle(cyc)
                print(f"{ui.BRED}○ {ts}  GETRENNT{ui.RESET}   "
                      f"T_cycle = {ui.BOLD}{cyc:5.2f}s{ui.RESET}  → {cls}")
                print(f"   {ui.GREY}↳ {reason}{ui.RESET}")
                # laufende Statistik
                avg = sum(cycles) / len(cycles)
                print(f"   {ui.CYAN}Zyklen:{ui.RESET} {len(cycles)}   "
                      f"{ui.CYAN}Ø:{ui.RESET} {avg:.2f}s   "
                      f"{ui.CYAN}Muster:{ui.RESET} {analyze_pattern(cycles)}")
                print(f"   {ui.NEON}{_spark(cycles)}{ui.RESET}")

            elif cur_present and present and dev["vidpid"] != last_vidpid:   # Moduswechsel während verbunden
                print(f"{ui.MAGENTA}↻ {ts}  MODUSWECHSEL{ui.RESET}  "
                      f"{last_vidpid} → {dev['vidpid']}  {usb.mode_badge(dev['mode'])}")
                last_vidpid = dev["vidpid"]

            time.sleep(POLL)

    except KeyboardInterrupt:
        stop.set()
        print()
        _summary(cycles, appear)
        ui.pause()


def _summary(cycles: list[float], appear: int) -> None:
    ui.rule("Bootloop-Auswertung", ui.YELLOW)
    if not cycles:
        ui.info(f"{appear} Verbindung(en) gesehen, aber keine vollständigen Zyklen gemessen.")
        if appear == 0:
            ui.info("Kein Gerät erkannt – Kabel/Modus prüfen (manche EDL-Geräte brauchen kurzen Tastendruck).")
        return
    avg = sum(cycles) / len(cycles)
    cls, reason = classify_cycle(avg)
    ui.kv("Gemessene Zyklen", len(cycles))
    ui.kv("Ø Zyklusdauer", f"{avg:.2f}s")
    ui.kv("Min / Max", f"{min(cycles):.2f}s / {max(cycles):.2f}s")
    ui.kv("Wahrscheinl. Klasse", f"{cls}")
    ui.kv("Ursache", reason)
    ui.kv("Muster", analyze_pattern(cycles))
    ui.kv("Verlauf", f"{ui.NEON}{_spark(cycles)}{ui.RESET}")
    print()
    # Handlungsempfehlung je Klasse
    if avg >= 30:
        ui.ok("OS-Loop → Rettung aussichtsreich: Safe-Mode, Cache wipen, A/B-Slot wechseln "
              "(Recovery/Fastboot). Logs liegen unter ~/Schreibtisch/Androidpanzer/bootloop/.")
    elif avg >= 3:
        ui.warn("Bootloader/Kernel-Loop → meist Software: dm-verity/Signatur, korruptes /system. "
                "Custom-Recovery flashen oder Werks-Image (Fastboot/Odin/MTK).")
    else:
        ui.err("Hardware-Loop → kein Software-Fix: PMIC/Akku/Power-Button/Kurzschluss. "
               "Stromzufuhr & Taster prüfen, ggf. Mainboard-Reparatur.")
