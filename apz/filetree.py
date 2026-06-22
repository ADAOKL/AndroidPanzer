"""Komplette Ordnerstruktur-/Dateisystem-Analyse (read-only).

Läuft rekursiv über einen Speicherbereich des Geräts und zeigt:
  • den vollständigen Verzeichnisbaum (Dateizahl + Größe je Ordner),
  • Gesamtzahlen (Ordner/Dateien/Größe),
  • Dateityp-Verteilung (welche Endungen, wie viele),
  • größte Dateien, versteckte Dateien/Ordner, leere Ordner,
  • Top-Verzeichnisse nach Größe.

Anzeige im Terminal (Pager) + Speicherung als Bericht (in forensik/, damit der
Report-Export ihn mitnimmt). Ohne Root: /sdcard & lesbare Bereiche; mit Root
auch /data, /system usw.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
import re
import sqlite3
import tempfile
import time
import zipfile
from collections import Counter

from . import ui
from .dataforensics import _write
from .util import LOG, human_size, shq

# zuletzt gefundene verdächtige Objekte (für die Tiefen-Untersuchung)
_LAST_SUSPECTS: list = []

# Magic-Signaturen → echter Dateityp (zum Entlarven getarnter Dateien)
_MAGICS = [
    (b"\x7fELF", "ELF-Binary (ausführbar!)"),
    (b"dex\n", "DEX (Android-Bytecode!)"),
    (b"PK\x03\x04", "ZIP/APK/JAR/Office"),
    (b"\x89PNG\r\n", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"GIF8", "GIF"),
    (b"%PDF", "PDF"),
    (b"SQLite format 3\x00", "SQLite-Datenbank"),
    (b"\x1f\x8b", "GZIP"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip"),
    (b"Rar!", "RAR"),
    (b"ID3", "MP3"),
    (b"OggS", "OGG"),
    (b"\x00\x00\x00\x18ftyp", "MP4/MOV"),
    (b"#!", "Shell-Skript (ausführbar!)"),
    (b"<?xml", "XML"),
    (b"\xca\xfe\xba\xbe", "Java-Class / Mach-O"),
    (b"MZ", "Windows-EXE (auf Android ungewöhnlich!)"),
    (b"\x42\x5a\x68", "BZIP2"),
]

# Endung → erwarteter Magic-Typ (für Tarn-Erkennung)
_EXT_EXPECT = {
    ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".gif": "GIF", ".pdf": "PDF",
    ".mp4": "MP4", ".mov": "MP4", ".m4a": "MP4", ".3gp": "MP4", ".mp3": "MP3",
    ".zip": "ZIP", ".apk": "ZIP", ".jar": "ZIP", ".docx": "ZIP", ".xlsx": "ZIP",
    ".db": "SQLite", ".sqlite": "SQLite", ".sqlite3": "SQLite",
    ".gz": "GZIP", ".7z": "7-Zip", ".rar": "RAR", ".ogg": "OGG", ".xml": "XML",
}


def _sh(adb, cmd, t=120):
    return adb.shell(cmd, timeout=t) or ""


# Verdachts-Heuristik für Dateien/Pfade
_SUS_KEYWORDS = ("vault", "hide", "hidden", "versteck", "secret", "geheim", "spy", "spion",
                 "track", "keylog", "stalk", "rat", "payload", "exploit", "backdoor", "trojan",
                 "cheat", "crack", "frida", "xposed", "magisk", "applock", "privatespace",
                 "calculator", "nodetect", "ghost", "shadow", "covert")
_SUS_EXEC_EXT = (".sh", ".elf", ".bin", ".so", ".dex", ".jar", ".run", ".out", ".ko")
_DOUBLE_EXT = re.compile(
    r"\.(jpe?g|png|gif|webp|heic|pdf|docx?|xlsx?|mp[34]|mov|3gp|txt|csv)\."
    r"(apk|exe|sh|js|bat|scr|elf|bin|dex|jar|com|vbs)$", re.I)
_STALKERWARE = ("mspy", "flexispy", "thetruthspy", "cymobile", "spyhuman", "hellospy",
                "cerberus", "wt.cs", "android.systemservice", "core.mate", "ws.dm")


def _suspicious(files: list, dirs: list) -> list:
    """Liefert [(grund, pfad)] für verdächtige Dateien/Pfade (Anti-Forensik/Spyware-Indikatoren)."""
    sus = []
    for f in files:
        low = f.lower()
        bn = os.path.basename(f)
        if _DOUBLE_EXT.search(bn):
            sus.append(("Tarn-Doppelendung", f)); continue
        if bn == "su" or low.endswith("/su") or bn in ("busybox", "magisk", "frida-server"):
            sus.append(("Root-/Hook-Binary", f)); continue
        if any(k in low for k in _STALKERWARE):
            sus.append(("Bekannte Stalkerware", f)); continue
        if low.endswith(_SUS_EXEC_EXT) and "/sdcard" in low:
            sus.append(("Ausführbare Datei im Nutzerspeicher", f)); continue
        if low.endswith(".apk") and not any(d in low for d in
                                            ("/download", "/telegram", "/whatsapp", "/bluetooth", "/apk")):
            sus.append(("APK an ungewöhnlichem Ort", f)); continue
        if any(k in low for k in _SUS_KEYWORDS):
            kw = next(k for k in _SUS_KEYWORDS if k in low)
            sus.append((f"Verdächtiger Name ('{kw}')", f)); continue
        if low.endswith((".crypt12", ".crypt14", ".crypt15", ".enc", ".aes", ".vault")):
            sus.append(("Verschlüsselter Container", f))
    for d in dirs:
        low = d.lower()
        if any(k in low for k in _SUS_KEYWORDS) or any(k in low for k in _STALKERWARE):
            kw = next((k for k in _SUS_KEYWORDS + _STALKERWARE if k in low), "?")
            sus.append((f"Verdächtiger Ordner ('{kw}')", d + "/"))
    # Duplikate raus, stabil sortiert
    seen, uniq = set(), []
    for r, p in sus:
        if p not in seen:
            seen.add(p); uniq.append((r, p))
    return uniq


def _parse_du(text: str) -> dict:
    """du-Ausgabe '<KB>\\t<pfad>' → {pfad: bytes}."""
    sizes = {}
    for ln in text.splitlines():
        m = re.match(r"^\s*(\d+)\s+(.+)$", ln)
        if m:
            sizes[m.group(2).rstrip("/")] = int(m.group(1)) * 1024
    return sizes


def analyze(adb, root: str, st, max_depth: int = 0, _auto: bool = False, deep_magic: bool = True) -> str:
    root = (root or "/sdcard").rstrip("/") or "/"
    if not _auto:
        ui.clear(); ui.rule(f"Ordnerstruktur-Analyse: {root}", ui.CYAN)
        ui.info("Sammle Verzeichnisse, Dateien und Größen … (kann bei vielen Dateien dauern)")
    asroot = bool(st.get("is_root"))

    dirs_raw = _sh(adb, f"find {shq(root)} -type d 2>/dev/null", t=180)
    files_raw = _sh(adb, f"find {shq(root)} -type f 2>/dev/null", t=240)
    du_raw = _sh(adb, f"du {shq(root)} 2>/dev/null", t=240)
    dirs = [d.rstrip("/") for d in dirs_raw.splitlines() if d.strip()]
    files = [f for f in files_raw.splitlines() if f.strip()]
    sizes = _parse_du(du_raw)

    if not dirs and not files:
        msg = (f"Bereich {root} nicht lesbar/leer." +
               ("" if asroot else " Ohne Root sind /data & System geschützt – /sdcard versuchen."))
        if not _auto:
            ui.warn(msg); ui.pause()
        return _section_write(root, [msg])

    # Datei-Anzahl je Ordner (direkt enthaltene Dateien)
    fcount = Counter(os.path.dirname(f).rstrip("/") for f in files)
    total_bytes = sizes.get(root, sum(sizes.get(d, 0) for d in dirs))

    suspects = _suspicious(files, dirs)
    # ---- Magic-Byte-Scan: getarnte Dateien (Endung ≠ echter Inhalt) ----
    disguised = []
    magic = {}
    if deep_magic:
        if not _auto:
            ui.info("Prüfe Datei-Header (Magic-Bytes) … erkennt getarnte/umbenannte Dateien.")
        magic = _magic_scan(adb, root)
        for f, rt in magic.items():
            ext = os.path.splitext(f)[1].lower()
            exp = _EXT_EXPECT.get(ext)
            if exp and exp not in rt:
                disguised.append((f"TARNUNG: '{ext}' → echt {rt}", f))
            elif ("ausführbar" in rt or "EXE" in rt or "DEX" in rt) and "/sdcard" in f.lower() \
                    and not f.lower().endswith(_SUS_EXEC_EXT):
                disguised.append((f"Getarnt ausführbar: {rt}", f))
        # getarnte Funde nach vorne, Duplikate raus
        dpaths = {p for _, p in disguised}
        suspects = disguised + [s for s in suspects if s[1] not in dpaths]
    _LAST_SUSPECTS[:] = suspects          # für die Tiefen-Untersuchung merken
    base_depth = root.count("/")
    out = [f"===== ORDNERSTRUKTUR  {root}  ({time.strftime('%Y-%m-%d %H:%M:%S')}) =====",
           f"Verzeichnisse: {len(dirs)}   Dateien: {len(files)}   Gesamtgröße: {human_size(total_bytes)}",
           f"⚠ VERDÄCHTIGE OBJEKTE: {len(suspects)}   ·   GETARNTE DATEIEN: {len(disguised)}"
           f"   (Header geprüft: {len(magic)})",
           "", f"===== 🚨 GETARNTE DATEIEN (Endung ≠ Inhalt) ({len(disguised)}) ====="]
    for reason, p in disguised:
        out.append(f"  [TARNUNG] {p}   →   {reason}")
    out += ["", f"===== ⚠ VERDÄCHTIGE DATEIEN/PFADE ({len(suspects)}) ====="]
    for reason, p in suspects:
        out.append(f"  [!] [{reason}] {p}")
    out += ["", "===== VERZEICHNISBAUM ====="]

    # Baum rendern (voll in Datei; Anzeige paginiert über Pager)
    for d in sorted(dirs):
        depth = d.count("/") - base_depth
        if depth < 0:
            depth = 0
        if max_depth and depth > max_depth:
            continue
        name = os.path.basename(d) or d
        fc = fcount.get(d, 0)
        kb = sizes.get(d, 0)
        marker = "📁" if fc or any(x.startswith(d + "/") for x in dirs[:1]) else "📂"
        line = f"{'│  ' * depth}{marker} {name}/   ({fc} Dateien, {human_size(kb)})"
        out.append(line)

    # ---- Auswertungen ----
    exts = Counter((os.path.splitext(f)[1].lower() or "(ohne)") for f in files)
    out += ["", "===== DATEITYP-VERTEILUNG ====="]
    for ext, n in exts.most_common(40):
        out.append(f"  {n:>7}×  {ext}")

    out += ["", "===== TOP-VERZEICHNISSE NACH GRÖSSE ====="]
    for d, b in sorted(sizes.items(), key=lambda x: -x[1])[:30]:
        out.append(f"  {human_size(b):>10}  {d}")

    # größte Dateien (du -a, auf Dateien gefiltert)
    fileset = set(files)
    bigfiles = []
    for ln in _sh(adb, f"du -a {shq(root)} 2>/dev/null | sort -rn 2>/dev/null", t=180).splitlines():
        m = re.match(r"^\s*(\d+)\s+(.+)$", ln)
        if m and m.group(2).rstrip("/") in fileset:
            bigfiles.append((int(m.group(1)) * 1024, m.group(2)))
        if len(bigfiles) >= 40:
            break
    out += ["", "===== GRÖSSTE DATEIEN ====="]
    for b, p in bigfiles[:40]:
        out.append(f"  {human_size(b):>10}  {p}")

    hidden = [f for f in files + dirs if os.path.basename(f).startswith(".")]
    out += ["", f"===== VERSTECKTE DATEIEN/ORDNER ({len(hidden)}) ====="]
    out += [f"  {h}" for h in sorted(hidden)[:80]]

    empties = [d for d in dirs if fcount.get(d, 0) == 0 and not any(x != d and x.startswith(d + "/") for x in dirs)]
    out += ["", f"===== LEERE ORDNER ({len(empties)}) ====="]
    out += [f"  {d}" for d in sorted(empties)[:60]]

    # forensisch interessante Dateien nach Kategorie
    interest = {
        "Datenbanken (SQLite)": (".db", ".sqlite", ".sqlite3", ".db-wal", ".db-journal", ".db-shm"),
        "APK-/App-Pakete": (".apk", ".xapk", ".apks", ".apkm"),
        "Archive": (".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".tgz"),
        "Backups/verschlüsselt": (".ab", ".bak", ".crypt12", ".crypt14", ".crypt15", ".enc"),
        "Schlüssel/Zertifikate": (".key", ".pem", ".p12", ".keystore", ".jks", ".cer", ".crt", ".pfx"),
        "Kontakte/Kalender": (".vcf", ".ics"),
        "Dokumente": (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf"),
        "Konfiguration": (".xml", ".json", ".conf", ".cfg", ".ini", ".plist", ".properties"),
        "Medien-Roh": (".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov", ".3gp", ".webp", ".gif"),
    }
    interest_counts = []
    out += ["", "===== FORENSISCH INTERESSANTE DATEIEN ====="]
    for label, exts_ in interest.items():
        hits = [f for f in files if f.lower().endswith(exts_)]
        if hits:
            interest_counts.append((label, len(hits)))
            out.append(f"\n## {label} ({len(hits)})")
            out += [f"  {h}" for h in sorted(hits)[:150]]

    syms = _sh(adb, f"find {shq(root)} -type l 2>/dev/null", t=120)
    sym_list = [s for s in syms.splitlines() if s.strip()]
    out += ["", f"===== SYMLINKS ({len(sym_list)}) ====="]
    out += [f"  {s}" for s in sym_list[:60]]

    # VOLLSTÄNDIGES Datei-Inventar (alle Pfade)
    out += ["", f"===== VOLLSTÄNDIGES DATEI-INVENTAR ({len(files)}) ====="]
    out += sorted(files)

    # Bildschirm-Digest
    if not _auto:
        ui.kv("Verzeichnisse", len(dirs))
        ui.kv("Dateien", len(files))
        ui.kv("Gesamtgröße", human_size(total_bytes))
        ui.kv("Versteckte Objekte", len(hidden))
        if deep_magic:
            ui.kv("Header geprüft (Magic)", f"{len(magic)} Dateien")
            if disguised:
                ui.crit(f"{len(disguised)} GETARNTE DATEIEN (Endung ≠ echter Inhalt)!")
        # VERDÄCHTIGE OBJEKTE – rot pulsierend
        if suspects:
            print()
            ui.crit(f"{len(suspects)} VERDÄCHTIGE DATEIEN/PFADE ERKANNT")
            for reason, p in suspects[:30]:
                print(f"   {ui.pulse('⚠ ' + os.path.basename(p) or p)}  "
                      f"{ui.BRED}{reason}{ui.RESET}  {ui.GREY}{p}{ui.RESET}")
            if len(suspects) > 30:
                print(f"   {ui.BRED}… +{len(suspects)-30} weitere (siehe Bericht){ui.RESET}")
        else:
            ui.ok("Keine offensichtlich verdächtigen Dateien/Pfade.")
        print(f"\n  {ui.BOLD}Top-Dateitypen:{ui.RESET}")
        for ext, n in exts.most_common(8):
            print(f"    {ui.BCYAN}{n:>6}×{ui.RESET}  {ext}")
        print(f"\n  {ui.BOLD}Größte Verzeichnisse:{ui.RESET}")
        for d, b in sorted(sizes.items(), key=lambda x: -x[1])[:6]:
            print(f"    {ui.BYELLOW}{human_size(b):>9}{ui.RESET}  {d}")

    return _section_write(root, out, _auto)


def _section_write(root: str, lines: list, _auto: bool = False) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", root).strip("_") or "root"
    body = "\n".join(lines)
    p = _write(f"deep_dateibaum_{safe}.txt", body)
    if not _auto:
        ui.ok(f"Gespeichert: {p}  ({len(body.splitlines())} Zeilen)")
    return body


def _detect_magic(data: bytes) -> str:
    if not data:
        return ""
    for sig, name in _MAGICS:
        if data.startswith(sig):
            return name
        if name == "MP4/MOV" and data[4:8] == b"ftyp":
            return name
    if b"ftyp" in data[:16]:
        return "MP4/MOV"
    return ""


def _magic_scan(adb, root: str, limit: int = 8000) -> dict:
    """Liest die ersten 32 Byte JEDER Datei in EINEM On-Device-Befehl (base64)
    und bestimmt den echten Typ. Rückgabe {pfad: echter_typ}. Bounded via *limit*."""
    # Ein einziger Roundtrip: find → je Datei 'pfad\tbase64(head)'
    cmd = (f"find {shq(root)} -type f 2>/dev/null | head -n {int(limit)} | while IFS= read -r f; do "
           f"printf '%s\\t' \"$f\"; dd if=\"$f\" bs=32 count=1 2>/dev/null | base64 | tr -d '\\n'; "
           f"echo; done")
    out = adb.shell(cmd, timeout=900)
    result = {}
    for ln in out.splitlines():
        if "\t" not in ln:
            continue
        path, b64 = ln.split("\t", 1)
        try:
            data = base64.b64decode(b64 + "===")
        except Exception:  # noqa: BLE001
            continue
        rt = _detect_magic(data)
        if rt:
            result[path] = rt
    return result


def _pull_sample(adb, path: str, full_max: int = 25 * 1024 * 1024):
    """Zieht die Datei (oder ein 8-MB-Sample bei großen Dateien) auf den PC.
    Rückgabe (lokaler_pfad, ist_vollständig, größe)."""
    size = 0
    m = re.search(r"\b(\d{3,})\b", adb.shell(f"stat -c %s {shq(path)} 2>/dev/null") or "")
    if m:
        size = int(m.group(1))
    fd, local = tempfile.mkstemp(prefix="pz_inspect_")
    os.close(fd)
    if size and size > full_max:
        adb.shell(f"dd if={shq(path)} of=/sdcard/.pz_sample bs=1048576 count=8 2>/dev/null")
        adb.raw(["pull", "/sdcard/.pz_sample", local], timeout=120)
        adb.shell("rm -f /sdcard/.pz_sample")
        return local, False, size
    adb.raw(["pull", path, local], timeout=300)
    return local, True, (size or (os.path.getsize(local) if os.path.isfile(local) else 0))


def inspect_file(adb, path: str, st) -> None:
    """Tiefen-Untersuchung EINER Datei: was versteckt sich wirklich darin?"""
    ui.clear()
    ui.rule(f"🔬 Untersuchung: {os.path.basename(path)}", ui.CYAN)
    out = [f"# TIEFEN-UNTERSUCHUNG  {path}  ({time.strftime('%Y-%m-%d %H:%M:%S')})"]

    # Metadaten am Gerät (Owner/Rechte/SELinux/Zeit)
    meta = _sh(adb, f"ls -laZ {shq(path)} 2>/dev/null || ls -la {shq(path)} 2>/dev/null", t=20)
    stat = _sh(adb, f"stat {shq(path)} 2>/dev/null", t=20)
    if meta:
        ui.kv("Eintrag", meta.splitlines()[0][:100]); out += ["## Metadaten", meta]
    if stat:
        out.append(stat)

    # Inhalt ziehen & analysieren
    ui.info("Ziehe Inhalt zur Analyse …")
    try:
        local, full, size = _pull_sample(adb, path)
    except Exception as e:  # noqa: BLE001
        ui.err(f"Konnte Datei nicht lesen: {e}"); LOG.exception("inspect pull", e); ui.pause(); return
    if not os.path.isfile(local) or os.path.getsize(local) == 0:
        ui.err("Inhalt nicht lesbar (Sandbox/Root nötig?)."); ui.pause(); return
    with open(local, "rb") as f:
        data = f.read()

    real = _detect_magic(data)
    ext = os.path.splitext(path)[1].lower()
    expect = _EXT_EXPECT.get(ext)
    ui.kv("Größe", human_size(size))
    ui.kv("Echter Typ (Magic-Bytes)", real or "unbekannt")
    ui.kv("Laut Endung erwartet", expect or (ext or "—"))
    out += [f"Größe: {human_size(size)}", f"Echter Typ: {real or 'unbekannt'}",
            f"Erwartet (Endung): {expect or ext or '—'}"]

    # TARNUNG: Endung ≠ echter Inhalt → rot pulsierend
    mismatch = expect and real and expect not in real
    if mismatch:
        ui.crit(f"TARNUNG! Datei gibt sich als {expect} aus – ist aber {real}")
        out.append(f"!!! TARNUNG: Endung={expect}  Inhalt={real}")
    elif real and ("ausführbar" in real or "EXE" in real or "DEX" in real):
        ui.crit(f"AUSFÜHRBARER INHALT: {real}")
        out.append(f"!!! AUSFÜHRBAR: {real}")

    # Hash + VirusTotal
    sha = hashlib.sha256(data).hexdigest()
    ui.kv("SHA-256" + ("" if full else " (Sample)"), sha)
    out += [f"SHA-256{'' if full else ' (Sample)'}: {sha}",
            f"VirusTotal: https://www.virustotal.com/gui/file/{sha}"]

    # Hexdump des Kopfes
    head = " ".join(f"{b:02x}" for b in data[:64])
    out += ["## Hex-Kopf (64 Byte)", head]

    # Eingebettete Strings → IOCs
    text = data.decode("latin-1", "ignore")
    blob = " ".join(re.findall(r"[\x20-\x7e]{5,}", text))
    urls = sorted(set(re.findall(r"https?://[^\s\"'<>]{6,}", blob)))[:50]
    ips = sorted(set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", blob)))[:50]
    emails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", blob)))[:30]
    pkgs = sorted(set(re.findall(r"\b[a-z][a-z0-9_]+(?:\.[a-z0-9_]{2,}){2,}\b", blob)))[:50]
    for label, items, crit in [("URLs", urls, True), ("IP-Adressen", ips, True),
                               ("E-Mails", emails, True), ("Paket-/Klassennamen", pkgs, False)]:
        if items:
            out += [f"## {label} ({len(items)})"] + [f"  {x}" for x in items]
            col = ui.BRED if crit else ui.GREY
            print(f"  {ui.BOLD}{label} ({len(items)}):{ui.RESET}")
            for x in items[:10]:
                print(f"    {col}{x[:96]}{ui.RESET}")

    # ZIP/APK-Inhalt
    if full and real and "ZIP" in real:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = zf.namelist()
                out += [f"## Archiv-Inhalt ({len(names)} Einträge)"] + [f"  {n}" for n in names[:120]]
                ui.kv("Archiv-Einträge", len(names))
                if "AndroidManifest.xml" in names:
                    from . import apkscan
                    mani = apkscan.parse_manifest(zf.read("AndroidManifest.xml"))
                    ui.crit(f"ENTHÄLT APK/MANIFEST! Paket: {mani.get('package','?')}")
                    out += [f"!!! APK-Paket: {mani.get('package','?')}  v{mani.get('version','?')}",
                            "Permissions: " + ", ".join(mani.get("permissions", [])[:30])]
        except Exception as e:  # noqa: BLE001
            out.append(f"(ZIP nicht lesbar: {e})")

    # SQLite-Tabellen
    if real and "SQLite" in real and full:
        try:
            con = sqlite3.connect(local)
            tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            con.close()
            out += [f"## SQLite-Tabellen ({len(tabs)})"] + [f"  {t}" for t in tabs]
            ui.kv("SQLite-Tabellen", ", ".join(tabs[:12]))
        except Exception as e:  # noqa: BLE001
            out.append(f"(SQLite nicht lesbar: {e})")

    try:
        os.remove(local)
    except OSError:
        pass

    safe = re.sub(r"[^A-Za-z0-9]+", "_", path).strip("_")[-60:] or "datei"
    p = _write(f"untersuchung_{safe}.txt", "\n".join(out))
    ui.ok(f"Untersuchungsbericht: {p}")
    print()
    if ui.confirm("Vollständigen Untersuchungsbericht im Terminal ansehen?", True):
        ui.pager("\n".join(out), os.path.basename(path))
    ui.pause()


def _investigate(adb, st) -> None:
    """Menü: ein verdächtiges Objekt aus der letzten Analyse tief untersuchen."""
    while True:
        if not _LAST_SUSPECTS:
            ui.info("Keine verdächtigen Objekte aus der letzten Analyse."); ui.pause(); return
        ui.clear(); ui.rule("🔬 Verdächtige Objekte untersuchen", ui.CYAN)
        entries = []
        for i, (reason, p) in enumerate(_LAST_SUSPECTS[:40], 1):
            entries.append((str(i), f"{ui.pulse('⚠')} {reason}  {ui.GREY}{p}{ui.RESET}"))
        ch = ui.menu("Was untersuchen?", entries, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        try:
            reason, p = _LAST_SUSPECTS[int(ch) - 1]
        except (ValueError, IndexError):
            continue
        inspect_file(adb, p, st)


def menu(adb, dev, st) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🗂  Ordnerstruktur-/Dateisystem-Analyse")
        ui.kv("Root", f"{ui.BGREEN}ja{ui.RESET}" if st.get("is_root") else f"{ui.GREY}nein{ui.RESET}")
        entries = [
            ("1", "📁 /sdcard komplett analysieren (Nutzerspeicher)"),
            ("2", "📁 /sdcard/Android (App-Daten/-Medien)"),
            ("3", "📁 /sdcard/DCIM + Pictures + Download (Medien/Downloads)"),
            ("4", "✏  Eigenen Pfad eingeben"),
        ]
        if st.get("is_root"):
            entries += [("5", f"{ui.BYELLOW}🔐 /data komplett (App-Sandboxes – ROOT){ui.RESET}"),
                        ("6", f"{ui.BYELLOW}🔐 / (gesamtes Dateisystem – ROOT){ui.RESET}")]
        ch = ui.menu("Bereich wählen", entries, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        root = {"1": "/sdcard", "2": "/sdcard/Android",
                "3": "/sdcard/DCIM", "5": "/data", "6": "/"}.get(ch)
        if ch == "3":
            # mehrere Medienordner nacheinander
            bodies = []
            for r in ("/sdcard/DCIM", "/sdcard/Pictures", "/sdcard/Download"):
                bodies.append(analyze(adb, r, st, _auto=False))
            _after(adb, dev, st, "\n\n".join(bodies))
            continue
        if ch == "4":
            root = ui.ask("Absoluter Pfad (z.B. /sdcard/WhatsApp)").strip()
            if not root:
                continue
        if not root:
            continue
        body = analyze(adb, root, st)
        _after(adb, dev, st, body)


def _after(adb, dev, st, body: str) -> None:
    """Vollen Baum zeigen + verdächtige Funde untersuchen + Ansehen/Export."""
    print()
    ui.rule("📄 Vollständige Ordnerstruktur", ui.BGREEN)
    ui.pager(body, "")
    while True:
        opts = []
        if _LAST_SUSPECTS:
            opts.append(("u", ui.pulse(f"🔬 {len(_LAST_SUSPECTS)} VERDÄCHTIGE untersuchen – was versteckt sich?")))
        opts += [("v", "📖 Bericht erneut im Terminal ansehen"),
                 ("e", f"{ui.BGREEN}📤 Exportieren: HTML + JSON + Markdown + SHA-256{ui.RESET}")]
        ch = ui.menu("Weiter", opts, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "u":
            _investigate(adb, st)
        elif ch == "v":
            ui.pager(body, "")
        elif ch == "e":
            try:
                from . import deepforensics, report
                report._do(deepforensics._device_data(adb, st), ("html", "md", "json", "manifest"))
            except Exception as e:  # noqa: BLE001
                ui.err(f"Export fehlgeschlagen: {e}"); LOG.exception("filetree export", e); ui.pause()
