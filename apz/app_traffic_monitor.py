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
#  HAUPTMENÜ
# ═══════════════════════════════════════════════════════════════════════════════

def menu(adb: ADB, dev=None, st=None, data=None) -> None:
    """App-Domain Monitor – Hauptmenü."""
    while True:
        ui.clear()
        ui.banner(subtitle="🌐 APP-DOMAIN MONITOR – Echtzeit · Statistik · Blacklist · DNS")
        print(f"  {ui.GREY}Zeigt welche Apps welche Domains aufrufen · Tracker-Erkennung · DNS-Analyse{ui.RESET}\n")
        ch = ui.menu("Aktion", [
            ("1", f"{ui.BRED}{ui.BOLD}🔴 LIVE DNS/Domain Monitor{ui.RESET}  "
                  f"(Echtzeit · Apps · Domains · Frequenz · Herzschlag-Alarm)"),
            ("2", "📊 App-Netzwerk-Statistik  (Traffic pro App · UID · Bytes/Pakete · sortierbar)"),
            ("3", "🚫 Blacklist-Check         (200+ Tracker · Malware-Domains · Sofort-Alarm)"),
            ("4", "🗂️  DNS-Cache Dump         (Resolver · Server · Props · /proc/net · Root)"),
            ("5", "📁 Alles speichern         (Vollexport: JSON + TXT + netstats + DNS)"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        try:
            dispatch = {
                "1": live_domain_monitor,
                "2": app_network_history,
                "3": domain_blacklist_check,
                "4": dns_cache_dump,
                "5": export_all,
            }
            fn = dispatch.get(ch)
            if fn:
                fn(adb, dev, st, data)
        except Exception as e:  # noqa: BLE001
            ui.err(f"Fehler: {e}")
            LOG.exception("app_traffic_monitor", e)
            ui.pause()
