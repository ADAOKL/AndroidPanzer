"""Automatischer Modus-Wechsel: bringt das Gerät in den für eine Aktion nötigen
Modus (System · Download/Odin · Fastboot · Recovery · ADB-Sideload · EDL).

Wo möglich vollautomatisch per ``adb reboot <ziel>`` bzw. ``fastboot reboot``;
ist das nicht möglich (Gerät aus / ohne USB-Debugging / EDL), wird die exakte
physische Tastenkombination genannt. In JEDEM Fall wartet das Tool aktiv, bis das
Gerät im Zielmodus erkannt wird (``usb.detect_all``), statt fester Wartezeiten.

Bewusst ohne Eingriff am Gerät selbst – ein Bootloader-Unlock oder ein Flash wird
hier NICHT ausgelöst; dieses Modul wechselt nur den Betriebsmodus.
"""
from __future__ import annotations

import subprocess
import sys
import time

from . import ui, usb
from .adb import ADB, Device
from .util import LOG

# Zielmodus → erkannte Modi aus usb.detect_all(), die ihn erfüllen.
_SATISFY = {
    "system": {"adb"},
    "download": {"odin"},
    "fastboot": {"fastboot"},
    "recovery": {"recovery"},
    "sideload": {"sideload"},
    "edl": {"edl"},
}
# adb reboot <sub> je Ziel ("" = schlichter Reboot ins System).
_ADB_SUB = {"system": "", "download": "download", "fastboot": "bootloader",
            "recovery": "recovery", "sideload": "sideload", "edl": "edl"}
_LABEL = {"system": "System (Android)", "download": "Download-Modus (Odin/Heimdall)",
          "fastboot": "Fastboot/Bootloader", "recovery": "Recovery",
          "sideload": "ADB-Sideload", "edl": "EDL (Qualcomm 9008)"}
# Modi, aus denen heraus ADB-Kommandos möglich sind.
_ADB_CAPABLE = {"adb", "recovery", "sideload"}


def _phys(brand: str, target: str) -> list[str]:
    """Exakte physische Tastenkombi für *target* (markenbewusst)."""
    b = (brand or "").lower()
    if target == "download":
        if "samsung" in b:
            return [
                "Gerät vollständig AUSschalten.",
                "Neuere Modelle (S10/Note10 und neuer): Vol-Hoch + Vol-Runter gleichzeitig "
                "gedrückt halten und DABEI das USB-Kabel zum PC einstecken.",
                "Ältere mit Bixby (S8/S9/Note8/9): Vol-Runter + Bixby + Power halten.",
                "Im blauen Warnscreen mit Vol-Hoch bestätigen.",
            ]
        return ["Gerät in den Download-/Flash-Modus des Herstellers bringen (modellabhängig)."]
    if target == "fastboot":
        if "samsung" in b:
            return ["Samsung hat KEINEN Fastboot-Modus – stattdessen den Download-Modus verwenden."]
        return ["Gerät AUSschalten, dann Vol-Runter + Power halten, bis das Fastboot-/Bootloader-Menü erscheint."]
    if target == "recovery":
        if "samsung" in b:
            return ["Aus → Vol-Hoch + Bixby + Power gleichzeitig halten, bis das Recovery-Menü erscheint."]
        return ["Aus → Vol-Hoch + Power gleichzeitig halten, bis das Recovery-Menü erscheint."]
    if target == "system":
        return ["Gerät normal einschalten (Power lang drücken). Im Download-Modus: Vol-Runter+Power ~10 s."]
    if target == "edl":
        return ["EDL (9008) ist modell-/chipsatzspezifisch (Testpoint/edl-Kabel) – siehe Modell-Doku."]
    return ["Modellspezifische Tastenkombination verwenden."]


def current(serial: str | None = None) -> Device | None:
    """Aktuell erkanntes Gerät (bei mehreren: nach Serial, sonst das erste)."""
    devs = usb.detect_all()
    if serial:
        for d in devs:
            if d.serial == serial:
                return d
    return devs[0] if devs else None


def wait_for_mode(targets: set, timeout: int = 180, on_tick=None) -> Device | None:
    """Pollt ``detect_all`` bis ein Gerät in *targets* auftaucht (oder Timeout)."""
    t0 = time.monotonic()
    i = 0
    while time.monotonic() - t0 < timeout:
        for d in usb.detect_all():
            if d.mode in targets:
                return d
        if on_tick:
            on_tick(i)
        i += 1
        time.sleep(1.5)
    return None


def _spinner(label: str):
    spin = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def tick(i: int) -> None:
        if ui._NO_COLOR:
            return
        sys.stdout.write(f"\r  {ui.NEON}{spin[i % len(spin)]}{ui.RESET} warte auf {label} …   ")
        sys.stdout.flush()
    return tick


def ensure(adb: ADB, dev: Device, target: str, timeout: int = 180, auto: bool = True) -> tuple[bool, Device | None]:
    """Stellt sicher, dass das Gerät im *target*-Modus ist.

    Versucht den Wechsel automatisch (adb/fastboot reboot); fällt sonst auf eine
    präzise physische Anleitung zurück. Wartet aktiv, bis der Zielmodus erkannt
    wird. Gibt (erfolg, erkanntes_gerät) zurück.
    """
    target = (target or "").lower()
    sat = _SATISFY.get(target)
    if not sat:
        ui.err(f"Unbekannter Zielmodus: {target!r}")
        return False, None

    cur = current(getattr(dev, "serial", None))
    if cur and cur.mode in sat:
        ui.ok(f"Gerät ist bereits im {_LABEL[target]}.")
        return True, cur

    cur_mode = cur.mode if cur else "kein Gerät"
    brand = ""
    if cur and cur.mode in _ADB_CAPABLE:
        try:
            brand = adb.getprop("ro.product.brand") or ""
        except Exception as e:  # noqa: BLE001
            LOG.exception("modeswitch getprop brand", e)

    issued = False
    if auto and cur:
        if cur.mode in _ADB_CAPABLE:
            sub = _ADB_SUB[target]
            ui.info(f"Starte das Gerät automatisch neu → {_LABEL[target]} …")
            args = ["reboot"] + ([sub] if sub else [])
            try:
                adb.raw(args, timeout=20)
                issued = True
            except Exception as e:  # noqa: BLE001
                LOG.exception("modeswitch adb reboot", e)
        elif cur.mode == "fastboot" and target in ("system", "recovery", "fastboot"):
            sub = {"system": "", "recovery": "recovery", "fastboot": "bootloader"}[target]
            fb = usb.tool_path("fastboot") or "fastboot"
            cmd = [fb] + (["-s", cur.serial] if cur.serial else []) + ["reboot"] + ([sub] if sub else [])
            ui.info(f"Fastboot-Neustart → {_LABEL[target]} …")
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                issued = True
            except Exception as e:  # noqa: BLE001
                LOG.exception("modeswitch fastboot reboot", e)

    if issued:
        if target == "download":
            ui.info("ADB-Verbindung wird dabei getrennt – das ist normal (Download-Modus hat kein ADB).")
    else:
        ui.warn(f"Automatischer Wechsel aus Modus '{cur_mode}' nicht möglich.")
        ui.info(f"Bitte das Gerät manuell in den {_LABEL[target]} bringen:")
        for ln in _phys(brand, target):
            print(f"   {ui.GREY}•{ui.RESET} {ln}")

    ui.info("Warte, bis das Gerät im Zielmodus erscheint … (STRG+C bricht ab)")
    try:
        d = wait_for_mode(sat, timeout=timeout, on_tick=_spinner(_LABEL[target]))
    except KeyboardInterrupt:
        print()
        ui.warn("Abgebrochen.")
        return False, None
    print()
    if d:
        ui.ok(f"Gerät im {_LABEL[target]} erkannt: {usb.mode_badge(d.mode)} {d.label}")
        return True, d
    ui.err(f"Zeitüberschreitung – {_LABEL[target]} wurde nicht erkannt.")
    if target == "download":
        ui.info("Prüfe: heimdall installiert? lsusb verfügbar? Kabel direkt am PC (kein Hub)? "
                "udev-Rechte (plugdev/Root)?")
    return False, None


def menu(adb: ADB, dev: Device, st: dict, data: dict | None = None) -> None:
    """Interaktiver Modus-Umschalter."""
    while True:
        ui.clear()
        ui.banner(subtitle="🔁 Automatischer Modus-Wechsel")
        cur = current(getattr(dev, "serial", None))
        ui.kv("Aktueller Modus", f"{usb.mode_badge(cur.mode)}  {cur.label}" if cur else "kein Gerät erkannt")
        print()
        ch = ui.menu("In welchen Modus soll das Gerät?", [
            ("1", "📥 Download-Modus (Samsung Odin/Heimdall)"),
            ("2", "⚡ Fastboot / Bootloader"),
            ("3", "🛟 Recovery"),
            ("4", "📦 ADB-Sideload"),
            ("5", "▶ System (normal neu starten)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        target = {"1": "download", "2": "fastboot", "3": "recovery",
                  "4": "sideload", "5": "system"}.get(ch)
        if target:
            ensure(adb, dev, target)
            ui.pause()
