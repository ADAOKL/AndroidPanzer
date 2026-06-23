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


def _bootloader_status(adb: ADB) -> None:
    """Bootloader-Lock-Status prüfen."""
    ui.clear()
    ui.rule("🔓 BOOTLOADER STATUS", ui.BCYAN)
    print()
    props = {
        "OEM Unlock erlaubt":     adb.shell("getprop ro.oem_unlock_supported 2>/dev/null").strip(),
        "Bootloader Status":      adb.shell("getprop ro.boot.flash.locked 2>/dev/null").strip(),
        "Bootloader-String":      adb.shell("getprop ro.boot.bootloader 2>/dev/null").strip(),
        "Secure Boot State":      adb.shell("getprop ro.boot.verifiedbootstate 2>/dev/null").strip(),
        "dm-verity Modus":        adb.shell("getprop ro.boot.veritymode 2>/dev/null").strip(),
        "vbmeta Device State":    adb.shell("getprop ro.boot.vbmeta.device_state 2>/dev/null").strip(),
        "AVB-Version":            adb.shell("getprop ro.boot.avb_version 2>/dev/null").strip(),
        "Build-Type":             adb.shell("getprop ro.build.type 2>/dev/null").strip(),
        "Release-Keys":           adb.shell("getprop ro.build.tags 2>/dev/null").strip(),
        "Unlock-Allowed (OEM)":   adb.shell("getprop sys.oem_unlock_allowed 2>/dev/null").strip(),
    }
    for k, v in props.items():
        if not v:
            continue
        if v in ("0", "unlocked", "orange", "1") and k in ("OEM Unlock erlaubt", "Unlock-Allowed (OEM)"):
            col = ui.BGREEN if v == "1" else ui.GREY
        elif v == "unlocked" or v == "orange":
            col = ui.BYELLOW
        elif v in ("locked", "green", "enforcing"):
            col = ui.BGREEN
        else:
            col = ui.GREY
        ui.kv(k, f"{col}{v}{ui.RESET}")
    print()
    locked_val = props.get("Bootloader Status", "")
    vbs = props.get("Secure Boot State", "")
    if locked_val == "0" or vbs in ("orange", "yellow"):
        ui.warn("Bootloader ist ENTSPERRT (orange/unverified boot state)")
    elif locked_val == "1" or vbs == "green":
        ui.ok("Bootloader ist gesperrt (green verified boot state)")
    else:
        ui.info("Bootloader-Status nicht eindeutig — Fastboot-Modus für genaue Auskunft")
    print()
    # Fastboot-Info falls verfügbar
    try:
        fb_out = subprocess.run(["fastboot", "getvar", "unlocked"],
                                capture_output=True, text=True, timeout=5).stderr.strip()
        if fb_out:
            ui.kv("fastboot unlocked", fb_out[:100])
    except Exception:
        pass


def _usb_diagnostics(adb: ADB) -> None:
    """USB-Verbindungs-Diagnose."""
    ui.clear()
    ui.rule("🔌 USB-DIAGNOSE", ui.BCYAN)
    print()
    cmds = [
        ("lsusb Android",  "lsusb 2>/dev/null | grep -iE 'android|samsung|google|qualcomm|mediatek'"),
        ("adb devices",    "adb devices 2>/dev/null"),
        ("fastboot devs",  "fastboot devices 2>/dev/null"),
        ("dmesg USB",      "dmesg 2>/dev/null | grep -iE 'usb.*android|android.*usb|ttyUSB|ACM' | tail -12"),
        ("USB-Kernel-Mod", "lsmod 2>/dev/null | grep -iE 'usb|android|cdc'"),
        ("udev-Regeln",    "ls /etc/udev/rules.d/ 2>/dev/null | grep -iE 'android|51'"),
    ]
    for label, cmd in cmds:
        try:
            out = subprocess.run(cmd, shell=True, capture_output=True,
                                 text=True, timeout=8).stdout.strip()
        except Exception:
            out = ""
        if out:
            ui.kv(label, out[:400])
    print()
    ui.info("Falls Gerät nicht erkannt:")
    print(f"  {ui.GREY}sudo apt install android-sdk-platform-tools adb fastboot")
    print(f"  sudo usermod -aG plugdev $USER")
    print(f"  echo 'SUBSYSTEM==\"usb\", ATTR{{idVendor}}==\"18d1\", MODE=\"0666\", GROUP=\"plugdev\"'")
    print(f"  sudo tee /etc/udev/rules.d/51-android.rules && sudo udevadm control --reload{ui.RESET}")


def _adb_commands_cheatsheet() -> None:
    """Wichtige ADB-Befehle Referenz."""
    ui.clear()
    ui.rule("📋 ADB & FASTBOOT CHEATSHEET", ui.BCYAN)
    print(f"""
{ui.BOLD}── VERBINDUNG ──────────────────────────────────────────────────────{ui.RESET}
{ui.GREY}  adb devices                       # Verbundene Geräte
  adb connect <IP>:5555             # Wireless ADB
  adb pair <IP>:<PORT>              # Android 11+ Pair
  adb kill-server && adb start-server   # Neustart ADB-Server
  adb -s <SERIAL> shell             # Bestimmtes Gerät{ui.RESET}

{ui.BOLD}── SHELL & INFO ────────────────────────────────────────────────────{ui.RESET}
{ui.GREY}  adb shell                         # Interaktive Shell
  adb shell getprop ro.build.version.release   # Android-Version
  adb shell getprop ro.product.brand           # Marke
  adb shell dumpsys battery          # Akku-Status
  adb shell wm size                  # Display-Auflösung
  adb shell input keyevent 26        # Power-Taste{ui.RESET}

{ui.BOLD}── DATEIEN ─────────────────────────────────────────────────────────{ui.RESET}
{ui.GREY}  adb pull /pfad/auf/gerät ./local/ # Datei herunterladen
  adb push datei.txt /sdcard/        # Datei hochladen
  adb pull /data/data/com.pkg/ .     # App-Daten (Root)
  adb shell ls /sdcard/              # Verzeichnis auflisten{ui.RESET}

{ui.BOLD}── APPS ────────────────────────────────────────────────────────────{ui.RESET}
{ui.GREY}  adb install app.apk               # APK installieren
  adb install -r app.apk            # Reinstall (Daten behalten)
  adb uninstall com.pkg.name        # App deinstallieren
  adb shell pm list packages -3     # Drittanbieter-Apps
  adb shell pm disable-user --user 0 com.pkg  # App deaktivieren
  adb shell am start -n pkg/.Act    # App starten
  adb shell am force-stop com.pkg   # App beenden{ui.RESET}

{ui.BOLD}── REBOOT / MODUS ──────────────────────────────────────────────────{ui.RESET}
{ui.GREY}  adb reboot                        # Normal neu starten
  adb reboot bootloader             # → Fastboot-Modus
  adb reboot recovery               # → Recovery
  adb reboot download               # → Download-Modus (Samsung)
  adb reboot edl                    # → EDL-Modus
  adb reboot sideload               # → ADB-Sideload{ui.RESET}

{ui.BOLD}── LOGCAT ──────────────────────────────────────────────────────────{ui.RESET}
{ui.GREY}  adb logcat                        # Live-Log
  adb logcat -d > log.txt           # Log speichern
  adb logcat -c && adb logcat       # Log leeren dann live
  adb logcat *:E                    # Nur Fehler
  adb logcat -s TAG:V               # Bestimmtes Tag{ui.RESET}

{ui.BOLD}── FASTBOOT ────────────────────────────────────────────────────────{ui.RESET}
{ui.GREY}  fastboot devices                  # Erkannte Geräte
  fastboot getvar all               # Alle Fastboot-Variablen
  fastboot oem unlock               # Bootloader (ältere Geräte)
  fastboot flashing unlock          # Bootloader (neuere Geräte)
  fastboot flash boot boot.img      # Boot-Image flashen
  fastboot flash recovery twrp.img  # Recovery flashen
  fastboot flash system system.img  # System flashen (Vorsicht!)
  fastboot wipe userdata            # Daten löschen
  fastboot reboot                   # Neu starten
  fastboot reboot recovery          # → Recovery
  fastboot reboot bootloader        # → Bootloader bleibt{ui.RESET}

{ui.BOLD}── HEIMDALL (Samsung) ──────────────────────────────────────────────{ui.RESET}
{ui.GREY}  heimdall detect                   # Gerät im Download-Modus
  heimdall print-pit                # Partition-Layout
  heimdall flash --RECOVERY twrp.img --no-reboot
  heimdall flash --BOOT boot.img{ui.RESET}
""")


def _wireless_adb(adb: ADB) -> None:
    """Wireless ADB einrichten."""
    ui.clear()
    ui.rule("📶 WIRELESS ADB EINRICHTEN", ui.BCYAN)
    print()
    dev_ip = adb.shell(
        "ip -4 addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1").strip()
    if not dev_ip:
        dev_ip = adb.shell(
            "ip addr 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d/ -f1"
        ).strip()
    print(f"  {ui.BOLD}Android 11+ (Wireless Debugging):{ui.RESET}")
    print(f"  {ui.GREY}Einstellungen → Entwickleroptionen → Drahtloses Debuggen aktivieren")
    print(f"  → 'Mit QR-Code koppeln'  ODER  'Mit Kopplungscode koppeln'")
    print(f"  adb pair <IP>:<PAIR-PORT>     (Port aus den Entwickleroptionen ablesen!){ui.RESET}")
    print()
    if dev_ip:
        print(f"  {ui.BOLD}Gerät-IP erkannt: {ui.BGREEN}{dev_ip}{ui.RESET}")
        print(f"  {ui.GREY}adb connect {dev_ip}:5555{ui.RESET}")
        print()
        if ui.confirm("Wireless ADB auf Port 5555 jetzt aktivieren?", True):
            adb.shell("setprop service.adb.tcp.port 5555 2>/dev/null")
            adb.shell("stop adbd 2>/dev/null; start adbd 2>/dev/null")
            ui.ok(f"TCP-ADB aktiviert → führe aus: adb connect {dev_ip}:5555")
    else:
        ui.warn("Gerät-IP nicht ermittelbar — WLAN aktiv?")
    print()
    print(f"  {ui.BOLD}Classic-Methode (USB → dann Wireless):{ui.RESET}")
    print(f"  {ui.GREY}1. Gerät per USB anschließen")
    print(f"  2. adb tcpip 5555")
    print(f"  3. USB trennen")
    print(f"  4. adb connect <GERÄT-IP>:5555{ui.RESET}")
    print()
    # Test ob Wireless-Verbindung bereits offen
    tcp_port = adb.shell("getprop service.adb.tcp.port 2>/dev/null").strip()
    if tcp_port:
        ui.kv("Aktueller TCP-Port", tcp_port)


def _scrcpy_guide(adb: ADB) -> None:
    """scrcpy Screen-Mirroring Guide."""
    ui.clear()
    ui.rule("🖥  SCRCPY – SCREEN MIRRORING & AUFNAHME", ui.BCYAN)
    has_scrcpy = subprocess.run("which scrcpy 2>/dev/null", shell=True,
                                capture_output=True).returncode == 0
    print(f"\n  scrcpy installiert: {ui.BGREEN + '✓' if has_scrcpy else ui.BRED + '✗'}{ui.RESET}")
    if not has_scrcpy:
        print(f"  {ui.GREY}sudo apt install scrcpy{ui.RESET}\n")
    print(f"""
  {ui.BOLD}Basis:{ui.RESET}
  {ui.GREY}scrcpy                              # Bildschirm spiegeln
  scrcpy --record recording.mp4       # Spiegeln + Video
  scrcpy --no-display --record vid.mp4  # Nur aufnehmen, kein Fenster
  scrcpy --bit-rate 4M                # Qualität (Standard: 8M)
  scrcpy --max-size 1080              # Auflösung begrenzen
  scrcpy --turn-screen-off -w         # Geräte-Display aus{ui.RESET}

  {ui.BOLD}Audio (Android 11+):{ui.RESET}
  {ui.GREY}scrcpy --audio-codec opus
  scrcpy --no-audio{ui.RESET}

  {ui.BOLD}Keyboard/Mouse/Clipboard:{ui.RESET}
  {ui.GREY}scrcpy --keyboard=uhid           # Physische Tastatur senden
  scrcpy --mouse=uhid              # Maus-Events
  scrcpy --stay-awake              # Gerät wach halten{ui.RESET}

  {ui.BOLD}Wireless:{ui.RESET}
  {ui.GREY}scrcpy --tcpip=<IP>:5555{ui.RESET}
""")
    if has_scrcpy:
        dev_ip = adb.shell(
            "ip -4 addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1").strip()
        if dev_ip:
            print(f"  {ui.BOLD}Wireless-Befehl für dieses Gerät:{ui.RESET}")
            print(f"  {ui.GREY}scrcpy --tcpip={dev_ip}:5555{ui.RESET}\n")
        if ui.confirm("scrcpy jetzt starten (USB)?", False):
            subprocess.Popen("scrcpy 2>/dev/null &", shell=True)
            ui.ok("scrcpy gestartet im Hintergrund.")


def _oem_unlock_guide(adb: ADB, data: dict) -> None:
    """OEM-Unlock Schritt-für-Schritt je Hersteller."""
    brand = (data or {}).get("brand", "").lower()
    model = (data or {}).get("model", "Unbekannt")
    android = (data or {}).get("android", "?")
    ui.clear()
    ui.rule("🔓 OEM-UNLOCK ANLEITUNG", ui.BYELLOW)
    print()
    print(f"  Gerät:   {ui.BOLD}{brand.title()} {model}{ui.RESET}")
    print(f"  Android: {ui.BOLD}{android}{ui.RESET}\n")
    oem_allowed = adb.shell("getprop ro.oem_unlock_supported 2>/dev/null").strip()
    vbs = adb.shell("getprop ro.boot.verifiedbootstate 2>/dev/null").strip()
    ui.kv("OEM-Unlock unterstützt", oem_allowed or "?")
    ui.kv("Verified Boot State", vbs or "?")
    print()
    if vbs in ("orange", "yellow"):
        ui.warn("Bootloader ist BEREITS ENTSPERRT — weiter zu Root/ROM!")
    print(f"  {ui.BOLD}Schritt 1 – Entwickleroptionen aktivieren:{ui.RESET}")
    print(f"  {ui.GREY}Einstellungen → Über das Telefon → Build-Nummer 7× tippen{ui.RESET}\n")
    print(f"  {ui.BOLD}Schritt 2 – OEM-Entsperrung aktivieren:{ui.RESET}")
    print(f"  {ui.GREY}Einstellungen → Entwickleroptionen → OEM-Entsperrung → EIN{ui.RESET}\n")
    print(f"  {ui.BOLD}Schritt 3 – Fastboot-Modus:{ui.RESET}")
    print(f"  {ui.GREY}adb reboot bootloader{ui.RESET}\n")
    print(f"  {ui.BOLD}Schritt 4 – Bootloader entsperren:{ui.RESET}")
    if "samsung" in brand:
        print(f"  {ui.BRED}Samsung nutzt KEINEN Fastboot-Unlock!{ui.RESET}")
        print(f"  {ui.GREY}Samsung: Download-Modus → Heimdall  (niemals fastboot oem unlock!)")
        print(f"  Modelle ab S10/Note10: Vol-Hoch+Runter + USB-Kabel → im blauen Screen Vol-Hoch{ui.RESET}")
    elif "xiaomi" in brand or "redmi" in brand or "poco" in brand:
        print(f"  {ui.GREY}Xiaomi: Mi Unlock Tool erforderlich (nur Windows / Wine)")
        print(f"  Download: https://www.miui.com/unlock/download.html")
        print(f"  Wartezeit: 72h–7 Tage nach Konto-Verknüpfung!{ui.RESET}")
    elif "huawei" in brand or "honor" in brand:
        print(f"  {ui.BRED}Huawei: Offizieller Unlock seit 2018 abgestellt.{ui.RESET}")
        print(f"  {ui.GREY}Alternativen: dc-unlocker, HCU Client (kostenpflichtig){ui.RESET}")
    else:
        print(f"  {ui.GREY}fastboot flashing unlock    # Pixel/OnePlus/Motorola (neuere)")
        print(f"  fastboot oem unlock         # ältere Geräte")
        print(f"  Im Bootloader-Menü mit Vol-Tasten bestätigen!{ui.RESET}")
    print()
    ui.warn("OEM-Unlock LÖSCHT ALLE GERÄTEDATEN. Backup zuerst!")


def _device_info_dump(adb: ADB, data: dict) -> None:
    """Vollständiger Geräte-Info-Dump."""
    import os
    import time as _time
    ui.clear()
    ui.rule("📊 GERÄTE-INFO DUMP", ui.BCYAN)
    print()
    brand = (data or {}).get("brand", "?")
    model = (data or {}).get("model", "?")
    props_cmds = [
        ("Marke",           "getprop ro.product.brand"),
        ("Modell",          "getprop ro.product.model"),
        ("Hersteller",      "getprop ro.product.manufacturer"),
        ("Codename",        "getprop ro.product.device"),
        ("Android",         "getprop ro.build.version.release"),
        ("SDK",             "getprop ro.build.version.sdk"),
        ("Build",           "getprop ro.build.id"),
        ("Fingerprint",     "getprop ro.build.fingerprint"),
        ("Bootloader",      "getprop ro.bootloader"),
        ("Baseband",        "getprop gsm.version.baseband"),
        ("CPU ABI",         "getprop ro.product.cpu.abi"),
        ("RAM",             "cat /proc/meminfo 2>/dev/null | grep MemTotal"),
        ("Storage",         "df /data 2>/dev/null | tail -1"),
        ("Kernel",          "uname -r 2>/dev/null"),
        ("Serial",          "getprop ro.serialno"),
        ("IMEI (adb)",      "service call iphonesubinfo 1 2>/dev/null | awk -F\\\"'\\\"' '{print $2}' | tr -d '.'"),
        ("Akku %",          "dumpsys battery 2>/dev/null | grep level"),
        ("Temperatur",      "dumpsys battery 2>/dev/null | grep temperature"),
    ]
    lines = [f"# Geräte-Dump {brand} {model} – {_time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    for label, cmd in props_cmds:
        val = adb.shell(cmd + " 2>/dev/null").strip()
        if val:
            ui.kv(label, val[:100])
            lines.append(f"{label}: {val}")
    # Speichern
    out_dir = os.path.expanduser("~/Schreibtisch/Androidpanzer/modeswitch")
    os.makedirs(out_dir, exist_ok=True)
    fn = os.path.join(out_dir, f"device_dump_{model.replace(' ','_')}.txt")
    try:
        with open(fn, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        ui.ok(f"Dump gespeichert: {fn}")
    except OSError as e:
        ui.err(str(e))


def menu(adb: ADB, dev: Device, st: dict, data: dict | None = None) -> None:
    """Interaktiver Modus-Umschalter — maximal ausgebaut."""
    while True:
        ui.clear()
        ui.banner(subtitle="🔁 Modus-Wechsel & Gerät-Steuerung")
        cur = current(getattr(dev, "serial", None))
        ui.kv("Aktueller Modus",
              f"{usb.mode_badge(cur.mode)}  {cur.label}" if cur else "kein Gerät erkannt")
        print()
        ch = ui.menu("Aktion", [
            ("1",  "📥 Download-Modus      (Samsung Odin/Heimdall)"),
            ("2",  "⚡ Fastboot/Bootloader  (Flashen/Unlock)"),
            ("3",  "🛟 Recovery             (TWRP/Stock)"),
            ("4",  "📦 ADB-Sideload         (OTA/ZIP flashen)"),
            ("5",  "▶  System               (normal neu starten)"),
            ("6",  "🔌 EDL-Modus            (Qualcomm 9008/Emergency)"),
            ("7",  "🔓 Bootloader-Status    (locked/unlocked/OEM-Info)"),
            ("8",  "📋 ADB Cheatsheet       (ADB & Fastboot Befehle)"),
            ("9",  "📶 Wireless ADB         (TCP/IP · Android 11+ Pair)"),
            ("10", "🖥  scrcpy Mirroring     (Bildschirm spiegeln/aufnehmen)"),
            ("11", "🔌 USB-Diagnose         (lsusb · udev · Treiber)"),
            ("12", "🔓 OEM-Unlock Anleitung (Schritt-für-Schritt je Hersteller)"),
            ("13", "📊 Geräte-Info Dump     (alle Props, RAM, Storage, IMEI)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch in ("1", "2", "3", "4", "5", "6"):
            target_map = {"1": "download", "2": "fastboot", "3": "recovery",
                          "4": "sideload", "5": "system", "6": "edl"}
            ensure(adb, dev, target_map[ch])
            ui.pause()
        elif ch == "7":
            _bootloader_status(adb)
            ui.pause()
        elif ch == "8":
            _adb_commands_cheatsheet()
            ui.pause()
        elif ch == "9":
            _wireless_adb(adb)
            ui.pause()
        elif ch == "10":
            _scrcpy_guide(adb)
            ui.pause()
        elif ch == "11":
            _usb_diagnostics(adb)
            ui.pause()
        elif ch == "12":
            _oem_unlock_guide(adb, data or {})
            ui.pause()
        elif ch == "13":
            _device_info_dump(adb, data or {})
            ui.pause()
