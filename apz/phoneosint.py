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
        ui.banner(subtitle="📞 Handynummer-Analyse (OSINT)")
        ui.info("Nummer im Format +49170… (international, mit Ländercode) eingeben.\n")
        num = ui.ask("Telefonnummer (oder 'q')")
        if not num or num.lower() in ("q", "quit", "0", "back"):
            return
        analyze(num)


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
