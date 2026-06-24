"""Datenmodelle für alle Play-Store-Artefakte.

Kein Pydantic-Overhead – reine dataclasses für maximale Kompatibilität.
Jedes Model hat to_dict() für JSON-Export und __str__ für CLI-Ausgabe.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Hilfsfunktion: Epoch (ms oder s) → lesbarer Timestamp
# ---------------------------------------------------------------------------

def _fmt_ts(raw: str | int | None) -> str:
    if raw is None or raw == "" or raw == "null":
        return "—"
    try:
        v = int(raw)
    except (ValueError, TypeError):
        return str(raw)
    if v <= 0:
        return "—"
    if v > 10_000_000_000:   # millisekunden → sekunden
        v //= 1000
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(v))
    except (OSError, OverflowError, ValueError):
        return str(raw)


# ---------------------------------------------------------------------------
# 1 – Installations-Datensatz (frosting.db / packages.xml / dumpsys)
# ---------------------------------------------------------------------------

@dataclass
class InstallRecord:
    package:        str
    label:          str = "—"
    first_install:  str = "—"        # ISO-String oder "—"
    last_update:    str = "—"
    installer:      str = "—"        # com.android.vending | sideload | null
    version_code:   str = "—"
    version_name:   str = "—"
    is_system:      bool = False
    is_sideloaded:  bool = False      # Installer unbekannt / nicht Play-Store
    apk_path:       str = "—"
    data_dir:       str = "—"

    @classmethod
    def from_dumpsys(cls, pkg: str, raw: str) -> "InstallRecord":
        import re
        def _get(pattern: str) -> str:
            m = re.search(pattern, raw)
            return m.group(1).strip() if m else "—"

        first = _fmt_ts(_get(r"firstInstallTime=([\d-]+ [\d:]+|[\d]+)"))
        last  = _fmt_ts(_get(r"lastUpdateTime=([\d-]+ [\d:]+|[\d]+)"))
        inst  = _get(r"installerPackageName=(\S+)")
        vc    = _get(r"versionCode=(\d+)")
        vn    = _get(r"versionName=(\S+)")
        path  = _get(r"codePath=(\S+)")
        ddir  = _get(r"dataDir=(\S+)")

        from .config import KNOWN_STORES
        sideloaded = inst not in KNOWN_STORES and inst not in ("—", "null", "")

        return cls(
            package=pkg, first_install=first, last_update=last,
            installer=inst, version_code=vc, version_name=vn,
            apk_path=path, data_dir=ddir, is_sideloaded=sideloaded,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def flag(self) -> str:
        """Schnell-Flag für CLI (⚠ = auffällig, ✓ = normal)."""
        if self.is_sideloaded:
            return "⚠ SIDELOAD"
        if self.installer in ("null", "—", ""):
            return "? UNBEKANNT"
        return "✓"

    def __str__(self) -> str:
        return (f"  [{self.flag()}] {self.package}\n"
                f"     Installiert : {self.first_install}\n"
                f"     Update      : {self.last_update}\n"
                f"     Quelle      : {self.installer}\n"
                f"     Version     : {self.version_name} (Code {self.version_code})\n")


# ---------------------------------------------------------------------------
# 2 – Suchanfrage (suggestions.db)
# ---------------------------------------------------------------------------

@dataclass
class SearchRecord:
    query:      str
    timestamp:  str = "—"
    source:     str = "—"   # "search" | "voice" | "qr"
    result_pkg: str = ""     # falls auf ein konkretes Ergebnis geklickt

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return f"  {self.timestamp}  [{self.source}]  {self.query}"


# ---------------------------------------------------------------------------
# 3 – App-Nutzungsstatistik (usagestats)
# ---------------------------------------------------------------------------

@dataclass
class UsageRecord:
    package:        str
    date_bucket:    str = "—"    # YYYY-MM-DD
    fg_time_ms:     int = 0       # Vordergrund-Nutzungsdauer
    last_used:      str = "—"
    launch_count:   int = 0

    @property
    def fg_minutes(self) -> float:
        return self.fg_time_ms / 60_000

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return (f"  {self.date_bucket}  {self.package:<45}  "
                f"{self.fg_minutes:6.1f} min  ({self.launch_count}x gestartet)")


# ---------------------------------------------------------------------------
# 4 – APK-Artefakt (statische Analyse)
# ---------------------------------------------------------------------------

@dataclass
class ApkArtifact:
    package:              str
    apk_path:             str
    signature_valid:      bool = True
    hardcoded_ips:        list[str] = field(default_factory=list)
    suspicious_perms:     list[str] = field(default_factory=list)
    known_c2_domains:     list[str] = field(default_factory=list)
    strings_of_interest:  list[str] = field(default_factory=list)
    risk_level:           str = "LOW"    # LOW | MEDIUM | HIGH | CRITICAL

    def to_dict(self) -> dict:
        return asdict(self)

    def assess_risk(self) -> None:
        score = 0
        if not self.signature_valid:   score += 30
        score += len(self.hardcoded_ips) * 10
        score += len(self.suspicious_perms) * 5
        score += len(self.known_c2_domains) * 20
        score += len(self.strings_of_interest) * 3
        self.risk_level = (
            "CRITICAL" if score >= 50 else
            "HIGH"     if score >= 30 else
            "MEDIUM"   if score >= 15 else
            "LOW"
        )

    def __str__(self) -> str:
        flags = []
        if not self.signature_valid:     flags.append("INVALID_SIG")
        if self.hardcoded_ips:           flags.append(f"IPs:{len(self.hardcoded_ips)}")
        if self.suspicious_perms:        flags.append(f"PERMS:{len(self.suspicious_perms)}")
        if self.known_c2_domains:        flags.append(f"C2:{len(self.known_c2_domains)}")
        flag_str = " | ".join(flags) if flags else "sauber"
        return f"  [{self.risk_level}] {self.package} → {flag_str}"


# ---------------------------------------------------------------------------
# 5 – Versions-Timeline-Eintrag
# ---------------------------------------------------------------------------

@dataclass
class VersionEntry:
    package:      str
    version_name: str
    version_code: str
    timestamp:    str
    event_type:   str = "INSTALL"   # INSTALL | UPDATE | UNINSTALL | DOWNGRADE

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 6 – Gesamt-Forensik-Bericht
# ---------------------------------------------------------------------------

@dataclass
class ForensicReport:
    device_serial:   str = "unknown"
    device_model:    str = "unknown"
    android_version: str = "unknown"
    root_available:  bool = False
    scan_timestamp:  str = ""
    authorization:   str = "OWN_DEVICE"

    installs:   list[InstallRecord] = field(default_factory=list)
    searches:   list[SearchRecord]  = field(default_factory=list)
    usage:      list[UsageRecord]   = field(default_factory=list)
    apk_scans:  list[ApkArtifact]   = field(default_factory=list)
    timeline:   list[VersionEntry]  = field(default_factory=list)

    errors:     list[str] = field(default_factory=list)
    warnings:   list[str] = field(default_factory=list)

    def summary(self) -> str:
        high_risk = [a for a in self.apk_scans if a.risk_level in ("HIGH", "CRITICAL")]
        sideloaded = [i for i in self.installs if i.is_sideloaded]
        return (
            f"  Gerätemodell    : {self.device_model}\n"
            f"  Android         : {self.android_version}\n"
            f"  Root            : {'ja' if self.root_available else 'nein'}\n"
            f"  Apps analysiert : {len(self.installs)}\n"
            f"  Suchanfragen    : {len(self.searches)}\n"
            f"  Nutzungs-Records: {len(self.usage)}\n"
            f"  APKs gescannt   : {len(self.apk_scans)}\n"
            f"  SIDELOADED      : {len(sideloaded)}\n"
            f"  HIGH/CRITICAL   : {len(high_risk)}\n"
        )

    def to_dict(self) -> dict:
        return {
            "meta": {
                "device_serial":   self.device_serial,
                "device_model":    self.device_model,
                "android_version": self.android_version,
                "root_available":  self.root_available,
                "scan_timestamp":  self.scan_timestamp,
                "authorization":   self.authorization,
            },
            "installs":  [i.to_dict() for i in self.installs],
            "searches":  [s.to_dict() for s in self.searches],
            "usage":     [u.to_dict() for u in self.usage],
            "apk_scans": [a.to_dict() for a in self.apk_scans],
            "timeline":  [t.to_dict() for t in self.timeline],
            "errors":    self.errors,
            "warnings":  self.warnings,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ForensicReport":
        """Deserialisiert einen gespeicherten Report-Dict zurück in ein ForensicReport.

        Verlustfreier Roundtrip: from_dict(report.to_dict()) == report (strukturell).
        Wird für Checkpoint-Resume und Report-Reload genutzt.
        """
        meta = d.get("meta", {})
        report = cls(
            device_serial=meta.get("device_serial", "unknown"),
            device_model=meta.get("device_model", "unknown"),
            android_version=meta.get("android_version", "unknown"),
            root_available=bool(meta.get("root_available", False)),
            scan_timestamp=meta.get("scan_timestamp", ""),
            authorization=meta.get("authorization", "UNKNOWN"),
        )
        report.installs  = [InstallRecord(**i)  for i in d.get("installs", [])]
        report.searches  = [SearchRecord(**s)   for s in d.get("searches", [])]
        report.usage     = [UsageRecord(**u)    for u in d.get("usage", [])]
        report.apk_scans = [ApkArtifact(**a)    for a in d.get("apk_scans", [])]
        report.timeline  = [VersionEntry(**t)   for t in d.get("timeline", [])]
        report.errors    = list(d.get("errors", []))
        report.warnings  = list(d.get("warnings", []))
        return report

    @classmethod
    def from_checkpoint(cls, path: str) -> "ForensicReport | None":
        """Lädt einen gespeicherten Checkpoint vom Disk.

        Gibt None zurück wenn Datei nicht existiert oder korrupt ist.
        """
        import json, os
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (json.JSONDecodeError, TypeError, KeyError):
            return None
