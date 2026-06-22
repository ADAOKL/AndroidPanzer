"""Daten-Forensik & Wiederherstellung.

Extrahiert – mit Zeitstempeln – das Maximum an Nutzerspuren von einem
verbundenen Gerät (eigenes/autorisiert untersuchtes Gerät):

  • Konten (Google & alle anderen) inkl. Residuen abgemeldeter/gelöschter
  • Anrufliste, SMS/MMS, Kontakte
  • Browser-Verläufe (Chrome/andere) – Root
  • Social-Media- & Messenger-Apps + deren Datenbanken/Voicenotes – Root
  • komplettes Medien-Inventar (Bilder/Videos/Audio) mit Aufnahme-/Änderungszeit
  • Sprachnachrichten / Anrufaufnahmen
  • Play-Store-Historie (Install-/Update-Zeit, Reinstall-Spuren)
  • Bewertung der Wiederherstellbarkeit gelöschter Daten

Ohne Root nur, was Content-Provider/Shell-UID legal liefern. Mit Root deutlich
tiefer. Nichts wird gefälscht – fehlt der Zugriff, sagt das Tool das klar.
"""
from __future__ import annotations

import os
import re
import time

from . import ui
from .adb import ADB
from .util import LOG, outdir, shq

OUT = outdir("forensik")


def _ts(ms_or_s: str) -> str:
    """Epoch (ms oder s) → lesbarer Zeitstempel."""
    try:
        v = int(ms_or_s)
    except (TypeError, ValueError):
        return "—"
    if v > 10_000_000_000:  # ms
        v //= 1000
    if v <= 0:
        return "—"
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v))
    except (OSError, ValueError, OverflowError):
        return str(ms_or_s)


def _query(adb: ADB, uri: str, projection: str = "", limit: int = 0, sort: str = "") -> list[dict]:
    """content query → Liste von Zeilen-Dicts. Robust gegen Berechtigungsfehler."""
    cmd = f"content query --uri {uri}"
    if projection:
        cmd += f" --projection {projection}"
    if sort:
        cmd += f" --sort '{sort}'"
    out = adb.shell(cmd, timeout=40)
    rows = []
    if not out or "Error" in out[:80] or "Exception" in out[:120] or "permission" in out.lower()[:120]:
        return rows
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("Row:"):
            continue
        d = {}
        for m in re.finditer(r"([A-Za-z0-9_]+)=([^,]*?)(?:,\s|$)", line.split(" ", 2)[-1]):
            d[m.group(1)] = m.group(2).strip()
        rows.append(d)
        if limit and len(rows) >= limit:
            break
    return rows


def _mkout() -> str:
    os.makedirs(OUT, exist_ok=True)
    return OUT


_quiet = {"on": False}   # beim Komplettscan True → keine Einzel-Pager (Bericht-Flut)


def _write(name: str, content: str, show: bool = True) -> str:
    _mkout()
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    if show and not _quiet["on"]:
        ui.show_report(content, name, p, note="Bericht")
    return p


# ====================================================================== #
#  Menü
# ====================================================================== #
def menu(adb: ADB, dev, st) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="Daten-Forensik & Wiederherstellung")
        root = st.get("is_root")
        ui.kv("Root-Zugriff", f"{ui.BGREEN}ja – Tiefenzugriff aktiv{ui.RESET}" if root
              else f"{ui.GREY}nein – nur Content-Provider-Ebene{ui.RESET}")
        ui.warn("Nur für dein eigenes / autorisiert untersuchtes Gerät verwenden.")
        ch = ui.menu("Forensik-Module", [
            ("1", "⏱  KOMPLETT-SCAN (alles, automatisch, mit Zeitstempeln)"),
            ("2", "👤 Konten – Google & alle (inkl. Spuren gelöschter)"),
            ("3", "📞 Anrufliste (mit Datum/Uhrzeit/Dauer)"),
            ("4", "💬 SMS / MMS (mit Zeitstempel)"),
            ("5", "👥 Kontakte"),
            ("6", "🌐 Browser-Verläufe (Chrome & andere)"),
            ("7", "📲 Social-Media & Messenger (Apps + Daten)"),
            ("8", "🖼  Medien-Inventar (Bilder/Videos/Audio + Zeit)"),
            ("9", "🎙  Sprachnachrichten / Anrufaufnahmen"),
            ("10", "🛒 Play-Store-Historie (Install/Update/Reinstall)"),
            ("11", "🗑  Wiederherstellbarkeit gelöschter Daten prüfen"),
            ("12", "📥 Komplettes Datenpartition-Backup ziehen"),
            ("13", f"{ui.BCYAN}🧬 MAXIMUM-DEEP-SCAN (WLAN/Standort/Kalender/Rechte/…){ui.RESET}"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        if ch == "13":
            from . import deepforensics
            deepforensics.menu(adb, dev, st)
            continue
        {
            "1": full_scan, "2": accounts, "3": call_log, "4": sms, "5": contacts,
            "6": browser_history, "7": social_media, "8": media_inventory,
            "9": voice_messages, "10": playstore_history, "11": recovery_assessment,
            "12": pull_userdata,
        }.get(ch, lambda *a: None)(adb, dev, st)


# ====================================================================== #
#  1 · Komplett-Scan
# ====================================================================== #
def full_scan(adb: ADB, dev, st) -> None:
    ui.clear()
    ui.banner(subtitle="Forensik-Komplettscan")
    ui.info("Sammle alle verfügbaren Spuren … das kann etwas dauern.\n")
    steps = [
        ("Konten", accounts), ("Anrufe", call_log), ("SMS/MMS", sms),
        ("Kontakte", contacts), ("Browser", browser_history),
        ("Social-Media", social_media), ("Medien", media_inventory),
        ("Sprachnachrichten", voice_messages), ("Play-Store", playstore_history),
    ]
    LOG.info("Forensik-Komplettscan gestartet")
    ui.scan_overview([n for n, _ in steps] + ["Maximum-Deep-Scan (alle Tiefen-Sektionen)"],
                     "Daten-Forensik – Bereiche")
    _quiet["on"] = True   # während des Komplettscans keine Einzel-Pager
    try:
        for name, fn in steps:
            ui.rule(f"▶ {name}", ui.YELLOW)
            try:
                fn(adb, dev, st, _auto=True)
                LOG.info(f"Scan-Sektion ok: {name}")
            except Exception as e:  # noqa: BLE001
                ui.err(f"{name}: {e}")
                LOG.exception(f"Scan-Sektion fehlgeschlagen: {name}", e)
        # Maximum-Deep-Scan automatisch anhängen (WLAN/Standort/Kalender/Rechte/Sicherheit/…)
        try:
            from . import deepforensics
            deepforensics.run_all(adb, dev, st, embedded=True)
        except Exception as e:  # noqa: BLE001
            ui.err(f"Deep-Scan: {e}")
            LOG.exception("Deep-Scan im Komplettscan fehlgeschlagen", e)
    finally:
        _quiet["on"] = False
    ui.ok(f"Komplettscan fertig. Berichte unter: {OUT}")
    if LOG.path:
        ui.info(f"Lauf-Log: {LOG.path}")
    # Ansehen & Exportieren direkt anbieten (HTML/JSON/Markdown + SHA-256)
    try:
        from . import deepforensics
        deepforensics._view_export_menu(adb, dev, st)
    except Exception as e:  # noqa: BLE001
        LOG.exception("View/Export nach Komplettscan", e)
        ui.pause()


# ====================================================================== #
#  2 · Konten
# ====================================================================== #
def accounts(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Konten-Analyse", ui.CYAN)
    dump = adb.shell("dumpsys account", timeout=30)
    found = re.findall(r"Account\s*\{name=([^,]+),\s*type=([^}]+)\}", dump)
    lines = [f"=== AKTIVE KONTEN ({len(found)}) ==="]
    if found:
        for name, typ in found:
            label = _account_label(typ)
            print(f"  {ui.BGREEN}●{ui.RESET} {name:<40} {ui.GREY}{label}{ui.RESET}")
            lines.append(f"AKTIV  {name:<45} {typ}")
    else:
        ui.warn("Keine aktiven Konten über dumpsys sichtbar (evtl. eingeschränkt).")

    # Letzte Sync-/Auth-Zeiten
    sync = re.findall(r"(\S+@\S+|\S+)\s+.*?(?:lastSuccessTime|syncTime|last)\D*(\d{12,13})", dump)
    if sync:
        print(f"\n  {ui.BOLD}Letzte Sync-/Auth-Zeiten:{ui.RESET}")
        for acc, t in sync[:20]:
            print(f"    {ui.GREY}{_ts(t)}{ui.RESET}  {acc}")
            lines.append(f"SYNC   {_ts(t)}  {acc}")

    # Auth-Events aus dem Log (auch kürzlich abgemeldete tauchen hier auf)
    authlog = adb.shell("logcat -d -t 2000 | grep -iE 'GLSUser|account.*(add|remove|login|logout)|Auth' | tail -n 25")
    if authlog.strip():
        print(f"\n  {ui.BOLD}Konto-Ereignisse (Log – auch An-/Abmeldungen):{ui.RESET}")
        for l in authlog.splitlines()[-15:]:
            print(f"    {ui.GREY}{l[:110]}{ui.RESET}")
        lines.append("\n=== KONTO-EREIGNISSE (LOG) ===\n" + authlog)

    # Root: Residuen gelöschter/abgemeldeter Konten
    if st.get("is_root"):
        print(f"\n  {ui.BOLD}{ui.YELLOW}Root-Tiefenscan: Konten-Residuen gelöschter Accounts{ui.RESET}")
        res = adb.shell(
            "for db in /data/system_ce/0/accounts_ce.db /data/system_de/0/accounts_de.db "
            "/data/system/users/0/accounts.db; do echo \"# $db\"; "
            "sqlite3 $db 'SELECT name,type FROM accounts;' 2>/dev/null; done", root=True)
        gms = adb.shell("find /data/data/com.google.android.gms -name '*.db' 2>/dev/null | head", root=True)
        if res.strip():
            ui.pager(res, "accounts_ce/de.db (auch ältere Einträge)")
            lines.append("\n=== ROOT: accounts DBs ===\n" + res)
        if gms.strip():
            print(f"    {ui.GREY}GMS-DBs für tiefere Analyse:{ui.RESET}\n    " + gms.replace("\n", "\n    "))
    else:
        ui.info("Hinweis: Vollständig gelöschte Konten hinterlassen Residuen nur in "
                "geschützten DBs (accounts_ce.db) → mit Root sichtbar.")

    p = _write("konten.txt", "\n".join(lines))
    # Tiefenprofil je Konto (50+ Fakten)
    if found:
        if _auto or ui.confirm("\nDetail-Tiefenprofil je Konto erstellen (50+ Infos)?", True):
            for name, typ in found:
                account_deep(adb, name, typ, dump, _auto=_auto)
    if not _auto:
        ui.ok(f"Gespeichert: {p}"); ui.pause()


def account_deep(adb: ADB, name: str, typ: str, accdump: str = "", _auto=False) -> None:
    """Sammelt 50+ Datenpunkte zu EINEM Konto (ohne Root, aus account+content+Providern)."""
    if not accdump:
        accdump = adb.shell("dumpsys account", timeout=30)
    content = adb.shell("dumpsys content", timeout=30)
    facts: list[str] = []

    def add(k, v):
        v = (str(v) or "").strip()
        if v and v.lower() not in ("", "null", "none"):
            facts.append(f"{len(facts)+1:>2}. {k}: {v}")

    if not _auto:
        ui.clear()
    ui.rule(f"Konto-Tiefenprofil · {name}", ui.BCYAN)

    # --- Stammdaten ---
    add("Konto-Name", name)
    add("Konto-Typ", typ)
    add("Anbieter", _account_label(typ))
    # zugehörige App/UID aus RegisteredServicesCache
    msvc = re.search(rf"type={re.escape(typ)}\}}, ComponentInfo\{{([^/]+)/([^}}]+)\}}, uid (\d+)", accdump)
    if msvc:
        add("Authenticator-App", msvc.group(1))
        add("Authenticator-Service", msvc.group(2))
        add("App-UID", msvc.group(3))
        pkg = msvc.group(1)
        pinfo = adb.shell(f"dumpsys package {shq(pkg)}", timeout=15)
        vn = re.search(r"versionName=(\S+)", pinfo)
        fi = re.search(r"firstInstallTime=([\d:\- ]+)", pinfo)
        lu = re.search(r"lastUpdateTime=([\d:\- ]+)", pinfo)
        inst = re.search(r"installerPackageName=(\S+)", pinfo)
        add("App-Version", vn.group(1) if vn else "")
        add("App installiert am", fi.group(1).strip() if fi else "")
        add("App aktualisiert am", lu.group(1).strip() if lu else "")
        add("App-Installquelle", inst.group(1) if inst else "")

    # --- Historie aus dumpsys account (add/remove/token-refresh) ---
    # AccountId der gesuchten Konten: über action_account_add Reihenfolge
    hist = re.findall(r"(-?\d+),(action_\w+),([\d:\- ]+),(\d+),accounts,(\d+)", accdump)
    adds = [(t, uid) for aid, act, t, uid, key in hist if act == "action_account_add"]
    removes = [(t, uid) for aid, act, t, uid, key in hist if act == "action_account_remove"]
    refreshes = [t for aid, act, t, uid, key in hist if act == "action_clear_password"]
    add("Konto-Hinzufügungen (gesamt)", len(adds))
    if adds:
        add("Erstes Konto hinzugefügt", adds[0][0].strip())
        add("Letztes Konto hinzugefügt", adds[-1][0].strip())
    add("Token-Refreshes (clear_password)", len(refreshes))
    if refreshes:
        add("Letzter Token-Refresh", refreshes[-1].strip())
    if removes:
        add("Konto-Entfernungen (Spuren gelöschter!)", "; ".join(t.strip() for t, _ in removes[:5]))

    # --- Sync-Dienste & letzte Sync-Zeiten (aus dumpsys content) ---
    esc = re.escape(name)
    authorities = sorted(set(re.findall(rf"{esc}/{re.escape(typ)}[^\n]*?\[([\w.\-]+)\]", content)))
    add("Synchronisierte Dienste (Anzahl)", len(authorities))
    SERVICE_DE = {
        "com.android.calendar": "Kalender", "com.android.contacts": "Kontakte",
        "com.google.android.apps.docs": "Drive/Docs", "gmail-ls": "Gmail",
        "com.google.android.gms.fitness": "Fit/Gesundheit", "com.google.android.gms.people": "Kontakte (People)",
        "com.google.android.gms.reminders": "Erinnerungen", "com.google.android.gms.chromesync": "Chrome-Sync",
        "com.google.android.location.reporting": "Standortverlauf", "com.google.android.gms.subscribedfeeds": "Feeds",
        "media": "Fotos/Medien", "com.android.keychain": "Keychain",
        "com.google.android.gms.games": "Play Games", "com.google.android.gms.games.background": "Play Games (BG)",
        "com.google.android.videos.sync": "Play Filme", "subscribedfeeds": "Abo-Feeds",
        "com.google.android.gms.auth.blockstore": "BlockStore", "com.google.android.gms.smart_profile": "Profil",
        "com.android.email.provider": "E-Mail", "com.google.android.gms.appdatasearch": "App-Suche",
    }
    for au in authorities:
        de = SERVICE_DE.get(au, au)
        # letzte erfolgreiche Sync-Zeit für diese Authority+Account
        m = re.search(rf"{esc}/{re.escape(typ)} u0\s+{re.escape(au)}.*?Success:\s*([\d:\- ]+)", content, re.S)
        when = m.group(1).strip() if m else ""
        add(f"Dienst · {de}", "aktiv" + (f", letzter Sync {when}" if when else ""))

    # --- Periodische Syncs (Intervalle) ---
    periods = re.findall(rf"{esc}/{re.escape(typ)} u0 \[([\w.\-]+)\] PERIODIC.*?period=([0-9dhms]+)", content)
    for au, per in periods[:8]:
        add(f"Periodischer Sync · {SERVICE_DE.get(au, au)}", f"alle {per}")

    # --- Letzte konkrete Sync-Operationen ---
    ops = re.findall(rf"#\d+\s*:\s*([\d:\- ]+)\s+(\w+)\s+{esc}/{re.escape(typ)} u0\s+([\w.\-]+)", content)
    for t, src, au in ops[:8]:
        add(f"Sync-Op {SERVICE_DE.get(au, au)} ({src})", t.strip())

    # --- Kontenspezifische Datenzähler ---
    where = shq("account_name='" + name.replace("'", "''") + "'")
    rc = adb.shell(f"content query --uri content://com.android.contacts/raw_contacts "
                   f"--where {where} 2>/dev/null | grep -c Row")
    if rc.strip().isdigit():
        add("Kontakte in diesem Konto", rc.strip())

    # --- Provider-spezifisch je Anbieter ---
    if "google" in typ:
        add("Google-Dienste-Backup-Konto", _is_backup_account(adb, name))
        gms_uid = re.search(r"type=com\.google\}, ComponentInfo\{com\.google\.android\.gms[^,]+, uid (\d+)", accdump)
        if gms_uid:
            add("GMS-UID", gms_uid.group(1))
        # Gmail-App-Datengröße als Aktivitätsindikator
        gmsz = adb.shell("du -sh /sdcard/Android/data/com.google.android.gm 2>/dev/null").split()[0:1]
        if gmsz:
            add("Gmail-Cache-Größe", gmsz[0])
    if "whatsapp" in typ:
        # WhatsApp-Nummer aus eigener JID erschließen + Medien
        for d, label in [("WhatsApp Images", "Bilder"), ("WhatsApp Video", "Videos"),
                         ("WhatsApp Voice Notes", "Sprachnachrichten"), ("WhatsApp Documents", "Dokumente")]:
            c = adb.shell(f"find '/sdcard/Android/media/com.whatsapp/WhatsApp/Media/{d}' -type f 2>/dev/null | wc -l")
            if c.strip().isdigit() and int(c) > 0:
                add(f"WhatsApp-Medien · {label}", c.strip())
        bk = adb.shell("ls /sdcard/Android/media/com.whatsapp/WhatsApp/Databases/*.crypt* 2>/dev/null | wc -l")
        if bk.strip().isdigit() and int(bk) > 0:
            add("WhatsApp Chat-Backups", bk.strip())

    # --- Ausgabe ---
    for f in facts:
        print(f"  {ui.GREY}{f}{ui.RESET}")
    ui.ok(f"{len(facts)} Fakten zu {name}")
    safe = "".join(c if c.isalnum() else "_" for c in name)[:40]
    _write(f"konto_{safe}.txt", f"# TIEFENPROFIL {name} ({typ})\n\n" + "\n".join(facts))


def _is_backup_account(adb: ADB, name: str) -> str:
    bm = adb.shell("bmgr list accounts 2>/dev/null; dumpsys backup | grep -i 'Current.*account' | head -1")
    return "ja" if name.split("@")[0] in bm else "—"


def _account_label(typ: str) -> str:
    t = typ.lower()
    if "google" in t:
        return "Google-Konto"
    if "whatsapp" in t:
        return "WhatsApp"
    if "telegram" in t:
        return "Telegram"
    if "facebook" in t:
        return "Facebook"
    if "microsoft" in t or "outlook" in t:
        return "Microsoft"
    return typ


# ====================================================================== #
#  3 · Anrufliste
# ====================================================================== #
def call_log(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Anrufliste", ui.CYAN)
    rows = _query(adb, "content://call_log/calls",
                  projection="number:name:date:duration:type", sort="date DESC")
    if not rows:
        ui.warn("Keine Anrufliste lesbar (Berechtigung/leer). Mit Root: DB direkt ziehen.")
        if st.get("is_root"):
            _root_sqlite(adb, "/data/data/com.android.providers.contacts/databases/calllog.db",
                         "SELECT number,date,duration,type FROM calls ORDER BY date DESC LIMIT 200;", "anrufe_root.txt")
        if not _auto:
            ui.pause()
        return
    types = {"1": "⬇ eingehend", "2": "⬆ ausgehend", "3": "✖ verpasst", "4": "Mailbox", "5": "abgelehnt", "6": "blockiert"}
    out = [f"{'DATUM/ZEIT':<20} {'TYP':<12} {'DAUER':>7}  NUMMER / NAME"]
    print(f"  {ui.BOLD}{out[0]}{ui.RESET}")
    for r in rows[:80]:
        dur = r.get("duration", "0")
        ds = f"{int(dur)//60}:{int(dur)%60:02d}" if dur.isdigit() else dur
        t = types.get(r.get("type", ""), r.get("type", ""))
        nm = (r.get("name", "") or "").strip()
        line = f"{_ts(r.get('date','')):<20} {t:<12} {ds:>7}  {r.get('number','')} {nm}"
        print("  " + line)
        out.append(line)
    # ---- Auswertung ----
    from collections import Counter
    by_type = Counter(types.get(r.get("type", ""), "?") for r in rows)
    total_dur = sum(int(r.get("duration", "0")) for r in rows if r.get("duration", "").isdigit())
    top = Counter((r.get("name") or r.get("number") or "?") for r in rows).most_common(15)
    out.append("\n=== AUSWERTUNG ===")
    out.append("Nach Typ: " + ", ".join(f"{k}={v}" for k, v in by_type.items()))
    out.append(f"Gesamte Gesprächszeit: {total_dur//3600}h {total_dur%3600//60}m {total_dur%60}s")
    out.append("Häufigste Kontakte (Anzahl Anrufe):")
    for who, n in top:
        out.append(f"  {n:>4}×  {who}")
    if not _auto:
        ui.kv("Anrufe nach Typ", ", ".join(f"{k}={v}" for k, v in by_type.items()))
        ui.kv("Gesprächszeit gesamt", f"{total_dur//3600}h {total_dur%3600//60}m")
        print(f"  {ui.BOLD}Top-Kontakte:{ui.RESET}")
        for who, n in top[:8]:
            print(f"    {ui.BCYAN}{n:>4}×{ui.RESET}  {who}")
    p = _write("anrufliste.txt", "\n".join(out) + f"\n\n# {len(rows)} Einträge gesamt")
    ui.ok(f"{len(rows)} Anrufe → {p}")
    if not _auto:
        ui.pause()


# ====================================================================== #
#  4 · SMS / MMS
# ====================================================================== #
def sms(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("SMS / MMS", ui.CYAN)
    rows = _query(adb, "content://sms", projection="address:date:type:body", sort="date DESC")
    if not rows:
        ui.warn("SMS nicht über Provider lesbar.")
        if st.get("is_root"):
            _root_sqlite(adb, "/data/data/com.android.providers.telephony/databases/mmssms.db",
                         "SELECT address,date,type,body FROM sms ORDER BY date DESC LIMIT 200;", "sms_root.txt")
        if not _auto:
            ui.pause()
        return
    out = [f"{'DATUM/ZEIT':<20} {'R':<4} ABSENDER  ::  TEXT"]
    for r in rows[:80]:
        dirn = "⬇" if r.get("type") == "1" else "⬆"
        body = (r.get("body", "") or "").replace("\n", " ")[:60]
        line = f"{_ts(r.get('date','')):<20} {dirn:<4} {r.get('address',''):<16} :: {body}"
        print("  " + line)
        out.append(line)
    # ---- MMS-Zähler + Konversations-Statistik ----
    from collections import Counter
    mms = _query(adb, "content://mms", projection="date:m_type") or []
    inc = sum(1 for r in rows if r.get("type") == "1")
    snt = sum(1 for r in rows if r.get("type") == "2")
    by_addr = Counter(r.get("address", "?") for r in rows).most_common(15)
    out.append("\n=== AUSWERTUNG ===")
    out.append(f"Empfangen: {inc}   Gesendet: {snt}   MMS: {len(mms)}")
    out.append("Häufigste Konversationen (Anzahl SMS):")
    for who, n in by_addr:
        out.append(f"  {n:>4}×  {who}")
    if not _auto:
        ui.kv("Empfangen / Gesendet / MMS", f"{inc} / {snt} / {len(mms)}")
        print(f"  {ui.BOLD}Top-Konversationen:{ui.RESET}")
        for who, n in by_addr[:8]:
            print(f"    {ui.BCYAN}{n:>4}×{ui.RESET}  {who}")
    p = _write("sms.txt", "\n".join(out) + f"\n\n# {len(rows)} SMS gesamt")
    ui.ok(f"{len(rows)} Nachrichten (+{len(mms)} MMS) → {p}")
    if not _auto:
        ui.pause()


# ====================================================================== #
#  5 · Kontakte
# ====================================================================== #
def contacts(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Kontakte", ui.CYAN)
    rows = _query(adb, "content://com.android.contacts/data/phones",
                  projection="display_name:data1")
    if not rows:  # Fallback-URIs (Hersteller-/Android-Versionen unterscheiden sich)
        for uri, proj in [
            ("content://contacts/phones", "name:number"),
            ("content://com.android.contacts/raw_contacts", "display_name"),
            ("content://icc/adn", "name:number"),  # SIM-Telefonbuch
        ]:
            rows = _query(adb, uri, projection=proj)
            if rows:
                for r in rows:  # Felder vereinheitlichen
                    r["display_name"] = r.get("display_name") or r.get("name", "")
                    r["data1"] = r.get("data1") or r.get("number", "")
                break
    if not rows:
        ui.warn("Kontakte nicht lesbar (Provider gesperrt – mit Root: contacts2.db ziehen).")
        if not _auto:
            ui.pause()
        return
    out = ["=== TELEFONNUMMERN ==="]
    for r in rows[:200]:
        out.append(f"{r.get('display_name',''):<30} {r.get('data1','')}")
    print("  " + "\n  ".join(out[1:31]))
    # E-Mail-Adressen der Kontakte (separate Provider-Tabelle)
    emails = _query(adb, "content://com.android.contacts/data/emails",
                    projection="display_name:data1")
    if emails:
        out.append("\n=== E-MAIL-ADRESSEN ===")
        for r in emails[:200]:
            out.append(f"{r.get('display_name',''):<30} {r.get('data1','')}")
        if not _auto:
            ui.kv("E-Mail-Kontakte", len(emails))
    p = _write("kontakte.txt", "\n".join(out) + f"\n\n# {len(rows)} Nummern, {len(emails)} E-Mails")
    ui.ok(f"{len(rows)} Kontakte (+{len(emails)} E-Mails) → {p}")
    if not _auto:
        ui.pause()


# ====================================================================== #
#  6 · Browser-Verläufe
# ====================================================================== #
BROWSERS = {
    "com.android.chrome": "app_chrome/Default/History",
    "com.chrome.beta": "app_chrome/Default/History",
    "org.mozilla.firefox": "files/places.sqlite",
    "com.brave.browser": "app_chrome/Default/History",
    "com.opera.browser": "app_opera/History",
    "com.microsoft.emmx": "app_chrome/Default/History",
    "com.sec.android.app.sbrowser": "app_sbrowser/Default/History",
    "com.duckduckgo.mobile.android": "databases/history.db",
}


def browser_history(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Browser-Verläufe", ui.CYAN)
    installed = [b for b in BROWSERS if b in adb.shell(f"pm list packages {shq(b)}")]
    if not installed:
        installed = [b for b in BROWSERS if adb.shell(f"pm path {shq(b)}").strip()]
    if installed:
        ui.info("Installierte Browser: " + ", ".join(installed))
    if not st.get("is_root"):
        ui.warn("Browser-Verläufe liegen in der App-Sandbox → nur mit Root direkt lesbar.")
        ui.info("Ohne Root: Verlauf nur über die App selbst exportierbar, oder via "
                "Google-Konto (myactivity.google.com) bei aktivierter Synchronisation.")
        if not _auto:
            ui.pause()
        return
    allout = []
    for pkg in installed:
        sub = BROWSERS[pkg]
        path = f"/data/data/{pkg}/{sub}"
        ui.info(f"Lese {pkg} …")
        if "places.sqlite" in sub:
            q = ("SELECT datetime(last_visit_date/1000000+strftime('%s','2000-01-01 00:00:00'),'unixepoch','localtime'),"
                 "url FROM moz_places ORDER BY last_visit_date DESC LIMIT 100;")
        else:
            q = ("SELECT datetime(last_visit_time/1000000-11644473600,'unixepoch','localtime'),url,title "
                 "FROM urls ORDER BY last_visit_time DESC LIMIT 100;")
        res = adb.shell(f"sqlite3 {shq(path)} \"{q}\" 2>/dev/null", root=True)
        if not res.strip():
            # DB ist evtl. gelockt → Kopie ziehen
            adb.shell(f"cp {shq(path)} /sdcard/_h.db 2>/dev/null", root=True)
            res = adb.shell(f"sqlite3 /sdcard/_h.db \"{q}\" 2>/dev/null")
            adb.shell("rm /sdcard/_h.db 2>/dev/null")
        if res.strip():
            allout.append(f"\n===== {pkg} =====\n{res}")
            for l in res.splitlines()[:15]:
                print(f"   {ui.GREY}{l[:115]}{ui.RESET}")
    if allout:
        p = _write("browser_verlauf.txt", "\n".join(allout))
        ui.ok(f"Verläufe → {p}")
    else:
        ui.warn("Keine Verlaufs-DB lesbar.")
    if not _auto:
        ui.pause()


# ====================================================================== #
#  7 · Social-Media & Messenger
# ====================================================================== #
SOCIAL = {
    "com.whatsapp": "WhatsApp", "com.whatsapp.w4b": "WhatsApp Business",
    "org.telegram.messenger": "Telegram", "com.instagram.android": "Instagram",
    "com.facebook.katana": "Facebook", "com.facebook.orca": "Messenger",
    "com.snapchat.android": "Snapchat", "com.zhiliaoapp.musically": "TikTok",
    "com.twitter.android": "X/Twitter", "com.discord": "Discord",
    "com.google.android.youtube": "YouTube", "com.reddit.frontpage": "Reddit",
    "com.tinder": "Tinder", "com.bumble.app": "Bumble", "com.signal.android": "Signal",
    "com.viber.voip": "Viber", "kik.android": "Kik", "com.skype.raider": "Skype",
    "com.linkedin.android": "LinkedIn", "com.pinterest": "Pinterest",
}


def social_media(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Social-Media & Messenger", ui.CYAN)
    installed = []
    pkgall = adb.shell("pm list packages")
    for pkg, name in SOCIAL.items():
        if f"package:{pkg}" in pkgall:
            installed.append((pkg, name))
    if not installed:
        ui.warn("Keine bekannten Social-/Messenger-Apps gefunden.")
        if not _auto:
            ui.pause()
        return
    out = [f"=== Gefundene Social/Messenger-Apps ({len(installed)}) ==="]
    for pkg, name in installed:
        info = adb.shell(f"dumpsys package {shq(pkg)}", timeout=20)
        fm = re.search(r"firstInstallTime=([\d:\- ]+)", info)
        lm = re.search(r"lastUpdateTime=([\d:\- ]+)", info)
        first = fm.group(1).strip() if fm else ""
        last = lm.group(1).strip() if lm else ""
        print(f"  {ui.BGREEN}●{ui.RESET} {name:<18} {ui.GREY}{pkg}{ui.RESET}")
        print(f"      installiert: {first or '—'}   aktualisiert: {last or '—'}")
        out.append(f"{name:<18} {pkg}\n    installiert={first}  aktualisiert={last}")
        # Medienordner (Bilder/Voicenotes) – ohne Root sichtbar in /sdcard
        for media in _social_media_dirs(adb, pkg, name):
            print(f"      {ui.CYAN}↳ {media}{ui.RESET}")
            out.append(f"    media: {media}")
    if st.get("is_root"):
        ui.info("Root: App-Datenbanken (Chats) liegen unter /data/data/<pkg>/databases/ – mit sqlite3 lesbar.")
        out.append("\nRoot-Hinweis: /data/data/<pkg>/databases/ (z.B. WhatsApp msgstore.db)")
    p = _write("social_media.txt", "\n".join(out))
    ui.ok(f"Übersicht → {p}")
    if not _auto:
        ui.pause()


def _social_media_dirs(adb: ADB, pkg: str, name: str) -> list[str]:
    paths = []
    candidates = {
        "com.whatsapp": ["/sdcard/Android/media/com.whatsapp/WhatsApp/Media"],
        "org.telegram.messenger": ["/sdcard/Android/media/org.telegram.messenger/Telegram",
                                    "/sdcard/Telegram"],
        "com.instagram.android": ["/sdcard/Pictures/Instagram", "/sdcard/DCIM/Instagram"],
        "com.snapchat.android": ["/sdcard/Pictures/Snapchat", "/sdcard/DCIM/Snapchat"],
    }
    for c in candidates.get(pkg, [f"/sdcard/Pictures/{name}", f"/sdcard/DCIM/{name}"]):
        cnt = adb.shell(f"find {shq(c)} -type f 2>/dev/null | wc -l").strip()
        if cnt.isdigit() and int(cnt) > 0:
            paths.append(f"{c}  ({cnt} Dateien)")
    return paths


# ====================================================================== #
#  8 · Medien-Inventar
# ====================================================================== #
def media_inventory(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Medien-Inventar (mit Zeitstempeln)", ui.CYAN)
    sections = [
        ("BILDER", "content://media/external/images/media", "_display_name:date_added:date_modified:_size:_data"),
        ("VIDEOS", "content://media/external/video/media", "_display_name:date_added:date_modified:_size:_data:duration"),
        ("AUDIO", "content://media/external/audio/media", "_display_name:date_added:_size:_data"),
    ]
    total = 0
    allout = []
    for label, uri, proj in sections:
        rows = _query(adb, uri, projection=proj, sort="date_added DESC")
        ui.kv(f"{label} gesamt", len(rows))
        total += len(rows)
        allout.append(f"\n===== {label} ({len(rows)}) =====")
        allout.append(f"{'AUFNAHME/HINZUGEFÜGT':<20} {'GRÖSSE':>9}  PFAD")
        for r in rows:
            t = _ts(r.get("date_added", ""))
            size = r.get("_size", "")
            sz = f"{int(size)//1024} KB" if size.isdigit() else size
            allout.append(f"{t:<20} {sz:>9}  {r.get('_data', r.get('_display_name',''))}")
        # erste paar live zeigen
        for r in rows[:8]:
            print(f"   {ui.GREY}{_ts(r.get('date_added','')):<20}{ui.RESET} {r.get('_data', r.get('_display_name',''))}")
    # Versteckte Medien (.nomedia / versteckte Ordner)
    hidden = adb.shell("find /sdcard -name '.nomedia' 2>/dev/null | head -n 30")
    hidden_dirs = adb.shell("find /sdcard -type d -name '.*' 2>/dev/null | head -n 30")
    if hidden.strip() or hidden_dirs.strip():
        ui.warn("Versteckte Medienordner (.nomedia / .versteckt) gefunden:")
        for l in (hidden + "\n" + hidden_dirs).splitlines()[:15]:
            if l.strip():
                print(f"   {ui.BYELLOW}• {l}{ui.RESET}")
        allout.append("\n===== VERSTECKTE ORDNER =====\n" + hidden + "\n" + hidden_dirs)
    p = _write("medien_inventar.txt", "\n".join(allout))
    ui.ok(f"{total} Medien indexiert → {p}")
    ui.info("Tatsächliche Dateien herunterladen: Hauptmenü → 5 (Datei-Transfer) → adb pull.")
    if not _auto:
        ui.pause()


# ====================================================================== #
#  9 · Sprachnachrichten / Aufnahmen
# ====================================================================== #
def voice_messages(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Sprachnachrichten & Anrufaufnahmen", ui.CYAN)
    spots = [
        "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Voice Notes",
        "/sdcard/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Audio",
        "/sdcard/Android/media/org.telegram.messenger/Telegram/Telegram Audio",
        "/sdcard/Recordings", "/sdcard/Record", "/sdcard/CallRecordings",
        "/sdcard/MIUI/sound_recorder", "/sdcard/Sounds", "/sdcard/Music/Recordings",
        "/sdcard/Android/data/com.google.android.dialer/files",
    ]
    out = []
    found_any = False
    for s in spots:
        listing = adb.shell(f"find {shq(s)} -type f 2>/dev/null | head -n 200")
        files = [l for l in listing.splitlines() if l.strip()]
        if files:
            found_any = True
            ui.warn(f"{len(files)} Datei(en) in {s}:")
            out.append(f"\n===== {s} ({len(files)}) =====")
            for fp in files:
                meta = adb.shell(f"stat -c '%y %s' {shq(fp)} 2>/dev/null").strip()
                print(f"   {ui.GREY}{meta[:19]}{ui.RESET}  {os.path.basename(fp)}")
                out.append(f"{meta}  {fp}")
    if not found_any:
        ui.info("Keine typischen Sprachnachrichten-/Aufnahme-Ordner gefunden.")
    else:
        p = _write("sprachnachrichten.txt", "\n".join(out))
        ui.ok(f"Liste → {p}")
    if not _auto:
        ui.pause()


# ====================================================================== #
#  10 · Play-Store-Historie
# ====================================================================== #
def playstore_history(adb: ADB, dev, st, _auto=False) -> None:
    if not _auto:
        ui.clear(); ui.rule("Play-Store- & Installations-Historie", ui.CYAN)
    pkgs = [l.split(":", 1)[1] for l in adb.shell("pm list packages -3").splitlines() if ":" in l]
    ui.info(f"Analysiere Install-/Update-Zeiten von {len(pkgs)} Apps …")
    rows = []
    for p in pkgs:
        info = adb.shell(f"dumpsys package {shq(p)} | grep -E 'firstInstallTime|lastUpdateTime|installerPackageName'")
        first = re.search(r"firstInstallTime=([\d-]+ [\d:]+)", info)
        last = re.search(r"lastUpdateTime=([\d-]+ [\d:]+)", info)
        inst = re.search(r"installerPackageName=(\S+)", info)
        rows.append((first.group(1) if first else "—", last.group(1) if last else "—",
                     inst.group(1) if inst else "—", p))
    rows.sort(reverse=True)
    out = [f"{'ERSTINSTALLATION':<20} {'LETZTES UPDATE':<20} {'QUELLE':<28} PAKET"]
    print(f"  {ui.BOLD}{out[0]}{ui.RESET}")
    for first, last, inst, p in rows[:40]:
        print(f"  {first:<20} {last:<20} {inst[:26]:<28} {p}")
        out.append(f"{first:<20} {last:<20} {inst:<28} {p}")
    # Install/Uninstall-Events aus dem Event-Log
    events = adb.shell("logcat -d -b events | grep -iE 'pm_|package' | tail -n 40")
    if events.strip():
        out.append("\n===== EVENT-LOG (Install/Remove/Update) =====\n" + events)
    ui.info("Reinstall-Zähler (wie oft gelöscht+neu installiert) wird vom Gerät NICHT lokal gespeichert.")
    ui.info("Diese Historie liegt serverseitig im Google-Konto: play.google.com/library bzw. "
            "myactivity.google.com → 'Play Store'.")
    if st.get("is_root"):
        ui.info("Root: lokale Vending-DB /data/data/com.android.vending/databases/ kann Teil-Historie enthalten.")
    p = _write("playstore_historie.txt", "\n".join(out))
    ui.ok(f"Install-Historie → {p}")
    if not _auto:
        ui.pause()


# ====================================================================== #
#  11 · Wiederherstellbarkeit
# ====================================================================== #
def recovery_assessment(adb: ADB, dev, st, _auto=False) -> None:
    ui.clear(); ui.rule("Wiederherstellbarkeit gelöschter Daten", ui.CYAN)
    crypto = adb.getprop("ro.crypto.state")
    typ = adb.getprop("ro.crypto.type")
    ui.kv("Verschlüsselung", f"{crypto} / {typ}")
    ui.kv("Root", "ja" if st.get("is_root") else "nein")
    print()
    ui.rule("Einschätzung", ui.YELLOW)
    if not st.get("is_root"):
        ui.err("Ohne Root: KEIN Raw-Zugriff auf die Datenpartition → echtes Datei-Carving unmöglich.")
        ui.info("Realistisch ohne Root wiederherstellbar:")
        print("   • In den Papierkorb verschobene Medien (Galerie/Google Fotos – 30/60 Tage)")
        print("   • Cloud-synchronisierte Daten (Google Fotos, Drive, Konto-Aktivität)")
        print("   • Noch nicht überschriebene Dateien in /sdcard (selten, via Provider-Index)")
    else:
        ui.ok("Root vorhanden – tiefere Optionen:")
        print("   • SQLite-DBs enthalten oft 'deleted'-Flags statt echter Löschung (Recovery möglich)")
        print("   • WAL-/journal-Dateien neben DBs enthalten ungespeicherte/gelöschte Datensätze")
        print("   • Thumbnails (.thumbnails) überleben Löschung des Originals oft")
        ui.info("Thumbnail-Cache nach gelöschten Bildern durchsuchen?")
        if ui.confirm("Jetzt .thumbnails & WAL-Reste scannen?", False):
            th = adb.shell("find /sdcard/DCIM/.thumbnails -type f 2>/dev/null | wc -l")
            ui.kv("Thumbnail-Dateien", th.strip())
            wal = adb.shell("find /data/data -name '*.db-wal' 2>/dev/null | head -n 20", root=True)
            ui.pager(wal or "—", "WAL-Dateien (mögliche gelöschte Datensätze)")
    print()
    ui.danger("Wichtig: FBE-Verschlüsselung macht klassisches Carving auf modernen Geräten "
              "weitgehend wirkungslos. Profi-Forensik (Cellebrite/Magnet) nutzt Exploits/Chip-Off.")
    ui.pause()


# ====================================================================== #
#  12 · Userdata-Backup
# ====================================================================== #
def pull_userdata(adb: ADB, dev, st, _auto=False) -> None:
    ui.clear(); ui.rule("Datenpartition sichern", ui.CYAN)
    ui.info("Sichert die zugänglichen Nutzerdaten für Offline-Analyse am PC.")
    dst = os.path.join(_mkout(), f"sdcard_{int(time.time())}")
    if ui.confirm(f"Komplettes /sdcard nach {dst} ziehen? (kann groß sein)", False):
        os.makedirs(dst, exist_ok=True)
        ui.info("Lade /sdcard … (Abbruch mit STRG+C)")
        rc, o, e = adb.raw(["pull", "/sdcard", dst], timeout=3600)
        ui.ok(f"Gesichert in {dst}") if rc == 0 else ui.err((e or o)[:200])
    if st.get("is_root"):
        ui.info("Root: ganze /data-Partition als Image:  dd if=/dev/block/by-name/userdata of=/sdcard/userdata.img "
                "(sehr groß; danach pullen).")
    ui.pause()


# ====================================================================== #
#  Helfer
# ====================================================================== #
def _root_sqlite(adb: ADB, dbpath: str, query: str, outname: str) -> None:
    ui.info(f"Root: lese {dbpath} …")
    res = adb.shell(f"sqlite3 {shq(dbpath)} \"{query}\" 2>/dev/null", root=True)
    if not res.strip():
        adb.shell(f"cp {shq(dbpath)} /sdcard/_f.db 2>/dev/null", root=True)
        res = adb.shell(f"sqlite3 /sdcard/_f.db \"{query}\" 2>/dev/null")
        adb.shell("rm /sdcard/_f.db 2>/dev/null")
    if res.strip():
        ui.pager(res, dbpath)
        _write(outname, res, show=False)   # bereits oben im Pager gezeigt
        ui.ok(f"Gespeichert: {os.path.join(OUT, outname)}")
    else:
        ui.warn("DB leer oder nicht lesbar.")
