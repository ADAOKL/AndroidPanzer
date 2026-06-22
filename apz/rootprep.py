"""Hintergrund-Root-Vorbereitung + vollautomatischer Magisk-Root-Flow.

Idee: Sobald ein Gerät erkannt ist, sammelt ein Hintergrund-Thread die für genau
dieses Modell nötigen Fakten und löst – ohne Eingriff – die passenden
Download-Links auf (Magisk-APK, platform-tools, hersteller-spezifische
Firmware-Quelle für das Stock-boot.img) und hält sie bereit.

Geht der Nutzer später auf „Rooten", werden die vorbereiteten Dateien auf Wunsch
geladen (HTTPS erzwungen, SHA-256), ZIPs sicher entpackt, die Magisk-App auf das
Gerät installiert und – Schritt für Schritt mit präzisen Konto-/FRP-/Neustart-
Hinweisen – Bootloader entsperrt, in Fastboot gebootet, boot.img gepatcht und
geflasht.

Sicherheit zuerst: Destruktive Schritte (Unlock = Datenverlust, Flashen =
Bootloop-Risiko) laufen NUR nach ausdrücklicher Bestätigung. Es werden keine
Sperren umgangen und keine Dateien erfunden – fehlt eine Quelle, sagt das Tool
das offen und nennt den genauen manuellen Weg.
"""
from __future__ import annotations

import os
import re
import shutil
import threading
import time
import urllib.request
import zipfile

from . import modeswitch, ui
from .adb import ADB, Device
from .util import (LOG, human_size, outdir, safe_download, safe_extract_member,
                   safe_name, sha256_file, shq)

WORK = outdir("rootprep")
MAGISK_API = "https://api.github.com/repos/topjohnwu/Magisk/releases/latest"
PLATFORM_TOOLS = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"


# --------------------------------------------------------------------------- #
#  Konto-/FRP-Hinweise (präzise, je Hersteller & Phase)
# --------------------------------------------------------------------------- #
def account_guidance(brand: str) -> dict:
    """Liefert präzise Konto-/FRP-/Neustart-Hinweise je Ablauf-Phase.

    FRP (Factory Reset Protection) sperrt ein Gerät nach einem Wipe, wenn vorher
    ein Google-Konto angemeldet war und nach dem Reset nicht dasselbe Konto
    bestätigt werden kann. Beim Bootloader-Entsperren wird zwangsweise gewiped.
    """
    b = (brand or "").lower()
    g = {
        "vor_unlock": [
            "ℹ FRP/Konto JETZT klären – Entsperren des Bootloaders LÖSCHT ALLE DATEN (Factory Reset):",
            "  • Bei EIGENEM Gerät: Google-Konto NICHT zwingend entfernen, ABER du musst es nach dem",
            "    Reset wieder anmelden können (Passwort/2FA griffbereit). Sonst sperrt FRP das Gerät.",
            "  • Sicherer Weg: Einstellungen → Konten → Google entfernen (UND Hersteller-Konto), DANN entsperren.",
            "  • Bei fremdem/gebrauchtem Gerät ohne legitime Abmeldung: STOP – nicht fortfahren.",
        ],
        "nach_unlock": [
            "ℹ Nach dem Entsperren startet das Gerät neu und ist WERKSZUSTAND (alle Daten weg).",
            "  • Richte es minimal ein (kein Konto nötig) und aktiviere erneut: Entwickleroptionen → USB-Debugging.",
            "  • Erst danach lässt sich wieder per ADB arbeiten.",
        ],
        "vor_flash": [
            "ℹ Gerät bleibt im Fastboot-Modus, USB-Kabel angeschlossen lassen, Akku >50 %.",
            "  • Während des Flashens nichts am Gerät antippen und nicht trennen.",
        ],
        "nach_flash": [
            "ℹ Nach dem ersten Neustart Magisk-App öffnen → ggf. 'Direct Install', um Root abzuschließen.",
            "  • Erst danach Google-Konto wieder anmelden, falls vorher entfernt.",
        ],
    }
    if b in ("samsung",):
        g["vor_unlock"].append(
            "  • SAMSUNG: OEM-Unlock in Entwickleroptionen muss verfügbar/aktiv sein; Knox-Bit wird")
        g["vor_unlock"].append(
            "    PERMANENT getrippt (Samsung Pay/Secure Folder/Pass dauerhaft verloren). Zusätzlich")
        g["vor_unlock"].append(
            "    Samsung-Konto-Reactivation-Lock abmelden, sonst greift FRP doppelt.")
    elif b in ("xiaomi", "redmi", "poco"):
        g["vor_unlock"].append(
            "  • XIAOMI: Mi-Konto mit dem Gerät verknüpfen und Mi-Unlock-Tool nutzen – oft 168 h")
        g["vor_unlock"].append(
            "    (7 Tage) Wartesperre. Mi-Cloud-Konto vorher abmelden (zweite Sperrebene).")
    elif b in ("google", "pixel"):
        g["vor_unlock"].append(
            "  • PIXEL: OEM-Unlock in Entwickleroptionen aktivieren. Ab Android 13 wird init_boot statt boot gepatcht.")
    elif b in ("motorola", "moto", "lenovo"):
        g["vor_unlock"].append(
            "  • MOTOROLA: Unlock-Code zuerst auf der Hersteller-Seite anfordern (an Konto/Mail gebunden).")
    return g


# --------------------------------------------------------------------------- #
#  Plan & Hintergrund-Auflösung der Download-Links
# --------------------------------------------------------------------------- #
def _dl(label: str, url: str, kind: str, note: str = "") -> dict:
    return {"label": label, "url": url, "kind": kind, "note": note,
            "status": "bereit" if url else "manuell", "local": "", "sha": ""}


def build_plan(data: dict) -> dict:
    """Synchrones Gerüst (ohne Netz): Methode, Bootloader-Status, Konto-Hinweise."""
    from .rooting import _method_for
    brand = (data.get("brand", "") or "").lower()
    bl = (data.get("bootloader_unlocked", "") or "").lower()
    vb = (data.get("verifiedboot", "") or "").lower()
    if bl in ("0", "false", "unlocked") or vb == "orange":
        bootloader = "unlocked"
    elif bl in ("1", "true", "locked", "green") or vb in ("green", "yellow"):
        bootloader = "locked"
    else:
        bootloader = "unknown"
    return {
        "status": "running",
        "brand": data.get("brand", ""),
        "model": data.get("model", ""),
        "device": data.get("device", ""),
        "android": data.get("android", ""),
        "sdk": data.get("sdk", ""),
        "abi": data.get("abi", ""),
        "build": data.get("build", ""),
        "fingerprint": data.get("fingerprint", ""),
        "is_mtk": bool(data.get("is_mtk")),
        "bootloader": bootloader,
        "method": _method_for(brand, data),
        "guidance": account_guidance(brand),
        "downloads": [],
        "notes": [],
        "error": "",
    }


def resolve_magisk_apk() -> dict | None:
    """Löst die URL der neuesten stabilen Magisk-APK auf (kein Download)."""
    try:
        req = urllib.request.Request(MAGISK_API, headers={"User-Agent": "panzer"})
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 (https)
            body = r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        LOG.exception("magisk release-api", e)
        return None
    urls = re.findall(r'"browser_download_url":\s*"([^"]+\.apk)"', body)
    if not urls:
        return None
    tag = re.search(r'"tag_name":\s*"([^"]+)"', body)
    url = next((u for u in urls if "debug" not in u.lower()), urls[0])
    ver = f" {tag.group(1)}" if tag else ""
    return _dl(f"Magisk-App (APK){ver}", url, "apk",
               "Root-Engine + Patcher. Wird auf das Gerät installiert und liefert magiskboot.")


def resolve_downloads(plan: dict) -> None:
    """Netz-Auflösung (Hintergrund): füllt plan['downloads']. Robust gegen Offline."""
    dls: list[dict] = []
    brand = (plan.get("brand", "") or "").lower()
    model = plan.get("model", "")
    build = plan.get("build", "")

    # 1) Magisk-APK (immer)
    mg = resolve_magisk_apk()
    dls.append(mg or _dl("Magisk-App (APK)", "", "apk",
                         "Auto-Auflösung fehlgeschlagen (offline?). Manuell: github.com/topjohnwu/Magisk/releases"))

    # 2) platform-tools (nur falls fastboot fehlt)
    if not shutil.which("fastboot"):
        dls.append(_dl("Android platform-tools (adb/fastboot)", PLATFORM_TOOLS, "tool-zip",
                       "fastboot fehlt im PATH – wird zum Flashen gebraucht. ZIP wird automatisch entpackt."))

    # 3) Hersteller-spezifische Quelle fürs Stock-boot.img
    q = urllib.request.quote(f"{plan.get('brand','')} {model} {build} stock boot.img firmware")
    search = f"https://www.google.com/search?q={q}"
    if plan.get("is_mtk"):
        dls.append(_dl("MediaTek-Root (integriert)", "", "builtin",
                       "MTK-Chipsatz erkannt → Hauptmenü 'M' nutzt mtkclient/BROM (oft OHNE Daten-Wipe)."))
    if brand in ("samsung",):
        dls.append(_dl("Samsung-Firmware (integriert via samloader)", "", "builtin",
                       "Hauptmenü 'G' → AUTO-ROOT lädt die exakte Firmware und patcht AP-Tar automatisch."))
    elif brand in ("google", "pixel"):
        dls.append(_dl("Pixel Factory/OTA-Image", "https://developers.google.com/android/images", "manual",
                       f"Lade das Image für Build {build or '(siehe Dashboard)'}, entpacke payload.bin → "
                       "init_boot.img (A13+) bzw. boot.img."))
    elif brand in ("xiaomi", "redmi", "poco"):
        dls.append(_dl("Xiaomi Fastboot-ROM", "https://xiaomifirmwareupdater.com/", "manual",
                       "Passende Fastboot-ROM laden, boot.img entnehmen. Entsperren via Mi-Unlock (168 h)."))
    elif brand in ("oneplus", "oppo", "realme"):
        dls.append(_dl("OnePlus/Oppo/Realme OTA", search, "search",
                       "Passendes OTA/Full-Package suchen, payload.bin → boot.img extrahieren."))
    elif brand in ("motorola", "moto", "lenovo"):
        dls.append(_dl("Motorola Firmware + Unlock-Code", "https://motorola-global-portal.custhelp.com/", "manual",
                       "Unlock-Code anfordern; Firmware (lenovo/moto) für boot.img besorgen."))
    else:
        dls.append(_dl(f"Stock-boot.img für {model or 'dieses Modell'} suchen", search, "search",
                       "Genau den AKTUELLEN Build verwenden – ein falsches boot.img führt zum Bootloop."))

    plan["downloads"] = dls
    plan["status"] = "done"


def start_background(data: dict, st: dict) -> None:
    """Startet die Hintergrund-Vorbereitung (idempotent pro Gerät)."""
    plan = build_plan(data)
    st["rootprep"] = plan

    def _worker() -> None:
        try:
            resolve_downloads(plan)
            LOG.info(f"Root-Vorbereitung fertig: {len(plan['downloads'])} Kandidaten")
        except Exception as e:  # noqa: BLE001
            plan["status"] = "error"
            plan["error"] = str(e)
            LOG.exception("rootprep-hintergrund", e)

    threading.Thread(target=_worker, name="rootprep", daemon=True).start()


# --------------------------------------------------------------------------- #
#  Download + sicheres Entpacken
# --------------------------------------------------------------------------- #
def _fetch(item: dict) -> bool:
    """Lädt EIN bereit-markiertes Item (HTTPS erzwungen) und entpackt ZIPs sicher."""
    if item["kind"] not in ("apk", "tool-zip") or not item["url"]:
        return False
    dst = os.path.join(WORK, safe_name(os.path.basename(item["url"]) or item["label"]))
    try:
        if os.path.isfile(dst) and os.path.getsize(dst) > 0:
            item["sha"] = sha256_file(dst)
            ui.ok(f"{item['label']} (bereits vorhanden) · SHA-256 {item['sha'][:16]}…")
        else:
            ui.info(f"Lade {item['label']} …")
            item["sha"] = safe_download(item["url"], dst)
            ui.ok(f"{item['label']} geladen · {human_size(os.path.getsize(dst))} · SHA-256 {item['sha'][:16]}…")
        item["local"] = dst
        item["status"] = "geladen"
    except Exception as e:  # noqa: BLE001
        ui.err(f"Download fehlgeschlagen ({item['label']}): {e}")
        LOG.exception(f"rootprep download {item['label']}", e)
        item["status"] = "fehler"
        return False
    # ZIP automatisch entpacken (z.B. platform-tools)
    if item["kind"] == "tool-zip" or dst.lower().endswith(".zip"):
        try:
            outd = os.path.join(WORK, safe_name(item["label"]) + "_entpackt")
            os.makedirs(outd, exist_ok=True)
            with zipfile.ZipFile(dst) as z:
                for m in z.namelist():
                    safe_extract_member(z, m, outd)
            item["extracted"] = outd
            ui.ok(f"Entpackt → {outd}")
        except Exception as e:  # noqa: BLE001
            ui.warn(f"Entpacken übersprungen ({item['label']}): {e}")
    return True


def download_all(plan: dict) -> dict:
    """Lädt alle automatisch ladbaren Items; gibt {kind:item} der Erfolge zurück."""
    got: dict = {}
    fetchable = [d for d in plan["downloads"] if d["kind"] in ("apk", "tool-zip") and d["url"]]
    if not fetchable:
        ui.warn("Keine automatisch ladbaren Dateien vorbereitet.")
        return got
    for item in fetchable:
        if _fetch(item):
            got[item["kind"]] = item
    # PATH um entpackte platform-tools erweitern (für dieses Tool-Laufzeit)
    tool = got.get("tool-zip")
    if tool and tool.get("extracted"):
        ptdir = os.path.join(tool["extracted"], "platform-tools")
        if os.path.isdir(ptdir):
            os.environ["PATH"] = ptdir + os.pathsep + os.environ.get("PATH", "")
            ui.ok(f"fastboot/adb aus {ptdir} für diese Sitzung aktiviert.")
    return got


# --------------------------------------------------------------------------- #
#  On-Device-Patch (generisch, ohne Root) – magiskboot aus der APK
# --------------------------------------------------------------------------- #
def _extract_magisk_bins(apk: str, abi: str) -> str | None:
    mdir = os.path.join(WORK, "magisk_bins")
    os.makedirs(mdir, exist_ok=True)
    for f in os.listdir(mdir):
        try:
            os.remove(os.path.join(mdir, f))
        except OSError:
            pass
    want = [("libmagiskboot.so", "magiskboot"), ("libmagiskinit.so", "magiskinit"),
            ("libmagisk.so", "magisk"), ("libmagisk64.so", "magisk64"),
            ("libmagisk32.so", "magisk32"), ("libmagiskpolicy.so", "magiskpolicy"),
            ("libbusybox.so", "busybox"), ("libinit-ld.so", "init-ld")]
    try:
        with zipfile.ZipFile(apk) as z:
            names = z.namelist()
            for libname, out in want:
                cand = next((n for n in names if n.endswith(f"/{abi}/{libname}")), None) \
                    or next((n for n in names if n.endswith(f"/{libname}")), None)
                if cand:
                    with z.open(cand) as s, open(os.path.join(mdir, out), "wb") as o:
                        o.write(s.read())
            for asset in ("boot_patch.sh", "util_functions.sh", "addon.d.sh", "stub.apk"):
                cand = next((n for n in names if n.endswith(f"assets/{asset}")), None)
                if cand:
                    with z.open(cand) as s, open(os.path.join(mdir, asset), "wb") as o:
                        o.write(s.read())
    except Exception as e:  # noqa: BLE001
        LOG.exception("magisk-bins extrahieren", e)
        return None
    return mdir if os.path.isfile(os.path.join(mdir, "magiskboot")) else None


def _patch_boot_ondevice(adb: ADB, boot: str, mdir: str) -> str | None:
    """Pusht magiskboot + boot.img, führt boot_patch.sh aus (ohne Root), holt new-boot.img."""
    rdir = "/data/local/tmp/panzer_magisk"
    adb.shell(f"rm -rf {shq(rdir)}; mkdir -p {shq(rdir)}")
    for f in os.listdir(mdir):
        adb.raw(["push", os.path.join(mdir, f), f"{rdir}/{f}"], timeout=120)
    adb.raw(["push", boot, f"{rdir}/boot.img"], timeout=180)
    out = adb.shell(
        f"cd {shq(rdir)} && chmod -R 0755 . && "
        f"KEEPVERITY=true KEEPFORCEENCRYPT=true sh boot_patch.sh {rdir}/boot.img 2>&1", timeout=180)
    print("   " + "\n   ".join((out or "").splitlines()[-12:]))
    listing = adb.shell(f"ls {shq(rdir)}")
    name = next((n for n in ("new-boot.img", "magisk_patched.img") if n in listing), None)
    if not name:
        return None
    local = os.path.join(WORK, "images", "magisk_patched_boot.img")
    os.makedirs(os.path.dirname(local), exist_ok=True)
    adb.raw(["pull", f"{rdir}/{name}", local], timeout=120)
    adb.shell(f"rm -rf {shq(rdir)}")
    return local if os.path.isfile(local) and os.path.getsize(local) > 0 else None


# --------------------------------------------------------------------------- #
#  Anzeige der Vorbereitung (im Root-Menü)
# --------------------------------------------------------------------------- #
def render_plan(plan: dict) -> None:
    status = plan.get("status")
    sym = {"running": f"{ui.BYELLOW}⟳ läuft …{ui.RESET}", "done": f"{ui.BGREEN}✓ bereit{ui.RESET}",
           "error": f"{ui.BRED}✗ Fehler{ui.RESET}"}.get(status, status)
    ui.rule(f"Vorbereitete Downloads (Hintergrund: {sym})", ui.CYAN)
    if status == "running":
        ui.info("Die Auflösung der Download-Links läuft noch – gleich aktualisiert.")
    for d in plan.get("downloads", []):
        kind = {"apk": "[APK]", "tool-zip": "[TOOL]", "manual": "[MANUELL]",
                "search": "[SUCHE]", "builtin": "[INTEGRIERT]"}.get(d["kind"], "")
        col = ui.BGREEN if d["status"] in ("bereit", "geladen") else ui.GREY
        ui.kv(f"{kind} {d['label']}", f"{col}{d['status']}{ui.RESET}", key_w=42)
        if d.get("url"):
            print(f"      {ui.GREY}{d['url'][:100]}{ui.RESET}")
        if d.get("note"):
            print(f"      {ui.DIM}{d['note']}{ui.RESET}")


def _print_block(lines: list[str]) -> None:
    for ln in lines:
        print(f"  {ln}")


# --------------------------------------------------------------------------- #
#  Vollautomatischer Flow
# --------------------------------------------------------------------------- #
def run_auto(adb: ADB, dev: Device, info: dict, st: dict) -> None:
    """Geführter Auto-Root: Downloads → Magisk-App → Unlock → Fastboot → Patch → Flash.

    Destruktive Schritte nur nach Bestätigung. Bei jedem Schritt stehen die
    nötigen Konto-/FRP-/Neustart-Hinweise.
    """
    if "samsung" in (info.get("brand", "") or "").lower():
        ui.warn("Hinweis: Samsung wird über Odin/Heimdall (Download-Modus) geflasht, NICHT über Fastboot.")
        ui.info("Empfohlen: Samsung-Modul (Hauptmenü 'G' → AUTO-ROOT). Der folgende generische")
        ui.info("Fastboot-Flow ist für Samsung NUR für den Download/Patch-Teil sinnvoll, nicht zum Flashen.")
        if not ui.confirm("Trotzdem mit dem generischen Flow fortfahren?", False):
            return
    plan = st.get("rootprep") or build_plan(info)
    if plan.get("status") == "running":
        ui.info("Hintergrund-Vorbereitung läuft noch – warte kurz …")
        for _ in range(20):
            if plan.get("status") != "running":
                break
            time.sleep(0.5)
    g = plan.get("guidance", account_guidance(info.get("brand", "")))

    ui.clear()
    ui.banner(subtitle="🚀 Auto-Root (vorbereitet) – Download · Patch · Flash")
    render_plan(plan)
    print()
    ui.danger("WARNUNG: Bootloader entsperren LÖSCHT ALLE DATEN. Flashen kann zum Bootloop führen.")
    ui.rule("Konto / FRP – JETZT klären (vor dem Entsperren)", ui.YELLOW)
    _print_block(g["vor_unlock"])
    print()
    if not ui.confirm("Verstanden – mit der Vorbereitung fortfahren?", False):
        ui.info("Abgebrochen – kein Eingriff vorgenommen."); ui.pause(); return

    # 1) Downloads
    got = {}
    if any(d["kind"] in ("apk", "tool-zip") and d["url"] for d in plan.get("downloads", [])):
        if ui.confirm("Vorbereitete Dateien jetzt automatisch herunterladen (HTTPS, mit SHA-256)?", True):
            ui.rule("Schritt 1 · Downloads", ui.CYAN)
            got = download_all(plan)
            ui.info("SHA-256 vor dem Flashen mit der offiziellen Quelle abgleichen.")
            ui.pause()

    # 2) Magisk-App installieren
    magisk_apk = (got.get("apk") or {}).get("local", "")
    if magisk_apk and os.path.isfile(magisk_apk):
        ui.rule("Schritt 2 · Magisk-App installieren", ui.CYAN)
        if ui.confirm("Magisk-App jetzt auf das Gerät installieren?", True):
            rc, out, err = adb.raw(["install", "-r", magisk_apk], timeout=180)
            ui.info((out + err).strip() or ("OK" if rc == 0 else "Installation unklar"))
            ui.info("Die reine APK gewährt noch KEINEN Root – erst der gepatchte boot/init_boot tut das.")
            ui.pause()

    # 3) Bootloader entsperren
    ui.rule("Schritt 3 · Bootloader", ui.CYAN)
    if plan.get("bootloader") == "unlocked":
        ui.ok("Bootloader bereits entsperrt – Schritt übersprungen.")
    else:
        ui.warn(f"Bootloader gesperrt. Methode für {info.get('brand','?')}: {plan['method']['unlock_cmd']}")
        _print_block(g["vor_unlock"])
        if ui.confirm("Jetzt automatisch in den Fastboot-Modus wechseln, um zu entsperren?", False):
            modeswitch.ensure(adb, dev, "fastboot")   # automatisch + warten bis erkannt
            ui.info("Im Fastboot:  fastboot flashing unlock  (am Gerät mit Lautstärke/Power bestätigen).")
            ui.warn("Das Gerät wird dabei GEWIPED.")
            _print_block(g["nach_unlock"])
        ui.pause("Wenn entsperrt, neu eingerichtet & USB-Debugging wieder AN: ENTER")

    # 4) boot.img besorgen
    ui.rule("Schritt 4 · Stock-boot.img", ui.CYAN)
    ui.kv("Exakter Build", info.get("fingerprint", "") or info.get("build", ""), key_w=14)
    ui.info("Das boot.img MUSS exakt zu diesem Build passen – sonst Bootloop.")
    for d in plan.get("downloads", []):
        if d["kind"] in ("manual", "search", "builtin"):
            ui.info(f"Quelle: {d['label']} – {d.get('note','')}")
            if d.get("url"):
                print(f"        {ui.GREY}{d['url']}{ui.RESET}")
    boot = ui.ask("Pfad zum Stock-boot.img (leer = im Magisk-App-GUI patchen)").strip()
    boot = os.path.expanduser(boot) if boot else ""

    patched = ""
    if boot and os.path.isfile(boot):
        # 5a) On-Device patchen (ohne Root)
        ui.rule("Schritt 5 · boot.img patchen (on-device, ohne Root)", ui.CYAN)
        if magisk_apk and ui.confirm("boot.img automatisch mit magiskboot patchen?", True):
            mdir = _extract_magisk_bins(magisk_apk, info.get("abi", "arm64-v8a"))
            if not mdir:
                ui.err("magiskboot konnte nicht aus der APK extrahiert werden – nutze Magisk-App-GUI.")
            else:
                patched = _patch_boot_ondevice(adb, boot, mdir) or ""
                if patched:
                    ui.ok(f"Gepatcht: {patched}")
                else:
                    ui.err("Patchen fehlgeschlagen – Fallback: boot.img in der Magisk-App patchen.")
    else:
        ui.info("Ohne lokales boot.img: Magisk-App öffnen → Install → 'Select and Patch a File' → boot.img,")
        ui.info("dann die magisk_patched-*.img per 'adb pull' auf den PC holen und hier flashen.")
        ui.pause("Wenn die gepatchte Datei auf dem PC liegt: ENTER")
        man = ui.ask("Pfad zur gepatchten Image-Datei (leer = abbrechen)").strip()
        patched = os.path.expanduser(man) if man else ""

    # 6) Flashen
    if not patched or not os.path.isfile(patched):
        ui.warn("Keine gepatchte Image-Datei – Flash-Schritt übersprungen.")
        ui.pause(); return
    ui.rule("Schritt 6 · Patched-Image flashen", ui.CYAN)
    _print_block(g["vor_flash"])
    if not shutil.which("fastboot"):
        ui.err("fastboot fehlt weiterhin im PATH – bitte platform-tools installieren/entpacken.")
        ui.pause(); return
    a = (info.get("android", "") or "")
    target = "init_boot" if (info.get("brand", "").lower() in ("google", "pixel") and a and a >= "13") else "boot"
    ui.warn(f"Auszuführen:  fastboot flash {target} {patched}")
    if ui.confirm("Jetzt flashen? (Gerät wird zuvor automatisch in Fastboot gebracht)", False):
        ok, _ = modeswitch.ensure(adb, dev, "fastboot")
        if not ok:
            ui.err("Fastboot-Modus nicht erreicht – Flash abgebrochen."); ui.pause(); return
        import subprocess
        try:
            p = subprocess.run(["fastboot", "flash", target, patched],
                               capture_output=True, text=True, timeout=180)
            ui.pager((p.stdout + "\n" + p.stderr).strip(), "fastboot-Ausgabe")
            if p.returncode == 0:
                ui.ok(f"{target} geflasht.")
                _print_block(g["nach_flash"])
                if ui.confirm("Jetzt neu starten (fastboot reboot)?", True):
                    subprocess.run(["fastboot", "reboot"], timeout=30)
        except Exception as e:  # noqa: BLE001
            ui.err(str(e))
            LOG.exception("fastboot flash", e)
    ui.pause()
