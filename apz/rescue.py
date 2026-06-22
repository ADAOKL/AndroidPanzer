"""Auto-Rescue-Engine – versucht in JEDEM Modus automatisch ~20 Dinge, um ein
Gerät zu retten / zu flashen / aus dem Bootloop zu holen.

Sicherheitslogik (wichtig, ehrlich):
  • SAFE-Schritte (datenerhaltend) laufen automatisch.
  • DESTRUKTIVE Schritte (Wipe/Flash/Unlock/Factory-Reset) laufen NUR, wenn du
    vorher den Aggressiv-Modus bestätigst – sonst werden sie übersprungen und
    nur als Hinweis gezeigt. Kein heimliches Datenlöschen.
  • Nach jedem Schritt wird geprüft, ob das Gerät gebootet ist → bei Erfolg STOPP.

Pro Modus ein eigener, eskalierender Katalog (sicher → aggressiv → externer Tool-Tipp).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

from . import ui, usb


@dataclass
class Step:
    name: str
    risk: str               # "safe" | "destructive" | "manual"
    fn: Callable[[], tuple[bool, str]]


# --------------------------------------------------------------------- #
#  Engine
# --------------------------------------------------------------------- #
def auto_rescue(dev) -> None:
    ui.clear()
    ui.banner(subtitle=f"🚑 AUTO-RESCUE · {usb.mode_badge(dev.mode)} {dev.model or dev.label}")
    ui.warn("Versucht automatisch eine Kaskade von Rettungsschritten.")
    ui.info("SAFE-Schritte laufen sofort. Destruktive (Wipe/Flash/Unlock) nur mit deiner Freigabe.\n")

    aggressive = ui.confirm("Aggressiv-Modus aktivieren? (auch Wipe/Flash/Unlock → DATENVERLUST möglich)", False)
    if aggressive:
        aggressive = ui.confirm(f"{ui.BRED}Sicher? Das kann ALLE Daten löschen und das Gerät verändern.{ui.RESET} "
                                "Wirklich aggressiv?", False)
    firmware = ""
    if aggressive:
        firmware = _get_firmware(dev)

    family = _family(dev.mode)
    catalog = BUILDERS[family](dev, firmware)

    ui.rule(f"Starte {len(catalog)} Rettungsschritte ({family})", ui.YELLOW)
    log = []
    rescued = False
    for i, step in enumerate(catalog, 1):
        tag = {"safe": ui.BGREEN + "SAFE", "destructive": ui.BRED + "DESTRUKTIV",
               "manual": ui.BYELLOW + "MANUELL"}.get(step.risk, "?") + ui.RESET
        head = f"{ui.BOLD}[{i:>2}/{len(catalog)}]{ui.RESET} {step.name}  {ui.GREY}({tag}{ui.GREY}){ui.RESET}"
        print(head)
        if step.risk == "destructive" and not aggressive:
            print(f"      {ui.GREY}↳ übersprungen (Aggressiv-Modus aus){ui.RESET}")
            log.append((step.name, "skip", "destruktiv, übersprungen"))
            continue
        try:
            ok, msg = step.fn()
        except KeyboardInterrupt:
            ui.warn("\nAbgebrochen durch Nutzer."); break
        except Exception as e:  # noqa: BLE001
            ok, msg = False, f"Fehler: {e}"
        color = ui.BGREEN if ok else ui.GREY
        print(f"      {color}↳ {msg}{ui.RESET}")
        log.append((step.name, "ok" if ok else "fail", msg))

        # Erfolg? (Gerät vollständig gebootet)
        if usb.device_booted():
            rescued = True
            print(f"\n{ui.BGREEN}{ui.BOLD}✔ GERÄT GEBOOTET – Rettung erfolgreich nach Schritt {i}!{ui.RESET}")
            break

    print()
    ui.rule("Auto-Rescue Ergebnis", ui.YELLOW)
    if rescued:
        ui.ok("Gerät ist wieder gebootet. 🎉")
    else:
        done = sum(1 for _, s, _ in log if s == "ok")
        ui.warn(f"{done} Schritte ausgeführt, Gerät noch nicht gebootet.")
        ui.info("Nächste Eskalation: " + _next_hint(dev.mode))
    _save_log(dev, log)
    ui.pause()


def _device_brand_model(dev) -> tuple[str, str]:
    """Liest Hersteller+Modell – auch im Fastboot via getvar, sonst via adb."""
    brand = (dev.model or "").lower()
    model = dev.model or ""
    if dev.mode == "fastboot":
        _, info = usb.fb(["getvar", "all"], dev.serial or None, timeout=12)
        import re
        pm = re.search(r"product:\s*(\S+)", info)
        if pm:
            model = pm.group(1)
            brand = model.lower()
    elif dev.adb_capable:
        from .adb import ADB
        a = ADB(serial=dev.serial or None)
        brand = (a.getprop("ro.product.brand") or a.getprop("ro.product.manufacturer")).lower()
        model = a.getprop("ro.product.model") or model
    return brand, model


def _get_firmware(dev) -> str:
    """Bietet die passende Firmware automatisch zum Download an (Ja/Nein) –
    statt manueller Pfadeingabe. Gibt einen Ordner mit Images zurück oder ''."""
    brand, model = _device_brand_model(dev)
    ui.rule("Stock-Firmware besorgen", ui.CYAN)
    ui.kv("Erkannt", f"{brand or '?'} {model or ''}".strip())

    # 1) Schon vorhandene Firmware im Projekt automatisch finden
    import glob
    roots = [os.path.expanduser("~/Schreibtisch/Androidpanzer/samsung/firmware"),
             os.path.expanduser("~/Schreibtisch/Androidpanzer/mediatek"),
             os.path.expanduser("~/Schreibtisch/Androidpanzer/firmware"),
             os.path.expanduser("~/Downloads")]
    found = []
    for r in roots:
        found += glob.glob(os.path.join(r, "**", "*.img"), recursive=True)[:1] or \
                 glob.glob(os.path.join(r, "AP_*"), recursive=False)
    if found:
        d = os.path.dirname(found[0])
        if ui.confirm(f"Vorhandene Firmware gefunden: {d} – verwenden?", True):
            return d

    # 2) Automatischer Download je Hersteller (nur Ja/Nein!)
    if "samsung" in brand or model.upper().startswith(("SM-", "GT-")):
        if usb.have("samloader"):
            if ui.confirm("Samsung-Stock-Firmware jetzt AUTOMATISCH per samloader laden? "
                          "(mehrere GB, Ja/Nein)", False):
                try:
                    from . import samsung
                    from .adb import ADB
                    a = ADB(serial=dev.serial or None) if dev.adb_capable else None
                    return os.path.dirname(samsung.download_firmware(a, dev, {}, {"model": model}) or "") or ""
                except Exception as e:  # noqa: BLE001
                    ui.err(str(e))
        else:
            ui.warn("samloader fehlt – Auto-Download nicht möglich.")
            ui.info("Direkt-Link (manuell):  https://samfw.com/firmware/" + (model or ""))
    elif any(x in brand for x in ("xiaomi", "redmi", "poco")):
        ui.info(f"Xiaomi-Fastboot-ROM:  https://xiaomifirmwareupdater.com/?s={model}")
    elif "google" in brand or "pixel" in brand or "pixel" in model.lower():
        ui.info("Pixel Factory-Image:  https://developers.google.com/android/images "
                f"(Codename suchen: {model})")
    elif any(x in brand for x in ("oneplus", "oppo", "realme")):
        ui.info("OnePlus/Oppo OTA → boot.img extrahieren:  https://oxygenos.oneplus.net")
    else:
        ui.info("Firmware modellspezifisch suchen (Hersteller-Seite).")

    # 3) Fallback: manueller Pfad
    p = ui.ask("Pfad zu Firmware/Images-Ordner (leer = Firmware-Schritte überspringen)")
    p = os.path.expanduser(p) if p else ""
    if p and not os.path.isdir(p):
        ui.warn("Ordner nicht gefunden – übersprungen.")
        return ""
    return p


def _family(mode: str) -> str:
    if mode == "fastboot":
        return "fastboot"
    if mode in ("adb", "recovery", "sideload", "usb", "nodebug"):
        return "adb"
    if mode == "edl":
        return "edl"
    if mode in ("mtk-brom", "mtk-preloader"):
        return "mtk"
    if mode == "odin":
        return "odin"
    return "adb"


def _next_hint(mode: str) -> str:
    return {
        "fastboot": "Stock-Firmware (Factory Image) besorgen und im Aggressiv-Modus mit Firmware-Ordner erneut starten.",
        "adb": "In den Bootloader neu starten und Fastboot-Rescue fahren (tiefere Kontrolle).",
        "edl": "Herstellerspezifischen Firehose-Loader (programmer.mbn) + edl/QFIL nutzen.",
        "mtk": "mtkclient mit passender DA/Auth-Datei für dein Modell.",
        "odin": "Werks-Firmware (4-File: AP/BL/CP/CSC) per heimdall/Odin flashen.",
    }.get(_family(mode), "Externes Hersteller-Flashtool verwenden.")


def _wait_check(seconds: float) -> tuple[bool, str]:
    """Wartet kurz und prüft auf Boot."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if usb.device_booted():
            return True, "Gerät gebootet!"
        time.sleep(1)
    return False, f"nach {seconds:.0f}s noch nicht gebootet"


# ===================================================================== #
#  FASTBOOT-Katalog (~20)
# ===================================================================== #
def _fastboot_catalog(dev, fw: str) -> list[Step]:
    s = dev.serial or None
    F = lambda *a, t=30: usb.fb(list(a), s, timeout=t)  # noqa: E731

    def img(name):
        if not fw:
            return None
        for cand in (name, name + ".img"):
            p = os.path.join(fw, cand)
            if os.path.isfile(p):
                return p
        return None

    def st_devices():
        rc, o = F("devices") if False else usb.fb(["devices"], s)
        return ("fastboot" in o or rc == 0), (o or "kein Gerät")

    def st_getvar():
        rc, o = usb.fb(["getvar", "all"], s, timeout=12)
        prod = [l for l in o.splitlines() if "product" in l or "version-baseband" in l]
        return rc == 0, ("; ".join(prod) or o[:80] or "gelesen")

    def st_reboot():
        usb.fb(["reboot"], s); return _wait_check(40)

    def st_reboot_recovery():
        rc, o = usb.fb(["reboot", "recovery"], s); time.sleep(3); return rc == 0, "Recovery angefordert"

    def st_reboot_fastbootd():
        rc, o = usb.fb(["reboot", "fastboot"], s); time.sleep(3); return rc == 0, o or "fastbootd"

    def st_slot_other():
        rc, o = usb.fb(["--set-active=other"], s)
        if rc != 0:
            rc, o = usb.fb(["set_active", "other"], s)
        return rc == 0, (o or "Slot gewechselt – häufiger OTA-Bootloop-Fix")

    def st_slot(x):
        def f():
            rc, o = usb.fb([f"--set-active={x}"], s)
            if rc != 0:
                rc, o = usb.fb(["set_active", x], s)
            usb.fb(["reboot"], s)
            return _wait_check(40)
        return f

    def st_flash_vbmeta():
        v = img("vbmeta")
        if not v:
            return False, "keine vbmeta.img im Firmware-Ordner"
        rc, o = usb.fb(["--disable-verity", "--disable-verification", "flash", "vbmeta", v], s, timeout=120)
        return rc == 0, (o[:80] or "vbmeta mit deaktivierter verity geflasht")

    def st_flash(part):
        def f():
            p = img(part)
            if not p:
                return False, f"keine {part}.img im Firmware-Ordner"
            rc, o = usb.fb(["flash", part, p], s, timeout=300)
            return rc == 0, (o[:100] or f"{part} geflasht")
        return f

    def st_flashall():
        if not fw:
            return False, "kein Firmware-Ordner"
        sh = next((os.path.join(fw, x) for x in ("flash-all.sh", "flashall.sh", "flash_all.sh")
                   if os.path.isfile(os.path.join(fw, x))), None)
        if not sh:
            return False, "kein flash-all-Skript gefunden"
        import subprocess
        try:
            p = subprocess.run(["bash", sh], cwd=fw, capture_output=True, text=True, timeout=900)
            return p.returncode == 0, (p.stdout[-120:] or "flash-all ausgeführt")
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    def st_wipe():
        rc, o = usb.fb(["-w"], s, timeout=120); return rc == 0, (o[:80] or "userdata gewiped")

    def st_erase_userdata():
        rc, o = usb.fb(["erase", "userdata"], s, timeout=120); return rc == 0, (o[:80] or "userdata erased")

    def st_unlock():
        rc, o = usb.fb(["flashing", "unlock"], s, timeout=60)
        if rc != 0:
            rc, o = usb.fb(["oem", "unlock"], s, timeout=60)
        return rc == 0, (o[:80] or "unlock gesendet – am Gerät bestätigen")

    def st_boot_recovery():
        r = img("recovery") or img("boot")
        if not r:
            return False, "kein recovery/boot-Image"
        rc, o = usb.fb(["boot", r], s, timeout=120); return rc == 0, (o[:80] or "temporär gebootet")

    def st_continue():
        rc, o = usb.fb(["continue"], s); return _wait_check(40)

    def st_manual():
        return True, "Letzter Ausweg: " + _next_hint("fastboot")

    return [
        Step("Fastboot-Geräte-Check", "safe", st_devices),
        Step("Geräte-Variablen lesen (getvar all)", "safe", st_getvar),
        Step("Normaler Neustart → System", "safe", st_reboot),
        Step("Neustart → Recovery", "safe", st_reboot_recovery),
        Step("Neustart → fastbootd (userspace)", "safe", st_reboot_fastbootd),
        Step("A/B-Slot auf ANDEREN umschalten (OTA-Bootloop-Fix)", "safe", st_slot_other),
        Step("Slot A aktiv + Neustart", "safe", st_slot("a")),
        Step("Slot B aktiv + Neustart", "safe", st_slot("b")),
        Step("vbmeta mit disable-verity flashen", "destructive", st_flash_vbmeta),
        Step("boot.img flashen", "destructive", st_flash("boot")),
        Step("init_boot.img flashen", "destructive", st_flash("init_boot")),
        Step("dtbo.img flashen", "destructive", st_flash("dtbo")),
        Step("vendor_boot.img flashen", "destructive", st_flash("vendor_boot")),
        Step("system.img flashen", "destructive", st_flash("system")),
        Step("Stock flash-all-Skript ausführen", "destructive", st_flashall),
        Step("Temporär Recovery/Boot-Image booten", "destructive", st_boot_recovery),
        Step("userdata wipen (fastboot -w)", "destructive", st_wipe),
        Step("userdata erase", "destructive", st_erase_userdata),
        Step("Bootloader entsperren (flashing unlock)", "destructive", st_unlock),
        Step("fastboot continue (Boot fortsetzen)", "safe", st_continue),
        Step("Letzter Ausweg / nächste Eskalation", "manual", st_manual),
    ]


# ===================================================================== #
#  ADB / Bootloop-Katalog (~20)
# ===================================================================== #
def _adb_catalog(dev, fw: str) -> list[Step]:
    def A(args, t=15):
        s = usb.adb_serial()
        if not s:
            return 1, "kein adb-Gerät"
        return usb.adb_cmd(["-s", s] + args, timeout=t)

    def sh(cmd, root=False, t=15):
        c = f"su -c '{cmd}'" if root else cmd
        return A(["shell", c], t)

    def st_wait():
        rc, o = usb.adb_cmd(["wait-for-device"], timeout=30)
        return usb.adb_serial() is not None, ("adb-Gerät da" if usb.adb_serial() else "kein adb-Fenster")

    def st_bootflag():
        rc, o = sh("getprop sys.boot_completed", t=6); return o.strip() == "1", f"sys.boot_completed={o.strip() or '?'}"

    def st_restart_fw():
        sh("stop", root=True); time.sleep(1); sh("start", root=True); return _wait_check(35)

    def st_trim():
        rc, o = sh("pm trim-caches 999G", t=30); return rc == 0, "Laufzeit-Caches geleert"

    def st_dalvik():
        rc, o = sh("rm -rf /data/dalvik-cache/* 2>/dev/null; echo done", root=True); return "done" in o, "Dalvik/ART-Cache gelöscht"

    def st_recompile():
        rc, o = sh("cmd package compile -m speed -a", t=120); return rc == 0, (o[:80] or "Pakete neu kompiliert")

    def st_safemode_on():
        sh("setprop persist.sys.safemode 1", root=True); A(["reboot"]); return _wait_check(45)

    def st_safemode_off():
        sh("setprop persist.sys.safemode 0", root=True); return True, "Safe-Mode-Flag zurückgesetzt"

    def st_disable_crash_app():
        rc, log = A(["logcat", "-b", "crash", "-d", "-t", "300"], t=8)
        import re
        m = re.search(r"Process:\s*([\w.]+)", log) or re.search(r"\bpid\b.*?([\w.]{6,})", log)
        if not m:
            return False, "keine abstürzende App im Crash-Log gefunden"
        pkg = m.group(1)
        sh(f"pm disable-user --user 0 {pkg}")
        return True, f"verdächtige App deaktiviert: {pkg}"

    def st_df():
        rc, o = sh("df /data | tail -1", t=8); return rc == 0, (o.strip()[:80] or "Speicher geprüft")

    def st_free_space():
        sh("rm -rf /data/local/tmp/* /data/anr/* 2>/dev/null; echo ok", root=True); return True, "Temp/ANR geleert"

    def st_reboot():
        A(["reboot"]); return _wait_check(45)

    def st_reboot_recovery():
        A(["reboot", "recovery"]); time.sleep(3); return True, "Recovery angefordert"

    def st_bootctl_slot():
        rc, o = sh("bootctl set-active-boot-slot $(( ($(bootctl get-current-slot)+1)%2 ))", root=True, t=10)
        return rc == 0, (o[:60] or "A/B-Slot via bootctl gewechselt")

    def st_reboot_bootloader():
        A(["reboot", "bootloader"]); return True, "→ Bootloader (für Fastboot-Rescue)"

    def st_logsave():
        s = usb.adb_serial()
        if not s:
            return False, "kein Gerät"
        out = os.path.expanduser("~/Schreibtisch/Androidpanzer/bootloop")
        os.makedirs(out, exist_ok=True)
        _, lc = sh("logcat -b crash,system -d -t 500", t=8)
        _, dm = sh("dmesg", t=8)
        open(os.path.join(out, "rescue_logs.txt"), "w", errors="replace").write(lc + "\n\n" + dm)
        return True, "Logs gesichert (bootloop/rescue_logs.txt)"

    def st_factory():
        sh("am broadcast -a android.intent.action.MASTER_CLEAR", root=False); return True, "Factory-Reset-Broadcast gesendet"

    def st_recovery_wipe():
        A(["reboot", "recovery"]); return True, "In Recovery → dort 'wipe cache/data' wählen"

    def st_manual():
        return True, _next_hint("adb")

    return [
        Step("Auf flüchtiges ADB-Fenster warten", "safe", st_wait),
        Step("Boot-Status lesen (sys.boot_completed)", "safe", st_bootflag),
        Step("Logs sichern (logcat crash/system + dmesg)", "safe", st_logsave),
        Step("Android-Framework neu starten (stop/start)", "safe", st_restart_fw),
        Step("Laufzeit-Caches leeren (pm trim-caches)", "safe", st_trim),
        Step("Dalvik/ART-Cache löschen", "safe", st_dalvik),
        Step("Speicherplatz prüfen (/data)", "safe", st_df),
        Step("Temp/ANR aufräumen", "safe", st_free_space),
        Step("Abstürzende App aus Crash-Log deaktivieren", "safe", st_disable_crash_app),
        Step("Pakete neu kompilieren (speed)", "safe", st_recompile),
        Step("Abgesicherten Modus erzwingen + Neustart", "safe", st_safemode_on),
        Step("Normaler Neustart", "safe", st_reboot),
        Step("A/B-Slot via bootctl wechseln", "safe", st_bootctl_slot),
        Step("Safe-Mode-Flag zurücksetzen", "safe", st_safemode_off),
        Step("In Recovery neu starten", "safe", st_reboot_recovery),
        Step("Cache/Data-Wipe in Recovery (manuell)", "manual", st_recovery_wipe),
        Step("Factory-Reset-Broadcast", "destructive", st_factory),
        Step("In Bootloader wechseln (für Fastboot-Rescue)", "safe", st_reboot_bootloader),
        Step("Nächste Eskalation", "manual", st_manual),
    ]


# ===================================================================== #
#  EDL / MTK / ODIN – externe Tools (Erkennung + Reset + Anleitung)
# ===================================================================== #
def _edl_catalog(dev, fw: str) -> list[Step]:
    def have(t):
        return usb.have(t)

    def st_detect():
        if have("edl"):
            import subprocess
            try:
                o = subprocess.run(["edl", "printgpt"], capture_output=True, text=True, timeout=30).stdout
                return bool(o), (o[:100] or "edl antwortet")
            except Exception as e:  # noqa: BLE001
                return False, str(e)
        return False, "Tool 'edl' (bkerler) nicht installiert: pip install edlclient"

    def st_reset():
        if have("edl"):
            import subprocess
            try:
                subprocess.run(["edl", "reset"], capture_output=True, timeout=20)
                return _wait_check(30)
            except Exception as e:  # noqa: BLE001
                return False, str(e)
        return False, "edl fehlt"

    def st_flash():
        if not fw:
            return False, "kein Firmware/Loader-Ordner (programmer.mbn + rawprogram*.xml nötig)"
        return True, ("Im Aggressiv-Modus: edl w <partition> <img> bzw. "
                      "QFIL/MiFlash mit Firehose-Loader (modellspezifisch)")

    def st_manual():
        return True, _next_hint("edl")

    return [
        Step("EDL erkennen / GPT lesen", "safe", st_detect),
        Step("EDL-Reset (Gerät neu starten)", "safe", st_reset),
        Step("Partitionen flashen (Firehose)", "destructive", st_flash),
        Step("Anleitung / Tool-Tipp", "manual", st_manual),
    ]


def _mtk_catalog(dev, fw: str) -> list[Step]:
    def st_detect():
        if usb.have("mtk"):
            return True, "mtkclient vorhanden – 'mtk printgpt' zum Lesen"
        return False, "mtkclient fehlt: pip install mtkclient (oder Repo klonen)"

    def st_reset():
        if usb.have("mtk"):
            import subprocess
            try:
                subprocess.run(["mtk", "reset"], capture_output=True, timeout=20)
                return _wait_check(30)
            except Exception as e:  # noqa: BLE001
                return False, str(e)
        return False, "mtk fehlt"

    def st_flash():
        return (bool(fw), "Aggressiv: mtk w <part> <img> / SP Flash Tool mit scatter-Datei"
                if fw else "kein scatter/Firmware-Ordner")

    def st_manual():
        return True, _next_hint("mtk")

    return [
        Step("MediaTek erkennen (BROM/Preloader)", "safe", st_detect),
        Step("MTK-Reset", "safe", st_reset),
        Step("Partitionen flashen (DA)", "destructive", st_flash),
        Step("Anleitung / Tool-Tipp", "manual", st_manual),
    ]


def _odin_catalog(dev, fw: str) -> list[Step]:
    def st_detect():
        if usb.have("heimdall"):
            import subprocess
            try:
                o = subprocess.run(["heimdall", "detect"], capture_output=True, text=True, timeout=15).stdout
                return "detected" in o.lower(), (o[:80] or "heimdall detect")
            except Exception as e:  # noqa: BLE001
                return False, str(e)
        return False, "heimdall fehlt: apt install heimdall-flash"

    def st_pit():
        if usb.have("heimdall"):
            import subprocess
            try:
                o = subprocess.run(["heimdall", "print-pit"], capture_output=True, text=True, timeout=30).stdout
                return bool(o), "PIT (Partitionstabelle) gelesen"
            except Exception as e:  # noqa: BLE001
                return False, str(e)
        return False, "heimdall fehlt"

    def st_flash():
        return (bool(fw), "Aggressiv: heimdall flash --AP <ap.img> … bzw. Odin 4-File (AP/BL/CP/CSC)"
                if fw else "kein Firmware-Ordner (4-File)")

    def st_manual():
        return True, _next_hint("odin")

    return [
        Step("Samsung Download erkennen (heimdall detect)", "safe", st_detect),
        Step("Partitionstabelle lesen (print-pit)", "safe", st_pit),
        Step("Werks-Firmware flashen (4-File)", "destructive", st_flash),
        Step("Anleitung / Tool-Tipp", "manual", st_manual),
    ]


BUILDERS = {
    "fastboot": _fastboot_catalog,
    "adb": _adb_catalog,
    "edl": _edl_catalog,
    "mtk": _mtk_catalog,
    "odin": _odin_catalog,
}


# --------------------------------------------------------------------- #
def _save_log(dev, log) -> None:
    out = os.path.expanduser("~/Schreibtisch/Androidpanzer/rescue")
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, f"rescue_{dev.mode}_{int(time.monotonic())}.txt")
    body = (f"AUTO-RESCUE · Modus {dev.mode} · {dev.label}\n\n"
            + "\n".join(f"[{status.upper():4}] {name}: {msg}" for name, status, msg in log) + "\n")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    ui.show_report(body, "Auto-Rescue · Protokoll", p, note="Rescue-Protokoll")
