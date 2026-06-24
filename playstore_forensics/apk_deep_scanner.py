"""APK Deep Scanner – statische Analyse installierter APKs direkt auf dem Gerät.

Keine APK-Downloads auf den Host. Alle Analysen laufen via ADB-Shell-Befehle
auf dem Gerät selbst: aapt/aapt2, strings, unzip, grep.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from apz.adb import ADB
from apz.util import shq


# ---------------------------------------------------------------------------
# Permission-Risiko-Datenbanken
# ---------------------------------------------------------------------------

DANGEROUS_PERMS: dict[str, list[str]] = {
    "CRITICAL": [
        "READ_CONTACTS", "WRITE_CONTACTS",
        "READ_CALL_LOG", "WRITE_CALL_LOG",
        "PROCESS_OUTGOING_CALLS",
        "READ_SMS", "RECEIVE_SMS", "SEND_SMS",
        "READ_MMS", "RECEIVE_MMS",
        "ACCESS_FINE_LOCATION", "ACCESS_BACKGROUND_LOCATION",
        "CAMERA", "RECORD_AUDIO",
        "READ_PHONE_STATE", "READ_PHONE_NUMBERS",
    ],
    "HIGH": [
        "BIND_ACCESSIBILITY_SERVICE", "BIND_DEVICE_ADMIN",
        "SYSTEM_ALERT_WINDOW", "WRITE_SETTINGS",
        "REQUEST_INSTALL_PACKAGES", "INSTALL_PACKAGES",
        "GET_ACCOUNTS", "USE_CREDENTIALS", "MANAGE_ACCOUNTS",
        "BIND_NOTIFICATION_LISTENER_SERVICE",
        "NFC", "BLUETOOTH_ADMIN",
    ],
    "MEDIUM": [
        "INTERNET", "ACCESS_WIFI_STATE", "CHANGE_WIFI_STATE",
        "RECEIVE_BOOT_COMPLETED", "FOREGROUND_SERVICE",
        "WAKE_LOCK", "VIBRATE",
        "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE",
        "USE_BIOMETRIC", "USE_FINGERPRINT",
    ],
}

# Jede Kombination mit >= 2 Treffern gilt als Match
SPYWARE_COMBOS: list[tuple[str, list[str], str]] = [
    ("CLASSIC_SPYWARE",    ["READ_SMS", "READ_CONTACTS", "ACCESS_FINE_LOCATION", "RECORD_AUDIO"],
     "Klassische Spyware-Kombination"),
    ("CALL_INTERCEPTOR",   ["PROCESS_OUTGOING_CALLS", "READ_CALL_LOG", "RECORD_AUDIO"],
     "Anruf-Überwachung"),
    ("ACCOUNT_STEALER",    ["GET_ACCOUNTS", "USE_CREDENTIALS", "INTERNET"],
     "Account-Diebstahl"),
    ("DEVICE_ADMIN_ABUSE", ["BIND_DEVICE_ADMIN", "SYSTEM_ALERT_WINDOW"],
     "Device-Admin-Missbrauch"),
    ("KEYLOGGER_PROFILE",  ["BIND_ACCESSIBILITY_SERVICE", "READ_CLIPBOARD", "INTERNET"],
     "Keylogger-Profil"),
    ("BANKING_TROJAN",     ["BIND_ACCESSIBILITY_SERVICE", "READ_SMS", "SYSTEM_ALERT_WINDOW"],
     "Banking-Trojaner"),
    ("STALKERWARE",        ["ACCESS_BACKGROUND_LOCATION", "READ_CONTACTS",
                            "RECEIVE_BOOT_COMPLETED", "FOREGROUND_SERVICE"],
     "Stalkerware"),
]

KNOWN_MALWARE_STRINGS: list[bytes] = [
    b"botnet", b"c2server", b"command_and_control",
    b"exfiltrate", b"uploadToServer", b"sendLocation",
    b"removeActiveAdmin", b"lockNow", b"wipeData",
    b"getMessageBody", b"SMS_RECEIVED",
    b"CVE-20", b"local_exploit", b"privilege_escalation",
    b"keylogger", b"screen_capture_service",
    b"sms_intercept", b"call_record",
    b"hiddenApp", b"hide_icon", b"conceal",
    b"superuser", b"rootshell",
]

# Regex-Varianten (werden als Strings gegen Shell-Ausgabe getestet)
MALWARE_REGEX_STRINGS: list[str] = [
    r"DexClassLoader\s*\(",
    r"PathClassLoader\s*\(",
    r"loadDex\s*\(",
    r"Runtime\.exec\s*\(",
    r"ProcessBuilder\s*\(",
    r"getDeviceId\(\)",
    r"getSubscriberId\(\)",
    r"getLine1Number\(\)",
    r"getAllCellInfo\(\)",
]


# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

@dataclass
class ManifestInfo:
    package:                str
    min_sdk:                int = 0
    target_sdk:             int = 0
    version_name:           str = "—"
    version_code:           str = "—"
    permissions:            list[str] = field(default_factory=list)
    activities:             list[str] = field(default_factory=list)
    services:               list[str] = field(default_factory=list)
    receivers:              list[str] = field(default_factory=list)
    providers:              list[str] = field(default_factory=list)
    backup_allowed:         bool = True
    debuggable:             bool = False
    network_security_config: str = ""
    parse_method:           str = "unknown"

    def to_dict(self) -> dict:
        return {
            "package":         self.package,
            "min_sdk":         self.min_sdk,
            "target_sdk":      self.target_sdk,
            "version_name":    self.version_name,
            "version_code":    self.version_code,
            "permissions":     self.permissions,
            "activities":      self.activities,
            "services":        self.services,
            "receivers":       self.receivers,
            "providers":       self.providers,
            "backup_allowed":  self.backup_allowed,
            "debuggable":      self.debuggable,
            "parse_method":    self.parse_method,
        }


@dataclass
class ApkDeepScanResult:
    package:           str
    apk_path:          str
    manifest:          Optional[ManifestInfo] = None
    perm_analysis:     dict = field(default_factory=dict)
    obfuscation:       dict = field(default_factory=dict)
    malware_strings:   list[str] = field(default_factory=list)
    hardcoded_ips:     list[str] = field(default_factory=list)
    hardcoded_urls:    list[str] = field(default_factory=list)
    hardcoded_secrets: list[str] = field(default_factory=list)
    risk_level:        str = "LOW"
    risk_reasons:      list[str] = field(default_factory=list)

    def to_text(self) -> str:
        sep = "─" * 68
        lines = [
            f"  ┌─ [{self.risk_level}] {self.package}",
            f"  │  APK: {self.apk_path}",
        ]
        if self.manifest:
            m = self.manifest
            lines += [
                f"  │  SDK: min={m.min_sdk} target={m.target_sdk}  "
                f"v{m.version_name} (code {m.version_code})",
                f"  │  Permissions: {len(m.permissions)}  "
                f"Services: {len(m.services)}  "
                f"Receivers: {len(m.receivers)}",
            ]
            if m.debuggable:
                lines.append("  │  ⚠ DEBUGGABLE=true")
            if m.backup_allowed:  # backup_allowed=True ist Risiko
                lines.append("  │  ⚠ android:allowBackup=true (Daten via ADB sicherbar)")

        pa = self.perm_analysis
        if pa:
            lines.append(
                f"  │  Perm-Score: {pa.get('risk_score', 0)}/100  "
                f"CRIT={pa.get('critical_count', 0)} "
                f"HIGH={pa.get('high_count', 0)} "
                f"MED={pa.get('medium_count', 0)}"
            )
            for combo in pa.get("matched_combos", []):
                lines.append(f"  │  ⚠ KOMBINATION: {combo}")

        ob = self.obfuscation
        if ob.get("is_obfuscated"):
            lines.append(f"  │  🔒 Obfuskiert: {', '.join(ob.get('obfuscation_indicators', []))}")
        if ob.get("dynamic_loading"):
            lines.append("  │  ⚠ Dynamisches Laden (DexClassLoader/PathClassLoader)")
        if ob.get("native_code"):
            lines.append("  │  ⚠ Native Libraries (.so)")
        if ob.get("base64_blobs", 0) > 3:
            lines.append(f"  │  ⚠ {ob['base64_blobs']} Base64-Blöcke (verschleierter Payload?)")

        if self.malware_strings:
            lines.append(f"  │  🔴 Malware-Strings: {', '.join(self.malware_strings[:5])}")
        if self.hardcoded_ips:
            lines.append(f"  │  📡 Hardcoded IPs: {', '.join(self.hardcoded_ips[:4])}")
        if self.hardcoded_secrets:
            lines.append(f"  │  🔑 Secret-Strings: {len(self.hardcoded_secrets)}")

        if self.risk_reasons:
            lines.append("  │  Risikogründe:")
            for r in self.risk_reasons:
                lines.append(f"  │    → {r}")

        lines.append("  └" + sep[2:])
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "package":           self.package,
            "apk_path":          self.apk_path,
            "manifest":          self.manifest.to_dict() if self.manifest else None,
            "perm_analysis":     self.perm_analysis,
            "obfuscation":       self.obfuscation,
            "malware_strings":   self.malware_strings,
            "hardcoded_ips":     self.hardcoded_ips,
            "hardcoded_urls":    self.hardcoded_urls,
            "hardcoded_secrets": self.hardcoded_secrets,
            "risk_level":        self.risk_level,
            "risk_reasons":      self.risk_reasons,
        }


# ---------------------------------------------------------------------------
# 1. Manifest-Extraktion (drei Methoden)
# ---------------------------------------------------------------------------

def extract_manifest_aapt(adb: ADB, apk_path: str, root: bool = False) -> str:
    """Nutzt aapt/aapt2 auf dem Gerät für strukturierte Manifest-Ausgabe."""
    for tool in ("aapt", "aapt2", "/system/bin/aapt", "/system/bin/aapt2"):
        which = adb.shell(f"which {tool} 2>/dev/null || command -v {tool} 2>/dev/null",
                          root=root, timeout=8)
        if which.strip():
            out = adb.shell(f"{tool} dump badging {shq(apk_path)} 2>/dev/null",
                            root=root, timeout=30)
            if out.strip() and "error" not in out[:40].lower():
                return out
    return ""


def extract_manifest_raw(adb: ADB, apk_path: str, root: bool = False) -> str:
    """Extrahiert lesbare Strings aus der binären AndroidManifest.xml im APK."""
    # unzip -p gibt den Datei-Inhalt auf stdout; strings filtert druckbare Zeichen
    out = adb.shell(
        f"unzip -p {shq(apk_path)} AndroidManifest.xml 2>/dev/null | "
        "strings -n 4 2>/dev/null | head -n 500",
        root=root, timeout=25,
    )
    if not out.strip():
        # Fallback: direkte strings-Analyse der gesamten APK
        out = adb.shell(
            f"strings -n 6 {shq(apk_path)} 2>/dev/null | "
            "grep -E 'android\\.|permission\\.|activity|service|receiver' | head -n 300",
            root=root, timeout=25,
        )
    return out


def extract_manifest_dexdump(adb: ADB, apk_path: str, root: bool = False) -> str:
    """Analysiert DEX-Bytecode mit dexdump (falls verfügbar) auf Klassen-Ebene."""
    which = adb.shell("which dexdump 2>/dev/null", root=root, timeout=8)
    if not which.strip():
        return ""
    # Extrahiere classes.dex temporär, dann dexdump
    tmp_dex = "/sdcard/_psf_classes.dex"
    adb.shell(f"unzip -p {shq(apk_path)} classes.dex > {tmp_dex} 2>/dev/null",
              root=root, timeout=20)
    out = adb.shell(f"dexdump -d {tmp_dex} 2>/dev/null | head -n 600",
                    root=root, timeout=30)
    adb.shell(f"rm -f {tmp_dex} 2>/dev/null")
    return out


# ---------------------------------------------------------------------------
# 2. aapt-Output-Parser
# ---------------------------------------------------------------------------

def parse_aapt_output(raw: str, pkg: str) -> ManifestInfo:
    """Extrahiert strukturierte ManifestInfo aus aapt dump badging Output."""
    info = ManifestInfo(package=pkg, parse_method="aapt")

    # package: name='...' versionCode='...' versionName='...'
    m = re.search(r"package: name='([^']+)'", raw)
    if m:
        info.package = m.group(1)
    m = re.search(r"versionCode=['\"]?([^'\" ]+)['\"]?", raw)
    if m:
        info.version_code = m.group(1)
    m = re.search(r"versionName=['\"]?([^'\" ]+)['\"]?", raw)
    if m:
        info.version_name = m.group(1)

    # sdkVersion / targetSdkVersion  (aapt nutzt ':' statt '=', Wert in ' oder ")
    m = re.search(r"sdkVersion:['\"]?(\d+)['\"]?", raw)
    if m:
        info.min_sdk = int(m.group(1))
    m = re.search(r"targetSdkVersion:['\"]?(\d+)['\"]?", raw)
    if m:
        info.target_sdk = int(m.group(1))

    # uses-permission: name='...' oder "..." (aapt und aapt2 unterschiedlich)
    info.permissions = list(dict.fromkeys(
        re.findall(r"uses-permission: name=['\"]android\.permission\.([^'\"]+)['\"]", raw)
    ))

    # application-debuggable / application-backup
    info.debuggable     = "application-debuggable" in raw
    info.backup_allowed = "application-backup" not in raw  # nicht explizit deaktiviert

    # launchable-activity / activity / service / receiver / provider
    info.activities = list(dict.fromkeys(re.findall(r"launchable-activity: name='([^']+)'", raw)))
    for tag in ("activity", "service", "receiver", "provider"):
        found = list(dict.fromkeys(re.findall(rf"{tag}: name='([^']+)'", raw)))
        setattr(info, tag + "s" if tag != "activity" else "activities",
                getattr(info, tag + "s" if tag != "activity" else "activities") + found)

    return info


def _parse_raw_manifest_strings(raw: str, pkg: str) -> ManifestInfo:
    """Fallback-Parser für rohe strings-Ausgabe des Manifests."""
    info = ManifestInfo(package=pkg, parse_method="strings")
    perms: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        m = re.match(r"android\.permission\.(\w+)", line)
        if m:
            perms.append(m.group(1))
        if "allowBackup" in line and "false" in line:
            info.backup_allowed = False
        if "debuggable" in line and "true" in line:
            info.debuggable = True
        m = re.search(r"minSdkVersion\s*[=:]\s*(\d+)", line)
        if m:
            info.min_sdk = int(m.group(1))
        m = re.search(r"targetSdkVersion\s*[=:]\s*(\d+)", line)
        if m:
            info.target_sdk = int(m.group(1))
    info.permissions = list(dict.fromkeys(perms))
    return info


def _get_permissions_via_pm(adb: ADB, pkg: str, root: bool = False) -> list[str]:
    """Liest Permissions aus dumpsys package als zuverlässigen Fallback."""
    out = adb.shell(
        f"dumpsys package {shq(pkg)} | grep -E 'granted=true|android\\.permission\\.'",
        root=root, timeout=20,
    )
    perms: list[str] = []
    for m in re.finditer(r"android\.permission\.(\w+)", out):
        p = m.group(1)
        if p not in perms:
            perms.append(p)
    return perms


# ---------------------------------------------------------------------------
# 3. Permission-Risiko-Scoring
# ---------------------------------------------------------------------------

def score_permissions(perms: list[str]) -> dict:
    """Berechnet Risk-Score und erkennt Spyware-Kombinationen."""
    perm_set = {p.upper().replace("ANDROID.PERMISSION.", "") for p in perms}

    critical_hits = [p for p in DANGEROUS_PERMS["CRITICAL"] if p in perm_set]
    high_hits     = [p for p in DANGEROUS_PERMS["HIGH"]     if p in perm_set]
    medium_hits   = [p for p in DANGEROUS_PERMS["MEDIUM"]   if p in perm_set]

    score = (
        len(critical_hits) * 15 +
        len(high_hits)     * 8  +
        len(medium_hits)   * 3
    )
    score = min(score, 100)

    matched_combos: list[str] = []
    for combo_name, required, description in SPYWARE_COMBOS:
        hits = sum(1 for p in required if p in perm_set)
        # Kombination gilt bei ≥ ceil(2/3) der Permissions
        threshold = max(2, len(required) * 2 // 3)
        if hits >= threshold:
            matched_combos.append(f"{combo_name} ({description})")
            score = min(score + 20, 100)

    if matched_combos:
        risk_level = "CRITICAL" if score >= 70 else "HIGH"
    elif score >= 60:
        risk_level = "HIGH"
    elif score >= 30:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "critical_count":  len(critical_hits),
        "high_count":      len(high_hits),
        "medium_count":    len(medium_hits),
        "critical_perms":  critical_hits,
        "high_perms":      high_hits,
        "risk_score":      score,
        "matched_combos":  matched_combos,
        "risk_level":      risk_level,
    }


# ---------------------------------------------------------------------------
# 4. Obfuskations-Detektion
# ---------------------------------------------------------------------------

_BASE64_RE = re.compile(r'[A-Za-z0-9+/]{40,}={0,2}')
_SHORT_CLASS_RE = re.compile(r'\b[a-z]{1,2}\.[a-z]{1,2}(?:\.[a-z]{1,2})+\b')


def detect_obfuscation(adb: ADB, apk_path: str, root: bool = False) -> dict:
    """Erkennt Obfuskierung und verdächtige Code-Muster via strings-Analyse."""
    raw = adb.shell(
        f"strings -n 5 {shq(apk_path)} 2>/dev/null | head -n 3000",
        root=root, timeout=35,
    )
    if not raw.strip():
        return {
            "is_obfuscated": False, "obfuscation_indicators": [],
            "dynamic_loading": False, "native_code": False,
            "crypto_usage": False, "reflection_usage": False, "base64_blobs": 0,
        }

    indicators: list[str] = []

    # Kurze Klassen-/Methodennamen → Proguard/R8
    short_matches = _SHORT_CLASS_RE.findall(raw)
    if len(short_matches) >= 10:
        indicators.append(f"Proguard/R8 ({len(short_matches)} kurze Bezeichner)")

    # Reflection
    reflection_hits = [kw for kw in ("getDeclaredMethod", "getDeclaredField",
                                     "Class.forName", "invoke(") if kw in raw]
    if reflection_hits:
        indicators.append(f"Reflection ({', '.join(reflection_hits[:3])})")

    # Dyn. Class-Loading
    dyn_loading = any(kw in raw for kw in (
        "DexClassLoader", "PathClassLoader", "InMemoryDexClassLoader", "loadDex",
    ))

    # Native Code
    native = any(kw in raw for kw in ("System.loadLibrary", "System.load(", ".so"))

    # Crypto
    crypto = any(kw in raw for kw in (
        "AES", "DES", "SecretKeySpec", "Cipher.getInstance", "KeyGenerator",
        "MessageDigest", "SecretKey",
    ))

    # Base64-Blöcke (verschleierter Payload)
    b64_blobs = len(_BASE64_RE.findall(raw))

    if dyn_loading:
        indicators.append("Dynamisches Laden")
    if native:
        indicators.append("Native Libs")
    if b64_blobs > 5:
        indicators.append(f"{b64_blobs} Base64-Blöcke")
    if crypto and dyn_loading:
        indicators.append("Crypto + DynLoading (Loader-Pattern)")

    return {
        "is_obfuscated":          len(indicators) >= 2,
        "obfuscation_indicators": indicators,
        "dynamic_loading":        dyn_loading,
        "native_code":            native,
        "crypto_usage":           crypto,
        "reflection_usage":       bool(reflection_hits),
        "base64_blobs":           b64_blobs,
    }


# ---------------------------------------------------------------------------
# 5. Malware-String-Suche
# ---------------------------------------------------------------------------

def check_malware_strings(adb: ADB, apk_path: str, root: bool = False) -> list[str]:
    """Sucht nach bekannten Malware-Indikatoren im APK-Binary via grep."""
    found: list[str] = []

    # Gebündelte grep-Suche: alle Patterns in einem Aufruf
    pattern_str = "|".join(
        s.decode("utf-8", errors="ignore") for s in KNOWN_MALWARE_STRINGS
    )
    # grep -c zählt matching lines; -l gibt Dateinamen; wir wollen die Matches selbst
    out = adb.shell(
        f"strings -n 4 {shq(apk_path)} 2>/dev/null | "
        f"grep -iE {shq(pattern_str)} 2>/dev/null | head -n 40",
        root=root, timeout=30,
    )
    for line in out.splitlines():
        line = line.strip()
        if line and line not in found:
            found.append(line[:120])

    # Regex-Patterns via grep auf Device
    for pattern in MALWARE_REGEX_STRINGS:
        hit = adb.shell(
            f"strings -n 4 {shq(apk_path)} 2>/dev/null | "
            f"grep -E {shq(pattern)} 2>/dev/null | head -n 3",
            root=root, timeout=15,
        )
        for line in hit.splitlines():
            line = line.strip()
            if line and line not in found:
                found.append(line[:120])

    return found


# ---------------------------------------------------------------------------
# 6. Netzwerk-Sicherheits-Config-Analyse
# ---------------------------------------------------------------------------

def extract_network_security_config(adb: ADB, apk_path: str, root: bool = False) -> dict:
    """Parst network_security_config.xml aus dem APK.

    Schwachstellen: cleartext traffic erlaubt, user-CAs vertraut (SSL-Pinning-Bypass).
    """
    raw = adb.shell(
        f"unzip -p {shq(apk_path)} res/xml/network_security_config.xml 2>/dev/null | "
        "strings 2>/dev/null",
        root=root, timeout=20,
    )
    if not raw.strip():
        return {"found": False}

    result = {
        "found":                    True,
        "cleartext_permitted":      "cleartextTrafficPermitted" in raw and "true" in raw,
        "user_ca_trusted":          "user" in raw and "certificates" in raw,
        "pin_set_found":            "pin-set" in raw or "pin:" in raw,
        "custom_trust_anchors":     "trust-anchors" in raw,
        "raw_snippet":              raw[:300],
    }

    result["risk"] = (
        "HIGH"   if result["cleartext_permitted"] or result["user_ca_trusted"] else
        "MEDIUM" if result["custom_trust_anchors"] else
        "LOW"
    )
    return result


# ---------------------------------------------------------------------------
# Master-Funktionen
# ---------------------------------------------------------------------------

def deep_scan_apk(adb: ADB, pkg: str, st: dict) -> ApkDeepScanResult:
    """Vollständiger Deep-Scan eines APKs. APK-Pfad via pm path."""
    is_root = st.get("is_root", False)

    # APK-Pfad ermitteln
    pm_out = adb.shell(f"pm path {shq(pkg)}", timeout=10)
    m = re.search(r"package:(.+)", pm_out)
    apk_path = m.group(1).strip() if m else ""

    result = ApkDeepScanResult(package=pkg, apk_path=apk_path)

    if not apk_path:
        result.risk_level = "UNKNOWN"
        result.risk_reasons.append("APK-Pfad nicht ermittelbar")
        return result

    # --- Manifest ---
    manifest: Optional[ManifestInfo] = None
    aapt_raw = extract_manifest_aapt(adb, apk_path, root=is_root)
    if aapt_raw.strip():
        manifest = parse_aapt_output(aapt_raw, pkg)
    else:
        raw_strings = extract_manifest_raw(adb, apk_path, root=is_root)
        if raw_strings.strip():
            manifest = _parse_raw_manifest_strings(raw_strings, pkg)
        else:
            manifest = ManifestInfo(package=pkg, parse_method="pm_dump")

    # Permissions aus pm dump wenn Manifest keine liefert
    if not manifest.permissions:
        manifest.permissions = _get_permissions_via_pm(adb, pkg, root=is_root)

    result.manifest = manifest

    # --- Permission-Scoring ---
    result.perm_analysis = score_permissions(manifest.permissions)

    # --- Obfuskation ---
    result.obfuscation = detect_obfuscation(adb, apk_path, root=is_root)

    # --- Malware-Strings ---
    result.malware_strings = check_malware_strings(adb, apk_path, root=is_root)

    # --- Hardcoded IPs / URLs / Secrets ---
    _ip_re  = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _url_re = re.compile(r"https?://[^\s\"'<>]{5,100}")
    _key_re = re.compile(r"(?i)(?:api[_-]?key|secret|password|token|auth)\s*[=:]\s*\S{6,}")

    strings_raw = adb.shell(
        f"strings -n 6 {shq(apk_path)} 2>/dev/null | head -n 3000",
        root=is_root, timeout=35,
    )
    all_ips = [ip for ip in _ip_re.findall(strings_raw)
               if not ip.startswith(("127.", "10.", "0.0.0.0"))]
    result.hardcoded_ips     = list(dict.fromkeys(all_ips))[:20]
    result.hardcoded_urls    = list(dict.fromkeys(_url_re.findall(strings_raw)))[:20]
    result.hardcoded_secrets = list(dict.fromkeys(_key_re.findall(strings_raw)))[:10]

    # --- Network Security Config ---
    nsc = extract_network_security_config(adb, apk_path, root=is_root)
    if nsc.get("found") and nsc.get("risk") in ("HIGH", "MEDIUM"):
        result.risk_reasons.append(
            f"NetworkSecurityConfig: cleartext={nsc.get('cleartext_permitted')}, "
            f"user-CA={nsc.get('user_ca_trusted')}"
        )

    # --- Gesamtrisiko bestimmen ---
    reasons: list[str] = []

    perm_lvl = result.perm_analysis.get("risk_level", "LOW")
    if perm_lvl in ("CRITICAL", "HIGH"):
        reasons.append(f"Permission-Risiko {perm_lvl}: {result.perm_analysis.get('risk_score')}/100")
    for combo in result.perm_analysis.get("matched_combos", []):
        reasons.append(f"Spyware-Kombination: {combo}")

    if result.malware_strings:
        reasons.append(f"Malware-Strings ({len(result.malware_strings)}): "
                       f"{', '.join(result.malware_strings[:3])}")
    if result.obfuscation.get("dynamic_loading"):
        reasons.append("Dynamisches Code-Laden (DexClassLoader)")
    if result.obfuscation.get("is_obfuscated") and result.malware_strings:
        reasons.append("Obfuskierung + Malware-Strings → starkes Indiz")
    if result.hardcoded_ips:
        reasons.append(f"{len(result.hardcoded_ips)} hardcoded IPs: "
                       f"{', '.join(result.hardcoded_ips[:3])}")
    if manifest.debuggable:
        reasons.append("android:debuggable=true (Release-App!)")
    if result.obfuscation.get("base64_blobs", 0) > 8:
        reasons.append(f"{result.obfuscation['base64_blobs']} Base64-Blöcke (Payload?)")

    result.risk_reasons = reasons

    # Stufenberechnung
    score = result.perm_analysis.get("risk_score", 0)
    if result.malware_strings:
        score += 30
    if result.obfuscation.get("dynamic_loading"):
        score += 15
    if result.perm_analysis.get("matched_combos"):
        score += 25
    if manifest.debuggable:
        score += 10

    result.risk_level = (
        "CRITICAL" if score >= 80 else
        "HIGH"     if score >= 50 else
        "MEDIUM"   if score >= 25 else
        "LOW"
    )
    return result


def batch_deep_scan(
    adb: ADB,
    pkgs: list[str],
    st: dict,
    progress_cb=None,
) -> list[ApkDeepScanResult]:
    """Scannt alle Pakete, ruft progress_cb(i, total, pkg) auf."""
    results: list[ApkDeepScanResult] = []
    for i, pkg in enumerate(pkgs):
        if progress_cb:
            progress_cb(i, len(pkgs), pkg)
        try:
            r = deep_scan_apk(adb, pkg, st)
            results.append(r)
        except Exception:
            results.append(ApkDeepScanResult(
                package=pkg, apk_path="", risk_level="ERROR",
                risk_reasons=["Scan-Fehler"],
            ))
    return results


def filter_noteworthy(results: list[ApkDeepScanResult]) -> list[ApkDeepScanResult]:
    """Gibt nur Ergebnisse mit risk_level != LOW zurück, sortiert nach Risiko."""
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "ERROR": 3}
    noteworthy = [r for r in results if r.risk_level not in ("LOW",)]
    noteworthy.sort(key=lambda r: order.get(r.risk_level, 9))
    return noteworthy
