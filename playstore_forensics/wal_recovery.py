"""SQLite WAL-Datei + Journal Recovery für Play Store Datenbanken.

WAL-Format:
  Header: 32 Bytes (Magic 0x377f0682 big-endian, version, page_size, ...)
  Frames: 24-Byte Frame-Header + page_size Bytes Dateninhalt

Journal-Format:
  Magic: 0xd9d505f920a163d7 (big-endian, 8 Bytes)
  Danach: page-entries

Unterstützte Dateien:
  frosting.db-wal     Play-Store Installations-WAL
  suggestions.db-wal  Suchverlauf-WAL
  *.db-journal        SQLite Rollback-Journal
"""
from __future__ import annotations

import hashlib
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from apz.adb import ADB
from apz.util import shq

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

WAL_MAGIC_LE   = 0x377f0683  # little-endian (selten)
WAL_MAGIC_BE   = 0x377f0682  # big-endian (Standard)
WAL_FRAME_HDR  = 24           # Bytes pro Frame-Header
WAL_FILE_HDR   = 32           # Bytes WAL-Datei-Header

JOURNAL_MAGIC  = b"\xd9\xd5\x05\xf9\x20\xa1\x63\xd7"  # 8 Bytes

# Minimale Konfidenz für Treffer-Aufnahme
MIN_CONFIDENCE = 0.25


# ---------------------------------------------------------------------------
# Regex-Muster für forensisch relevante Strings
# ---------------------------------------------------------------------------

_RE_PACKAGE  = re.compile(rb"[a-z][a-z0-9_]{1,15}(?:\.[a-z][a-z0-9_]{1,15}){1,6}")
_RE_URL      = re.compile(rb"https?://[^\x00\s<>\"]{6,120}")
_RE_IP       = re.compile(rb"(?:\d{1,3}\.){3}\d{1,3}")
_RE_EMAIL    = re.compile(rb"[a-zA-Z0-9._%+\-]{3,40}@[a-zA-Z0-9.\-]{3,30}\.[a-zA-Z]{2,6}")
_RE_EPOCH_MS = re.compile(rb"[\x00-\x7f]{8}")   # potenzielle 8-Byte-Integers
_RE_TS_STR   = re.compile(rb"20[12]\d-[01]\d-[0-3]\d[ T][0-2]\d:[0-5]\d:[0-5]\d")


# ---------------------------------------------------------------------------
# Datenklassen
# ---------------------------------------------------------------------------

@dataclass
class WalFrame:
    frame_number:   int
    page_number:    int
    db_size_after:  int     # 0 = kein Commit, >0 = Commit-Frame
    salt1:          int
    salt2:          int
    checksum1:      int
    checksum2:      int
    page_data:      bytes   # Länge = page_size aus WAL-Header
    is_commit:      bool    = False


@dataclass
class RecoveredRecord:
    source:      str           # "WAL", "JOURNAL", "BINARY_SCAN"
    db_path:     str
    frame_num:   int
    record_type: str           # "PACKAGE", "URL", "TIMESTAMP", "EMAIL", "IP", "RAW"
    value:       str
    context:     str = ""
    confidence:  float = 0.5


@dataclass
class WalRecoveryResult:
    db_path:         str
    wal_path:        str        # leer wenn nicht gefunden
    journal_path:    str        # leer wenn nicht gefunden
    frames_total:    int  = 0
    frames_commit:   int  = 0
    records:         list[RecoveredRecord] = field(default_factory=list)
    raw_packages:    list[str] = field(default_factory=list)
    raw_urls:        list[str] = field(default_factory=list)
    raw_timestamps:  list[str] = field(default_factory=list)
    errors:          list[str] = field(default_factory=list)
    sha256:          str  = ""

    @property
    def has_data(self) -> bool:
        return bool(self.records or self.raw_packages or self.raw_urls)


# ---------------------------------------------------------------------------
# WAL-Header Parsing
# ---------------------------------------------------------------------------

@dataclass
class WalFileHeader:
    magic:         int
    version:       int
    page_size:     int
    seq_counter:   int
    salt1:         int
    salt2:         int
    checksum1:     int
    checksum2:     int
    is_little_endian: bool = False

    @classmethod
    def from_bytes(cls, data: bytes) -> "WalFileHeader":
        if len(data) < WAL_FILE_HDR:
            raise ValueError(f"WAL-Header zu kurz: {len(data)} < {WAL_FILE_HDR}")
        magic = struct.unpack_from(">I", data, 0)[0]
        if magic == WAL_MAGIC_BE:
            le = False
        elif magic == WAL_MAGIC_LE:
            le = True
        else:
            raise ValueError(f"Kein gültiges WAL-Magic: 0x{magic:08x}")
        fmt = "<IIIIIII" if le else ">IIIIIII"
        version, page_size, seq, salt1, salt2, cs1, cs2 = struct.unpack_from(fmt, data, 4)
        # WAL page_size codiert: 0 bedeutet 65536
        if page_size == 0:
            page_size = 65536
        return cls(magic, version, page_size, seq, salt1, salt2, cs1, cs2, le)


# ---------------------------------------------------------------------------
# WAL-Frame Parsing
# ---------------------------------------------------------------------------

def _parse_wal_frame(
    data: bytes,
    offset: int,
    frame_num: int,
    page_size: int,
    little_endian: bool,
) -> Optional[WalFrame]:
    """Parsed einen einzelnen WAL-Frame aus `data` ab `offset`."""
    needed = WAL_FRAME_HDR + page_size
    if offset + needed > len(data):
        return None
    fmt = "<IIIIII" if little_endian else ">IIIIII"
    page_num, db_size, salt1, salt2, cs1, cs2 = struct.unpack_from(fmt, data, offset)
    page_data = data[offset + WAL_FRAME_HDR : offset + WAL_FRAME_HDR + page_size]
    return WalFrame(
        frame_number=frame_num,
        page_number=page_num,
        db_size_after=db_size,
        salt1=salt1,
        salt2=salt2,
        checksum1=cs1,
        checksum2=cs2,
        page_data=page_data,
        is_commit=(db_size > 0),
    )


# ---------------------------------------------------------------------------
# Nutzdaten-Extraktion aus einem Frame
# ---------------------------------------------------------------------------

def _extract_from_frame(frame: WalFrame, db_path: str) -> list[RecoveredRecord]:
    """Durchsucht den Frame-Inhalt nach forensisch relevanten Daten."""
    recs: list[RecoveredRecord] = []
    d = frame.page_data

    def _add(rtype: str, value: str, ctx: str = "", conf: float = 0.5) -> None:
        recs.append(RecoveredRecord(
            source="WAL", db_path=db_path,
            frame_num=frame.frame_number,
            record_type=rtype, value=value,
            context=ctx, confidence=conf,
        ))

    # Paket-Namen
    for m in _RE_PACKAGE.finditer(d):
        val = m.group().decode("ascii", errors="replace")
        dots = val.count(".")
        if dots < 1:
            continue
        # Mindestens 2 Segmente, kein zu kurzes Segment
        segs = val.split(".")
        if any(len(s) < 2 for s in segs):
            continue
        conf = 0.7 if dots >= 2 else 0.4
        ctx = d[max(0, m.start()-16) : m.end()+16].decode("latin-1", errors="replace")
        _add("PACKAGE", val, ctx, conf)

    # URLs
    for m in _RE_URL.finditer(d):
        url = m.group().decode("ascii", errors="replace")
        _add("URL", url, "", 0.85)

    # IP-Adressen
    for m in _RE_IP.finditer(d):
        ip = m.group().decode("ascii")
        parts = ip.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            _add("IP", ip, "", 0.6)

    # E-Mail-Adressen
    for m in _RE_EMAIL.finditer(d):
        _add("EMAIL", m.group().decode("ascii", errors="replace"), "", 0.75)

    # Timestamp-Strings
    for m in _RE_TS_STR.finditer(d):
        _add("TIMESTAMP", m.group().decode("ascii"), "", 0.9)

    # 8-Byte Epoch-Millis (SQLite integer columns)
    for i in range(0, len(d) - 8, 4):
        chunk = d[i:i+8]
        ts_ms = struct.unpack_from(">Q", chunk)[0]
        # Epoch-ms zwischen 2015-01-01 und 2030-01-01
        if 1_420_000_000_000 <= ts_ms <= 1_893_456_000_000:
            import time
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts_ms // 1000))
            _add("TIMESTAMP_MS", dt, f"offset={i}", 0.6)

    return [r for r in recs if r.confidence >= MIN_CONFIDENCE]


# ---------------------------------------------------------------------------
# WAL-Datei vollständig lesen
# ---------------------------------------------------------------------------

def _read_local_wal(wal_path: str) -> WalRecoveryResult:
    """Liest eine lokale WAL-Datei und extrahiert alle Records."""
    path = Path(wal_path)
    db_path = str(path).removesuffix("-wal")
    result = WalRecoveryResult(db_path=db_path, wal_path=wal_path, journal_path="")

    if not path.exists() or path.stat().st_size == 0:
        result.errors.append(f"WAL-Datei nicht vorhanden oder leer: {wal_path}")
        return result

    data = path.read_bytes()

    # Checksum
    result.sha256 = hashlib.sha256(data).hexdigest()

    # Header
    try:
        hdr = WalFileHeader.from_bytes(data)
    except ValueError as e:
        result.errors.append(f"WAL-Header Fehler: {e}")
        # Trotzdem binären Scan versuchen
        result.records.extend(_binary_scan_data(data, wal_path, "WAL_BINARY"))
        return result

    page_size = hdr.page_size
    offset = WAL_FILE_HDR
    frame_num = 0

    while offset + WAL_FRAME_HDR + page_size <= len(data):
        frame = _parse_wal_frame(data, offset, frame_num, page_size, hdr.is_little_endian)
        if frame is None:
            break
        result.frames_total += 1
        if frame.is_commit:
            result.frames_commit += 1
        result.records.extend(_extract_from_frame(frame, db_path))
        offset += WAL_FRAME_HDR + page_size
        frame_num += 1

    # Deduplizieren
    _dedup_records(result)
    return result


# ---------------------------------------------------------------------------
# Journal Recovery
# ---------------------------------------------------------------------------

def _read_local_journal(journal_path: str) -> WalRecoveryResult:
    """Liest ein SQLite Rollback-Journal."""
    path = Path(journal_path)
    db_path = str(path).removesuffix("-journal")
    result = WalRecoveryResult(db_path=db_path, wal_path="", journal_path=journal_path)

    if not path.exists() or path.stat().st_size < 8:
        result.errors.append(f"Journal nicht gefunden: {journal_path}")
        return result

    data = path.read_bytes()
    result.sha256 = hashlib.sha256(data).hexdigest()

    # Magic prüfen
    if not data.startswith(JOURNAL_MAGIC):
        # Trotzdem scannen
        result.errors.append("Kein gültiges Journal-Magic – binärer Scan.")
        result.records.extend(_binary_scan_data(data, journal_path, "JOURNAL_BINARY"))
        _dedup_records(result)
        return result

    # Journal-Header: magic(8) + pagecnt(4) + rand_nonce(4) + initial_size(4) + ...
    # Ab Byte 20 folgen die Page-Entries: pageno(4) + page_data + checksum(4)
    # page_size ist unbekannt ohne die Haupt-DB – wir lesen nur freie Strings
    result.records.extend(_binary_scan_data(data[20:], journal_path, "JOURNAL"))
    _dedup_records(result)
    return result


# ---------------------------------------------------------------------------
# Binärer Scan (Fallback ohne valides Header-Format)
# ---------------------------------------------------------------------------

def _binary_scan_data(
    data: bytes,
    source_path: str,
    source_label: str,
) -> list[RecoveredRecord]:
    recs: list[RecoveredRecord] = []

    def _add(rtype: str, value: str, conf: float) -> None:
        recs.append(RecoveredRecord(
            source=source_label, db_path=source_path,
            frame_num=-1, record_type=rtype,
            value=value, confidence=conf,
        ))

    for m in _RE_PACKAGE.finditer(data):
        val = m.group().decode("ascii", errors="replace")
        if val.count(".") >= 2:
            _add("PACKAGE", val, 0.5)

    for m in _RE_URL.finditer(data):
        _add("URL", m.group().decode("ascii", errors="replace"), 0.8)

    for m in _RE_EMAIL.finditer(data):
        _add("EMAIL", m.group().decode("ascii", errors="replace"), 0.7)

    for m in _RE_TS_STR.finditer(data):
        _add("TIMESTAMP", m.group().decode("ascii"), 0.85)

    for m in _RE_IP.finditer(data):
        ip = m.group().decode("ascii")
        if all(0 <= int(p) <= 255 for p in ip.split(".")):
            _add("IP", ip, 0.4)

    return [r for r in recs if r.confidence >= MIN_CONFIDENCE]


# ---------------------------------------------------------------------------
# Deduplizierung
# ---------------------------------------------------------------------------

def _dedup_records(result: WalRecoveryResult) -> None:
    seen: set[tuple] = set()
    unique: list[RecoveredRecord] = []
    for r in result.records:
        key = (r.record_type, r.value)
        if key not in seen:
            seen.add(key)
            unique.append(r)
        else:
            # Konfidenz-Boost durch mehrfaches Vorkommen
            for u in unique:
                if (u.record_type, u.value) == key:
                    u.confidence = min(1.0, u.confidence + 0.1)
                    break
    result.records = unique

    # Kurzlisten befüllen
    result.raw_packages  = [r.value for r in unique if r.record_type == "PACKAGE"]
    result.raw_urls      = [r.value for r in unique if r.record_type == "URL"]
    result.raw_timestamps = [r.value for r in unique if r.record_type in ("TIMESTAMP", "TIMESTAMP_MS")]


# ---------------------------------------------------------------------------
# ADB-gestützte Extraktion
# ---------------------------------------------------------------------------

def _pull_file_via_adb(adb: ADB, device_path: str, local_path: str, root: bool) -> bool:
    """Zieht eine einzelne Datei via ADB (mit sdcard-Trick bei root)."""
    if root:
        sdtmp = "/sdcard/psf_tmp_wal"
        adb.shell(f"cp {shq(device_path)} {shq(sdtmp)} 2>/dev/null", root=True, timeout=10)
        result = adb.raw(["pull", sdtmp, local_path], timeout=20)
        adb.shell(f"rm -f {shq(sdtmp)} 2>/dev/null", root=True, timeout=5)
        return Path(local_path).exists() and Path(local_path).stat().st_size > 0

    result = adb.raw(["pull", device_path, local_path], timeout=20)
    return Path(local_path).exists() and Path(local_path).stat().st_size > 0


def extract_wal_from_device(
    adb: ADB,
    db_path: str,
    st: dict,
    local_dir: str = "/tmp/psf_wal",
) -> WalRecoveryResult:
    """Zieht WAL+Journal vom Gerät und analysiert sie."""
    import tempfile
    import os

    root = bool(st.get("is_root"))
    local_dir_path = Path(local_dir)
    local_dir_path.mkdir(parents=True, exist_ok=True)

    db_name  = Path(db_path).name
    wal_dev  = db_path + "-wal"
    jrnl_dev = db_path + "-journal"
    wal_local  = str(local_dir_path / (db_name + "-wal"))
    jrnl_local = str(local_dir_path / (db_name + "-journal"))

    result = WalRecoveryResult(db_path=db_path, wal_path="", journal_path="")

    # WAL ziehen
    wal_ok = _pull_file_via_adb(adb, wal_dev, wal_local, root)
    if wal_ok:
        result.wal_path = wal_local
        wal_result = _read_local_wal(wal_local)
        result.frames_total  = wal_result.frames_total
        result.frames_commit = wal_result.frames_commit
        result.records.extend(wal_result.records)
        result.errors.extend(wal_result.errors)
        result.sha256 = wal_result.sha256
    else:
        result.errors.append(f"WAL nicht verfügbar: {wal_dev}")

    # Journal ziehen
    jrnl_ok = _pull_file_via_adb(adb, jrnl_dev, jrnl_local, root)
    if jrnl_ok:
        result.journal_path = jrnl_local
        jrnl_result = _read_local_journal(jrnl_local)
        result.records.extend(jrnl_result.records)
        result.errors.extend(jrnl_result.errors)

    _dedup_records(result)
    return result


# ---------------------------------------------------------------------------
# Batch über alle Play-Store DBs
# ---------------------------------------------------------------------------

_PLAYSTORE_DBS = [
    "/data/data/com.android.vending/databases/frosting.db",
    "/data/data/com.android.vending/databases/suggestions.db",
    "/data/data/com.android.vending/databases/localappstate.db",
    "/data/data/com.android.vending/databases/purchase.db",
    "/data/data/com.android.vending/databases/experiments.db",
]


def batch_wal_recovery(
    adb: ADB,
    st: dict,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> list[WalRecoveryResult]:
    """Führt WAL/Journal-Recovery für alle bekannten Play-Store DBs durch."""
    import tempfile
    local_dir = "/tmp/psf_wal_batch"
    Path(local_dir).mkdir(parents=True, exist_ok=True)

    results: list[WalRecoveryResult] = []
    for i, db_path in enumerate(_PLAYSTORE_DBS):
        if progress_cb:
            progress_cb(i, len(_PLAYSTORE_DBS), db_path)
        r = extract_wal_from_device(adb, db_path, st, local_dir)
        if r.has_data or r.frames_total > 0:
            results.append(r)

    return results


# ---------------------------------------------------------------------------
# Ausgabe-Formatierung
# ---------------------------------------------------------------------------

_SEP = "─" * 100


def run_wal_recovery(adb: ADB, st: dict, out_dir: str) -> dict:
    """High-level wrapper: zieht alle Play-Store WAL/Journal-Dateien und schreibt Reports.

    Gibt ein dict zurück das action_wal_recovery in main.py erwartet:
      wal_files_found, records_extracted, high_confidence_records,
      unique_packages, output_files
    """
    import os
    import json

    results = batch_wal_recovery(adb, st)

    if not results:
        return {
            "wal_files_found":        0,
            "records_extracted":      0,
            "high_confidence_records": 0,
            "unique_packages":        [],
            "output_files":           [],
        }

    all_records   = [r for res in results for r in res.records]
    high_conf     = [r for r in all_records if r.confidence >= 0.75]
    all_packages  = list(dict.fromkeys(p for res in results for p in res.raw_packages))
    output_files: list[str] = []

    os.makedirs(out_dir, exist_ok=True)

    # Text-Report
    txt_path = os.path.join(out_dir, "wal_recovery.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(format_wal_report(results))
    output_files.append(txt_path)

    # JSON-Export
    json_path = os.path.join(out_dir, "wal_recovery.json")
    export = []
    for res in results:
        entry: dict = {
            "db_path":     res.db_path,
            "wal_path":    res.wal_path,
            "journal_path": res.journal_path,
            "frames_total":  res.frames_total,
            "frames_commit": res.frames_commit,
            "sha256":        res.sha256,
            "packages":      res.raw_packages,
            "urls":          res.raw_urls,
            "timestamps":    res.raw_timestamps,
            "record_count":  len(res.records),
            "errors":        res.errors,
        }
        export.append(entry)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2)
    output_files.append(json_path)

    return {
        "wal_files_found":        len(results),
        "records_extracted":      len(all_records),
        "high_confidence_records": len(high_conf),
        "unique_packages":        all_packages[:20],
        "output_files":           output_files,
    }


def format_wal_report(results: list[WalRecoveryResult]) -> str:
    lines = [
        "═" * 100,
        "  WAL / JOURNAL RECOVERY REPORT",
        "═" * 100,
    ]
    if not results:
        lines += [
            "  Keine WAL/Journal-Dateien gefunden oder kein Root-Zugriff.",
            "  Hinweis: WAL-Recovery erfordert Root-Zugriff auf /data/data/.",
            "═" * 100,
        ]
        return "\n".join(lines)

    for r in results:
        lines += [
            _SEP,
            f"  DB          : {r.db_path}",
            f"  WAL         : {r.wal_path or '(nicht verfügbar)'}",
            f"  Journal     : {r.journal_path or '(nicht verfügbar)'}",
            f"  Frames      : {r.frames_total} total, {r.frames_commit} Commits",
            f"  SHA-256     : {r.sha256[:16]}..." if r.sha256 else "  SHA-256: —",
        ]
        if r.raw_packages:
            lines.append(f"  Pakete      : {len(r.raw_packages)}")
            for pkg in r.raw_packages[:10]:
                lines.append(f"    • {pkg}")
        if r.raw_urls:
            lines.append(f"  URLs        : {len(r.raw_urls)}")
            for url in r.raw_urls[:5]:
                lines.append(f"    • {url[:80]}")
        if r.raw_timestamps:
            lines.append(f"  Timestamps  : {len(r.raw_timestamps)}")
            for ts in sorted(r.raw_timestamps)[:5]:
                lines.append(f"    • {ts}")
        if r.errors:
            lines.append("  Fehler:")
            for e in r.errors:
                lines.append(f"    ✗ {e}")

    lines.append("═" * 100)
    return "\n".join(lines)
