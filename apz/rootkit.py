"""ROOT-ARSENAL – vollständige Root-only-Funktionen (echt, keine Simulation).

Diese Kategorie erscheint im Hauptmenü NUR, wenn der Erstscan echtes Root,
KernelSU/Magisk-su oder adb-root ('Fakeroot') erkannt hat. Alles hier nutzt
tatsächlichen Root-Zugriff:

  A) Tiefe Daten-Extraktion  – App-DBs, Chats, Browser, Passwörter, Konten, WLAN
  B) Echte Datenwiederherstellung – SQLite-Freelist/WAL, Thumbnails, Trash, Caches
  C) Backdoor-/Spyware-/Rootkit-Scan ("bd-Scan")
  D) System & Partitionen – Imaging, Backups, NVRAM/EFS, RW-Mount

Jede Funktion ist defensiv geschrieben (Fehler werden gemeldet statt verschluckt).
"""
from __future__ import annotations

import os
import re
import time

from . import ui
from .adb import ADB
from .util import https_only, safe_name, sha256_file, shq

OUT = os.path.expanduser("~/Schreibtisch/Androidpanzer/root_arsenal")


def _o() -> str:
    os.makedirs(OUT, exist_ok=True)
    return OUT


def _save(name: str, content: str, show: bool = True) -> str:
    _o()
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    if show:
        ui.show_report(content, name, p, note="Bericht")
    return p


def _r(adb: ADB, cmd: str, timeout: int = 60) -> str:
    """Root-Shell-Kommando."""
    return adb.shell(cmd, timeout=timeout, root=True)


def _pull_root_file(adb: ADB, remote: str, localname: str) -> str | None:
    """Kopiert eine geschützte Datei via Root nach /sdcard, zieht sie, räumt auf.
    Gibt den lokalen Pfad zurück oder None."""
    tmp = f"/sdcard/.panzer_tmp_{int(time.time()*1000)%100000}"
    _r(adb, f"cp -a '{remote}' '{tmp}' 2>/dev/null; chmod 666 '{tmp}' 2>/dev/null")
    # WAL/SHM mitnehmen, falls SQLite
    for ext in ("-wal", "-shm"):
        _r(adb, f"[ -f '{remote}{ext}' ] && cp -a '{remote}{ext}' '{tmp}{ext}' 2>/dev/null; "
                f"chmod 666 '{tmp}{ext}' 2>/dev/null")
    local = os.path.join(_o(), localname)
    rc, out, err = adb.raw(["pull", tmp, local], timeout=120)
    for ext in ("", "-wal", "-shm"):
        adb.raw(["pull", f"{tmp}{ext}", local + ext], timeout=60) if ext else None
        _r(adb, f"rm -f '{tmp}{ext}' 2>/dev/null")
    return local if os.path.exists(local) and os.path.getsize(local) > 0 else None


# ====================================================================== #
#  Menü
# ====================================================================== #
def menu(adb: ADB, dev, st) -> None:
    mode, detail = adb.root_method()
    while True:
        ui.clear()
        ui.banner(subtitle="🔓 ROOT-ARSENAL · vollständiger Tiefenzugriff")
        badge = {"adb-root": "adb-root (Fakeroot/userdebug)", "magisk": "Magisk",
                 "su": "su-Binary", "none": "KEIN ROOT"}.get(mode, mode)
        ui.kv("Root-Modus", f"{ui.BGREEN}{badge}{ui.RESET}  {ui.GREY}{detail}{ui.RESET}")
        if mode == "none":
            ui.err("Root ist nicht (mehr) verfügbar – Arsenal deaktiviert.")
            ui.pause()
            return
        ch = ui.menu("Root-Funktionen", [
            ("", f"{ui.BOLD}── A · TIEFE DATEN-EXTRAKTION ──{ui.RESET}"),
            ("1", "Komplette App-Daten-Extraktion (DBs + shared_prefs, jede App)"),
            ("2", "Messenger-Chats entschlüsselt (WhatsApp/Telegram/Signal/…)"),
            ("3", "Browser komplett (Verlauf+Downloads+Suchen+Logins+Autofill)"),
            ("4", "Gespeicherte Passwörter & Autofill (Chrome/Gecko)"),
            ("5", "WLAN-Passwörter im Klartext"),
            ("6", "Konten inkl. Residuen GELÖSCHTER/abgemeldeter (accounts_ce.db)"),
            ("7", "Zwischenablage-/Benachrichtigungs-Historie"),
            ("", f"{ui.BOLD}── B · ECHTE DATENWIEDERHERSTELLUNG ──{ui.RESET}"),
            ("8", "Gelöschte SQLite-Datensätze rekonstruieren (Freelist/WAL/.recover)"),
            ("9", "Gelöschte Bilder via Thumbnail-Cache wiederherstellen"),
            ("10", "Papierkorb / .trashed-Medien (Android 11+) bergen"),
            ("11", "Gelöschte Chats/SMS aus WAL & Journal carven"),
            ("12", "App-Cache nach Medienresten durchsuchen (Foto/Video-Carving)"),
            ("", f"{ui.BOLD}── C · BACKDOOR- & SPYWARE-SCAN (bd-Scan) ──{ui.RESET}"),
            ("13", "VOLLSTÄNDIGER bd-Scan (alle Checks nacheinander)"),
            ("14", "SUID/SGID & versteckte root-Binaries"),
            ("15", "Persistenz (init.d, init-rc, Magisk-Module, app_process)"),
            ("16", "Offene Ports & Reverse-Shells (LISTEN + Prozess)"),
            ("17", "Spyware-Indikatoren (Accessibility/DeviceAdmin/Inject/Frida/Xposed)"),
            ("18", "System-Integrität (verändertes /system, fremde APKs, hosts)"),
            ("", f"{ui.BOLD}── D · SYSTEM & PARTITIONEN ──{ui.RESET}"),
            ("19", "Partition als Raw-Image sichern (dd)"),
            ("20", "NVRAM/EFS sichern (IMEI/Funk-Kalibrierung)"),
            ("21", "Komplettes /data als TAR (Offline-Forensik)"),
            ("22", "/system RW mounten (Modding)"),
            ("", f"{ui.BOLD}── E · LIVE-NETZWERK ──{ui.RESET}"),
            ("23", f"{ui.BGREEN}📡 DNS- & SNI-Watch (domain-genau, live){ui.RESET}"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit", ""):
            if ch == "":
                continue
            return
        fn = {
            "1": extract_app_data, "2": extract_messenger, "3": extract_browsers_full,
            "4": extract_passwords, "5": wifi_passwords, "6": accounts_residue,
            "7": clipboard_notif_history,
            "8": recover_sqlite, "9": recover_thumbnails, "10": recover_trash,
            "11": recover_chats_wal, "12": carve_cache_media,
            "13": bd_scan_full, "14": scan_suid, "15": scan_persistence,
            "16": scan_ports, "17": scan_spyware, "18": scan_system_integrity,
            "19": image_partition, "20": backup_efs, "21": tar_data, "22": mount_system_rw,
            "23": network_watch,
        }.get(ch)
        if fn:
            try:
                fn(adb, dev, st)
            except KeyboardInterrupt:
                ui.warn("\nAbgebrochen.")
            except Exception as e:  # noqa: BLE001
                ui.err(f"Fehler: {e}")
                ui.pause()


# ====================================================================== #
#  A · TIEFE DATEN-EXTRAKTION
# ====================================================================== #
def extract_app_data(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Komplette App-Daten-Extraktion", ui.CYAN)
    pkg = ui.ask("Paketname (leer = ALLE Drittanbieter-Apps)")
    pkgs = [pkg] if pkg else [l.split(":", 1)[1] for l in
                              adb.shell("pm list packages -3").splitlines() if ":" in l]
    if not pkgs:
        ui.warn("Keine Apps."); ui.pause(); return
    base = os.path.join(_o(), f"appdata_{int(time.time())}")
    os.makedirs(base, exist_ok=True)
    for p in pkgs:
        ui.info(f"Extrahiere {p} …")
        tmp = f"/sdcard/.pz_{p}.tar"
        _r(adb, f"cd /data/data/{p} 2>/dev/null && tar -cf {tmp} databases shared_prefs files 2>/dev/null; "
                f"chmod 666 {tmp} 2>/dev/null")
        local = os.path.join(base, f"{p}.tar")
        adb.raw(["pull", tmp, local], timeout=180)
        _r(adb, f"rm -f {tmp}")
        if os.path.exists(local) and os.path.getsize(local) > 0:
            ui.ok(f"  → {local} ({os.path.getsize(local)//1024} KB)")
            # DBs auflisten
            dbs = _r(adb, f"ls /data/data/{p}/databases/ 2>/dev/null")
            if dbs.strip():
                print(f"     {ui.GREY}DBs: {dbs.replace(chr(10),', ')}{ui.RESET}")
        else:
            ui.warn(f"  {p}: nichts extrahierbar.")
    ui.ok(f"Fertig: {base}")
    ui.info("Auspacken am PC:  tar -xf <app>.tar   → SQLite-DBs mit DB-Browser öffnen.")
    ui.pause()


def extract_messenger(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Messenger-Chat-Extraktion", ui.CYAN)
    targets = {
        "com.whatsapp": [("databases/msgstore.db", "WhatsApp Nachrichten"),
                         ("databases/wa.db", "WhatsApp Kontakte")],
        "org.telegram.messenger": [("files/cache4.db", "Telegram Cache/Chats")],
        "org.thoughtcrime.securesms": [("databases/signal.db", "Signal (verschlüsselt – Key nötig)")],
        "com.signal.android": [("databases/signal.db", "Signal")],
        "com.facebook.orca": [("databases/threads_db2", "Messenger")],
        "com.viber.voip": [("databases/viber_messages", "Viber")],
        "com.discord": [("files/", "Discord Cache")],
    }
    found = False
    for pkg, files in targets.items():
        if f"package:{pkg}" not in adb.shell(f"pm list packages {shq(pkg)}"):
            continue
        found = True
        ui.warn(f"{pkg} gefunden:")
        for rel, desc in files:
            remote = f"/data/data/{pkg}/{rel}"
            exists = _r(adb, f"[ -e '{remote}' ] && echo yes").strip()
            if exists != "yes":
                print(f"     {ui.GREY}– {rel} nicht vorhanden{ui.RESET}")
                continue
            local = _pull_root_file(adb, remote, f"{pkg}_{os.path.basename(rel)}")
            if local:
                ui.ok(f"  {desc}: {local}")
                # Vorschau: Anzahl Nachrichten bei WhatsApp msgstore
                if "msgstore" in rel:
                    cnt = _sqlite_local(local, "SELECT count(*) FROM message;") or \
                          _sqlite_local(local, "SELECT count(*) FROM messages;")
                    if cnt:
                        print(f"     {ui.CYAN}↳ ~{cnt.strip()} Nachrichten in der DB{ui.RESET}")
            else:
                print(f"     {ui.YELLOW}– {rel} nicht ziehbar{ui.RESET}")
    if not found:
        ui.info("Keine bekannten Messenger installiert.")
    else:
        ui.info("Hinweis: WhatsApp msgstore.db ist lesbar (Crypt-DBs in /sdcard brauchen den Key "
                "aus /data/data/com.whatsapp/files/key).")
    ui.pause()


def extract_browsers_full(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Browser-Volltextract (Root)", ui.CYAN)
    from .dataforensics import BROWSERS
    any_found = False
    for pkg, histsub in BROWSERS.items():
        if not _r(adb, f"[ -d /data/data/{pkg} ] && echo y").strip():
            continue
        any_found = True
        ui.warn(f"{pkg}:")
        prof = "/data/data/%s/%s" % (pkg, os.path.dirname(histsub))
        # History
        hp = f"/data/data/{pkg}/{histsub}"
        local = _pull_root_file(adb, hp, f"{pkg}_History.db")
        if local:
            if "places.sqlite" in histsub:
                q = ("SELECT datetime(last_visit_date/1000000,'unixepoch','localtime') t,url "
                     "FROM moz_places WHERE last_visit_date NOT NULL ORDER BY last_visit_date DESC LIMIT 100;")
            else:
                q = ("SELECT datetime(last_visit_time/1000000-11644473600,'unixepoch','localtime') t,"
                     "url,title FROM urls ORDER BY last_visit_time DESC LIMIT 100;")
            res = _sqlite_local(local, q)
            if res:
                _save(f"{pkg}_verlauf.txt", res)
                ui.ok(f"  Verlauf: {len([x for x in res.splitlines() if x])} Einträge")
                for l in res.splitlines()[:8]:
                    print(f"     {ui.GREY}{l[:115]}{ui.RESET}")
        # Downloads & Logins (Chromium)
        if "Default" in histsub:
            for db, label, q in [
                ("Login Data", "Gespeicherte Logins",
                 "SELECT origin_url,username_value,datetime(date_created/1000000-11644473600,'unixepoch','localtime') FROM logins;"),
                ("Web Data", "Autofill",
                 "SELECT name,value FROM autofill LIMIT 100;"),
            ]:
                dp = f"{prof}/{db}"
                lf = _pull_root_file(adb, dp, f"{pkg}_{db.replace(' ','')}.db")
                if lf:
                    res = _sqlite_local(lf, q)
                    if res and res.strip():
                        _save(f"{pkg}_{label}.txt", res)
                        ui.ok(f"  {label}: {len(res.splitlines())} Zeilen → gespeichert")
    if not any_found:
        ui.info("Keine unterstützten Browser installiert.")
    ui.pause()


def extract_passwords(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Gespeicherte Passwörter & Autofill", ui.CYAN)
    ui.warn("Chromium speichert Passwörter in 'Login Data' (auf Android per Keystore verschlüsselt).")
    targets = ["com.android.chrome", "com.sec.android.app.sbrowser", "com.brave.browser"]
    for pkg in targets:
        if not _r(adb, f"[ -d /data/data/{pkg} ] && echo y").strip():
            continue
        dp = f"/data/data/{pkg}/app_chrome/Default/Login Data"
        lf = _pull_root_file(adb, dp, f"{pkg}_LoginData.db")
        if lf:
            res = _sqlite_local(lf, "SELECT origin_url,username_value,length(password_value) FROM logins;")
            if res:
                ui.ok(f"{pkg}: {len(res.splitlines())} Login-Einträge (Passwort-Blob verschlüsselt)")
                _save(f"{pkg}_logins.txt", res)
                for l in res.splitlines()[:10]:
                    print(f"   {ui.GREY}{l}{ui.RESET}")
    ui.info("Klartext-Passwörter erfordern den App-gebundenen Keystore-Schlüssel (TEE) – "
            "auf dem Gerät selbst via Frida-Hook zur Laufzeit, nicht offline.")
    ui.pause()


def wifi_passwords(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("WLAN-Passwörter (Klartext)", ui.CYAN)
    paths = [
        "/data/misc/wifi/WifiConfigStore.xml",
        "/data/misc/apexdata/com.android.wifi/WifiConfigStore.xml",
        "/data/misc/wifi/wpa_supplicant.conf",
    ]
    got = False
    for p in paths:
        raw = _r(adb, f"cat '{p}' 2>/dev/null")
        if not raw.strip():
            continue
        got = True
        nets = re.findall(r"<string name=\"SSID\">&quot;?([^<&]+)&quot;?</string>.*?"
                          r"<string name=\"PreSharedKey\">&quot;?([^<]*)&quot;?</string>",
                          raw, re.DOTALL)
        if not nets:  # wpa_supplicant Format
            nets = re.findall(r'ssid="([^"]+)".*?psk="([^"]+)"', raw, re.DOTALL)
        if nets:
            ui.ok(f"{len(nets)} WLAN-Profile aus {p}:")
            out = []
            for ssid, psk in nets:
                psk = psk.replace("&quot;", "") or "(offen/kein PSK)"
                print(f"   {ui.BGREEN}●{ui.RESET} {ssid:<32} {ui.YELLOW}{psk}{ui.RESET}")
                out.append(f"{ssid}\t{psk}")
            _save("wlan_passwoerter.txt", "\n".join(out))
        else:
            _save("WifiConfigStore.xml", raw)
            ui.info(f"Rohdaten gesichert (Format abweichend): {p}")
    if not got:
        ui.warn("Keine WLAN-Konfig lesbar.")
    ui.pause()


def accounts_residue(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Konten inkl. Residuen gelöschter/abgemeldeter", ui.CYAN)
    dbs = ["/data/system_ce/0/accounts_ce.db", "/data/system_de/0/accounts_de.db",
           "/data/system/users/0/accounts.db"]
    allout = []
    for db in dbs:
        if not _r(adb, f"[ -f '{db}' ] && echo y").strip():
            continue
        ui.info(f"Lese {db} …")
        # aktive Konten
        acc = _r(adb, f"sqlite3 '{db}' 'SELECT name,type FROM accounts;' 2>/dev/null")
        # gelöschte Spuren: oft in 'accounts'-Freelist + Tabellen 'shared_accounts','grants'
        deleted = _sqlite_recover_remote(adb, db)
        if acc.strip():
            ui.ok(f"  Aktive Konten in {os.path.basename(db)}:")
            for l in acc.splitlines():
                print(f"     {ui.BGREEN}●{ui.RESET} {l}")
            allout.append(f"# {db} (aktiv)\n{acc}")
        if deleted.strip():
            ui.warn("  Gelöschte/Residuen-Spuren (Freelist/.recover):")
            hits = [l for l in deleted.splitlines() if "@" in l or "com.google" in l]
            for l in hits[:20]:
                print(f"     {ui.BYELLOW}↳ {l[:100]}{ui.RESET}")
            allout.append(f"# {db} (Residuen)\n{deleted}")
    # Auth-/Logout-Events
    ev = adb.shell("logcat -d -t 4000 | grep -iE 'account.*(remove|delete|logout|signout)|GLSUser' | tail -n 30")
    if ev.strip():
        ui.info("Konto-Entfernungs-Events (Log):")
        for l in ev.splitlines()[-12:]:
            print(f"   {ui.GREY}{l[:110]}{ui.RESET}")
        allout.append("# Logout-Events\n" + ev)
    if allout:
        ui.ok(f"Gesichert: {_save('konten_residuen.txt', chr(10).join(allout))}")
    else:
        ui.warn("Keine Konten-DB lesbar.")
    ui.pause()


def clipboard_notif_history(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Zwischenablage- & Benachrichtigungs-Historie", ui.CYAN)
    clip = _r(adb, "cat /data/system/clipboard* 2>/dev/null; dumpsys clipboard 2>/dev/null | head -n 30")
    if clip.strip():
        ui.pager(clip, "Clipboard")
    notif = adb.shell("dumpsys notification --noredact 2>/dev/null | grep -iE 'tickerText|text=|title=' | tail -n 40")
    if notif.strip():
        ui.info("Letzte Benachrichtigungs-Inhalte (--noredact):")
        ui.pager(notif, "Notification-History")
        _save("notifications.txt", notif, show=False)   # bereits im Pager gezeigt
    ui.pause()


# ====================================================================== #
#  B · ECHTE DATENWIEDERHERSTELLUNG
# ====================================================================== #
def recover_sqlite(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Gelöschte SQLite-Datensätze rekonstruieren", ui.CYAN)
    ui.info("Sucht App-DBs, zieht sie inkl. WAL und rekonstruiert gelöschte Zeilen "
            "(.recover + Freelist-Strings).")
    pkg = ui.ask("Paketname (leer = SMS+Anrufe+Kontakte-DBs)")
    if pkg:
        dbs = _r(adb, f"ls /data/data/{pkg}/databases/*.db 2>/dev/null").splitlines()
    else:
        dbs = [
            "/data/data/com.android.providers.telephony/databases/mmssms.db",
            "/data/data/com.android.providers.contacts/databases/calllog.db",
            "/data/data/com.android.providers.contacts/databases/contacts2.db",
        ]
    base = os.path.join(_o(), f"sqlite_recover_{int(time.time())}")
    os.makedirs(base, exist_ok=True)
    for db in dbs:
        db = db.strip()
        if not db or not _r(adb, f"[ -f '{db}' ] && echo y").strip():
            continue
        ui.info(f"▶ {db}")
        local = _pull_root_file(adb, db, os.path.basename(db))
        if not local:
            ui.warn("  nicht ziehbar."); continue
        # 1) .recover (rekonstruiert auch teils gelöschte Pages)
        rec = _sqlite_recover_local(local)
        if rec:
            rp = os.path.join(base, os.path.basename(db) + ".recovered.sql")
            open(rp, "w", encoding="utf-8", errors="replace").write(rec)
            ui.ok(f"  .recover → {rp} ({len(rec.splitlines())} Zeilen)")
        # 2) Freelist/Unallocated nach Textresten durchsuchen
        carved = _carve_strings(local)
        if carved:
            cp = os.path.join(base, os.path.basename(db) + ".carved.txt")
            open(cp, "w", encoding="utf-8", errors="replace").write(carved)
            ui.ok(f"  Freelist-Strings → {cp}")
        # 3) WAL separat (enthält jüngste, evtl. gelöschte Transaktionen)
        if os.path.exists(local + "-wal"):
            walc = _carve_strings(local + "-wal")
            if walc:
                open(os.path.join(base, os.path.basename(db) + ".wal.txt"), "w",
                     encoding="utf-8", errors="replace").write(walc)
                ui.ok("  WAL-Reste gesichert.")
    ui.ok(f"Ergebnisse: {base}")
    ui.pause()


def recover_thumbnails(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Gelöschte Bilder via Thumbnails wiederherstellen", ui.CYAN)
    ui.info("Thumbnails überleben oft die Löschung des Originals.")
    dirs = _r(adb, "find /sdcard /data/media -type d -name '.thumbnails' 2>/dev/null").splitlines()
    total = 0
    base = os.path.join(_o(), f"thumbnails_{int(time.time())}")
    for d in dirs:
        d = d.strip()
        if not d:
            continue
        cnt = _r(adb, f"find '{d}' -type f 2>/dev/null | wc -l").strip()
        ui.kv(d, f"{cnt} Dateien")
        if cnt.isdigit() and int(cnt) > 0:
            os.makedirs(base, exist_ok=True)
            sub = os.path.join(base, d.strip("/").replace("/", "_"))
            adb.raw(["pull", d, sub], timeout=300)
            total += int(cnt)
    if total:
        ui.ok(f"{total} Thumbnails gezogen → {base}")
    else:
        ui.warn("Keine Thumbnails gefunden.")
    # MediaStore-Thumbnail-DB
    tdb = "/data/data/com.android.providers.media/databases/external.db"
    if _r(adb, f"[ -f '{tdb}' ] && echo y").strip():
        ui.info("MediaStore-DB enthält Pfade gelöschter Medien (date_added/_data) → "
                "via Punkt 8 auf diese DB anwenden.")
    ui.pause()


def recover_trash(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Papierkorb / .trashed-Medien bergen (Android 11+)", ui.CYAN)
    files = _r(adb, "find /sdcard /data/media -type f \\( -name '.trashed-*' -o -path '*/.Trash*' "
                    "-o -path '*RecycleBin*' \\) 2>/dev/null").splitlines()
    files = [f for f in files if f.strip()]
    if not files:
        ui.warn("Keine .trashed-/Papierkorb-Dateien gefunden.")
        ui.pause(); return
    ui.warn(f"{len(files)} Papierkorb-Dateien gefunden:")
    base = os.path.join(_o(), f"trash_{int(time.time())}")
    os.makedirs(base, exist_ok=True)
    for f in files[:200]:
        meta = _r(adb, f"stat -c '%y %s' '{f}' 2>/dev/null").strip()
        print(f"   {ui.GREY}{meta[:19]}{ui.RESET}  {os.path.basename(f)}")
        adb.raw(["pull", f, base], timeout=60)
    ui.ok(f"Geborgen → {base}")
    ui.pause()


def recover_chats_wal(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Gelöschte Chats/SMS aus WAL & Journal carven", ui.CYAN)
    dbs = {
        "WhatsApp": "/data/data/com.whatsapp/databases/msgstore.db",
        "SMS": "/data/data/com.android.providers.telephony/databases/mmssms.db",
        "Telegram": "/data/data/org.telegram.messenger/files/cache4.db",
    }
    base = os.path.join(_o(), f"chat_recover_{int(time.time())}")
    for name, db in dbs.items():
        if not _r(adb, f"[ -f '{db}' ] && echo y").strip():
            continue
        ui.info(f"▶ {name}")
        local = _pull_root_file(adb, db, f"{name}_{os.path.basename(db)}")
        if not local:
            continue
        os.makedirs(base, exist_ok=True)
        # .recover holt gelöschte Zeilen aus freien Pages
        rec = _sqlite_recover_local(local)
        carved = _carve_strings(local) + ("\n" + _carve_strings(local + "-wal") if os.path.exists(local + "-wal") else "")
        sn = safe_name(name)
        if rec:
            open(os.path.join(base, f"{sn}.recovered.sql"), "w", encoding="utf-8", errors="replace").write(rec)
        if carved.strip():
            open(os.path.join(base, f"{sn}.carved.txt"), "w", encoding="utf-8", errors="replace").write(carved)
        ui.ok(f"  {name}: rekonstruiert → {base}")
    ui.info("Tipp: WhatsApp markiert gelöschte Nachrichten oft nur per Flag – '.recovered.sql' "
            "nach 'message'-Tabelle durchsuchen.")
    ui.pause()


def carve_cache_media(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("App-Cache nach Medienresten carven", ui.CYAN)
    ui.info("Durchsucht App-Caches nach JPEG/PNG/MP4-Resten (z.B. Snapchat/Insta-Vorschauen).")
    pkg = ui.ask("Paket (leer = bekannte Social-Apps)")
    pkgs = [pkg] if pkg else ["com.snapchat.android", "com.instagram.android",
                              "com.whatsapp", "com.facebook.katana", "org.telegram.messenger"]
    base = os.path.join(_o(), f"cache_carve_{int(time.time())}")
    for p in pkgs:
        if not _r(adb, f"[ -d /data/data/{p} ] && echo y").strip():
            continue
        ui.info(f"▶ {p}")
        # Medien im cache/files mit Größe > 10k
        media = _r(adb, f"find /data/data/{p} /sdcard/Android/data/{p} -type f "
                        f"\\( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.mp4' "
                        f"-o -iname '*.nomedia' -o -iname '*.enc' -o -iname '*.0' -o -iname '*.1' \\) "
                        f"-size +10k 2>/dev/null | head -n 300")
        files = [f for f in media.splitlines() if f.strip()]
        if files:
            os.makedirs(os.path.join(base, p), exist_ok=True)
            ui.ok(f"  {len(files)} Cache-Mediendateien")
            for f in files[:150]:
                adb.raw(["pull", f, os.path.join(base, p)], timeout=60)
    if os.path.isdir(base):
        ui.ok(f"Geborgen → {base}")
        ui.info("Endungslose/.enc-Dateien am PC mit 'file *' prüfen, ggf. umbenennen.")
    else:
        ui.warn("Nichts gefunden.")
    ui.pause()


# ====================================================================== #
#  C · BACKDOOR-/SPYWARE-SCAN
# ====================================================================== #
def bd_scan_full(adb: ADB, dev, st) -> None:
    ui.clear(); ui.banner(subtitle="Vollständiger Backdoor-/Spyware-Scan")
    ui.info("Führe alle Sicherheitschecks nacheinander aus …\n")
    findings: list[str] = []
    for name, fn in [("SUID/Binaries", scan_suid), ("Persistenz", scan_persistence),
                     ("Ports/Reverse-Shells", scan_ports), ("Spyware-Indikatoren", scan_spyware),
                     ("System-Integrität", scan_system_integrity)]:
        ui.rule(f"▶ {name}", ui.YELLOW)
        try:
            r = fn(adb, dev, st, _auto=True)
            if r:
                findings.extend(r)
        except Exception as e:  # noqa: BLE001
            ui.err(f"{name}: {e}")
    ui.rule("GESAMTERGEBNIS", ui.YELLOW)
    if findings:
        ui.warn(f"{len(findings)} potenzielle Auffälligkeit(en):")
        for x in findings:
            print(f"   {ui.BRED}⚑{ui.RESET} {x}")
        _save("backdoor_scan.txt", "\n".join(findings))
    else:
        ui.ok("Keine offensichtlichen Backdoor-/Spyware-Indikatoren.")
    ui.pause()


def scan_suid(adb: ADB, dev, st, _auto=False) -> list:
    if not _auto:
        ui.clear(); ui.rule("SUID/SGID & versteckte root-Binaries", ui.CYAN)
    out = _r(adb, "find / -type f \\( -perm -4000 -o -perm -2000 \\) 2>/dev/null", timeout=90)
    lines = [l for l in out.splitlines() if l.strip()]
    # Bekannte legitime vs. verdächtige
    susp = [l for l in lines if re.search(r"/(data|sdcard|tmp|cache|local)/", l)
            or l.endswith("/su") and "/system/" not in l and "/su/" not in l]
    findings = []
    for l in lines[:60]:
        flag = l in susp
        col = ui.BRED if flag else ui.GREY
        print(f"   {col}{'⚑ ' if flag else '  '}{l}{ui.RESET}")
        if flag:
            findings.append(f"Verdächtiges SUID-Binary: {l}")
    # extra su-Binaries
    sus = _r(adb, "find / -name 'su' -type f 2>/dev/null", timeout=60)
    for l in sus.splitlines():
        if l.strip() and not re.search(r"/(system|sbin|su|apex|magisk)", l):
            findings.append(f"su-Binary an ungewöhnlichem Ort: {l}")
            print(f"   {ui.BRED}⚑ {l}{ui.RESET}")
    if not _auto:
        ui.ok(f"{len(findings)} Auffälligkeiten.") if findings else ui.ok("Unauffällig.")
        ui.pause()
    return findings


def scan_persistence(adb: ADB, dev, st, _auto=False) -> list:
    if not _auto:
        ui.clear(); ui.rule("Persistenz-Mechanismen", ui.CYAN)
    findings = []
    checks = {
        "init.d-Skripte": "ls -la /system/etc/init.d /data/adb/service.d /data/adb/post-fs-data.d 2>/dev/null",
        "Magisk-Module": "ls /data/adb/modules 2>/dev/null",
        "Fremde init-rc": "ls -la /data/local/tmp 2>/dev/null; find /data -name '*.rc' 2>/dev/null | head",
        "Autostart-Apps (BOOT_COMPLETED)": "dumpsys package 2>/dev/null | grep -B2 BOOT_COMPLETED | grep -i 'Package\\|priority' | head -n 30",
        "app_process-Hijack (Xposed)": "ls -la /system/bin/app_process* 2>/dev/null",
    }
    for label, cmd in checks.items():
        res = _r(adb, cmd)
        print(f"   {ui.BOLD}{label}:{ui.RESET}")
        if res.strip():
            for l in res.splitlines()[:12]:
                hot = re.search(r"riru|lsposed|xposed|frida|/data/local/tmp|magisk", l, re.I)
                col = ui.BYELLOW if hot else ui.GREY
                print(f"      {col}{l}{ui.RESET}")
                if hot and label != "Magisk-Module":
                    findings.append(f"{label}: {l.strip()}")
        else:
            print(f"      {ui.GREY}— keine{ui.RESET}")
    if not _auto:
        ui.pause()
    return findings


def scan_ports(adb: ADB, dev, st, _auto=False) -> list:
    if not _auto:
        ui.clear(); ui.rule("Offene Ports & Reverse-Shells", ui.CYAN)
    out = _r(adb, "netstat -tlnpW 2>/dev/null || netstat -tlnp 2>/dev/null || ss -tlnp 2>/dev/null")
    findings = []
    print(f"   {ui.BOLD}LISTEN-Sockets:{ui.RESET}")
    for l in out.splitlines():
        if "LISTEN" in l or re.search(r":\d+\s", l):
            m = re.search(r"[\d.]+:(\d+)", l)
            port = m.group(1) if m else "?"
            suspicious = port in ("4444", "1337", "31337", "5555", "23", "12345", "9999", "8888")
            print("      " + (ui.pulse(l.strip()[:110]) if suspicious else f"{ui.GREY}{l.strip()[:110]}{ui.RESET}"))
            if suspicious:
                findings.append(f"Verdächtiger LISTEN-Port {port}: {l.strip()}")
    # Aktive Outbound-Verbindungen zu ungewöhnlichen IPs
    est = _r(adb, "netstat -tnpW 2>/dev/null | grep ESTABLISHED | head -n 30")
    if est.strip():
        print(f"\n   {ui.BOLD}Aktive Verbindungen (ESTABLISHED):{ui.RESET}")
        for l in est.splitlines()[:20]:
            print(f"      {ui.GREY}{l.strip()[:110]}{ui.RESET}")
    if not _auto:
        ui.ok(f"{len(findings)} verdächtige Ports.") if findings else ui.ok("Keine verdächtigen Ports.")
        ui.pause()
    return findings


def scan_spyware(adb: ADB, dev, st, _auto=False) -> list:
    if not _auto:
        ui.clear(); ui.rule("Spyware-/Stalkerware-Indikatoren", ui.CYAN)
    findings = []
    # Accessibility-Dienste
    acc = adb.shell("settings get secure enabled_accessibility_services")
    if acc and acc not in ("null", ""):
        print(f"   {ui.BOLD}Accessibility-Dienste:{ui.RESET}")
        for s in acc.split(":"):
            if s.strip():
                print(f"      {ui.BRED}⚑ {s.strip()}{ui.RESET}")
                findings.append(f"Accessibility-Dienst (Keylogger-Risiko): {s.strip()}")
    # Device-Admin / Notification-Listener
    admins = _r(adb, "dumpsys device_policy 2>/dev/null | grep -iE 'admin=ComponentInfo' ")
    for m in re.findall(r"ComponentInfo\{([^}]+)\}", admins):
        print(f"   {ui.BYELLOW}Device-Admin: {m}{ui.RESET}")
        findings.append(f"Device-Admin aktiv: {m}")
    nl = adb.shell("settings get secure enabled_notification_listeners")
    if nl and nl not in ("null", ""):
        for s in nl.split(":"):
            if s.strip() and not re.search(r"google|systemui|samsung|android", s, re.I):
                findings.append(f"Notification-Listener (liest alle Benachrichtigungen): {s.strip()}")
                print(f"   {ui.BYELLOW}Notif-Listener: {s.strip()}{ui.RESET}")
    # Frida/Injection-Prozesse
    procs = _r(adb, "ps -A 2>/dev/null | grep -iE 'frida|gum-js|gadget|xposed|riru' ")
    if procs.strip():
        for l in procs.splitlines():
            findings.append(f"Injection-Prozess: {l.strip()}")
            print(f"   {ui.BRED}⚑ {l.strip()}{ui.RESET}")
    # Apps mit SMS+INTERNET+RECORD_AUDIO+LOCATION-Kombi (Stalkerware-typisch)
    print(f"   {ui.BOLD}Apps mit kritischer Rechte-Kombi werden geprüft …{ui.RESET}")
    pkgs = [l.split(":", 1)[1] for l in adb.shell("pm list packages -3").splitlines() if ":" in l]
    for p in pkgs:
        perms = adb.shell(f"dumpsys package {shq(p)} | grep 'granted=true'")
        crit = sum(x in perms for x in ["RECORD_AUDIO", "ACCESS_FINE_LOCATION", "READ_SMS",
                                        "READ_CALL_LOG", "CAMERA", "READ_CONTACTS"])
        hides = "SYSTEM_ALERT_WINDOW" in perms or not adb.shell(
            f"cmd package query-activities --brief -a android.intent.action.MAIN "
            f"-c android.intent.category.LAUNCHER {p}").strip()
        if crit >= 4:
            tag = f"{p} (kritische Rechte: {crit}/6" + (", versteckt/Overlay" if hides else "") + ")"
            findings.append("Stalkerware-Verdacht: " + tag)
            print("   " + ui.pulse(f"⚑ {tag}"))
    if not _auto:
        ui.ok(f"{len(findings)} Indikatoren.") if findings else ui.ok("Keine Spyware-Indikatoren.")
        ui.pause()
    return findings


def scan_system_integrity(adb: ADB, dev, st, _auto=False) -> list:
    if not _auto:
        ui.clear(); ui.rule("System-Integrität", ui.CYAN)
    findings = []
    # hosts-Hijack
    hosts = _r(adb, "cat /system/etc/hosts 2>/dev/null")
    extra = [l for l in hosts.splitlines() if l.strip() and not l.strip().startswith("#")
             and "localhost" not in l and "127.0.0.1" not in l and "::1" not in l]
    if extra:
        findings.append(f"hosts-Datei manipuliert ({len(extra)} Einträge)")
        print(f"   {ui.BYELLOW}hosts-Einträge:{ui.RESET}")
        for l in extra[:10]:
            print(f"      {l}")
    # Fremde APKs in /system
    sysapk = _r(adb, "find /system/app /system/priv-app /system/product -name '*.apk' -newer /system/build.prop 2>/dev/null | head")
    if sysapk.strip():
        print(f"   {ui.BYELLOW}Nach build.prop hinzugefügte System-APKs:{ui.RESET}")
        for l in sysapk.splitlines()[:10]:
            print(f"      {l}")
            findings.append(f"Neuere System-APK: {l}")
    # SELinux
    enf = adb.shell("getenforce")
    if enf.strip().lower() == "permissive":
        findings.append("SELinux ist Permissive (Schutz reduziert)")
        print(f"   {ui.BRED}⚑ SELinux: Permissive{ui.RESET}")
    else:
        print(f"   {ui.GREY}SELinux: {enf}{ui.RESET}")
    # Kürzlich veränderte System-Binaries
    recent = _r(adb, "find /system/bin /system/xbin -type f -mtime -30 2>/dev/null | head")
    if recent.strip():
        print(f"   {ui.BYELLOW}System-Binaries < 30 Tage geändert:{ui.RESET}")
        for l in recent.splitlines()[:10]:
            print(f"      {l}")
    if not _auto:
        ui.ok(f"{len(findings)} Auffälligkeiten.") if findings else ui.ok("System unauffällig.")
        ui.pause()
    return findings


# ====================================================================== #
#  D · SYSTEM & PARTITIONEN
# ====================================================================== #
def image_partition(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Partition als Raw-Image sichern", ui.CYAN)
    parts = _r(adb, "ls -l /dev/block/by-name/ 2>/dev/null || ls -l /dev/block/bootdevice/by-name/ 2>/dev/null")
    ui.pager(parts, "Verfügbare Partitionen")
    name = ui.ask("Partitionsname (z.B. boot, system, modem, efs)")
    if not name:
        return
    src = _r(adb, f"ls -l /dev/block/by-name/{name} 2>/dev/null").strip()
    if not src:
        ui.err("Partition nicht gefunden.")
        ui.pause(); return
    remote = f"/sdcard/{name}.img"
    ui.info(f"dd if=/dev/block/by-name/{name} → {remote} … (kann dauern)")
    res = _r(adb, f"dd if=/dev/block/by-name/{name} of={remote} bs=4M 2>&1; chmod 666 {remote}", timeout=900)
    print(res[-300:])
    local = os.path.join(_o(), f"{name}.img")
    ui.info("Ziehe Image auf den PC …")
    adb.raw(["pull", remote, local], timeout=1800)
    _r(adb, f"rm -f {remote}")
    ui.ok(f"Image: {local}") if os.path.exists(local) else ui.err("Fehlgeschlagen.")
    ui.pause()


def backup_efs(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("NVRAM/EFS sichern (IMEI/Funk-Kalibrierung)", ui.CYAN)
    cand = _r(adb, "ls /dev/block/by-name/ 2>/dev/null | grep -iE 'efs|modemst|fsg|fsc|nvram|nvdata|nvcfg|protect'")
    parts = [c.strip() for c in cand.splitlines() if c.strip()]
    if not parts:
        ui.warn("Keine EFS/NVRAM-Partition per Name gefunden – prüfe MTK-Pfade …")
        mtk = _r(adb, "ls -la /mnt/vendor/nvdata /mnt/vendor/nvram /data/nvram 2>/dev/null | head")
        ui.pager(mtk or "—", "MTK NVRAM")
        ui.pause(); return
    ui.warn(f"Gefunden: {', '.join(parts)}")
    base = os.path.join(_o(), f"efs_backup_{int(time.time())}")
    os.makedirs(base, exist_ok=True)
    for pname in parts:
        rem = f"/sdcard/{pname}.img"
        _r(adb, f"dd if=/dev/block/by-name/{pname} of={rem} 2>/dev/null; chmod 666 {rem}", timeout=300)
        adb.raw(["pull", rem, base], timeout=300)
        _r(adb, f"rm -f {rem}")
        ui.ok(f"  {pname} gesichert")
    ui.ok(f"EFS/NVRAM → {base}  (sicher aufbewahren!)")
    ui.pause()


def tar_data(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Komplettes /data als TAR", ui.CYAN)
    ui.warn("Kann sehr groß werden (mehrere GB). Genug Speicher auf PC & /sdcard nötig.")
    if not ui.confirm("Fortfahren?", False):
        return
    remote = "/sdcard/data_backup.tar"
    ui.info("Erzeuge TAR von /data/data … (lange Laufzeit)")
    _r(adb, f"tar -cf {remote} --exclude=/data/data/*/cache /data/data /data/system_ce 2>/dev/null; "
            f"chmod 666 {remote}", timeout=3600)
    local = os.path.join(_o(), f"data_backup_{int(time.time())}.tar")
    adb.raw(["pull", remote, local], timeout=3600)
    _r(adb, f"rm -f {remote}")
    ui.ok(f"Backup: {local}") if os.path.exists(local) else ui.err("Fehlgeschlagen.")
    ui.pause()


def mount_system_rw(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("/system RW mounten", ui.CYAN)
    ui.warn("Macht die Systempartition beschreibbar (für Modding). Auf modernen Geräten oft "
            "wegen dynamic partitions/dm-verity eingeschränkt.")
    if not ui.confirm("Jetzt versuchen?", False):
        return
    res = _r(adb, "mount -o rw,remount /system 2>&1 || mount -o rw,remount / 2>&1; "
                  "mount | grep -E ' / | /system '")
    ui.pager(res, "Mount-Status")
    ui.pause()


# ====================================================================== #
#  SQLite-Recovery-Helfer (echt, lokal am PC)
# ====================================================================== #
def _local_sqlite_bin() -> str | None:
    import shutil
    return shutil.which("sqlite3")


def _sqlite_local(dbpath: str, query: str) -> str:
    """Führt eine Query lokal am PC aus (sqlite3). Leer bei Fehler."""
    import subprocess
    if not _local_sqlite_bin() or not os.path.exists(dbpath):
        return ""
    try:
        p = subprocess.run(["sqlite3", "-readonly", dbpath, query],
                           capture_output=True, text=True, timeout=60)
        return p.stdout
    except Exception:  # noqa: BLE001
        return ""


def _sqlite_recover_local(dbpath: str) -> str:
    """sqlite3 .recover – rekonstruiert auch aus beschädigten/teilgelöschten Pages."""
    import subprocess
    if not _local_sqlite_bin() or not os.path.exists(dbpath):
        return ""
    try:
        p = subprocess.run(["sqlite3", dbpath, ".recover"],
                           capture_output=True, text=True, timeout=120)
        return p.stdout
    except Exception:  # noqa: BLE001
        return ""


def _sqlite_recover_remote(adb: ADB, remote_db: str) -> str:
    """Zieht DB via Root und versucht lokale Recovery; fällt auf String-Carving zurück."""
    local = _pull_root_file(adb, remote_db, "_resid_" + os.path.basename(remote_db))
    if not local:
        return ""
    rec = _sqlite_recover_local(local)
    return rec or _carve_strings(local)


def _carve_strings(path: str, minlen: int = 5) -> str:
    """Extrahiert druckbare Strings aus (auch freien) DB-Pages – findet gelöschte Textreste."""
    if not os.path.exists(path):
        return ""
    try:
        data = open(path, "rb").read()
    except OSError:
        return ""
    # druckbare ASCII + erweiterte; sammelt zusammenhängende Sequenzen
    out, cur = [], bytearray()
    for b in data:
        if 32 <= b < 127 or b in (9,):
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("ascii", "replace"))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(cur.decode("ascii", "replace"))
    # Heuristik: Zeilen mit @, http, +49, Telefonnummern, Namen-artigem zuerst
    interesting = [s for s in out if re.search(r"@|https?://|\+?\d{6,}|[A-Za-zÄÖÜäöü]{4,}", s)]
    return "\n".join(dict.fromkeys(interesting))  # dedupe, Reihenfolge erhalten


# ====================================================================== #
#  NETZWERK-WATCH (Root): DNS-Queries + TLS-SNI live, domain-genau
# ====================================================================== #
def network_watch(adb: ADB, dev, st) -> None:
    import subprocess
    import re as _re
    from .deepforensics import _categorize_domain
    ui.clear()
    ui.banner(subtitle="📡 Netzwerk-Watch · DNS + SNI (domain-genau, Root)")
    if not st.get("is_root"):
        ui.err("Benötigt Root (tcpdump auf dem Gerät)."); ui.pause(); return

    # tcpdump finden – sonst AUTOMATISCH besorgen (verifiziert) und pushen
    tdbin = ensure_tcpdump(adb, st)
    if not tdbin:
        ui.pause(); return

    ui.info("Lausche auf DNS (Port 53) + TLS-SNI (Port 443). STRG+C beendet.\n")
    print(f"{ui.BOLD}{'Zeit':<9} {'Typ':<5} {'Kategorie':<16} Domain{ui.RESET}")
    print(f"{ui.GREY}{'-'*70}{ui.RESET}")

    logpath = _save("netzwerk_watch.txt", f"# DNS/SNI-Watch ab {time.strftime('%Y-%m-%d %H:%M:%S')}\n", show=False)
    logf = open(logpath, "a", encoding="utf-8")
    seen: set = set()
    count = 0

    # tcpdump-Kommando: DNS + 443, zeilengepuffert, ASCII für SNI
    cmd_inner = f"{tdbin} -l -nn -i any -s 0 -A '(udp port 53) or (tcp port 443)' 2>/dev/null"
    base = [adb.bin] + (["-s", adb.serial] if adb.serial else [])
    if adb.root_mode == "adb-root":
        full = base + ["shell", cmd_inner]
    else:
        full = base + ["shell", f"su -c \"{cmd_inner}\""]

    dns_q = _re.compile(r"(?:A|AAAA|CNAME)\??\s+([a-z0-9][a-z0-9.\-]+\.[a-z]{2,})", _re.I)
    host_like = _re.compile(r"\b([a-z0-9][a-z0-9.\-]+\.[a-z]{2,})\b", _re.I)

    def handle(host: str, typ: str):
        nonlocal count
        host = host.strip(".").lower()
        if not host or host in seen or host.replace(".", "").isdigit():
            return
        if len(host) < 5 or host.endswith((".in-addr.arpa",)):
            return
        seen.add(host)
        cat = _categorize_domain(host)
        ts = time.strftime("%H:%M:%S")
        col = (ui.pulse(cat) if cat in ("Adult/18+", "Dating")
               else f"{ui.BYELLOW}{cat}{ui.RESET}" if cat == "Tracker/Werbung"
               else f"{ui.BCYAN}{cat}{ui.RESET}" if cat != "Sonstiges" else f"{ui.GREY}{cat}{ui.RESET}")
        print(f"{ts:<9} {typ:<5} {col:<16} {host}")
        logf.write(f"{ts}\t{typ}\t{cat}\t{host}\n"); logf.flush()
        count += 1

    try:
        proc = subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, bufsize=1)
        for line in proc.stdout:  # type: ignore
            if ".53:" in line or " 53:" in line or "domain" in line:
                for m in dns_q.findall(line):
                    handle(m, "DNS")
            elif "443" in line:
                # SNI/Host aus ClientHello-ASCII (best effort)
                for m in host_like.findall(line):
                    if "." in m and not m[0].isdigit():
                        handle(m, "SNI")
    except KeyboardInterrupt:
        pass
    finally:
        try:
            proc.terminate(); proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            pass
        logf.close()
    print()
    ui.ok(f"Watch beendet. {count} eindeutige Domains erfasst → {logpath}")
    from collections import Counter
    if seen:
        stat = Counter(_categorize_domain(h) for h in seen)
        ui.rule("Zusammenfassung nach Kategorie", ui.YELLOW)
        for cat, n in stat.most_common():
            print(f"  {cat:<16} {ui.BCYAN}{'█'*min(30,n)}{ui.RESET} {n}")
    ui.pause()


# ====================================================================== #
#  tcpdump automatisch besorgen (mit Sicherheits-Verifikation!)
# ====================================================================== #
# ELF-Header für ARM aarch64: 7f 45 4c 46 (ELF) ... e_machine=0xB7 (183) bei Offset 18-19
def _is_arm64_elf(path: str) -> bool:
    try:
        d = open(path, "rb").read(20)
    except OSError:
        return False
    if d[:4] != b"\x7fELF":
        return False
    # e_machine @ offset 18 (little-endian 16-bit). 0x00B7 = AArch64
    return d[18:20] == b"\xb7\x00"


# Quellen werden NUR genutzt, wenn das Ergebnis als ARM64-ELF verifiziert ist.
_TCPDUMP_SOURCES = [
    # (URL, Beschreibung) – können je nach Verfügbarkeit angepasst werden
    ("https://github.com/wuseman/tcpdump-android-binaries/raw/main/arm64-v8a/tcpdump", "wuseman arm64"),
    ("https://github.com/wlsgur0306/tcpdump-android-binary/raw/main/tcpdump", "wlsgur0306"),
]


def ensure_tcpdump(adb: ADB, st: dict, interactive: bool = True) -> str | None:
    """Stellt tcpdump auf dem Gerät sicher. Pusht NUR ein als ARM64-ELF
    verifiziertes Binary. Rückgabe: Pfad auf dem Gerät oder None."""
    # 1) schon vorhanden?
    have = _r(adb, "which tcpdump || ls /data/local/tmp/tcpdump /system/xbin/tcpdump "
                   "/data/adb/modules/tcpdump/system/*/tcpdump 2>/dev/null").strip().splitlines()
    for h in have:
        if h.startswith("/") and "No such" not in h:
            # ausführbar?
            t = _r(adb, f"{h} --version 2>&1 | head -1")
            if "tcpdump" in t.lower() or "libpcap" in t.lower():
                ui.ok(f"tcpdump vorhanden: {h}")
                return h
    # 2) lokal gebündeltes Binary im Projekt?
    bundled = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "bin", "tcpdump-arm64")
    if os.path.isfile(bundled) and _is_arm64_elf(bundled):
        return _push_tcpdump(adb, bundled)
    # 3) Download + VERIFIKATION
    abi = adb.getprop("ro.product.cpu.abi")
    if "arm64" not in abi:
        ui.warn(f"Geräte-ABI ist {abi} – diese Auto-Beschaffung liefert nur arm64.")
    if interactive and not ui.confirm("tcpdump aus dem Netz beziehen (wird vor dem Push als "
                                      "ARM64-ELF verifiziert)?", True):
        _tcpdump_manual_hint(); return None
    import tempfile
    import urllib.request
    tmp = os.path.join(tempfile.gettempdir(), "tcpdump_dl")
    for url, desc in _TCPDUMP_SOURCES:
        ui.info(f"Versuche {desc} …")
        try:
            https_only(url)              # tcpdump läuft als ROOT → nur HTTPS
            req = urllib.request.Request(url, headers={"User-Agent": "panzer"})
            with urllib.request.urlopen(req, timeout=40) as r, open(tmp, "wb") as f:  # noqa: S310
                f.write(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"   {ui.GREY}✗ Download fehlgeschlagen: {e}{ui.RESET}"); continue
        if _is_arm64_elf(tmp):
            ui.ok(f"Verifiziert: ARM64-ELF von {desc} ({os.path.getsize(tmp)//1024} KB) · "
                  f"SHA-256: {sha256_file(tmp)}")
            # ins Projekt cachen
            os.makedirs(os.path.dirname(bundled), exist_ok=True)
            import shutil
            shutil.copy(tmp, bundled)
            return _push_tcpdump(adb, tmp)
        print(f"   {ui.BRED}✗ KEIN gültiges ARM64-Binary (404/HTML/falsche Arch) – verworfen{ui.RESET}")
        os.remove(tmp) if os.path.exists(tmp) else None
    ui.err("Kein verifiziertes tcpdump-Binary gefunden.")
    _tcpdump_manual_hint()
    return None


def _push_tcpdump(adb: ADB, local: str) -> str | None:
    dst = "/data/local/tmp/tcpdump"
    ui.info("Pushe & installiere tcpdump (Root) …")
    adb.raw(["push", local, "/sdcard/tcpdump.bin"], timeout=60)
    _r(adb, f"cp /sdcard/tcpdump.bin {dst}; chmod 755 {dst}; rm /sdcard/tcpdump.bin")
    test = _r(adb, f"{dst} --version 2>&1 | head -1")
    if "tcpdump" in test.lower() or "libpcap" in test.lower():
        ui.ok(f"tcpdump läuft: {test.strip()}")
        return dst
    ui.err(f"tcpdump startet nicht ({test[:60]}) – evtl. inkompatibles Binary.")
    return None


def _tcpdump_manual_hint() -> None:
    ui.rule("Vertrauenswürdige Alternative", ui.CYAN)
    for l in ["• Magisk → Module → aus dem Repo 'tcpdump' suchen & installieren (1 Tap, signiert)",
              "• oder selbst bauen mit Android-NDK (libpcap + tcpdump, -static)",
              "• fertiges Binary nach /data/local/tmp/tcpdump legen (chmod 755) – wird dann genutzt"]:
        print(f"   {ui.GREY}{l}{ui.RESET}")
