"""Handynummer-Analyse (OSINT) – nach dem Vorbild von PhoneInfoga.

Was eine Nummer ZUVERLÄSSIG verrät (offline, via Google libphonenumber):
  • Gültigkeit & Format (E.164 / national / international / RFC3966)
  • Land, Region, Vorwahl-Gebiet, Zeitzone(n)
  • Netzbetreiber (Carrier) & Leitungstyp (Mobil / Festnetz / VoIP)

Was nur per OSINT-Recherche möglich ist (das Tool liefert die Ansatzpunkte):
  • Präsenz auf Messengern (WhatsApp/Telegram/Signal – Klick-Links)
  • Öffentliche Spuren (Suchmaschinen-Dorks, Social-Media, Reverse-Lookup-Seiten)
  • Spam/Scam-Reputation (Community-Datenbanken)

EHRLICH: Name/Adresse/„registrierte Konten" sind aus der Nummer NICHT abrufbar –
nur auffindbar, wenn die Person sie selbst öffentlich gepostet hat. Nutze das nur
für legitime Zwecke (eigene Nummer, autorisierte Recherche, Betrugsabwehr).
"""
from __future__ import annotations

import urllib.parse

from . import ui

try:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone
    _HAVE = True
except Exception:  # noqa: BLE001
    _HAVE = False


def menu(adb=None, dev=None, st=None) -> None:
    if not _HAVE:
        ui.clear(); ui.rule("Handynummer-Analyse", ui.CYAN)
        ui.err("Bibliothek fehlt:  pip install phonenumbers")
        ui.pause(); return
    while True:
        ui.clear()
        ui.banner(subtitle="📞 Telefon-OSINT & Nummer-Analyse")
        ch = ui.menu("Aktion", [
            ("1",  "🔍 Nummer analysieren      (Format, Land, Carrier, Messenger, OSINT-Links)"),
            ("2",  "📦 Mehrere Nummern         (Batch-Analyse, Liste einlesen)"),
            ("3",  "📶 Carrier-Vollsuche        (Netz-Identifikation, Portierung, VoIP-Check)"),
            ("4",  "⚠  Spam-Score              (Tellows, CleverDialer, WerruftAn)"),
            ("5",  "🌐 Social-Media Suche       (Facebook, Instagram, Telegram, TikTok)"),
            ("6",  "✉  E-Mail-Permutationen     (Mögliche Adressen aus Name/Nummer generieren)"),
            ("7",  "🔓 Breach-Check Anleitung   (HaveIBeenPwned, LeakCheck, Dehashed)"),
            ("8",  "🕵 CallerID-Datenbanken     (Truecaller, Sync.me, Reverse-Lookup)"),
            ("9",  "📍 Carrier-Standort         (MCC/MNC → Netz, Land, Region)"),
            ("10", "🤖 KI-Rechercheplan          (Ollama – strukturierter OSINT-Plan)"),
            ("11", "💾 Report exportieren        (TXT-Datei aller gesammelten Daten)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            num = ui.ask("Telefonnummer (+49170…) oder 'q'")
            if num and num.lower() not in ("q", "quit", ""):
                analyze(num)
        elif ch == "2":
            _batch_analyze()
        elif ch == "3":
            num = ui.ask("Telefonnummer (+49170…)")
            if num and num.strip():
                _carrier_deep(num.strip())
        elif ch == "4":
            num = ui.ask("Telefonnummer (+49170…)")
            if num and num.strip():
                _spam_check(num.strip())
        elif ch == "5":
            num = ui.ask("Telefonnummer (+49170…)")
            if num and num.strip():
                _social_deep(num.strip())
        elif ch == "6":
            _email_permutations()
        elif ch == "7":
            _breach_guide()
        elif ch == "8":
            num = ui.ask("Telefonnummer (+49170…)")
            if num and num.strip():
                _callerid_lookup(num.strip())
        elif ch == "9":
            _carrier_location(adb)
        elif ch == "10":
            num = ui.ask("Telefonnummer (+49170…)")
            if num and num.strip():
                _run_ai_plan(num.strip())
        elif ch == "11":
            num = ui.ask("Telefonnummer für Export (+49170…)")
            if num and num.strip():
                _full_export(num.strip())


def _batch_analyze() -> None:
    """Mehrere Nummern auf einmal analysieren."""
    ui.clear()
    ui.rule("📦 BATCH-ANALYSE", ui.BCYAN)
    print(f"\n  {ui.GREY}Nummern kommasepariert oder eine pro Zeile (leer = Ende):{ui.RESET}\n")
    nums = []
    raw = ui.ask("Nummern (kommasepariert) oder Pfad zur .txt-Datei")
    if not raw:
        return
    import os
    if os.path.isfile(raw.strip()):
        with open(raw.strip(), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        nums = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
    else:
        nums = [n.strip() for n in raw.replace("\n", ",").split(",") if n.strip()]
    if not nums:
        ui.err("Keine Nummern erkannt."); ui.pause(); return
    ui.info(f"{len(nums)} Nummern gefunden. Analyse startet…\n")
    results = []
    for num in nums[:50]:
        try:
            n = phonenumbers.parse(num, "DE" if not num.startswith("+") else None)
            valid = phonenumbers.is_valid_number(n)
            e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
            country = _country_name(n)
            car = carrier.name_for_number(n, "de") or "?"
            ltype = _line_type(n)
            line = f"{e164:20s} | {'✓' if valid else '✗'} | {country:20s} | {car:15s} | {ltype}"
            print(f"  {line}")
            results.append(line)
        except Exception as e:
            line = f"{num:20s} | ERROR: {e}"
            print(f"  {ui.BRED}{line}{ui.RESET}")
            results.append(line)
    if results and ui.confirm("Ergebnisse speichern?", True):
        import time as _time
        out = os.path.expanduser(f"~/Schreibtisch/Androidpanzer/phone_osint/batch_{_time.strftime('%Y%m%d_%H%M%S')}.txt")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write("Nummer               | Gültig | Land                 | Carrier         | Typ\n")
            f.write("-" * 80 + "\n")
            f.write("\n".join(results) + "\n")
        ui.ok(f"Gespeichert: {out}")
    ui.pause()


def _carrier_deep(raw: str) -> None:
    """Carrier-Vollsuche – Netzidentifikation, VoIP-Check, Portierungs-Hinweis."""
    ui.clear()
    ui.rule("📶 CARRIER-VOLLSUCHE", ui.BCYAN)
    try:
        n = phonenumbers.parse(raw, "DE" if not raw.startswith("+") else None)
    except Exception as e:
        ui.err(f"Parse-Fehler: {e}"); ui.pause(); return
    e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
    intl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    print(f"\n  Nummer: {ui.BOLD}{intl}{ui.RESET}\n")
    # Carrier-Infos
    car_de = carrier.name_for_number(n, "de")
    car_en = carrier.name_for_number(n, "en")
    tzs = timezone.time_zones_for_number(n)
    ltype = _line_type(n)
    region = geocoder.description_for_number(n, "de")
    ui.kv("Carrier (DE)", car_de or "— (bei portierten Nummern oft leer)")
    ui.kv("Carrier (EN)", car_en or "—")
    ui.kv("Leitungstyp", ltype)
    ui.kv("Region",      region or "—")
    ui.kv("Zeitzonen",   ", ".join(tzs) or "—")
    print()
    # VoIP-Einschätzung
    t = phonenumbers.number_type(n)
    if t == phonenumbers.PhoneNumberType.VOIP:
        ui.warn("VoIP-Nummer erkannt (Dienst wie Skype/Google Voice/Twilio)")
    elif t == phonenumbers.PhoneNumberType.MOBILE:
        ui.ok("Mobilfunk-Nummer")
    elif t == phonenumbers.PhoneNumberType.FIXED_LINE:
        ui.info("Festnetz-Nummer")
    elif t == phonenumbers.PhoneNumberType.PREMIUM_RATE:
        ui.warn("Premium-Nummer (kostenpflichtig!)")
    # Portierung
    print(f"\n  {ui.BOLD}Portierungs-Prüfung:{ui.RESET}")
    print(f"  {ui.GREY}Carrier-Datenbanken zeigen den ORIGINAL-Carrier – bei portierten Nummern")
    print(f"  weicht der angezeigte Carrier vom echten Anbieter ab.")
    print(f"  Prüfung über: https://www.bundesnetzagentur.de/portierungsabfrage{ui.RESET}")
    # Rufnummernplan-Check
    rc = phonenumbers.region_code_for_number(n)
    print(f"\n  {ui.BOLD}Rufnummernplan:{ui.RESET}")
    print(f"  {ui.GREY}Region-Code: {rc}")
    print(f"  E.164: {e164}")
    print(f"  Gültig: {'✓' if phonenumbers.is_valid_number(n) else '✗'}{ui.RESET}")
    ui.pause()


def _spam_check(raw: str) -> None:
    """Spam-Score – alle Community-Datenbanken."""
    ui.clear()
    ui.rule("⚠  SPAM / SCAM SCORE", ui.BYELLOW)
    try:
        n = phonenumbers.parse(raw, "DE" if not raw.startswith("+") else None)
        natl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.NATIONAL)
        e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
        intl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    except Exception:
        natl = raw; e164 = raw; intl = raw
    natl_clean = natl.replace(" ", "").replace("/", "").replace("-", "")
    digits = e164.lstrip("+")
    print(f"\n  Nummer: {ui.BOLD}{intl}{ui.RESET}\n")
    sources = [
        ("tellows (DE, Score 1-9)", f"https://www.tellows.de/num/{urllib.parse.quote(natl_clean)}"),
        ("clever-dialer",           f"https://www.cleverdialer.de/telefonnummer/{urllib.parse.quote(natl_clean)}"),
        ("WerruftAn",               f"https://www.werruftan.com/Phonenumber-{urllib.parse.quote(natl_clean)}"),
        ("Should I Answer",         f"https://www.shouldianswer.com/phone-number/{urllib.parse.quote(natl_clean)}"),
        ("Truecaller",              f"https://www.truecaller.com/search/de/{urllib.parse.quote(natl_clean)}"),
        ("Mr. Number (US)",         f"https://mrnumber.com/{urllib.parse.quote(digits)}"),
        ("800Notes",                f"https://800notes.com/Phone.aspx/{urllib.parse.quote(natl_clean)}"),
        ("NumLookup",               f"https://numlookup.com/search?phone={urllib.parse.quote(e164)}"),
        ("Reverse Phone Check",     f"https://www.reversephonecheck.com/{urllib.parse.quote(digits)}"),
        ("Sync.me",                 f"https://sync.me/search/?number={urllib.parse.quote(digits)}"),
    ]
    for label, url in sources:
        print(f"  {ui.BCYAN}▸{ui.RESET} {label:30s} {ui.GREY}{url}{ui.RESET}")
    ui.pause()


def _social_deep(raw: str) -> None:
    """Social-Media Tiefensuche – plattformspezifische Dorks."""
    ui.clear()
    ui.rule("🌐 SOCIAL-MEDIA TIEFENSUCHE", ui.BCYAN)
    try:
        n = phonenumbers.parse(raw, "DE" if not raw.startswith("+") else None)
        e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
        natl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.NATIONAL)
        intl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    except Exception:
        e164 = raw; natl = raw; intl = raw
    natl_clean = natl.replace(" ", "").replace("/", "").replace("-", "")
    digits = e164.lstrip("+")
    q = urllib.parse.quote
    forms = f'"{e164}" OR "{natl}" OR "{natl_clean}"'
    g = "https://www.google.com/search?q="
    print(f"\n  Nummer: {ui.BOLD}{intl}{ui.RESET}\n")
    sections = {
        "Direkt-Links (Messenger)": [
            ("WhatsApp",       f"https://wa.me/{digits}"),
            ("Telegram",       f"https://t.me/+{digits}"),
            ("Signal",         f"signal: Kontakt hinzufügen → {e164}"),
            ("Viber",          f"viber://chat?number={q(e164)}"),
        ],
        "Google-Dorks": [
            ("Facebook",       g + q(f"{forms} site:facebook.com")),
            ("Instagram",      g + q(f"{forms} site:instagram.com")),
            ("Twitter/X",      g + q(f"{forms} (site:x.com OR site:twitter.com)")),
            ("LinkedIn",       g + q(f"{forms} site:linkedin.com")),
            ("TikTok",         g + q(f"{forms} site:tiktok.com")),
            ("YouTube",        g + q(f"{forms} site:youtube.com")),
            ("Telegram-Gruppen", g + q(f"{forms} (site:t.me OR telegram group)")),
            ("Reddit",         g + q(f"{forms} site:reddit.com")),
            ("Kleinanzeigen",  g + q(f"{forms} (ebay-kleinanzeigen OR kleinanzeigen OR marktplatz)")),
        ],
        "Konto-Recovery (manuell prüfen)": [
            ("Facebook",       "https://www.facebook.com/login/identify/"),
            ("Instagram",      "https://www.instagram.com/accounts/password/reset/"),
            ("Twitter/X",      "https://x.com/account/begin_password_reset"),
            ("Google",         "https://accounts.google.com/signin/recovery"),
            ("Snapchat",       "https://accounts.snapchat.com/accounts/password_reset_request"),
        ],
        "Aggregatoren": [
            ("Epieos (Phone→Konten)", f"https://epieos.com/?q={q(e164)}&t=phone"),
            ("OSINT Industries",      f"https://osint.industries/ (Phone: {e164})"),
            ("PhoneInfoga (lokal)",   "python3 -m phoneinfoga scan -n " + e164),
        ],
    }
    for section, links in sections.items():
        ui.rule(section, ui.GREY)
        for label, url in links:
            print(f"  {ui.BCYAN}▸{ui.RESET} {label:28s} {ui.GREY}{url}{ui.RESET}")
    ui.pause()


def _email_permutations() -> None:
    """E-Mail-Permutationen aus Name + Domain generieren."""
    ui.clear()
    ui.rule("✉  E-MAIL PERMUTATIONEN", ui.BCYAN)
    print(f"\n  {ui.GREY}Generiert mögliche E-Mail-Adressen aus Vor-/Nachname{ui.RESET}\n")
    first = ui.ask("Vorname").strip().lower()
    last = ui.ask("Nachname").strip().lower()
    domain = ui.ask("Domain (z.B. gmail.com, web.de)").strip().lower()
    if not first or not last or not domain:
        ui.err("Alle Felder erforderlich."); ui.pause(); return
    f, l = first, last
    fi, li = f[0], l[0]
    permutations = [
        f"{f}.{l}@{domain}",
        f"{f}{l}@{domain}",
        f"{fi}{l}@{domain}",
        f"{f}{li}@{domain}",
        f"{f}.{li}@{domain}",
        f"{fi}.{l}@{domain}",
        f"{l}.{f}@{domain}",
        f"{l}{f}@{domain}",
        f"{l}{fi}@{domain}",
        f"{f}_{l}@{domain}",
        f"{l}_{f}@{domain}",
        f"{fi}_{l}@{domain}",
    ]
    print(f"\n  {ui.BOLD}Mögliche E-Mail-Adressen für {first.title()} {last.title()} @ {domain}:{ui.RESET}\n")
    q = urllib.parse.quote
    for mail in permutations:
        g_url = f"https://www.google.com/search?q={q(chr(34) + mail + chr(34))}"
        print(f"  {ui.BGREEN}{mail:35s}{ui.RESET} → {ui.GREY}{g_url}{ui.RESET}")
    print()
    print(f"  {ui.BOLD}Breach-Check (alle auf einmal):{ui.RESET}")
    print(f"  {ui.GREY}HaveIBeenPwned API: https://haveibeenpwned.com/API/v3")
    print(f"  Hunter.io Verify: https://api.hunter.io/v2/email-verifier?email=<mail>&api_key=...")
    print(f"  Skript: for mail in {' '.join(permutations[:3])} ...; do curl hibp; done{ui.RESET}")
    ui.pause()


def _breach_guide() -> None:
    """Breach-Check Anleitung – HaveIBeenPwned, Dehashed, LeakCheck."""
    ui.clear()
    ui.rule("🔓 BREACH-CHECK ANLEITUNG", ui.BYELLOW)
    print(f"""
  {ui.BOLD}HaveIBeenPwned (HIBP) – kostenlos für E-Mail:{ui.RESET}
  {ui.GREY}Web: https://haveibeenpwned.com/
  API: curl -H "hibp-api-key: <KEY>" https://haveibeenpwned.com/api/v3/breachedaccount/<email>
  Passwort-Check: https://haveibeenpwned.com/Passwords  (SHA1-Präfix-Methode){ui.RESET}

  {ui.BOLD}Dehashed – kostenpflichtig (Telefon + E-Mail):{ui.RESET}
  {ui.GREY}https://dehashed.com/
  API: curl -H "Dehashed-Api-Key: <KEY>" "https://api.dehashed.com/search?query=phone:<NUMMER>"
  Sucht in Datenlecks nach Telefonnummer → E-Mail, Name, Passwort-Hash{ui.RESET}

  {ui.BOLD}LeakCheck – Telefon-Datenbanken:{ui.RESET}
  {ui.GREY}https://leakcheck.io/
  API: POST /api/v2/query  body: {"query": "+49170...", "type": "phone"}{ui.RESET}

  {ui.BOLD}IntelX (Intelligence X):{ui.RESET}
  {ui.GREY}https://intelx.io/ – Darkweb + Pastes + Breaches
  Sucht Telefon, E-Mail, IP, BTC-Adresse{ui.RESET}

  {ui.BOLD}Snusbase:{ui.RESET}
  {ui.GREY}https://snusbase.com/ – Breached DB Search{ui.RESET}

  {ui.BOLD}OSINT Framework (Übersicht aller Tools):{ui.RESET}
  {ui.GREY}https://osintframework.com/ → Phone Number → alle verlinkten Tools{ui.RESET}

  {ui.BOLD}CLI-Tool: holehe (E-Mail → Konten):{ui.RESET}
  {ui.GREY}pip install holehe
  holehe <email@domain.de>    # prüft 120+ Dienste{ui.RESET}

  {ui.BOLD}CLI-Tool: phoneinfoga:{ui.RESET}
  {ui.GREY}https://github.com/sundowndev/phoneinfoga
  phoneinfoga scan -n +49170XXXXXXX{ui.RESET}
""")
    ui.pause()


def _callerid_lookup(raw: str) -> None:
    """CallerID-Datenbanken – Truecaller, Sync.me, Reverse-Lookup."""
    ui.clear()
    ui.rule("🕵 CALLERID DATENBANKEN", ui.BCYAN)
    try:
        n = phonenumbers.parse(raw, "DE" if not raw.startswith("+") else None)
        e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
        natl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.NATIONAL)
        intl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    except Exception:
        e164 = raw; natl = raw; intl = raw
    natl_clean = natl.replace(" ", "").replace("/", "").replace("-", "")
    digits = e164.lstrip("+")
    q = urllib.parse.quote
    print(f"\n  Nummer: {ui.BOLD}{intl}{ui.RESET}\n")
    sources = [
        ("Truecaller (Account nötig)", f"https://www.truecaller.com/search/de/{q(natl_clean)}"),
        ("Sync.me",                   f"https://sync.me/search/?number={q(digits)}"),
        ("Das Örtliche (DE Rückwärtssuche)", f"https://www.dasoertliche.de/rueckwaertssuche/?ph={q(natl_clean)}"),
        ("Telefonbuch.de",            f"https://www.telefonbuch.de/r?n={q(natl_clean)}"),
        ("Das Telefonbuch",           f"https://www.dastelefonbuch.de/?kw={q(natl_clean)}&cmd=suche"),
        ("Anrufmonitor (DE)",         f"https://www.anrufmonitor.de/{q(natl_clean)}"),
        ("NumLookup (INT)",           f"https://numlookup.com/search?phone={q(e164)}"),
        ("SpamCalls",                 f"https://spamcalls.net/de/search?num={q(natl_clean)}"),
        ("PhoneInfoga (lokal)",       f"python3 -m phoneinfoga scan -n {e164}"),
        ("Opencnam (API, US)",        f"https://api.opencnam.com/v3/phone/{q(digits)}"),
    ]
    print(f"  {ui.BOLD}CallerID-Quellen:{ui.RESET}\n")
    for label, url in sources:
        print(f"  {ui.BCYAN}▸{ui.RESET} {label:35s} {ui.GREY}{url}{ui.RESET}")
    print()
    print(f"  {ui.BOLD}Hinweis:{ui.RESET}")
    print(f"  {ui.GREY}Truecaller zeigt am meisten – aber Konto + Einverständnis erforderlich.")
    print(f"  PhoneInfoga (lokal): pip install phoneinfoga{ui.RESET}")
    ui.pause()


def _carrier_location(adb) -> None:
    """Carrier-Standort aus MCC/MNC ermitteln."""
    ui.clear()
    ui.rule("📍 CARRIER-STANDORT (MCC/MNC)", ui.BCYAN)
    print()
    # Gerätedaten wenn ADB verfügbar
    mcc_mnc = ""
    if adb:
        try:
            op = adb.shell("getprop gsm.operator.numeric 2>/dev/null").strip()
            if op:
                mcc_mnc = op
                mcc, mnc = op[:3], op[3:]
                ui.kv("MCC/MNC vom Gerät", f"{mcc_mnc} (MCC={mcc}, MNC={mnc})")
        except Exception:
            pass
    # MCC/MNC Datenbank (Ausschnitt)
    _MCC = {
        "262": "Deutschland", "232": "Österreich", "228": "Schweiz",
        "310": "USA", "234": "Großbritannien", "208": "Frankreich",
        "222": "Italien", "214": "Spanien", "204": "Niederlande",
        "260": "Polen", "286": "Türkei", "250": "Russland",
        "505": "Australien", "440": "Japan", "460": "China",
    }
    _MNC_DE = {
        "01": "T-Mobile/Telekom", "02": "Vodafone", "03": "E-Plus (ehem.)",
        "07": "O2/Telefónica", "06": "T-Mobile", "09": "Vodafone",
        "20": "Telekom (Virtuell)", "77": "E-Plus (1&1)",
    }
    if mcc_mnc:
        mcc, mnc = mcc_mnc[:3], mcc_mnc[3:]
        land = _MCC.get(mcc, "Unbekannt")
        netz = _MNC_DE.get(mnc, "Unbekannt") if mcc == "262" else "Netz aus MNC-DB"
        ui.kv("Land",    land)
        ui.kv("Netz",    netz)
    else:
        mcc_mnc = ui.ask("MCC+MNC manuell eingeben (z.B. 26202 für Vodafone DE)")
        if mcc_mnc and len(mcc_mnc) >= 5:
            mcc, mnc = mcc_mnc[:3], mcc_mnc[3:]
            land = _MCC.get(mcc, "?")
            netz = _MNC_DE.get(mnc, "?") if mcc == "262" else "?"
            ui.kv("Land", land)
            ui.kv("Netz", netz)
    print(f"\n  {ui.BOLD}Vollständige MCC/MNC-Datenbank:{ui.RESET}")
    print(f"  {ui.GREY}https://www.mcc-mnc.com/")
    print(f"  https://www.mobilefish.com/services/mobile_country_code/mobile_country_code.php{ui.RESET}")
    ui.pause()


def _run_ai_plan(raw: str) -> None:
    """KI-Rechercheplan für Telefonnummer via Ollama."""
    try:
        n = phonenumbers.parse(raw, "DE" if not raw.startswith("+") else None)
        e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
        country = _country_name(n)
        car = carrier.name_for_number(n, "de") or "?"
        ltype = _line_type(n)
    except Exception:
        e164 = raw; country = "?"; car = "?"; ltype = "?"
    _ai_plan(e164, raw, country, car, ltype)


def _full_export(raw: str) -> None:
    """Vollständiger Export aller OSINT-Daten als TXT."""
    import os, time as _time
    ui.clear()
    try:
        n = phonenumbers.parse(raw, "DE" if not raw.startswith("+") else None)
        valid = phonenumbers.is_valid_number(n)
        e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
        intl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        natl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.NATIONAL)
        country = _country_name(n)
        car = carrier.name_for_number(n, "de") or "—"
        ltype = _line_type(n)
        tzs = timezone.time_zones_for_number(n)
        region = geocoder.description_for_number(n, "de") or "—"
    except Exception as e:
        ui.err(f"Parse-Fehler: {e}"); ui.pause(); return

    digits = e164.lstrip("+")
    natl_clean = natl.replace(" ", "").replace("/", "").replace("-", "")
    q = urllib.parse.quote
    ts = _time.strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# TELEFON-OSINT REPORT",
        f"# Erstellt: {ts}",
        f"# Nummer: {intl}",
        "",
        "## BASIS-INFORMATIONEN",
        f"Gültig:       {'✓' if valid else '✗'}",
        f"E.164:        {e164}",
        f"International:{intl}",
        f"National:     {natl}",
        f"Land:         {country}",
        f"Region:       {region}",
        f"Carrier:      {car}",
        f"Typ:          {ltype}",
        f"Zeitzonen:    {', '.join(tzs)}",
        "",
        "## MESSENGER",
        f"WhatsApp:  https://wa.me/{digits}",
        f"Telegram:  https://t.me/+{digits}",
        "",
        "## SPAM-CHECK",
    ]
    for label, url in _reputation_links(digits, natl):
        lines.append(f"  {label}: {url}")
    lines += ["", "## SOCIAL-MEDIA SUCHE"]
    for label, url in _social_search(e164, natl):
        lines.append(f"  {label}: {url}")
    lines += ["", "## OSINT-LINKS"]
    for label, url in _osint_links(e164, natl, n):
        lines.append(f"  {label}: {url}")
    lines += ["", "## CALLERID / LOOKUP"]
    callerid_sources = [
        f"  Truecaller:   https://www.truecaller.com/search/de/{q(natl_clean)}",
        f"  Das Örtliche: https://www.dasoertliche.de/rueckwaertssuche/?ph={q(natl_clean)}",
        f"  Sync.me:      https://sync.me/search/?number={q(digits)}",
        f"  NumLookup:    https://numlookup.com/search?phone={q(e164)}",
    ]
    lines += callerid_sources
    lines += [
        "",
        "## HINWEIS",
        "Name/Adresse/Konten sind NICHT aus der Nummer abrufbar – nur via OSINT-Recherche,",
        "falls die Person sie selbst öffentlich gemacht hat. Nur für legitime Zwecke nutzen.",
    ]
    body = "\n".join(lines) + "\n"
    out_dir = os.path.expanduser("~/Schreibtisch/Androidpanzer/phone_osint")
    os.makedirs(out_dir, exist_ok=True)
    fn = os.path.join(out_dir, f"{digits}_{_time.strftime('%Y%m%d_%H%M%S')}.txt")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(body)
    ui.show_report(body, f"Telefon-OSINT · {intl}", fn, note="Vollständiger Report")
    ui.pause()


def analyze(raw: str) -> None:
    ui.clear()
    # Parsen (Default-Region DE, falls keine +Vorwahl)
    try:
        n = phonenumbers.parse(raw, "DE" if not raw.strip().startswith("+") else None)
    except Exception as e:  # noqa: BLE001
        ui.err(f"Nicht parsebar: {e}"); ui.pause(); return

    valid = phonenumbers.is_valid_number(n)
    possible = phonenumbers.is_possible_number(n)
    e164 = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.E164)
    intl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    natl = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.NATIONAL)
    rfc = phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.RFC3966)

    ui.rule(f"Analyse · {intl}", ui.BCYAN)
    ui.kv("Gültig", f"{ui.BGREEN}ja{ui.RESET}" if valid else
          (f"{ui.BYELLOW}nur möglich (Format ok, evtl. nicht vergeben){ui.RESET}" if possible
           else f"{ui.BRED}nein{ui.RESET}"))
    ui.kv("E.164", e164)
    ui.kv("International", intl)
    ui.kv("National", natl)
    ui.kv("RFC3966", rfc)
    ui.kv("Ländercode", f"+{n.country_code}")
    ui.kv("Nationale Nummer", str(n.national_number))

    # Geo / Carrier / Typ
    region = geocoder.description_for_number(n, "de") or geocoder.description_for_number(n, "en")
    car = carrier.name_for_number(n, "de") or carrier.name_for_number(n, "en")
    tzs = timezone.time_zones_for_number(n)
    ltype = _line_type(n)
    country = _country_name(n)

    ui.rule("Geografie & Netz", ui.CYAN)
    ui.kv("Land", country)
    ui.kv("Region/Gebiet", region or "—")
    ui.kv("Zeitzone(n)", ", ".join(tzs) or "—")
    ui.kv("Netzbetreiber", car or "— (bei portierten Nummern oft leer)")
    ui.kv("Leitungstyp", ltype)

    # Messenger-Präsenz (Klick-Links – kein automatisches Abfragen)
    digits = e164.lstrip("+")
    ui.rule("Messenger-Präsenz (anklicken zum Prüfen)", ui.CYAN)
    ui.kv("WhatsApp", f"https://wa.me/{digits}")
    ui.kv("Telegram", f"https://t.me/+{digits}")
    ui.kv("Signal", "in Signal-App: Kontakt hinzufügen → " + e164)
    ui.kv("Viber", f"viber://chat?number={urllib.parse.quote(e164)}")

    # Social-Media: „Ist eine Nummer registriert?" via Account-Recovery-Flow
    ui.rule("Social-Media · Konto-Registrierung prüfen (Recovery-Flow)", ui.CYAN)
    ui.info("Diese Seiten zeigen im 'Passwort vergessen'-Schritt, ob ein Konto mit der Nummer "
            "existiert (oft maskiert: +49•••••717). Manuell prüfen:")
    for label, url in _recovery_links(e164, natl):
        print(f"  {ui.BCYAN}▸{ui.RESET} {label}: {ui.GREY}{url}{ui.RESET}")

    # Aggregator-Dienste (machen mehrere Plattformen auf einmal)
    ui.rule("Aggregatoren (mehrere Plattformen)", ui.CYAN)
    for label, url in [
        ("Epieos (Phone→Konten)", f"https://epieos.com/?q={urllib.parse.quote(e164)}&t=phone"),
        ("PhoneInfoga-Web (falls gehostet)", "https://github.com/sundowndev/phoneinfoga"),
        ("Castrick / Numlookup", f"https://numlookup.com/search?phone={urllib.parse.quote(e164)}"),
        ("OSINT Industries", f"https://osint.industries/ (Phone: {e164})"),
    ]:
        print(f"  {ui.BCYAN}▸{ui.RESET} {label}: {ui.GREY}{url}{ui.RESET}")

    # Social-Media gezielte Suche (Dorks pro Netzwerk)
    ui.rule("Social-Media gezielte Suche", ui.CYAN)
    for label, url in _social_search(e164, natl):
        print(f"  {ui.BCYAN}▸{ui.RESET} {label}: {ui.GREY}{url}{ui.RESET}")

    # OSINT-Footprint
    ui.rule("OSINT-Recherche (öffentliche Spuren)", ui.CYAN)
    for label, url in _osint_links(e164, natl, n):
        print(f"  {ui.BCYAN}▸{ui.RESET} {label}")
        print(f"     {ui.GREY}{url}{ui.RESET}")

    # Reputation / Spam
    ui.rule("Spam-/Scam-Reputation", ui.CYAN)
    for label, url in _reputation_links(digits, natl):
        print(f"  {ui.BCYAN}▸{ui.RESET} {label}: {ui.GREY}{url}{ui.RESET}")

    # Fund ins OSINT-Sammelregister (für KI-Analyst)
    try:
        from . import osint
        osint._note(f"Telefon {e164}: {country}, {car or '?'}, {ltype}, {region or '?'}")
    except Exception:  # noqa: BLE001
        pass

    print()
    ui.warn("Ehrlich: Name/Adresse/Konten sind NICHT aus der Nummer abrufbar – nur via "
            "obige Recherche, falls die Person sie selbst öffentlich gemacht hat.")
    # KI-Rechercheplan
    if ui.confirm("KI-Rechercheplan für diese Nummer erstellen?", False):
        _ai_plan(e164, natl, country, car, ltype)
    if ui.confirm("Report als Datei speichern?", False):
        _save(e164, intl, natl, country, region, car, ltype, tzs, valid)
    if ui.confirm("Online-Lookup über kostenlose API (NumVerify, API-Key nötig)?", False):
        _api_lookup(e164)
    ui.pause()


def _ai_plan(e164, natl, country, car, ltype) -> None:
    try:
        from . import aishell
        if not aishell._ollama_up():
            ui.warn("ollama nicht erreichbar (ollama serve)."); return
        m = aishell._pick_model()
        ans = aishell._gen(m,
            f"Telefonnummer {e164} ({country}, Netz {car}, Typ {ltype}).\n"
            "Erstelle einen konkreten OSINT-Rechercheplan auf Deutsch: welche Plattformen/Dienste "
            "in welcher Reihenfolge prüfen, welche Such-Dorks, worauf achten. NUR legale, "
            "öffentliche Quellen. Stichpunkte.",
            "Du bist ein OSINT-Experte für legale Recherche.", timeout=150)
        ui.pager(ans, "KI-Rechercheplan")
    except Exception as e:  # noqa: BLE001
        ui.err(str(e))


def _line_type(n) -> str:
    t = phonenumbers.number_type(n)
    return {
        phonenumbers.PhoneNumberType.MOBILE: "📱 Mobil",
        phonenumbers.PhoneNumberType.FIXED_LINE: "☎ Festnetz",
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "Festnetz oder Mobil",
        phonenumbers.PhoneNumberType.VOIP: "🌐 VoIP",
        phonenumbers.PhoneNumberType.TOLL_FREE: "Gebührenfrei (0800)",
        phonenumbers.PhoneNumberType.PREMIUM_RATE: "⚠ Premium (teuer!)",
        phonenumbers.PhoneNumberType.SHARED_COST: "Shared-Cost",
        phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "Persönliche Nummer",
        phonenumbers.PhoneNumberType.PAGER: "Pager",
        phonenumbers.PhoneNumberType.UAN: "UAN",
        phonenumbers.PhoneNumberType.VOICEMAIL: "Voicemail",
    }.get(t, "unbekannt")


def _country_name(n) -> str:
    rc = phonenumbers.region_code_for_number(n) or ""
    names = {"DE": "Deutschland", "AT": "Österreich", "CH": "Schweiz", "US": "USA",
             "GB": "Großbritannien", "FR": "Frankreich", "IT": "Italien", "ES": "Spanien",
             "NL": "Niederlande", "PL": "Polen", "TR": "Türkei", "RU": "Russland"}
    return f"{names.get(rc, rc)} ({rc})" if rc else "unbekannt"


def _osint_links(e164: str, natl: str, n) -> list[tuple[str, str]]:
    q = urllib.parse.quote
    digits = e164.lstrip("+")
    natl_clean = natl.replace(" ", "").replace("/", "").replace("-", "")
    variants = f'"{e164}" OR "{natl}" OR "{natl_clean}"'
    return [
        ("Google (exakte Phrasen)", f"https://www.google.com/search?q={q(variants)}"),
        ("Google Dork (Profile/Docs)",
         f"https://www.google.com/search?q={q(f'{e164} OR {natl_clean} (site:facebook.com OR site:linkedin.com OR site:twitter.com OR filetype:pdf)')}"),
        ("Bing", f"https://www.bing.com/search?q={q(variants)}"),
        ("DuckDuckGo", f"https://duckduckgo.com/?q={q(variants)}"),
        ("Facebook-Suche", f"https://www.facebook.com/search/top?q={q(e164)}"),
        ("Truecaller (Account nötig)", f"https://www.truecaller.com/search/de/{q(natl_clean)}"),
        ("Reverse-Lookup (sync.me)", f"https://sync.me/search/?number={q(digits)}"),
        ("Das Örtliche (DE Rückwärtssuche)", f"https://www.dasoertliche.de/rueckwaertssuche/?ph={q(natl_clean)}"),
    ]


def _recovery_links(e164: str, natl: str) -> list[tuple[str, str]]:
    """Direktlinks zu den 'Konto wiederherstellen'-Flows – dort sieht man, ob eine
    Nummer registriert ist (maskiert). Manuelle Prüfung, kein Auto-Scraping."""
    return [
        ("Facebook (Passwort vergessen)", "https://www.facebook.com/login/identify/"),
        ("Instagram (Hilfe beim Login)", "https://www.instagram.com/accounts/password/reset/"),
        ("Google (Konto-Wiederherstellung)", "https://accounts.google.com/signin/recovery"),
        ("Twitter/X (Passwort zurücksetzen)", "https://x.com/account/begin_password_reset"),
        ("PayPal (Login → Probleme)", "https://www.paypal.com/authflow/password-recovery/"),
        ("Microsoft", "https://account.live.com/ResetPassword.aspx"),
        ("Amazon", "https://www.amazon.de/ap/forgotpassword"),
        ("Snapchat", "https://accounts.snapchat.com/accounts/password_reset_request"),
        ("LinkedIn", "https://www.linkedin.com/uas/request-password-reset"),
    ]


def _social_search(e164: str, natl: str) -> list[tuple[str, str]]:
    q = urllib.parse.quote
    natl_clean = natl.replace(" ", "").replace("/", "").replace("-", "")
    forms = f'"{e164}" OR "{natl}" OR "{natl_clean}"'
    g = "https://www.google.com/search?q="
    return [
        ("Facebook-Profile", g + q(f"{forms} site:facebook.com")),
        ("Instagram", g + q(f"{forms} site:instagram.com")),
        ("Twitter/X", g + q(f"{forms} (site:x.com OR site:twitter.com)")),
        ("LinkedIn", g + q(f"{forms} site:linkedin.com")),
        ("TikTok", g + q(f"{forms} site:tiktok.com")),
        ("Telegram-Gruppen", g + q(f"{forms} (site:t.me OR telegram)")),
        ("Kleinanzeigen/Marktplätze", g + q(f"{forms} (kleinanzeigen OR ebay OR marktplatz)")),
        ("Foren/Pastes", g + q(f"{forms} (site:pastebin.com OR forum)")),
    ]


def _reputation_links(digits: str, natl: str) -> list[tuple[str, str]]:
    q = urllib.parse.quote
    natl_clean = natl.replace(" ", "").replace("/", "").replace("-", "")
    return [
        ("tellows (Spam-Score)", f"https://www.tellows.de/num/{q(natl_clean)}"),
        ("clever-dialer", f"https://www.cleverdialer.de/telefonnummer/{q(natl_clean)}"),
        ("WerruftAn", f"https://www.werruftan.com/Phonenumber-{q(natl_clean)}"),
        ("Should I Answer", f"https://www.shouldianswer.com/phone-number/{q(natl_clean)}"),
    ]


def _save(e164, intl, natl, country, region, car, ltype, tzs, valid) -> None:
    import os
    out = os.path.expanduser("~/Schreibtisch/Androidpanzer/phone_osint")
    os.makedirs(out, exist_ok=True)
    fn = os.path.join(out, e164.lstrip("+") + ".txt")
    digits = e164.lstrip("+")
    lines = [f"# Nummer-Analyse {intl}",
             f"Gültig: {valid}", f"E164: {e164}", f"National: {natl}",
             f"Land: {country}", f"Region: {region}", f"Carrier: {car}",
             f"Typ: {ltype}", f"Zeitzonen: {', '.join(tzs)}", "",
             "Messenger:", f"  WhatsApp: https://wa.me/{digits}",
             f"  Telegram: https://t.me/+{digits}", "", "OSINT-Links:"]
    lines += [f"  {label}: {url}" for label, url in _osint_links(e164, natl, None)]
    body = "\n".join(lines) + "\n"
    with open(fn, "w", encoding="utf-8") as f:
        f.write(body)
    ui.show_report(body, f"Telefon-OSINT · {intl}", fn, note="OSINT-Bericht")


def _api_lookup(e164: str) -> None:
    key = ui.ask("NumVerify API-Key (kostenlos auf numverify.com; leer = überspringen)")
    if not key:
        return
    try:
        import json
        import urllib.request
        url = (f"http://apilayer.net/api/validate?access_key={key}"
               f"&number={urllib.parse.quote(e164)}&format=1")
        data = json.loads(urllib.request.urlopen(url, timeout=20).read())
        ui.rule("NumVerify-Ergebnis", ui.CYAN)
        for k in ("country_name", "location", "carrier", "line_type", "valid"):
            if k in data:
                ui.kv(k, data[k])
    except Exception as e:  # noqa: BLE001
        ui.err(f"API-Fehler: {e}")
