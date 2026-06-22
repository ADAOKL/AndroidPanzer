"""Traffic-Interception – kompletter HTTPS-Klartext jeder App.

Kombiniert:
  • Geräte-Proxy auf den PC (settings put global http_proxy)
  • mitmproxy-CA installieren (User-Store; mit Root auch System-Store)
  • mitmdump im Hintergrund mitschneiden lassen
  • optional Frida-SSL-Unpinning, um Certificate-Pinning zu brechen
  • Flows live anzeigen & als Datei sichern / parsen

Benötigt: mitmproxy (pip install mitmproxy). Für gepinnte Apps zusätzlich Root + Frida.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time

from . import frida_engine, ui
from .adb import ADB
from .util import shq

WORK = os.path.expanduser("~/Schreibtisch/Androidpanzer/traffic")
MITM_CA = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.cer")
MITM_CA_PEM = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.pem")


def _have(bin_: str) -> str | None:
    return shutil.which(bin_)


def _pc_ip(adb: ADB) -> str:
    """Ermittelt die vom Gerät erreichbare PC-IP (Standardroute-Quelladresse)."""
    try:
        out = subprocess.run(["ip", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=5).stdout
        for tok in out.split():
            if tok.count(".") == 3 and tok[0].isdigit():
                # 'src <ip>'
                pass
        import re
        m = re.search(r"src (\d+\.\d+\.\d+\.\d+)", out)
        if m:
            return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    return ""


def _ensure_ca() -> bool:
    if os.path.exists(MITM_CA) or os.path.exists(MITM_CA_PEM):
        return True
    # mitmproxy erzeugt die CA beim ersten Lauf
    if _have("mitmdump"):
        ui.info("Erzeuge mitmproxy-CA (einmaliger Kurzlauf) …")
        try:
            p = subprocess.Popen(["mitmdump", "-q"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            p.terminate()
        except Exception:  # noqa: BLE001
            pass
    return os.path.exists(MITM_CA) or os.path.exists(MITM_CA_PEM)


def menu(adb: ADB, dev, st) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🌐 Traffic-Interception (HTTPS-Klartext)")
        ui.kv("mitmproxy (PC)", f"{ui.BGREEN}{_have('mitmdump')}{ui.RESET}" if _have("mitmdump")
              else f"{ui.BRED}fehlt → pip install mitmproxy{ui.RESET}")
        ip = _pc_ip(adb)
        ui.kv("PC-IP (für Proxy)", ip or "unbekannt")
        cur = adb.shell("settings get global http_proxy")
        ui.kv("Aktueller Geräte-Proxy", cur if cur not in ("null", ":0", "") else "—")
        ch = ui.menu("Aktionen", [
            ("1", "Setup: CA installieren + Proxy setzen"),
            ("2", "Mitschnitt starten (live, mit optionalem Frida-Unpin)"),
            ("3", "Gespeicherten Mitschnitt parsen/anzeigen"),
            ("4", "Proxy entfernen (aufräumen)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        {"1": setup, "2": capture, "3": parse_flows, "4": cleanup}.get(ch, lambda *a: None)(adb, dev, st)


def setup(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Setup", ui.CYAN)
    if not _have("mitmdump"):
        ui.err("mitmproxy fehlt:  pip install mitmproxy"); ui.pause(); return
    if not _ensure_ca():
        ui.err("mitmproxy-CA nicht gefunden – starte mitmproxy einmal manuell."); ui.pause(); return
    ip = _pc_ip(adb) or ui.ask("PC-IP manuell eingeben")
    if not ip:
        ui.err("Keine IP."); ui.pause(); return
    # CA aufs Gerät
    ca = MITM_CA_PEM if os.path.exists(MITM_CA_PEM) else MITM_CA
    adb.raw(["push", ca, "/sdcard/mitmproxy-ca.crt"])
    if st.get("is_root"):
        # System-CA installieren (überlebt Pinning auf Apps, die System-CAs trauen)
        h = adb.shell("openssl x509 -inform PEM -subject_hash_old -in /sdcard/mitmproxy-ca.crt 2>/dev/null | head -1").strip()
        if h:
            cert = shq(f"/system/etc/security/cacerts/{h}.0")
            adb.shell(f"mount -o rw,remount /system 2>/dev/null; "
                      f"cp /sdcard/mitmproxy-ca.crt {cert}; chmod 644 {cert}", root=True)
            ui.ok(f"System-CA installiert ({h}.0).")
    else:
        ui.info("CA als /sdcard/mitmproxy-ca.crt abgelegt.")
        adb.shell("am start -a android.settings.SECURITY_SETTINGS")
        ui.info("Am Gerät: Einstellungen → Sicherheit → Zertifikat installieren → CA → mitmproxy-ca.crt")
    # Proxy setzen
    proxy = shq(f"{ip}:8080")
    adb.shell(f"settings put global http_proxy {proxy}")
    ui.ok(f"Geräte-Proxy → {ip}:8080")
    ui.info("Jetzt 'Mitschnitt starten' wählen.")
    ui.pause()


def capture(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Live-Mitschnitt", ui.CYAN)
    if not _have("mitmdump"):
        ui.err("mitmproxy fehlt."); ui.pause(); return
    # Preflight: Gerät MUSS im selben WLAN wie der PC sein (sonst leere Logs!)
    pcip = _pc_ip(adb)
    wifi_ip = adb.shell("ip -f inet addr show wlan0 2>/dev/null | grep -o 'inet [0-9.]*' | cut -d' ' -f2").strip()
    if not wifi_ip:
        ui.err("Gerät ist NICHT im WLAN – der Proxy gilt nur im WLAN.")
        ui.info("Verbinde das Gerät mit DEMSELBEN WLAN wie der PC, dann erneut versuchen.")
        ui.info(f"(PC ist im Netz {pcip.rsplit('.',1)[0]}.x)")
        ui.pause(); return
    same_subnet = pcip and wifi_ip.rsplit(".", 1)[0] == pcip.rsplit(".", 1)[0]
    ui.kv("Geräte-WLAN-IP", wifi_ip)
    ui.kv("PC-IP", pcip)
    if not same_subnet:
        ui.warn(f"Gerät ({wifi_ip}) und PC ({pcip}) scheinen in verschiedenen Netzen – "
                "der Proxy ist evtl. nicht erreichbar.")
        if not ui.confirm("Trotzdem fortfahren?", False):
            return
    # Erreichbarkeit testen (Gerät → PC)
    ping = adb.shell(f"ping -c 1 -W 2 {shq(pcip)} 2>&1")
    if "unreachable" in ping.lower() or "100% packet loss" in ping.lower():
        ui.warn(f"Gerät kann den PC ({pcip}) nicht erreichen (Ping fehlgeschlagen).")
        if not ui.confirm("Trotzdem fortfahren?", False):
            return
    else:
        ui.ok(f"Gerät erreicht den PC ({pcip}) ✓")

    # Vorab-Checks gegen "leere Logs"
    ca_ok = "mitmproxy-ca" in adb.shell("ls /sdcard/ 2>/dev/null") or \
            os.path.exists(MITM_CA) or os.path.exists(MITM_CA_PEM)
    if not ca_ok:
        ui.warn("mitmproxy-CA noch nicht eingerichtet → HTTPS-Apps werden die Verbindung ablehnen.")
        ui.info("Empfehlung: erst Menü 1 (Setup) ausführen. HTTP wird trotzdem mitgeschnitten.")
        if not ui.confirm("Trotzdem aufzeichnen?", True):
            return
    os.makedirs(WORK, exist_ok=True)
    flowfile = os.path.join(WORK, f"flows_{int(time.time())}.mitm")

    # Optional Frida-Unpin für gepinnte App
    if st.get("is_root") and ui.confirm("Frida-SSL-Unpinning für eine App starten (gegen Pinning)?", False):
        pkg = ui.ask("Ziel-Paket")
        if pkg and frida_engine.ensure_server(adb, st):
            ui.info("Starte Unpin-Hook im Hintergrund (läuft, solange du interagierst).")
            # im Hintergrund attached lassen
            import threading
            threading.Thread(target=frida_engine.run_script,
                             args=(adb, pkg, frida_engine.SCRIPTS["ssl-unpin"][1], 600, True),
                             daemon=True).start()
            time.sleep(2)

    # WICHTIG: auf 0.0.0.0 lauschen, sonst kann das Handy im WLAN den Proxy NICHT erreichen
    ip = _pc_ip(adb)
    cur_proxy = adb.shell("settings get global http_proxy")
    if ip and (not cur_proxy or cur_proxy in ("null", ":0", "")):
        proxy = shq(f"{ip}:8080")
        adb.shell(f"settings put global http_proxy {proxy}")
        ui.ok(f"Geräte-Proxy automatisch gesetzt → {ip}:8080")
    ui.info(f"mitmdump lauscht auf 0.0.0.0:8080 (erreichbar als {ip}:8080) → {flowfile}")
    ui.info("Nutze jetzt Apps am Gerät. Beenden mit STRG+C.\n")
    cmd = ["mitmdump", "--listen-host", "0.0.0.0", "--listen-port", "8080",
           "-w", flowfile, "--set", "console_eventlog_verbosity=info", "--flow-detail", "1"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:  # type: ignore
            print("   " + line.rstrip())
    except KeyboardInterrupt:
        pass
    finally:
        try:
            proc.terminate(); proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            pass
    ui.ok(f"Mitschnitt gesichert: {flowfile}")
    ui.info("Mit Option 3 parsen oder im mitmweb/Wireshark öffnen.")
    ui.pause()


def parse_flows(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Mitschnitt parsen", ui.CYAN)
    if not os.path.isdir(WORK):
        ui.warn("Noch kein Mitschnitt vorhanden."); ui.pause(); return
    flows = sorted(f for f in os.listdir(WORK) if f.endswith(".mitm"))
    if not flows:
        ui.warn("Keine .mitm-Dateien."); ui.pause(); return
    for i, f in enumerate(flows, 1):
        print(f"  {ui.CYAN}{i}{ui.RESET}  {f}")
    sel = ui.ask("Datei-Nr", str(len(flows)))
    try:
        ff = os.path.join(WORK, flows[int(sel) - 1])
    except (ValueError, IndexError):
        return
    # Übersicht: Methode + Host + Pfad + Status
    script = os.path.join(WORK, "_dump.py")
    open(script, "w").write(
        "def response(flow):\n"
        "    print(f'{flow.request.method:6} {flow.response.status_code} "
        "{flow.request.pretty_host}{flow.request.path}')\n")
    out = subprocess.run(["mitmdump", "-nr", ff, "-s", script, "-q"],
                         capture_output=True, text=True, timeout=120).stdout
    ui.pager(out or "(leer)", os.path.basename(ff))
    txt = os.path.join(WORK, os.path.basename(ff) + ".txt")
    open(txt, "w").write(out)
    ui.ok(f"Übersicht gespeichert: {txt}")
    ui.pause()


def cleanup(adb: ADB, dev, st) -> None:
    adb.shell("settings put global http_proxy :0")
    ui.ok("Geräte-Proxy entfernt.")
    if st.get("is_root") and ui.confirm("System-CA wieder entfernen?", False):
        adb.shell("mount -o rw,remount /system; rm -f /system/etc/security/cacerts/*mitmproxy* 2>/dev/null", root=True)
    ui.pause()
