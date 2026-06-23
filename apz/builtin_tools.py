"""BUILT-IN TOOLS: Alle forensischen Kernfunktionen direkt im Tool – KEIN pip install nötig.

Nutzt ausschließlich Python-Standardbibliothek (sqlite3, hashlib, zipfile, struct,
socket, base64, re, os, subprocess). Keine externen Abhängigkeiten.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import socket
import sqlite3
import struct
import subprocess
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import ui

# ══════════════════════════════════════════════════════════════════════════════
# 1. HASH-BERECHNUNG (hashlib – built-in)
# ══════════════════════════════════════════════════════════════════════════════

def file_hashes(path: str) -> Dict[str, str]:
    """MD5, SHA1, SHA256, SHA512 für eine Datei."""
    algos = {
        "MD5":    hashlib.md5(),
        "SHA1":   hashlib.sha1(),
        "SHA256": hashlib.sha256(),
        "SHA512": hashlib.sha512(),
    }
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                for h in algos.values():
                    h.update(chunk)
        return {name: h.hexdigest() for name, h in algos.items()}
    except OSError as e:
        return {"error": str(e)}


def hash_string(data: str, algo: str = "sha256") -> str:
    return hashlib.new(algo, data.encode()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# 2. APK-ANALYSE (zipfile – built-in)
# ══════════════════════════════════════════════════════════════════════════════

_DANGEROUS_PERMS = {
    "android.permission.READ_SMS",
    "android.permission.SEND_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.READ_CALL_LOG",
    "android.permission.PROCESS_OUTGOING_CALLS",
    "android.permission.READ_CONTACTS",
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.INTERNET",
    "android.permission.RECEIVE_BOOT_COMPLETED",
    "android.permission.FOREGROUND_SERVICE",
    "android.permission.REQUEST_INSTALL_PACKAGES",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.GET_ACCOUNTS",
}

def apk_info(apk_path: str) -> Dict[str, Any]:
    """Analysiert eine APK-Datei (ZIP-Format) ohne externe Tools."""
    result: Dict[str, Any] = {
        "path": apk_path,
        "size_mb": 0.0,
        "files": [],
        "has_classes_dex": False,
        "has_native_libs": [],
        "manifest_raw": "",
        "permissions": [],
        "dangerous_permissions": [],
        "hashes": {},
        "cert_info": "",
    }
    try:
        result["size_mb"] = round(os.path.getsize(apk_path) / 1024 / 1024, 2)
        result["hashes"] = file_hashes(apk_path)
        with zipfile.ZipFile(apk_path, "r") as z:
            names = z.namelist()
            result["files"] = names[:200]
            result["has_classes_dex"] = any(n.startswith("classes") and n.endswith(".dex") for n in names)
            result["has_native_libs"] = [n for n in names if n.startswith("lib/") and n.endswith(".so")]
            # Manifest (binär-XML – nur rohe Bytes, keine Dekodierung ohne aapt)
            if "AndroidManifest.xml" in names:
                raw = z.read("AndroidManifest.xml")
                result["manifest_raw"] = f"{len(raw)} Bytes (binär-XML – aapt/apktool für Klartext)"
                # Permissions aus rohen Bytes per Regex extrahieren (oft als Strings eingebettet)
                text = raw.decode("latin-1", errors="replace")
                perms = re.findall(r"android\.permission\.[A-Z_]+", text)
                result["permissions"] = list(set(perms))
                result["dangerous_permissions"] = [p for p in result["permissions"] if p in _DANGEROUS_PERMS]
            # Zertifikat
            cert_files = [n for n in names if n.startswith("META-INF/") and n.endswith((".RSA", ".DSA", ".EC"))]
            if cert_files:
                cert_raw = z.read(cert_files[0])
                result["cert_info"] = f"{cert_files[0]} – {len(cert_raw)} Bytes"
    except Exception as e:  # noqa: BLE001
        result["error"] = str(e)
    return result


def show_apk_info(apk_path: str) -> None:
    """Zeigt APK-Infos im Terminal."""
    ui.rule(f"APK: {os.path.basename(apk_path)}", ui.CYAN)
    info = apk_info(apk_path)
    if "error" in info:
        ui.err(info["error"]); return
    ui.kv("Größe",           f"{info['size_mb']} MB")
    ui.kv("Dateien",         str(len(info["files"])))
    ui.kv("DEX vorhanden",   "JA" if info["has_classes_dex"] else "NEIN")
    ui.kv("Native Libs",     str(len(info["has_native_libs"])))
    ui.kv("SHA256",          info["hashes"].get("SHA256", ""))
    print()
    if info["dangerous_permissions"]:
        ui.warn(f"{len(info['dangerous_permissions'])} GEFÄHRLICHE BERECHTIGUNGEN:")
        for p in sorted(info["dangerous_permissions"]):
            print(f"  {ui.BRED}✗{ui.RESET} {p}")
    else:
        ui.ok("Keine gefährlichen Berechtigungen erkannt.")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# 3. SQLITE-FORENSIK (sqlite3 – built-in)
# ══════════════════════════════════════════════════════════════════════════════

def sqlite_tables(db_path: str) -> List[str]:
    try:
        con = sqlite3.connect(db_path)
        cur = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [r[0] for r in cur.fetchall()]
    except Exception:
        return []


def sqlite_dump(db_path: str, table: str, limit: int = 100) -> List[Dict]:
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        rows = con.execute(f"SELECT * FROM [{table}] LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def sqlite_recover_deleted(db_path: str) -> List[bytes]:
    """Versucht gelöschte Zeilen aus nicht-überschriebenen Seiten zu extrahieren."""
    recovered = []
    try:
        with open(db_path, "rb") as f:
            data = f.read()
        # SQLite Seitengröße aus Header (Byte 16-17)
        page_size = struct.unpack(">H", data[16:18])[0]
        if page_size == 1:
            page_size = 65536
        # Suche nach Record-Mustern in freien Seitenbereichen
        for i in range(0, len(data) - page_size, page_size):
            page = data[i:i+page_size]
            # Freie Block-Liste suchen
            free_start = struct.unpack(">H", page[1:3])[0] if len(page) >= 4 else 0
            if free_start > 0 and free_start < page_size:
                recovered.append(page[free_start:free_start+64])
    except Exception:
        pass
    return recovered


def show_sqlite_db(db_path: str) -> None:
    """Interaktiver SQLite-Browser (built-in)."""
    tables = sqlite_tables(db_path)
    if not tables:
        ui.err(f"Keine Tabellen in {db_path}"); return
    ui.rule(f"SQLite: {os.path.basename(db_path)}", ui.CYAN)
    for i, t in enumerate(tables, 1):
        print(f"  {i:2d}  {t}")
    print()
    ch = input("  Tabelle (Nr): ").strip()
    try:
        tbl = tables[int(ch) - 1]
    except (ValueError, IndexError):
        return
    rows = sqlite_dump(db_path, tbl)
    ui.rule(f"Tabelle: {tbl} ({len(rows)} Zeilen)", ui.CYAN)
    for r in rows[:30]:
        print(f"  {r}")
    if len(rows) == 100:
        print(f"  {ui.GREY}… (max. 100 Zeilen angezeigt){ui.RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. STRING-EXTRAKTION (built-in)
# ══════════════════════════════════════════════════════════════════════════════

def extract_strings(path: str, min_len: int = 4) -> List[str]:
    """Extrahiert druckbare ASCII/UTF-8-Strings aus Binärdateien (wie 'strings')."""
    results = []
    pattern = re.compile(rb"[\x20-\x7e]{" + str(min_len).encode() + rb",}")
    try:
        with open(path, "rb") as f:
            data = f.read()
        results = [m.group().decode("ascii", errors="replace") for m in pattern.finditer(data)]
    except OSError:
        pass
    return results


def extract_emails(path: str) -> List[str]:
    strings = extract_strings(path, min_len=6)
    email_re = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    emails = set()
    for s in strings:
        emails.update(email_re.findall(s))
    return sorted(emails)


def extract_urls(path: str) -> List[str]:
    strings = extract_strings(path, min_len=8)
    url_re = re.compile(r"https?://[^\s\"'<>]{4,}")
    urls = set()
    for s in strings:
        urls.update(url_re.findall(s))
    return sorted(urls)


def extract_ips(path: str) -> List[str]:
    strings = extract_strings(path)
    ip_re = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    ips = set()
    for s in strings:
        ips.update(ip_re.findall(s))
    return sorted(ips)


# ══════════════════════════════════════════════════════════════════════════════
# 5. DATEI-CARVING (built-in Magic-Bytes)
# ══════════════════════════════════════════════════════════════════════════════

_MAGIC: List[Tuple[bytes, str, str]] = [
    (b"\xff\xd8\xff",         "JPEG",    ".jpg"),
    (b"\x89PNG\r\n\x1a\n",   "PNG",     ".png"),
    (b"GIF8",                  "GIF",     ".gif"),
    (b"BM",                    "BMP",     ".bmp"),
    (b"PK\x03\x04",           "ZIP/APK/DOCX", ".zip"),
    (b"\x50\x4b\x05\x06",    "ZIP-End", ".zip"),
    (b"dex\n",                 "DEX",     ".dex"),
    (b"\x7fELF",              "ELF",     ".elf"),
    (b"SQLite format 3",       "SQLite",  ".db"),
    (b"%PDF",                  "PDF",     ".pdf"),
    (b"\x1f\x8b",             "GZIP",    ".gz"),
    (b"MZ",                    "PE-EXE",  ".exe"),
    (b"\xca\xfe\xba\xbe",    "Java-Class", ".class"),
    (b"RIFF",                  "WAV/AVI", ".riff"),
    (b"\x00\x00\x00 ftyp",   "MP4",     ".mp4"),
    (b"ID3",                   "MP3",     ".mp3"),
    (b"OggS",                  "OGG",     ".ogg"),
    (b"\x49\x49\x2a\x00",    "TIFF-LE", ".tif"),
    (b"\x4d\x4d\x00\x2a",    "TIFF-BE", ".tif"),
    (b"-----BEGIN",            "PEM/Cert", ".pem"),
    (b"-----BEGIN RSA",        "RSA-Key",  ".key"),
]

def carve_files(data_path: str, out_dir: str, chunk_size: int = 1024 * 1024) -> List[str]:
    """Einfaches Datei-Carving per Magic-Bytes aus einem Image/Dump."""
    os.makedirs(out_dir, exist_ok=True)
    found = []
    try:
        with open(data_path, "rb") as f:
            data = f.read(chunk_size * 100)  # max 100 MB
        for magic, ftype, ext in _MAGIC:
            offset = 0
            while True:
                pos = data.find(magic, offset)
                if pos < 0:
                    break
                # Grobe Größenschätzung: 512 KB ab Fundstelle
                snippet = data[pos:pos + 512 * 1024]
                fname = os.path.join(out_dir, f"carved_{ftype}_{pos:08x}{ext}")
                with open(fname, "wb") as out:
                    out.write(snippet)
                found.append(fname)
                offset = pos + len(magic)
    except OSError:
        pass
    return found


# ══════════════════════════════════════════════════════════════════════════════
# 6. NETZWERK-SCAN (socket – built-in)
# ══════════════════════════════════════════════════════════════════════════════

def port_scan(host: str, ports: List[int], timeout: float = 0.5) -> Dict[int, bool]:
    """Einfacher TCP-Port-Scanner ohne nmap."""
    result = {}
    for port in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            open_ = s.connect_ex((host, port)) == 0
            s.close()
            result[port] = open_
        except Exception:
            result[port] = False
    return result


def resolve_host(hostname: str) -> str:
    try:
        return socket.gethostbyname(hostname)
    except Exception:
        return ""


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ══════════════════════════════════════════════════════════════════════════════
# 7. BASE64 / ENCODING (built-in)
# ══════════════════════════════════════════════════════════════════════════════

def b64_decode_safe(data: str) -> str:
    try:
        return base64.b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""


def find_b64_in_strings(path: str) -> List[Tuple[str, str]]:
    """Findet Base64-kodierte Strings in einer Datei und dekodiert sie."""
    b64_re = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")
    results = []
    for s in extract_strings(path, min_len=20):
        for m in b64_re.finditer(s):
            decoded = b64_decode_safe(m.group())
            if decoded and any(c.isprintable() for c in decoded[:20]):
                results.append((m.group(), decoded))
    return results[:50]


# ══════════════════════════════════════════════════════════════════════════════
# 8. TIMELINE / ZEITSTEMPEL (built-in)
# ══════════════════════════════════════════════════════════════════════════════

def file_timeline(directory: str, recursive: bool = True) -> List[Dict]:
    """Erstellt eine Zeitstempel-Timeline aller Dateien in einem Verzeichnis."""
    entries = []
    walk = os.walk(directory) if recursive else [(directory, [], os.listdir(directory))]
    for root, dirs, files in walk:
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                s = os.stat(fpath)
                entries.append({
                    "path": fpath,
                    "size": s.st_size,
                    "mtime": datetime.fromtimestamp(s.st_mtime).isoformat(),
                    "ctime": datetime.fromtimestamp(s.st_ctime).isoformat(),
                    "atime": datetime.fromtimestamp(s.st_atime).isoformat(),
                })
            except OSError:
                pass
    entries.sort(key=lambda x: x["mtime"], reverse=True)
    return entries


# ══════════════════════════════════════════════════════════════════════════════
# 9. PASSWORT-ANALYSE (built-in – ohne Cracking)
# ══════════════════════════════════════════════════════════════════════════════

def analyze_hash(hash_str: str) -> Dict[str, str]:
    """Erkennt Hash-Typ anhand Länge und Muster."""
    h = hash_str.strip().lower()
    length_map = {
        32:  "MD5",
        40:  "SHA1",
        56:  "SHA224",
        64:  "SHA256",
        96:  "SHA384",
        128: "SHA512",
    }
    htype = length_map.get(len(h), "Unbekannt")
    is_hex = bool(re.fullmatch(r"[0-9a-f]+", h))
    if h.startswith("$2b$") or h.startswith("$2a$"):
        htype = "bcrypt"
    elif h.startswith("$6$"):
        htype = "SHA512-crypt (Linux)"
    elif h.startswith("$5$"):
        htype = "SHA256-crypt (Linux)"
    elif h.startswith("$1$"):
        htype = "MD5-crypt"
    elif h.startswith("$apr1$"):
        htype = "APR1-MD5 (Apache)"
    return {"hash": hash_str, "type": htype, "is_hex": str(is_hex), "length": str(len(h))}


# ══════════════════════════════════════════════════════════════════════════════
# 10. CAPABILITY-REGISTRY – Was ist built-in vs. installiert
# ══════════════════════════════════════════════════════════════════════════════

BUILTIN_CAPABILITIES: Dict[str, Dict] = {
    "hash_calc":       {"name": "Hash-Berechnung (MD5/SHA*)",  "fn": file_hashes,          "builtin": True},
    "apk_analyse":     {"name": "APK-Analyse",                  "fn": apk_info,             "builtin": True},
    "sqlite_forensik": {"name": "SQLite-Forensik",              "fn": sqlite_tables,        "builtin": True},
    "string_extract":  {"name": "String-Extraktion",            "fn": extract_strings,      "builtin": True},
    "file_carving":    {"name": "Datei-Carving (Magic-Bytes)",  "fn": carve_files,          "builtin": True},
    "email_extract":   {"name": "E-Mail-Extraktion",            "fn": extract_emails,       "builtin": True},
    "url_extract":     {"name": "URL-Extraktion",               "fn": extract_urls,         "builtin": True},
    "port_scan":       {"name": "TCP-Port-Scanner",             "fn": port_scan,            "builtin": True},
    "b64_decode":      {"name": "Base64-Erkennung/-Dekodierung","fn": find_b64_in_strings,  "builtin": True},
    "timeline":        {"name": "Datei-Timeline",               "fn": file_timeline,        "builtin": True},
    "hash_analyze":    {"name": "Hash-Typ-Erkennung",           "fn": analyze_hash,         "builtin": True},
}


def show_capability_status() -> None:
    """Zeigt alle built-in Fähigkeiten + externe Tool-Verfügbarkeit."""
    import shutil
    ui.clear()
    ui.banner(subtitle="⚙️  TOOL-FÄHIGKEITEN – Built-in & Externe Tools")
    print()

    ui.rule("✅ BUILT-IN (kein Install nötig)", ui.BGREEN)
    print()
    for key, cap in BUILTIN_CAPABILITIES.items():
        print(f"  {ui.BGREEN}✓{ui.RESET}  {cap['name']:<40} {ui.GREY}(Python stdlib){ui.RESET}")
    print()

    ui.rule("🔧 EXTERNE TOOLS (optional – erweitern die Fähigkeiten)", ui.CYAN)
    print()
    ext_tools = [
        ("adb",         "ADB",              "android-sdk-platform-tools"),
        ("frida",       "Frida",            "pip: frida-tools"),
        ("jadx",        "JADX Decompiler",  "apt: jadx"),
        ("apktool",     "Apktool",          "apt: apktool"),
        ("sqlite3",     "SQLite3 CLI",      "apt: sqlite3"),
        ("volatility3", "Volatility3",      "pip: volatility3"),
        ("yara",        "YARA",             "apt: yara"),
        ("nmap",        "nmap",             "apt: nmap"),
        ("hashcat",     "hashcat",          "apt: hashcat"),
        ("exiftool",    "ExifTool",         "apt: libimage-exiftool-perl"),
        ("binwalk",     "binwalk",          "apt: binwalk"),
        ("foremost",    "foremost",         "apt: foremost"),
        ("wireshark",   "Wireshark",        "apt: wireshark"),
        ("aircrack-ng", "aircrack-ng",      "apt: aircrack-ng"),
        ("radare2",     "Radare2",          "apt: radare2"),
        ("ghidra",      "Ghidra",           "manual: ghidra.re"),
        ("burpsuite",   "BurpSuite",        "manual: portswigger.net"),
    ]
    for binary, name, install in ext_tools:
        path = shutil.which(binary)
        if path:
            print(f"  {ui.BGREEN}✓{ui.RESET}  {name:<25} {ui.GREY}{path}{ui.RESET}")
        else:
            print(f"  {ui.GREY}✗{ui.RESET}  {name:<25} {ui.GREY}→ {install}{ui.RESET}")
    print()
    ui.pause()
