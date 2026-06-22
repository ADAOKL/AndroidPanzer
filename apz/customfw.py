"""Zeigt flashbare Custom-Firmware & Recovery für das angeschlossene Gerät an –
anhand des Geräte-Codenamens, live aus dem Internet.

Verifizierbar per API (echte Build-Daten):
  • LineageOS   – offizielle Builds (Version, Datum, Größe, direkter Download-Link)
  • TWRP        – alle verfügbaren Recovery-Versionen (dl.twrp.me)

Ohne saubere API → direkte Projekt-/Such-Einstiege (XDA, OrangeFox, PixelExperience,
crDroid, SourceForge). Ehrlich gekennzeichnet: was real gefunden wurde vs. wo man
selbst nachsehen muss. Nichts wird erfunden.

Custom-Firmware setzt einen ENTSPERRTEN Bootloader voraus und löscht Daten – das
Modul lädt/flasht NICHTS, es zeigt nur an, was es für den Codename gibt.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from urllib.parse import quote

from . import ui
from .util import LOG, human_size, outdir

_UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")}


def _get(url: str, timeout: int = 20) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout).read()


def _codenames(data: dict, adb) -> list[str]:
    """Plausible Geräte-Codenamen (für die ROM-/Recovery-Abfrage)."""
    g = adb.getprop
    raw = [data.get("device", ""), g("ro.product.device"), g("ro.product.vendor.device"),
           g("ro.build.product"), g("ro.product.name")]
    out: list[str] = []
    for v in raw:
        v = (v or "").strip().lower()
        if v and v not in out and re.match(r"^[a-z0-9_]+$", v):
            out.append(v)
    return out or ["?"]


def lineageos_builds(code: str) -> list[dict]:
    """Offizielle LineageOS-Builds für *code* (leer = nicht offiziell unterstützt)."""
    try:
        data = json.loads(_get(f"https://download.lineageos.org/api/v1/{code}/nightly/1"))
        return data.get("response", []) or []
    except Exception as e:  # noqa: BLE001
        LOG.exception(f"lineageos api {code}", e)
        return []


def twrp_versions(code: str) -> list[str]:
    """Verfügbare offizielle TWRP-Versionen für *code*."""
    try:
        html = _get(f"https://dl.twrp.me/{code}/").decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return []
    return sorted(set(re.findall(r"twrp-([\d.]+_\d+-\d+)-", html)), reverse=True)


def show_custom_firmware(adb, dev, st, data) -> None:
    ui.clear()
    ui.banner(subtitle="🌐 Custom-Firmware & Recovery für dieses Gerät")
    codes = _codenames(data, adb)
    ui.kv("Gerät", f"{data.get('brand', '')} {data.get('model', '')}")
    ui.kv("Codename(n)", ", ".join(codes))
    ui.info("Frage offizielle Quellen ab (LineageOS-API · TWRP) … kurz Geduld.")

    title = f"{data.get('brand', '')} {data.get('model', '')} ({codes[0]})".strip()
    lines = [f"# CUSTOM-FIRMWARE & RECOVERY · {title}",
             f"# {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    found = False
    seen_codes = set()
    for code in codes:
        if code in seen_codes:
            continue
        seen_codes.add(code)

        builds = lineageos_builds(code)
        if builds:
            found = True
            ui.ok(f"LineageOS: offiziell unterstützt ({code}) – {len(builds)} Build(s)")
            lines.append(f"== LineageOS · OFFIZIELL unterstützt · {code} ==")
            for b in builds[:6]:
                d = time.strftime("%Y-%m-%d", time.localtime(b.get("datetime", 0)))
                lines.append(f"  • Lineage {b.get('version', '?')} ({b.get('romtype', '?')}) · {d} · "
                             f"{human_size(b.get('size', 0))}")
                lines.append(f"      {b.get('url', '')}")
            lines.append(f"      Installations-Anleitung: https://wiki.lineageos.org/devices/{code}/install")
            lines.append("")

        vers = twrp_versions(code)
        if vers:
            found = True
            ui.ok(f"TWRP: {len(vers)} Version(en) für {code}")
            lines.append(f"== TWRP-Recovery · {code} ==")
            lines.append(f"  • Versionen: {', '.join(vers[:8])}")
            lines.append(f"      Übersicht & Download: https://dl.twrp.me/{code}/")
            lines.append("  • (Im Tool direkt flashbar: Samsung-Menü → 3 'TWRP-Recovery flashen')")
            lines.append("")

    c0 = codes[0]
    model = data.get("model", "")
    lines += [
        "== Weitere ROMs & Recoveries – direkte Projekt-/Such-Einstiege ==",
        "  (keine einheitliche API – Verfügbarkeit dort selbst prüfen)",
        f"  • OrangeFox Recovery : https://orangefox.download/device/{c0}",
        f"  • PixelExperience    : https://download.pixelexperience.org/{c0}",
        f"  • crDroid            : https://crdroid.net/{c0}",
        f"  • Evolution X        : https://evolution-x.org/downloads/{c0}",
        f"  • XDA (alle ROMs/Kernels): https://www.google.com/search?q={quote('XDA ' + model + ' ' + c0 + ' custom ROM')}",
        f"  • SourceForge        : https://sourceforge.net/directory/?q={quote(c0)}",
        f"  • Allg. Suche        : https://www.google.com/search?q={quote(c0 + ' custom rom download')}",
        "",
        "⚠ Hinweise:",
        "  • Custom-Firmware braucht einen ENTSPERRTEN Bootloader und LÖSCHT alle Daten.",
        "  • Nur ROM/Recovery für EXAKT diesen Codename nutzen – falsches Image = Bootloop/Brick.",
        "  • Bei Samsung wird per Heimdall/Odin (Download-Modus) geflasht, nicht Fastboot.",
    ]
    if not found:
        lines.insert(2, "(Keine offiziellen LineageOS-/TWRP-Treffer für den Codename – "
                        "siehe Such-Einstiege unten.)")

    body = "\n".join(lines) + "\n"
    p = os.path.join(outdir("customfw"), f"customfw_{c0}.txt")
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
    except OSError as e:
        ui.err(str(e)); p = None
    ui.show_report(body, f"Custom-Firmware & Recovery · {c0}", p, note="Custom-FW-Liste")
    ui.pause()
