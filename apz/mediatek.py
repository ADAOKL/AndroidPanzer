"""MediaTek Root/Flash-Suite (mtkclient · BROM-Exploit).

Der MTK-BROM-Exploit (kamakiri/hashimoto) erlaubt Lesen/Schreiben jeder Partition
OHNE Bootloader-Unlock – und Bootloader-Unlock via seccfg oft OHNE Datenverlust.

Funktionen:
  1) AUTO-ROOT (Magisk): seccfg-Unlock → boot.img dumpen → on-device patchen →
     vbmeta-verity deaktivieren → zurückschreiben.  (meist ohne Wipe!)
  2) Bootloader entsperren (seccfg) – ohne Wipe, soweit das Modell es zulässt.
  3) Partitionen lesen (printgpt) / Voll-Backup / Einzel-Dump / Flashen.

Benötigt: mtkclient (pip install mtkclient) + USB-Treiber/Rechte. Gerät im BROM:
ausschalten → Vol-Hoch+Vol-Runter gedrückt halten → USB einstecken (mtk wartet).

Reuse der Magisk-Patch-Pipeline aus samsung.py (APK→magiskboot→on-device-Patch).
"""
from __future__ import annotations

import os
import subprocess

from . import ui, usb
from .samsung import (_disable_vbmeta, _download_magisk_apk, _extract_magisk_bins,
                      _patch_boot_ondevice)

WORK = os.path.expanduser("~/Schreibtisch/Androidpanzer/mediatek")


def _w(*sub) -> str:
    p = os.path.join(WORK, *sub)
    os.makedirs(os.path.dirname(p) if os.path.splitext(p)[1] else p, exist_ok=True)
    return p


def _have_mtk() -> str | None:
    return usb.tool_path("mtk")


def mtk(args: list[str], timeout: int = 600, stream: bool = True) -> tuple[int, str]:
    """mtkclient-Aufruf. Wartet ggf. auf das BROM-Gerät; Ausgabe optional live."""
    cmd = [usb.tool_path("mtk") or "mtk"] + args
    if not stream:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return p.returncode, (p.stdout + p.stderr).strip()
        except subprocess.TimeoutExpired:
            return 124, "Timeout"
        except Exception as e:  # noqa: BLE001
            return 1, str(e)
    # Live-Stream (mtk zeigt Fortschritt + 'Waiting for device')
    out = []
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:  # type: ignore
            print("   " + line.rstrip())
            out.append(line.rstrip())
        proc.wait(timeout=timeout)
        return proc.returncode, "\n".join(out)
    except subprocess.TimeoutExpired:
        proc.kill(); return 124, "\n".join(out)
    except KeyboardInterrupt:
        proc.kill(); return 130, "\n".join(out)
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


# ===================================================================== #
#  Menü
# ===================================================================== #
def menu(adb, dev, st, data: dict) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🔶 MediaTek Root/Flash-Suite (mtkclient/BROM)")
        ui.kv("Modell", f"{data.get('brand','')} {data.get('model','')}")
        ui.kv("Chipsatz", data.get("platform", "") or data.get("hardware", "") or "—")
        ui.kv("mtkclient", f"{ui.BGREEN}{_have_mtk()}{ui.RESET}" if _have_mtk()
              else f"{ui.BRED}fehlt → pip install mtkclient{ui.RESET}")
        ui.kv("Modus", usb.mode_badge(dev.mode))
        ch = ui.menu("Aktionen", [
            ("1", f"{ui.BGREEN}{ui.BOLD}🚀 AUTO-ROOT (Magisk, meist OHNE Wipe){ui.RESET}"),
            ("2", "🔓 Bootloader entsperren (seccfg, ohne Wipe)"),
            ("3", "🔒 Bootloader sperren (seccfg lock)"),
            ("4", "📖 Partitionstabelle lesen (printgpt)"),
            ("5", "📤 Einzelne Partition dumpen (z.B. boot)"),
            ("6", "💾 Voll-Backup ALLER Partitionen"),
            ("7", "📥 Partition flashen (write)"),
            ("8", "↩ vbmeta verity deaktivieren + zurückschreiben"),
            ("9", "↻ Gerät zurücksetzen (mtk reset)"),
            ("?", "ℹ Voraussetzungen & BROM-Anleitung"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        {"1": auto_root, "2": unlock, "3": lock, "4": printgpt, "5": dump_part,
         "6": full_backup, "7": flash_part, "8": fix_vbmeta, "9": reset_dev,
         "?": show_help}.get(ch, lambda *a: None)(adb, dev, st, data)


def show_help(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("MediaTek BROM – Voraussetzungen", ui.CYAN)
    for l in [
        "1. mtkclient installieren:  pip install mtkclient",
        "   (+ Linux-Rechte: USB-udev-Regeln, ggf. als root/sudo ausführen)",
        "2. Gerät in den BROM-Modus bringen:",
        "   • Gerät komplett ausschalten",
        "   • Vol-Hoch + Vol-Runter gleichzeitig gedrückt halten",
        "   • USB-Kabel zum PC einstecken (Tasten weiter halten, bis mtk verbindet)",
        "   • Manche Geräte brauchen entladenen Akku oder Test-Point (kurz GND).",
        "3. mtk wartet automatisch ('Waiting for device') – Tasten loslassen, sobald erkannt.",
        "",
        "Vorteil BROM: liest/schreibt JEDE Partition ohne Unlock; seccfg-Unlock oft OHNE Wipe.",
        "Risiko: falsches Preloader/Image kann hart bricken – nur passende Dateien schreiben.",
    ]:
        print(f"   {ui.GREY}{l}{ui.RESET}")
    ui.pause()


def _need_mtk() -> bool:
    if not _have_mtk():
        ui.err("mtkclient fehlt:  pip install mtkclient")
        ui.info("Danach Gerät in BROM-Modus (Hilfe: Menü ?).")
        ui.pause(); return False
    return True


def unlock(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Bootloader entsperren (seccfg)", ui.CYAN)
    if not _need_mtk():
        return
    ui.warn("Entsperrt den Bootloader. Auf vielen MTK-Geräten OHNE Datenverlust – "
            "aber nicht garantiert. Backup empfohlen.")
    if not ui.confirm("Jetzt 'mtk da seccfg unlock' (Gerät im BROM)?", False):
        return
    rc, o = mtk(["da", "seccfg", "unlock"], timeout=300)
    ui.ok("Unlock-Befehl ausgeführt – am Gerät ggf. bestätigen, dann neu starten.") if rc == 0 \
        else ui.err("Fehlgeschlagen (siehe Ausgabe).")
    ui.pause()


def lock(adb, dev, st, data) -> None:
    if not _need_mtk():
        return
    if ui.confirm("Bootloader wieder sperren (mtk da seccfg lock)?", False):
        mtk(["da", "seccfg", "lock"], timeout=300)
    ui.pause()


def printgpt(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Partitionstabelle (printgpt)", ui.CYAN)
    if not _need_mtk():
        return
    rc, o = mtk(["printgpt"], timeout=180)
    open(_w("printgpt.txt"), "w").write(o)
    ui.ok(f"Gespeichert: {os.path.join(WORK,'printgpt.txt')}")
    ui.pause()


def dump_part(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Partition dumpen", ui.CYAN)
    if not _need_mtk():
        return
    part = ui.ask("Partition (z.B. boot, vbmeta, recovery, userdata)")
    if not part:
        return
    out = _w("dumps", f"{part}.img")
    rc, o = mtk(["r", part, out], timeout=1200)
    ui.ok(f"Dump: {out}") if os.path.isfile(out) else ui.err("Dump fehlgeschlagen.")
    ui.pause()


def full_backup(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Voll-Backup aller Partitionen", ui.CYAN)
    if not _need_mtk():
        return
    out = _w("full_dump")
    ui.warn("Liest ALLE Partitionen (kann sehr groß sein & lange dauern).")
    if ui.confirm("Starten?", False):
        mtk(["rl", out], timeout=7200)
        ui.ok(f"Backup-Ordner: {out}")
    ui.pause()


def flash_part(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Partition flashen", ui.CYAN)
    if not _need_mtk():
        return
    part = ui.ask("Ziel-Partition (z.B. boot, recovery, vbmeta)")
    img = ui.ask("Pfad zum Image")
    img = os.path.expanduser(img or "")
    if not part or not os.path.isfile(img):
        ui.err("Partition/Datei ungültig."); ui.pause(); return
    ui.danger(f"Schreibe {img} → {part}. Falsches Image kann hart bricken!")
    if ui.confirm("Wirklich flashen?", False):
        rc, o = mtk(["w", part, img], timeout=1200)
        ui.ok("Geflasht.") if rc == 0 else ui.err("Fehlgeschlagen.")
    ui.pause()


def fix_vbmeta(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("vbmeta verity deaktivieren", ui.CYAN)
    if not _need_mtk():
        return
    out = _w("dumps", "vbmeta.img")
    ui.info("Lese vbmeta …")
    mtk(["r", "vbmeta", out], timeout=300)
    if not os.path.isfile(out):
        ui.err("vbmeta nicht lesbar."); ui.pause(); return
    _disable_vbmeta(out)
    ui.ok("Flags gesetzt (disable-verity/verification).")
    if ui.confirm("Zurückschreiben (mtk w vbmeta)?", False):
        mtk(["w", "vbmeta", out], timeout=300)
    ui.pause()


def reset_dev(adb, dev, st, data) -> None:
    if _have_mtk():
        mtk(["reset"], timeout=30)
    ui.pause()


# ===================================================================== #
#  AUTO-ROOT
# ===================================================================== #
def auto_root(adb, dev, st, data) -> None:
    ui.clear(); ui.banner(subtitle="🚀 MediaTek Auto-Root (Magisk via BROM)")
    if not _need_mtk():
        return
    ui.info("Ablauf: Unlock → boot dumpen → on-device patchen → vbmeta → zurückschreiben.")
    ui.warn("Gerät muss im BROM-Modus sein (Hilfe: Menü ?). Für das Patchen muss es danach "
            "einmal normal booten (ADB).")
    if not ui.confirm("Starten?", False):
        return

    # 1) Unlock
    ui.rule("1 · Bootloader entsperren (seccfg, meist ohne Wipe)", ui.CYAN)
    if ui.confirm("seccfg unlock jetzt ausführen?", True):
        mtk(["da", "seccfg", "unlock"], timeout=300)

    # 2) boot + vbmeta dumpen
    ui.rule("2 · boot.img & vbmeta.img aus dem Gerät lesen (BROM)", ui.CYAN)
    boot = _w("dumps", "boot.img")
    vb = _w("dumps", "vbmeta.img")
    mtk(["r", "boot", boot], timeout=600)
    mtk(["r", "vbmeta", vb], timeout=300)
    if not os.path.isfile(boot):
        ui.err("boot.img konnte nicht gelesen werden."); ui.pause(); return
    ui.ok(f"boot.img: {boot}")

    # 3) Magisk vorbereiten
    ui.rule("3 · Magisk vorbereiten (APK → magiskboot)", ui.CYAN)
    apk = _download_magisk_apk()
    if not apk:
        ui.pause(); return
    ui.info("Jetzt das Gerät NORMAL booten (es bootet mit entsperrtem Bootloader) und "
            "USB-Debugging aktivieren – fürs on-device-Patchen.")
    ui.pause("Wenn Gerät gebootet & per ADB erreichbar: ENTER")
    if not usb.adb_serial():
        ui.err("Kein ADB-Gerät – Patchen nicht möglich. (Alternativ boot.img in Magisk-App patchen.)")
        ui.pause(); return
    abi = adb.getprop("ro.product.cpu.abi") or "arm64-v8a"
    mdir = _extract_magisk_bins(apk, abi)
    usb.adb_cmd(["install", "-r", apk], timeout=120)

    # 4) on-device patchen
    ui.rule("4 · boot.img patchen (on-device, ohne Root)", ui.CYAN)
    patched = _patch_boot_ondevice(adb, dev, boot, mdir)
    if not patched:
        ui.err("Patchen fehlgeschlagen."); ui.pause(); return
    ui.ok(f"Gepatcht: {patched}")

    # 5) vbmeta verity deaktivieren
    if os.path.isfile(vb):
        _disable_vbmeta(vb)
        ui.ok("vbmeta verity deaktiviert.")

    # 6) zurück in BROM, schreiben
    ui.rule("5 · Zurück in den BROM-Modus & schreiben", ui.CYAN)
    ui.info("Gerät wieder ausschalten → Vol-Hoch+Vol-Runter → USB (BROM).")
    ui.pause("Wenn wieder im BROM: ENTER")
    ui.danger(f"Schreibe gepatchtes boot → boot{', vbmeta → vbmeta' if os.path.isfile(vb) else ''}")
    if ui.confirm("Jetzt flashen?", False):
        mtk(["w", "boot", patched], timeout=600)
        if os.path.isfile(vb):
            mtk(["w", "vbmeta", vb], timeout=300)
        mtk(["reset"], timeout=30)
        ui.ok("Fertig! Gerät startet neu – Magisk-App öffnen und ggf. 'Direct Install'. "
              "MTK-Root meist OHNE Datenverlust. 🎉")
    ui.pause()
