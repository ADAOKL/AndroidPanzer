"""Root-Status-Analyse & Rooting-Assistent.

Prüft, ob das Gerät gerootet ist. Falls nicht: sammelt ALLE für genau dieses
Modell nötigen Fakten (Bootloader-Lock, A/B-Slot, ABI, Boot-Image-Quelle),
schätzt den Aufwand & das Risiko ein, listet die benötigten Dateien/Tools und
FRAGT dann, ob das Tool den Magisk-Standardweg durchführen soll.

Bewusst kein blindes Auto-Flashen: Root ist modellspezifisch und kann bei
falschem Boot-Image zum Bootloop führen. Das Tool assistiert Schritt für
Schritt und führt nur nach ausdrücklicher Bestätigung fastboot-Befehle aus.
"""
from __future__ import annotations

import os
import time

from . import rootprep, ui
from .adb import ADB, Device
from .util import LOG, outdir, shq


def analyze(adb: ADB, dev: Device, d: dict) -> dict:
    """Liefert eine Root-Einschätzung als dict."""
    g = adb.getprop
    info: dict = {}
    info["rooted"] = bool(d.get("root"))
    info["magisk"] = d.get("magisk", "")
    info["su"] = d.get("su_bin", "")

    # Bootloader-Lock
    locked = (g("ro.boot.flash.locked") or "").strip()
    vbstate = (g("ro.boot.verifiedbootstate") or "").strip()
    oem_allowed = (g("ro.oem_unlock_supported") or g("sys.oem_unlock_allowed") or "").strip()
    info["locked"] = locked
    info["vbstate"] = vbstate
    info["oem_unlock_allowed"] = oem_allowed
    if locked in ("0", "false") or vbstate.lower() == "orange":
        info["bootloader"] = "unlocked"
    elif locked in ("1", "true") or vbstate.lower() in ("green", "yellow"):
        info["bootloader"] = "locked"
    else:
        info["bootloader"] = "unknown"

    # A/B
    info["slot"] = (g("ro.boot.slot_suffix") or "").strip()
    info["ab"] = bool(info["slot"])

    # Modell-Fakten
    info["brand"] = d.get("brand", "")
    info["model"] = d.get("model", "")
    info["device"] = d.get("device", "")
    info["android"] = d.get("android", "")
    info["abi"] = d.get("abi", "")
    info["build"] = d.get("build", "")
    info["fingerprint"] = d.get("fingerprint", "")
    info["dynamic_partitions"] = (g("ro.boot.dynamic_partitions") or "").strip()

    # Hersteller-spezifische Methode
    info["method"] = _method_for(info["brand"].lower(), d)
    info["effort"], info["risk"] = _effort(info)
    return info


def _method_for(brand: str, d: dict) -> dict:
    """Grobe Hersteller-Heuristik für den Entsperr-/Root-Weg."""
    m = {
        "unlock_cmd": "fastboot flashing unlock   (älter: fastboot oem unlock)",
        "notes": "",
        "patch": "boot.img mit Magisk-App patchen, dann per Fastboot flashen.",
    }
    if brand in ("google", "pixel"):
        m["notes"] = "Pixel: OEM-Unlock in Entwickleroptionen aktivieren, init_boot.img (Android 13+) statt boot.img patchen."
        m["patch"] = "init_boot.img (A13+) bzw. boot.img mit Magisk patchen → fastboot flash init_boot."
    elif brand in ("xiaomi", "redmi", "poco"):
        m["unlock_cmd"] = "Mi Unlock Tool (Windows) – 7 Tage Wartezeit möglich"
        m["notes"] = "Xiaomi: Konto verknüpfen, 168h-Sperre üblich. Danach boot.img aus passender Fastboot-ROM patchen."
    elif brand in ("samsung",):
        m["unlock_cmd"] = "Download-Modus + OEM-Unlock; Flashen via Odin/Heimdall (KEIN fastboot!)"
        m["notes"] = "Samsung nutzt Odin/Heimdall, nicht fastboot. Magisk patcht AP-Tar (recovery/vbmeta). Knox wird permanent getrippt (0x1)."
        m["patch"] = "AP-Datei (.tar.md5) in Magisk patchen → via Odin/Heimdall flashen."
    elif brand in ("oneplus", "oppo", "realme"):
        m["notes"] = "OnePlus/Oppo/Realme: fastboot flashing unlock; boot.img aus passendem OTA-Payload extrahieren."
    elif brand in ("motorola", "moto", "lenovo"):
        m["unlock_cmd"] = "Motorola-Unlock-Code von der Hersteller-Seite anfordern → fastboot oem unlock <code>"
    else:
        m["notes"] = "Generisch: Bootloader entsperren, passendes boot.img patchen, flashen. Modellspezifisch recherchieren."
    return m


def _effort(info: dict) -> tuple[str, str]:
    if info["rooted"]:
        return "—", "—"
    if info["bootloader"] == "unlocked":
        return ("Mittel (~15–30 Min): boot.img patchen + flashen",
                "Mittel: Bootloop-Risiko bei falschem Image, OTA bricht.")
    return ("Hoch (~30–90 Min + evtl. Wartezeit): Bootloader entsperren → Daten-Wipe → patchen → flashen",
            "Hoch: Entsperren LÖSCHT ALLE DATEN. Garantie/Knox/SafetyNet-Folgen, Bootloop möglich.")


# --- UI-Flow --------------------------------------------------------------
def show_and_offer(adb: ADB, dev: Device, d: dict, st: dict | None = None) -> None:
    st = st if st is not None else {}
    info = analyze(adb, dev, d)
    ui.clear()
    ui.banner(subtitle="Root-Status & Rooting-Assistent")
    ui.rule("Root-Status", ui.YELLOW)

    if info["rooted"]:
        mg = f"Magisk {info['magisk']}" if info["magisk"] else "su vorhanden"
        ui.ok(f"Gerät ist BEREITS GEROOTET  ({mg})")
        ui.kv("su-Binary", info["su"] or "—")
        ui.info("Alle [ROOT]-Funktionen im Tool sind freigeschaltet.")
        if ui.confirm("Tiefen-Diagnose (Bootloader/Knox/dm-verity/Magisk) erstellen & loggen?", False):
            root_diagnostics(adb, dev, d)
        ui.pause()
        return

    ui.warn("Gerät ist NICHT gerootet.")
    print()
    ui.rule("Für dieses Modell gesammelte Fakten", ui.CYAN)
    ui.kv("Modell", f"{info['brand']} {info['model']} ({info['device']})")
    ui.kv("Android / Build", f"{info['android']}  •  {info['build']}")
    ui.kv("Architektur (ABI)", info["abi"])
    ui.kv("Bootloader", {
        "unlocked": f"{ui.BYELLOW}entsperrt ✓ (bereit){ui.RESET}",
        "locked": f"{ui.BRED}gesperrt ✗ (muss entsperrt werden){ui.RESET}",
        "unknown": "unbekannt",
    }[info["bootloader"]])
    ui.kv("OEM-Unlock erlaubt", info["oem_unlock_allowed"] or "unbekannt (in Entwickleroptionen prüfen)")
    ui.kv("Partitionsschema", ("A/B (slot " + info["slot"] + ")") if info["ab"] else "A-only")
    ui.kv("Dynamic Partitions", info["dynamic_partitions"] or "—")

    print()
    ui.rule("Aufwand & Risiko", ui.CYAN)
    ui.kv("Aufwand", info["effort"], key_w=10, color=ui.BYELLOW)
    ui.kv("Risiko", info["risk"], key_w=10, color=ui.BRED)

    print()
    ui.rule("Benötigte Komponenten (Checkliste)", ui.CYAN)
    meth = info["method"]
    needs = [
        ("PC mit USB-Kabel & USB-Debugging", "✓ vorhanden (du bist verbunden)"),
        ("Platform-Tools (adb/fastboot)", _have_fastboot()),
        ("Bootloader entsperrt", "✓" if info["bootloader"] == "unlocked" else f"✗ – {meth['unlock_cmd']}"),
        ("Magisk-App (APK)", "→ github.com/topjohnwu/Magisk/releases (auf das Gerät laden)"),
        (f"Passendes boot.img für {info['build'] or 'diesen Build'}",
         "→ aus Hersteller-/OTA-Firmware extrahieren (genau dieser Build!)"),
        ("Methode", meth["patch"]),
    ]
    for k, v in needs:
        ui.kv(k, v, key_w=34)
    if meth["notes"]:
        print()
        ui.info(meth["notes"])

    # Im Hintergrund vorbereitete Download-Links anzeigen (falls vorhanden)
    plan = st.get("rootprep")
    if plan:
        print()
        rootprep.render_plan(plan)

    print()
    ui.rule("Soll das Tool jetzt assistieren?", ui.YELLOW)
    ui.danger("WARNUNG: Bootloader-Entsperren LÖSCHT ALLE DATEN. Flashen kann zum Bootloop führen.")
    print(f"  {ui.BOLD}{ui.BGREEN}A{ui.RESET}  🚀 AUTO-ROOT – vorbereitete Dateien laden → Magisk → patchen → flashen "
          f"{ui.GREY}(geführt, mit Konto-/FRP-Hinweisen){ui.RESET}")
    print(f"  {ui.BOLD}1{ui.RESET}  Geführter Magisk-Ablauf (Schritt für Schritt, mit Bestätigung je Schritt)")
    print(f"  {ui.BOLD}2{ui.RESET}  Nur Reboot in den Bootloader/Fastboot (manuell weitermachen)")
    print(f"  {ui.BOLD}3{ui.RESET}  Checkliste als Datei speichern und später entscheiden")
    print(f"  {ui.BOLD}4{ui.RESET}  🩺 Tiefen-Diagnose (Bootloader/Knox/dm-verity/Magisk) als Log erzeugen")
    print(f"  {ui.BOLD}5{ui.RESET}  🌐 Custom-Firmware/ROMs aus dem Internet anzeigen (LineageOS/TWRP/…)")
    print(f"  {ui.BOLD}0{ui.RESET}  Abbrechen / nichts tun")
    choice = ui.ask("Auswahl", "0").lower()

    if choice == "5":
        from . import customfw
        customfw.show_custom_firmware(adb, dev, st, d)
    elif choice == "a":
        brand = (info.get("brand") or "").lower()
        if "samsung" in brand:
            ui.warn("Samsung flasht über Odin/Heimdall (Download-Modus) – NICHT Fastboot.")
            ui.info("Korrekter vollautomatischer Weg: das Samsung-Modul (Firmware via samloader → "
                    "AP-Tar on-device patchen → Heimdall).")
            if ui.confirm("Jetzt ins Samsung-Root-Modul wechseln?", True):
                from . import samsung
                samsung.menu(adb, dev, st, d)
            else:
                rootprep.run_auto(adb, dev, info, st)
        elif d.get("is_mtk"):
            ui.info("MediaTek-Chipsatz erkannt – das MTK-Modul (mtkclient/BROM) ist meist der "
                    "schnellste Weg (oft ohne Daten-Wipe).")
            if ui.confirm("Jetzt ins MediaTek-Root-Modul wechseln?", True):
                from . import mediatek
                mediatek.menu(adb, dev, st, d)
            else:
                rootprep.run_auto(adb, dev, info, st)
        else:
            rootprep.run_auto(adb, dev, info, st)
    elif choice == "1":
        _guided_flow(adb, dev, info)
    elif choice == "4":
        root_diagnostics(adb, dev, d)
    elif choice == "2":
        if ui.confirm("Gerät jetzt in den Fastboot-Modus neu starten?", False):
            ui.info(adb.shell("reboot bootloader") or "Reboot ausgelöst.")
        ui.pause()
    elif choice == "3":
        _save_checklist(info, needs, meth)
        ui.pause()
    else:
        ui.info("Kein Eingriff vorgenommen.")
        ui.pause()


# --- Tiefen-Diagnose (Bootloader / Knox / dm-verity / Magisk) -------------- #
# Erzwungene Matrix sicherheitsrelevanter Properties (inspiriert von dedizierten
# Samsung-Root-Diagnose-Skripten): wird komplett & zeitgestempelt protokolliert.
FORCED_PROPS = [
    "ro.product.manufacturer", "ro.product.brand", "ro.product.model",
    "ro.product.device", "ro.product.cpu.abi",
    "ro.build.version.release", "ro.build.version.sdk", "ro.build.version.security_patch",
    "ro.build.fingerprint", "ro.build.display.id",
    "ro.boot.bootloader", "ro.bootloader",
    "ro.boot.flash.locked", "ro.boot.verifiedbootstate", "ro.boot.veritymode",
    "ro.boot.warranty_bit", "ro.boot.warrantbit", "ro.warranty_bit",
    "ro.boot.avb_version", "ro.boot.vbmeta.avb_version",
    "ro.boot.slot_suffix", "ro.boot.dynamic_partitions",
    "sys.oem_unlock_allowed", "ro.oem_unlock_supported",
    "ro.crypto.state", "ro.crypto.type",
    "ro.boot.secureboot", "ro.secure", "ro.debuggable", "ro.adb.secure",
    "ro.boot.selinux", "ro.build.selinux",
]

# OEM-/Cloud-Sperrdienste (zweite Sperrebene über die Google-FRP hinaus).
# Reine Property-Indikatoren – read-only, dienen der Risiko-Einschätzung.
OEM_LOCK_PROPS = {
    "Samsung Knox Guard / RLC": ["ro.bla.kg.state", "sys.remotelock.state",
                                 "persist.sys.kg_state", "ro.knox.enhanced.secure_boot"],
    "Xiaomi Mi Cloud": ["ro.miui.cloud.id", "persist.sys.cloud.lock", "ro.miui.has_cust_partition"],
    "Huawei Cloud": ["ro.config.hw_cloudphone", "ro.huawei.cust.cloud"],
    "Oppo/Realme/Vivo Cloud": ["ro.oppo.cloud.lock", "persist.sys.vivo.lock"],
    "Sony MyXperia": ["ro.semc.product.name", "persist.sony.myxperia"],
}

# Konto-Indikatoren aus dumpsys account (FRP/Cloud nach Reset scharf?).
ACCOUNT_INDICATORS = [
    ("Google-Konto → FRP nach Reset SCHARF", "com.google"),
    ("Samsung-Konto (Reactivation Lock möglich)", "com.osp.app.signin"),
    ("Xiaomi Mi-Konto (Mi Cloud Lock möglich)", "com.xiaomi"),
]

# EFS/Funk-Kalibrierungs-Partitionen – beim Low-Level-Löschen TABU (IMEI/Netz-Tod).
EFS_PARTITION_HINT = ("efs", "modemst1", "modemst2", "nvram", "nvdata",
                      "fsg", "fsc", "backup", "persist", "protect_f", "protect_s")


def root_diagnostics(adb: ADB, dev: Device, d: dict) -> str:
    """Erzeugt eine lückenlose, zeitgestempelte Root-/Bootloader-Tiefen-Diagnose.

    Vereint die Module dedizierter Diagnose-Skripte – ausschließlich READ-ONLY:
      1) erzwungene Eigenschafts-Matrix (ro.boot.* u.a.)
      2) Bootloader-Lock-/Knox-/AVB-Analyse
      3) Magisk-Architektur (App-UI vs. echtes su-Binary)
      4) dm-verity / Schreibschutz der System-Partitionen (mount RO/RW)
      5) Persist/Metadata-Integrität (kryptografische FRP-Gegenprüfung)
      6) OEM-/Cloud-Sperrdienste (Knox Guard, Mi Cloud, Konten → zweite Sperrebene)
      7) Flash-Geometrie (Sektorgröße) + EFS/IMEI-Partitions-Schutz
    Abschließend eine konsolidierte Risiko-Matrix. Schreibt einen Report nach
    diagnostics/ und protokolliert Kernbefunde. Führt KEINE Löschungen/Bypässe aus.
    """
    ui.clear()
    ui.banner(subtitle="🩺 Root-/Bootloader-Tiefen-Diagnose")
    LOG.info("Root-Tiefen-Diagnose gestartet")
    lines: list[str] = []

    def emit(s: str = "") -> None:
        lines.append(s)

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    emit("=" * 72)
    emit(f"ANDROID PANZER · Root-/Bootloader-Tiefen-Diagnose · {stamp}")
    emit(f"Gerät: {d.get('brand','?')} {d.get('model','?')} ({d.get('device','?')})  "
         f"Serial: {dev.serial or '—'}")
    emit("=" * 72)

    # --- MODUL 1: Eigenschafts-Matrix --------------------------------------
    ui.rule("Modul 1 · Eigenschafts-Matrix", ui.CYAN)
    emit("\n--- [MODUL 1: EIGENSCHAFTS-MATRIX] ---")
    props = {}
    for p in FORCED_PROPS:
        v = (adb.getprop(p) or "").strip()
        props[p] = v
        if v:
            emit(f"  PROP  {p:<34} = '{v}'")
            ui.kv(p, v, key_w=32)
    # nicht gesetzte Properties kompakt vermerken
    empty = [p for p in FORCED_PROPS if not props[p]]
    if empty:
        emit(f"  (nicht gesetzt: {', '.join(empty)})")

    # --- MODUL 2: Bootloader / Knox / AVB ----------------------------------
    ui.rule("Modul 2 · Bootloader / Knox / AVB", ui.CYAN)
    emit("\n--- [MODUL 2: BOOTLOADER-ANALYSE] ---")
    vb = props.get("ro.boot.verifiedbootstate", "")
    locked = props.get("ro.boot.flash.locked", "")
    knox = (props.get("ro.boot.warranty_bit") or props.get("ro.boot.warrantbit")
            or props.get("ro.warranty_bit") or "")
    avb = props.get("ro.boot.avb_version") or props.get("ro.boot.vbmeta.avb_version") or ""
    oem = props.get("sys.oem_unlock_allowed") or props.get("ro.oem_unlock_supported") or ""
    emit(f"  verifiedbootstate = '{vb}'  flash.locked = '{locked}'  warranty/knox = '{knox}'")
    emit(f"  avb_version = '{avb}'  oem_unlock_allowed = '{oem}'")
    is_locked = locked in ("1", "true") or vb.lower() in ("green", "yellow")
    is_unlocked = locked in ("0", "false") or vb.lower() == "orange"
    if is_locked and not is_unlocked:
        ui.crit("Bootloader GESPERRT (locked) – per Software NICHT umgehbar.")
        emit("  STATUS: GESPERRT (locked). Entsperren ist nur manuell im Download-/Fastboot-Modus")
        emit("          möglich und LÖSCHT ALLE DATEN (Factory Reset).")
    elif is_unlocked:
        ui.ok("Bootloader entsperrt/modifiziert (orange) – Flashen grundsätzlich möglich.")
        emit(f"  STATUS: ENTSPERRT/MODIFIZIERT (verifiedbootstate={vb}).")
    else:
        ui.warn("Bootloader-Status unklar (Properties leer/maskiert).")
        emit("  STATUS: UNBEKANNT.")
    if knox in ("1", "0x1", "true"):
        ui.crit("Knox Warranty Bit = 1 → Knox dauerhaft getrippt (Samsung Pay/Secure Folder verloren).")
        emit("  KNOX: Warranty Bit getrippt (0x1) – irreversibel.")

    # --- MODUL 3: Magisk-Architektur ---------------------------------------
    ui.rule("Modul 3 · Magisk-Architektur (App vs. su)", ui.CYAN)
    emit("\n--- [MODUL 3: MAGISK-ARCHITEKTUR] ---")
    pkgs = adb.shell("pm list packages")
    magisk_app = ""
    for cand in ("com.topjohnwu.magisk", "io.github.huskydg.magisk", "io.github.vvb2060.magisk"):
        if f"package:{cand}" in pkgs:
            magisk_app = cand
            break
    if magisk_app:
        ver = adb.shell(f"dumpsys package {shq(magisk_app)} | grep -m1 versionName").strip()
        ui.ok(f"Magisk-App (UI) installiert: {magisk_app}  {ver}")
        emit(f"  Magisk-App installiert: {magisk_app}  {ver}")
    else:
        ui.warn("Keine Magisk-App (UI) installiert.")
        emit("  Magisk-App (UI): NICHT installiert. (Die reine APK gewährt KEINE Root-Rechte.)")
    which_su = adb.shell("which su 2>/dev/null").strip()
    id_root = adb.shell("su -c id 2>/dev/null").strip()
    if "uid=0" in id_root or (which_su and "not found" not in which_su and which_su):
        ui.ok(f"Echtes su-Binary aktiv: {which_su or '(Pfad n/a)'}  → {id_root or 'uid=0'}")
        emit(f"  su-Binary: VORHANDEN ({which_su or 'n/a'})  id: {id_root or 'uid=0'}")
    else:
        ui.crit("KEIN funktionierendes su-Binary – System läuft im Standard-User-Modus.")
        emit("  su-Binary: NICHT vorhanden. Root muss erst eingerichtet werden")
        emit("            (boot/recovery/AP per Magisk patchen → passend flashen).")

    # --- MODUL 4: dm-verity / Schreibschutz --------------------------------
    ui.rule("Modul 4 · dm-verity / Partitions-Schreibschutz", ui.CYAN)
    emit("\n--- [MODUL 4: SCHREIBSCHUTZ / DM-VERITY] ---")
    veritymode = props.get("ro.boot.veritymode", "")
    emit(f"  ro.boot.veritymode = '{veritymode}'   avb_version = '{avb}'")
    if veritymode and veritymode.lower() != "disabled":
        emit("  dm-verity ist AKTIV → System-Partition manipulationsgeschützt.")
    mounts = adb.shell("cat /proc/mounts 2>/dev/null") or adb.shell("mount")
    ro_parts, rw_parts = [], []
    for ln in mounts.splitlines():
        if any(f" /{x}" in f" {ln}" for x in ("system", "vendor", "product", "system_ext")):
            opts = ln.split()
            is_ro = " ro," in f" {ln}," or (len(opts) >= 4 and opts[3].startswith("ro"))
            (ro_parts if is_ro else rw_parts).append(ln)
            tag = "ro" if is_ro else "rw"
            emit(f"  MOUNT [{tag}] {ln[:110]}")
    if ro_parts and not rw_parts:
        ui.warn(f"System-Partitionen strikt READ-ONLY ({len(ro_parts)}) – kein direktes Schreiben.")
    elif rw_parts:
        ui.ok(f"{len(rw_parts)} System-Partition(en) beschreibbar (rw).")
    else:
        emit("  (keine system/vendor/product-Mounts gefunden – evtl. eingeschränkter Shell-Zugriff)")

    # --- MODUL 5: Persist / Metadata-Integrität ----------------------------
    ui.rule("Modul 5 · Persist / Metadata-Integrität (FRP-Gegenprüfung)", ui.CYAN)
    emit("\n--- [MODUL 5: PERSIST/METADATA-INTEGRITÄT] ---")
    persist = (adb.shell("cat /proc/mounts 2>/dev/null | grep -Ei 'persist|metadata'")
               or adb.shell("mount 2>/dev/null | grep -Ei 'persist|metadata'"))
    if persist.strip():
        for ln in persist.splitlines():
            emit(f"  AKTIV  {ln[:110]}")
        ui.crit("Persist/Metadata-Sicherungsblock aktiv – FRP-/Aktivierungs-Flags werden hier "
                "kryptografisch gegengeprüft.")
        emit("  ↳ Das System gleicht FRP-/Auth-Flags mit /persist bzw. /metadata ab.")
        emit("    Ein reines Löschen der frp-Partition OHNE /persist-Beachtung kann das Gerät hart sperren.")
    else:
        ui.ok("Keine separate Persist/Metadata-Validierung auf OS-Ebene sichtbar.")
        emit("  Keine persist/metadata-Mounts sichtbar (oder Shell-Zugriff eingeschränkt).")
    # Read-only Inventar: wo liegt die FRP-/Config-Partition physisch?
    frp = adb.shell("ls -l /dev/block/by-name/ 2>/dev/null | grep -iE 'frp|config|persistent'")
    if frp.strip():
        emit("  FRP-/Config-Partition (read-only Inventar – KEIN Eingriff durch das Tool):")
        for ln in frp.splitlines():
            emit(f"    {ln[:110]}")
        ui.info("FRP-/Config-Partition lokalisiert (nur Inventar – das Tool löscht/ändert nichts).")

    # --- MODUL 6: OEM-/Cloud-Sperrdienste ----------------------------------
    ui.rule("Modul 6 · OEM-/Cloud-Sperrdienste (zweite Sperrebene)", ui.CYAN)
    emit("\n--- [MODUL 6: OEM-/CLOUD-SPERREN] ---")
    cloud_found = False
    for label, keys in OEM_LOCK_PROPS.items():
        for k in keys:
            v = (adb.getprop(k) or "").strip()
            if v:
                cloud_found = True
                ui.crit(f"{label}: {k}='{v}' – zweite Sperrebene möglich!")
                emit(f"  {label}: {k} = '{v}'")
                break
    accts = adb.shell("dumpsys account 2>/dev/null")
    for label, needle in ACCOUNT_INDICATORS:
        if needle in accts:
            cloud_found = True
            ui.warn(label)
            emit(f"  KONTO: {label}  (Indikator: {needle})")
    if not cloud_found:
        ui.ok("Keine OEM-/Cloud-Sperr-Indikatoren gefunden.")
        emit("  Keine OEM-/Cloud-Sperr-Indikatoren gefunden (Properties/Konten leer oder maskiert).")
    else:
        emit("  ↳ Selbst nach Entfernen der Google-FRP kann ein OEM-Cloud-Dienst das Gerät erneut sperren,")
        emit("    sobald es online geht. Vor jedem Eingriff klären, ob das Konto rechtmäßig abgemeldet wurde.")

    # --- MODUL 7: Flash-Geometrie & EFS-Schutz -----------------------------
    ui.rule("Modul 7 · Flash-Geometrie & EFS/IMEI-Schutz", ui.CYAN)
    emit("\n--- [MODUL 7: FLASH-GEOMETRIE] ---")
    block_size = ""
    for cmd in ("cat /sys/block/mmcblk0/queue/logical_block_size 2>/dev/null",
                "cat /sys/block/sda/queue/logical_block_size 2>/dev/null",
                "cat /sys/block/sdc/queue/logical_block_size 2>/dev/null"):
        v = adb.shell(cmd).strip()
        if v.isdigit():
            block_size = v
            dev_name = cmd.split("/")[3]
            ui.kv("Logische Sektorgröße", f"{v} Bytes  ({dev_name})")
            emit(f"  {dev_name}: logische Sektorgröße = {v} Bytes")
            break
    if not block_size:
        ui.warn("Sektorgröße nicht direkt auslesbar – Standard meist 512 (eMMC) oder 4096 (UFS) Bytes.")
        emit("  Sektorgröße nicht auslesbar (Standard: 512 eMMC / 4096 UFS).")
    # EFS/Funk-Partitionen lokalisieren und als TABU markieren
    efs = adb.shell("ls -l /dev/block/by-name/ 2>/dev/null")
    efs_hits = [ln for ln in efs.splitlines() if any(p in ln.lower() for p in EFS_PARTITION_HINT)]
    if efs_hits:
        ui.crit("EFS/Funk-Kalibrierungs-Partitionen erkannt – beim Low-Level-Löschen TABU (IMEI/Netz-Tod)!")
        emit("  EFS/Funk-Partitionen (NIEMALS in einen Löschbereich aufnehmen):")
        for ln in efs_hits[:20]:
            emit(f"    {ln[:110]}")
    else:
        emit("  Keine EFS/Funk-Partitionsnamen sichtbar (by-name evtl. nicht lesbar ohne Root).")
    emit("  ⚠ Low-Level-Löschungen (EDL/BROM) müssen exakt sektor-/partitionsgenau sein – ein Byte-Offset")
    emit("    daneben überschreibt IMEI/EFS und macht das Gerät dauerhaft funktot. Das Tool führt KEINE")
    emit("    solchen Löschungen automatisiert aus.")

    # --- RISIKO-MATRIX (Konsolidierung der Leitfragen) ---------------------
    ui.rule("Risiko-Matrix · Entscheidungsgrundlage", ui.YELLOW)
    emit("\n--- [RISIKO-MATRIX] ---")
    bl_txt = ("ENTSPERRT" if is_unlocked else "GESPERRT" if is_locked else "unbekannt")
    matrix = [
        ("Bootloader-Status", bl_txt),
        ("Root / su aktiv", "ja" if ("uid=0" in id_root) else "nein"),
        ("Dateisystem-/Persist-Gegenprüfung", "AKTIV" if persist.strip() else "nicht sichtbar"),
        ("FRP-Partition lokalisiert", "ja" if frp.strip() else "nein/nicht lesbar"),
        ("Zweite Sperre (OEM/Cloud/Konto)", "JA – Vorsicht" if cloud_found else "keine erkannt"),
        ("Flash-Sektorgröße bekannt", f"{block_size} B" if block_size else "unbekannt (512/4096 annehmen)"),
        ("EFS/IMEI-Partitionen als TABU markiert", "ja" if efs_hits else "n/a"),
    ]
    for k, v in matrix:
        ui.kv(k, v, key_w=38)
        emit(f"  {k:<40} : {v}")
    emit("\n  HINWEIS: Dieses Tool sammelt ausschließlich read-only Diagnosedaten und führt KEINE")
    emit("  FRP-/Partitions-Löschungen oder Sperr-Umgehungen automatisiert aus. Eingriffe sind manuell,")
    emit("  nur an EIGENEN/autorisiert untersuchten Geräten und in eigener Verantwortung durchzuführen.")

    # --- Direkt anzeigen + speichern --------------------------------------
    emit("\n" + "=" * 72)
    emit("DIAGNOSE BEENDET.")
    body = "\n".join(lines) + "\n"
    # Vollständigen Bericht DIREKT im Terminal anzeigen (seitenweise), nicht nur in die Datei.
    ui.pager(body, "Root-/Bootloader-Tiefen-Diagnose · vollständiger Bericht")
    ddir = outdir("diagnostics")
    fn = os.path.join(ddir, f"root_diag_{d.get('device','device')}_{time.strftime('%Y%m%d_%H%M%S')}.log")
    try:
        with open(fn, "w", encoding="utf-8") as f:
            f.write(body)
        ui.ok(f"Vollständiger Bericht oben angezeigt · zusätzlich gespeichert: {fn}")
        LOG.info(f"Root-Diagnose-Log: {fn}")
    except OSError as e:
        ui.err(f"Konnte Log nicht schreiben: {e}")
        LOG.exception("Root-Diagnose-Log schreiben", e)
    ui.pause()
    return fn


def _have_fastboot() -> str:
    import shutil
    p = shutil.which("fastboot")
    return f"✓ {p}" if p else "✗ fastboot fehlt – Android platform-tools installieren"


def _guided_flow(adb: ADB, dev: Device, info: dict) -> None:
    import shutil
    ui.clear()
    ui.rule("Geführter Magisk-Root-Ablauf", ui.YELLOW)
    ui.danger("Letzte Warnung: Datenverlust & Bootloop möglich. Akku >50% sicherstellen!")
    if not ui.confirm("Verstanden und fortfahren?", False):
        return

    # Schritt 1: Bootloader
    ui.rule("Schritt 1 – Bootloader", ui.CYAN)
    if info["bootloader"] != "unlocked":
        ui.warn("Bootloader ist gesperrt. Entsperren wipet das Gerät.")
        ui.info(f"Methode für {info['brand']}: {info['method']['unlock_cmd']}")
        if ui.confirm("In den Fastboot-Modus neu starten, um zu entsperren?", False):
            adb.shell("reboot bootloader")
            ui.info("Im Fastboot dann ausführen:  fastboot flashing unlock  (Tasten am Gerät bestätigen).")
        ui.pause("Wenn entsperrt & neu gebootet: ENTER")
    else:
        ui.ok("Bootloader bereits entsperrt – Schritt übersprungen.")

    # Schritt 2: boot.img ziehen (falls möglich) und Magisk
    ui.rule("Schritt 2 – boot.img besorgen & patchen", ui.CYAN)
    ui.info("Das stock boot.img MUSS exakt zu deinem aktuellen Build passen:")
    ui.kv("Build-Fingerprint", info["fingerprint"], key_w=18)
    if info["bootloader"] == "unlocked" and adb.check_root() is False:
        # Ohne Root lässt sich die boot-Partition i.d.R. nicht dumpen -> Hinweis
        ui.info("Ohne Root lässt sich boot.img nicht direkt auslesen → aus der zum Build passenden "
                "Hersteller-Firmware/OTA extrahieren (payload.bin → boot.img).")
    ui.info("Magisk-APK auf das Gerät installieren, dort 'Install → Select & Patch a File' → boot.img wählen.")
    ui.info("Die gepatchte Datei (magisk_patched-xxxx.img) zurück auf den PC ziehen (adb pull).")
    ui.pause("Wenn magisk_patched.img auf dem PC liegt: ENTER")

    # Schritt 3: flashen
    ui.rule("Schritt 3 – Patched-Image flashen", ui.CYAN)
    if not shutil.which("fastboot"):
        ui.err("fastboot fehlt – bitte installieren, dann manuell flashen.")
        ui.pause()
        return
    img = ui.ask("Pfad zur gepatchten Image-Datei (leer = abbrechen)")
    if not img or not os.path.isfile(os.path.expanduser(img)):
        ui.warn("Keine gültige Datei – Flash abgebrochen.")
        ui.pause()
        return
    target = "init_boot" if info["brand"].lower() in ("google", "pixel") and info["android"] >= "13" else "boot"
    cmd = f"fastboot flash {target} {os.path.expanduser(img)}"
    ui.warn(f"Auszuführender Befehl:  {cmd}")
    if ui.confirm("Jetzt flashen? (Gerät muss im Fastboot sein)", False):
        import subprocess
        try:
            p = subprocess.run(["fastboot", "flash", target, os.path.expanduser(img)],
                               capture_output=True, text=True, timeout=120)
            ui.pager((p.stdout + "\n" + p.stderr).strip(), "fastboot-Ausgabe")
            if p.returncode == 0:
                ui.ok("Image geflasht. Nächster Schritt:  fastboot reboot")
                if ui.confirm("Jetzt neu starten?", True):
                    subprocess.run(["fastboot", "reboot"], timeout=30)
        except Exception as e:  # noqa: BLE001
            ui.err(str(e))
    ui.pause()


def _save_checklist(info: dict, needs: list, meth: dict) -> None:
    fn = os.path.expanduser(f"~/Schreibtisch/Androidpanzer/root_checklist_{info['device'] or 'device'}.txt")
    lines = [f"ROOT-CHECKLISTE – {info['brand']} {info['model']} ({info['device']})",
             f"Android {info['android']}  Build {info['build']}",
             f"Fingerprint: {info['fingerprint']}",
             f"Bootloader: {info['bootloader']}  |  Slot: {info['slot'] or 'A-only'}",
             f"Aufwand: {info['effort']}", f"Risiko: {info['risk']}", "", "Benötigt:"]
    lines += [f"  - {k}: {v}" for k, v in needs]
    lines += ["", f"Methode: {meth['patch']}", f"Unlock: {meth['unlock_cmd']}",
              f"Hinweise: {meth['notes']}"]
    body = "\n".join(lines) + "\n"
    try:
        with open(fn, "w", encoding="utf-8") as f:
            f.write(body)
    except OSError as e:
        ui.err(str(e)); return
    ui.show_report(body, "Root-Checkliste", fn, note="Checkliste")
