"""Analyzer – Timeline-Korrelation, Anomalie-Erkennung, Scoring.

Arbeitet ausschließlich auf den strukturierten Model-Objekten.
Kein ADB-Zugriff – reine Datenanalyse.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import (
    InstallRecord, SearchRecord, UsageRecord, ApkArtifact,
    VersionEntry, ForensicReport,
)
from .config import KNOWN_STORES, SUSPICIOUS_PERMISSIONS


# ---------------------------------------------------------------------------
# Timeline aus allen Quellen aufbauen
# ---------------------------------------------------------------------------

def build_timeline(report: ForensicReport) -> list[dict]:
    """Kombiniert alle Artefakte zu einer chronologisch sortierten Timeline."""
    events: list[dict] = []

    for r in report.installs:
        if r.first_install != "—":
            events.append({
                "ts":    r.first_install,
                "type":  "INSTALL",
                "pkg":   r.package,
                "detail": f"v{r.version_name} via {r.installer}",
                "flag":  r.flag(),
            })
        if r.last_update != "—" and r.last_update != r.first_install:
            events.append({
                "ts":    r.last_update,
                "type":  "UPDATE",
                "pkg":   r.package,
                "detail": f"→ v{r.version_name}",
                "flag":  "✓",
            })

    for s in report.searches:
        if s.timestamp != "—":
            events.append({
                "ts":    s.timestamp,
                "type":  "SEARCH",
                "pkg":   "",
                "detail": f'"{s.query}"',
                "flag":  "✓",
            })

    for u in report.usage:
        if u.last_used != "—":
            events.append({
                "ts":    u.last_used,
                "type":  "USED",
                "pkg":   u.package,
                "detail": f"{u.fg_minutes:.1f} min gesamt",
                "flag":  "✓",
            })

    events.sort(key=lambda e: e["ts"])
    return events


# ---------------------------------------------------------------------------
# Anomalie-Erkennung
# ---------------------------------------------------------------------------

def detect_anomalies(report: ForensicReport) -> list[dict]:
    """Findet forensisch relevante Auffälligkeiten."""
    anomalies: list[dict] = []

    # 1. Sideloaded Apps
    for r in report.installs:
        if r.is_sideloaded:
            anomalies.append({
                "severity": "HIGH",
                "type":     "SIDELOAD",
                "package":  r.package,
                "detail":   f"Installiert via '{r.installer}' (kein bekannter Store)",
            })

    # 2. Unbekannter Installer
    for r in report.installs:
        if r.installer in ("—", "null", "") and not r.is_system:
            anomalies.append({
                "severity": "MEDIUM",
                "type":     "UNKNOWN_INSTALLER",
                "package":  r.package,
                "detail":   "Kein Installer-Eintrag – manuell per ADB installiert?",
            })

    # 3. High/Critical APK-Risiko
    for a in report.apk_scans:
        if a.risk_level in ("HIGH", "CRITICAL"):
            detail_parts = []
            if not a.signature_valid:
                detail_parts.append("ungültige Signatur")
            if a.hardcoded_ips:
                detail_parts.append(f"{len(a.hardcoded_ips)} hardcoded IPs")
            if a.suspicious_perms:
                detail_parts.append(f"verdächtige Permissions: {', '.join(a.suspicious_perms[:3])}")
            if a.strings_of_interest:
                detail_parts.append(f"{len(a.strings_of_interest)} Secret-Strings")
            anomalies.append({
                "severity": a.risk_level,
                "type":     "APK_RISK",
                "package":  a.package,
                "detail":   " | ".join(detail_parts),
            })

    # 4. Suchanfragen zeitlich VOR Installation → Intent-Nachweis
    search_times = {s.query.lower(): s.timestamp for s in report.searches if s.timestamp != "—"}
    install_times = {r.package: r.first_install for r in report.installs if r.first_install != "—"}
    for pkg, inst_ts in install_times.items():
        app_name = pkg.split(".")[-1].lower()
        for query, search_ts in search_times.items():
            if app_name in query and search_ts < inst_ts:
                anomalies.append({
                    "severity": "INFO",
                    "type":     "SEARCH_BEFORE_INSTALL",
                    "package":  pkg,
                    "detail":   f'Suche "{query}" am {search_ts} → Installation am {inst_ts}',
                })

    # 5. Hintergrundaktivität zu ungewöhnlichen Zeiten (02:00–05:00)
    for u in report.usage:
        if u.last_used != "—":
            try:
                hour = int(u.last_used[11:13])
                if 2 <= hour <= 5:
                    anomalies.append({
                        "severity": "MEDIUM",
                        "type":     "NIGHTTIME_ACTIVITY",
                        "package":  u.package,
                        "detail":   f"Aktiv um {u.last_used[11:16]} Uhr (nächtliche Hintergrundaktivität)",
                    })
            except (IndexError, ValueError):
                pass

    # 6. Verdächtige Suchbegriffe (Intent-Nachweis für schädliche Aktivitäten)
    _SUSPICIOUS_KEYWORDS: tuple[str, ...] = (
        "hack", "crack", "keygen", "serial key", "patch", "bypass",
        "spy", "spyware", "stalker", "track", "überwachen",
        "exploit", "root exploit", "cve", "privilege escalation",
        "backdoor", "keylogger", "rat ", "remote access",
        "free premium", "unlocked apk", "modded apk", "apk mod",
        "drogen", "drugs", "bestellen anonym",
    )
    for s in report.searches:
        q = s.query.lower()
        matched = [kw for kw in _SUSPICIOUS_KEYWORDS if kw in q]
        if matched:
            anomalies.append({
                "severity": "HIGH",
                "type":     "SUSPICIOUS_SEARCH",
                "package":  "",
                "detail":   f'Suchbegriff: "{s.query}" | Treffer: {", ".join(matched)} | Zeitpunkt: {s.timestamp}',
            })

    # 7. Sehr viele Updates eines Pakets in kurzer Zeit (Malware-Rotation)
    from collections import defaultdict as _dd
    update_counts: dict[str, int] = _dd(int)
    for r in report.installs:
        if r.last_update != "—" and r.last_update != r.first_install:
            update_counts[r.package] += 1
    for pkg, cnt in update_counts.items():
        if cnt >= 4:
            anomalies.append({
                "severity": "MEDIUM",
                "type":     "FREQUENT_UPDATES",
                "package":  pkg,
                "detail":   f"{cnt} Updates erfasst – mögliche Malware-Versionswechsel",
            })

    anomalies.sort(key=lambda a: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}.get(a["severity"], 4))
    return anomalies


# ---------------------------------------------------------------------------
# Statistiken
# ---------------------------------------------------------------------------

def compute_stats(report: ForensicReport) -> dict[str, Any]:
    """Berechnet Zusammenfassungsstatistiken über alle Artefakte."""
    sideloaded    = [r for r in report.installs if r.is_sideloaded]
    unknown_inst  = [r for r in report.installs if r.installer in ("—", "null", "")]
    high_risk     = [a for a in report.apk_scans if a.risk_level in ("HIGH", "CRITICAL")]
    installer_cnt: dict[str, int] = defaultdict(int)
    for r in report.installs:
        installer_cnt[r.installer or "unbekannt"] += 1

    top_used = sorted(report.usage, key=lambda u: u.fg_time_ms, reverse=True)[:10]

    return {
        "total_apps":          len(report.installs),
        "sideloaded_count":    len(sideloaded),
        "unknown_installer":   len(unknown_inst),
        "high_risk_apks":      len(high_risk),
        "total_searches":      len(report.searches),
        "total_usage_records": len(report.usage),
        "installer_breakdown": dict(installer_cnt),
        "top_used_apps":       [u.package for u in top_used],
    }


# ---------------------------------------------------------------------------
# Versions-Auffälligkeiten (Downgrade, Malware-Versionswechsel)
# ---------------------------------------------------------------------------

def analyze_version_timeline(timeline: list[VersionEntry]) -> list[dict]:
    """Sucht Downgrades und schnelle Versionswechsel (Malware-Indikator)."""
    findings: list[dict] = []
    by_pkg: dict[str, list[VersionEntry]] = defaultdict(list)
    for e in timeline:
        by_pkg[e.package].append(e)

    for pkg, entries in by_pkg.items():
        updates = [e for e in entries if e.event_type == "UPDATE"]
        if len(updates) >= 3:
            findings.append({
                "type":    "FREQUENT_UPDATES",
                "package": pkg,
                "detail":  f"{len(updates)} Updates in kurzer Zeit – möglicher Versionswechsel einer Malware",
                "count":   len(updates),
            })

        # Versions-Regression prüfen
        versions = [(e.version_code, e.timestamp) for e in entries if e.version_code != "—"]
        versions.sort(key=lambda x: x[1])
        for i in range(1, len(versions)):
            try:
                if int(versions[i][0]) < int(versions[i-1][0]):
                    findings.append({
                        "type":    "DOWNGRADE",
                        "package": pkg,
                        "detail":  f"Downgrade von vCode {versions[i-1][0]} auf {versions[i][0]} am {versions[i][1]}",
                    })
            except ValueError:
                pass

    return findings


# ---------------------------------------------------------------------------
# Netzwerk-Anomalien
# ---------------------------------------------------------------------------

def detect_network_anomalies(
    report: ForensicReport,
    net_data: dict | None = None,
) -> list[dict]:
    """Erkennt Netzwerk-Anomalien aus APK-Scans und optionalen Live-Daten."""
    anomalies: list[dict] = []

    _RFC1918 = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
                "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")

    for a in report.apk_scans:
        public_ips = [
            ip for ip in a.hardcoded_ips
            if not ip.startswith(_RFC1918) and not ip.startswith("127.")
        ]
        if public_ips:
            for ip in public_ips[:5]:
                anomalies.append({
                    "severity": "HIGH",
                    "type":     "HARDCODED_C2_IP",
                    "package":  a.package,
                    "detail":   f"Hardcoded öffentliche IP: {ip}",
                })
        if len(a.hardcoded_ips) >= 5:
            anomalies.append({
                "severity": "MEDIUM",
                "type":     "MANY_NETWORK_ENDPOINTS",
                "package":  a.package,
                "detail":   (f"{len(a.hardcoded_ips)} hardcoded Endpunkte "
                             "– mögliche C2-Infrastruktur"),
            })

    if net_data:
        for conn in net_data.get("tcp_connections", []):
            remote = conn.get("remote_addr", "")
            state  = conn.get("state", "")
            pkg    = conn.get("package", "?")
            if state == "ESTABLISHED" and remote:
                ip = remote.split(":")[0]
                if ip and not ip.startswith(("127.",) + _RFC1918):
                    anomalies.append({
                        "severity": "INFO",
                        "type":     "ACTIVE_EXTERNAL_CONNECTION",
                        "package":  pkg,
                        "detail":   f"Aktive Verbindung → {remote}",
                    })

    return anomalies


# ---------------------------------------------------------------------------
# Persistenz-Mechanismen
# ---------------------------------------------------------------------------

_PERSISTENCE_PERMS: dict[str, tuple[str, str]] = {
    "RECEIVE_BOOT_COMPLETED":              ("HIGH",    "Boot-Receiver – startet bei Neustart automatisch"),
    "BIND_DEVICE_ADMIN":                   ("CRITICAL","Device-Admin – kann Gerät sperren/löschen"),
    "BIND_ACCESSIBILITY_SERVICE":          ("CRITICAL","Accessibility-Service – vollständige UI-Kontrolle"),
    "BIND_NOTIFICATION_LISTENER_SERVICE":  ("HIGH",    "Notification Listener – liest alle Benachrichtigungen"),
    "SYSTEM_ALERT_WINDOW":                 ("MEDIUM",  "System-Overlay – kann andere Apps überlagern"),
    "REQUEST_INSTALL_PACKAGES":            ("HIGH",    "Kann beliebige APKs installieren"),
    "MANAGE_EXTERNAL_STORAGE":             ("MEDIUM",  "Vollständiger Dateisystem-Zugriff"),
}


def detect_persistence_mechanisms(report: ForensicReport) -> list[dict]:
    """Erkennt Persistenz-Mechanismen (Boot-Receiver, DeviceAdmin, Accessibility)."""
    findings: list[dict] = []

    for a in report.apk_scans:
        for perm in a.suspicious_perms:
            short = perm.split(".")[-1]
            if short in _PERSISTENCE_PERMS:
                severity, desc = _PERSISTENCE_PERMS[short]
                findings.append({
                    "severity": severity,
                    "type":     "PERSISTENCE_MECHANISM",
                    "package":  a.package,
                    "detail":   f"{short}: {desc}",
                })

    high_risk_pkgs = {a.package for a in report.apk_scans if a.risk_level in ("HIGH", "CRITICAL")}
    for r in report.installs:
        if r.is_sideloaded and r.package in high_risk_pkgs:
            findings.append({
                "severity": "CRITICAL",
                "type":     "SIDELOADED_HIGH_RISK",
                "package":  r.package,
                "detail":   "Sidegeloadete App mit HIGH/CRITICAL APK-Risiko – aktive Bedrohung",
            })

    findings.sort(
        key=lambda f: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}.get(f["severity"], 4)
    )
    return findings


# ---------------------------------------------------------------------------
# Datenleck-Erkennung
# ---------------------------------------------------------------------------

_SPYWARE_COMBOS: list[tuple[list[str], str, str]] = [
    (["READ_CONTACTS", "READ_CALL_LOG", "ACCESS_FINE_LOCATION"],
     "CRITICAL", "Spyware-Trias: Kontakte+Anrufe+GPS"),
    (["READ_SMS", "RECEIVE_SMS", "SEND_SMS"],
     "HIGH", "SMS-Vollzugriff: lesen+empfangen+senden"),
    (["RECORD_AUDIO", "PROCESS_OUTGOING_CALLS", "READ_PHONE_STATE"],
     "HIGH", "Telefonat-Überwachung"),
    (["CAMERA", "READ_CONTACTS", "ACCESS_FINE_LOCATION"],
     "HIGH", "Kamera+Kontakte+GPS – Stalkerware-Muster"),
    (["READ_CALL_LOG", "READ_SMS", "ACCESS_FINE_LOCATION"],
     "HIGH", "Anruf+SMS+GPS – vollständige Überwachung"),
]


def detect_data_leakage_risk(
    report: ForensicReport,
    shared_prefs: list[dict] | None = None,
) -> list[dict]:
    """Erkennt Datenleck-Risiken aus Permission-Kombos und SharedPrefs."""
    findings: list[dict] = []

    for a in report.apk_scans:
        perm_set = {p.split(".")[-1] for p in a.suspicious_perms}
        for combo, severity, label in _SPYWARE_COMBOS:
            if all(p in perm_set for p in combo):
                findings.append({
                    "severity": severity,
                    "type":     "SPYWARE_PERMISSION_COMBO",
                    "package":  a.package,
                    "detail":   label,
                })

    if shared_prefs:
        for prefs in shared_prefs:
            pkg = prefs.get("pkg", "?")
            api_keys = prefs.get("api_keys_found", [])
            if api_keys:
                findings.append({
                    "severity": "HIGH",
                    "type":     "EXPOSED_SECRETS_IN_PREFS",
                    "package":  pkg,
                    "detail":   (f"{len(api_keys)} API-Key(s)/Token(s) in SharedPreferences: "
                                 f"{', '.join(api_keys[:2])}"),
                })

    for a in report.apk_scans:
        perm_shorts = [p.split(".")[-1] for p in a.suspicious_perms]
        if "READ_EXTERNAL_STORAGE" in perm_shorts or "MANAGE_EXTERNAL_STORAGE" in perm_shorts:
            findings.append({
                "severity": "MEDIUM",
                "type":     "BROAD_STORAGE_ACCESS",
                "package":  a.package,
                "detail":   "Vollständiger Lese-Zugriff auf externen Speicher",
            })

    findings.sort(
        key=lambda f: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}.get(f["severity"], 4)
    )
    return findings


# ---------------------------------------------------------------------------
# Master Risk-Report Builder
# ---------------------------------------------------------------------------

def build_comprehensive_risk_report(
    report: ForensicReport,
    anomalies: list[dict],
    stats: dict,
    extra_findings: list[dict] | None = None,
) -> str:
    """Generiert textuellen Master-Risikobericht aus allen Quellen."""
    all_findings = list(anomalies)
    if extra_findings:
        all_findings.extend(extra_findings)
    all_findings.sort(
        key=lambda f: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}.get(
            f.get("severity", "INFO"), 4
        )
    )

    critical = [f for f in all_findings if f.get("severity") == "CRITICAL"]
    high     = [f for f in all_findings if f.get("severity") == "HIGH"]
    medium   = [f for f in all_findings if f.get("severity") == "MEDIUM"]
    info     = [f for f in all_findings if f.get("severity") == "INFO"]

    def _section(label: str, items: list[dict], limit: int) -> list[str]:
        lines = ["-" * 72, f"  {label}:"]
        for f in items[:limit]:
            lines.append(f"  [{f.get('severity','?'):8}] {f.get('type','?'):<32} {f.get('package','')}")
            lines.append(f"    → {str(f.get('detail',''))[:68]}")
        if not items:
            lines.append("  (keine)")
        return lines

    parts = [
        "=" * 72,
        "  MASTER RISK-REPORT – AndroidPanzer Play Store Forensics",
        "=" * 72,
        f"  Gerät       : {report.device_model}",
        f"  Android     : {report.android_version}",
        f"  Scan-Zeit   : {report.scan_timestamp}",
        f"  Root        : {'JA' if report.root_available else 'NEIN'}",
        "-" * 72,
        "  RISIKO-ÜBERSICHT:",
        f"    CRITICAL  : {len(critical)}",
        f"    HIGH      : {len(high)}",
        f"    MEDIUM    : {len(medium)}",
        f"    INFO      : {len(info)}",
        f"    GESAMT    : {len(all_findings)}",
        "-" * 72,
        "  STATISTIKEN:",
        f"    Apps gesamt          : {stats.get('total_apps', 0)}",
        f"    Sideloaded           : {stats.get('sideloaded_count', 0)}",
        f"    Unbekannter Installer : {stats.get('unknown_installer', 0)}",
        f"    HIGH/CRITICAL APKs   : {stats.get('high_risk_apks', 0)}",
        f"    Suchanfragen          : {stats.get('total_searches', 0)}",
    ]
    parts += _section("CRITICAL-BEFUNDE", critical, 10)
    parts += _section("HIGH-BEFUNDE",     high,     15)
    parts += _section("MEDIUM-BEFUNDE",   medium,   20)
    parts.append("=" * 72)
    return "\n".join(parts)
