"""Hersteller-spezifische Tools, Anleitungen und ADB-Aktionen für alle Android-Marken.

Xiaomi/Redmi/POCO, Google Pixel, OnePlus/OPPO/Realme, Motorola/Lenovo, Huawei/Honor.
Je Marke: Unlock-Anleitung, Debloat, Props, Diagnose, spezifische ADB-Befehle.
"""
from __future__ import annotations

import subprocess

from . import lang, rooting, ui
from .adb import ADB, Device

# ── Xiaomi/Redmi Bloatware-Liste ──────────────────────────────────────────────
_XIAOMI_BLOAT = [
    "com.miui.analytics", "com.miui.msa.global", "com.xiaomi.mipicks",
    "com.miui.systemAdSolution", "com.miui.bugreport", "com.miui.cleaner",
    "com.miui.powerkeeper", "com.miui.videoplayer", "com.miui.fm",
    "com.miui.hybrid", "com.miui.daemon", "com.miui.weather2",
    "com.miui.newmidrive", "com.miui.cloudservice", "com.miui.cloudbackup",
    "com.miui.backup", "com.miui.misdp", "cn.wps.xiaomi.abroad.lite",
    "com.miui.global.packageinstaller", "com.mi.global.shop",
]

# ── Samsung Bloatware-Liste ────────────────────────────────────────────────────
_SAMSUNG_BLOAT = [
    "com.samsung.android.app.tips", "com.samsung.android.bixby.agent",
    "com.samsung.android.bixby.service", "com.samsung.android.bixbyvision.framework",
    "com.samsung.android.game.gametools", "com.samsung.android.game.gamebooster",
    "com.samsung.android.weather", "com.samsung.android.spay",
    "com.samsung.android.livestickers", "com.samsung.android.service.livedrawing",
    "com.samsung.android.calendar", "com.samsung.android.video",
    "com.samsung.android.voiceserviceplatform", "com.samsung.android.wellbeing",
    "com.samsung.android.scloud", "com.sec.android.app.shealth",
    "com.amazon.mShop.android.shopping",
]

# ── OnePlus/OxygenOS Bloatware ────────────────────────────────────────────────
_ONEPLUS_BLOAT = [
    "com.oneplus.brickmode", "com.oneplus.weather", "com.oneplus.healthcheck",
    "com.oneplus.gamespace", "com.heliplus.plus", "com.oneplus.filemanager",
    "com.oneplus.gallery", "net.oneplus.odm", "com.oneplus.screenrecord",
    "com.oneplus.personalassistants",
]


def menu(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    """Hersteller-Tools Hauptmenü."""
    brand = data.get("brand", "").lower()
    model = data.get("model", "")
    while True:
        ui.clear()
        ui.banner(subtitle=f"🏷 Hersteller-Tools · {data.get('brand','?')} {model}")
        opts = [
            ("1", "📖 Unlock/Root Anleitung   (markenspezifische Schritte)"),
            ("2", "🧹 Bloatware entfernen      (Hersteller-Apps via ADB deaktivieren)"),
            ("3", "🔑 Hersteller-Props          (MIUI, OEM-Flags, Build-Infos)"),
            ("4", "📊 Geräte-Diagnose           (Brand-spezifische Checks)"),
            ("5", "⚡ ADB-Schnellbefehle        (Brand-spezifische Shell-Befehle)"),
            ("6", "🌐 Firmware-Suche            (Brand-spezifische Download-Quellen)"),
            ("7", "🔒 Sicherheits-Einstellungen (Hersteller-spezifische Sicherheitsoptionen)"),
        ]
        ch = ui.menu("Aktion", opts, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            _unlock_guide(adb, dev, st, data)
        elif ch == "2":
            _debloat_menu(adb, brand, model)
        elif ch == "3":
            _brand_props(adb, brand, data)
        elif ch == "4":
            _brand_diagnostics(adb, brand, data)
        elif ch == "5":
            _brand_adb_commands(adb, brand, data)
        elif ch == "6":
            _firmware_search(brand, data)
        elif ch == "7":
            _security_settings(adb, brand, data)


def _debloat_menu(adb: ADB, brand: str, model: str) -> None:
    """Bloatware per ADB deaktivieren — sicheres pm disable-user --user 0."""
    ui.clear()
    ui.rule("🧹 BLOATWARE ENTFERNEN", ui.BCYAN)
    print(f"\n  Gerät: {ui.BOLD}{model}{ui.RESET}")
    print(f"  {ui.GREY}Methode: pm disable-user --user 0 (kein echtes Löschen, deaktivierbar){ui.RESET}\n")

    if brand in ("xiaomi", "redmi", "poco"):
        bloat_list = _XIAOMI_BLOAT
        label = "Xiaomi/MIUI"
    elif brand in ("samsung",):
        bloat_list = _SAMSUNG_BLOAT
        label = "Samsung/OneUI"
    elif brand in ("oneplus", "oppo", "realme"):
        bloat_list = _ONEPLUS_BLOAT
        label = "OnePlus/OPPO"
    else:
        # Generisch: alle Drittanbieter-Apps anzeigen
        raw = adb.shell("pm list packages -3 2>/dev/null").strip()
        pkgs = [l.replace("package:", "").strip() for l in raw.splitlines() if l.strip()]
        label = "Drittanbieter"
        bloat_list = pkgs[:30]

    print(f"  {ui.BOLD}{label} – {len(bloat_list)} bekannte Bloatware-Pakete:{ui.RESET}\n")
    # Welche davon sind installiert?
    installed = []
    raw_all = adb.shell("pm list packages 2>/dev/null")
    for pkg in bloat_list:
        if pkg in raw_all:
            installed.append(pkg)

    if not installed:
        ui.ok("Keine bekannte Bloatware installiert gefunden.")
        ui.pause(); return

    for i, pkg in enumerate(installed, 1):
        print(f"  {ui.GREY}{i:2}. {pkg}{ui.RESET}")
    print()
    ui.warn("Falsche Pakete können System destabilisieren! Einzeln auswählen.")
    if ui.confirm(f"ALLE {len(installed)} Pakete deaktivieren?", False):
        ok, fail = [], []
        for pkg in installed:
            r = adb.shell(f"pm disable-user --user 0 {pkg} 2>&1").strip()
            if "disabled" in r.lower() or "success" in r.lower():
                ok.append(pkg)
            else:
                fail.append(pkg)
        ui.ok(f"{len(ok)} Pakete deaktiviert.")
        if fail:
            ui.warn(f"{len(fail)} fehlgeschlagen: {', '.join(fail[:5])}")
    else:
        # Einzeln auswählen
        idx_str = ui.ask("Nummern (kommasepariert, z.B. 1,3,5) oder 'q'")
        if idx_str and idx_str.lower() not in ("q", ""):
            idxs = [int(x.strip()) - 1 for x in idx_str.split(",")
                    if x.strip().isdigit() and 0 < int(x.strip()) <= len(installed)]
            for idx in idxs:
                pkg = installed[idx]
                r = adb.shell(f"pm disable-user --user 0 {pkg} 2>&1").strip()
                if "disabled" in r.lower():
                    ui.ok(f"Deaktiviert: {pkg}")
                else:
                    ui.warn(f"Fehler bei {pkg}: {r}")
    print()
    ui.info("Re-aktivieren: adb shell pm enable <paket.name>")
    ui.pause()


def _brand_props(adb: ADB, brand: str, data: dict) -> None:
    """Hersteller-spezifische Android-Properties."""
    ui.clear()
    ui.rule("🔑 HERSTELLER PROPERTIES", ui.BCYAN)
    print(f"\n  Marke: {ui.BOLD}{data.get('brand','?')}{ui.RESET}\n")
    base_props = [
        ("Marke",           "ro.product.brand"),
        ("Hersteller",      "ro.product.manufacturer"),
        ("Modell",          "ro.product.model"),
        ("Codename",        "ro.product.device"),
        ("Build",           "ro.build.id"),
        ("Fingerprint",     "ro.build.fingerprint"),
        ("Android",         "ro.build.version.release"),
        ("SDK",             "ro.build.version.sdk"),
        ("Baseband",        "gsm.version.baseband"),
        ("Bootloader",      "ro.bootloader"),
        ("CPU-ABI",         "ro.product.cpu.abi"),
        ("Build-Type",      "ro.build.type"),
        ("Tags",            "ro.build.tags"),
        ("Secure-Boot",     "ro.boot.verifiedbootstate"),
        ("OEM-Unlock",      "ro.oem_unlock_supported"),
        ("Treble",          "ro.treble.enabled"),
        ("A/B-Update",      "ro.build.ab_update"),
        ("System-as-Root",  "ro.build.system_root_image"),
    ]
    if brand in ("xiaomi", "redmi", "poco"):
        base_props += [
            ("MIUI-Version",    "ro.miui.ui.version.name"),
            ("MIUI-Code",       "ro.miui.ui.version.code"),
            ("MIUI-Region",     "ro.product.mod_device"),
            ("XiaoMi HyperOS",  "ro.mi.os.version.name"),
            ("Mi-Konto Pflicht","ro.miui.region"),
        ]
    elif brand in ("samsung",):
        base_props += [
            ("OneUI-Version",   "ro.build.version.oneui"),
            ("Samsung-ISP",     "ro.product.device"),
            ("CSC",             "ro.csc.sales_code"),
        ]
    elif brand in ("google",):
        base_props += [
            ("Pixel-Generation", "ro.product.device"),
            ("Pixel-SOC",        "ro.hardware"),
            ("Tensor-Rev",       "ro.hardware.chipname"),
        ]
    elif brand in ("huawei", "honor"):
        base_props += [
            ("EMUI-Version",    "ro.build.version.emui"),
            ("HiSilicon",       "ro.hardware"),
            ("HW-Build",        "ro.huawei.build.hwversion"),
        ]
    for label, prop in base_props:
        val = adb.shell(f"getprop {prop} 2>/dev/null").strip()
        if val:
            ui.kv(label, val[:120])
    ui.pause()


def _brand_diagnostics(adb: ADB, brand: str, data: dict) -> None:
    """Marken-spezifische Diagnose-Checks."""
    ui.clear()
    model = data.get("model", "")
    ui.rule(f"📊 DIAGNOSE · {data.get('brand','?')} {model}", ui.BCYAN)
    print()
    # Universell
    checks = [
        ("Akku-Status",    "dumpsys battery 2>/dev/null | grep -E 'level|status|health|voltage'"),
        ("Temperatur",     "dumpsys battery 2>/dev/null | grep temperature"),
        ("Uptime",         "uptime 2>/dev/null"),
        ("CPU-Frequenz",   "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null"),
        ("CPU-Kerne",      "nproc 2>/dev/null"),
        ("RAM gesamt",     "cat /proc/meminfo 2>/dev/null | grep MemTotal"),
        ("RAM frei",       "cat /proc/meminfo 2>/dev/null | grep MemAvailable"),
        ("Speicher /data", "df /data 2>/dev/null | tail -1"),
        ("Speicher /",     "df / 2>/dev/null | tail -1"),
        ("WLAN-SSID",      "dumpsys wifi 2>/dev/null | grep 'mWifiInfo' | head -1"),
        ("IP-Adresse",     "ip -4 addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}'"),
        ("Display-Info",   "wm size 2>/dev/null && wm density 2>/dev/null"),
        ("Laufende Proz.", "ps 2>/dev/null | wc -l"),
    ]
    if brand in ("samsung",):
        checks += [
            ("Knox-Version", "getprop ro.boot.warranty_bit 2>/dev/null"),
            ("Sboot-Flag",   "getprop ro.securestorage.knox 2>/dev/null"),
        ]
    elif brand in ("xiaomi", "redmi", "poco"):
        checks += [
            ("MIUI-Security", "getprop ro.miui.security.level 2>/dev/null"),
            ("Xiaomi-AD",     "settings get global miui_optimization 2>/dev/null"),
        ]
    for label, cmd in checks:
        val = adb.shell(cmd).strip()
        if val:
            ui.kv(label, val[:120])
    ui.pause()


def _brand_adb_commands(adb: ADB, brand: str, data: dict) -> None:
    """Marken-spezifische ADB-Schnellbefehle."""
    ui.clear()
    ui.rule("⚡ BRAND-SPEZIFISCHE ADB-BEFEHLE", ui.BCYAN)
    brand_name = data.get("brand", "?")
    print(f"\n  Marke: {ui.BOLD}{brand_name}{ui.RESET}\n")
    if brand in ("xiaomi", "redmi", "poco"):
        opts = [
            ("1", "MIUI-Optimierung deaktivieren (Speicher/Performance)"),
            ("2", "MIUI-Werbung deaktivieren"),
            ("3", "MIUI-Blocker (App-Install von unbekannten Quellen erlauben)"),
            ("4", "Deep Sleep Checker (Hintergrundprozesse)"),
            ("5", "USB-Debug dauerhaft (kein Popup bei Neustart)"),
        ]
        cmds = {
            "1": ("settings put global miui_optimization 0", "MIUI-Optimierung → 0 (aus)"),
            "2": ("settings put global MIUI_OPTIMIZATION 0; "
                  "pm disable-user --user 0 com.miui.systemAdSolution 2>/dev/null; "
                  "pm disable-user --user 0 com.miui.msa.global 2>/dev/null", "Ad-Systeme deaktiviert"),
            "3": ("settings put secure install_non_market_apps 1", "Unbekannte Quellen erlaubt"),
            "4": ("dumpsys deviceidle 2>/dev/null | grep -E 'enabled|deep|light'", None),
            "5": ("settings put global adb_always_ask 0 2>/dev/null", "ADB-Popup deaktiviert"),
        }
    elif brand in ("samsung",):
        opts = [
            ("1", "Samsung Pay Blocker (pa.android deaktivieren)"),
            ("2", "Bixby Wakeup deaktivieren"),
            ("3", "Game Launcher deaktivieren"),
            ("4", "S-Health / Samsung Health deaktivieren"),
            ("5", "Smart Capture / Edge Panels deaktivieren"),
        ]
        cmds = {
            "1": ("pm disable-user --user 0 com.samsung.android.spay 2>/dev/null", "Samsung Pay deaktiviert"),
            "2": ("pm disable-user --user 0 com.samsung.android.bixby.agent 2>/dev/null; "
                  "pm disable-user --user 0 com.samsung.android.bixby.service 2>/dev/null", "Bixby deaktiviert"),
            "3": ("pm disable-user --user 0 com.samsung.android.game.gametools 2>/dev/null", "Game Launcher deaktiviert"),
            "4": ("pm disable-user --user 0 com.sec.android.app.shealth 2>/dev/null", "Health deaktiviert"),
            "5": ("pm disable-user --user 0 com.samsung.android.service.livedrawing 2>/dev/null", "Edge deaktiviert"),
        }
    elif brand in ("google",):
        opts = [
            ("1", "Google-Telemetrie minimal setzen"),
            ("2", "Assistant deaktivieren"),
            ("3", "Pixel-Dienste anzeigen"),
            ("4", "OTA-Update-Check blockieren (für Tests)"),
            ("5", "Google Backup deaktivieren"),
        ]
        cmds = {
            "1": ("settings put global send_action_app_error 0 2>/dev/null; "
                  "settings put global dropbox:data_app_crash 0 2>/dev/null", "Telemetrie reduziert"),
            "2": ("pm disable-user --user 0 com.google.android.googlequicksearchbox 2>/dev/null", "Assistant deaktiviert"),
            "3": ("pm list packages | grep google | sort", None),
            "4": ("settings put global ota_disable_automatic_update 1 2>/dev/null", "OTA-Auto-Update deaktiviert"),
            "5": ("bmgr enable false 2>/dev/null", "Backup deaktiviert"),
        }
    else:
        opts = [
            ("1", "Alle Drittanbieter-Apps auflisten"),
            ("2", "Speicher-Analyse (/data)"),
            ("3", "Laufende Dienste anzeigen"),
            ("4", "Telemetrie-Pakete suchen"),
            ("5", "USB-Debug-Popup deaktivieren"),
        ]
        cmds = {
            "1": ("pm list packages -3 2>/dev/null", None),
            "2": ("df -h /data 2>/dev/null", None),
            "3": ("dumpsys activity services 2>/dev/null | grep 'ServiceRecord' | head -20", None),
            "4": ("pm list packages 2>/dev/null | grep -iE 'analytics|telemetry|tracking'", None),
            "5": ("settings put global adb_always_ask 0 2>/dev/null", "ADB-Popup deaktiviert"),
        }
    while True:
        ch = ui.menu("ADB-Befehl", opts, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch in cmds:
            cmd, success_msg = cmds[ch]
            out = adb.shell(cmd + " 2>&1").strip()
            if out:
                print(f"\n{ui.GREY}{out[:500]}{ui.RESET}\n")
            if success_msg:
                ui.ok(success_msg)
            ui.pause()


def _firmware_search(brand: str, data: dict) -> None:
    """Brand-spezifische Firmware-Download-Quellen."""
    from urllib.parse import quote as _q
    ui.clear()
    model = data.get("model", "")
    ui.rule(f"🌐 FIRMWARE-QUELLEN · {data.get('brand','?')} {model}", ui.BCYAN)
    print()
    codes_val = data.get("device", model.lower().replace(" ", "_"))
    if brand in ("samsung",):
        print(f"  {ui.BOLD}Samsung Firmware-Quellen:{ui.RESET}")
        print(f"  {ui.GREY}SamFirm/Frija (offiziell, kostenlos):")
        print(f"    https://github.com/jesec/SamFirm.NET")
        print(f"  SamMobile: https://www.sammobile.com/firmwares/")
        print(f"  SamFW: https://samfw.com/firmware/search?mQuery={_q(model)}")
        print(f"  FRIJA (Windows GUI): https://github.com/SlackingVeteran/frija{ui.RESET}")
    elif brand in ("xiaomi", "redmi", "poco"):
        print(f"  {ui.BOLD}Xiaomi/MIUI Firmware:{ui.RESET}")
        print(f"  {ui.GREY}Offiziell: https://xiaomifirmwareupdater.com/miui/{codes_val}/")
        print(f"  MIUI-Downloads: https://c.mi.com/global/miuidownload/index")
        print(f"  Fastboot-ROM: https://xiaomifirmwareupdater.com/archive/miui/{codes_val}/")
        print(f"  XiaomiROM: https://xiaomirom.com/series/{_q(model.lower())}/{ui.RESET}")
    elif brand in ("google",):
        print(f"  {ui.BOLD}Google Pixel Factory Images & OTA:{ui.RESET}")
        print(f"  {ui.GREY}Factory Images: https://developers.google.com/android/images")
        print(f"  OTA Updates: https://developers.google.com/android/ota")
        print(f"  Kernel Sources: https://android.googlesource.com/kernel/google-modules/{ui.RESET}")
    elif brand in ("oneplus", "oppo", "realme"):
        print(f"  {ui.BOLD}OnePlus/OxygenOS Firmware:{ui.RESET}")
        print(f"  {ui.GREY}OnePlus: https://www.oneplus.com/support/softwareupgrade")
        print(f"  OnePlus Archive: https://oxygenos.oneplus.net.cn/")
        print(f"  XDA: https://www.google.com/search?q={_q('XDA ' + model + ' firmware')}{ui.RESET}")
    elif brand in ("motorola", "moto", "lenovo"):
        print(f"  {ui.BOLD}Motorola/Moto Firmware:{ui.RESET}")
        print(f"  {ui.GREY}Offiziell: https://www.motorola.com/us/support")
        print(f"  Leidio Motorola: https://leidio.net/motorola-firmware/")
        print(f"  XDA: https://www.google.com/search?q={_q('XDA ' + model + ' stock ROM')}{ui.RESET}")
    elif brand in ("huawei", "honor"):
        print(f"  {ui.BOLD}Huawei/Honor Firmware:{ui.RESET}")
        print(f"  {ui.GREY}HiSuite (offiziell): https://consumer.huawei.com/de/support/hisuite/")
        print(f"  Huawei Firmwares: https://firmwarefile.com/tag/{_q(model.lower())}")
        print(f"  ⚠ Bootloader-Unlock seit 2018 abgestellt!{ui.RESET}")
    else:
        print(f"  {ui.BOLD}Allgemeine Firmware-Quellen:{ui.RESET}")
        print(f"  {ui.GREY}Firmware.mobi: https://firmware.mobi/")
        print(f"  SamFW (viele Marken): https://samfw.com/")
        print(f"  XDA: https://www.google.com/search?q={_q('XDA ' + model + ' firmware download')}{ui.RESET}")
    print()
    ui.pause()


def _security_settings(adb: ADB, brand: str, data: dict) -> None:
    """Brand-spezifische Sicherheits-Einstellungen."""
    ui.clear()
    model = data.get("model", "")
    ui.rule(f"🔒 SICHERHEITS-EINSTELLUNGEN · {data.get('brand','?')} {model}", ui.BCYAN)
    print()
    # Universelle Sicherheitsprops
    sec_props = [
        ("SELinux-Status",       "getenforce 2>/dev/null"),
        ("Verified Boot",        "getprop ro.boot.verifiedbootstate 2>/dev/null"),
        ("dm-verity",            "getprop ro.boot.veritymode 2>/dev/null"),
        ("Secure Boot",          "getprop ro.boot.flash.locked 2>/dev/null"),
        ("USB-Debug aktiv",      "getprop persist.service.adb.enable 2>/dev/null"),
        ("Root-Zugriff (MagiskD)","getprop ro.magisk.version 2>/dev/null"),
        ("Encryption",           "getprop ro.crypto.state 2>/dev/null"),
        ("FDE/FBE",              "getprop ro.crypto.type 2>/dev/null"),
        ("Keymaster",            "getprop ro.hardware.keystore 2>/dev/null"),
        ("StrongBox",            "getprop ro.hardware.strongbox 2>/dev/null"),
    ]
    if brand in ("samsung",):
        sec_props += [
            ("Knox-Counter",     "getprop ro.boot.warranty_bit 2>/dev/null"),
            ("Knox-Version",     "getprop ro.boot.knox 2>/dev/null"),
            ("RKP-Support",      "getprop ro.rkp.hal.version 2>/dev/null"),
        ]
    elif brand in ("xiaomi", "redmi", "poco"):
        sec_props += [
            ("MIUI Security",    "getprop ro.miui.security.level 2>/dev/null"),
            ("Anti-Rollback",    "getprop ro.build.version.security_patch 2>/dev/null"),
        ]
    for label, cmd in sec_props:
        val = adb.shell(cmd).strip()
        if val:
            col = ui.BRED if val in ("0", "Permissive", "orange") else ui.BGREEN
            ui.kv(label, f"{col}{val}{ui.RESET}")
    print()
    # SELinux-Toggle
    selinux = adb.shell("getenforce 2>/dev/null").strip()
    if selinux.lower() == "enforcing":
        ui.ok("SELinux: Enforcing (sicher)")
        if ui.confirm("SELinux auf Permissive setzen (für Root-Tools)?", False):
            adb.shell("setenforce 0 2>/dev/null")
            ui.warn("SELinux → Permissive gesetzt (temporär bis Neustart)")
    elif selinux.lower() == "permissive":
        ui.warn("SELinux: Permissive (reduzierte Sicherheit)")
        if ui.confirm("SELinux auf Enforcing zurücksetzen?", True):
            adb.shell("setenforce 1 2>/dev/null")
            ui.ok("SELinux → Enforcing")
    ui.pause()


# ──────────────────────────────────────────────────────────────────────────────

def _unlock_guide(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    """Marken-spezifische Unlock/Root Anleitung."""
    brand = data.get("brand", "").lower()
    if brand in ("xiaomi", "redmi", "poco"):
        _xiaomi(adb, dev, st, data)
    elif brand in ("google",):
        _pixel(adb, dev, st, data)
    elif brand in ("oneplus", "oppo", "realme"):
        _oneplus(adb, dev, st, data)
    elif brand in ("motorola", "moto", "lenovo"):
        _motorola(adb, dev, st, data)
    elif brand in ("huawei", "honor"):
        _huawei(adb, dev, st, data)
    else:
        _generic(adb, dev, st, data)


def _show_info(adb: ADB, dev: Device, st: dict, data: dict, title: str, lines: list[str]) -> None:
    ui.clear()
    ui.banner(subtitle=title)
    for ln in lines:
        if ln.startswith("!!"):
            ui.warn(ln[2:].strip())
        elif ln.startswith("✔"):
            ui.ok(ln)
        elif ln.startswith("ℹ"):
            ui.info(ln[1:].strip())
        else:
            print(f"  {ln}")
    print()
    if ui.confirm(lang.t("brand_continue_rooting"), False):
        rooting.show_and_offer(adb, dev, data, st)
        st["is_root"] = adb.check_root()
        data["root"] = st["is_root"]
    else:
        ui.pause()


def _xiaomi(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    sdk = data.get("sdk", "")
    _show_info(adb, dev, st, data,
        f"Xiaomi/MIUI – {model}",
        [
            "Schritt 1 – Mi-Konto verknüpfen:",
            "  • Einstellungen → Mein Konto → Bei Mi-Konto anmelden (falls noch nicht geschehen).",
            "  • Einstellungen → Entwickleroptionen → Mi Unlock Status → Konto verknüpfen.",
            "",
            "Schritt 2 – Entsperr-Wartezeit abwarten:",
            "!! Xiaomi erzwingt eine Wartezeit (72–168 Stunden / bis zu 7 Tage) zwischen",
            "!! Kontoverbindung und Unlock. Die genaue Dauer hängt vom Modell ab.",
            "",
            "Schritt 3 – Mi Unlock Tool (nur Windows):",
            "  • Download: https://www.miui.com/unlock/download.html",
            "  • Gerät in Fastboot bringen (Vol-Runter + Power), USB verbinden.",
            "  • Im Mi Unlock Tool: Mit Mi-Konto anmelden → Entsperren.",
            "  • WARNUNG: Entsperren LÖSCHT ALLE DATEN (Factory Reset).",
            "",
            "Schritt 4 – Root via Magisk:",
            "  • Passendes boot.img aus MIUI Fastboot-ROM (gleicher Build!) extrahieren.",
            "  • Magisk-App → boot.img patchen → gepatchtes Image per fastboot flash boot.",
            "",
            f"ℹ Modell: {model}  SDK: {sdk}",
            "ℹ Kein Windows? Mi Unlock unter Wine teilweise nutzbar; 3rd-Party-Tool 'xiaomi-adb-miui-debloater' hilft nicht beim Unlock.",
        ])


def _pixel(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    android = data.get("android", "")
    try:
        ver = int(str(android).split(".")[0])
    except (ValueError, AttributeError):
        ver = 0
    img_name = "init_boot.img" if ver >= 13 else "boot.img"
    _show_info(adb, dev, st, data,
        f"Google Pixel – {model}",
        [
            "Google Pixel unterstützt OEM-Unlock nativ. Kein Tool von Drittanbietern nötig.",
            "",
            "Schritt 1 – OEM-Unlock aktivieren:",
            "  • Einstellungen → Entwickleroptionen → OEM-Entsperrung aktivieren.",
            "  • Bei Pixel-6+-Modellen: Gerät muss mindestens 7 Tage alt sein.",
            "",
            "Schritt 2 – Bootloader entsperren:",
            "  • Gerät in Fastboot bringen: adb reboot bootloader",
            "  • fastboot flashing unlock",
            "!! WARNUNG: Entsperren LÖSCHT ALLE DATEN.",
            "",
            f"Schritt 3 – {img_name} patchen (Android {android}):",
            f"  • Passendes {img_name} von https://developers.google.com/android/images herunterladen.",
            f"  • Magisk-App → {img_name} patchen → gepatchtes Image zurück auf den PC kopieren.",
            f"  • fastboot flash {img_name.replace('.img','')} magisk_patched_*.img",
            "",
            "Schritt 4 – Neustart:",
            "  • fastboot reboot → Gerät startet, Magisk-App öffnen → 'Direct Install'.",
            "",
            f"ℹ Android {android} · Zu patchendes Image: {img_name}",
        ])


def _oneplus(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    brand = data.get("brand", "OnePlus")
    _show_info(adb, dev, st, data,
        f"{brand.title()} – {model}",
        [
            f"{brand.title()} / OPPO / Realme: Standard-Fastboot-Entsperrung.",
            "",
            "Schritt 1 – OEM-Unlock freischalten:",
            "  • Einstellungen → Über das Telefon → 7× auf Build-Nummer tippen.",
            "  • Einstellungen → Entwickleroptionen → OEM-Entsperrung aktivieren.",
            "  • Manche OPPO/Realme-Modelle brauchen ein Entwicklerkonto auf der Hersteller-Website.",
            "",
            "Schritt 2 – Bootloader entsperren:",
            "  • adb reboot bootloader",
            "  • fastboot flashing unlock   (ältere Geräte: fastboot oem unlock)",
            "!! WARNUNG: Entsperren LÖSCHT ALLE DATEN.",
            "",
            "Schritt 3 – boot.img patchen:",
            "  • OTA-Payload-Datei des passenden Builds herunterladen (XDA Developers).",
            "  • payload_dumper.py verwenden, um boot.img zu extrahieren.",
            "  • Magisk-App → boot.img patchen → fastboot flash boot magisk_patched.img",
            "",
            f"ℹ Modell: {model} · Hersteller: {brand.title()}",
            "ℹ OnePlus-Geräte ab OxygenOS 14 (2023+): Unlock manchmal nur mit Hersteller-Tool.",
        ])


def _motorola(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    _show_info(adb, dev, st, data,
        f"Motorola – {model}",
        [
            "Motorola verwendet ein Unlock-Code-System (kein freier Fastboot-Unlock).",
            "",
            "Schritt 1 – Bootloader-ID auslesen:",
            "  • Gerät in Fastboot bringen: adb reboot bootloader",
            "  • fastboot oem get_unlock_data",
            "  • Den angezeigten langen Code notieren.",
            "",
            "Schritt 2 – Unlock-Code bei Motorola anfordern:",
            "  • https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device-a",
            "  • Unlock-Daten einfügen → Motorola schickt einen Code per E-Mail.",
            "",
            "Schritt 3 – Entsperren:",
            "  • fastboot oem unlock <CODE-VON-MOTOROLA>",
            "!! WARNUNG: Entsperren LÖSCHT ALLE DATEN.",
            "",
            "Schritt 4 – Root:",
            "  • Passendes boot.img aus Stock-ROM herunterladen.",
            "  • Magisk-App → patchen → fastboot flash boot magisk_patched.img",
            "",
            f"ℹ Modell: {model}",
            "ℹ Nicht alle Motorola-Modelle unterstützen Bootloader-Unlock (Carrier-locked).",
        ])


def _huawei(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    _show_info(adb, dev, st, data,
        f"Huawei/Honor – {model}",
        [
            "!! Wichtig: Huawei hat den Bootloader-Unlock-Service seit Mai 2018 eingestellt.",
            "!! Für die meisten Geräte nach 2018 gibt es keinen offiziellen Entsperr-Weg mehr.",
            "",
            "Möglichkeiten (je nach Modell):",
            "  1. dc-unlocker / HCU Client (kostenpflichtig, inoffizielle Tools) – auf Gerät prüfen.",
            "  2. Für alte Geräte (vor 2018): Unlock-Code über Huawei-Portal (abgeschaltet).",
            "  3. EDL-Exploit (Kirin 9xx) – sehr modellspezifisch, hohes Brick-Risiko.",
            "  4. Manche Geräte: TWRP via ADB-Sideload (nur wenn bereits entsperrt).",
            "",
            "ℹ Ehrliche Einschätzung: Huawei/Honor-Geräte neuerer Baujahr sind de facto",
            "ℹ nicht rootbar ohne kostenpflichtige Drittanbieter-Tools oder Hardware-Eingriff.",
            "",
            f"ℹ Modell: {model}",
            "ℹ Forensik-Funktionen über ADB (ohne Root) sind weiterhin nutzbar.",
        ])


def _generic(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    brand = data.get("brand", "")
    model = data.get("model", "")
    _show_info(adb, dev, st, data,
        f"{brand} {model} – Allgemeiner Root-Weg",
        [
            "Generischer Android-Root-Weg (Fastboot + Magisk):",
            "",
            "Schritt 1 – OEM-Unlock freischalten:",
            "  • Einstellungen → Über das Telefon → 7× auf Build-Nummer tippen.",
            "  • Einstellungen → Entwickleroptionen → OEM-Entsperrung aktivieren.",
            "",
            "Schritt 2 – Bootloader entsperren:",
            "  • adb reboot bootloader",
            "  • fastboot flashing unlock   (ältere: fastboot oem unlock)",
            "!! WARNUNG: Entsperren LÖSCHT ALLE DATEN.",
            "",
            "Schritt 3 – boot.img patchen:",
            "  • Stock-ROM des exakt passenden Builds herunterladen (XDA / Hersteller).",
            "  • boot.img / init_boot.img extrahieren.",
            "  • Magisk-App → boot.img patchen → gepatchtes Image zurück auf PC.",
            "  • fastboot flash boot magisk_patched_*.img",
            "",
            "Schritt 4 – Neustart & Magisk abschließen:",
            "  • fastboot reboot → Magisk-App öffnen → 'Direct Install' (falls nötig).",
            "",
            f"ℹ Marke: {brand}  Modell: {model}",
            "ℹ Für modellspezifische Anleitungen: XDA Developers Forum durchsuchen.",
        ])
