"""Hilfsfunktionen für ADB-Dateizugriff, SQLite-Extraktion, Timestamps."""
from __future__ import annotations

import os
import re
import time
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

from apz.adb import ADB
from apz.util import shq


# ---------------------------------------------------------------------------
# Timestamp-Helfer
# ---------------------------------------------------------------------------

def epoch_to_human(ms_or_s: str | int | None) -> str:
    """Epoch (ms oder s) → YYYY-MM-DD HH:MM:SS oder '—'."""
    if ms_or_s is None or ms_or_s == "":
        return "—"
    try:
        v = int(ms_or_s)
    except (ValueError, TypeError):
        return str(ms_or_s)
    if v <= 0:
        return "—"
    if v > 10_000_000_000:
        v //= 1000
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(v))
    except (OSError, OverflowError, ValueError):
        return str(ms_or_s)


def parse_android_date(s: str | None) -> str:
    """Konvertiert Android-Datumsstring aus dumpsys (YYYY-MM-DD HH:MM:SS) direkt."""
    if not s:
        return "—"
    return s.strip() or "—"


# ---------------------------------------------------------------------------
# ADB-Dateizugriff
# ---------------------------------------------------------------------------

def file_exists_on_device(adb: ADB, path: str, root: bool = False) -> bool:
    """Prüft ob eine Datei auf dem Gerät existiert."""
    out = adb.shell(f"test -f {shq(path)} && echo YES || echo NO", root=root)
    return "YES" in out


def dir_exists_on_device(adb: ADB, path: str, root: bool = False) -> bool:
    out = adb.shell(f"test -d {shq(path)} && echo YES || echo NO", root=root)
    return "YES" in out


def get_file_size_bytes(adb: ADB, path: str, root: bool = False) -> int:
    out = adb.shell(f"stat -c%s {shq(path)} 2>/dev/null", root=root)
    try:
        return int(out.strip())
    except (ValueError, TypeError):
        return 0


def pull_db_via_sdcard(adb: ADB, db_path: str, local_path: str, root: bool = True) -> bool:
    """Kopiert eine DB via /sdcard auf den Host.

    Strategie:
      1. cp DB → /sdcard/_psf_tmp.db  (root)
      2. adb pull /sdcard/_psf_tmp.db → local_path
      3. rm /sdcard/_psf_tmp.db

    Gibt True zurück wenn erfolgreich.
    """
    from .config import MAX_DB_SIZE_MB
    size = get_file_size_bytes(adb, db_path, root=root)
    if size > 0 and size > MAX_DB_SIZE_MB * 1024 * 1024:
        return False

    tmp = "/sdcard/_psf_tmp.db"
    adb.shell(f"cp {shq(db_path)} {tmp} 2>/dev/null", root=root)
    adb.shell(f"chmod 644 {tmp} 2>/dev/null", root=root)

    rc, _, _ = adb.raw(["pull", tmp, local_path], timeout=60)
    adb.shell(f"rm -f {tmp} 2>/dev/null")

    return rc == 0 and os.path.exists(local_path) and os.path.getsize(local_path) > 0


def sqlite_query_on_device(adb: ADB, db_path: str, query: str, root: bool = True) -> str:
    """Führt SQLite-Query direkt auf dem Gerät aus (wenn sqlite3 Binary vorhanden).

    Fallback: Kopiert DB via pull_db_via_sdcard und führt lokal aus.
    """
    # Direkte Methode: sqlite3 auf dem Gerät
    escaped = query.replace('"', '\\"')
    result = adb.shell(f'sqlite3 {shq(db_path)} "{escaped}" 2>/dev/null', root=root, timeout=30)
    if result.strip() and not result.strip().startswith("Error"):
        return result

    # Fallback: lokale Abfrage
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        tmp_path = tf.name

    try:
        if pull_db_via_sdcard(adb, db_path, tmp_path, root=root):
            conn = sqlite3.connect(tmp_path)
            try:
                cur = conn.execute(query)
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description] if cur.description else []
                lines = []
                if cols:
                    lines.append("|".join(cols))
                for row in rows:
                    lines.append("|".join(str(c) for c in row))
                return "\n".join(lines)
            except sqlite3.Error as e:
                return f"[SQL ERROR] {e}"
            finally:
                conn.close()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return ""


def list_tables(adb: ADB, db_path: str, root: bool = True) -> list[str]:
    """Listet alle Tabellen einer SQLite-DB."""
    out = sqlite_query_on_device(adb, db_path, ".tables", root=root)
    if not out.strip():
        out = sqlite_query_on_device(
            adb, db_path,
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            root=root
        )
    return [t.strip() for t in re.split(r"[\s|]+", out) if t.strip() and t != "name"]


def detect_db_encryption(adb: ADB, db_path: str, root: bool = True) -> bool:
    """Prüft ob eine SQLite-DB verschlüsselt ist.

    SQLite-Klartext-DBs beginnen immer mit 'SQLite format 3\x00'.
    """
    # Lese ersten 16 Bytes als Hex
    out = adb.shell(f"od -A n -t x1 -N 16 {shq(db_path)} 2>/dev/null", root=root)
    hex_bytes = out.replace("\n", " ").split()
    if len(hex_bytes) < 16:
        return True  # Kann nicht lesen → vermutlich verschlüsselt
    magic = bytes(int(h, 16) for h in hex_bytes[:15])
    expected = b"SQLite format 3"
    return magic != expected


# ---------------------------------------------------------------------------
# Paketnamen-Extraktion
# ---------------------------------------------------------------------------

def list_third_party_packages(adb: ADB) -> list[str]:
    out = adb.shell("pm list packages -3")
    pkgs = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            parts = line[len("package:"):].split()
            if parts:
                pkgs.append(parts[0])
    return pkgs


def get_installer(adb: ADB, pkg: str) -> str:
    out = adb.shell(f"pm list packages -i {shq(pkg)}")
    m = re.search(r"installer=(\S+)", out)
    val = m.group(1) if m else "null"
    return "" if val in ("null", "") else val


def get_dumpsys_package(adb: ADB, pkg: str) -> str:
    return adb.shell(
        f"dumpsys package {shq(pkg)} | grep -E "
        f"'firstInstallTime|lastUpdateTime|installerPackageName|versionCode|versionName|codePath|dataDir'",
        timeout=20,
    )


# ---------------------------------------------------------------------------
# String-Suche in APK-Strings
# ---------------------------------------------------------------------------

_IP_RE   = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_URL_RE  = re.compile(r"https?://[^\s\"'<>]{5,100}")
_KEY_RE  = re.compile(r"(?i)(?:api[_-]?key|secret|password|token|auth)[=:][^\s\"']{6,}")

def extract_strings_from_apk(adb: ADB, apk_path: str, root: bool = False) -> dict:
    """Sucht Strings in einer APK auf dem Gerät (grep/strings auf device).

    Gibt dict mit keys: ips, urls, secrets zurück.
    """
    result: dict = {"ips": [], "urls": [], "secrets": []}

    # strings binary vorhanden?
    has_strings = "strings" in adb.shell("which strings 2>/dev/null || command -v strings 2>/dev/null")
    if has_strings:
        raw = adb.shell(f"strings {shq(apk_path)} 2>/dev/null | head -n 2000", root=root, timeout=30)
    else:
        raw = adb.shell(
            f"cat {shq(apk_path)} | tr -d '\\000-\\010\\013-\\037' 2>/dev/null | "
            "grep -oE '[[:print:]]{8,100}' | head -n 2000",
            root=root, timeout=30
        )

    if not raw.strip():
        return result

    result["ips"]     = list(set(_IP_RE.findall(raw)))
    result["urls"]    = list(set(_URL_RE.findall(raw)))
    result["secrets"] = list(set(_KEY_RE.findall(raw)))
    return result


# ---------------------------------------------------------------------------
# Ausgabe-Verzeichnis
# ---------------------------------------------------------------------------

def ensure_output_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
