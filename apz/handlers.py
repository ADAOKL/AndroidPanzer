"""Interaktive Feature-Handler (Live-Streams, Input, Datei-Transfer, Monitore).

Jeder Handler hat die Signatur handler(adb, dev, st) und kümmert sich selbst um
Ein-/Ausgabe. 'st' ist ein gemeinsamer State-Dict (z.B. is_root)."""
from __future__ import annotations

import os
import re
import subprocess
import time

from . import ui
from .adb import ADB
from .util import as_int, is_coords, shq


# ====================================================================== #
#  Hilfen
# ====================================================================== #
def _stream(adb: ADB, args: list[str], title: str, grep: str | None = None) -> None:
    """Live-Stream eines adb-Kommandos bis Strg+C."""
    ui.rule(title, ui.BCYAN)
    ui.info("Live – mit STRG+C beenden.\n")
    cmd = [adb.bin] + (["-s", adb.serial] if adb.serial else []) + args
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except FileNotFoundError:
        ui.err("adb nicht gefunden.")
        return
    rx = re.compile(grep, re.I) if grep else None
    try:
        for line in proc.stdout:  # type: ignore
            if rx is None or rx.search(line):
                print(line.rstrip())
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    print()
    ui.ok("Stream beendet.")
    ui.pause()


def _outdir() -> str:
    d = os.path.expanduser("~/Schreibtisch/Androidpanzer/out")
    os.makedirs(d, exist_ok=True)
    return d


# ====================================================================== #
#  Kategorie 3 – Input / UI-Steuerung
# ====================================================================== #
def tap(adb: ADB, dev, st) -> None:
    xy = ui.ask("Koordinaten X Y (z.B. 540 1200)")
    if xy and not is_coords(xy):
        ui.warn("Nur Zahlen erlaubt (z.B. '540 1200').")
    elif xy:
        ui.info(adb.shell(f"input tap {xy}") or "Tap gesendet.")
    ui.pause()


def swipe(adb: ADB, dev, st) -> None:
    v = ui.ask("X1 Y1 X2 Y2 [Dauer ms] (z.B. 500 1500 500 300 300)")
    if v and not is_coords(v):
        ui.warn("Nur Zahlen erlaubt (z.B. '500 1500 500 300 300').")
    elif v:
        ui.info(adb.shell(f"input swipe {v}") or "Swipe gesendet.")
    ui.pause()


def text_input(adb: ADB, dev, st) -> None:
    t = ui.ask("Text (Leerzeichen werden als %s gesendet)")
    if t:
        esc = t.replace(" ", "%s").replace("'", "")
        ui.info(adb.shell(f"input text '{esc}'") or "Text gesendet.")
    ui.pause()


def keyevent(adb: ADB, dev, st) -> None:
    keys = [
        ("3", "HOME"), ("4", "ZURÜCK"), ("26", "POWER"), ("82", "MENU"),
        ("187", "App-Switch (Recents)"), ("24", "Lauter"), ("25", "Leiser"),
        ("66", "ENTER"), ("61", "TAB"), ("85", "Play/Pause"), ("223", "Sleep"),
        ("224", "Wakeup"), ("27", "Kamera-Auslöser"), ("231", "Voice-Assist"),
    ]
    ui.rule("Hardware-/Scancode-Tasten", ui.CYAN)
    for k, lbl in keys:
        print(f"  {ui.CYAN}{k:>4}{ui.RESET}  {lbl}")
    code = ui.ask("Keycode (Zahl) oder eigener").strip()
    if code and not code.isdigit():
        ui.warn("Keycode muss eine Zahl sein.")
    elif code:
        ui.info(adb.shell(f"input keyevent {code}") or f"Keyevent {code} gesendet.")
    ui.pause()


def screen_state(adb: ADB, dev, st) -> None:
    disp = adb.shell("dumpsys power | grep -E 'mWakefulness=|Display Power'")
    ui.pager(disp or "—", "Bildschirm-Status")
    ch = ui.menu("Aktion", [("1", "Aufwecken (Wakeup)"), ("2", "Sperren (Sleep)"),
                            ("3", "Power-Taste togglen")], back_label="Zurück")
    if ch == "1":
        adb.shell("input keyevent KEYCODE_WAKEUP")
    elif ch == "2":
        adb.shell("input keyevent KEYCODE_SLEEP")
    elif ch == "3":
        adb.shell("input keyevent 26")
    if ch in ("1", "2", "3"):
        ui.ok("Gesendet.")
    ui.pause()


def ui_dump(adb: ADB, dev, st) -> None:
    ui.info("Lese UI-Hierarchie (uiautomator dump) …")
    adb.shell("uiautomator dump /sdcard/window_dump.xml")
    local = os.path.join(_outdir(), "window_dump.xml")
    adb.raw(["pull", "/sdcard/window_dump.xml", local])
    if os.path.isfile(local):
        ui.ok(f"Gespeichert: {local}")
        xml = open(local, encoding="utf-8", errors="replace").read()
        # kompakt: nur klickbare Elemente mit Text/Resource-ID
        hits = re.findall(r'(text|resource-id)="([^"]+)"[^>]*bounds="([^"]+)"', xml)
        ui.info("Elemente (Auszug):")
        for kind, val, bounds in hits[:30]:
            if val:
                print(f"   {ui.GREY}{bounds:<22}{ui.RESET} {kind}={val}")
    else:
        ui.err("Dump fehlgeschlagen.")
    ui.pause()


# ====================================================================== #
#  Kategorie 5 – Datei-Transfer / Medien
# ====================================================================== #
def screenshot(adb: ADB, dev, st) -> None:
    fn = os.path.join(_outdir(), f"screenshot_{int(time.time())}.png")
    rc, out, err = adb.raw(["exec-out", "screencap", "-p"], timeout=30)
    # exec-out liefert binär – über raw geht das nicht sauber; daher direkt streamen:
    cmd = [adb.bin] + (["-s", adb.serial] if adb.serial else []) + ["exec-out", "screencap", "-p"]
    try:
        with open(fn, "wb") as f:
            p = subprocess.run(cmd, stdout=f, timeout=30)
        if p.returncode == 0 and os.path.getsize(fn) > 0:
            ui.ok(f"Screenshot gespeichert: {fn}")
        else:
            ui.err("Screenshot fehlgeschlagen.")
    except Exception as e:  # noqa: BLE001
        ui.err(str(e))
    ui.pause()


def screenrecord(adb: ADB, dev, st) -> None:
    secs = as_int(ui.ask("Aufnahmedauer in Sekunden", "10"), 10, lo=1, hi=180)
    remote = "/sdcard/panzer_rec.mp4"
    ui.info(f"Nehme {secs}s auf … (am Gerät passiert die Aufnahme)")
    adb.shell(f"screenrecord --time-limit {secs} {remote}", timeout=secs + 15)
    local = os.path.join(_outdir(), f"screenrec_{int(time.time())}.mp4")
    adb.raw(["pull", remote, local], timeout=60)
    adb.shell(f"rm {remote}")
    ui.ok(f"Video gespeichert: {local}") if os.path.isfile(local) else ui.err("Aufnahme fehlgeschlagen.")
    ui.pause()


def pull_files(adb: ADB, dev, st) -> None:
    remote = ui.ask("Pfad auf dem Gerät (z.B. /sdcard/DCIM)")
    if not remote:
        return
    local = ui.ask("Zielordner am PC", _outdir())
    os.makedirs(local, exist_ok=True)
    rc, out, err = adb.raw(["pull", remote, local], timeout=600)
    ui.pager((out + "\n" + err).strip() or "fertig", "adb pull")
    ui.pause()


def push_files(adb: ADB, dev, st) -> None:
    local = ui.ask("Datei/Ordner am PC")
    if not local or not os.path.exists(os.path.expanduser(local)):
        ui.err("Pfad existiert nicht.")
        ui.pause()
        return
    remote = ui.ask("Ziel auf dem Gerät", "/sdcard/")
    rc, out, err = adb.raw(["push", os.path.expanduser(local), remote], timeout=600)
    ui.pager((out + "\n" + err).strip() or "fertig", "adb push")
    ui.pause()


def logcat_crashes(adb: ADB, dev, st) -> None:
    _stream(adb, ["logcat", "-v", "time", "*:E"], "Logcat – Fehler & Crashes (live)",
            grep=r"crash|exception|fatal|anr|error|died")


def logcat_radio(adb: ADB, dev, st) -> None:
    _stream(adb, ["logcat", "-b", "radio", "-v", "time"], "Radio-Logcat (Funk-Aktivität, live)")


def clipboard(adb: ADB, dev, st) -> None:
    ch = ui.menu("Zwischenablage", [("1", "Auslesen"), ("2", "Beschreiben")], back_label="Zurück")
    if ch == "1":
        out = adb.shell("cmd clipboard get 2>/dev/null") or adb.shell("service call clipboard 1")
        ui.pager(out or "(leer/nicht unterstützt)", "Clipboard")
    elif ch == "2":
        t = ui.ask("Neuer Inhalt")
        r = adb.shell(f"cmd clipboard set {shq(t)}")
        ui.info(r or "Gesetzt (falls unterstützt).")
    ui.pause()


def adb_backup(adb: ADB, dev, st) -> None:
    ui.warn("Erstellt ein verschlüsseltes Voll-Backup (am Gerät bestätigen!). Kann lange dauern.")
    if not ui.confirm("Fortfahren?", False):
        return
    fn = os.path.join(_outdir(), f"backup_{int(time.time())}.ab")
    ui.info("Backup läuft – am Gerät bestätigen …")
    adb.raw(["backup", "-apk", "-shared", "-all", "-f", fn], timeout=1800)
    ui.ok(f"Backup: {fn}") if os.path.isfile(fn) else ui.err("Backup fehlgeschlagen.")
    ui.pause()


def reboot_menu(adb: ADB, dev, st) -> None:
    ch = ui.menu("Reboot-Steuerung", [
        ("1", "Normaler Neustart"), ("2", "Recovery"), ("3", "Bootloader/Fastboot"),
        ("4", "Fastbootd (userspace)"), ("5", "Sideload (OTA)"), ("6", "Ausschalten"),
    ], back_label="Zurück")
    mp = {"1": "reboot", "2": "reboot recovery", "3": "reboot bootloader",
          "4": "reboot fastboot", "5": "reboot sideload-auto-reboot", "6": "reboot -p"}
    if ch in mp:
        if ui.confirm(f"'{mp[ch]}' ausführen?", False):
            ui.info(adb.shell(mp[ch]) or "Befehl gesendet.")
    ui.pause()


# ====================================================================== #
#  Kategorie 2 – Apps
# ====================================================================== #
def app_list_export(adb: ADB, dev, st) -> None:
    third = adb.shell("pm list packages -3").replace("package:", "")
    system = adb.shell("pm list packages -s").replace("package:", "")
    body = "=== DRITTANBIETER ===\n" + third + "\n\n=== SYSTEM ===\n" + system
    fn = os.path.join(_outdir(), "apps.txt")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(body)
    ui.show_report(body, "Installierte Apps (Drittanbieter + System)", fn, note="App-Liste")
    ui.pause()


def install_apk(adb: ADB, dev, st) -> None:
    p = ui.ask("Pfad zur APK (oder mehrere durch Leerzeichen für Split-APK)")
    if not p:
        return
    paths = [os.path.expanduser(x) for x in p.split()]
    if any(not os.path.isfile(x) for x in paths):
        ui.err("Mindestens eine Datei existiert nicht.")
        ui.pause()
        return
    args = ["install-multiple", "-r"] + paths if len(paths) > 1 else ["install", "-r", paths[0]]
    rc, out, err = adb.raw(args, timeout=300)
    ui.pager((out + "\n" + err).strip(), "Installation")
    ui.pause()


def uninstall_app(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Paketname (z.B. com.beispiel.app)")
    if not pkg:
        return
    keep = ui.confirm("Datenrest behalten (--keep-data)?", False)
    mode = ui.menu("Modus", [("1", "Deinstallieren"),
                             ("2", "Nur deaktivieren (disable-user)"),
                             ("3", "Für aktuellen User entfernen (Bloatware ohne Root)")],
                   back_label="Zurück")
    if mode == "1":
        args = ["uninstall"] + (["-k"] if keep else []) + [pkg]
        rc, out, err = adb.raw(args)
        ui.info((out + err).strip() or "OK")
    elif mode == "2":
        ui.info(adb.shell(f"pm disable-user --user 0 {shq(pkg)}"))
    elif mode == "3":
        ui.info(adb.shell(f"pm uninstall -k --user 0 {shq(pkg)}"))
    ui.pause()


def app_inspect(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Paketname")
    if not pkg:
        return
    out = []
    out.append("PFAD:        " + adb.shell(f"pm path {shq(pkg)}"))
    out.append("VERSION:     " + adb.shell(f"dumpsys package {shq(pkg)} | grep -E 'versionName|versionCode' | head -2"))
    out.append("INSTALLER:   " + adb.shell(f"pm list packages -i {shq(pkg)}"))
    sig = adb.shell(f"pm dump {shq(pkg)} | grep -iA1 'signatures' | head -3")
    out.append("SIGNATUR:\n" + sig)
    out.append("\n— BERECHTIGUNGEN —\n" + adb.shell(
        f"dumpsys package {shq(pkg)} | grep -E 'permission|granted=' | head -40"))
    out.append("\n— KOMPONENTEN (Activities/Services/Receiver) —\n" + adb.shell(
        f"dumpsys package {shq(pkg)} | grep -E 'Activity|Service|Receiver' | head -40"))
    ui.pager("\n".join(out), f"App-Analyse: {pkg}")
    ui.pause()


def app_permissions(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Paketname")
    if not pkg:
        return
    action = ui.menu("Rechte verwalten", [("1", "Anzeigen"), ("2", "Gewähren"), ("3", "Entziehen")],
                     back_label="Zurück")
    if action == "1":
        ui.pager(adb.shell(f"dumpsys package {shq(pkg)} | grep -E 'permission|granted'"), f"Rechte: {pkg}")
    elif action in ("2", "3"):
        perm = ui.ask("Permission (z.B. android.permission.CAMERA)")
        verb = "grant" if action == "2" else "revoke"
        ui.info(adb.shell(f"pm {verb} {shq(pkg)} {shq(perm)}") or f"{verb} ok")
    ui.pause()


def app_control(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Paketname")
    if not pkg:
        return
    action = ui.menu("App-Steuerung", [
        ("1", "Force-Stop"), ("2", "Daten löschen (pm clear)"),
        ("3", "Starten (Launcher-Intent)"), ("4", "Nutzungsstatistik 24h"),
    ], back_label="Zurück")
    if action == "1":
        ui.info(adb.shell(f"am force-stop {shq(pkg)}") or "gestoppt")
    elif action == "2":
        if ui.confirm(f"Wirklich ALLE Daten von {pkg} löschen?", False):
            ui.info(adb.shell(f"pm clear {shq(pkg)}"))
    elif action == "3":
        ui.info(adb.shell(f"monkey -p {shq(pkg)} -c android.intent.category.LAUNCHER 1"))
    elif action == "4":
        ui.pager(adb.shell(f"dumpsys usagestats | grep -A3 {shq(pkg)} | head -20"), f"Nutzung {pkg}")
    ui.pause()


def deep_link(adb: ADB, dev, st) -> None:
    url = ui.ask("URL / Deep-Link (z.B. https://example.com)")
    if url:
        ui.info(adb.shell(f"am start -a android.intent.action.VIEW -d {shq(url)}"))
    ui.pause()


def fuzz_intents(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Ziel-Paket für Monkey-Fuzzing")
    if not pkg:
        return
    n = ui.ask("Anzahl Zufallsereignisse", "500")
    ui.warn("Sendet zufällige UI-Events an die App (kann sie zum Absturz bringen).")
    if ui.confirm("Starten?", True):
        ui.pager(adb.shell(f"monkey -p {shq(pkg)} --throttle 50 -v {shq(n)}", timeout=120), "Monkey-Fuzzing")
    ui.pause()


# ====================================================================== #
#  Kategorie 17 – Mobilfunk-Zellen-Monitor (moderner CellInfo-Parser)
# ====================================================================== #
_TECH = {"Lte": "LTE", "Nr": "5G-NR", "Gsm": "GSM/2G", "Wcdma": "3G/WCDMA",
         "Tdscdma": "TD-SCDMA", "Cdma": "CDMA"}
_SENTINEL = {"2147483647", "-2147483648", "-1", "", "null"}


def parse_cells(dump: str) -> list[dict]:
    """Zerlegt 'dumpsys telephony.registry' in Zellen (registriert + Nachbarn).
    Robust gegen mBands=[..] (kein Abschneiden mehr am ']')."""
    cells = []
    pat = re.compile(
        r"CellInfo(Lte|Nr|Gsm|Wcdma|Tdscdma|Cdma)\b(.*?)"
        r"(?=CellInfo(?:Lte|Nr|Gsm|Wcdma|Tdscdma|Cdma)\b|\Z)", re.S)
    for m in pat.finditer(dump):
        tech, body = m.group(1), m.group(2)

        def g(*keys, body=body):       # body explizit binden (kein Late-Binding der Schleifenvar)
            for k in keys:
                mm = re.search(rf"\b{k}\s*=\s*(-?\d+)", body)
                if mm and mm.group(1) not in _SENTINEL:
                    return mm.group(1)
            return ""

        mccmnc = re.search(r"mMccMnc\s*=\s*(\d{5,6})", body)
        if mccmnc:
            mcc, mnc = mccmnc.group(1)[:3], mccmnc.group(1)[3:]
        else:
            mcc, mnc = g("mMcc"), g("mMnc")
        bands = re.search(r"mBands\s*=\s*\[([^\]]*)\]", body)
        alpha = re.search(r"mAlphaLong\s*=\s*([^\s,}]+)", body)
        cells.append({
            "tech": _TECH[tech],
            "registered": bool(re.search(r"mRegistered\s*=\s*YES", body)),
            "mcc": mcc, "mnc": mnc, "operator": alpha.group(1) if alpha else "",
            "ci": g("mCi", "mNci", "mCid"),
            "tac": g("mTac", "mLac"),
            "pci": g("mPci", "mPsc"),
            "arfcn": g("mEarfcn", "mNrArfcn", "mArfcn", "mUarfcn", "mChannelNumber"),
            "bands": bands.group(1) if bands else "",
            "rsrp": g("rsrp", "ssRsrp", "mRsrp"),
            "rsrq": g("rsrq", "ssRsrq", "mRsrq"),
            "sinr": g("rssnr", "ssSinr", "mSnr"),
            "rssi": g("rssi", "mRssi", "mDbm"),
            "level": g("mLevel", "level"),
        })
    return cells


def _registered(cells: list[dict]) -> dict | None:
    reg = [c for c in cells if c["registered"]]
    if reg:
        # NR vor LTE bevorzugen (bei NSA sind beide registriert)
        reg.sort(key=lambda c: 0 if c["tech"] == "5G-NR" else 1)
        return reg[0]
    return cells[0] if cells else None


def cell_monitor(adb: ADB, dev, st) -> None:
    ui.clear()
    ui.rule("Forensik · Mobilfunk-Zellen-Monitor (live)", ui.BCYAN)
    op = adb.getprop("gsm.operator.alpha") or adb.getprop("gsm.sim.operator.alpha")
    ui.kv("Netzbetreiber (SIM)", op or "—")
    ui.info("Tech · MCC-MNC · TAC · CI · PCI · Band/EARFCN · RSRP/RSRQ/SINR. STRG+C beendet.\n")
    hdr = (f"{'Zeit':<9}|{'Tech':<7}|{'MCC-MNC':<9}|{'TAC':<7}|{'CI':<11}|"
           f"{'PCI':<5}|{'Band':<7}|{'RSRP':<6}|{'RSRQ':<5}|{'SINR':<5}| Status")
    print(f"{ui.BOLD}{hdr}{ui.RESET}")
    print(f"{ui.GREY}{'-'*len(hdr)}{ui.RESET}")
    last_ci = ""
    tick = 0
    try:
        while True:
            dump = adb.shell("dumpsys telephony.registry", timeout=15)
            cells = parse_cells(dump)
            c = _registered(cells)
            ts = time.strftime("%H:%M:%S")
            if not c:
                voice = adb.getprop("gsm.voice.network.type") or "—"
                print(f"{ts:<9}| {ui.BRED}kein CellInfo (Flugmodus/keine SIM/keine Standortrechte){ui.RESET}"
                      f"  {ui.GREY}voice-net={voice}{ui.RESET}")
                time.sleep(4); tick += 1; continue
            band = f"[{c['bands']}]" if c["bands"] else (c["arfcn"] or "—")
            status = f"{ui.BGREEN}🟢 OK{ui.RESET}"
            if last_ci and c["ci"] and c["ci"] != last_ci:
                status = f"{ui.BYELLOW}🟡 Zellenwechsel{ui.RESET}"
            if c["tech"] in ("GSM/2G",):
                status = ui.pulse("⚠️ 2G – unsicher/Downgrade!")
            # Signal-Bewertung (RSRP)
            try:
                rsrp = int(c["rsrp"])
                if rsrp > -50 and c["tech"] != "5G-NR":
                    status = ui.pulse("🚨 Extrem stark – IMSI-Catcher-Verdacht!")
            except (ValueError, TypeError):
                pass
            mm = f"{c['mcc']}-{c['mnc']}" if c["mcc"] else "—"
            print(f"{ts:<9}|{c['tech']:<7}|{mm:<9}|{c['tac'] or '—':<7}|{c['ci'] or '—':<11}|"
                  f"{c['pci'] or '—':<5}|{band[:7]:<7}|{(c['rsrp']+'d') if c['rsrp'] else '—':<6}|"
                  f"{c['rsrq'] or '—':<5}|{c['sinr'] or '—':<5}| {status}")
            if c["ci"]:
                last_ci = c["ci"]
            # alle 5 Ticks Nachbarzellen einblenden
            tick += 1
            if tick % 5 == 0:
                nb = [x for x in cells if not x["registered"]]
                if nb:
                    print(f"   {ui.GREY}Nachbarn ({len(nb)}): " +
                          "  ".join(f"{x['tech']}/PCI{x['pci']}/{x['rsrp']}d" for x in nb[:6]) + ui.RESET)
            time.sleep(4)
    except KeyboardInterrupt:
        print()
        ui.ok("Monitor beendet.")
    ui.pause()


def neighbor_cells(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Nachbarzellen-Analyse", ui.CYAN)
    cells = parse_cells(adb.shell("dumpsys telephony.registry", timeout=15))
    if not cells:
        ui.warn("Keine Zellinfos (Flugmodus/keine SIM/Standortrechte nötig).")
        ui.pause(); return
    for c in cells:
        tag = f"{ui.BGREEN}★ REGISTRIERT{ui.RESET}" if c["registered"] else f"{ui.GREY}  Nachbar{ui.RESET}"
        print(f"  {tag}  {ui.BOLD}{c['tech']:<6}{ui.RESET} "
              f"MCC-MNC {c['mcc'] or '?'}-{c['mnc'] or '?'}  "
              f"CI {c['ci'] or '—'}  TAC {c['tac'] or '—'}  PCI {c['pci'] or '—'}  "
              f"Band [{c['bands']}] EARFCN {c['arfcn'] or '—'}  "
              f"RSRP {c['rsrp'] or '—'}dBm RSRQ {c['rsrq'] or '—'} SINR {c['sinr'] or '—'}")
    ui.info(f"\n{len(cells)} Zelle(n) gesamt. Plötzliche Fremd-MCC/MNC oder fehlende Nachbarn → "
            "möglicher IMSI-Catcher.")
    ui.pause()


# ====================================================================== #
#  Kategorie 7 – Netzwerk
# ====================================================================== #
def set_proxy(adb: ADB, dev, st) -> None:
    ch = ui.menu("Globaler Proxy", [("1", "Setzen (host:port)"), ("2", "Entfernen")], back_label="Zurück")
    if ch == "1":
        hp = ui.ask("host:port (z.B. 192.168.1.50:8080)")
        if hp:
            ui.info(adb.shell(f"settings put global http_proxy {shq(hp)}") or f"Proxy gesetzt: {hp}")
            ui.info("Burp/mitmproxy-CA als User-Zertifikat installieren (Menü 9).")
    elif ch == "2":
        adb.shell("settings put global http_proxy :0")
        ui.ok("Proxy entfernt.")
    ui.pause()


def port_forward(adb: ADB, dev, st) -> None:
    ch = ui.menu("Port-Forwarding", [
        ("1", "forward (Gerät→PC, lokaler PC-Port)"),
        ("2", "reverse (PC→Gerät, Gerät nutzt PC-Dienst)"),
        ("3", "Liste anzeigen"), ("4", "Alle entfernen")], back_label="Zurück")
    if ch == "1":
        spec = ui.ask("z.B. tcp:8080 tcp:8080")
        if spec:
            rc, o, e = adb.raw(["forward"] + spec.split())
            ui.info((o + e).strip() or "OK")
    elif ch == "2":
        spec = ui.ask("z.B. tcp:3000 tcp:3000")
        if spec:
            rc, o, e = adb.raw(["reverse"] + spec.split())
            ui.info((o + e).strip() or "OK")
    elif ch == "3":
        rc, o, e = adb.raw(["forward", "--list"])
        rc2, o2, e2 = adb.raw(["reverse", "--list"])
        ui.pager(f"FORWARD:\n{o}\nREVERSE:\n{o2}", "Aktive Weiterleitungen")
    elif ch == "4":
        adb.raw(["forward", "--remove-all"])
        adb.raw(["reverse", "--remove-all"])
        ui.ok("Alle entfernt.")
    ui.pause()


def adb_wifi(adb: ADB, dev, st) -> None:
    ui.info("Aktiviert ADB über WLAN (Port 5555). Danach Kabel abziehbar.")
    ip = adb.shell("ip -f inet addr show wlan0 | grep -o 'inet [0-9.]*' | cut -d' ' -f2")
    adb.raw(["tcpip", "5555"], timeout=10)
    ui.ok(f"ADB-over-WiFi aktiv. Verbinden mit:  adb connect {ip or '<GERÄT-IP>'}:5555")
    ui.pause()


def tcpdump_capture(adb: ADB, dev, st) -> None:
    if not st.get("is_root"):
        ui.warn("Paket-Sniffing per tcpdump benötigt Root (tcpdump-Binary am Gerät).")
        ui.info("Alternativ: globalen Proxy setzen (Menü 7) + mitmproxy/Wireshark am PC.")
        ui.pause()
        return
    secs = ui.ask("Dauer Sekunden", "20")
    remote = "/sdcard/panzer.pcap"
    ui.info("Starte tcpdump (Root) …")
    adb.shell(f"timeout {secs} tcpdump -i any -w {remote}", root=True, timeout=int(secs) + 10)
    local = os.path.join(_outdir(), f"capture_{int(time.time())}.pcap")
    adb.raw(["pull", remote, local], timeout=60)
    ui.ok(f"PCAP: {local}  → in Wireshark öffnen.") if os.path.isfile(local) else ui.err("Fehlgeschlagen.")
    ui.pause()


# ====================================================================== #
#  Kategorie 9 – Security
# ====================================================================== #
def debuggable_scan(adb: ADB, dev, st) -> None:
    ui.info("Scanne installierte Apps auf debuggable-Flag … (kann dauern)")
    pkgs = [l.split(":", 1)[1] for l in adb.shell("pm list packages -3").splitlines() if ":" in l]
    flagged = []
    for p in pkgs:
        d = adb.shell(f"dumpsys package {shq(p)} | grep -m1 'flags=\\['")
        if "DEBUGGABLE" in d:
            flagged.append(p)
    if flagged:
        ui.warn(f"{len(flagged)} debuggable App(s):")
        for p in flagged:
            print(f"   {ui.BYELLOW}•{ui.RESET} {p}")
    else:
        ui.ok("Keine debuggable Drittanbieter-App gefunden.")
    ui.pause()


def install_cert(adb: ADB, dev, st) -> None:
    ui.info("Installiert ein CA-Zertifikat in den User-Store (für SSL-Interception).")
    p = ui.ask("Pfad zur .pem/.crt-Datei am PC")
    if not p or not os.path.isfile(os.path.expanduser(p)):
        ui.err("Datei nicht gefunden.")
        ui.pause()
        return
    adb.raw(["push", os.path.expanduser(p), "/sdcard/panzer_ca.crt"])
    ui.info("Öffne Zertifikats-Installer am Gerät – dort bestätigen.")
    adb.shell("am start -a android.settings.SECURITY_SETTINGS")
    ui.info("Einstellungen → Sicherheit → Verschlüsselung → Zertifikat installieren → /sdcard/panzer_ca.crt")
    if st.get("is_root"):
        if ui.confirm("Alternativ als System-CA installieren (Root)?", False):
            h = adb.shell("openssl x509 -inform PEM -subject_hash_old -in /sdcard/panzer_ca.crt 2>/dev/null | head -1")
            ui.info(f"Hash: {h} – nach /system/etc/security/cacerts/ kopieren (RW-Mount nötig).")
    ui.pause()
