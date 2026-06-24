"""Report-Generierung – JSON, Text, Timeline-ASCII."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .models import ForensicReport, ApkArtifact
from .analyzer import build_timeline, detect_anomalies, compute_stats, analyze_version_timeline
from .utils import ensure_output_dir


# ---------------------------------------------------------------------------
# Text-Report
# ---------------------------------------------------------------------------

_SEP  = "─" * 72
_SEP2 = "═" * 72


def generate_text_report(report: ForensicReport) -> str:
    """Erstellt vollständigen menschenlesbaren Textbericht."""
    lines: list[str] = []
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    lines += [
        _SEP2,
        "  PLAY STORE ARTIFACT FORENSIC REPORT",
        f"  Erstellt: {ts}",
        _SEP2, "",
        "═ GERÄT ══════════════════════════════════════════════════════════",
        report.summary(),
    ]

    # --- Installations-Tabelle ---
    lines += [
        "═ INSTALLATIONS-HISTORIE ════════════════════════════════════════",
        f"  {'STATUS':<14} {'ERSTINSTALL':<20} {'UPDATE':<20} {'QUELLE':<28} PAKET",
        _SEP,
    ]
    for r in report.installs[:100]:
        lines.append(
            f"  {r.flag():<14} {r.first_install:<20} {r.last_update:<20} "
            f"{(r.installer or '—')[:26]:<28} {r.package}"
        )
    if len(report.installs) > 100:
        lines.append(f"  … ({len(report.installs) - 100} weitere Einträge im JSON-Export)")

    # --- Suchhistorie ---
    if report.searches:
        lines += ["", "═ SUCHHISTORIE (Play Store) ═════════════════════════════════════", _SEP]
        for s in report.searches[:200]:
            lines.append(str(s))
        if len(report.searches) > 200:
            lines.append(f"  … ({len(report.searches) - 200} weitere)")

    # --- Nutzungsstatistik ---
    if report.usage:
        lines += ["", "═ APP-NUTZUNG (Top 30) ══════════════════════════════════════════", _SEP]
        for u in report.usage[:30]:
            lines.append(str(u))

    # --- APK-Scan ---
    risky = [a for a in report.apk_scans if a.risk_level != "LOW"]
    if risky:
        lines += ["", "═ APK-RISIKO-BEFUNDE ════════════════════════════════════════════", _SEP]
        for a in risky:
            lines.append(str(a))
            if a.hardcoded_ips:
                lines.append(f"     Hardcoded IPs : {', '.join(a.hardcoded_ips[:5])}")
            if a.suspicious_perms:
                lines.append(f"     Verdächt. Perms: {', '.join(a.suspicious_perms[:5])}")

    # --- Anomalien ---
    anomalies = detect_anomalies(report)
    if anomalies:
        lines += ["", "═ ANOMALIEN & AUFFÄLLIGKEITEN ═══════════════════════════════════", _SEP]
        for a in anomalies:
            sev_color = {"CRITICAL": "!!!",  "HIGH": "!! ", "MEDIUM": "!  ", "INFO": "   "}
            marker = sev_color.get(a["severity"], "   ")
            lines.append(f"  [{a['severity']:<8}] {marker} {a['type']:<25} {a.get('package', '')}")
            lines.append(f"              Detail: {a['detail']}")

    # --- Statistiken ---
    stats = compute_stats(report)
    lines += [
        "", "═ STATISTIK ═════════════════════════════════════════════════════",
        f"  Apps gesamt       : {stats['total_apps']}",
        f"  Sideloaded        : {stats['sideloaded_count']}",
        f"  Unbekannte Quelle : {stats['unknown_installer']}",
        f"  HIGH/CRITICAL APKs: {stats['high_risk_apks']}",
        f"  Suchanfragen      : {stats['total_searches']}",
        "", _SEP2,
        "  ENDE DES BERICHTS",
        _SEP2,
    ]

    if report.errors:
        lines += ["", "═ FEHLER WÄHREND EXTRAKTION ═════════════════════════════════════"]
        for e in report.errors:
            lines.append(f"  ⚠ {e}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Timeline-ASCII
# ---------------------------------------------------------------------------

def generate_timeline_ascii(report: ForensicReport, max_events: int = 60) -> str:
    """Erstellt eine ASCII-Zeitlinie aller Ereignisse."""
    events = build_timeline(report)
    if not events:
        return "  [Keine Timeline-Daten verfügbar]"

    lines: list[str] = [
        _SEP2,
        "  EREIGNIS-ZEITLINIE (chronologisch)",
        _SEP2,
    ]

    type_icons = {
        "INSTALL": "📦",
        "UPDATE":  "🔄",
        "SEARCH":  "🔍",
        "USED":    "▶",
    }

    shown = 0
    for ev in events[:max_events]:
        icon = type_icons.get(ev["type"], "·")
        flag = f" [{ev['flag']}]" if ev["flag"] != "✓" else ""
        pkg  = f" {ev['pkg'][:35]}" if ev["pkg"] else ""
        lines.append(
            f"  {ev['ts']}  {ev['type']:<8}{flag}  {icon}{pkg}"
            f"  {ev['detail'][:40]}"
        )
        shown += 1

    if len(events) > max_events:
        lines.append(f"  … ({len(events) - max_events} weitere Ereignisse im JSON-Export)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON-Export
# ---------------------------------------------------------------------------

def generate_json_report(report: ForensicReport, indent: int = 2) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=indent, default=str)


# ---------------------------------------------------------------------------
# Dateispeicherung
# ---------------------------------------------------------------------------

def save_reports(
    report: ForensicReport,
    output_dir: str | Path,
) -> dict[str, str]:
    """Speichert alle Report-Formate in output_dir.

    Gibt dict {format: dateipfad} zurück.
    """
    out = ensure_output_dir(output_dir)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    saved: dict[str, str] = {}

    # Text
    txt_path = str(out / f"psf_report_{stamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(generate_text_report(report))
    saved["txt"] = txt_path

    # JSON
    json_path = str(out / f"psf_report_{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(generate_json_report(report))
    saved["json"] = json_path

    # Timeline
    tl_path = str(out / f"psf_timeline_{stamp}.txt")
    with open(tl_path, "w", encoding="utf-8") as f:
        f.write(generate_timeline_ascii(report))
    saved["timeline"] = tl_path

    # Anomalien separat
    anomalies = detect_anomalies(report)
    if anomalies:
        an_path = str(out / f"psf_anomalies_{stamp}.txt")
        with open(an_path, "w", encoding="utf-8") as f:
            for a in anomalies:
                f.write(f"[{a['severity']}] {a['type']} | {a.get('package', '')} | {a['detail']}\n")
        saved["anomalies"] = an_path

    return saved
