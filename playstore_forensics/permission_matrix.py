"""Per-App Permission Matrix mit AppOps-basiertem Risiko-Scoring.

Unterscheidet zwischen:
  declared  = im Manifest deklariert
  granted   = vom System tatsächlich gewährt
  used      = laut AppOps wirklich genutzt  ← forensisch am relevantesten
  denied    = angefordert aber verweigert
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional
from apz.adb import ADB
from apz.util import shq


# ---------------------------------------------------------------------------
# Datenklasse
# ---------------------------------------------------------------------------

@dataclass
class AppPermissionProfile:
    pkg: str
    declared_perms:           list[str] = field(default_factory=list)
    granted_perms:            list[str] = field(default_factory=list)
    used_perms:               list[str] = field(default_factory=list)
    denied_perms:             list[str] = field(default_factory=list)
    risk_score:               int  = 0
    risk_level:               str  = "LOW"
    spyware_indicators:       list[str] = field(default_factory=list)
    is_device_admin:          bool = False
    is_accessibility_service: bool = False
    has_notification_listener:bool = False
    has_overlay_permission:   bool = False

    def to_dict(self) -> dict:
        return {
            "pkg":                      self.pkg,
            "declared_count":           len(self.declared_perms),
            "granted_count":            len(self.granted_perms),
            "used_count":               len(self.used_perms),
            "denied_count":             len(self.denied_perms),
            "risk_score":               self.risk_score,
            "risk_level":               self.risk_level,
            "spyware_indicators":       self.spyware_indicators,
            "is_device_admin":          self.is_device_admin,
            "is_accessibility_service": self.is_accessibility_service,
            "has_notification_listener":self.has_notification_listener,
            "has_overlay_permission":   self.has_overlay_permission,
            "used_perms":               self.used_perms,
            "granted_perms":            self.granted_perms,
        }


# ---------------------------------------------------------------------------
# Gewichte & Kombinations-Tabellen
# ---------------------------------------------------------------------------

DANGEROUS_PERM_WEIGHTS: dict[str, int] = {
    "android.permission.READ_SMS":                        20,
    "android.permission.RECEIVE_SMS":                     18,
    "android.permission.SEND_SMS":                        15,
    "android.permission.READ_CALL_LOG":                   20,
    "android.permission.PROCESS_OUTGOING_CALLS":          18,
    "android.permission.RECORD_AUDIO":                    15,
    "android.permission.CAMERA":                          12,
    "android.permission.ACCESS_FINE_LOCATION":            15,
    "android.permission.ACCESS_BACKGROUND_LOCATION":      20,
    "android.permission.READ_CONTACTS":                   12,
    "android.permission.GET_ACCOUNTS":                    12,
    "android.permission.USE_CREDENTIALS":                 15,
    "android.permission.BIND_ACCESSIBILITY_SERVICE":      25,
    "android.permission.BIND_DEVICE_ADMIN":               30,
    "android.permission.SYSTEM_ALERT_WINDOW":             20,
    "android.permission.REQUEST_INSTALL_PACKAGES":        18,
    "android.permission.WRITE_SETTINGS":                  12,
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": 20,
    "android.permission.READ_PHONE_STATE":                12,
    "android.permission.READ_PHONE_NUMBERS":              15,
    "android.permission.READ_EXTERNAL_STORAGE":            8,
    "android.permission.WRITE_EXTERNAL_STORAGE":           8,
    "android.permission.RECEIVE_BOOT_COMPLETED":           8,
    "android.permission.INTERNET":                         5,
}

# (label, frozenset of short names, bonus_score)
SPYWARE_PERMISSION_COMBOS: list[tuple[str, frozenset, int]] = [
    ("CLASSIC_SPYWARE",
     frozenset(["READ_SMS", "ACCESS_FINE_LOCATION", "RECORD_AUDIO"]),
     35),
    ("CALL_MONITOR",
     frozenset(["READ_CALL_LOG", "PROCESS_OUTGOING_CALLS", "RECORD_AUDIO"]),
     30),
    ("ACCOUNT_HARVESTER",
     frozenset(["GET_ACCOUNTS", "USE_CREDENTIALS", "INTERNET"]),
     25),
    ("SILENT_INSTALLER",
     frozenset(["REQUEST_INSTALL_PACKAGES", "RECEIVE_BOOT_COMPLETED"]),
     25),
    ("OVERLAY_ATTACK",
     frozenset(["SYSTEM_ALERT_WINDOW", "BIND_ACCESSIBILITY_SERVICE"]),
     35),
    ("BANKING_TROJAN",
     frozenset(["BIND_ACCESSIBILITY_SERVICE", "READ_SMS", "SYSTEM_ALERT_WINDOW"]),
     40),
    ("STALKERWARE",
     frozenset(["ACCESS_BACKGROUND_LOCATION", "READ_CONTACTS", "FOREGROUND_SERVICE"]),
     35),
    ("KEYLOGGER",
     frozenset(["BIND_ACCESSIBILITY_SERVICE", "READ_CLIPBOARD"]),
     40),
    ("FULL_SURVEILLANCE",
     frozenset(["READ_SMS", "READ_CALL_LOG", "ACCESS_FINE_LOCATION",
                "RECORD_AUDIO", "CAMERA"]),
     50),
    ("DATA_EXFILTRATOR",
     frozenset(["READ_EXTERNAL_STORAGE", "READ_CONTACTS",
                "GET_ACCOUNTS", "INTERNET"]),
     25),
]

_SHORT_RE = re.compile(r"android\.permission\.([A-Z_]+)")


def _short(perm: str) -> str:
    """'android.permission.READ_SMS' → 'READ_SMS'"""
    m = _SHORT_RE.search(perm)
    return m.group(1) if m else perm.split(".")[-1].upper()


# ---------------------------------------------------------------------------
# Extraktionsfunktionen
# ---------------------------------------------------------------------------

def extract_granted_permissions(adb: ADB, pkg: str) -> list[str]:
    """Liest tatsächlich gewährte Permissions via `dumpsys package`."""
    raw = adb.shell(
        f"dumpsys package {shq(pkg)} | grep -A 5000 'granted permissions'",
        timeout=20,
    )
    perms: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        # Format: "android.permission.CAMERA: granted=true"
        if "granted=true" in line:
            m = re.match(r"(android\.permission\.[A-Z_]+)", line)
            if m:
                perms.append(m.group(1))
    return perms


def extract_used_permissions(adb: ADB, pkg: str) -> list[str]:
    """AppOps-basierte Nutzungserfassung: was wurde TATSÄCHLICH aufgerufen."""
    raw = adb.shell(f"cmd appops get {shq(pkg)}", timeout=20)
    used: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        # Format: "OP_READ_SMS: allow; time=..."  or "OP_CAMERA: foreground; ..."
        if ("allow" in line.lower() or "foreground" in line.lower()) and "OP_" in line:
            # OP_READ_SMS → READ_SMS → android.permission.READ_SMS
            m = re.match(r"OP_([A-Z_]+):", line)
            if m:
                short = m.group(1)
                used.append(f"android.permission.{short}")
    return used


def extract_device_admins(adb: ADB) -> list[str]:
    """Gibt Paketnamen zurück die Device-Admin-Rechte besitzen."""
    pkgs: list[str] = []

    # Methode 1: dpm list-owners
    raw = adb.shell("dpm list-owners 2>/dev/null", timeout=15)
    for line in raw.splitlines():
        m = re.search(r"package:\s*(\S+)", line)
        if m:
            pkgs.append(m.group(1))

    # Methode 2: dumpsys device_policy
    raw2 = adb.shell("dumpsys device_policy 2>/dev/null | grep -i 'packageName'", timeout=20)
    for line in raw2.splitlines():
        m = re.search(r"packageName=(\S+)", line)
        if m and m.group(1) not in pkgs:
            pkgs.append(m.group(1))

    return pkgs


def extract_accessibility_services(adb: ADB) -> list[str]:
    """Liest aktive Accessibility Services aus System-Settings."""
    raw = adb.shell(
        "settings get secure enabled_accessibility_services 2>/dev/null",
        timeout=10,
    )
    raw = raw.strip()
    if not raw or raw in ("null", ""):
        return []
    # Format: "com.pkg/.Service:com.other/.Svc"
    pkgs: list[str] = []
    for entry in raw.split(":"):
        entry = entry.strip()
        if "/" in entry:
            pkg = entry.split("/")[0]
            pkgs.append(pkg)
        elif "." in entry:
            pkgs.append(entry)
    return list(dict.fromkeys(pkgs))  # dedupliziert, Reihenfolge erhalten


def extract_notification_listeners(adb: ADB) -> list[str]:
    """Liest aktive Notification-Listener-Services."""
    raw = adb.shell(
        "settings get secure enabled_notification_listeners 2>/dev/null",
        timeout=10,
    )
    raw = raw.strip()
    if not raw or raw in ("null", ""):
        return []
    pkgs: list[str] = []
    for entry in raw.split(":"):
        if "/" in entry:
            pkgs.append(entry.split("/")[0].strip())
    return list(dict.fromkeys(pkgs))


def extract_overlay_apps(adb: ADB) -> list[str]:
    """Findet Apps mit aktiven Overlay-Permissions (SYSTEM_ALERT_WINDOW)."""
    pkgs: list[str] = []

    # cmd overlay list
    raw = adb.shell("cmd overlay list 2>/dev/null", timeout=15)
    for line in raw.splitlines():
        # aktive Overlays haben '[x]' Prefix
        if "[x]" in line or "enabled" in line.lower():
            m = re.search(r"([a-z][a-z0-9_.]+\.[a-z][a-z0-9_.]+)", line)
            if m:
                pkgs.append(m.group(1))

    # dumpsys window overlays
    raw2 = adb.shell(
        "dumpsys window 2>/dev/null | grep -i 'TYPE_APPLICATION_OVERLAY\\|SYSTEM_ALERT'",
        timeout=15,
    )
    for line in raw2.splitlines():
        m = re.search(r"([a-z][a-z0-9_.]+\.[a-z][a-z0-9_.]+)", line)
        if m and m.group(1) not in pkgs:
            pkgs.append(m.group(1))

    return list(dict.fromkeys(pkgs))


def extract_declared_permissions(adb: ADB, pkg: str) -> list[str]:
    """Liest im Manifest deklarierte Permissions via `dumpsys package`."""
    raw = adb.shell(
        f"dumpsys package {shq(pkg)} | grep -E 'uses-permission|permission\\.'",
        timeout=15,
    )
    perms: list[str] = []
    for line in raw.splitlines():
        m = re.search(r"(android\.permission\.[A-Z_]+)", line)
        if m and m.group(1) not in perms:
            perms.append(m.group(1))
    return perms


def extract_denied_permissions(adb: ADB, pkg: str) -> list[str]:
    """Permissions die angefordert aber nicht gewährt wurden."""
    raw = adb.shell(
        f"dumpsys package {shq(pkg)} | grep 'revoked\\|denied\\|not granted'",
        timeout=15,
    )
    perms: list[str] = []
    for line in raw.splitlines():
        m = re.search(r"(android\.permission\.[A-Z_]+)", line)
        if m and m.group(1) not in perms:
            perms.append(m.group(1))
    return perms


# ---------------------------------------------------------------------------
# Risiko-Scoring
# ---------------------------------------------------------------------------

def score_app_permissions(profile: AppPermissionProfile) -> AppPermissionProfile:
    """Berechnet risk_score (0–100) und füllt spyware_indicators.

    Basis: Summe der Gewichte für GENUTZTE Permissions (used_perms).
    Bonus: Spyware-Kombinationen die vollständig erfüllt sind.
    Cap: 100.
    """
    # Normalisiere auf Short-Names für Kombinationsvergleiche
    used_shorts = {_short(p) for p in profile.used_perms}
    granted_shorts = {_short(p) for p in profile.granted_perms}
    # Für Kombinations-Check: verwendet granted wenn used leer (AppOps nicht verfügbar)
    effective_shorts = used_shorts if used_shorts else granted_shorts

    score = 0
    indicators: list[str] = []

    # Einzelne Permission-Gewichte (auf used_perms)
    for perm in profile.used_perms:
        score += DANGEROUS_PERM_WEIGHTS.get(perm, 0)

    # Bonus für Spyware-Kombinationen
    for label, combo_set, bonus in SPYWARE_PERMISSION_COMBOS:
        if combo_set.issubset(effective_shorts):
            score += bonus
            indicators.append(label)

    # Sonderrechte
    if profile.is_device_admin:
        score += 30
        indicators.append("DEVICE_ADMIN")
    if profile.is_accessibility_service:
        score += 25
        indicators.append("ACCESSIBILITY_SERVICE")
    if profile.has_notification_listener:
        score += 20
        indicators.append("NOTIFICATION_LISTENER")
    if profile.has_overlay_permission:
        score += 15
        indicators.append("OVERLAY")

    profile.risk_score = min(score, 100)
    profile.spyware_indicators = list(dict.fromkeys(indicators))

    if profile.risk_score >= 70:
        profile.risk_level = "CRITICAL"
    elif profile.risk_score >= 45:
        profile.risk_level = "HIGH"
    elif profile.risk_score >= 20:
        profile.risk_level = "MEDIUM"
    else:
        profile.risk_level = "LOW"

    return profile


# ---------------------------------------------------------------------------
# Vollprofil-Extraktion
# ---------------------------------------------------------------------------

def extract_full_permission_profile(
    adb: ADB,
    pkg: str,
    st: dict,
    device_admins: list[str] | None = None,
    acc_services: list[str] | None = None,
    notif_listeners: list[str] | None = None,
    overlay_apps: list[str] | None = None,
) -> AppPermissionProfile:
    """Kombiniert alle Extraktoren für ein Paket und berechnet Score.

    Vorbefüllte Listen (device_admins etc.) vermeiden wiederholte ADB-Calls
    beim Batch-Betrieb.
    """
    profile = AppPermissionProfile(pkg=pkg)

    profile.declared_perms = extract_declared_permissions(adb, pkg)
    profile.granted_perms  = extract_granted_permissions(adb, pkg)
    profile.denied_perms   = extract_denied_permissions(adb, pkg)

    if st.get("is_root"):
        profile.used_perms = extract_used_permissions(adb, pkg)

    # Sonderrechte aus gecachten Listen oder frisch abfragen
    admins   = device_admins   if device_admins   is not None else extract_device_admins(adb)
    accs     = acc_services    if acc_services    is not None else extract_accessibility_services(adb)
    notifs   = notif_listeners if notif_listeners is not None else extract_notification_listeners(adb)
    overlays = overlay_apps    if overlay_apps    is not None else extract_overlay_apps(adb)

    profile.is_device_admin           = pkg in admins
    profile.is_accessibility_service  = any(pkg in s for s in accs)
    profile.has_notification_listener = any(pkg in s for s in notifs)
    profile.has_overlay_permission    = any(pkg in s for s in overlays)

    return score_app_permissions(profile)


# ---------------------------------------------------------------------------
# Batch-Analyse
# ---------------------------------------------------------------------------

def analyze_all_apps(
    adb: ADB,
    pkgs: list[str],
    st: dict,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> list[AppPermissionProfile]:
    """Analysiert alle Pakete. Cached Sonderrecht-Listen für Performance."""
    # Einmal global abfragen
    admins   = extract_device_admins(adb)
    accs     = extract_accessibility_services(adb)
    notifs   = extract_notification_listeners(adb)
    overlays = extract_overlay_apps(adb)

    profiles: list[AppPermissionProfile] = []
    for i, pkg in enumerate(pkgs):
        if progress_cb:
            progress_cb(i, len(pkgs), pkg)
        try:
            p = extract_full_permission_profile(
                adb, pkg, st,
                device_admins=admins, acc_services=accs,
                notif_listeners=notifs, overlay_apps=overlays,
            )
            profiles.append(p)
        except Exception:
            profiles.append(AppPermissionProfile(pkg=pkg))

    profiles.sort(key=lambda p: p.risk_score, reverse=True)
    return profiles


# ---------------------------------------------------------------------------
# Ausgabe-Formatierung
# ---------------------------------------------------------------------------

_SEP = "─" * 100


def format_permission_matrix(profiles: list[AppPermissionProfile]) -> str:
    lines: list[str] = [
        "═" * 100,
        "  PERMISSION RISK MATRIX",
        "═" * 100,
        f"  {'RISIKO':<8}  {'PAKET':<45}  {'SCORE':>5}  {'INDIKATOREN'}",
        _SEP,
    ]
    for p in profiles:
        if p.risk_level == "LOW":
            continue
        color_tag = {
            "CRITICAL": "[CRIT]",
            "HIGH":     "[HIGH]",
            "MEDIUM":   "[MED ]",
        }.get(p.risk_level, "[    ]")
        inds = ", ".join(p.spyware_indicators[:4]) if p.spyware_indicators else "—"
        lines.append(
            f"  {color_tag}  {p.pkg[:43]:<45}  {p.risk_score:>5}  {inds}"
        )
        if p.used_perms:
            top = ", ".join(_short(x) for x in p.used_perms[:5])
            lines.append(f"          {'':45}  Genutzt: {top}")

    if all(p.risk_level == "LOW" for p in profiles):
        lines.append("  Keine HIGH/CRITICAL Risiken gefunden.")
    lines += [_SEP, f"  Gesamt analysiert: {len(profiles)} Apps"]
    return "\n".join(lines)


def format_top_risky_apps(
    profiles: list[AppPermissionProfile],
    n: int = 10,
) -> str:
    top = [p for p in profiles if p.risk_level != "LOW"][:n]
    if not top:
        return "  Keine risikobehafteten Apps gefunden."
    lines = [f"  TOP {n} RISIKO-APPS:", "─" * 70]
    for i, p in enumerate(top, 1):
        inds = " | ".join(p.spyware_indicators[:3]) if p.spyware_indicators else "—"
        lines.append(f"  {i:2}. [{p.risk_level:<8}] {p.pkg[:40]:<40}  Score={p.risk_score}  {inds}")
    return "\n".join(lines)
