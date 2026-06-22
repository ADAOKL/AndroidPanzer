"""Maximum-Deep-Scan – sammelt das absolute Maximum an Spuren ohne Root.

Jede der 20 Sektionen ist auf Tiefe ausgelegt: pro Punkt werden viele
unabhängige Quellen abgefragt (Content-Provider, dumpsys, appops, netstats,
batterystats, telephony.registry, getprop, /proc, /sys …). Die VOLLE Rohausgabe
jeder Quelle landet in der jeweiligen `deep_*.txt`; am Bildschirm wird ein
Digest gezeigt.

Alles read-only. Wo Android die Shell-UID beschränkt, wird der Mangel benannt
(und auf Root/Root-Arsenal verwiesen) statt Daten zu erfinden.
"""
from __future__ import annotations

import os
import re
import socket
import time
from collections import Counter, defaultdict

from . import ui
from .adb import ADB
from .dataforensics import _query, _ts, _write, OUT
from .util import LOG, shq


def menu(adb: ADB, dev, st) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🧬 Maximum-Deep-Scan")
        ui.kv("Root", f"{ui.BGREEN}ja{ui.RESET}" if st.get("is_root") else f"{ui.GREY}nein{ui.RESET}")
        ch = ui.menu("Sektionen", [
            ("0", f"{ui.BGREEN}{ui.BOLD}⏱ ALLES scannen (Maximum){ui.RESET}"),
            ("1", "🪪 Identität & IDs (Konten, Seriennummern, Geräte-IDs)"),
            ("2", "📶 WLAN-Netze, aktuelle Verbindung & Bluetooth-Pairings"),
            ("3", "📍 Standort (letzte Position, Standort-Apps, GPS)"),
            ("4", "📅 Kalender-Termine"),
            ("5", "⬇ Downloads-Historie"),
            ("6", "🔔 Benachrichtigungs-Snapshot"),
            ("7", "⏳ Detaillierte App-Nutzung (Vordergrundzeiten)"),
            ("8", "🔑 Berechtigungs-Matrix (Kamera/Mikro/SMS/Standort)"),
            ("9", "🛡 Sicherheitslage (Lock/Crypto/ADB-Keys/unbek. Quellen)"),
            ("10", "🌐 Netzwerk-Spuren (ARP/Routen/Verbindungen/VPN)"),
            ("11", "🗑 Hinweise auf gelöschte Daten (MediaStore .trashed/.pending)"),
            ("12", "📡 Funk-Aktivität & Mobilfunk-Historie"),
            ("13", f"{ui.BCYAN}⏱ AKTIVITÄTS-TIMELINE (jedes App-Öffnen mit Uhrzeit){ui.RESET}"),
            ("14", "⌨ Persönliches Wörterbuch (selbst getippte Wörter/Namen)"),
            ("15", "⚙ Alle System-Settings (Secure/Global/System)"),
            ("16", "🔖 Browser-Lesezeichen"),
            ("17", "🩺 Health/Fitness & sensible App-Kategorien"),
            ("18", "🔋 Akku-Verlauf & Wakelock-Verursacher"),
            ("19", f"{ui.BCYAN}🌐 Verbindungs-/Browsing-Analyse (Social/Adult/Tracker){ui.RESET}"),
            ("20", f"{ui.BGREEN}{ui.BOLD}📡 LIVE-Verbindungsüberwachung (Echtzeit){ui.RESET}"),
            ("R", f"{ui.BCYAN}📄 Berichte im Terminal ansehen & exportieren (HTML/JSON/MD){ui.RESET}"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "0":
            run_all(adb, dev, st)
        elif ch == "20":
            connection_monitor_live(adb, dev, st)
        elif ch == "r":
            _view_export_menu(adb, dev, st)
        else:
            fn = {"1": ident, "2": wifi_bt, "3": location, "4": calendar, "5": downloads,
                  "6": notifications, "7": app_usage, "8": perm_matrix, "9": security,
                  "10": network, "11": deleted_hints, "12": radio_history,
                  "13": activity_timeline, "14": dictionary, "15": settings_dump,
                  "16": bookmarks, "17": health_apps, "18": battery_history,
                  "19": connection_analysis}.get(ch)
            if fn:
                ui.clear()
                body = fn(adb, dev, st)
                # Den vollständigen Fund IMMER direkt darunter zeigen …
                print()
                ui.rule("📄 Vollständiger Fund", ui.BGREEN)
                ui.pager(body, "")
                # … danach Ansehen erneut / exportieren anbieten
                _view_export_menu(adb, dev, st, body=body)


def run_all(adb: ADB, dev, st, embedded: bool = False) -> None:
    if not embedded:
        ui.clear(); ui.banner(subtitle="Maximum-Deep-Scan – alle Sektionen")
    steps = [("Identität", ident), ("WLAN/BT", wifi_bt), ("Standort", location),
             ("Kalender", calendar), ("Downloads", downloads), ("Notifications", notifications),
             ("App-Nutzung", app_usage), ("Rechte-Matrix", perm_matrix),
             ("Sicherheit", security), ("Netzwerk", network),
             ("Gelöscht-Hinweise", deleted_hints), ("Funk", radio_history),
             ("Aktivitäts-Timeline", activity_timeline), ("Wörterbuch", dictionary),
             ("Settings", settings_dump), ("Lesezeichen", bookmarks),
             ("Health/Apps", health_apps), ("Akku-Verlauf", battery_history),
             ("Verbindungen", connection_analysis)]
    LOG.info("Maximum-Deep-Scan gestartet")
    ui.scan_overview([n for n, _ in steps], "Maximum-Deep-Scan – Bereiche")
    bodies = []
    total = len(steps)
    for i, (name, fn) in enumerate(steps, 1):
        ui.scan_start(i, total, name)
        try:
            body = fn(adb, dev, st, _auto=True)
            bodies.append(f"\n{'='*74}\n# {name}\n{'='*74}\n{body}")
            ui.scan_done(i, total, name, ok=True, note=f"{len(body.splitlines())} Zeilen")
            LOG.info(f"Deep-Sektion ok: {name}")
        except Exception as e:  # noqa: BLE001
            ui.scan_done(i, total, name, ok=False, note=str(e)[:40])
            LOG.exception(f"Deep-Sektion fehlgeschlagen: {name}", e)
    # Kombinierten Gesamtbericht schreiben
    combined = (f"# ANDROID PANZER · MAXIMUM-DEEP-SCAN · {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                + "\n".join(bodies))
    _write("deep_GESAMTBERICHT.txt", combined)
    ui.ok(f"Maximum-Scan fertig. {len(bodies)} Sektionen · Berichte unter: {OUT}")
    if not embedded:
        ui.info("Gesamtbericht: deep_GESAMTBERICHT.txt")
        _view_export_menu(adb, dev, st, body=combined)


# --------------------------------------------------------------------- #
#  Helfer
# --------------------------------------------------------------------- #
def _sh(adb, cmd, t=20):
    return adb.shell(cmd, timeout=t)


def _ok(v) -> str:
    """Bereinigt eine Ausgabe; '' wenn leer/Fehler/null."""
    v = (v or "").strip()
    low = v.lower()
    if not v or low in ("null", "none") or low.startswith(
            ("error", "exception", "permission denial", "securityexception", "no such")):
        return ""
    return v


def _section(name, lines, _auto):
    body = "\n".join(str(x) for x in lines)
    p = _write(f"deep_{name}.txt", body)
    if not _auto:
        ui.ok(f"Gespeichert: {p}  ({len(body.splitlines())} Zeilen)")
    return body


def _grab(adb, label, cmd, out, t=20, show=0, _auto=True, color=None):
    """Führt *cmd* aus, hängt die VOLLE Ausgabe (mit Überschrift) an *out* an.
    Zeigt bei Interaktivität die ersten *show* Zeilen. Gibt die Ausgabe zurück ('' bei leer)."""
    o = _ok(adb.shell(cmd, timeout=t))
    if not o:
        return ""
    out.append(f"\n##### {label} #####")
    out.append(o)
    if not _auto:
        ui.info(f"{label}  ({len(o.splitlines())} Z.)")
        for ln in o.splitlines()[:show]:
            print(f"   {(color or ui.GREY)}{ln.strip()[:108]}{ui.RESET}")
    return o


def _kv(out, key, val, _auto, crit=False):
    val = (str(val) if val is not None else "").strip()
    if not val or val.lower() == "null":
        return
    out.append(f"{key}: {val}")
    if not _auto:
        ui.kv(key, ui.pulse(val) if crit else val[:80])


def _imei(adb) -> list[str]:
    """Versucht IMEI/MEID über die iphonesubinfo-Parcel zu dekodieren (oft ab A10 gesperrt)."""
    found = []
    for code in (1, 3, 4):           # Transaktionscodes variieren je Android-Version/Slot
        out = adb.shell(f"service call iphonesubinfo {code} s16 com.android.shell 2>/dev/null") or \
              adb.shell(f"service call iphonesubinfo {code} 2>/dev/null")
        chars = "".join(re.findall(r"'(.*?)'", out or ""))
        digits = re.sub(r"[^0-9]", "", chars)
        if 14 <= len(digits) <= 17 and digits not in found:
            found.append(digits[:16])
    return found


# --------------------------------------------------------------------- #
#  Bericht: im Terminal ansehen & exportieren (HTML/JSON/MD + SHA-256)
# --------------------------------------------------------------------- #
def _device_data(adb, st) -> dict:
    g = adb.getprop
    return {"brand": g("ro.product.brand") or g("ro.product.manufacturer"),
            "model": g("ro.product.model"), "serial": g("ro.serialno"),
            "android": g("ro.build.version.release"), "root": bool(st.get("is_root"))}


def _list_reports() -> list[str]:
    try:
        files = [f for f in os.listdir(OUT) if f.startswith("deep_") and f.endswith(".txt")]
    except OSError:
        return []
    return sorted(files)


def _browse_reports() -> None:
    """Alle Deep-Scan-Berichtsdateien auflisten und einzeln im Pager anzeigen."""
    while True:
        files = _list_reports()
        if not files:
            ui.info("Noch keine Deep-Scan-Berichte vorhanden. Erst eine Sektion/Vollscan ausführen.")
            ui.pause(); return
        ui.clear(); ui.rule("Deep-Scan-Berichte", ui.CYAN)
        entries = []
        for i, f in enumerate(files, 1):
            try:
                n = sum(1 for _ in open(os.path.join(OUT, f), encoding="utf-8"))
            except OSError:
                n = 0
            entries.append((str(i), f"{f:<32} {ui.GREY}{n} Zeilen{ui.RESET}"))
        ch = ui.menu("Datei wählen", entries, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        try:
            f = files[int(ch) - 1]
        except (ValueError, IndexError):
            continue
        try:
            body = open(os.path.join(OUT, f), encoding="utf-8").read()
        except OSError as e:
            ui.err(str(e)); ui.pause(); continue
        ui.pager(body, f)


def _export_reports(adb, st) -> None:
    """Exportiert ALLE Funde (inkl. Deep-Scan) als HTML + Markdown + JSON + SHA-256-Manifest."""
    ui.info("Bündle alle Berichte, berechne Hashes, rendere HTML/JSON/Markdown …")
    try:
        from . import report
        summary = report.generate(_device_data(adb, st), ("html", "md", "json", "manifest"))
    except Exception as e:  # noqa: BLE001
        ui.err(f"Export fehlgeschlagen: {e}")
        LOG.exception("Deep-Scan Export", e)
        ui.pause(); return
    ui.ok(f"{summary['files_total']} Artefakte exportiert:")
    for fmt, path in summary["report_files"].items():
        ui.kv(fmt.upper(), path)
    ui.info("HTML im Browser öffnen, JSON/Markdown weiterverarbeiten – alles unter reports/.")
    ui.pause()


def _view_export_menu(adb, dev, st, body=None) -> None:
    """Interaktiv: aktuellen Bericht im Terminal ansehen, alle Dateien browsen, exportieren."""
    while True:
        opts = []
        if body is not None:
            opts.append(("v", "📖 Diesen Bericht jetzt im Terminal ansehen (Pager)"))
        opts += [
            ("a", "📂 Alle Deep-Scan-Berichte ansehen (Datei wählen)"),
            ("e", f"{ui.BGREEN}📤 Exportieren: HTML + JSON + Markdown + SHA-256-Manifest{ui.RESET}"),
        ]
        ch = ui.menu("Bericht ansehen / exportieren", opts, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "v" and body is not None:
            ui.pager(body, "Vollständiger Bericht")
        elif ch == "a":
            _browse_reports()
        elif ch == "e":
            _export_reports(adb, st)


# ===================================================================== #
#  1 · Identität – Geräte-, Nutzer- & Konto-Identität (maximal)
# ===================================================================== #
def ident(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Identität & IDs", ui.CYAN)
    g = adb.getprop
    out = ["===== GERÄTE-IDENTITÄT ====="]
    base = [
        ("Modell", g("ro.product.model")), ("Marketing-Name", g("ro.product.vendor.marketname")),
        ("Hersteller", g("ro.product.manufacturer")), ("Marke", g("ro.product.brand")),
        ("Codename (device)", g("ro.product.device")), ("Board", g("ro.product.board")),
        ("Plattform/SoC", g("ro.board.platform")), ("Hardware", g("ro.hardware")),
        ("Seriennummer (prop)", g("ro.serialno")),
        ("Seriennummer (live)", _sh(adb, "getprop ro.serialno; settings get global device_name")),
        ("Build-Fingerprint", g("ro.build.fingerprint")), ("Build-ID", g("ro.build.display.id")),
        ("Build-Datum", g("ro.build.date")), ("Build-Typ/Tags", f"{g('ro.build.type')} / {g('ro.build.tags')}"),
        ("Android-Version", f"{g('ro.build.version.release')} (SDK {g('ro.build.version.sdk')})"),
        ("Security-Patch", g("ro.build.version.security_patch")),
        ("Bootloader", g("ro.bootloader")), ("Baseband/Radio", g("gsm.version.baseband")),
        ("Kernel", _sh(adb, "uname -a")),
        ("Android-ID", _sh(adb, "settings get secure android_id")),
        ("Bluetooth-Name", _sh(adb, "settings get secure bluetooth_name")),
        ("Bluetooth-Adresse", _sh(adb, "settings get secure bluetooth_address")),
        ("Gerätename", _sh(adb, "settings get global device_name")),
        ("Zeitzone", g("persist.sys.timezone")), ("Locale", g("persist.sys.locale")),
        ("Uptime / letzter Boot", _sh(adb, "uptime")),
        ("Boot-Grund", g("sys.boot.reason") or g("ro.boot.bootreason")),
    ]
    for k, v in base:
        _kv(out, k, v, _auto)
    # IMEI/MEID
    imeis = _imei(adb)
    if imeis:
        for i, im in enumerate(imeis, 1):
            _kv(out, f"IMEI/MEID #{i}", im, _auto, crit=True)
    else:
        out.append("IMEI/MEID: nicht über Shell lesbar (ab Android 10 privilegiert) → NVRAM/Diag/Root")

    # Hardware-Spezifikation
    out.append("\n===== HARDWARE =====")
    _kv(out, "ABI/Architektur", g("ro.product.cpu.abi") + " | " + g("ro.product.cpu.abilist"), _auto)
    cpu = _sh(adb, "cat /proc/cpuinfo | grep -iE 'Hardware|model name|processor' | sort -u")
    cores = _sh(adb, "cat /proc/cpuinfo | grep -c ^processor")
    _kv(out, "CPU-Kerne", cores, _auto)
    if _ok(cpu):
        out.append("CPU:\n" + cpu)
    mem = _sh(adb, "cat /proc/meminfo | grep -E 'MemTotal|MemAvailable|SwapTotal'")
    if _ok(mem):
        out.append("RAM:\n" + mem)
        if not _auto:
            for l in mem.splitlines():
                print(f"   {ui.GREY}{l.strip()}{ui.RESET}")
    _kv(out, "Bildschirm-Auflösung", _sh(adb, "wm size"), _auto)
    _kv(out, "Bildschirm-Dichte", _sh(adb, "wm density"), _auto)
    _grab(adb, "Speicher (df)", "df -h 2>/dev/null | grep -E 'data|sdcard|/storage' ", out, show=4, _auto=_auto)

    # Nutzerprofile (Haupt/Gast/Arbeit/Klon)
    out.append("\n===== NUTZERPROFILE =====")
    _grab(adb, "Alle Nutzer (dumpsys user)", "dumpsys user | grep -iE 'UserInfo|Created|Last logged|flags|partial' ",
          out, show=8, _auto=_auto)

    # Konten + Authenticator + Sync
    out.append("\n===== KONTEN =====")
    acc = _sh(adb, "dumpsys account")
    accounts = re.findall(r"Account\s*\{name=([^,]+),\s*type=([^}]+)\}", acc)
    seen = set()
    if accounts and not _auto:
        print(f"  {ui.BOLD}Konten:{ui.RESET}")
    for nm, tp in accounts:
        if (nm, tp) in seen:
            continue
        seen.add((nm, tp))
        out.append(f"Konto: {nm}  ({tp})")
        if not _auto:
            print(f"     {ui.BGREEN}●{ui.RESET} {nm}  {ui.GREY}({tp}){ui.RESET}")
    # Authenticator-Apps + letzte Syncs
    _grab(adb, "Authenticator-Dienste", "dumpsys account | grep -iE 'Authenticator|RegisteredServicesCache' | head -n 30",
          out, _auto=_auto)
    _grab(adb, "Letzte Sync-Operationen", "dumpsys content | grep -iE 'authority|Success|periodic' | head -n 40",
          out, _auto=_auto)
    # Google Services Framework ID (für Geräte-Tracking relevant)
    gsf = _query(adb, "content://com.google.android.gsf.gservices", projection="") or []
    if gsf:
        out.append(f"GSF/Gservices-Einträge: {len(gsf)} (Geräte-Tracking-relevant)")
    if not _auto:
        ui.ok(f"{len(seen)} Konto/Konten, {len(imeis)} IMEI, Identität erfasst.")
    return _section("identitaet", out, _auto)


# ===================================================================== #
#  2 · WLAN & Bluetooth (maximal)
# ===================================================================== #
def wifi_bt(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("WLAN-Netze & Bluetooth", ui.CYAN)
    out = ["===== WLAN ====="]
    _kv(out, "WLAN-Status", _sh(adb, "settings get global wifi_on"), _auto)
    _kv(out, "WLAN-MAC", _sh(adb, "cat /sys/class/net/wlan0/address 2>/dev/null"), _auto)
    _kv(out, "WLAN-Land", _sh(adb, "cmd wifi get-country-code 2>/dev/null"), _auto)
    _grab(adb, "Aktuelle Verbindung", "dumpsys wifi | grep -iE 'mWifiInfo|SSID|BSSID|RSSI|Link speed|Frequency|mNetworkInfo' | head -n 12",
          out, show=6, _auto=_auto, color=ui.BCYAN)
    _grab(adb, "IP-Konfiguration (wlan0)", "ip addr show wlan0 2>/dev/null; ip route 2>/dev/null | grep wlan0",
          out, show=4, _auto=_auto)
    sv = _grab(adb, "Gespeicherte WLAN-Netze", "cmd wifi list-networks 2>/dev/null", out, show=20, _auto=_auto, color=ui.BCYAN)
    if not sv:
        out.append("Gespeicherte Netz-Namen nur mit Root (WifiConfigStore.xml) – siehe Root-Arsenal.")
        if not _auto:
            ui.info("Gespeicherte Netze nur mit Root sichtbar (WifiConfigStore.xml).")
    _grab(adb, "Netze in Reichweite (Scan)", "cmd wifi list-scan-results 2>/dev/null", out, show=10, _auto=_auto)
    _grab(adb, "Hotspot/Tethering-Konfiguration", "dumpsys wifi | grep -iE 'SoftAp|tether|ap_ssid' | head -n 10", out, _auto=_auto)
    _grab(adb, "Bekannte WLAN-Verbindungs-Historie", "dumpsys wifi | grep -iE 'Connection events|connected to|disconnect' | tail -n 20", out, _auto=_auto)

    out.append("\n===== BLUETOOTH =====")
    _kv(out, "BT-Status", _sh(adb, "settings get global bluetooth_on"), _auto)
    _grab(adb, "Gekoppelte Geräte (bonded)",
          "dumpsys bluetooth_manager | grep -iE 'Bonded|Device|address|name:|class|bondState|connected' | head -n 40",
          out, show=12, _auto=_auto, color=ui.BCYAN)
    _grab(adb, "BT-Scan/Discovery-Historie", "dumpsys bluetooth_manager | grep -iE 'Discovery|scan|Inquiry' | head -n 15", out, _auto=_auto)

    out.append("\n===== NFC / NETZWERK-POLICY =====")
    _kv(out, "NFC", _sh(adb, "dumpsys nfc | grep -iE 'mState' | head -n 1"), _auto)
    _kv(out, "Data Saver", _sh(adb, "cmd netpolicy get restrict-background 2>/dev/null"), _auto)
    if not _auto:
        ui.ok("WLAN/Bluetooth/NFC erfasst.")
    return _section("wlan_bluetooth", out, _auto)


# ===================================================================== #
#  3 · Standort (maximal)
# ===================================================================== #
def location(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Standort", ui.CYAN)
    out = ["===== STANDORT ====="]
    _kv(out, "Location-Mode", _sh(adb, "settings get secure location_mode"), _auto)
    _kv(out, "Erlaubte Provider", _sh(adb, "settings get secure location_providers_allowed"), _auto)
    loc = _grab(adb, "Letzte bekannte Position (alle Provider)",
                "dumpsys location | grep -iE 'last location|Location\\[|fused|gps|network|passive' | head -n 40",
                out, _auto=_auto)
    coords = re.findall(r"(-?\d{1,3}\.\d{4,})\s*,?\s*(-?\d{1,3}\.\d{4,})", loc)
    seen = set()
    for la, lo in coords:
        if (la, lo) in seen:
            continue
        seen.add((la, lo))
        out.append(f"KOORDINATE {la},{lo}  https://maps.google.com/?q={la},{lo}")
        if not _auto:
            print(f"   {ui.BYELLOW}📍 {la}, {lo}{ui.RESET}   {ui.GREY}maps.google.com/?q={la},{lo}{ui.RESET}")
    if not coords and not _auto:
        ui.info("Keine Klartext-Koordinaten im location-Dump.")
    _grab(adb, "Aktive Standort-Anforderungen (welche App, wie oft)",
          "dumpsys location | grep -iE 'request|package|interval|provider' | head -n 40", out, show=10, _auto=_auto)
    _grab(adb, "Geofences", "dumpsys location | grep -iE 'geofence' | head -n 15", out, _auto=_auto)
    _grab(adb, "GNSS/GPS-Status", "dumpsys location | grep -iE 'GnssLocationProvider|satellites|TTFF|gnss' | head -n 15", out, _auto=_auto)
    _grab(adb, "Standort-Nutzung pro App (appops)",
          "dumpsys appops | grep -iE 'Package |COARSE_LOCATION|FINE_LOCATION|MONITOR_LOCATION|time=' | head -n 60",
          out, show=10, _auto=_auto, color=ui.BYELLOW)
    _kv(out, "Mock-Location-App", _sh(adb, "settings get secure mock_location") + " " +
        _sh(adb, "dumpsys appops | grep -B2 MOCK_LOCATION | head -n 3"), _auto)
    if not _auto:
        ui.ok(f"{len(seen)} Koordinate(n), Standort-Quellen erfasst.")
    return _section("standort", out, _auto)


# ===================================================================== #
#  4 · Kalender (maximal)
# ===================================================================== #
def calendar(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Kalender-Termine", ui.CYAN)
    out = ["===== KALENDER ====="]
    cals = _query(adb, "content://com.android.calendar/calendars",
                  projection="_id:calendar_displayName:account_name:account_type:ownerAccount")
    if cals:
        out.append(f"## Kalender ({len(cals)})")
        for c in cals:
            out.append(f"  [{c.get('_id','')}] {c.get('calendar_displayName','')}  "
                       f"<{c.get('account_name','')}> ({c.get('account_type','')})")
        if not _auto:
            ui.info(f"{len(cals)} Kalender ({', '.join(c.get('account_name','') for c in cals[:4])})")
    rows = _query(adb, "content://com.android.calendar/events",
                  projection="title:dtstart:dtend:eventLocation:description:organizer:rrule:allDay")
    if not rows:
        out.append("Termine nicht lesbar (Provider/Permission).")
        if not _auto:
            ui.info("Kalender-Events nicht lesbar (Provider/Permission).")
        return _section("kalender", out, _auto)
    out.append(f"\n## Termine ({len(rows)})")
    for r in sorted(rows, key=lambda x: x.get("dtstart", "") or "", reverse=True)[:120]:
        t = _ts(r.get("dtstart", ""))
        rec = " [↻]" if r.get("rrule") else ""
        line = (f"{t}{rec}  {r.get('title','')}  @{r.get('eventLocation','')}  "
                f"org:{r.get('organizer','')}  {r.get('description','')[:60]}")
        out.append(line)
        if not _auto:
            print(f"   {ui.GREY}{t}{ui.RESET}  {r.get('title','')[:46]}{rec}  {ui.GREY}{r.get('eventLocation','')[:24]}{ui.RESET}")
    # Erinnerungen / Geburtstage
    _grab(adb, "Aufgaben/Reminder (sofern Provider offen)",
          "content query --uri content://com.android.calendar/reminders 2>/dev/null | head -n 30", out, _auto=_auto)
    if not _auto:
        ui.ok(f"{len(rows)} Termine.")
    return _section("kalender", out, _auto)


# ===================================================================== #
#  5 · Downloads (maximal – inkl. herunterladende App & Quell-URL)
# ===================================================================== #
def downloads(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Downloads-Historie", ui.CYAN)
    out = ["===== DOWNLOADS ====="]
    rows = _query(adb, "content://downloads/all_downloads",
                  projection="title:uri:_data:total_bytes:lastmod:status:mediaprovider_uri:"
                             "notificationpackage:description:mimetype:referer") or \
        _query(adb, "content://downloads/my_downloads",
               projection="title:uri:_data:total_bytes:lastmod:mimetype:notificationpackage")
    if rows:
        out.append(f"## Download-Provider ({len(rows)} Einträge)")
        by_app = Counter()
        for r in sorted(rows, key=lambda x: x.get("lastmod", "") or "", reverse=True):
            t = _ts(r.get("lastmod", ""))
            app = r.get("notificationpackage", "") or "?"
            by_app[app] += 1
            sz = r.get("total_bytes", "")
            out.append(f"{t}  [{app}]  {r.get('_data', r.get('title',''))}  "
                       f"{sz}B  {r.get('mimetype','')}  src={r.get('uri','')[:80]}  ref={r.get('referer','')[:60]}")
            if not _auto and len(out) <= 55:
                print(f"   {ui.GREY}{t}{ui.RESET} [{ui.BCYAN}{app.split('.')[-1][:10]}{ui.RESET}] "
                      f"{os.path.basename(r.get('_data','') or r.get('title',''))[:42]}")
        out.append("\n## Downloads pro App")
        for app, n in by_app.most_common():
            out.append(f"  {n:>4}×  {app}")
        if not _auto:
            ui.ok(f"{len(rows)} Downloads von {len(by_app)} App(s).")
    else:
        if not _auto:
            ui.info("Download-Provider leer – nutze Dateisystem-Listing.")
    # Dateisystem-Quellen (mehrere Download-Ordner)
    for d in ("/sdcard/Download", "/sdcard/Bluetooth", "/sdcard/Telegram",
              "/sdcard/Android/data/org.telegram.messenger/files/Telegram"):
        _grab(adb, f"Dateien in {d}", f"ls -la --time-style=long-iso {shq(d)} 2>/dev/null | head -n 60", out, _auto=_auto)
    return _section("downloads", out, _auto)


# ===================================================================== #
#  6 · Notifications (maximal)
# ===================================================================== #
def notifications(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Benachrichtigungs-Snapshot", ui.CYAN)
    out = ["===== BENACHRICHTIGUNGEN ====="]
    nl = _grab(adb, "Aktuelle Notifications (--noredact, Klartext)",
               "dumpsys notification --noredact 2>/dev/null | grep -iE 'pkg=|tickerText|android.text=|android.title=|android.bigText=|when=' | head -n 120",
               out, show=18, _auto=_auto)
    if not nl:
        _grab(adb, "Aktuelle Notifications", "dumpsys notification 2>/dev/null | grep -iE 'pkg=|tickerText|when=' | head -n 60", out, show=12, _auto=_auto)
    _grab(adb, "Notification-Listener (Apps, die ALLE Notifications lesen)",
          "settings get secure enabled_notification_listeners", out, show=4, _auto=_auto, color=ui.BYELLOW)
    _grab(adb, "Notification-Kanäle pro App",
          "dumpsys notification 2>/dev/null | grep -iE 'NotificationChannel|importance' | head -n 60", out, _auto=_auto)
    _grab(adb, "Snoozed / Zen / DND",
          "dumpsys notification 2>/dev/null | grep -iE 'snoozed|mZenMode|interruption' | head -n 20", out, _auto=_auto)
    if not _auto:
        ui.ok("Notification-Snapshot erfasst.")
    return _section("notifications", out, _auto)


# ===================================================================== #
#  7 · App-Nutzung (maximal – Zeit + Starts + letzter Gebrauch + Bucket)
# ===================================================================== #
def app_usage(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Detaillierte App-Nutzung", ui.CYAN)
    raw = _sh(adb, "dumpsys usagestats", t=40)
    out = ["===== APP-NUTZUNG ====="]
    # pro Paket: totalTime + lastTimeUsed + launchCount
    times, last, launches = {}, {}, {}
    cur = None
    for l in raw.splitlines():
        m = re.search(r"package=(\S+)", l)
        if m:
            cur = m.group(1)
        if not cur:
            continue
        tt = re.search(r"totalTime(?:Visible|InForeground)?=(\d+)", l)
        if tt:
            times[cur] = max(times.get(cur, 0), int(tt.group(1)))
        lt = re.search(r"lastTimeUsed=\"?([\d:\-\s]+)", l)
        if lt and lt.group(1).strip():
            last[cur] = lt.group(1).strip()
        lc = re.search(r"(?:appLaunchCount|launchCount)=(\d+)", l)
        if lc:
            launches[cur] = max(launches.get(cur, 0), int(lc.group(1)))
    ranked = sorted(times.items(), key=lambda x: -x[1])
    out.append(f"## Vordergrundzeit / Starts / zuletzt ({len(ranked)} Apps)")
    out.append(f"{'STUNDEN':>9}  {'STARTS':>6}  {'ZULETZT':<19}  PAKET")
    for pkg, ms in ranked[:60]:
        h = ms / 3600000
        out.append(f"{h:9.2f}  {launches.get(pkg,0):>6}  {last.get(pkg,'?'):<19}  {pkg}")
        if not _auto and h > 0:
            print(f"   {ui.BCYAN}{h:7.2f}h{ui.RESET} {ui.GREY}{launches.get(pkg,0):>4}×{ui.RESET}  {pkg}")
    # Standby-Buckets (aktiv/selten/eingeschränkt)
    _grab(adb, "App-Standby-Buckets", "dumpsys usagestats 2>/dev/null | grep -iE 'standby|bucket' | head -n 40", out, _auto=_auto)
    if not _auto:
        ui.ok(f"{len(ranked)} Apps mit Nutzungszeit." if ranked else "Keine usagestats lesbar.")
    return _section("app_nutzung", out, _auto)


# ===================================================================== #
#  8 · Berechtigungs-Matrix (maximal – Rechte + appops + Special Access)
# ===================================================================== #
_WATCH_PERMS = {
    "CAMERA": "Kamera", "RECORD_AUDIO": "Mikrofon", "ACCESS_FINE_LOCATION": "Standort (fein)",
    "ACCESS_BACKGROUND_LOCATION": "Standort (Hintergrund)", "READ_SMS": "SMS lesen",
    "SEND_SMS": "SMS senden", "READ_CONTACTS": "Kontakte", "READ_CALL_LOG": "Anrufliste",
    "READ_PHONE_STATE": "Telefonstatus", "READ_EXTERNAL_STORAGE": "Speicher",
    "MANAGE_EXTERNAL_STORAGE": "Voller Speicherzugriff", "BODY_SENSORS": "Körpersensoren",
    "READ_CALENDAR": "Kalender", "GET_ACCOUNTS": "Konten", "SYSTEM_ALERT_WINDOW": "Overlay",
    "REQUEST_INSTALL_PACKAGES": "App-Installation", "QUERY_ALL_PACKAGES": "App-Liste",
}


def perm_matrix(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Berechtigungs-Matrix (Drittanbieter)", ui.CYAN)
    pkgs = [l.split(":", 1)[1] for l in _sh(adb, "pm list packages -3").splitlines() if ":" in l]
    matrix = {label: [] for label in _WATCH_PERMS.values()}
    out = ["===== BERECHTIGUNGS-MATRIX ====="]
    perapp = []
    for p in pkgs:
        granted = _sh(adb, f"dumpsys package {shq(p)} | grep 'granted=true'", t=15)
        hits = [label for perm, label in _WATCH_PERMS.items() if perm in granted]
        for label in hits:
            matrix[label].append(p)
        if hits:
            perapp.append(f"{p}: {', '.join(hits)}")
    out.append(f"## Pro sensibler Berechtigung ({len(pkgs)} Apps geprüft)")
    for label, apps in matrix.items():
        out.append(f"\n### {label} ({len(apps)})")
        out += [f"  {a}" for a in apps]
        if not _auto and apps:
            col = ui.BRED if label.split()[0] in ("Mikrofon", "Standort", "SMS", "Kamera", "Voller") else ui.BYELLOW
            print(f"   {col}{label:<22}{ui.RESET} {len(apps):>3}: {ui.GREY}{', '.join(a.split('.')[-1] for a in apps[:6])}"
                  f"{' …' if len(apps)>6 else ''}{ui.RESET}")
    out.append("\n## Pro App (sensible Rechte)")
    out += perapp
    # appops: tatsächliche jüngste Nutzung von Kamera/Mikro/Standort (mit Zeit)
    _grab(adb, "appops – jüngste Kamera/Mikro/Standort-Nutzung (mit Zeit)",
          "dumpsys appops | grep -iE 'Package |CAMERA|RECORD_AUDIO|FINE_LOCATION|COARSE_LOCATION|time=' | head -n 120",
          out, show=12, _auto=_auto, color=ui.BYELLOW)
    # Special Access
    out.append("\n===== SPECIAL ACCESS =====")
    _grab(adb, "Device-Admins (volle Geräteverwaltung)", "dumpsys device_policy | grep -iE 'admin=|Active admin|policy' | head -n 25", out, show=6, _auto=_auto, color=ui.BRED)
    _grab(adb, "Accessibility-Dienste (potenzielle Keylogger)", "settings get secure enabled_accessibility_services", out, show=3, _auto=_auto, color=ui.BRED)
    _grab(adb, "Notification-Listener", "settings get secure enabled_notification_listeners", out, show=3, _auto=_auto, color=ui.BYELLOW)
    _grab(adb, "Overlay-Apps (SYSTEM_ALERT_WINDOW)", "dumpsys appops | grep -B1 SYSTEM_ALERT_WINDOW | grep -iE 'Package|allow' | head -n 20", out, _auto=_auto)
    _grab(adb, "Voller Dateizugriff (MANAGE_EXTERNAL_STORAGE)", "dumpsys appops | grep -B1 MANAGE_EXTERNAL_STORAGE | grep -iE 'Package|allow' | head -n 20", out, _auto=_auto)
    _grab(adb, "Usage-Access (GET_USAGE_STATS)", "dumpsys appops | grep -B1 GET_USAGE_STATS | grep -iE 'Package|allow' | head -n 20", out, _auto=_auto)
    _grab(adb, "Akku-Optimierung ausgenommen (Dauerläufer)", "dumpsys deviceidle whitelist 2>/dev/null | head -n 30", out, _auto=_auto)
    if not _auto:
        ui.ok("Rechte-Matrix + appops + Special-Access erstellt.")
    return _section("rechte_matrix", out, _auto)


# ===================================================================== #
#  9 · Sicherheitslage (maximal)
# ===================================================================== #
def security(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Sicherheitslage", ui.CYAN)
    g = adb.getprop
    out = ["===== SICHERHEITSLAGE ====="]
    checks = [
        ("Verschlüsselung", g("ro.crypto.state") + " / " + g("ro.crypto.type")),
        ("Verified-Boot", g("ro.boot.verifiedbootstate")),
        ("Bootloader-Lock", g("ro.boot.flash.locked")),
        ("dm-verity", g("ro.boot.veritymode")),
        ("OEM-Unlock erlaubt", _sh(adb, "settings get global oem_unlock_supported") + " / " + g("sys.oem_unlock_allowed")),
        ("SELinux", _sh(adb, "getenforce")),
        ("Sicherheits-Patch", g("ro.build.version.security_patch")),
        ("Sperrbildschirm (trust)", _sh(adb, "dumpsys trust | grep -iE 'secure|trusted|deviceLocked' | head -n 3")),
        ("Lock-Timeout", _sh(adb, "settings get secure lock_screen_lock_after_timeout")),
        ("Lockscreen-Inhalt sichtbar", _sh(adb, "settings get secure lock_screen_show_notifications")),
        ("Fingerabdruck registriert", _sh(adb, "dumpsys fingerprint | grep -iE 'enrolled|Fingerprint' | head -n 3")),
        ("Gesicht registriert", _sh(adb, "dumpsys face | grep -iE 'enrolled|Face' | head -n 2")),
        ("Unbekannte Quellen (global)", _sh(adb, "settings get secure install_non_market_apps")),
        ("Entwickleroptionen", _sh(adb, "settings get global development_settings_enabled")),
        ("USB-Debugging", _sh(adb, "settings get global adb_enabled")),
        ("WLAN-ADB-Port", _sh(adb, "settings get global adb_wifi_enabled")),
        ("Play-Protect-Verifier", _sh(adb, "settings get global package_verifier_enable")),
        ("Verify-Apps über USB", _sh(adb, "settings get global verifier_verify_adb_installs")),
        ("Always-on VPN", _sh(adb, "settings get global always_on_vpn_app 2>/dev/null")),
        ("Knox-Warranty-Bit", g("ro.boot.warranty_bit") or g("ro.warranty_bit")),
    ]
    for k, v in checks:
        v = (v or "").strip().replace("\n", " ")
        crit = ((k.startswith("Unbekannte Quellen") and v == "1") or
                (k == "WLAN-ADB-Port" and v == "1") or
                (k == "Verschlüsselung" and "unencrypted" in v.lower()) or
                (k == "dm-verity" and "disabled" in v.lower()))
        _kv(out, k, v, _auto, crit=crit)
    # ADB-Keys
    _grab(adb, "Autorisierte ADB-Keys", "cat /data/misc/adb/adb_keys 2>/dev/null", out, _auto=_auto)
    # vom Nutzer hinzugefügte CAs (MITM-Indikator)
    uca = _sh(adb, "ls /data/misc/user/0/cacerts-added 2>/dev/null | wc -l")
    if _ok(uca) and uca.strip().isdigit():
        n = int(uca)
        _kv(out, "Nutzer-hinzugefügte CAs (MITM-Indikator!)", n, _auto, crit=(n > 0))
    else:
        out.append("Nutzer-CAs: Liste nur mit Root (/data/misc/user/0/cacerts-added)")
    _grab(adb, "Device-Admins", "dumpsys device_policy | grep -iE 'admin=|Active admin' | head -n 15", out, show=5, _auto=_auto, color=ui.BRED)
    _grab(adb, "Accessibility-Dienste (Keylogger-Risiko)", "settings get secure enabled_accessibility_services", out, show=3, _auto=_auto, color=ui.BRED)
    _grab(adb, "VPN-Konfiguration aktiv", "dumpsys connectivity | grep -iE 'VPN|tun|always-on' | head -n 8", out, _auto=_auto)
    if not _auto:
        ui.ok("Sicherheitslage erfasst.")
    return _section("sicherheit", out, _auto)


# ===================================================================== #
#  10 · Netzwerk-Spuren (maximal)
# ===================================================================== #
def network(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Netzwerk-Spuren", ui.CYAN)
    out = ["===== NETZWERK ====="]
    _grab(adb, "Schnittstellen (ip addr)", "ip addr 2>/dev/null", out, show=6, _auto=_auto)
    _grab(adb, "Schnittstellen-Statistik", "ip -s link 2>/dev/null | head -n 40", out, _auto=_auto)
    _grab(adb, "Aktive Verbindungen", "ss -tunp 2>/dev/null || netstat -tunp 2>/dev/null", out, show=12, _auto=_auto)
    _grab(adb, "Lauschende Ports (Dienste)", "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null", out, show=8, _auto=_auto, color=ui.BYELLOW)
    _grab(adb, "Routing (IPv4)", "ip route 2>/dev/null", out, show=6, _auto=_auto)
    _grab(adb, "Routing (IPv6)", "ip -6 route 2>/dev/null | head -n 15", out, _auto=_auto)
    _grab(adb, "ARP / Nachbargeräte", "ip neigh 2>/dev/null; cat /proc/net/arp 2>/dev/null", out, show=10, _auto=_auto)
    _grab(adb, "DNS", "getprop | grep -iE 'net.dns'; settings get global private_dns_specifier; settings get global private_dns_mode", out, show=6, _auto=_auto)
    _kv(out, "HTTP-Proxy", _sh(adb, "settings get global http_proxy"), _auto)
    _grab(adb, "VPN/Tunnel", "dumpsys connectivity | grep -iE 'VPN|tun|underlying' | head -n 12", out, _auto=_auto)
    _grab(adb, "Datenverbrauch pro App (netstats, Top)",
          "dumpsys netstats 2>/dev/null | grep -iE 'uid=|rb=|tb=|set=' | head -n 60", out, show=10, _auto=_auto)
    _grab(adb, "Tethering/Hotspot-Clients", "dumpsys connectivity | grep -iE 'tether|downstream' | head -n 10", out, _auto=_auto)
    if not _auto:
        ui.ok("Netzwerk-Spuren erfasst.")
    return _section("netzwerk", out, _auto)


# ===================================================================== #
#  11 · Hinweise auf gelöschte Daten (maximal)
# ===================================================================== #
def deleted_hints(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Hinweise auf gelöschte Daten", ui.CYAN)
    out = ["===== GELÖSCHT/BERGBAR ====="]
    total = 0
    for label, uri in [("Bilder", "content://media/external/images/media"),
                       ("Videos", "content://media/external/video/media"),
                       ("Audio", "content://media/external/audio/media"),
                       ("Downloads", "content://media/external/downloads")]:
        rows = _query(adb, uri, projection="_display_name:_data:is_trashed:is_pending:date_expires:_size")
        trashed = [r for r in rows if r.get("is_trashed") == "1" or r.get("is_pending") == "1"]
        if trashed:
            total += len(trashed)
            out.append(f"\n## Papierkorb/pending {label} – {len(trashed)} bergbar")
            for r in trashed[:40]:
                exp = _ts(r.get("date_expires", "")) if r.get("date_expires") else "?"
                out.append(f"  {r.get('_data', r.get('_display_name',''))}  {r.get('_size','')}B  (läuft ab: {exp})")
            if not _auto:
                ui.warn(f"{label}: {len(trashed)} im Papierkorb/pending (bergbar!)")
    # Dateisystem-Papierkorb (mehrere Hersteller)
    _grab(adb, "Papierkorb-/Trash-Dateien im Speicher",
          "find /sdcard -iname '.trashed-*' -o -iname '*RecycleBin*' -o -path '*/.Trash*' "
          "-o -path '*com.miui.gallery/cache/.trashBin*' 2>/dev/null | head -n 80", out, show=12, _auto=_auto, color=ui.BYELLOW)
    # SQLite WAL/Journal (zugängliche Bereiche) → Hinweis auf carve-bare gelöschte Zeilen
    _grab(adb, "SQLite WAL/Journal (carve-bare gelöschte DB-Zeilen)",
          "find /sdcard -iname '*-wal' -o -iname '*-journal' 2>/dev/null | head -n 40", out, _auto=_auto)
    # Thumbnail-Caches (zeigen gelöschte Bilder als Vorschau)
    _grab(adb, "Thumbnail-Caches (gelöschte Bilder als Vorschau)",
          "ls -la /sdcard/DCIM/.thumbnails /sdcard/.thumbnails 2>/dev/null | head -n 20", out, _auto=_auto)
    if total == 0 and not _auto:
        ui.info("Kein offensichtlicher Papierkorb-Inhalt (echtes Carving: Root-Arsenal).")
    return _section("geloescht_hinweise", out, _auto)


# ===================================================================== #
#  12 · Funk / Mobilfunk-Historie (maximal)
# ===================================================================== #
def radio_history(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Funk- & Mobilfunk-Historie", ui.CYAN)
    g = adb.getprop
    out = ["===== MOBILFUNK ====="]
    for k, key in [("Betreiber", "gsm.operator.alpha"), ("SIM-Betreiber", "gsm.sim.operator.alpha"),
                   ("Netz-Numerisch (MCC+MNC)", "gsm.operator.numeric"), ("Netztyp", "gsm.network.type"),
                   ("Land", "gsm.operator.iso-country"), ("Baseband", "gsm.version.baseband"),
                   ("SIM-Status", "gsm.sim.state"), ("Roaming", "gsm.operator.isroaming"),
                   ("Datenaktivität", "gsm.data.network.type")]:
        _kv(out, k, g(key), _auto)
    # telephony.registry: Zellinfo (Serving + Nachbarn) + Signal
    _grab(adb, "Funkzellen (Serving + Nachbarn) & Signal",
          "dumpsys telephony.registry | grep -iE 'mCellInfo|CellIdentity|mSignalStrength|mCellLocation|rsrp|rsrq|level' | head -n 50",
          out, show=12, _auto=_auto, color=ui.BCYAN)
    _grab(adb, "IMS / VoLTE / VoWiFi",
          "dumpsys telephony.registry | grep -iE 'ims|volte|wifi calling|registration' | head -n 20", out, _auto=_auto)
    _grab(adb, "Anruf-/Datenstatus",
          "dumpsys telephony.registry | grep -iE 'mCallState|mDataConnectionState|mServiceState' | head -n 12", out, _auto=_auto)
    apn = _query(adb, "content://telephony/carriers/preferapn", projection="name:apn:type:mcc:mnc") or \
        _query(adb, "content://telephony/carriers", projection="name:apn:type")
    if apn:
        out.append("\n## APN-Profile")
        for r in apn[:15]:
            out.append(f"  {r.get('name','')}  {r.get('apn','')}  [{r.get('type','')}]  {r.get('mcc','')}{r.get('mnc','')}")
        if not _auto:
            ui.info(f"{len(apn)} APN-Profil(e).")
    _grab(adb, "Radio-Log (letzte Funkereignisse)",
          "logcat -b radio -d -t 300 2>/dev/null | grep -iE 'registered|cell|plmn|handover|rsrp|attach' | tail -n 25", out, _auto=_auto)
    _grab(adb, "Mobile Datennutzung", "dumpsys netstats 2>/dev/null | grep -iE 'mobile|ident=' | head -n 20", out, _auto=_auto)
    if not _auto:
        ui.ok("Funk-/Mobilfunk-Historie erfasst.")
    return _section("funk_historie", out, _auto)


# ===================================================================== #
#  13 · Aktivitäts-Timeline (maximal – Sessions je Tag)
# ===================================================================== #
def activity_timeline(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Aktivitäts-Timeline – jedes App-Öffnen mit Uhrzeit", ui.CYAN)
    raw = _sh(adb, "dumpsys usagestats | grep -E 'type=ACTIVITY_RESUMED|type=MOVE_TO_FOREGROUND|"
                   "type=ACTIVITY_PAUSED|type=ACTIVITY_STOPPED|type=DEVICE_SHUTDOWN|type=DEVICE_STARTUP|"
                   "type=KEYGUARD_HIDDEN|type=SCREEN_INTERACTIVE|type=SCREEN_NON_INTERACTIVE' | tail -n 800", t=45)
    events = []
    for l in raw.splitlines():
        tm = re.search(r'time="([^"]+)"', l)
        pk = re.search(r"package=(\S+)", l)
        ty = re.search(r"type=(\w+)", l)
        if tm:
            events.append((tm.group(1), pk.group(1) if pk else "-", ty.group(1) if ty else "?"))
    out = [f"===== AKTIVITÄTS-TIMELINE ({len(events)} Ereignisse) ====="]
    # Sessions je Tag: erstes/letztes Ereignis = Gerät aktiv von..bis
    by_day = defaultdict(list)
    last_day = ""
    fg = [(t, p) for t, p, ty in events if ty in ("ACTIVITY_RESUMED", "MOVE_TO_FOREGROUND")]
    for t, pkg in fg:
        day = t.split()[0]
        by_day[day].append(t)
        out.append(f"{t}  {pkg}")
        if not _auto:
            if day != last_day:
                print(f"   {ui.BYELLOW}── {day} ──{ui.RESET}")
                last_day = day
            hhmm = t.split()[1][:5] if " " in t else t
            print(f"     {ui.GREY}{hhmm}{ui.RESET}  {pkg}")
    out.append("\n## Geräte-Aktivität pro Tag (erstes → letztes App-Öffnen)")
    def _hms(t):                       # Uhrzeit-Teil robust (Timestamp evtl. ohne Leerzeichen)
        return t.split()[1][:8] if " " in t else t[:8]
    for day in sorted(by_day):
        ts = sorted(by_day[day])
        out.append(f"  {day}:  {_hms(ts[0])} → {_hms(ts[-1])}   ({len(ts)} Starts)")
    top = Counter(p for _, p in fg).most_common(15)
    out.append("\n## Top-Apps nach Öffnungen")
    for pkg, n in top:
        out.append(f"  {n:>4}×  {pkg}")
    # vollständige Roh-Events ebenfalls sichern
    out.append("\n## Alle Event-Typen (roh)")
    out += [f"{t}  {ty:<22}  {p}" for t, p, ty in events]
    if not _auto:
        ui.ok(f"{len(fg)} App-Starts an {len(by_day)} Tag(en).")
    return _section("aktivitaets_timeline", out, _auto)


# ===================================================================== #
#  14 · Persönliches Wörterbuch + Tastatur/Clipboard (maximal)
# ===================================================================== #
def dictionary(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Persönliches Wörterbuch & Eingabe-Spuren", ui.CYAN)
    out = ["===== EINGABE-SPUREN ====="]
    rows = _query(adb, "content://user_dictionary/words", projection="word:frequency:locale:shortcut:appid")
    words = [r.get("word", "") for r in rows if r.get("word")]
    out.append(f"## Benutzer-Wörterbuch ({len(words)})")
    for r in rows:
        out.append(f"  {r.get('word','')}  (freq={r.get('frequency','')}, locale={r.get('locale','')}, "
                   f"shortcut={r.get('shortcut','')})")
    if words and not _auto:
        ui.ok(f"{len(words)} selbst gespeicherte Wörter/Namen:")
        print("   " + ", ".join(words[:50]))
    elif not words and not _auto:
        ui.info("Wörterbuch leer/gesperrt (Lernwörter sonst in der Keyboard-Sandbox → Root).")
    _kv(out, "Standard-Tastatur", _sh(adb, "settings get secure default_input_method"), _auto)
    _grab(adb, "Aktivierte Eingabemethoden", "ime list -s 2>/dev/null", out, show=4, _auto=_auto)
    _grab(adb, "Rechtschreibprüfung", "settings get secure selected_spell_checker", out, _auto=_auto)
    _grab(adb, "Zwischenablage (aktueller Inhalt)", "cmd clipboard get 2>/dev/null", out, show=3, _auto=_auto, color=ui.BYELLOW)
    _grab(adb, "TTS-Engine", "settings get secure tts_default_synth", out, _auto=_auto)
    if not _auto:
        ui.ok("Eingabe-Spuren erfasst.")
    return _section("woerterbuch", out, _auto)


# ===================================================================== #
#  15 · Alle System-Settings + kuratierte forensische Auswertung
# ===================================================================== #
_INTERESTING_SETTINGS = [
    "android_id", "bluetooth_name", "bluetooth_address", "device_name", "default_input_method",
    "location_mode", "location_providers_allowed", "user_setup_complete", "time_zone", "auto_time",
    "auto_time_zone", "wifi_on", "data_roaming", "adb_enabled", "adb_wifi_enabled",
    "development_settings_enabled", "install_non_market_apps", "package_verifier_enable",
    "accessibility_enabled", "enabled_accessibility_services", "enabled_notification_listeners",
    "always_on_vpn_app", "private_dns_mode", "private_dns_specifier", "screen_off_timeout",
    "lock_screen_show_notifications", "default_dns_server", "usb_audio_automatic_routing_disabled",
    "boot_count", "setup_wizard_has_run", "night_display_activated", "assistant",
]


def settings_dump(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("System-Settings (Secure/Global/System)", ui.CYAN)
    out = ["===== SYSTEM-SETTINGS ====="]
    full = {}
    for ns in ("system", "secure", "global"):
        d = _sh(adb, f"settings list {ns}", t=25)
        full[ns] = d
        out.append(f"\n===== {ns.upper()} ({len(d.splitlines())} Einträge) =====\n{d}")
    # kuratierte, forensisch relevante Keys über alle Namespaces hervorheben
    out.append("\n===== FORENSISCH RELEVANTE EINSTELLUNGEN =====")
    if not _auto:
        ui.info("Forensisch relevante Settings:")
    alltext = "\n".join(full.values())
    for key in _INTERESTING_SETTINGS:
        m = re.search(rf"^{re.escape(key)}=(.*)$", alltext, re.M)
        if m and m.group(1).strip() and m.group(1).strip() != "null":
            val = m.group(1).strip()
            out.append(f"  {key} = {val}")
            if not _auto:
                print(f"   {ui.BCYAN}{key}{ui.RESET} = {val[:70]}")
    if not _auto:
        ui.ok(f"Alle Settings gesichert ({sum(len(v.splitlines()) for v in full.values())} Einträge).")
    return _section("settings", out, _auto)


# ===================================================================== #
#  16 · Browser-Lesezeichen + Topsites + Suchverlauf (maximal)
# ===================================================================== #
def bookmarks(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Browser-Lesezeichen & Suchverlauf", ui.CYAN)
    out = ["===== LESEZEICHEN/SUCHE ====="]
    found = 0
    for label, uri, proj in [
        ("Lesezeichen (generisch)", "content://browser/bookmarks", "title:url:created:visits"),
        ("Lesezeichen (Chrome)", "content://com.android.chrome.browser/bookmarks", "title:url"),
        ("Lesezeichen (Samsung)", "content://com.sec.android.app.sbrowser.browser/bookmarks", "title:url"),
        ("Top-Sites/Meistbesucht", "content://browser/searches", "search:date"),
    ]:
        rows = _query(adb, uri, projection=proj)
        if rows:
            out.append(f"\n## {label} ({len(rows)})")
            for r in rows:
                val = r.get("url") or r.get("search") or ""
                if val:
                    out.append(f"  {r.get('title','')}  {val}  {r.get('created','')}{r.get('date','')}")
                    found += 1
                    if not _auto and found <= 40:
                        print(f"   {ui.GREY}{(r.get('title','') or val)[:34]:<34}{ui.RESET} {val[:50]}")
    _kv(out, "Browser-Homepage", _sh(adb, "settings get secure browser_homepage 2>/dev/null"), _auto)
    if found:
        if not _auto:
            ui.ok(f"{found} Lesezeichen/Sucheinträge.")
    else:
        out.append("Keine Lesezeichen via Provider (moderne Browser kapseln sie – mit Root: Bookmarks-DB).")
        if not _auto:
            ui.info("Keine Lesezeichen via Provider – mit Root: Browser-DB (siehe Daten-Forensik/Root).")
    return _section("lesezeichen", out, _auto)


# ===================================================================== #
#  17 · Sensible App-Kategorien (maximal – ganzes App-Inventar klassifiziert)
# ===================================================================== #
_APP_CATEGORIES = {
    "Health/Fitness": ["shealth", "google.android.apps.fitness", "fitbit", "garmin", "strava",
                       "myfitnesspal", "huami", "mi.health", "withings", "samsung.android.app.health"],
    "Banking/Finanz": ["sparkasse", "volksbank", "ing", "dkb", "n26", "revolut", "comdirect",
                       "commerzbank", "deutschebank", "paypal", "trade", "vivid", "c24"],
    "Krypto-Wallet": ["coinbase", "binance", "metamask", "trust", "blockchain", "kraken", "bitpanda", "ledger"],
    "Dating": ["tinder", "bumble", "grindr", "lovoo", "badoo", "okcupid", "happn", "hinge", "feeld"],
    "Messenger (verschlüsselt)": ["signal", "threema", "telegram", "whatsapp", "wire", "session", "wickr"],
    "VPN/Anonymität": ["nordvpn", "expressvpn", "protonvpn", "mullvad", "wireguard", "openvpn", "orbot", "torproject"],
    "Passwort/2FA": ["lastpass", "bitwarden", "1password", "keepass", "authy", "google.android.apps.authenticator",
                     "dashlane", "aegis"],
    "Cloud/Sync": ["dropbox", "google.android.apps.docs", "onedrive", "mega", "pcloud", "nextcloud",
                   "samsung.android.scloud"],
    "Anti-Forensik/Tarnung": ["vault", "calculator.vault", "applock", "hide", "gallerylock", "privatespace",
                              "shelter", "island"],
}


def health_apps(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Sensible App-Kategorien", ui.CYAN)
    out = ["===== SENSIBLE APP-KATEGORIEN ====="]
    pkgs = [l.split(":", 1)[1] for l in _sh(adb, "pm list packages -3").splitlines() if ":" in l]
    cat_hits = defaultdict(list)
    for p in pkgs:
        pl = p.lower()
        for cat, kws in _APP_CATEGORIES.items():
            if any(k in pl for k in kws):
                cat_hits[cat].append(p)
    for cat, kws in _APP_CATEGORIES.items():
        apps = sorted(set(cat_hits.get(cat, [])))
        out.append(f"\n## {cat} ({len(apps)})")
        for p in apps:
            info = _sh(adb, f"dumpsys package {shq(p)} | grep -E 'firstInstallTime|lastUpdateTime'", t=12)
            fi = re.search(r"firstInstallTime=([\d:\- ]+)", info)
            lu = re.search(r"lastUpdateTime=([\d:\- ]+)", info)
            sz = _sh(adb, f"du -sh /sdcard/Android/data/{shq(p)} 2>/dev/null").split()[0:1]
            out.append(f"  {p}  installiert={fi.group(1).strip() if fi else '?'}  "
                       f"aktualisiert={lu.group(1).strip() if lu else '?'}  data={sz[0] if sz else '—'}")
        if not _auto and apps:
            col = ui.BRED if cat in ("Anti-Forensik/Tarnung", "Krypto-Wallet", "Dating") else ui.BYELLOW
            print(f"   {col}{cat:<26}{ui.RESET} {len(apps)}: {ui.GREY}{', '.join(a.split('.')[-1] for a in apps[:5])}{ui.RESET}")
    total = sum(len(v) for v in cat_hits.values())
    out.append(f"\n## App-Inventar gesamt: {len(pkgs)} Drittanbieter-Apps")
    if not _auto:
        ui.ok(f"{total} Apps in sensiblen Kategorien (von {len(pkgs)} Drittanbieter-Apps).")
    return _section("health_apps", out, _auto)


# ===================================================================== #
#  18 · Akku-Verlauf & Wakelocks (maximal – pro App)
# ===================================================================== #
def battery_history(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Akku-Verlauf & Wakelock-Verursacher", ui.CYAN)
    out = ["===== AKKU ====="]
    bat = _sh(adb, "dumpsys battery")
    for k, pat in [("Ladestand", r"level:\s*(\d+)"), ("Skala", r"scale:\s*(\d+)"),
                   ("Temperatur", r"temperature:\s*(\d+)"), ("Spannung", r"voltage:\s*(\d+)"),
                   ("Technologie", r"technology:\s*(\S+)"), ("Ladezyklen", r"[Cc]ycle\s*[Cc]ount:\s*(\d+)")]:
        m = re.search(pat, bat or "")
        if m:
            _kv(out, k, m.group(1), _auto)
    _kv(out, "Geschätzte Kapazität (µAh)", _sh(adb, "cat /sys/class/power_supply/battery/charge_full 2>/dev/null"), _auto)
    _kv(out, "Design-Kapazität (µAh)", _sh(adb, "cat /sys/class/power_supply/battery/charge_full_design 2>/dev/null"), _auto)
    _grab(adb, "Geschätzter Stromverbrauch pro App",
          "dumpsys batterystats --charged 2>/dev/null | grep -iE 'Estimated power|Uid .*: |Computed drain' | head -n 50",
          out, show=12, _auto=_auto, color=ui.BCYAN)
    _grab(adb, "Wakelocks (wer hält das Gerät wach)",
          "dumpsys batterystats 2>/dev/null | grep -iE 'Wake lock|partial wake' | head -n 40", out, show=10, _auto=_auto)
    _grab(adb, "Bildschirm-an-Zeit / Foreground",
          "dumpsys batterystats 2>/dev/null | grep -iE 'Screen on|Foreground activities|Top app' | head -n 20", out, _auto=_auto)
    _grab(adb, "Doze/Idle-Status", "dumpsys deviceidle 2>/dev/null | grep -iE 'mState|mDeepEnabled|Stepped' | head -n 10", out, _auto=_auto)
    _grab(adb, "Lade-/Entlade-Historie", "dumpsys batterystats 2>/dev/null | grep -iE 'Battery History|status=|plug' | head -n 20", out, _auto=_auto)
    if not _auto:
        ui.ok("Akku-Verlauf & Verbraucher erfasst.")
    return _section("akku_verlauf", out, _auto)


# ===================================================================== #
#  19 · Verbindungs-/Browsing-Analyse (maximal)
# ===================================================================== #
_DOMAIN_CATS = {
    "Social Media": ["facebook", "fbcdn", "instagram", "cdninstagram", "twitter", "x.com", "twimg",
                     "tiktok", "snapchat", "linkedin", "pinterest", "reddit", "threads", "mastodon"],
    "Messenger": ["whatsapp", "telegram", "signal", "discord", "messenger", "viber", "wa.me", "threema"],
    "Adult/18+": ["pornhub", "xvideos", "xnxx", "xhamster", "redtube", "youporn", "onlyfans",
                  "brazzers", "chaturbate", "stripchat", "porn", "sex", "adult", "nsfw", "fap"],
    "Dating": ["tinder", "bumble", "grindr", "lovoo", "badoo", "okcupid", "match.com", "happn", "hinge"],
    "Shopping": ["amazon.de", "amazon.com", "amazon.co", "ebay.", "aliexpress", "shein", "otto.de",
                 "zalando", "kaufland", "wish.com", "temu.", "etsy.", "klarna"],
    "Streaming/Media": ["youtube", "ytimg", "googlevideo", "netflix", "nflx", "twitch", "spotify",
                        "disney", "primevideo", "dazn", "vimeo"],
    "Tracker/Werbung": ["doubleclick", "google-analytics", "googlesyndication", "googleadservices",
                        "adservice", "scorecardresearch", "moatads", "criteo", "taboola", "outbrain",
                        "appsflyer", "adjust.com", "branch.io", "facebook.com/tr", "graph.facebook",
                        "crashlytics", "firebase", "amplitude", "mixpanel", "segment.io"],
    "Cloud/CDN": ["googleapis", "gstatic", "cloudfront", "akamai", "fastly", "cloudflare",
                  "amazonaws", "azureedge", "windows.net", "googleusercontent",
                  "1e100.net", "compute.amazonaws", "gvt1.com", "akamaitechnologies"],
    "Banking/Finanzen": ["paypal", "sparkasse", "volksbank", "ing.de", "dkb.de", "n26", "revolut",
                         "comdirect", "commerzbank", "deutsche-bank", "trade", "coinbase", "binance"],
    "E-Mail": ["gmail", "outlook", "googlemail", "mail.google", "protonmail", "gmx", "web.de", "yahoo"],
    "Gaming": ["steam", "epicgames", "playstation", "xbox", "nintendo", "supercell", "riotgames"],
}


def _categorize_domain(host: str) -> str:
    h = host.lower()
    for cat, kws in _DOMAIN_CATS.items():
        if any(k in h for k in kws):
            return cat
    return "Sonstiges"


def connection_analysis(adb, dev, st, _auto=False):
    if not _auto:
        ui.rule("Verbindungs-/Browsing-Analyse", ui.CYAN)
    out = ["===== VERBINDUNGSANALYSE ====="]
    raw = _sh(adb, "ss -tnp 2>/dev/null || netstat -tnW 2>/dev/null || netstat -tn 2>/dev/null", t=20)
    out.append("\n## Rohausgabe Sockets\n" + raw)
    ips = set()
    ip_app = {}
    for l in raw.splitlines():
        pairs = re.findall(r"(\d+\.\d+\.\d+\.\d+):(\d+)", l)
        if len(pairs) >= 2:
            rip = pairs[1][0]
            if not rip.startswith(("127.", "0.0.0.0", "192.168.", "10.", "172.")):
                ips.add(rip)
                am = re.search(r'users:\(\("([\w./]+)"|(\d+)/([\w./]+)', l)
                if am:
                    ip_app[rip] = am.group(1) or am.group(3) or ""
    hosts = set()
    dns_raw = _sh(adb, "dumpsys connectivity 2>/dev/null | grep -oE '[a-z0-9.-]+\\.[a-z]{2,}' | head -n 300")
    for h in dns_raw.split():
        if "." in h and not h.replace(".", "").isdigit():
            hosts.add(h.lower())
    resolved = {}
    for ip in list(ips)[:60]:
        try:
            resolved[ip] = socket.gethostbyaddr(ip)[0]
            hosts.add(resolved[ip].lower())
        except Exception:  # noqa: BLE001
            resolved[ip] = ip
    cats = defaultdict(list)
    for h in sorted(hosts):
        if h.count(".") >= 1 and len(h) > 4:
            cats[_categorize_domain(h)].append(h)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    out.append(f"\n=== Analyse {ts} · {len(ips)} Fremd-IPs · {len(hosts)} Hosts ===")
    if not _auto:
        ui.kv("Aktive Fremd-IPs", len(ips))
        ui.kv("Erkannte Hosts", len(hosts))
    # IP→App→Host
    if ip_app:
        out.append("\n## IP → App")
        for ip, app in ip_app.items():
            out.append(f"  {ip}  {resolved.get(ip,ip)}  [{app}]")
    order = ["Adult/18+", "Dating", "Tracker/Werbung", "Social Media", "Messenger",
             "Shopping", "Banking/Finanzen", "Streaming/Media", "E-Mail", "Gaming",
             "Cloud/CDN", "Sonstiges"]
    seen = set()
    for cat in order + list(cats.keys()):
        if cat in seen or cat not in cats:
            continue
        seen.add(cat)
        domains = sorted(set(cats[cat]))
        label = ui.pulse(f"{cat} ({len(domains)})") if cat in ("Adult/18+", "Dating") \
            else f"{ui.BYELLOW}{cat} ({len(domains)}){ui.RESET}" if cat == "Tracker/Werbung" \
            else f"{ui.BCYAN}{cat} ({len(domains)}){ui.RESET}"
        if not _auto:
            print(f"  {label}")
        out.append(f"\n## {cat} ({len(domains)})")
        for d in domains:
            if not _auto and domains.index(d) < 15:
                print(f"     {ui.GREY}• {d}{ui.RESET}")
            out.append(f"  {d}")
    # Datenverbrauch pro App als zusätzliche Quelle
    _grab(adb, "Datenverbrauch pro App (netstats)",
          "dumpsys netstats 2>/dev/null | grep -iE 'uid=|rb=|tb=' | head -n 40", out, _auto=_auto)
    if not ips and not hosts and not _auto:
        ui.info("Aktuell keine aktiven Fremd-Verbindungen. Für vollständige Domain-Historie: "
                "Root (Browser-DBs/DNS-Cache) oder LIVE-Überwachung (Punkt 20) bei App-Nutzung.")
    elif not _auto:
        ui.ok(f"{len(hosts)} Hosts in {len(seen)} Kategorien analysiert.")
    return _section("verbindungsanalyse", out, _auto)


# ===================================================================== #
#  20 · LIVE-Verbindungsüberwachung
# ===================================================================== #
def connection_monitor_live(adb, dev, st, _auto=False):
    ui.clear()
    ui.banner(subtitle="🌐 LIVE-Verbindungsüberwachung")
    ui.info("Zeigt jede NEUE ausgehende Verbindung des Geräts live, kategorisiert. STRG+C beendet.\n")
    hdr = f"{'Zeit':<9} {'Kategorie':<16} {'Host / IP':<40} App/PID"
    print(f"{ui.BOLD}{hdr}{ui.RESET}")
    print(f"{ui.GREY}{'-'*len(hdr)}{ui.RESET}")
    seen: set = set()
    rev_cache: dict = {}
    logpath = _write("verbindungen_live.txt", f"# Live-Verbindungen ab {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    logf = open(logpath, "a", encoding="utf-8")
    count = 0
    try:
        while True:
            raw = adb.shell("netstat -tnpW 2>/dev/null || netstat -tnp 2>/dev/null || ss -tnp 2>/dev/null", timeout=12)
            for l in raw.splitlines():
                if "ESTABLISHED" not in l and "SYN_SENT" not in l:
                    continue
                pairs = re.findall(r"(\d+\.\d+\.\d+\.\d+):(\d+)", l)
                if len(pairs) < 2:
                    continue
                rip, rport = pairs[1]
                if rip.startswith(("127.", "0.0.0.0", "192.168.", "10.", "172.16.")):
                    continue
                key = f"{rip}:{rport}"
                if key in seen:
                    continue
                seen.add(key)
                pm = re.search(r"(\d+)/([\w./]+)|users:\(\(\"([\w./]+)\",pid=(\d+)", l)
                appinfo = ""
                if pm:
                    appinfo = (pm.group(2) or pm.group(3) or "") + (("/" + (pm.group(1) or pm.group(4))) if (pm.group(1) or pm.group(4)) else "")
                if rip not in rev_cache:
                    try:
                        rev_cache[rip] = socket.gethostbyaddr(rip)[0]
                    except Exception:  # noqa: BLE001
                        rev_cache[rip] = rip
                host = rev_cache[rip]
                cat = _categorize_domain(host)
                ts = time.strftime("%H:%M:%S")
                col = (ui.pulse(cat) if cat in ("Adult/18+", "Dating")
                       else f"{ui.BYELLOW}{cat}{ui.RESET}" if cat == "Tracker/Werbung"
                       else f"{ui.BCYAN}{cat}{ui.RESET}" if cat != "Sonstiges"
                       else f"{ui.GREY}{cat}{ui.RESET}")
                disp = host if host != rip else f"{rip}:{rport}"
                print(f"{ts:<9} {col:<16} {disp[:40]:<40} {ui.GREY}{appinfo}{ui.RESET}")
                logf.write(f"{ts}\t{cat}\t{disp}\t{rip}:{rport}\t{appinfo}\n")
                logf.flush()
                count += 1
            time.sleep(2)
    except KeyboardInterrupt:
        print()
        ui.ok(f"Überwachung beendet. {count} neue Verbindungen erfasst → {logpath}")
        if rev_cache:
            stat = Counter(_categorize_domain(h) for h in rev_cache.values())
            print()
            ui.rule("Zusammenfassung nach Kategorie", ui.YELLOW)
            for cat, n in stat.most_common():
                bar = "█" * min(30, n)
                print(f"  {cat:<16} {ui.BCYAN}{bar}{ui.RESET} {n}")
    finally:
        logf.close()
    if not _auto:
        ui.pause()
