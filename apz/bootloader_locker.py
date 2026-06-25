"""BOOTLOADER LOCKER: Sperrt Bootloader via Download-Modus (fastboot flashing lock).

⚠  AUF CUSTOM-ROM OHNE AVB-SIGNING BRICKT DAS DAS GERÄT.
   Nur verwenden wenn das ROM mit eigenen AVB-Keys signiert ist,
   oder wenn danach offizielles Firmware wiederhergestellt wird.
"""
from __future__ import annotations

import subprocess
import time

from . import ui


def _fastboot_wait(timeout: int = 60) -> bool:
    """Wartet bis Gerät im Fastboot/Download-Modus erscheint."""
    spin = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    import sys
    for i in range(timeout * 2):
        r = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, timeout=3)
        if r.stdout.strip():
            print()
            return True
        sys.stdout.write(f"\r  {ui.NEON}{spin[i % len(spin)]}{ui.RESET} Warte auf Fastboot-Modus...  ")
        sys.stdout.flush()
        time.sleep(0.5)
    print()
    return False


def _fastboot_run(*args) -> tuple[bool, str]:
    """Führt fastboot-Befehl aus, gibt (success, output) zurück."""
    try:
        r = subprocess.run(["fastboot"] + list(args),
                           capture_output=True, text=True, timeout=30)
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except Exception as e:
        return False, str(e)


def _show_avb_warning() -> None:
    ui.rule("⚠  SICHERHEITSWARNUNG", ui.BRED)
    print(f"""
  {ui.BRED}GEFAHR: Bootloader auf Custom-ROM sperren{ui.RESET}

  Das Sperren des Bootloaders aktiviert Verified Boot (AVB).
  Das Gerät prüft beim Start die Signatur aller Partitionen.

  {ui.BYELLOW}Wenn das ROM NICHT mit eigenen AVB-Keys signiert ist:{ui.RESET}
    → Gerät startet NIE MEHR ins System  (Soft-Brick)
    → Recovery bleibt zugänglich für Wiederherstellung

  {ui.BGREEN}Sicher ist es nur wenn:{ui.RESET}
    ✓ Eigene AVB-Keys generiert wurden
    ✓ LineageOS damit signiert und geflasht wurde
    ✓ Keys in den Bootloader eingebettet wurden

  {ui.GREY}Nach dem Sperren wird /data automatisch gewischt (Samsung-Standard).{ui.RESET}
""")
    ui.rule(color=ui.BRED)


def lock_sequence(adb) -> None:
    """Vollautomatische Bootloader-Sperr-Sequenz."""
    ui.clear()
    ui.banner(subtitle="🔒 BOOTLOADER SPERREN")
    _show_avb_warning()

    print(f"  {ui.BOLD}Optionen:{ui.RESET}")
    print(f"  {ui.BOLD}1{ui.RESET}  {ui.BRED}ERZWINGEN{ui.RESET}  – Bootloader jetzt sperren (AVB-Warnung ignorieren)")
    print(f"  {ui.BOLD}2{ui.RESET}  {ui.BGREEN}SICHER VORBEREITEN{ui.RESET}  – AVB-Keys generieren & ROM signieren")
    print(f"  {ui.BOLD}0{ui.RESET}  Abbrechen")
    print()
    ch = ui.ask("Auswahl", "0")

    if ch == "0":
        return
    elif ch == "2":
        _avb_preparation_guide()
        return
    elif ch != "1":
        ui.warn("Ungültig")
        return

    # ── Erzwingen: dreifache Bestätigung ────────────────────────────────────
    ui.clear()
    ui.banner(subtitle="🔒 BOOTLOADER SPERREN · Bestätigung")
    _show_avb_warning()
    print(f"  {ui.BRED}Tippe exakt  SPERREN  um fortzufahren (oder ENTER zum Abbrechen):{ui.RESET}")
    print()
    ans = ui.ask("", "").strip()
    if ans != "SPERREN":
        ui.warn("Abgebrochen.")
        time.sleep(1)
        return

    ui.warn("Letzte Chance! Wirklich sperren? [ja/nein]")
    ans2 = ui.ask("", "nein").strip().lower()
    if ans2 not in ("ja", "j"):
        ui.warn("Abgebrochen.")
        time.sleep(1)
        return

    # ── Schritt 1: In Download-Modus booten ─────────────────────────────────
    ui.clear()
    ui.banner(subtitle="🔒 BOOTLOADER SPERREN · Läuft")
    ui.rule("SCHRITT 1 / 3 · Neustart in Download-Modus", ui.CYAN)
    ui.info("Sende Reboot-Befehl...")
    try:
        subprocess.run(["adb", "reboot", "bootloader"], timeout=10)
        ui.ok("Reboot-Befehl gesendet")
    except Exception as e:
        ui.err(f"Reboot fehlgeschlagen: {e}")
        ui.pause()
        return

    # ── Schritt 2: Auf Fastboot warten ──────────────────────────────────────
    ui.rule("SCHRITT 2 / 3 · Warte auf Fastboot/Download-Modus", ui.CYAN)
    if not _fastboot_wait(timeout=45):
        ui.err("Gerät erschien nicht im Fastboot-Modus nach 45 Sekunden.")
        ui.pause()
        return
    ok, out = _fastboot_run("devices")
    ui.ok(f"Fastboot verbunden: {out.splitlines()[0] if out else 'OK'}")
    time.sleep(1)

    # ── Schritt 3: Bootloader sperren ───────────────────────────────────────
    ui.rule("SCHRITT 3 / 3 · Bootloader sperren", ui.CYAN)
    ui.info("Führe fastboot flashing lock aus...")

    # Samsung: zuerst Standard, dann OEM-Fallback
    success, out = _fastboot_run("flashing", "lock")
    if not success or "error" in out.lower():
        ui.warn(f"flashing lock fehlgeschlagen ({out[:80]}), versuche oem lock...")
        success, out = _fastboot_run("oem", "lock")

    if success or "OKAY" in out or "lock" in out.lower():
        ui.ok(f"Bootloader gesperrt: {out[:120]}")
        time.sleep(1)
        ui.rule("NEUSTART", ui.CYAN)
        ui.info("Starte neu...")
        _fastboot_run("reboot")
        ui.ok("Neustart gesendet — Gerät startet. /data wird gewischt (normal).")
    else:
        ui.err(f"Sperren fehlgeschlagen: {out[:200]}")
        ui.info("Versuche manuell: Halte Volume-Up auf dem Gerät wenn gefragt.")
        _fastboot_run("reboot")

    ui.pause()


def _avb_preparation_guide() -> None:
    """Schritt-für-Schritt Anleitung zum AVB-Key-Signing für LineageOS."""
    ui.clear()
    ui.banner(subtitle="🔑 AVB-SIGNING VORBEREITUNG")
    ui.rule("SCHRITT-FÜR-SCHRITT: Bootloader SICHER sperren", ui.BGREEN)
    print(f"""
  Für sicheres Sperren braucht LineageOS eigene AVB-Signatur-Keys.

  {ui.BOLD}Schritt 1 — Keys generieren (einmalig):{ui.RESET}
  {ui.CYAN}subject='/CN=LineageOS/O=LineageOS'
  for alg in rsa2048 rsa4096; do
    openssl genrsa 4096 | openssl pkcs8 -topk8 -nocrypt -out $alg.pk8
    openssl req -new -x509 -key $alg.pk8 -out $alg.x509.pem -days 10000 -subj "$subject"
  done{ui.RESET}

  {ui.BOLD}Schritt 2 — ROM mit Keys signieren:{ui.RESET}
  {ui.CYAN}python3 sign_target_files_apks.py \\
    -o -d ~/.android-certs lineage-23.2-*.zip signed.zip{ui.RESET}

  {ui.BOLD}Schritt 3 — AVB Keys dem Gerät beibringen:{ui.RESET}
  {ui.CYAN}fastboot reboot bootloader
  fastboot erase avb_custom_key
  avbtool extract_public_key --key rsa4096.pk8 --output avb_pkmd.bin
  fastboot flash avb_custom_key avb_pkmd.bin{ui.RESET}

  {ui.BOLD}Schritt 4 — Signierten ROM flashen, dann sperren:{ui.RESET}
  {ui.CYAN}fastboot sideload signed.zip
  fastboot flashing lock{ui.RESET}

  {ui.GREY}Quellen: LineageOS AVB docs · source.android.com/security/verifiedboot{ui.RESET}
""")
    ui.rule(color=ui.BGREEN)
    ui.pause()


def menu(adb=None, dev=None, st=None, data=None) -> None:
    """Bootloader-Locker Menü."""
    while True:
        ui.clear()
        ui.banner(subtitle="🔒 BOOTLOADER-MANAGER")

        # Aktuellen Status anzeigen
        ui.rule("STATUS", ui.CYAN)
        try:
            r = subprocess.run(["adb", "shell", "getprop", "ro.boot.verifiedbootstate"],
                               capture_output=True, text=True, timeout=5)
            vbs = r.stdout.strip()
            r2 = subprocess.run(["adb", "shell", "getprop", "ro.boot.flash.locked"],
                                capture_output=True, text=True, timeout=5)
            locked = r2.stdout.strip()
            bl_status = f"{ui.BGREEN}GESPERRT{ui.RESET}" if locked == "1" else f"{ui.BRED}ENTSPERRT{ui.RESET}"
            avb_status = f"{ui.BGREEN}{vbs}{ui.RESET}" if vbs == "green" else f"{ui.BYELLOW}{vbs or 'unbekannt'}{ui.RESET}"
            print(f"  Bootloader:     {bl_status}")
            print(f"  Verified Boot:  {avb_status}")
        except Exception:
            print(f"  {ui.GREY}Status nicht lesbar{ui.RESET}")
        print()

        ui.rule("OPTIONEN", ui.CYAN)
        print(f"  {ui.BOLD}1{ui.RESET}  🔒 Bootloader sperren  {ui.BRED}(automatisch: DL-Modus → lock → reboot){ui.RESET}")
        print(f"  {ui.BOLD}2{ui.RESET}  🔑 AVB-Signing Anleitung  (für sicheres Sperren)")
        print(f"  {ui.BOLD}0{ui.RESET}  Zurück")
        print()
        ch = ui.ask("Auswahl", "0")

        if ch == "0":
            return
        elif ch == "1":
            lock_sequence(adb)
        elif ch == "2":
            _avb_preparation_guide()
