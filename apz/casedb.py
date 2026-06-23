"""PC-seitige Fall-Datenbank (Beweissicherung & Chain-of-Custody).

Alle vom Tool extrahierten Artefakte werden strukturiert auf dem PC in einer
SQLite-Datenbank archiviert – mit SHA-256 je Datensatz und einer
hash-verketteten Chain-of-Custody (manipulationssicher nachvollziehbar).

WICHTIG: Diese DB liegt ausschließlich auf dem PC. Das Beweisgerät wird nur
read-only ausgelesen und NIE beschrieben – so bleibt die Integrität gewahrt.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time

from . import ui
from .adb import ADB
from .dataforensics import _query, _ts
from .util import shq

DB_DIR = os.path.expanduser("~/Schreibtisch/Androidpanzer/cases")


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def _sha_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------- #
#  Schema
# --------------------------------------------------------------------- #
SCHEMA = """
CREATE TABLE IF NOT EXISTS case_info (
    id INTEGER PRIMARY KEY,
    name TEXT, examiner TEXT,
    device_serial TEXT, device_model TEXT,
    created_at TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY,
    case_id INTEGER,
    category TEXT,          -- Anruf | SMS | Konto | Medien | App | ...
    artifact_type TEXT,     -- eingehend | gesendet | installiert | ...
    source_uri TEXT,        -- woher (content://…, dumpsys, Pfad)
    event_time TEXT,        -- Zeitpunkt des Ereignisses (falls bekannt)
    content TEXT,           -- der eigentliche Datensatz
    sha256 TEXT,            -- Integrität dieses Datensatzes
    collected_at TEXT
);
CREATE TABLE IF NOT EXISTS evidence_files (
    id INTEGER PRIMARY KEY,
    case_id INTEGER,
    device_path TEXT, local_path TEXT,
    size INTEGER, sha256 TEXT, collected_at TEXT
);
CREATE TABLE IF NOT EXISTS chain_of_custody (
    id INTEGER PRIMARY KEY,
    case_id INTEGER,
    ts TEXT, actor TEXT, action TEXT, detail TEXT,
    prev_hash TEXT, entry_hash TEXT
);
"""


def _connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.commit()
    return con


# --------------------------------------------------------------------- #
#  Chain-of-Custody (hash-verkettet → tamper-evident)
# --------------------------------------------------------------------- #
def log_custody(con: sqlite3.Connection, case_id: int, action: str, detail: str,
                actor: str = "") -> None:
    cur = con.execute("SELECT entry_hash FROM chain_of_custody WHERE case_id=? ORDER BY id DESC LIMIT 1",
                      (case_id,))
    row = cur.fetchone()
    prev = row[0] if row else "GENESIS"
    ts = _now()
    actor = actor or os.environ.get("USER", "examiner")
    entry_hash = _sha(f"{prev}|{ts}|{actor}|{action}|{detail}")
    con.execute("INSERT INTO chain_of_custody(case_id,ts,actor,action,detail,prev_hash,entry_hash) "
                "VALUES(?,?,?,?,?,?,?)", (case_id, ts, actor, action, detail, prev, entry_hash))
    con.commit()


# --------------------------------------------------------------------- #
#  Datensätze einfügen
# --------------------------------------------------------------------- #
def add_artifact(con: sqlite3.Connection, case_id: int, category: str, atype: str,
                 source: str, event_time: str, content: str) -> None:
    sha = _sha(f"{category}|{atype}|{source}|{event_time}|{content}")
    con.execute("INSERT INTO artifacts(case_id,category,artifact_type,source_uri,event_time,"
                "content,sha256,collected_at) VALUES(?,?,?,?,?,?,?,?)",
                (case_id, category, atype, source, event_time, content, sha, _now()))


def add_evidence_file(con: sqlite3.Connection, case_id: int, device_path: str, local_path: str) -> str:
    size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
    sha = _sha_file(local_path)
    con.execute("INSERT INTO evidence_files(case_id,device_path,local_path,size,sha256,collected_at) "
                "VALUES(?,?,?,?,?,?)", (case_id, device_path, local_path, size, sha, _now()))
    con.commit()
    return sha


# --------------------------------------------------------------------- #
#  Menü
# --------------------------------------------------------------------- #
def menu(adb: ADB, dev, st, data: dict) -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    while True:
        ui.clear()
        ui.banner(subtitle="📁 Fall-Datenbank & Beweissicherung")
        cases = [f for f in os.listdir(DB_DIR) if f.endswith(".db")]
        ui.kv("Vorhandene Fälle", f"{len(cases)} Fall/Fälle" if cases else "—")
        ch = ui.menu("Aktionen", [
            ("1", "Neuen Fall anlegen"),
            ("2", "Geräte-Artefakte in einen Fall importieren (read-only)"),
            ("3", "Beweisdatei (Pull/Image) registrieren + hashen"),
            ("4", "Integrität & Chain-of-Custody prüfen"),
            ("5", "Fall-Report exportieren (HTML)"),
            ("6", "Artefakte durchsuchen & filtern"),
            ("7", "Fall-Übersicht & Statistik"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        {"1": _new_case, "2": _ingest, "3": _register_file,
         "4": _verify, "5": _report,
         "6": _search, "7": _stats}.get(ch, lambda *a: None)(adb, dev, st, data)


def _pick_case() -> str | None:
    cases = [f for f in os.listdir(DB_DIR) if f.endswith(".db")]
    if not cases:
        ui.warn("Noch kein Fall angelegt."); ui.pause(); return None
    for i, c in enumerate(cases, 1):
        print(f"  {ui.CYAN}{i}{ui.RESET}  {c}")
    sel = ui.ask("Fall-Nr", "1")
    try:
        return os.path.join(DB_DIR, cases[int(sel) - 1])
    except (ValueError, IndexError):
        return None


def _new_case(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Neuen Fall anlegen", ui.CYAN)
    name = ui.ask("Fallname / Aktenzeichen")
    if not name:
        return
    examiner = ui.ask("Bearbeiter", os.environ.get("USER", "examiner"))
    notes = ui.ask("Notiz (optional)")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    path = os.path.join(DB_DIR, f"{safe}.db")
    con = _connect(path)
    con.execute("INSERT INTO case_info(name,examiner,device_serial,device_model,created_at,notes) "
                "VALUES(?,?,?,?,?,?)",
                (name, examiner, data.get("serial", dev.serial),
                 f"{data.get('brand','')} {data.get('model','')}".strip(), _now(), notes))
    con.commit()
    log_custody(con, 1, "CASE_CREATED", f"Fall '{name}' für Gerät {dev.serial} angelegt", examiner)
    con.close()
    ui.ok(f"Fall angelegt: {path}")
    ui.pause()


def _ingest(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Geräte-Artefakte importieren (read-only)", ui.CYAN)
    path = _pick_case()
    if not path:
        return
    con = _connect(path)
    case_id = 1
    log_custody(con, case_id, "INGEST_START", "Read-only Extraktion gestartet")
    total = 0

    ui.info("Anrufe …")
    for r in _query(adb, "content://call_log/calls", projection="number:name:date:duration:type"):
        add_artifact(con, case_id, "Anruf",
                     {"1": "eingehend", "2": "ausgehend", "3": "verpasst"}.get(r.get("type", ""), "?"),
                     "content://call_log/calls", _ts(r.get("date", "")),
                     f"{r.get('number','')} {r.get('name','')} dur={r.get('duration','0')}s")
        total += 1

    ui.info("SMS …")
    for r in _query(adb, "content://sms", projection="address:date:type:body"):
        add_artifact(con, case_id, "SMS", "empfangen" if r.get("type") == "1" else "gesendet",
                     "content://sms", _ts(r.get("date", "")),
                     f"{r.get('address','')}: {r.get('body','')}")
        total += 1

    ui.info("Medien-Index …")
    for label, uri in [("Foto", "content://media/external/images/media"),
                       ("Video", "content://media/external/video/media")]:
        for r in _query(adb, uri, projection="_display_name:date_added:_size:_data"):
            add_artifact(con, case_id, label, "Index", uri, _ts(r.get("date_added", "")),
                         f"{r.get('_data', r.get('_display_name',''))} size={r.get('_size','')}")
            total += 1

    ui.info("Konten …")
    accs = adb.shell("dumpsys account")
    for nm, tp in re.findall(r"Account\s*\{name=([^,]+),\s*type=([^}]+)\}", accs):
        add_artifact(con, case_id, "Konto", "aktiv", "dumpsys account", "", f"{nm} ({tp})")
        total += 1

    ui.info("Installierte Apps (Install-/Update-Zeit) …")
    for p in [l.split(":", 1)[1] for l in adb.shell("pm list packages -3").splitlines() if ":" in l]:
        info = adb.shell(f"dumpsys package {shq(p)} | grep -E 'firstInstallTime|lastUpdateTime'")
        fi = re.search(r"firstInstallTime=([\d-]+ [\d:]+)", info)
        add_artifact(con, case_id, "App", "installiert", "dumpsys package",
                     fi.group(1) if fi else "", p)
        total += 1

    con.commit()
    log_custody(con, case_id, "INGEST_DONE", f"{total} Artefakte importiert (je mit SHA-256)")
    con.close()
    ui.ok(f"{total} Artefakte importiert & gehasht → {path}")
    ui.pause()


def _register_file(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Beweisdatei registrieren", ui.CYAN)
    path = _pick_case()
    if not path:
        return
    local = ui.ask("Lokale Datei (Pull/Image/Backup am PC)")
    local = os.path.expanduser(local or "")
    if not os.path.isfile(local):
        ui.err("Datei nicht gefunden."); ui.pause(); return
    devpath = ui.ask("Ursprungspfad auf dem Gerät (optional)")
    con = _connect(path)
    sha = add_evidence_file(con, 1, devpath, local)
    log_custody(con, 1, "EVIDENCE_ADDED", f"{os.path.basename(local)} sha256={sha}")
    con.close()
    ui.ok(f"Registriert. SHA-256: {sha}")
    ui.pause()


def _verify(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Integritätsprüfung", ui.CYAN)
    path = _pick_case()
    if not path:
        return
    con = _connect(path)
    # 1) Artefakt-Hashes neu berechnen
    bad = 0
    for row in con.execute("SELECT category,artifact_type,source_uri,event_time,content,sha256 FROM artifacts"):
        recomputed = _sha(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}")
        if recomputed != row[5]:
            bad += 1
    total = con.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    ui.kv("Artefakte", total)
    ui.kv("Hash-Abweichungen", f"{ui.BRED}{bad}{ui.RESET}" if bad else f"{ui.BGREEN}0 – integer{ui.RESET}")

    # 2) Beweisdateien: Datei-Hash neu rechnen
    fbad = 0
    for fid, lp, sha in con.execute("SELECT id,local_path,sha256 FROM evidence_files"):
        if _sha_file(lp) != sha:
            fbad += 1
            print(f"   {ui.BRED}⚠ verändert/fehlt: {lp}{ui.RESET}")
    ui.kv("Beweisdateien geprüft", con.execute("SELECT count(*) FROM evidence_files").fetchone()[0])
    ui.kv("Datei-Abweichungen", f"{ui.BRED}{fbad}{ui.RESET}" if fbad else f"{ui.BGREEN}0{ui.RESET}")

    # 3) Chain-of-Custody verketten prüfen
    prev = "GENESIS"
    chain_ok = True
    for ts, actor, action, detail, ph, eh in con.execute(
            "SELECT ts,actor,action,detail,prev_hash,entry_hash FROM chain_of_custody ORDER BY id"):
        if ph != prev or _sha(f"{ph}|{ts}|{actor}|{action}|{detail}") != eh:
            chain_ok = False
            break
        prev = eh
    ui.kv("Chain-of-Custody", f"{ui.BGREEN}unverändert ✓{ui.RESET}" if chain_ok
          else f"{ui.BRED}MANIPULIERT ✗{ui.RESET}")
    con.close()
    ui.pause()


def _search(adb, dev, st, data) -> None:
    """Artefakte in einem Fall durchsuchen."""
    ui.clear(); ui.rule("🔍 ARTEFAKTE DURCHSUCHEN", ui.CYAN)
    path = _pick_case()
    if not path:
        return
    con = _connect(path)
    term = ui.ask("Suchbegriff (Inhalt / Nummer / App-Name)").strip()
    if not term:
        con.close(); return
    cat_filter = ui.ask("Kategorie-Filter (Anruf/SMS/App/Konto/Medien oder leer = alle)").strip()
    query = "SELECT category,artifact_type,event_time,content,sha256 FROM artifacts WHERE content LIKE ?"
    params = [f"%{term}%"]
    if cat_filter:
        query += " AND category LIKE ?"
        params.append(f"%{cat_filter}%")
    query += " ORDER BY event_time DESC LIMIT 100"
    rows = con.execute(query, params).fetchall()
    con.close()
    print(f"\n  {ui.BOLD}{len(rows)} Treffer für '{term}'{ui.RESET}\n")
    if not rows:
        ui.info("Keine Artefakte gefunden.")
    for cat, atype, ts, content, sha in rows[:50]:
        print(f"  {ui.BCYAN}[{cat}/{atype}]{ui.RESET} {ui.GREY}{ts:19s}{ui.RESET}  {content[:80]}")
        print(f"    {ui.GREY}SHA256: {sha[:32]}…{ui.RESET}")
    if len(rows) > 50:
        ui.info(f"… {len(rows)-50} weitere Treffer nicht angezeigt.")
    ui.pause()


def _stats(adb, dev, st, data) -> None:
    """Fall-Übersicht und Statistik."""
    ui.clear(); ui.rule("📊 FALL-ÜBERSICHT & STATISTIK", ui.CYAN)
    path = _pick_case()
    if not path:
        return
    con = _connect(path)
    ci = con.execute("SELECT name,examiner,device_serial,device_model,created_at,notes FROM case_info LIMIT 1").fetchone()
    if ci:
        print(f"\n  {ui.BOLD}Fall:    {ci[0]}{ui.RESET}")
        print(f"  Bearbeiter: {ci[1]}")
        print(f"  Gerät:      {ci[3]} ({ci[2]})")
        print(f"  Angelegt:   {ci[4]}")
        if ci[5]:
            print(f"  Notiz:      {ci[5]}")
    print()
    # Artefakt-Statistik nach Kategorie
    ui.rule("Artefakte", ui.GREY)
    total = con.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    cats = con.execute("SELECT category, count(*) FROM artifacts GROUP BY category ORDER BY count(*) DESC").fetchall()
    ui.kv("Gesamt-Artefakte", str(total))
    for cat, cnt in cats:
        ui.kv(f"  {cat}", str(cnt))
    # Zeitraum
    oldest = con.execute("SELECT min(event_time) FROM artifacts WHERE event_time != ''").fetchone()[0]
    newest = con.execute("SELECT max(event_time) FROM artifacts WHERE event_time != ''").fetchone()[0]
    if oldest:
        print()
        ui.kv("Ältestes Ereignis", oldest or "?")
        ui.kv("Neuestes Ereignis", newest or "?")
    # Beweisdateien
    nfiles = con.execute("SELECT count(*) FROM evidence_files").fetchone()[0]
    sz = con.execute("SELECT sum(size) FROM evidence_files").fetchone()[0] or 0
    print()
    ui.kv("Beweisdateien", f"{nfiles} Dateien / {sz//1024//1024:.1f} MB total")
    # Chain-of-Custody Einträge
    ncoc = con.execute("SELECT count(*) FROM chain_of_custody").fetchone()[0]
    last_coc = con.execute("SELECT ts,action FROM chain_of_custody ORDER BY id DESC LIMIT 1").fetchone()
    ui.kv("Chain-of-Custody", f"{ncoc} Einträge")
    if last_coc:
        ui.kv("Letzter Eintrag", f"{last_coc[0]} – {last_coc[1]}")
    con.close()
    ui.pause()


def _report(adb, dev, st, data) -> None:
    ui.clear(); ui.rule("Fall-Report exportieren", ui.CYAN)
    path = _pick_case()
    if not path:
        return
    con = _connect(path)
    ci = con.execute("SELECT name,examiner,device_serial,device_model,created_at,notes FROM case_info LIMIT 1").fetchone()
    arts = con.execute("SELECT category,artifact_type,event_time,content,sha256 FROM artifacts ORDER BY event_time").fetchall()
    files = con.execute("SELECT local_path,size,sha256,collected_at FROM evidence_files").fetchall()
    coc = con.execute("SELECT ts,actor,action,detail,entry_hash FROM chain_of_custody ORDER BY id").fetchall()
    con.close()

    def esc(s):
        return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rows = "".join(f"<tr><td>{esc(a[2])}</td><td>{esc(a[0])}</td><td>{esc(a[1])}</td>"
                   f"<td>{esc(a[3])[:120]}</td><td class=h>{a[4][:16]}…</td></tr>" for a in arts)
    frows = "".join(f"<tr><td>{esc(f[0])}</td><td>{f[1]}</td><td class=h>{f[2]}</td><td>{f[3]}</td></tr>" for f in files)
    crows = "".join(f"<tr><td>{esc(c[0])}</td><td>{esc(c[1])}</td><td>{esc(c[2])}</td>"
                    f"<td>{esc(c[3])}</td><td class=h>{c[4][:16]}…</td></tr>" for c in coc)
    html = f"""<html><head><meta charset='utf-8'><style>
    body{{font-family:system-ui;margin:0;background:#fff;color:#111}}
    h1{{background:#1b2230;color:#fff;padding:16px;margin:0}} h2{{padding:8px 16px;background:#eef}}
    table{{border-collapse:collapse;width:100%;font-size:12px}} td,th{{border:1px solid #ddd;padding:5px;text-align:left}}
    .h{{font-family:monospace;color:#666}} .meta td{{border:none}}
    </style></head><body>
    <h1>🛡 Forensik-Fall-Report</h1>
    <table class=meta><tr><td><b>Fall:</b></td><td>{esc(ci[0])}</td><td><b>Bearbeiter:</b></td><td>{esc(ci[1])}</td></tr>
    <tr><td><b>Gerät:</b></td><td>{esc(ci[3])} ({esc(ci[2])})</td><td><b>Angelegt:</b></td><td>{esc(ci[4])}</td></tr>
    <tr><td><b>Notiz:</b></td><td colspan=3>{esc(ci[5])}</td></tr></table>
    <h2>Artefakte ({len(arts)}) – je mit SHA-256</h2>
    <table><tr><th>Zeit</th><th>Kategorie</th><th>Typ</th><th>Inhalt</th><th>SHA-256</th></tr>{rows}</table>
    <h2>Beweisdateien ({len(files)})</h2>
    <table><tr><th>Datei</th><th>Größe</th><th>SHA-256</th><th>Erfasst</th></tr>{frows}</table>
    <h2>Chain-of-Custody ({len(coc)})</h2>
    <table><tr><th>Zeit</th><th>Akteur</th><th>Aktion</th><th>Detail</th><th>Hash</th></tr>{crows}</table>
    </body></html>"""
    out = path.replace(".db", "_report.html")
    open(out, "w", encoding="utf-8").write(html)
    ui.ok(f"Report: {out}")
    ui.info("Öffnen:  xdg-open " + out)
    ui.pause()
