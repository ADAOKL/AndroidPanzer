"""Einheitlicher Forensik-Report & Export über ALLE Ausgabeverzeichnisse.

Fasst die von den einzelnen Modulen erzeugten Artefakte (forensik/, osint/,
timeline/, app_export/, messenger/, traffic/, …) zu einem einzigen, signierten
Gesamtbericht zusammen:

  • HTML   – dunkles, lesbares Layout mit ein-/ausklappbaren Sektionen
  • Markdown – versionierbar / für Berichte
  • JSON   – maschinenlesbar (Weiterverarbeitung, Diffing)
  • MANIFEST.sha256 – SHA-256 jeder Datei (Chain-of-Custody, mit `sha256sum -c` prüfbar)

Liest ausschließlich bereits erzeugte Dateien auf dem PC – greift NICHT erneut
auf das Gerät zu. So bleibt der Bericht reproduzierbar.
"""
from __future__ import annotations

import html
import json
import os
import time

from . import ui
from .util import LOG, BASE, human_size, outdir, sha256_file, sha256_text

# Bekannte Ausgabeverzeichnisse → menschenlesbare Kategorie.
SECTIONS = {
    "forensik_full": "Vollständige forensische Akquise (45-Sektionen-Gesamtbericht)",
    "forensik": "Daten-Forensik (Konten, Anrufe, SMS, Medien, Deep-Scan)",
    "apkscan": "APK-Statik-Analyse · Risiko-Inventar · IOC-Scan",
    "diagnostics": "Root-/Bootloader-Tiefen-Diagnose",
    "app_export": "Exportierte Apps (APK + Metadaten)",
    "messenger": "Messenger-Auswertung",
    "timeline": "Timeline & Geo-Mapping",
    "traffic": "Netzwerk-/Traffic-Mitschnitte",
    "osint": "OSINT-Recherche",
    "phone_osint": "Telefon-OSINT",
    "root_arsenal": "Root-Arsenal (Tiefen-Extraktion/Recovery)",
    "rescue": "Rettungs-/Flash-Protokolle",
    "bootloop": "Bootloop-Monitor",
    "logs": "Lauf-Logs",
}

# Diese Dateiendungen als Text einbetten (Vorschau); alles andere nur als Datei listen.
TEXT_EXT = {".txt", ".csv", ".log", ".json", ".md", ".xml", ".html", ".kml", ".pit", ".sha256"}
PREVIEW_BYTES = 200_000          # max. eingebetteter Textinhalt je Datei
REPORT_DIR = "reports"


# --------------------------------------------------------------------------- #
#  Sammeln
# --------------------------------------------------------------------------- #
def _iter_files(root: str):
    for dirpath, _dirs, files in os.walk(root):
        # Caches/Bytecode überspringen
        if "__pycache__" in dirpath:
            continue
        for fn in sorted(files):
            yield os.path.join(dirpath, fn)


def collect() -> list[dict]:
    """Sammelt alle Artefakt-Dateien aus den bekannten Ausgabeverzeichnissen."""
    items: list[dict] = []
    for sub, label in SECTIONS.items():
        root = os.path.join(BASE, sub)
        if not os.path.isdir(root):
            continue
        for path in _iter_files(root):
            try:
                stat = os.stat(path)
            except OSError as e:
                LOG.exception(f"report: stat {path}", e)
                continue
            ext = os.path.splitext(path)[1].lower()
            rec = {
                "category": label,
                "section": sub,
                "path": path,
                "rel": os.path.relpath(path, BASE),
                "name": os.path.basename(path),
                "size": stat.st_size,
                "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "sha256": "",
                "preview": None,
                "is_text": ext in TEXT_EXT,
            }
            try:
                rec["sha256"] = sha256_file(path)
            except OSError as e:
                LOG.exception(f"report: sha256 {path}", e)
            if rec["is_text"] and stat.st_size <= PREVIEW_BYTES:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        rec["preview"] = f.read()
                except OSError as e:
                    LOG.exception(f"report: read {path}", e)
            items.append(rec)
    return items


def _summary(items: list[dict], data: dict | None) -> dict:
    by_section: dict[str, int] = {}
    total_size = 0
    for it in items:
        by_section[it["section"]] = by_section.get(it["section"], 0) + 1
        total_size += it["size"]
    return {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base": BASE,
        "device": {
            "brand": (data or {}).get("brand", ""),
            "model": (data or {}).get("model", ""),
            "serial": (data or {}).get("serial", ""),
            "android": (data or {}).get("android", ""),
            "root": bool((data or {}).get("root")),
        },
        "files_total": len(items),
        "size_total": total_size,
        "by_section": by_section,
    }


# --------------------------------------------------------------------------- #
#  Renderer
# --------------------------------------------------------------------------- #
def render_json(items: list[dict], summary: dict) -> str:
    payload = {"summary": summary,
               "files": [{k: v for k, v in it.items() if k != "preview"} | {"has_preview": it["preview"] is not None}
                         for it in items]}
    return json.dumps(payload, indent=2, ensure_ascii=False)


def render_markdown(items: list[dict], summary: dict) -> str:
    d = summary["device"]
    out = ["# Android Panzer – Forensik-Report", "",
           f"- **Erstellt:** {summary['generated']}",
           f"- **Gerät:** {d['brand']} {d['model']}  (Serial `{d['serial'] or '—'}`)",
           f"- **Android:** {d['android'] or '—'}  ·  **Root:** {'ja' if d['root'] else 'nein'}",
           f"- **Artefakte:** {summary['files_total']} Dateien · {human_size(summary['size_total'])}",
           ""]
    cur = None
    for it in sorted(items, key=lambda x: (x["section"], x["rel"])):
        if it["category"] != cur:
            cur = it["category"]
            out += ["", f"## {cur}", ""]
        out.append(f"- `{it['rel']}` — {human_size(it['size'])} · {it['mtime']} · "
                   f"sha256 `{it['sha256'][:16]}…`")
    return "\n".join(out) + "\n"


_HTML_HEAD = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Android Panzer – Forensik-Report</title>
<style>
:root{--bg:#120608;--card:#1b0c10;--fg:#ece6e8;--mut:#9a7a82;--neon:#ff1a3c;--ok:#40ff96;--line:#3a141c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 ui-monospace,Menlo,Consolas,monospace}
header{padding:22px 26px;border-bottom:2px solid var(--neon);
background:linear-gradient(180deg,#250a10,#120608)}
h1{margin:0 0 6px;color:var(--neon);letter-spacing:2px}
.meta{color:var(--mut)}.meta b{color:var(--fg)}
.wrap{padding:18px 26px;max-width:1100px;margin:0 auto}
.stat{display:inline-block;margin:0 18px 8px 0}
.stat b{color:var(--neon);font-size:18px}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:10px 0;overflow:hidden}
summary{cursor:pointer;padding:12px 16px;font-weight:bold;color:var(--neon);
list-style:none;display:flex;justify-content:space-between;gap:10px}
summary::-webkit-details-marker{display:none}
summary .c{color:var(--mut);font-weight:normal}
.file{border-top:1px solid var(--line);padding:10px 16px}
.fh{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.fn{color:var(--ok)}.fm{color:var(--mut);font-size:12px}
.sha{color:var(--mut);font-size:11px;word-break:break-all}
pre{background:#0d0406;border:1px solid var(--line);border-radius:6px;padding:10px;
overflow:auto;max-height:420px;white-space:pre-wrap;color:#d8d0d2}
footer{color:var(--mut);padding:20px 26px;border-top:1px solid var(--line)}
a{color:var(--neon)}
</style></head><body>"""


def render_html(items: list[dict], summary: dict) -> str:
    d = summary["device"]
    parts = [_HTML_HEAD,
             "<header><h1>&#9760; ANDROID PANZER — FORENSIK-REPORT</h1>",
             f"<div class='meta'>Erstellt <b>{html.escape(summary['generated'])}</b> · "
             f"Gerät <b>{html.escape(d['brand'])} {html.escape(d['model'])}</b> · "
             f"Serial <b>{html.escape(d['serial'] or '—')}</b> · "
             f"Android <b>{html.escape(d['android'] or '—')}</b> · "
             f"Root <b>{'ja' if d['root'] else 'nein'}</b></div></header>",
             "<div class='wrap'>",
             f"<div><span class='stat'><b>{summary['files_total']}</b> Artefakte</span>"
             f"<span class='stat'><b>{human_size(summary['size_total'])}</b> gesamt</span>"
             f"<span class='stat'><b>{len(summary['by_section'])}</b> Kategorien</span></div>"]

    cur = None
    open_section = False
    for it in sorted(items, key=lambda x: (x["category"], x["rel"])):
        if it["category"] != cur:
            if open_section:
                parts.append("</details>")
            cur = it["category"]
            cnt = summary["by_section"].get(it["section"], 0)
            parts.append(f"<details open><summary>{html.escape(cur)}"
                         f"<span class='c'>{cnt} Datei(en)</span></summary>")
            open_section = True
        parts.append("<div class='file'><div class='fh'>"
                     f"<span class='fn'>{html.escape(it['name'])}</span>"
                     f"<span class='fm'>{human_size(it['size'])} · {html.escape(it['mtime'])}</span></div>"
                     f"<div class='fm'>{html.escape(it['rel'])}</div>"
                     f"<div class='sha'>sha256: {it['sha256']}</div>")
        if it["preview"] is not None:
            parts.append(f"<pre>{html.escape(it['preview'])}</pre>")
        elif not it["is_text"]:
            parts.append("<div class='fm'>(Binärdatei – nur Hash gelistet)</div>")
        parts.append("</div>")
    if open_section:
        parts.append("</details>")

    parts.append("</div><footer>Android Panzer · Nur für eigene/autorisiert untersuchte Geräte. "
                 "Integrität via MANIFEST.sha256 (sha256sum -c) prüfbar.</footer></body></html>")
    return "".join(parts)


def render_manifest(items: list[dict]) -> str:
    """sha256sum-kompatibel: '<hash>  <relpfad>' je Zeile."""
    lines = [f"{it['sha256']}  {it['rel']}" for it in items if it["sha256"]]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
#  Schreiben
# --------------------------------------------------------------------------- #
def generate(data: dict | None = None, formats=("html", "md", "json", "manifest")) -> dict:
    """Erzeugt die gewählten Report-Formate. Gibt {format: pfad} zurück."""
    items = collect()
    summary = _summary(items, data)
    rdir = outdir(REPORT_DIR)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    written: dict[str, str] = {}

    renderers = {
        "html": (f"report_{stamp}.html", render_html),
        "md": (f"report_{stamp}.md", render_markdown),
        "json": (f"report_{stamp}.json", render_json),
    }
    md_body = ""
    for fmt in formats:
        if fmt == "manifest":
            continue
        name, fn = renderers[fmt]
        path = os.path.join(rdir, name)
        content = fn(items, summary)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        written[fmt] = path
        if fmt == "md":
            md_body = content

    if "manifest" in formats:
        man = os.path.join(rdir, f"MANIFEST_{stamp}.sha256")
        body = render_manifest(items)
        with open(man, "w", encoding="utf-8") as f:
            f.write(body)
        # Selbst-Hash des Manifests (Anker der Chain-of-Custody)
        with open(man + ".self", "w", encoding="utf-8") as f:
            f.write(f"{sha256_text(body)}  {os.path.basename(man)}\n")
        written["manifest"] = man

    summary["report_files"] = written
    if md_body:
        ui.show_report(md_body, "📑 Gesamtbericht (Markdown)", written.get("md"), note="Gesamtbericht")
    return summary


# --------------------------------------------------------------------------- #
#  Menü
# --------------------------------------------------------------------------- #
def menu(adb=None, dev=None, st=None, data=None) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="📑 Report & Export")
        items_preview = collect()
        n = len(items_preview)
        size = sum(i["size"] for i in items_preview)
        ui.kv("Gefundene Artefakte", f"{n} Dateien · {human_size(size)}")
        secs = {}
        for it in items_preview:
            secs[it["category"]] = secs.get(it["category"], 0) + 1
        for cat, c in sorted(secs.items()):
            ui.kv(f"  {cat}", c)
        print()
        ch = ui.menu("Aktion", [
            ("1", "📄 Gesamt-Report erzeugen (HTML + Markdown + JSON + SHA-256-Manifest)"),
            ("2", "🌐 Nur HTML-Report"),
            ("3", "🔐 Nur SHA-256-Manifest (Chain-of-Custody)"),
            ("4", "✅ Manifest verifizieren (Integritätsprüfung)"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            _do(data, ("html", "md", "json", "manifest"))
        elif ch == "2":
            _do(data, ("html",))
        elif ch == "3":
            _do(data, ("manifest",))
        elif ch == "4":
            _verify()
        else:
            ui.warn("Ungültige Auswahl."); time.sleep(0.6)


def _do(data, formats) -> None:
    ui.info("Sammle Artefakte, berechne Hashes, rendere …")
    try:
        summary = generate(data, formats)
    except Exception as e:  # noqa: BLE001
        ui.err(f"Report fehlgeschlagen: {e}")
        LOG.exception("Report-Erzeugung", e)
        ui.pause(); return
    ui.ok(f"{summary['files_total']} Artefakte · {human_size(summary['size_total'])}")
    for fmt, path in summary["report_files"].items():
        ui.kv(fmt.upper(), path)
    ui.pause()


def _verify() -> None:
    rdir = os.path.join(BASE, REPORT_DIR)
    if not os.path.isdir(rdir):
        ui.warn("Noch kein Report-Verzeichnis – zuerst Manifest erzeugen.")
        ui.pause(); return
    mans = sorted([f for f in os.listdir(rdir) if f.startswith("MANIFEST_") and f.endswith(".sha256")])
    if not mans:
        ui.warn("Kein Manifest gefunden.")
        ui.pause(); return
    man = os.path.join(rdir, mans[-1])
    ui.info(f"Prüfe gegen {os.path.basename(man)} …")
    ok = bad = missing = 0
    out = []
    with open(man, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            expected, _, rel = line.partition("  ")
            path = os.path.join(BASE, rel)
            if not os.path.isfile(path):
                missing += 1; out.append(f"FEHLT    {rel}"); continue
            actual = sha256_file(path)
            if actual == expected:
                ok += 1
            else:
                bad += 1; out.append(f"GEÄNDERT {rel}")
    if bad or missing:
        ui.err(f"Integrität verletzt: {bad} geändert, {missing} fehlen, {ok} ok.")
        ui.pager("\n".join(out), "Abweichungen")
    else:
        ui.ok(f"Alle {ok} Dateien unverändert – Integrität bestätigt. ✔")
    ui.pause()
