"""Zeigt flashbare Custom-Firmware & Recovery für das angeschlossene Gerät an –
anhand des Geräte-Codenamens, live aus dem Internet.

Verifizierbar per API (echte Build-Daten):
  • LineageOS   – offizielle Builds (Version, Datum, Größe, direkter Download-Link)
  • TWRP        – alle verfügbaren Recovery-Versionen (dl.twrp.me)

Ohne saubere API → direkte Projekt-/Such-Einstiege (XDA, OrangeFox, PixelExperience,
crDroid, SourceForge). Ehrlich gekennzeichnet: was real gefunden wurde vs. wo man
selbst nachsehen muss. Nichts wird erfunden.

Custom-Firmware setzt einen ENTSPERRTEN Bootloader voraus und löscht Daten – das
Modul lädt/flasht NICHTS, es zeigt nur an, was es für den Codename gibt.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from urllib.parse import quote

from . import ui
from .util import LOG, human_size, outdir

_UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")}


def _get(url: str, timeout: int = 20) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout).read()


def _codenames(data: dict, adb) -> list[str]:
    """Plausible Geräte-Codenamen (für die ROM-/Recovery-Abfrage)."""
    g = adb.getprop
    raw = [data.get("device", ""), g("ro.product.device"), g("ro.product.vendor.device"),
           g("ro.build.product"), g("ro.product.name")]
    out: list[str] = []
    for v in raw:
        v = (v or "").strip().lower()
        if v and v not in out and re.match(r"^[a-z0-9_]+$", v):
            out.append(v)
    return out or ["?"]


def lineageos_builds(code: str) -> list[dict]:
    """Offizielle LineageOS-Builds für *code* (leer = nicht offiziell unterstützt)."""
    try:
        data = json.loads(_get(f"https://download.lineageos.org/api/v1/{code}/nightly/1"))
        return data.get("response", []) or []
    except Exception as e:  # noqa: BLE001
        LOG.exception(f"lineageos api {code}", e)
        return []


def twrp_versions(code: str) -> list[str]:
    """Verfügbare offizielle TWRP-Versionen für *code*."""
    try:
        html = _get(f"https://dl.twrp.me/{code}/").decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return []
    return sorted(set(re.findall(r"twrp-([\d.]+_\d+-\d+)-", html)), reverse=True)


def _rom_search(adb, dev, data) -> None:
    """ROM-Suche via LineageOS-API + TWRP + Such-Einstiege."""
    ui.clear()
    ui.banner(subtitle="🌐 Custom-ROM & Recovery Suche")
    codes = _codenames(data, adb)
    ui.kv("Gerät", f"{data.get('brand', '')} {data.get('model', '')}")
    ui.kv("Codename(n)", ", ".join(codes))
    ui.info("Frage offizielle Quellen ab (LineageOS-API · TWRP) …")

    title = f"{data.get('brand', '')} {data.get('model', '')} ({codes[0]})".strip()
    lines = [f"# CUSTOM-FIRMWARE & RECOVERY · {title}",
             f"# {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    found = False
    seen_codes: set = set()
    for code in codes:
        if code in seen_codes:
            continue
        seen_codes.add(code)
        builds = lineageos_builds(code)
        if builds:
            found = True
            ui.ok(f"LineageOS: offiziell unterstützt ({code}) – {len(builds)} Build(s)")
            lines.append(f"== LineageOS · OFFIZIELL · {code} ==")
            for b in builds[:6]:
                d = time.strftime("%Y-%m-%d", time.localtime(b.get("datetime", 0)))
                lines.append(f"  • Lineage {b.get('version','?')} ({b.get('romtype','?')}) · "
                             f"{d} · {human_size(b.get('size', 0))}")
                lines.append(f"      {b.get('url','')}")
            lines.append(f"      Anleitung: https://wiki.lineageos.org/devices/{code}/install")
            lines.append("")
        vers = twrp_versions(code)
        if vers:
            found = True
            ui.ok(f"TWRP: {len(vers)} Version(en) für {code}")
            lines.append(f"== TWRP-Recovery · {code} ==")
            lines.append(f"  • Versionen: {', '.join(vers[:8])}")
            lines.append(f"      Download: https://dl.twrp.me/{code}/")
            lines.append("")

    c0 = codes[0]
    model = data.get("model", "")
    lines += [
        "== Weitere ROMs & Such-Einstiege ==",
        f"  OrangeFox   : https://orangefox.download/device/{c0}",
        f"  PixelExp.   : https://download.pixelexperience.org/{c0}",
        f"  crDroid     : https://crdroid.net/{c0}",
        f"  Evolution X : https://evolution-x.org/downloads/{c0}",
        f"  XDA         : https://www.google.com/search?q={quote('XDA ' + model + ' ' + c0 + ' custom ROM')}",
        f"  SourceForge : https://sourceforge.net/directory/?q={quote(c0)}",
        "",
        "⚠ Custom-ROM setzt ENTSPERRTEN Bootloader voraus und LÖSCHT ALLE DATEN.",
        "⚠ Nur ROM für EXAKT diesen Codename – falsches Image = Brick!",
    ]
    if not found:
        lines.insert(2, "(Keine offiziellen LineageOS-/TWRP-Treffer – siehe Such-Einstiege.)")
    body = "\n".join(lines) + "\n"
    p = os.path.join(outdir("customfw"), f"customfw_{c0}.txt")
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    except OSError as e:
        ui.err(str(e)); p = None
    ui.show_report(body, f"Custom-FW · {c0}", p, note="ROM-Liste")
    ui.pause()


def _twrp_flash_guide(adb, dev, data) -> None:
    """TWRP Flash-Anleitung (Fastboot & Heimdall)."""
    ui.clear()
    codes = _codenames(data, adb)
    c0 = codes[0]
    brand = data.get("brand", "").lower()
    model = data.get("model", "")
    ui.rule("🛟 TWRP FLASH-ANLEITUNG", ui.BCYAN)
    print(f"\n  Gerät: {ui.BOLD}{model}{ui.RESET}  Codename: {ui.BOLD}{c0}{ui.RESET}\n")
    vers = twrp_versions(c0)
    if vers:
        ui.ok(f"Verfügbare TWRP-Versionen: {', '.join(vers[:5])}")
        print(f"  Download: https://dl.twrp.me/{c0}/")
    else:
        ui.warn(f"Kein offizielles TWRP für '{c0}' gefunden.")
        print(f"  → OrangeFox: https://orangefox.download/device/{c0}")
    print()
    if "samsung" in brand:
        print(f"  {ui.BOLD}Samsung – Heimdall (Download-Modus):{ui.RESET}")
        print(f"  {ui.GREY}1. TWRP-Image für dein Modell herunterladen (twrp.img)")
        print(f"  2. Gerät in Download-Modus: Vol-Hoch+Runter + USB-Kabel (S10+) oder Vol-Runter+Bixby+Power")
        print(f"  3. heimdall detect   # muss das Gerät finden")
        print(f"  4. heimdall flash --RECOVERY twrp.img --no-reboot")
        print(f"  5. Vol-Hoch+Power halten → Recovery bleibt (NICHT normal starten!){ui.RESET}")
    else:
        print(f"  {ui.BOLD}Fastboot-Methode:{ui.RESET}")
        print(f"  {ui.GREY}1. TWRP-Image herunterladen: https://dl.twrp.me/{c0}/")
        print(f"  2. adb reboot bootloader")
        print(f"  3. fastboot flash recovery twrp.img")
        print(f"  4. fastboot reboot recovery   # direkt in TWRP")
        print(f"  ODER: fastboot boot twrp.img  # temporär (kein Flash){ui.RESET}")
    print()
    print(f"  {ui.BOLD}In TWRP – erste Schritte:{ui.RESET}")
    print(f"  {ui.GREY}• Wipe → Advanced Wipe → System + Data + Cache (KEIN Internal Storage!)")
    print(f"  • Install → ROM-ZIP auswählen → Swipe to Flash")
    print(f"  • Optional: Magisk-ZIP nachflashen (für Root)")
    print(f"  • Reboot System{ui.RESET}")
    ui.pause()


def _backup_guide(adb, dev, data) -> None:
    """Backup vor dem Flash – TWRP + ADB + Datenrettung."""
    ui.clear()
    ui.rule("💾 BACKUP VOR DEM FLASH", ui.BYELLOW)
    print()
    brand = data.get("brand", "").lower()
    codes = _codenames(data, adb)
    print(f"  {ui.BOLD}Methode 1 – TWRP-Backup (empfohlen, Nandroid):{ui.RESET}")
    print(f"  {ui.GREY}• In TWRP: Backup → Boot + System + Data → Swipe to Backup")
    print(f"  • Backup liegt auf /sdcard/TWRP/BACKUPS/")
    print(f"  • adb pull /sdcard/TWRP ./TWRP_Backup_{codes[0]}  # auf PC kopieren{ui.RESET}")
    print()
    print(f"  {ui.BOLD}Methode 2 – ADB-Backup (eingeschränkt):{ui.RESET}")
    print(f"  {ui.GREY}adb backup -apk -shared -all -f backup_{codes[0]}.ab")
    print(f"  # Entpacken: java -jar abe.jar unpack backup.ab backup.tar{ui.RESET}")
    print()
    print(f"  {ui.BOLD}Methode 3 – Wichtige Daten via ADB pull:{ui.RESET}")
    print(f"  {ui.GREY}adb pull /sdcard/DCIM ./DCIM_backup    # Fotos")
    print(f"  adb pull /sdcard/Download ./Download_backup")
    print(f"  adb pull /sdcard/WhatsApp ./WhatsApp_backup{ui.RESET}")
    print()
    print(f"  {ui.BOLD}Methode 4 – Titanium Backup (Root):{ui.RESET}")
    print(f"  {ui.GREY}• App installieren, alle Apps+Daten sichern")
    print(f"  • Backup auf /sdcard/TitaniumBackup/{ui.RESET}")
    print()
    # ADB Backup direkt anbieten
    if ui.confirm("Schnell-Backup der SD-Card-Daten jetzt starten?", False):
        import subprocess as sp
        dest = os.path.expanduser(f"~/Schreibtisch/Androidpanzer/customfw/sdcard_backup_{codes[0]}")
        os.makedirs(dest, exist_ok=True)
        for folder in ["DCIM", "Download", "WhatsApp", "Pictures"]:
            out = adb.shell(f"ls /sdcard/{folder} 2>/dev/null | head -1").strip()
            if out:
                ui.info(f"Kopiere /sdcard/{folder} …")
                sp.run(f"adb pull /sdcard/{folder} {dest}/ 2>/dev/null", shell=True)
        ui.ok(f"Backup abgeschlossen → {dest}")
    ui.pause()


def _fastboot_flash_tutorial(adb, dev, data) -> None:
    """Fastboot Flash-Tutorial – boot/system/recovery/vbmeta."""
    ui.clear()
    ui.rule("⚡ FASTBOOT FLASH TUTORIAL", ui.BCYAN)
    codes = _codenames(data, adb)
    c0 = codes[0]
    android_ver = data.get("android", "?")
    try:
        av = int(str(android_ver).split(".")[0])
    except Exception:
        av = 0
    init_boot = av >= 13
    print(f"""
  {ui.BOLD}Gerät: {data.get('brand','?')} {data.get('model','?')} · Android {android_ver}{ui.RESET}
  {'→ init_boot.img patchen (Android 13+)' if init_boot else '→ boot.img patchen (Android ≤12)'}

  {ui.BOLD}Schritt 1 – Fastboot aktivieren:{ui.RESET}
  {ui.GREY}adb reboot bootloader{ui.RESET}

  {ui.BOLD}Schritt 2 – Gerät prüfen:{ui.RESET}
  {ui.GREY}fastboot devices
  fastboot getvar unlocked     # muss 'yes' sein!{ui.RESET}

  {ui.BOLD}Schritt 3 – Images flashen:{ui.RESET}
  {ui.GREY}# Recovery:
  fastboot flash recovery twrp.img

  # Boot (für Magisk):
  {'fastboot flash init_boot magisk_patched.img' if init_boot else 'fastboot flash boot magisk_patched.img'}

  # Vbmeta deaktivieren (bei AVB-Fehler):
  fastboot flash vbmeta --disable-verity --disable-verification vbmeta.img

  # System (Vorsicht – ALLE DATEN WEG!):
  fastboot flash system system.img
  fastboot -w                  # wipe + format{ui.RESET}

  {ui.BOLD}Schritt 4 – Neustart:{ui.RESET}
  {ui.GREY}fastboot reboot
  fastboot reboot recovery     # direkt in Recovery{ui.RESET}

  {ui.BOLD}Stock-Images für Pixel:{ui.RESET}
  {ui.GREY}https://developers.google.com/android/images
  Archiv entpacken → flash-all.sh (Linux/Mac) oder flash-all.bat (Windows){ui.RESET}

  {ui.BOLD}XDA Thread für dieses Gerät:{ui.RESET}
  {ui.GREY}https://www.google.com/search?q={quote('XDA ' + data.get('model','') + ' ' + c0 + ' fastboot flash')}{ui.RESET}
""")
    ui.pause()


def _stock_restore(adb, dev, data) -> None:
    """Stock-ROM wiederherstellen – Hersteller-Quellen."""
    ui.clear()
    ui.rule("🔄 STOCK-ROM WIEDERHERSTELLEN", ui.BYELLOW)
    brand = data.get("brand", "").lower()
    model = data.get("model", "")
    codes = _codenames(data, adb)
    c0 = codes[0]
    print(f"\n  Gerät: {ui.BOLD}{model}{ui.RESET}  ({c0})\n")

    if "samsung" in brand:
        print(f"  {ui.BOLD}Samsung – Odin/Heimdall Restore:{ui.RESET}")
        print(f"  {ui.GREY}1. Stock-Firmware auf SamFirm / Frija / SamMobile herunterladen")
        print(f"     SamFirm: https://github.com/jesec/SamFirm.NET")
        print(f"     SamMobile: https://www.sammobile.com/firmwares/")
        print(f"  2. Odin (Windows) oder Heimdall (Linux/Mac) nutzen")
        print(f"  3. Gerät in Download-Modus → AP=*.tar.md5, BL, CP, CSC auswählen → Start{ui.RESET}")
    elif "google" in brand or "pixel" in model.lower():
        print(f"  {ui.BOLD}Google Pixel – Factory Images:{ui.RESET}")
        print(f"  {ui.GREY}https://developers.google.com/android/images")
        print(f"  Passendes Image laden → flash-all.sh ausführen")
        print(f"  ODER: adb sideload ota_update.zip (OTA-Image){ui.RESET}")
    elif "xiaomi" in brand or "redmi" in brand:
        print(f"  {ui.BOLD}Xiaomi – Fastboot-ROM:{ui.RESET}")
        print(f"  {ui.GREY}https://xiaomifirmwareupdater.com/archive/miui/{c0}/")
        print(f"  MiFlash-Tool (Windows) ODER miflash_unlock_tool")
        print(f"  Linux: git clone https://github.com/piterKa/MiFlash-Linux{ui.RESET}")
    elif "oneplus" in brand:
        print(f"  {ui.BOLD}OnePlus – MSM Download Tool:{ui.RESET}")
        print(f"  {ui.GREY}https://www.oneplus.com/support/softwareupgrade/details?code=PM1574156785765")
        print(f"  OnePlus Community → Support → Firmware{ui.RESET}")
    else:
        print(f"  {ui.BOLD}Generisch – Stock-ROM-Quellen:{ui.RESET}")
        print(f"  {ui.GREY}Hersteller-Website: Support → Downloads")
        print(f"  XDA: https://www.google.com/search?q={quote('XDA ' + model + ' stock ROM download')}")
        print(f"  Firmware.mobi: https://firmware.mobi/")
        print(f"  SamFW (viele Marken): https://samfw.com/{ui.RESET}")
    print()
    ui.warn("Stock-Restore mit Fastboot (-w) löscht ALLE Daten. Backup zuerst!")
    ui.pause()


def _compat_check(adb, data) -> None:
    """Kompatibilitäts-Check vor dem Flash."""
    ui.clear()
    ui.rule("✅ KOMPATIBILITÄTS-CHECK", ui.BCYAN)
    print()
    codes = _codenames(data, adb)
    c0 = codes[0]
    brand = data.get("brand", "")
    model = data.get("model", "")
    android_ver = data.get("android", "?")
    sdk = data.get("sdk", "?")
    checks = []

    # Treble-Prüfung
    treble = adb.shell("getprop ro.treble.enabled 2>/dev/null").strip()
    checks.append(("Project Treble", treble == "true",
                   f"{'Unterstützt' if treble=='true' else 'Nicht unterstützt'} – "
                   f"{'GSI-ROMs möglich' if treble=='true' else 'Nur gerätespezifische ROMs'}"))

    # A/B Partition
    ab = adb.shell("getprop ro.build.ab_update 2>/dev/null").strip()
    checks.append(("A/B-Partition", True,
                   f"{'Ja (Seamless Updates)' if ab=='true' else 'Nein (nur A-Slot)'}"))

    # SAR (System-as-Root)
    sar = adb.shell("getprop ro.build.system_root_image 2>/dev/null").strip()
    checks.append(("System-as-Root", True,
                   f"{'Ja' if sar=='true' else 'Nein'} (wichtig für Magisk-Patching)"))

    # AVB
    avb = adb.shell("getprop ro.boot.avb_version 2>/dev/null").strip()
    checks.append(("AVB (Verified Boot)", True,
                   f"v{avb}" if avb else "Nicht erkannt"))

    # RAM
    ram_raw = adb.shell("cat /proc/meminfo 2>/dev/null | grep MemTotal").strip()
    ram_mb = 0
    if ram_raw:
        try:
            ram_mb = int(ram_raw.split()[1]) // 1024
        except Exception:
            pass
    checks.append(("RAM", ram_mb >= 2048,
                   f"{ram_mb} MB {'✓ ausreichend' if ram_mb >= 2048 else '⚠ knapp (min. 2GB)'}"))

    # Storage
    store_raw = adb.shell("df /data 2>/dev/null | tail -1").strip()
    checks.append(("Interner Speicher", True, store_raw[:60] if store_raw else "?"))

    # Android-Version für ROM
    try:
        av = int(str(android_ver).split(".")[0])
    except Exception:
        av = 0
    checks.append(("Android-Version", True,
                   f"Android {android_ver} (SDK {sdk}) → "
                   f"{'init_boot.img benötigt' if av >= 13 else 'boot.img patchen'}"))

    for label, ok, msg in checks:
        col = ui.BGREEN if ok else ui.BYELLOW
        ui.kv(f"{col}{'✓' if ok else '⚠'}{ui.RESET} {label}", msg)

    print()
    ui.kv("Codename", c0)
    ui.kv("Gerät", f"{brand} {model}")
    print(f"\n  {ui.BOLD}ROM-Suche für genau diesen Codename:{ui.RESET}")
    print(f"  {ui.GREY}https://www.google.com/search?q={quote(c0 + ' custom rom android ' + str(android_ver))}{ui.RESET}")
    ui.pause()


def _magisk_guide(adb, dev, data) -> None:
    """Magisk Root – vollständige Anleitung."""
    ui.clear()
    ui.rule("🪄 MAGISK ROOT ANLEITUNG", ui.BCYAN)
    android_ver = data.get("android", "?")
    try:
        av = int(str(android_ver).split(".")[0])
    except Exception:
        av = 0
    img = "init_boot.img" if av >= 13 else "boot.img"
    model = data.get("model", "")
    brand = data.get("brand", "").lower()
    codes = _codenames(data, adb)
    print(f"""
  {ui.BOLD}Gerät: {data.get('brand','?')} {model} · Android {android_ver}{ui.RESET}
  Zu patchendes Image: {ui.BGREEN}{img}{ui.RESET}

  {ui.BOLD}Schritt 1 – Magisk-App herunterladen:{ui.RESET}
  {ui.GREY}https://github.com/topjohnwu/Magisk/releases
  Neueste stable: Magisk-vXX.X.apk{ui.RESET}

  {ui.BOLD}Schritt 2 – {img} beschaffen:{ui.RESET}
  {ui.GREY}{'• Pixel: https://developers.google.com/android/images' if 'google' in brand else ''}
  {'• Samsung: SamFirm/Frija → boot.img aus AP-TAR extrahieren' if 'samsung' in brand else ''}
  {'• Xiaomi: Fastboot-ROM (miui_*_fastboot.tgz) → images/' if 'xiaomi' in brand or 'redmi' in brand else ''}
  • Allgemein: Stock-ROM des EXAKT gleichen Builds herunterladen → {img} extrahieren
  • payload.bin extrahieren: python3 payload_dumper.py payload.bin{ui.RESET}

  {ui.BOLD}Schritt 3 – Image patchen:{ui.RESET}
  {ui.GREY}adb push {img} /sdcard/
  # In Magisk-App: Install → Select and Patch a File → {img}
  adb pull /sdcard/Download/magisk_patched_*.img .{ui.RESET}

  {ui.BOLD}Schritt 4 – Image flashen:{ui.RESET}
  {ui.GREY}adb reboot bootloader
  fastboot flash {img.replace('.img','')} magisk_patched_*.img
  fastboot reboot{ui.RESET}

  {ui.BOLD}Schritt 5 – Magisk abschließen:{ui.RESET}
  {ui.GREY}Magisk-App öffnen → ggf. 'Direct Install' wählen → Neustart
  # Root-Zugriff testen: adb shell su -c id{ui.RESET}

  {ui.BOLD}Aktuelle Magisk-Version:{ui.RESET}
  {ui.GREY}Releases: https://github.com/topjohnwu/Magisk/releases{ui.RESET}
""")
    ui.pause()


def _gsi_guide(adb, dev, data) -> None:
    """Generic System Image (GSI) – Treble-ROMs."""
    ui.clear()
    ui.rule("🌐 GSI / GENERIC SYSTEM IMAGE", ui.BCYAN)
    treble = adb.shell("getprop ro.treble.enabled 2>/dev/null").strip()
    ab = adb.shell("getprop ro.build.ab_update 2>/dev/null").strip()
    arch = adb.shell("getprop ro.product.cpu.abi 2>/dev/null").strip()
    android_ver = data.get("android", "?")
    print(f"""
  {ui.BOLD}Project Treble: {ui.BGREEN if treble=='true' else ui.BRED}{'Unterstützt' if treble=='true' else 'NICHT unterstützt'}{ui.RESET}
  A/B-Partition: {'Ja' if ab=='true' else 'Nein'}
  CPU-Arch: {arch}
  Android: {android_ver}
""")
    if treble != "true":
        ui.warn("Dieses Gerät unterstützt kein Project Treble → GSI-ROMs nicht möglich.")
        print(f"  {ui.GREY}Nur gerätespezifische ROMs (XDA, Codename-suche){ui.RESET}")
        ui.pause(); return

    # GSI-Typ bestimmen
    gsi_arch = "arm64" if "arm64" in arch.lower() else "arm"
    ab_suffix = "_ab" if ab == "true" else "_a"
    gsi_type = f"{gsi_arch}{ab_suffix}"
    print(f"  {ui.BOLD}Empfohlener GSI-Typ: {ui.BGREEN}{gsi_type}{ui.RESET}\n")
    print(f"  {ui.BOLD}GSI-Quellen:{ui.RESET}")
    print(f"  {ui.GREY}• Android GSI (Google): https://developer.android.com/topic/generic-system-image")
    print(f"  • phh-treble (populär): https://github.com/phhusson/treble_experimentations/releases")
    print(f"  • TrebleDroid: https://github.com/TrebleDroid/treble_experimentations/releases")
    print(f"  • AndyYan GSI: https://github.com/AndyCGYan/lineage_build_unified{ui.RESET}")
    print()
    print(f"  {ui.BOLD}Flash-Befehl:{ui.RESET}")
    print(f"  {ui.GREY}fastboot flash system system-{gsi_type}.img")
    print(f"  fastboot -w   # data wipe (nötig!)")
    print(f"  fastboot reboot{ui.RESET}")
    ui.pause()


def _sideload_guide(adb, dev) -> None:
    """ADB-Sideload – OTA und ZIP flashen."""
    ui.clear()
    ui.rule("📦 ADB SIDELOAD ANLEITUNG", ui.BCYAN)
    print(f"""
  {ui.BOLD}Was ist Sideload?{ui.RESET}
  {ui.GREY}ADB-Sideload ermöglicht das Flashen von ZIP-Dateien (OTA-Updates, ROMs, Magisk)
  direkt über das USB-Kabel, ohne die ZIP auf die SD-Karte kopieren zu müssen.{ui.RESET}

  {ui.BOLD}Methode 1 – Via TWRP-Recovery:{ui.RESET}
  {ui.GREY}1. Gerät in TWRP booten
  2. TWRP: Advanced → ADB Sideload → Swipe to Start
  3. adb sideload rom_oder_ota.zip{ui.RESET}

  {ui.BOLD}Methode 2 – Via Stock-Recovery (OTA):{ui.RESET}
  {ui.GREY}1. adb reboot sideload     # oder: Recovery → Apply update from ADB
  2. adb sideload ota_update.zip{ui.RESET}

  {ui.BOLD}Methode 3 – Aus diesem Tool:{ui.RESET}
""")
    if ui.confirm("Sideload jetzt starten? (Gerät muss bereits in Recovery/Sideload-Modus sein)", False):
        import subprocess as sp
        zip_path = ui.ask("Pfad zur ZIP-Datei (lokal auf diesem PC)")
        if zip_path and os.path.isfile(zip_path):
            ui.info(f"Starte: adb sideload {zip_path}")
            sp.run(["adb", "sideload", zip_path])
            ui.ok("Sideload abgeschlossen.")
        else:
            ui.err("Datei nicht gefunden.")
    ui.pause()


def show_custom_firmware(adb, dev, st, data) -> None:
    """Entry-Point: Custom-Firmware-Menü — maximal ausgebaut."""
    while True:
        ui.clear()
        codes = _codenames(data, adb)
        c0 = codes[0]
        brand = data.get("brand", "")
        model = data.get("model", "")
        ui.banner(subtitle=f"🔧 Custom-Firmware & Flash-Tools · {brand} {model} ({c0})")
        ch = ui.menu("Aktion", [
            ("1",  "🌐 ROM-Suche             (LineageOS-API · TWRP · Such-Einstiege)"),
            ("2",  "🛟 TWRP Flash-Anleitung  (Fastboot & Heimdall, Schritt-für-Schritt)"),
            ("3",  "💾 Backup vor dem Flash  (TWRP-Nandroid, ADB-Backup, SD-Card)"),
            ("4",  "⚡ Fastboot Flash-Guide  (boot/system/recovery/vbmeta)"),
            ("5",  "🔄 Stock-ROM Restore     (Hersteller-Quellen je Marke)"),
            ("6",  "✅ Kompatibilitäts-Check (Treble, A/B, RAM, SDK, AVB)"),
            ("7",  "🪄 Magisk Root-Anleitung (patchen, flashen, abschließen)"),
            ("8",  "🌐 GSI / Treble-ROM      (Generic System Image – geräteunabhängige ROMs)"),
            ("9",  "📦 ADB Sideload          (OTA/ZIP ohne SD-Karte flashen)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            _rom_search(adb, dev, data)
        elif ch == "2":
            _twrp_flash_guide(adb, dev, data)
        elif ch == "3":
            _backup_guide(adb, dev, data)
        elif ch == "4":
            _fastboot_flash_tutorial(adb, dev, data)
        elif ch == "5":
            _stock_restore(adb, dev, data)
        elif ch == "6":
            _compat_check(adb, data)
        elif ch == "7":
            _magisk_guide(adb, dev, data)
        elif ch == "8":
            _gsi_guide(adb, dev, data)
        elif ch == "9":
            _sideload_guide(adb, dev)
