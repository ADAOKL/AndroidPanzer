"""OSINT-Toolkit (modern, mit KI-Analyst) – legitime Open-Source-Intelligence.

Module:
  📞 Telefonnummer   → Land/Carrier/Typ + OSINT-Links (phoneosint.py)
  📧 E-Mail          → Validierung, Gravatar (live), Breach-Check, Social-Permutationen
  👤 Username        → Live-Enumeration über ~35 Plattformen (Sherlock-Stil)
  🌐 Domain/IP       → DNS-Records, WHOIS, Reverse-DNS, Subdomain-Hinweise
  🧑 Person/Name     → KI-generierte Google-Dorks & Social-Suche
  🖼  Bild            → Reverse-Image-Search-Links
  🤖 KI-ANALYST      → führt gesammelte Funde zusammen, schlägt Pivots/nächste Schritte vor

Alles nutzt NUR öffentlich zugängliche Quellen. Kein Hacking, kein Zugriff auf private
Daten. Für legitime Zwecke: eigene Spuren prüfen, Betrugsabwehr, autorisierte Recherche.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

from . import ui

OUT = os.path.expanduser("~/Schreibtisch/Androidpanzer/osint")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
# Sammelt Funde der aktuellen Sitzung für den KI-Analysten
_FINDINGS: list[str] = []


def _o() -> str:
    os.makedirs(OUT, exist_ok=True)
    return OUT


def _note(s: str) -> None:
    _FINDINGS.append(s)


def menu(adb=None, dev=None, st=None) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🕵️  OSINT-Toolkit (mit KI-Analyst)")
        ui.kv("Gesammelte Funde (Sitzung)", len(_FINDINGS))
        ch = ui.menu("Module", [
            ("1", "📞 Telefonnummer analysieren"),
            ("2", "📧 E-Mail-Adresse (Gravatar/Breach/Social)"),
            ("3", "👤 Username über ~35 Plattformen suchen (live)"),
            ("4", "🌐 Domain / IP (DNS/WHOIS/Reverse)"),
            ("5", "📍 IP-Adresse analysieren (Geo/ASN/Reputation)"),
            ("6", "🧑 Person/Name (KI-Dorks & Social)"),
            ("7", "🖼  Bild – Reverse-Image-Search"),
            ("8", f"{ui.BCYAN}{ui.BOLD}🤖 KI-ANALYST – Funde zusammenführen & Pivots{ui.RESET}"),
            ("9", "🗑 Funde dieser Sitzung löschen"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            from . import phoneosint
            phoneosint.menu()
        elif ch == "2":
            email_osint()
        elif ch == "3":
            username_osint()
        elif ch == "4":
            domain_osint()
        elif ch == "5":
            ip_osint()
        elif ch == "6":
            person_osint()
        elif ch == "7":
            image_osint()
        elif ch == "8":
            ai_analyst()
        elif ch == "9":
            _FINDINGS.clear(); ui.ok("Funde gelöscht."); ui.pause()


# ===================================================================== #
#  📍 IP-Adresse analysieren (legitime IP-OSINT)
# ===================================================================== #
def ip_osint() -> None:
    ui.clear(); ui.rule("IP-Adresse analysieren", ui.CYAN)
    ip = ui.ask("IP-Adresse (oder 'meine' für eigene öffentliche IP)")
    if not ip:
        return
    if ip.lower() in ("meine", "my", "self"):
        ip = _http_get("https://api.ipify.org").strip() or ""
        ui.kv("Eigene öffentliche IP", ip)
    if not re.match(r"^[0-9a-fA-F:.]+$", ip):
        ui.err("Keine gültige IP."); ui.pause(); return

    # Geolocation + ASN (ip-api.com, kostenlos)
    raw = _http_get(f"http://ip-api.com/json/{urllib.parse.quote(ip)}"
                    "?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,"
                    "timezone,isp,org,as,asname,reverse,mobile,proxy,hosting,query")
    out = [f"# IP-OSINT {ip}"]
    try:
        d = json.loads(raw)
    except Exception:  # noqa: BLE001
        d = {}
    if d.get("status") == "success":
        ui.rule("Geolocation & Netz", ui.CYAN)
        rows = [
            ("Land", f"{d.get('country','')} ({d.get('countryCode','')})"),
            ("Region/Stadt", f"{d.get('regionName','')} / {d.get('city','')} {d.get('zip','')}"),
            ("Koordinaten", f"{d.get('lat')}, {d.get('lon')}  → maps.google.com/?q={d.get('lat')},{d.get('lon')}"),
            ("Zeitzone", d.get("timezone", "")),
            ("Provider (ISP)", d.get("isp", "")),
            ("Organisation", d.get("org", "")),
            ("ASN", f"{d.get('as','')}  ({d.get('asname','')})"),
            ("Reverse-DNS", d.get("reverse", "") or "—"),
        ]
        for k, v in rows:
            ui.kv(k, v); out.append(f"{k}: {v}")
        # Flags
        ui.rule("Einordnung", ui.CYAN)
        if d.get("hosting"):
            ui.kv("Typ", f"{ui.BYELLOW}Rechenzentrum/Hosting (Server, kein Privatanschluss){ui.RESET}")
        if d.get("proxy"):
            ui.kv("Proxy/VPN/Tor", ui.pulse("ja – verschleierte Herkunft"))
        if d.get("mobile"):
            ui.kv("Mobilfunk", "ja (Mobile-Carrier-IP)")
        out.append(f"hosting={d.get('hosting')} proxy={d.get('proxy')} mobile={d.get('mobile')}")
        _note(f"IP {ip}: {d.get('country')}/{d.get('city')}, {d.get('isp')}, {d.get('as')}, "
              f"proxy={d.get('proxy')}, hosting={d.get('hosting')}")
    else:
        ui.warn("Geo-Lookup fehlgeschlagen: " + d.get("message", "(keine Antwort)"))

    # Reputation / weiterführend
    ui.rule("Reputation & weiterführend", ui.CYAN)
    for label, url in [
        ("AbuseIPDB (Missbrauchs-Score)", f"https://www.abuseipdb.com/check/{ip}"),
        ("Shodan (offene Dienste)", f"https://www.shodan.io/host/{ip}"),
        ("VirusTotal", f"https://www.virustotal.com/gui/ip-address/{ip}"),
        ("GreyNoise (Scanner?)", f"https://viz.greynoise.io/ip/{ip}"),
        ("IPinfo", f"https://ipinfo.io/{ip}"),
        ("Censys", f"https://search.censys.io/hosts/{ip}"),
    ]:
        print(f"  {ui.BCYAN}▸{ui.RESET} {label}: {ui.GREY}{url}{ui.RESET}")
    # Reverse-DNS lokal
    ptr = _run(["dig", "+short", "-x", ip])
    if ptr.strip():
        ui.kv("PTR (lokal)", ptr.strip())
    _save(f"ip_{ip.replace(':','_')}.txt", "\n".join(out))
    ui.warn("Hinweis: IP-Geo zeigt den PROVIDER-Standort, nicht die genaue Adresse einer Person. "
            "VPN/Proxy/Mobilfunk verfälschen die Lokalisierung stark.")
    ui.pause()


# ===================================================================== #
#  📧 E-Mail
# ===================================================================== #
def email_osint() -> None:
    ui.clear(); ui.rule("E-Mail-OSINT", ui.CYAN)
    email = ui.ask("E-Mail-Adresse")
    if not email or "@" not in email:
        return
    user, _, domain = email.partition("@")
    ui.kv("Adresse", email)
    # Format/MX
    valid = bool(re.match(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", email))
    ui.kv("Format gültig", "ja" if valid else "nein")
    mx = _dns(domain, "MX")
    ui.kv("MX-Server (Mail existiert?)", ", ".join(mx[:3]) or "— (keine MX → Domain empfängt keine Mail)")

    # Gravatar (live, öffentlich)
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    ui.kv("Gravatar-Profil-URL", f"https://www.gravatar.com/{h}")
    prof = _http_get(f"https://www.gravatar.com/{h}.json")
    if prof and "entry" in prof:
        ui.ok("Gravatar-Profil gefunden (öffentlich):")
        try:
            e = json.loads(prof)["entry"][0]
            ui.kv("  Anzeigename", e.get("displayName", "—"))
            ui.kv("  Benutzername", e.get("preferredUsername", "—"))
            ui.kv("  Standort", e.get("currentLocation", "—"))
            accs = [a.get("shortname", a.get("url", "")) for a in e.get("accounts", [])]
            if accs:
                ui.kv("  Verknüpfte Konten", ", ".join(accs))
                _note(f"E-Mail {email}: Gravatar-Konten {accs}")
            _note(f"E-Mail {email}: Gravatar-Name '{e.get('displayName','')}', Ort '{e.get('currentLocation','')}'")
        except Exception:  # noqa: BLE001
            pass
    else:
        ui.info("Kein öffentliches Gravatar-Profil.")
    ui.kv("Gravatar-Bild", f"https://www.gravatar.com/avatar/{h}?d=404")

    # Breach-Check-Links + optional API
    ui.rule("Datenleck-Prüfung (Breach)", ui.CYAN)
    ui.kv("HaveIBeenPwned", f"https://haveibeenpwned.com/account/{urllib.parse.quote(email)}")
    ui.kv("DeHashed", f"https://dehashed.com/search?query={urllib.parse.quote(email)}")
    ui.kv("Intelligence X", f"https://intelx.io/?s={urllib.parse.quote(email)}")

    # Social-Permutationen (User-Teil als Username prüfen)
    ui.rule("Social-Recherche", ui.CYAN)
    ui.kv("Google", f"https://www.google.com/search?q={urllib.parse.quote(chr(34)+email+chr(34))}")
    ui.kv("Username-Teil prüfen", f"→ Modul 3 mit '{user}'")
    _note(f"E-Mail untersucht: {email} (MX: {bool(mx)}, Gravatar: {'ja' if prof else 'nein'})")
    if ui.confirm("Username-Teil jetzt über Plattformen suchen?", False):
        username_osint(user)
    ui.pause()


# ===================================================================== #
#  👤 Username – Live-Enumeration
# ===================================================================== #
# (site, URL-Template mit {u}, Erkennung: 'status' = 200=existiert, oder 'text:<marker>')
SITES = {
    "GitHub": ("https://github.com/{u}", "status"),
    "GitLab": ("https://gitlab.com/{u}", "status"),
    "Instagram": ("https://www.instagram.com/{u}/", "status"),
    "Twitter/X": ("https://x.com/{u}", "status"),
    "TikTok": ("https://www.tiktok.com/@{u}", "status"),
    "Reddit": ("https://www.reddit.com/user/{u}", "status"),
    "Telegram": ("https://t.me/{u}", "text:tgme_page_title"),
    "Twitch": ("https://www.twitch.tv/{u}", "status"),
    "YouTube": ("https://www.youtube.com/@{u}", "status"),
    "Pinterest": ("https://www.pinterest.com/{u}/", "status"),
    "Steam": ("https://steamcommunity.com/id/{u}", "text:g_steamID"),
    "Spotify": ("https://open.spotify.com/user/{u}", "status"),
    "SoundCloud": ("https://soundcloud.com/{u}", "status"),
    "Vimeo": ("https://vimeo.com/{u}", "status"),
    "Flickr": ("https://www.flickr.com/people/{u}", "status"),
    "Medium": ("https://medium.com/@{u}", "status"),
    "DevTo": ("https://dev.to/{u}", "status"),
    "Keybase": ("https://keybase.io/{u}", "status"),
    "HackerNews": ("https://news.ycombinator.com/user?id={u}", "text:created"),
    "Patreon": ("https://www.patreon.com/{u}", "status"),
    "Gravatar": ("https://gravatar.com/{u}", "status"),
    "About.me": ("https://about.me/{u}", "status"),
    "Linktree": ("https://linktr.ee/{u}", "status"),
    "Replit": ("https://replit.com/@{u}", "status"),
    "Codepen": ("https://codepen.io/{u}", "status"),
    "Bandcamp": ("https://{u}.bandcamp.com", "status"),
    "Wordpress": ("https://{u}.wordpress.com", "status"),
    "Blogger": ("https://{u}.blogspot.com", "status"),
    "Tumblr": ("https://{u}.tumblr.com", "status"),
    "Mastodon (.social)": ("https://mastodon.social/@{u}", "status"),
    "Last.fm": ("https://www.last.fm/user/{u}", "status"),
    "Chess.com": ("https://www.chess.com/member/{u}", "status"),
    "ProductHunt": ("https://www.producthunt.com/@{u}", "status"),
    "Buymeacoffee": ("https://www.buymeacoffee.com/{u}", "status"),
    "Kick": ("https://kick.com/{u}", "status"),
}


def _check_site(name: str, tmpl: str, mode: str, u: str) -> tuple[str, bool, str]:
    url = tmpl.format(u=urllib.parse.quote(u))
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        with urllib.request.urlopen(req, timeout=12) as r:
            code = r.status
            body = r.read(20000).decode("utf-8", "replace") if mode.startswith("text:") else ""
        if mode == "status":
            return name, code == 200, url
        marker = mode.split("text:", 1)[-1]   # [-1] statt [1]: kein IndexError bei unerwartetem mode
        return name, marker in body, url
    except urllib.error.HTTPError:  # noqa: BLE001
        return name, False, url
    except Exception:  # noqa: BLE001
        return name, False, url


def username_osint(prefill: str = "") -> None:
    ui.clear(); ui.rule("Username-Enumeration (live)", ui.CYAN)
    u = prefill or ui.ask("Username")
    if not u:
        return
    ui.info(f"Prüfe '{u}' auf {len(SITES)} Plattformen … (parallel, ~15s)\n")
    hits, misses = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(_check_site, n, t, m, u) for n, (t, m) in SITES.items()]
        for f in concurrent.futures.as_completed(futs):
            name, found, url = f.result()
            if found:
                hits.append((name, url))
                print(f"   {ui.BGREEN}✓ {name:<18}{ui.RESET} {url}")
            else:
                misses.append(name)
    print()
    ui.ok(f"{len(hits)} Treffer / {len(misses)} ohne Profil")
    if hits:
        _note(f"Username '{u}': gefunden auf " + ", ".join(n for n, _ in hits))
        _save(f"username_{u}.txt", f"Username: {u}\n\nGefunden:\n" +
              "\n".join(f"{n}: {url}" for n, url in hits) +
              "\n\nNicht gefunden:\n" + ", ".join(misses))
    ui.warn("Hinweis: Treffer = öffentliches Profil existiert. Gleicher Name ≠ gleiche Person.")
    ui.pause()


# ===================================================================== #
#  🌐 Domain / IP
# ===================================================================== #
def domain_osint() -> None:
    ui.clear(); ui.rule("Domain / IP-OSINT", ui.CYAN)
    target = ui.ask("Domain (example.com) oder IP")
    if not target:
        return
    is_ip = bool(re.match(r"^\d+\.\d+\.\d+\.\d+$", target))
    out = [f"# OSINT {target}"]
    if not is_ip:
        ui.rule("DNS-Records", ui.CYAN)
        for rt in ("A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"):
            recs = _dns(target, rt)
            if recs:
                ui.kv(rt, "; ".join(recs[:4])[:90])
                out.append(f"{rt}: {'; '.join(recs)}")
        # SPF/DMARC aus TXT
        txt = _dns(target, "TXT")
        for t in txt:
            if "spf" in t.lower():
                ui.kv("SPF", t[:80])
            if "dmarc" in t.lower():
                ui.kv("DMARC", t[:80])
    # WHOIS
    ui.rule("WHOIS", ui.CYAN)
    who = _whois(target)
    if who:
        for key in ("Registrar", "Creation Date", "Registry Expiry", "Updated Date",
                    "Organization", "Country", "Name Server", "netname", "descr", "origin"):
            m = re.search(rf"{key}:\s*(.+)", who, re.I)
            if m:
                ui.kv(key, m.group(1).strip()[:70])
                out.append(f"{key}: {m.group(1).strip()}")
    # Reverse-DNS bei IP
    if is_ip:
        ui.rule("Reverse-DNS", ui.CYAN)
        ptr = _run(["dig", "+short", "-x", target])
        ui.kv("PTR", ptr.strip() or "—")
        out.append(f"PTR: {ptr.strip()}")
    # Recherche-Links
    ui.rule("Weiterführend", ui.CYAN)
    for label, url in [
        ("crt.sh (Subdomains via Zertifikate)", f"https://crt.sh/?q={urllib.parse.quote(target)}"),
        ("Shodan", f"https://www.shodan.io/search?query={urllib.parse.quote(target)}"),
        ("VirusTotal", f"https://www.virustotal.com/gui/domain/{urllib.parse.quote(target)}"),
        ("Wayback Machine", f"https://web.archive.org/web/*/{urllib.parse.quote(target)}"),
        ("DNSDumpster", "https://dnsdumpster.com/"),
    ]:
        print(f"  {ui.BCYAN}▸{ui.RESET} {label}: {ui.GREY}{url}{ui.RESET}")
    _note(f"Domain/IP {target}: " + "; ".join(out[1:6]))
    _save(f"domain_{target}.txt", "\n".join(out))
    ui.pause()


# ===================================================================== #
#  🧑 Person/Name – KI-Dorks
# ===================================================================== #
def person_osint() -> None:
    ui.clear(); ui.rule("Person/Name-Recherche", ui.CYAN)
    name = ui.ask("Name (z.B. Max Mustermann)")
    if not name:
        return
    extra = ui.ask("Zusatz-Hinweis (Stadt/Beruf/Firma, optional)")
    q = urllib.parse.quote
    full = f'"{name}"' + (f' {extra}' if extra else "")
    ui.rule("Standard-Dorks", ui.CYAN)
    dorks = [
        ("Allgemein", full),
        ("LinkedIn", f'{full} site:linkedin.com'),
        ("Facebook", f'{full} site:facebook.com'),
        ("Xing", f'{full} site:xing.com'),
        ("Dokumente", f'{full} (filetype:pdf OR filetype:docx)'),
        ("Lebenslauf", f'{full} (CV OR Lebenslauf OR resume)'),
        ("Kontakt", f'{full} (email OR "@" OR telefon OR phone)'),
    ]
    for label, d in dorks:
        print(f"  {ui.BCYAN}▸{ui.RESET} {label}: {ui.GREY}https://www.google.com/search?q={q(d)}{ui.RESET}")
    # KI-generierte zusätzliche Dorks
    if ui.confirm("\nKI zusätzliche, kreative Dorks generieren lassen?", True):
        _ai_dorks(name, extra)
    _note(f"Person recherchiert: {name} ({extra})")
    ui.pause()


def _ai_dorks(name: str, extra: str) -> None:
    try:
        from . import aishell
        if not aishell._ollama_up():
            ui.warn("ollama aus."); return
        m = aishell._pick_model()
        ans = aishell._gen(m,
            f"Ziel-Person: {name}. Zusatz: {extra or '-'}.\n"
            "Erzeuge 8 fortgeschrittene Google-Dork-Suchanfragen (OSINT) um öffentliche "
            "Spuren zu finden. Nur die Dorks, je eine Zeile, kein Markdown.",
            "Du bist ein OSINT-Experte. Nur legale, öffentliche Quellen.", timeout=120)
        ui.rule("KI-Dorks", ui.BCYAN)
        for line in ans.splitlines():
            line = line.strip().lstrip("0123456789.-) ").strip()
            if len(line) > 5:
                print(f"  {ui.BCYAN}▸{ui.RESET} https://www.google.com/search?q={urllib.parse.quote(line)}")
    except Exception as e:  # noqa: BLE001
        ui.err(str(e))


# ===================================================================== #
#  🖼  Bild
# ===================================================================== #
def image_osint() -> None:
    ui.clear(); ui.rule("Reverse-Image-Search", ui.CYAN)
    ui.info("Bild-URL angeben (öffentlich erreichbar) oder Datei am PC hochladen-Hinweis.")
    url = ui.ask("Bild-URL (oder leer für Anleitung)")
    q = urllib.parse.quote
    if url:
        for label, link in [
            ("Google Lens", f"https://lens.google.com/uploadbyurl?url={q(url)}"),
            ("Yandex (stark bei Gesichtern)", f"https://yandex.com/images/search?rpt=imageview&url={q(url)}"),
            ("Bing Visual", f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{q(url)}"),
            ("TinEye", f"https://tineye.com/search?url={q(url)}"),
        ]:
            print(f"  {ui.BCYAN}▸{ui.RESET} {label}: {ui.GREY}{link}{ui.RESET}")
        _note(f"Bild reverse-gesucht: {url}")
    else:
        ui.info("Ohne URL: Bild bei images.google.com / yandex.com/images per Upload suchen.")
        ui.info("Für EXIF-GPS aus eigenen Fotos: Forensik → Timeline → Geo-Mapping.")
    ui.pause()


# ===================================================================== #
#  🤖 KI-ANALYST
# ===================================================================== #
def ai_analyst() -> None:
    ui.clear(); ui.rule("🤖 KI-OSINT-Analyst", ui.BCYAN)
    if not _FINDINGS:
        ui.warn("Noch keine Funde gesammelt – erst Module 1-6 nutzen."); ui.pause(); return
    try:
        from . import aishell
        if not aishell._ollama_up():
            ui.err("ollama nicht erreichbar."); ui.pause(); return
        m = aishell._pick_model()
        ui.info(f"Analysiere {len(_FINDINGS)} Funde …\n")
        data = "\n".join(f"- {f}" for f in _FINDINGS)
        ans = aishell._gen(m,
            f"Gesammelte OSINT-Funde:\n{data}\n\n"
            "Als OSINT-Analyst: 1) Fasse das Ziel-Profil zusammen, 2) nenne Verknüpfungen/Muster, "
            "3) schlage die nächsten Recherche-Schritte (Pivots) vor, 4) bewerte die Konfidenz. "
            "Auf Deutsch, strukturiert.",
            "Du bist ein professioneller OSINT-Analyst. Nur legale, öffentliche Quellen.", timeout=240)
        ui.pager(ans, "KI-OSINT-Analyse")
        _save("ki_analyse.txt", "FUNDE:\n" + data + "\n\nKI-ANALYSE:\n" + ans)
    except Exception as e:  # noqa: BLE001
        ui.err(str(e))
    ui.pause()


# ===================================================================== #
#  Helfer
# ===================================================================== #
def _dns(domain: str, rtype: str) -> list[str]:
    try:
        import dns.resolver
        ans = dns.resolver.resolve(domain, rtype, lifetime=8)
        return [r.to_text().strip('"') for r in ans]
    except Exception:  # noqa: BLE001
        out = _run(["dig", "+short", rtype, domain])
        return [l for l in out.splitlines() if l.strip()]


def _whois(target: str) -> str:
    return _run(["whois", target], timeout=25)


def _run(args: list[str], timeout: int = 15) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.stdout + p.stderr
    except Exception:  # noqa: BLE001
        return ""


def _http_get(url: str, timeout: int = 12) -> str:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(50000).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def _save(name: str, content: str) -> None:
    _o()
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    ui.show_report(content, f"OSINT · {name}", p, note="OSINT-Bericht")
