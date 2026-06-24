"""Netzwerk-Forensik – Verbindungen, DNS, Traffic, Security-Configs.

Quellen (Root bevorzugt, Shell-Fallback):
  /proc/net/tcp|tcp6|udp  – aktive Sockets mit UID
  /proc/net/xt_qtaguid    – Traffic-Statistiken per App
  logcat                  – DNS-Auflösungen
  APK network_security_config.xml – Cleartext / Pinning

Keine externen Libs, kein Pydantic. Nur stdlib + apz/adb.ADB.
"""
from __future__ import annotations

import re
import struct
import socket
import time
from dataclasses import dataclass, field
from apz.adb import ADB
from apz.util import shq


# ---------------------------------------------------------------------------
# Datenklassen
# ---------------------------------------------------------------------------

@dataclass
class NetworkConnection:
    proto:       str        # tcp | udp | tcp6 | udp6
    local_addr:  str        # IP:PORT
    remote_addr: str        # IP:PORT  oder  "0.0.0.0:0"
    state:       str        # ESTABLISHED | LISTEN | TIME_WAIT | CLOSE_WAIT | …
    uid:         str
    pkg:         str = ""
    pid:         str = ""
    process:     str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class DnsEntry:
    hostname:    str
    resolved_ip: str
    timestamp:   str
    pkg:         str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class AppTrafficStats:
    pkg:        str
    uid:        str
    rx_bytes:   int
    tx_bytes:   int
    rx_packets: int
    tx_packets: int

    @property
    def ratio(self) -> float:
        return self.tx_bytes / max(self.rx_bytes, 1)

    def rx_mb(self) -> float:
        return self.rx_bytes / 1_048_576

    def tx_mb(self) -> float:
        return self.tx_bytes / 1_048_576

    def to_dict(self) -> dict:
        return {**self.__dict__, "ratio": round(self.ratio, 2)}


@dataclass
class NetworkSecurityConfig:
    pkg:              str
    allows_cleartext: bool
    pinned_domains:   list[str] = field(default_factory=list)
    custom_cas:       bool = False
    raw:              str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


# ---------------------------------------------------------------------------
# Bekannte Bad-IPs und Tracker-Domains
# ---------------------------------------------------------------------------

KNOWN_BAD_IPS: set[str] = {
    # Tor-Exit-Nodes (Beispiel-Range)
    "185.220.101.0", "185.220.101.1", "185.220.101.34",
    "185.220.101.47", "185.220.101.180",
    # Bekannte C2-Ranges
    "194.165.16.0", "194.165.16.11",
    "45.142.212.0", "45.142.212.100",
    "91.108.4.0",   "91.108.56.0",     # diverse C2
    "176.119.0.1",  "185.234.218.0",
}

KNOWN_TRACKERS: set[str] = {
    "adjust.com", "app.adjust.com",
    "appsflyer.com", "t.appsflyer.com",
    "flurry.com", "data.flurry.com",
    "amplitude.com", "api.amplitude.com",
    "mixpanel.com", "api.mixpanel.com",
    "hotjar.com",
    "doubleclick.net", "stats.g.doubleclick.net",
    "admob.com", "googleadservices.com",
    "scorecardresearch.com",
    "chartboost.com", "ironsrc.com",
    "mopub.com", "ads.mopub.com",
    "branch.io", "api2.branch.io",
    "firebase.io", "firebaseio.com",
    "crashlytics.com", "settings.crashlytics.com",
    "kochava.com", "control.kochava.com",
    "singular.net", "sdk.singular.net",
    "applovin.com", "rt.applovin.com",
}

# TCP-Zustände aus Linux /proc/net/tcp
_TCP_STATES: dict[str, str] = {
    "01": "ESTABLISHED", "02": "SYN_SENT",   "03": "SYN_RECV",
    "04": "FIN_WAIT1",   "05": "FIN_WAIT2",  "06": "TIME_WAIT",
    "07": "CLOSE",       "08": "CLOSE_WAIT", "09": "LAST_ACK",
    "0A": "LISTEN",      "0B": "CLOSING",
}

# Ports die normal/erwartet sind
_NORMAL_PORTS: set[int] = {
    80, 443, 5228, 5229, 5230,  # HTTP(S) + GCM/FCM
    8080, 8443,                  # Alt-HTTP(S)
    53, 853,                     # DNS + DoT
    25, 465, 587,                # E-Mail
}


# ---------------------------------------------------------------------------
# Adress-Dekoder
# ---------------------------------------------------------------------------

def _hex_to_ip(hex_addr: str) -> str:
    """Linux /proc/net/tcp Hex-Adresse → IP:Port (Little-Endian IPv4).

    Format: "0F02000A:1F40"  →  "10.0.2.15:8000"
    IPv6 hat 32 Hex-Zeichen vor dem Doppelpunkt.
    """
    try:
        addr, port_hex = hex_addr.split(":")
        port = int(port_hex, 16)
        if len(addr) == 8:                          # IPv4 (LE)
            raw = bytes.fromhex(addr)[::-1]         # Little-Endian umkehren
            ip  = socket.inet_ntoa(raw)
        else:                                        # IPv6 (4×LE 32-bit words)
            parts = [addr[i:i+8] for i in range(0, 32, 8)]
            raw   = b"".join(bytes.fromhex(p)[::-1] for p in parts)
            ip    = socket.inet_ntop(socket.AF_INET6, raw)
        return f"{ip}:{port}"
    except Exception:
        return hex_addr


# Modul-globaler Cache: {f"{adb_id}:{uid}": pkg} – wird bei Gerätewechsel nicht
# automatisch geleert, aber adb_id ändert sich mit der ADB-Instanz.
_UID_PKG_CACHE: dict[str, str] = {}


def _uid_to_package(adb: ADB, uid: str) -> str:
    """Mappt Linux-UID auf Android-Paketnamen via dumpsys package."""
    if not uid.isdigit():
        return f"uid:{uid}"

    cache_key = f"{id(adb)}:{uid}"
    if cache_key in _UID_PKG_CACHE:
        return _UID_PKG_CACHE[cache_key]

    out = adb.shell(f"pm list packages --uid {uid} 2>/dev/null", timeout=10)
    m   = re.search(r"package:(\S+)", out)
    if m:
        _UID_PKG_CACHE[cache_key] = m.group(1)
        return m.group(1)

    out2 = adb.shell(
        f"dumpsys package | grep -B10 'userId={uid}\\b' | grep 'Package \\[' | tail -1",
        timeout=15,
    )
    m2 = re.search(r"Package \[([^\]]+)\]", out2)
    pkg = m2.group(1) if m2 else f"uid:{uid}"
    _UID_PKG_CACHE[cache_key] = pkg
    return pkg


def _build_uid_map(adb: ADB) -> dict[str, str]:
    """Liest alle Pakete + UIDs auf einmal → {uid: pkg}."""
    uid_map: dict[str, str] = {}
    out = adb.shell("pm list packages -U 2>/dev/null", timeout=20)
    for line in out.splitlines():
        # "package:com.example  uid:10123"
        pm = re.search(r"package:(\S+).*uid:(\d+)", line)
        if pm:
            uid_map[pm.group(2)] = pm.group(1)
    return uid_map


# ---------------------------------------------------------------------------
# Verbindungen
# ---------------------------------------------------------------------------

def _parse_proc_net(raw: str, proto: str, uid_map: dict[str, str]) -> list[NetworkConnection]:
    """Parst /proc/net/tcp|udp Output."""
    conns: list[NetworkConnection] = []
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 10 or not parts[0].endswith(":"):
            continue
        try:
            local  = _hex_to_ip(parts[1])
            remote = _hex_to_ip(parts[2])
            state  = _TCP_STATES.get(parts[3].upper(), parts[3])
            uid    = parts[7]
            pkg    = uid_map.get(uid, f"uid:{uid}")
            conns.append(NetworkConnection(
                proto=proto, local_addr=local, remote_addr=remote,
                state=state, uid=uid, pkg=pkg,
            ))
        except (IndexError, ValueError):
            continue
    return conns


def extract_active_connections(adb: ADB, st: dict) -> list[NetworkConnection]:
    """Aktive TCP/UDP-Verbindungen mit Paket-Zuordnung.

    Root-Pfad: /proc/net/tcp|tcp6|udp direkt lesen (vollständige UID-Info).
    Fallback: `ss -tupn` oder `netstat -tupn`.
    """
    uid_map = _build_uid_map(adb)
    conns: list[NetworkConnection] = []
    is_root = st.get("is_root", False)

    if is_root:
        for proto, path in [("tcp", "/proc/net/tcp"), ("tcp6", "/proc/net/tcp6"),
                             ("udp", "/proc/net/udp"), ("udp6", "/proc/net/udp6")]:
            raw = adb.shell(f"cat {path} 2>/dev/null", root=True, timeout=15)
            if raw.strip():
                conns.extend(_parse_proc_net(raw, proto, uid_map))
    else:
        # `ss` Fallback
        ss_out = adb.shell("ss -tupn 2>/dev/null", timeout=15)
        if ss_out.strip():
            for line in ss_out.splitlines():
                # Netid  State   Recv-Q Send-Q  Local Address:Port  Peer Address:Port  Process
                parts = line.split()
                if len(parts) < 5 or parts[0] in ("Netid", "State"):
                    continue
                proto  = parts[0].lower()
                state  = parts[1]
                local  = parts[4] if len(parts) > 4 else "?"
                remote = parts[5] if len(parts) > 5 else "0.0.0.0:0"
                # Extrahiere pid/process aus "users:(("app",pid=1234,fd=5))"
                pid = ""
                proc = ""
                pm = re.search(r'"([^"]+)",pid=(\d+)', line)
                if pm:
                    proc = pm.group(1)
                    pid  = pm.group(2)
                uid = ""
                conns.append(NetworkConnection(
                    proto=proto, local_addr=local, remote_addr=remote,
                    state=state, uid=uid, pkg=proc or "unknown",
                    pid=pid, process=proc,
                ))
        else:
            # netstat Fallback
            ns_out = adb.shell("netstat -tupn 2>/dev/null", timeout=15)
            for line in ns_out.splitlines():
                parts = line.split()
                if len(parts) < 6 or parts[0] in ("Proto", "Active"):
                    continue
                proto  = parts[0].lower().rstrip("6")
                local  = parts[3]
                remote = parts[4]
                state  = parts[5] if len(parts) > 5 else "?"
                pid_prog = parts[-1] if parts[-1] != "-" else ""
                pkg = pid_prog.split("/")[-1] if "/" in pid_prog else pid_prog
                conns.append(NetworkConnection(
                    proto=proto, local_addr=local, remote_addr=remote,
                    state=state, uid="", pkg=pkg,
                ))

    return conns


def extract_listening_ports(adb: ADB, st: dict) -> list[NetworkConnection]:
    """Nur LISTEN-State – lokale Server auf dem Gerät."""
    all_conns = extract_active_connections(adb, st)
    return [c for c in all_conns if c.state in ("LISTEN", "0A")]


# ---------------------------------------------------------------------------
# DNS-Cache
# ---------------------------------------------------------------------------

def extract_dns_cache(adb: ADB, st: dict) -> list[DnsEntry]:
    """DNS-Auflösungen aus mehreren Quellen zusammenführen."""
    entries: list[DnsEntry] = []
    seen: set[str] = set()
    is_root = st.get("is_root", False)

    # Quelle 1: /proc/net/dns_resolver (root, seltener verfügbar)
    if is_root:
        raw = adb.shell("cat /proc/net/dns_resolver 2>/dev/null", root=True, timeout=10)
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                key = f"{parts[0]}:{parts[1]}"
                if key not in seen:
                    seen.add(key)
                    entries.append(DnsEntry(hostname=parts[0], resolved_ip=parts[1], timestamp="—"))

    # Quelle 2: logcat DNS-Events
    logcat_raw = adb.shell(
        "logcat -d -b main,system -s 'NetdEventListenerService','DnsResolver','netd' 2>/dev/null"
        " | grep -iE 'hostname|dns|resolv|lookup' | tail -300",
        timeout=20,
    )
    # Format: "... hostname=example.com ip=1.2.3.4 ..."
    for line in logcat_raw.splitlines():
        ts_m = re.search(r"^(\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
        ts   = ts_m.group(1) if ts_m else "—"
        hm   = re.search(r"hostname[=:][\s]*([a-zA-Z0-9._-]+\.[a-z]{2,})", line, re.I)
        im   = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
        if hm and im:
            key = f"{hm.group(1)}:{im.group(1)}"
            if key not in seen:
                seen.add(key)
                entries.append(DnsEntry(hostname=hm.group(1), resolved_ip=im.group(1), timestamp=ts))

    # Quelle 3: Allgemeines logcat-grep nach IP-Hostname-Paaren
    if not entries:
        broad = adb.shell(
            "logcat -d | grep -oE '[a-zA-Z0-9._-]+\\.[a-z]{2,}.*[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+'"
            " | head -100",
            timeout=20,
        )
        for line in broad.splitlines():
            hm = re.search(r"([a-zA-Z0-9._-]+\.[a-z]{2,})", line)
            im = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
            if hm and im:
                key = f"{hm.group(1)}:{im.group(1)}"
                if key not in seen:
                    seen.add(key)
                    entries.append(DnsEntry(hostname=hm.group(1), resolved_ip=im.group(1), timestamp="—"))

    return entries[:500]  # Limit


# ---------------------------------------------------------------------------
# Traffic-Statistiken
# ---------------------------------------------------------------------------

def extract_traffic_stats(adb: ADB, st: dict) -> list[AppTrafficStats]:
    """Traffic-Statistiken pro App aus mehreren Quellen."""
    stats: list[AppTrafficStats] = []
    uid_map = _build_uid_map(adb)
    is_root = st.get("is_root", False)

    # Quelle 1: /proc/net/xt_qtaguid/stats (root, Android < 10)
    if is_root:
        raw = adb.shell("cat /proc/net/xt_qtaguid/stats 2>/dev/null", root=True, timeout=15)
        if raw.strip():
            # Format: idx iface acct_tag_hex uid_tag_int cnt_set rx_bytes rx_packets tx_bytes tx_packets ...
            uid_agg: dict[str, list[int]] = {}
            for line in raw.splitlines():
                parts = line.split()
                if len(parts) < 9 or not parts[3].isdigit():
                    continue
                uid = parts[3]
                try:
                    rx_b = int(parts[5])
                    rx_p = int(parts[6])
                    tx_b = int(parts[7])
                    tx_p = int(parts[8])
                except (ValueError, IndexError):
                    continue
                if uid not in uid_agg:
                    uid_agg[uid] = [0, 0, 0, 0]
                uid_agg[uid][0] += rx_b
                uid_agg[uid][1] += rx_p
                uid_agg[uid][2] += tx_b
                uid_agg[uid][3] += tx_p
            for uid, (rx_b, rx_p, tx_b, tx_p) in uid_agg.items():
                pkg = uid_map.get(uid, f"uid:{uid}")
                stats.append(AppTrafficStats(pkg=pkg, uid=uid,
                                             rx_bytes=rx_b, tx_bytes=tx_b,
                                             rx_packets=rx_p, tx_packets=tx_p))

    # Quelle 2: dumpsys netstats (Shell, keine Root nötig)
    if not stats:
        ns_raw = adb.shell("dumpsys netstats detail 2>/dev/null", timeout=30)
        # Suche nach: UID=10123 ... rb=1234567 ... tb=7654321
        for m in re.finditer(r"UID=(\d+).*?rb=(\d+).*?tb=(\d+)", ns_raw, re.DOTALL):
            uid  = m.group(1)
            rx_b = int(m.group(2))
            tx_b = int(m.group(3))
            pkg  = uid_map.get(uid, f"uid:{uid}")
            if not any(s.uid == uid for s in stats):
                stats.append(AppTrafficStats(pkg=pkg, uid=uid,
                                             rx_bytes=rx_b, tx_bytes=tx_b,
                                             rx_packets=0, tx_packets=0))

    # Sortiere nach Gesamtverkehr
    stats.sort(key=lambda s: s.rx_bytes + s.tx_bytes, reverse=True)
    return stats


# ---------------------------------------------------------------------------
# Network-Security-Config
# ---------------------------------------------------------------------------

def extract_network_security_configs(
    adb: ADB, pkgs: list[str], st: dict
) -> list[NetworkSecurityConfig]:
    """Liest network_security_config.xml aus APK und analysiert Cleartext/Pinning."""
    configs: list[NetworkSecurityConfig] = []

    for pkg in pkgs:
        # APK-Pfad ermitteln
        pm_out = adb.shell(f"pm path {shq(pkg)}", timeout=10)
        m      = re.search(r"package:(\S+\.apk)", pm_out)
        if not m:
            continue
        apk_path = m.group(1)

        # network_security_config.xml extrahieren (als strings, da binär)
        raw = adb.shell(
            f"unzip -p {shq(apk_path)} 'res/xml/network_security_config.xml' 2>/dev/null | strings",
            timeout=15,
        )
        if not raw.strip():
            # Manche APKs nutzen anderes Verzeichnis
            raw = adb.shell(
                f"unzip -l {shq(apk_path)} 2>/dev/null | grep -i network_security",
                timeout=10,
            )
            if not raw.strip():
                continue

        allows_cleartext = "cleartextTrafficPermitted" in raw and "true" in raw.lower()
        custom_cas       = "trust-anchors" in raw and "user" in raw
        pinned_domains: list[str] = re.findall(
            r'<domain[^>]*>([a-zA-Z0-9._-]+\.[a-z]{2,})</domain>', raw
        )

        configs.append(NetworkSecurityConfig(
            pkg=pkg,
            allows_cleartext=allows_cleartext,
            pinned_domains=pinned_domains,
            custom_cas=custom_cas,
            raw=raw[:2000],
        ))

    return configs


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

def analyze_connections(conns: list[NetworkConnection]) -> list[dict]:
    """Findet Anomalien in Verbindungsliste."""
    anomalies: list[dict] = []
    remote_ip_to_pkgs: dict[str, list[str]] = {}

    for c in conns:
        remote_ip = c.remote_addr.rsplit(":", 1)[0] if ":" in c.remote_addr else c.remote_addr
        remote_port_str = c.remote_addr.rsplit(":", 1)[-1] if ":" in c.remote_addr else "0"

        # Bekannte Bad-IPs
        if remote_ip in KNOWN_BAD_IPS:
            anomalies.append({
                "severity": "CRITICAL",
                "type":     "KNOWN_BAD_IP",
                "pkg":      c.pkg,
                "detail":   f"Verbindung zu bekannter C2/Malware-IP {remote_ip} (Port {remote_port_str})",
            })

        # Apps lauschen auf 0.0.0.0 (extern erreichbar)
        local_ip = c.local_addr.rsplit(":", 1)[0] if ":" in c.local_addr else c.local_addr
        if c.state == "LISTEN" and local_ip in ("0.0.0.0", "::"):
            local_port = c.local_addr.rsplit(":", 1)[-1] if ":" in c.local_addr else "?"
            anomalies.append({
                "severity": "HIGH",
                "type":     "EXTERNAL_LISTEN",
                "pkg":      c.pkg,
                "detail":   f"Lauscht auf externem Interface 0.0.0.0:{local_port} – von außen erreichbar",
            })

        # Ungewöhnliche Ports bei aktiven Verbindungen
        try:
            remote_port = int(remote_port_str)
            if (c.state == "ESTABLISHED" and remote_port > 0
                    and remote_port not in _NORMAL_PORTS
                    and not remote_ip.startswith(("10.", "192.168.", "172.16.", "127."))):
                anomalies.append({
                    "severity": "MEDIUM",
                    "type":     "UNUSUAL_PORT",
                    "pkg":      c.pkg,
                    "detail":   f"Verbindung zu {remote_ip}:{remote_port} (kein Standard-Port)",
                })
        except ValueError:
            pass

        # Mehrere Apps → gleiche externe IP aufzeichnen
        if remote_ip and not remote_ip.startswith(("0.", "10.", "192.", "172.", "127.", "::")):
            remote_ip_to_pkgs.setdefault(remote_ip, []).append(c.pkg)

    # Mehrere Apps an gleicher IP
    for ip, pkgs in remote_ip_to_pkgs.items():
        unique = list(set(pkgs))
        if len(unique) >= 3:
            anomalies.append({
                "severity": "MEDIUM",
                "type":     "SHARED_C2_IP",
                "pkg":      ", ".join(unique[:4]),
                "detail":   f"{len(unique)} Apps verbunden zu {ip} – möglicher gemeinsamer C2-Server",
            })

    return anomalies


def analyze_traffic_anomalies(stats: list[AppTrafficStats]) -> list[dict]:
    """Findet Daten-Exfiltrations-Muster in Traffic-Statistiken."""
    anomalies: list[dict] = []

    for s in stats:
        # Sehr hoher Upload > 10 MB
        if s.tx_bytes > 10_485_760:
            anomalies.append({
                "severity": "HIGH",
                "type":     "HIGH_UPLOAD",
                "pkg":      s.pkg,
                "detail":   f"Upload: {s.tx_mb():.1f} MB – mögliche Daten-Exfiltration",
            })

        # Upload stark > Download (>5:1)
        elif s.ratio > 5.0 and s.tx_bytes > 1_048_576:
            anomalies.append({
                "severity": "MEDIUM",
                "type":     "UPLOAD_RATIO",
                "pkg":      s.pkg,
                "detail":   f"TX/RX-Verhältnis {s.ratio:.1f}:1 ({s.tx_mb():.1f} MB up / {s.rx_mb():.1f} MB down)",
            })

    return anomalies


def analyze_netsec_configs(configs: list[NetworkSecurityConfig]) -> list[dict]:
    """Findet unsichere Netzwerkkonfigurationen."""
    anomalies: list[dict] = []
    for c in configs:
        if c.allows_cleartext:
            anomalies.append({
                "severity": "HIGH",
                "type":     "CLEARTEXT_ALLOWED",
                "pkg":      c.pkg,
                "detail":   "cleartextTrafficPermitted=true – HTTP-Traffic unverschlüsselt möglich",
            })
        if c.custom_cas:
            anomalies.append({
                "severity": "MEDIUM",
                "type":     "USER_CA_TRUSTED",
                "pkg":      c.pkg,
                "detail":   "Vertraut Nutzer-CAs – MITM via eigenem Zertifikat möglich",
            })
    return anomalies


# ---------------------------------------------------------------------------
# Formatierung
# ---------------------------------------------------------------------------

def format_traffic_table(stats: list[AppTrafficStats]) -> str:
    """ASCII-Tabelle der Traffic-Statistiken."""
    if not stats:
        return "  [Keine Traffic-Daten verfügbar]"

    SEP = "─" * 80
    lines = [
        SEP,
        f"  {'PAKET':<45}  {'RX':>8}  {'TX':>8}  {'TX/RX':>6}  {'PAKETE-TX':>10}",
        SEP,
    ]
    for s in stats[:40]:
        ratio_str = f"{s.ratio:.1f}x" if s.ratio < 999 else ">999x"
        lines.append(
            f"  {s.pkg[:44]:<45}  "
            f"{s.rx_mb():>6.1f}MB  {s.tx_mb():>6.1f}MB  "
            f"{ratio_str:>6}  {s.tx_packets:>10,}"
        )
    if len(stats) > 40:
        lines.append(f"  … ({len(stats) - 40} weitere)")
    lines.append(SEP)
    return "\n".join(lines)


def format_connections_table(conns: list[NetworkConnection], max_rows: int = 50) -> str:
    """ASCII-Tabelle aktiver Verbindungen."""
    if not conns:
        return "  [Keine Verbindungen gefunden]"

    SEP = "─" * 90
    lines = [
        SEP,
        f"  {'PROTO':<6} {'STATUS':<13} {'LOCAL':<22} {'REMOTE':<22} PAKET",
        SEP,
    ]
    shown = 0
    for c in conns:
        if shown >= max_rows:
            lines.append(f"  … ({len(conns) - shown} weitere)")
            break
        lines.append(
            f"  {c.proto:<6} {c.state:<13} {c.local_addr:<22} "
            f"{c.remote_addr:<22} {c.pkg[:28]}"
        )
        shown += 1
    lines.append(SEP)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Master-Funktion
# ---------------------------------------------------------------------------

def run_network_forensics(adb: ADB, dev, st: dict) -> dict:
    """Führt alle Network-Forensik-Module aus und liefert konsolidiertes Ergebnis."""

    conns:   list[NetworkConnection] = []
    dns:     list[DnsEntry]          = []
    traffic: list[AppTrafficStats]   = []
    err_msgs: list[dict]             = []

    # 1. Verbindungen
    try:
        conns = extract_active_connections(adb, st)
    except Exception as e:
        err_msgs.append({"severity": "INFO", "type": "EXTRACT_ERROR",
                         "pkg": "", "detail": f"Verbindungen: {e}"})

    # 2. DNS
    try:
        dns = extract_dns_cache(adb, st)
    except Exception:
        pass

    # 3. Traffic
    try:
        traffic = extract_traffic_stats(adb, st)
    except Exception:
        pass

    # 4. Analyse
    conn_anomalies    = analyze_connections(conns)
    traffic_anomalies = analyze_traffic_anomalies(traffic)
    all_anomalies     = err_msgs + conn_anomalies + traffic_anomalies
    all_anomalies.sort(
        key=lambda a: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}.get(a["severity"], 4)
    )

    # 5. Zusammenfassung
    est   = sum(1 for c in conns if c.state in ("ESTABLISHED", "ESTAB"))
    lst   = sum(1 for c in conns if c.state in ("LISTEN", "LISTEN"))
    total_tx = sum(s.tx_bytes for s in traffic) / 1_048_576
    total_rx = sum(s.rx_bytes for s in traffic) / 1_048_576

    trackers_found = set()
    for entry in dns:
        for t in KNOWN_TRACKERS:
            if t in entry.hostname:
                trackers_found.add(t)

    lines = [
        "═" * 70,
        "  NETZWERK-FORENSIK ZUSAMMENFASSUNG",
        "═" * 70,
        f"  Aktive Verbindungen : {len(conns)} ({est} ESTABLISHED, {lst} LISTEN)",
        f"  DNS-Einträge        : {len(dns)}",
        f"  Traffic gesamt      : ↓{total_rx:.1f} MB  ↑{total_tx:.1f} MB",
        f"  Tracker-Domains     : {len(trackers_found)}  {', '.join(sorted(trackers_found)[:5])}",
        f"  Anomalien           : {len(all_anomalies)} ({sum(1 for a in all_anomalies if a['severity'] in ('CRITICAL','HIGH'))} HIGH+)",
    ]
    if all_anomalies:
        lines.append("")
        lines.append("  KRITISCHE BEFUNDE:")
        for a in all_anomalies[:8]:
            lines.append(f"  [{a['severity']:8}] {a['type']:<22} {a.get('pkg','')[:25]}")
            lines.append(f"               {a['detail'][:60]}")
    summary = "\n".join(lines)

    return {
        "connections":    [c.to_dict() for c in conns],
        "dns":            [d.to_dict() for d in dns],
        "traffic":        [t.to_dict() for t in traffic],
        "anomalies":      all_anomalies,
        "summary":        summary,
    }
