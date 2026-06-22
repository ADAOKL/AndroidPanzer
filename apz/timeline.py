"""Forensische Super-Timeline & Geo-Mapping.

Führt alle Spuren chronologisch zusammen (wie eine Mini-Cellebrite-Timeline):
  Anrufe, SMS, App-Installationen/Updates, Konto-Events, Browser, Medien.
→ Export als CSV + interaktives HTML.

Zusätzlich Geo-Mapping: liest GPS aus Foto-EXIF (eigener Parser, kein Fremdpaket)
und exportiert die Bewegungspunkte als KML für Google Earth/Maps.
"""
from __future__ import annotations

import os
import re
import struct
import time

from . import ui
from .adb import ADB
from .dataforensics import _query, _ts
from .util import shq

OUT = os.path.expanduser("~/Schreibtisch/Androidpanzer/timeline")


def _o() -> str:
    os.makedirs(OUT, exist_ok=True)
    return OUT


def menu(adb: ADB, dev, st) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🗓 Super-Timeline & Geo-Mapping")
        ch = ui.menu("Module", [
            ("1", "Super-Timeline erstellen (alle Spuren → CSV + HTML)"),
            ("2", "Geo-Mapping aus Foto-EXIF → KML (Google Earth)"),
            ("3", "Beides nacheinander"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            build_timeline(adb, dev, st)
        elif ch == "2":
            geo_map(adb, dev, st)
        elif ch == "3":
            build_timeline(adb, dev, st)
            geo_map(adb, dev, st)


# ===================================================================== #
#  Super-Timeline
# ===================================================================== #
def build_timeline(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Super-Timeline", ui.CYAN)
    events: list[tuple[float, str, str, str]] = []  # (epoch, quelle, typ, detail)

    ui.info("Sammle Anrufe …")
    for r in _query(adb, "content://call_log/calls", projection="number:name:date:duration:type"):
        ep = _epoch(r.get("date"))
        if ep:
            tp = {"1": "eingehend", "2": "ausgehend", "3": "verpasst"}.get(r.get("type", ""), "Anruf")
            events.append((ep, "Anruf", tp, f"{r.get('number','')} {r.get('name','')} ({r.get('duration','0')}s)"))

    ui.info("Sammle SMS …")
    for r in _query(adb, "content://sms", projection="address:date:type:body"):
        ep = _epoch(r.get("date"))
        if ep:
            dirn = "empfangen" if r.get("type") == "1" else "gesendet"
            events.append((ep, "SMS", dirn, f"{r.get('address','')}: {(r.get('body','') or '')[:80]}"))

    ui.info("Sammle App-Installationen …")
    pkgs = [l.split(":", 1)[1] for l in adb.shell("pm list packages -3").splitlines() if ":" in l]
    for p in pkgs:
        info = adb.shell(f"dumpsys package {shq(p)} | grep -E 'firstInstallTime|lastUpdateTime'")
        fi = re.search(r"firstInstallTime=([\d-]+ [\d:]+)", info)
        lu = re.search(r"lastUpdateTime=([\d-]+ [\d:]+)", info)
        if fi:
            ep = _epoch_str(fi.group(1))
            if ep:
                events.append((ep, "App", "installiert", p))
        if lu and (not fi or lu.group(1) != fi.group(1)):
            ep = _epoch_str(lu.group(1))
            if ep:
                events.append((ep, "App", "aktualisiert", p))

    ui.info("Sammle Medien …")
    for r in _query(adb, "content://media/external/images/media",
                    projection="_display_name:date_added:_data"):
        ep = _epoch(r.get("date_added"))
        if ep:
            events.append((ep, "Foto", "erstellt", r.get("_data", r.get("_display_name", ""))))
    for r in _query(adb, "content://media/external/video/media",
                    projection="_display_name:date_added:_data"):
        ep = _epoch(r.get("date_added"))
        if ep:
            events.append((ep, "Video", "erstellt", r.get("_data", r.get("_display_name", ""))))

    ui.info("Sammle Konto-Events (Log) …")
    for l in adb.shell("logcat -d -t 3000 | grep -iE 'account.*(add|remove)|GLSUser'").splitlines()[-40:]:
        events.append((time.time(), "Konto", "Event", l[:100]))

    if not events:
        ui.warn("Keine Ereignisse gesammelt (Berechtigungen?)."); ui.pause(); return

    events.sort(key=lambda e: e[0])
    # CSV
    csv = "Zeitstempel;Quelle;Typ;Detail\n" + "\n".join(
        f"{_ts(int(e[0]*1000))};{e[1]};{e[2]};{_csv(e[3])}" for e in events)
    csvp = os.path.join(_o(), f"timeline_{int(time.time())}.csv")
    open(csvp, "w", encoding="utf-8").write(csv)
    # HTML
    htmlp = csvp.replace(".csv", ".html")
    open(htmlp, "w", encoding="utf-8").write(_render_html(events))

    ui.ok(f"{len(events)} Ereignisse in der Timeline")
    ui.ok(f"CSV : {csvp}")
    ui.ok(f"HTML: {htmlp}   (xdg-open zum Öffnen)")
    # Vorschau
    ui.rule("Letzte 12 Ereignisse", ui.GREY)
    for e in events[-12:]:
        col = {"Anruf": ui.CYAN, "SMS": ui.GREEN, "App": ui.YELLOW, "Foto": ui.MAGENTA,
               "Video": ui.MAGENTA, "Konto": ui.BRED}.get(e[1], ui.WHITE)
        print(f"  {ui.GREY}{_ts(int(e[0]*1000))}{ui.RESET} {col}{e[1]:<6}{ui.RESET} {e[2]:<12} {e[3][:60]}")
    print()
    ui.show_report(csv, "Super-Timeline · alle Ereignisse (CSV)", csvp, note="Timeline")
    ui.pause()


def _render_html(events) -> str:
    css = """<style>
    body{background:#11151c;color:#e6e6e6;font-family:system-ui,sans-serif;margin:0;padding:0}
    h1{background:#1b2230;padding:14px;margin:0}
    .f{padding:8px 14px;background:#1b2230;position:sticky;top:0}
    input,select{background:#0c1018;color:#e6e6e6;border:1px solid #2a3344;padding:5px;border-radius:5px}
    table{border-collapse:collapse;width:100%}
    td,th{padding:6px 10px;border-bottom:1px solid #222a36;font-size:13px;text-align:left}
    tr:hover{background:#161c27}
    .Anruf{color:#4fc3f7}.SMS{color:#81c784}.App{color:#ffb74d}.Foto,.Video{color:#ba68c8}.Konto{color:#e57373}
    </style>"""
    rows = []
    for e in events:
        rows.append(f"<tr><td>{_ts(int(e[0]*1000))}</td><td class='{e[1]}'>{e[1]}</td>"
                    f"<td>{e[2]}</td><td>{_esc(e[3])}</td></tr>")
    js = """<script>
    function flt(){var q=document.getElementById('q').value.toLowerCase();
    var s=document.getElementById('s').value;
    document.querySelectorAll('tbody tr').forEach(function(r){
      var t=r.innerText.toLowerCase();var src=r.children[1].innerText;
      r.style.display=(t.includes(q)&&(s==''||src==s))?'':'none';});}
    </script>"""
    return (f"<html><head><meta charset='utf-8'>{css}{js}</head><body>"
            f"<h1>🛡 Forensische Super-Timeline · {len(events)} Ereignisse</h1>"
            "<div class='f'>Filter: <input id='q' onkeyup='flt()' placeholder='Suche…'> "
            "<select id='s' onchange='flt()'><option value=''>Alle</option>"
            "<option>Anruf</option><option>SMS</option><option>App</option>"
            "<option>Foto</option><option>Video</option><option>Konto</option></select></div>"
            "<table><thead><tr><th>Zeit</th><th>Quelle</th><th>Typ</th><th>Detail</th></tr></thead>"
            "<tbody>" + "".join(rows) + "</tbody></table></body></html>")


# ===================================================================== #
#  Geo-Mapping aus Foto-EXIF
# ===================================================================== #
def geo_map(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Geo-Mapping aus Foto-EXIF", ui.CYAN)
    n = ui.ask("Wie viele neueste Fotos prüfen?", "200")
    n = int(n) if n.isdigit() else 200
    rows = _query(adb, "content://media/external/images/media",
                  projection="_data:date_added", sort="date_added DESC")
    paths = [r.get("_data", "") for r in rows if r.get("_data", "").lower().endswith((".jpg", ".jpeg"))][:n]
    if not paths:
        ui.warn("Keine JPG-Pfade aus MediaStore."); ui.pause(); return
    ui.info(f"Lade & prüfe {len(paths)} Fotos auf GPS-EXIF … (kann dauern)")
    tmp = os.path.join(_o(), "_exif_tmp")
    os.makedirs(tmp, exist_ok=True)
    points = []
    for i, rp in enumerate(paths):
        # nur die ersten 64 KB ziehen (EXIF steckt am Dateianfang)
        local = os.path.join(tmp, f"img_{i}.jpg")
        head = adb.shell(f"dd if={shq(rp)} bs=65536 count=1 2>/dev/null | base64", timeout=30)
        try:
            import base64
            open(local, "wb").write(base64.b64decode(head))
        except Exception:  # noqa: BLE001
            continue
        gps = _exif_gps(local)
        os.remove(local)
        if gps:
            lat, lon = gps
            points.append((lat, lon, os.path.basename(rp)))
            print(f"   {ui.BGREEN}●{ui.RESET} {lat:.6f}, {lon:.6f}  {os.path.basename(rp)}")
        if (i + 1) % 25 == 0:
            ui.info(f"… {i+1}/{len(paths)} geprüft, {len(points)} mit GPS")
    try:
        os.rmdir(tmp)
    except OSError:
        pass
    if not points:
        ui.warn("Keine GPS-Daten in den Fotos (oft entfernt/Standort war aus).")
        ui.pause(); return
    kml = _render_kml(points)
    kmlp = os.path.join(_o(), f"locations_{int(time.time())}.kml")
    open(kmlp, "w", encoding="utf-8").write(kml)
    ui.ok(f"{len(points)} GPS-Punkte → {kmlp}")
    ui.info("In Google Earth öffnen oder bei google.com/maps importieren.")
    ui.pause()


def _render_kml(points) -> str:
    pm = []
    for lat, lon, name in points:
        pm.append(f"<Placemark><name>{_esc(name)}</name>"
                  f"<Point><coordinates>{lon},{lat},0</coordinates></Point></Placemark>")
    return ("<?xml version='1.0' encoding='UTF-8'?>"
            "<kml xmlns='http://www.opengis.net/kml/2.2'><Document>"
            "<name>Android Panzer – Foto-Standorte</name>" + "".join(pm) +
            "</Document></kml>")


# ----- Minimaler EXIF-GPS-Parser (reines Python) ---------------------- #
def _exif_gps(path: str):
    """Liest GPS-Koordinaten aus einer JPEG-Datei. Gibt (lat, lon) oder None."""
    try:
        data = open(path, "rb").read()
    except OSError:
        return None
    if data[:2] != b"\xff\xd8":
        return None
    # APP1/Exif-Segment finden
    i = 2
    while i < len(data) - 4:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\x00\x00":
            seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
            tiff = data[i + 10:i + 2 + seg_len]
            return _parse_tiff_gps(tiff)
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if i + 3 >= len(data):
            break
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        i += 2 + seg_len
    return None


def _parse_tiff_gps(tiff: bytes):
    if len(tiff) < 8:
        return None
    bo = "<" if tiff[:2] == b"II" else ">"
    try:
        ifd0_off = struct.unpack(bo + "I", tiff[4:8])[0]
        gps_ifd_off = _find_tag(tiff, ifd0_off, 0x8825, bo)
        if not gps_ifd_off:
            return None
        lat = _gps_coord(tiff, gps_ifd_off, 2, 1, bo)
        lon = _gps_coord(tiff, gps_ifd_off, 4, 3, bo)
        if lat is None or lon is None:
            return None
        return (lat, lon)
    except Exception:  # noqa: BLE001
        return None


def _find_tag(tiff, ifd_off, tag, bo):
    if ifd_off + 2 > len(tiff):
        return None
    count = struct.unpack(bo + "H", tiff[ifd_off:ifd_off + 2])[0]
    for k in range(count):
        e = ifd_off + 2 + k * 12
        if e + 12 > len(tiff):
            break
        t = struct.unpack(bo + "H", tiff[e:e + 2])[0]
        if t == tag:
            return struct.unpack(bo + "I", tiff[e + 8:e + 12])[0]
    return None


def _gps_coord(tiff, gps_ifd, val_tag, ref_tag, bo):
    """Liest GPS-Koordinate (Grad/Min/Sek als 3 Rationals) + Himmelsrichtung."""
    count = struct.unpack(bo + "H", tiff[gps_ifd:gps_ifd + 2])[0]
    val_off = ref = None
    for k in range(count):
        e = gps_ifd + 2 + k * 12
        if e + 12 > len(tiff):
            break
        t = struct.unpack(bo + "H", tiff[e:e + 2])[0]
        if t == val_tag:
            val_off = struct.unpack(bo + "I", tiff[e + 8:e + 12])[0]
        if t == ref_tag:
            ref = tiff[e + 8:e + 9].decode("ascii", "ignore")
    if val_off is None or val_off + 24 > len(tiff):
        return None
    nums = struct.unpack(bo + "IIIIII", tiff[val_off:val_off + 24])
    def rat(n, d):
        return n / d if d else 0
    deg = rat(nums[0], nums[1]) + rat(nums[2], nums[3]) / 60 + rat(nums[4], nums[5]) / 3600
    if ref in ("S", "W"):
        deg = -deg
    return deg


def _epoch(s):
    try:
        v = int(s)
        return v / 1000 if v > 10_000_000_000 else v
    except (TypeError, ValueError):
        return 0


def _epoch_str(s):
    try:
        return time.mktime(time.strptime(s.strip(), "%Y-%m-%d %H:%M:%S"))
    except (ValueError, TypeError):
        return 0


def _csv(s):
    return (s or "").replace(";", ",").replace("\n", " ")


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
