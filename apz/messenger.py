"""Messenger-Voll-Decrypt & Konversations-Renderer.

  • WhatsApp: msgstore.db (per Root Klartext) → komplette Chronologie als HTML-Timeline
              mit Kontakten, Zeitstempeln & verlinkten Medien.
              Zusätzlich .crypt14/15-Backup-Entschlüsselung mit dem key-File.
  • Telegram: cache4.db (best-effort Parsing).
  • Signal:   SQLCipher-DB – Key via Frida ziehen, dann entschlüsseln (geführt).

Primärweg ist die per Root gezogene Klartext-DB (zuverlässig). Backup-Decrypt &
Signal sind Zusatzwege. Fehlt etwas, sagt das Tool genau was.
"""
from __future__ import annotations

import os
import re
import subprocess
import time

from . import ui
from .adb import ADB
from .rootkit import _pull_root_file, _save
from .util import shq

OUT = os.path.expanduser("~/Schreibtisch/Androidpanzer/messenger")


def _o() -> str:
    os.makedirs(OUT, exist_ok=True)
    return OUT


def _sqlite(db: str, q: str) -> str:
    import shutil
    if not shutil.which("sqlite3") or not os.path.exists(db):
        return ""
    try:
        return subprocess.run(["sqlite3", "-readonly", "-separator", "\x1f", db, q],
                             capture_output=True, text=True, timeout=90).stdout
    except Exception:  # noqa: BLE001
        return ""


def menu(adb: ADB, dev, st) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="💬 Messenger-Decrypt & Timeline")
        if not st.get("is_root"):
            ui.warn("Ohne Root nur .crypt-Backup-Entschlüsselung möglich (key-File nötig).")
        ch = ui.menu("Messenger", [
            ("1", "WhatsApp → komplette HTML-Chat-Timeline (Root, Klartext-DB)"),
            ("2", "WhatsApp .crypt14/15-Backup entschlüsseln (key-File)"),
            ("3", "Telegram cache4.db auslesen"),
            ("4", "Signal entschlüsseln (Key via Frida, geführt)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        {"1": whatsapp_timeline, "2": whatsapp_decrypt_backup,
         "3": telegram_dump, "4": signal_decrypt}.get(ch, lambda *a: None)(adb, dev, st)


# ===================================================================== #
#  WhatsApp – Klartext-DB → HTML-Timeline
# ===================================================================== #
def whatsapp_timeline(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("WhatsApp – HTML-Chat-Timeline", ui.CYAN)
    if not st.get("is_root"):
        ui.err("Benötigt Root (Klartext-DB liegt in /data/data)."); ui.pause(); return
    msg = _pull_root_file(adb, "/data/data/com.whatsapp/databases/msgstore.db", "msgstore.db")
    wa = _pull_root_file(adb, "/data/data/com.whatsapp/databases/wa.db", "wa.db")
    if not msg:
        ui.err("msgstore.db nicht ziehbar."); ui.pause(); return

    # Kontaktnamen (wa.db) → JID-Map
    names = {}
    if wa:
        for line in _sqlite(wa, "SELECT jid, COALESCE(display_name,wa_name,'') FROM wa_contacts;").splitlines():
            parts = line.split("\x1f")
            if len(parts) == 2 and parts[1].strip():
                names[parts[0]] = parts[1]

    # Schema-tolerant: neue Schemas nutzen message + chat + jid; alte messages + key_remote_jid
    rows = _sqlite(msg,
        "SELECT j.raw_string, m.from_me, m.timestamp, m.text_data "
        "FROM message m JOIN chat c ON m.chat_row_id=c._id JOIN jid j ON c.jid_row_id=j._id "
        "WHERE m.text_data IS NOT NULL ORDER BY m.timestamp;")
    schema = "neu"
    if not rows.strip():
        rows = _sqlite(msg,
            "SELECT key_remote_jid, key_from_me, timestamp, data FROM messages "
            "WHERE data IS NOT NULL ORDER BY timestamp;")
        schema = "alt"
    if not rows.strip():
        ui.warn("Keine Nachrichten gefunden (Schema unbekannt). DB ist unter "
                f"{msg} gesichert – manuell mit DB-Browser öffnen.")
        ui.pause(); return

    # Parsen
    msgs = []
    for line in rows.splitlines():
        p = line.split("\x1f")
        if len(p) < 4:
            continue
        jid, from_me, ts, text = p[0], p[1], p[2], "\x1f".join(p[3:])
        try:
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ts) / 1000))
        except (ValueError, OSError):
            t = ts
        msgs.append((jid, from_me == "1", t, text))

    # nach Chat gruppieren
    chats: dict = {}
    for jid, fromme, t, text in msgs:
        chats.setdefault(jid, []).append((fromme, t, text))

    html = _render_whatsapp_html(chats, names)
    p = os.path.join(_o(), f"whatsapp_timeline_{int(time.time())}.html")
    open(p, "w", encoding="utf-8").write(html)
    ui.ok(f"{len(msgs)} Nachrichten in {len(chats)} Chats (Schema: {schema})")
    ui.ok(f"HTML-Timeline: {p}")
    ui.info("Im Browser öffnen:  xdg-open " + p)
    # kurze Konsolen-Vorschau
    for jid in list(chats)[:3]:
        nm = names.get(jid, jid)
        print(f"\n  {ui.BOLD}{nm}{ui.RESET} ({len(chats[jid])} Nachrichten)")
        for fromme, t, text in chats[jid][-4:]:
            who = "Ich" if fromme else nm.split("@")[0]
            print(f"    {ui.GREY}{t}{ui.RESET} {who}: {text[:60]}")
    ui.pause()


def _render_whatsapp_html(chats: dict, names: dict) -> str:
    css = """<style>
    body{background:#0b141a;color:#e9edef;font-family:system-ui,sans-serif;margin:0}
    h1{padding:16px;background:#202c33;margin:0}
    .chat{margin:18px;border:1px solid #222d34;border-radius:8px;overflow:hidden}
    .chat h2{background:#202c33;margin:0;padding:10px 14px;font-size:15px}
    .msgs{padding:10px;background:#0b141a;max-height:480px;overflow:auto}
    .b{max-width:70%;margin:4px 0;padding:6px 9px;border-radius:7px;font-size:14px}
    .me{background:#005c4b;margin-left:auto}.them{background:#202c33}
    .t{display:block;font-size:10px;color:#8696a0;margin-top:2px}
    </style>"""
    parts = [f"<html><head><meta charset='utf-8'>{css}</head><body>",
             f"<h1>🛡 WhatsApp-Timeline · {len(chats)} Chats</h1>"]
    for jid, msgs in sorted(chats.items(), key=lambda x: -len(x[1])):
        nm = names.get(jid, jid)
        parts.append(f"<div class='chat'><h2>{_esc(nm)} <small>({len(msgs)})</small></h2><div class='msgs'>")
        for fromme, t, text in msgs:
            cls = "me" if fromme else "them"
            parts.append(f"<div class='b {cls}'>{_esc(text)}<span class='t'>{t}</span></div>")
        parts.append("</div></div>")
    parts.append("</body></html>")
    return "".join(parts)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ===================================================================== #
#  WhatsApp – .crypt14/15 entschlüsseln
# ===================================================================== #
def whatsapp_decrypt_backup(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("WhatsApp .crypt14/15 entschlüsseln", ui.CYAN)
    import importlib.util
    if importlib.util.find_spec("cryptography") is None:
        ui.err("Python-Paket fehlt:  pip install cryptography"); ui.pause(); return

    # key-File holen
    keyf = None
    if st.get("is_root"):
        keyf = _pull_root_file(adb, "/data/data/com.whatsapp/files/key", "wa_key")
    if not keyf:
        kp = ui.ask("Pfad zum WhatsApp 'key'-File am PC (158 Bytes)")
        keyf = os.path.expanduser(kp) if kp and os.path.isfile(os.path.expanduser(kp)) else None
    if not keyf:
        ui.err("Kein key-File. (Liegt unter /data/data/com.whatsapp/files/key – Root.)"); ui.pause(); return

    # Backup-Datei holen
    candidates = adb.shell("ls -t /sdcard/Android/media/com.whatsapp/WhatsApp/Databases/msgstore*.crypt* "
                           "/sdcard/WhatsApp/Databases/msgstore*.crypt* 2>/dev/null").splitlines()
    candidates = [c for c in candidates if c.strip()]
    cryptf = None
    if candidates:
        ui.info("Gefundene Backups:")
        for i, c in enumerate(candidates[:10], 1):
            print(f"  {ui.CYAN}{i}{ui.RESET}  {c}")
        sel = ui.ask("Nr (oder leer für eigenen Pfad)", "1")
        if sel.isdigit() and 1 <= int(sel) <= len(candidates):
            remote = candidates[int(sel) - 1]
            local = os.path.join(_o(), os.path.basename(remote))
            adb.raw(["pull", remote, local], timeout=180)
            cryptf = local
    if not cryptf:
        cp = ui.ask("Pfad zur .crypt14/15-Datei am PC")
        cryptf = os.path.expanduser(cp) if cp and os.path.isfile(os.path.expanduser(cp)) else None
    if not cryptf:
        ui.err("Keine Backup-Datei."); ui.pause(); return

    out = os.path.join(_o(), "msgstore_decrypted.db")
    if _decrypt_crypt(keyf, cryptf, out):
        ui.ok(f"Entschlüsselt: {out}")
        cnt = _sqlite(out, "SELECT count(*) FROM message;") or _sqlite(out, "SELECT count(*) FROM messages;")
        if cnt.strip():
            ui.ok(f"~{cnt.strip()} Nachrichten – jetzt mit Option 1-Renderer / DB-Browser nutzbar.")
    else:
        ui.err("Entschlüsselung fehlgeschlagen (Format/Key prüfen).")
    ui.pause()


def _decrypt_crypt(keyfile: str, cryptfile: str, outfile: str) -> bool:
    """Entschlüsselt msgstore.db.crypt14/15. Basiert auf dem dokumentierten WA-Format."""
    import zlib

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        kf = open(keyfile, "rb").read()
        key = kf[126:158] if len(kf) >= 158 else kf[-32:]
        data = open(cryptfile, "rb").read()
        # crypt15: protobuf-Header variabler Länge; IV (16B) + Ciphertext folgen.
        # Heuristik: suche 16-Byte-IV-Offset. Für crypt14/15 liegt der Ciphertext
        # nach einem Header; gängige Implementierungen nutzen Offset über den
        # protobuf-Header. Wir versuchen mehrere bekannte Offsets.
        for hdr in (_crypt15_offset(data), 67, 51, 191):
            if hdr is None or hdr + 16 >= len(data):
                continue
            iv = data[hdr:hdr + 16]
            ct = data[hdr + 16:]
            try:
                pt = AESGCM(key).decrypt(iv, ct, None)
            except Exception:  # noqa: BLE001
                continue
            # SQLite-Magic prüfen (ggf. zlib-komprimiert)
            if pt[:15] == b"SQLite format 3":
                open(outfile, "wb").write(pt); return True
            try:
                dec = zlib.decompress(pt)
                if dec[:15] == b"SQLite format 3":
                    open(outfile, "wb").write(dec); return True
            except Exception:  # noqa: BLE001
                pass
        return False
    except Exception:  # noqa: BLE001
        return False


def _crypt15_offset(data: bytes):
    """Versucht, den Ciphertext-Offset aus dem protobuf-Header zu bestimmen."""
    # crypt15-Header beginnt oft mit einem length-delimited protobuf; das erste
    # Byte nach dem Header-Block ist 0x00..; gängiger Offset = Headerlänge.
    try:
        if data[0] == 0x00:
            # Header-Länge steht in den ersten Bytes (varint-artig) – grobe Schätzung
            return data[1] + 2
    except Exception:  # noqa: BLE001
        return None
    return None


# ===================================================================== #
#  Telegram
# ===================================================================== #
def telegram_dump(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Telegram cache4.db", ui.CYAN)
    if not st.get("is_root"):
        ui.err("Benötigt Root."); ui.pause(); return
    db = _pull_root_file(adb, "/data/data/org.telegram.messenger/files/cache4.db", "telegram_cache4.db")
    if not db:
        ui.err("cache4.db nicht ziehbar."); ui.pause(); return
    tables = _sqlite(db, "SELECT name FROM sqlite_master WHERE type='table';")
    ui.info("Tabellen: " + ", ".join(tables.split()))
    # Dialoge & Nachrichten (Telegram speichert Messages teils als Blob/TL-serialisiert)
    msgs = _sqlite(db, "SELECT mid, uid, date FROM messages_v2 ORDER BY date DESC LIMIT 200;") or \
           _sqlite(db, "SELECT mid, uid, date FROM messages ORDER BY date DESC LIMIT 200;")
    if msgs.strip():
        out = []
        for l in msgs.splitlines():
            p = l.split("\x1f")
            if len(p) >= 3:
                t = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(p[2]))) if p[2].isdigit() else p[2]
                out.append(f"{t}  uid={p[1]}  mid={p[0]}")
        path = _save("telegram_messages.txt", "\n".join(out))
        ui.ok(f"{len(out)} Nachrichten-Metadaten → {path}")
        ui.info("Telegram-Texte sind TL-serialisiert (Blob) – Volltext via Telegram-Export "
                "oder spezialisiertem Parser (z.B. telegram_media_downloader).")
    else:
        ui.warn("Keine Nachrichtentabelle erkannt – DB gesichert für manuelle Analyse: " + db)
    ui.pause()


# ===================================================================== #
#  Signal (SQLCipher) – Key via Frida
# ===================================================================== #
def signal_decrypt(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Signal entschlüsseln (SQLCipher)", ui.CYAN)
    ui.info("Signal nutzt SQLCipher; der Schlüssel liegt im Keystore/SharedPrefs.")
    pkg = "org.thoughtcrime.securesms"
    if f"package:{pkg}" not in adb.shell(f"pm list packages {shq(pkg)}"):
        pkg = "com.signal.android" if "com.signal.android" in adb.shell("pm list packages com.signal.android") else pkg
    if not st.get("is_root"):
        ui.err("Benötigt Root (DB + Prefs in /data/data)."); ui.pause(); return

    # 1) DB & Prefs ziehen
    db = _pull_root_file(adb, f"/data/data/{pkg}/databases/signal.db", "signal.db")
    prefs = adb.shell(f"cat /data/data/{shq(pkg)}/shared_prefs/*.xml 2>/dev/null", root=True)
    if prefs:
        _save("signal_prefs.xml", prefs)
    # 2) Key-Hinweis: ältere Signal-Versionen speichern 'pref_database_encrypted_secret'
    m = re.search(r'pref_database_encrypted_secret">([^<]+)<', prefs)
    if m:
        ui.warn("Verschlüsseltes DB-Secret in Prefs gefunden (mit Keystore-Schlüssel entschlüsselbar).")
    ui.info("Empfohlener Weg: Frida-Hook zur Laufzeit zieht den entschlüsselten 32-Byte-Key.")
    if ui.confirm("Jetzt Frida-Key-Hook gegen Signal starten?", False):
        from . import frida_engine
        if frida_engine.ensure_server(adb, st):
            js = frida_engine.SCRIPTS["keystore-dump"][1]
            frida_engine.run_script(adb, pkg, js, seconds=20, spawn=False)
            ui.info("Suche im Output nach einem 32-Byte-Key (SecretKeySpec).")
    if db:
        ui.info(f"DB gesichert: {db}")
        ui.info("Entschlüsseln am PC mit dem gefundenen Key:")
        print(f"   {ui.GREY}sqlcipher {db} \"PRAGMA key=\\\"x'<HEXKEY>'\\\"; .once out.db; "
              f".dump\"{ui.RESET}")
    ui.pause()
