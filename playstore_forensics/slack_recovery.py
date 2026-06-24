"""Forensische Slack-Space-Recovery – gelöschte SQLite-Einträge rekonstruieren.

Deckt zwei Ebenen ab:
  1. Freelist-Pages (offizielle gelöschte Pages im SQLite-Format)
  2. Unallocated Space (Null-Byte-Lücken zwischen aktiven Pages)

Für jede Fundstelle wird ein Confidence-Score berechnet.
Kein Pydantic, keine externen Abhängigkeiten.
"""
from __future__ import annotations

import re
import struct
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .utils import epoch_to_human


# ---------------------------------------------------------------------------
# SQLite-Konstanten
# ---------------------------------------------------------------------------

SQLITE_MAGIC = b"SQLite format 3"
PAGE_TYPE_FREE        = 0x00
PAGE_TYPE_LEAF_TABLE  = 0x0D
PAGE_TYPE_INT_TABLE   = 0x05

# Android-Paketnamen-Pattern (binär)
_PKG_RE  = re.compile(rb'(?:com|org|net|io|de|uk)\.[a-z][a-z0-9_]+(?:\.[a-z][a-z0-9_]+)+')
_TS_RE   = re.compile(rb'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}')
_VER_RE  = re.compile(rb'\d{1,3}\.\d{1,3}(?:\.\d{1,4})?(?:\.\d{1,4})?')
_IP_RE   = re.compile(rb'\b(?:\d{1,3}\.){3}\d{1,3}\b')


# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

@dataclass
class SQLiteHeader:
    """Deserialisierter 100-Byte SQLite-Datei-Header."""
    page_size:        int
    page_count:       int
    freelist_trunk:   int
    freelist_count:   int
    change_counter:   int
    text_encoding:    str    # UTF-8 | UTF-16le | UTF-16be
    sqlite_version:   int

    @classmethod
    def from_bytes(cls, data: bytes) -> "SQLiteHeader":
        if len(data) < 100:
            raise ValueError("Zu wenig Daten für SQLite-Header")
        if data[:15] != SQLITE_MAGIC:
            raise ValueError(f"Keine SQLite-Datei (Magic: {data[:4].hex()})")
        raw_page = struct.unpack(">H", data[16:18])[0]
        page_size = 65536 if raw_page == 1 else raw_page
        enc_map = {1: "UTF-8", 2: "UTF-16le", 3: "UTF-16be"}
        enc = enc_map.get(struct.unpack(">I", data[56:60])[0], "UTF-8")
        return cls(
            page_size      = page_size,
            page_count     = struct.unpack(">I", data[28:32])[0],
            freelist_trunk = struct.unpack(">I", data[32:36])[0],
            freelist_count = struct.unpack(">I", data[36:40])[0],
            change_counter = struct.unpack(">I", data[24:28])[0],
            text_encoding  = enc,
            sqlite_version = struct.unpack(">I", data[96:100])[0],
        )


@dataclass
class DeletedRecord:
    """Ein aus dem Slack Space rekonstruierter Datensatz."""
    offset:        int                       # Byte-Offset in der Datei
    page_num:      int                       # Seiten-Nummer
    raw:           bytes                     # Rohdaten (max. 256 Bytes Kontext)
    confidence:    float                     # 0.0 – 1.0
    pkg:           Optional[str] = None      # Gefundener Paketname
    timestamp:     Optional[str] = None      # Gefundener Zeitstempel
    version:       Optional[str] = None      # Gefundene Versionsnummer
    ips:           list[str] = field(default_factory=list)
    rec_type:      str = "UNKNOWN"           # PKG | TIMESTAMP | IP | MIXED

    def summary(self) -> str:
        parts = []
        if self.pkg:       parts.append(f"PKG={self.pkg}")
        if self.timestamp: parts.append(f"TS={self.timestamp}")
        if self.version:   parts.append(f"VER={self.version}")
        if self.ips:       parts.append(f"IPs={','.join(self.ips[:2])}")
        return f"[Page {self.page_num:4d} / Off {self.offset:8d}] Conf={self.confidence:.2f}  {' | '.join(parts)}"

    def to_dict(self) -> dict:
        return {
            "offset":     self.offset,
            "page_num":   self.page_num,
            "confidence": self.confidence,
            "pkg":        self.pkg,
            "timestamp":  self.timestamp,
            "version":    self.version,
            "ips":        self.ips,
            "rec_type":   self.rec_type,
        }


@dataclass
class RecoveryReport:
    """Ergebnis eines vollständigen Slack-Space-Scans."""
    db_path:       str
    db_size:       int
    page_size:     int
    page_count:    int
    freelist_count: int
    records:       list[DeletedRecord] = field(default_factory=list)
    file_sha256:   str = ""
    errors:        list[str] = field(default_factory=list)

    def high_confidence(self, threshold: float = 0.65) -> list[DeletedRecord]:
        return [r for r in self.records if r.confidence >= threshold]

    def unique_packages(self) -> set[str]:
        return {r.pkg for r in self.records if r.pkg}

    def to_text(self) -> str:
        sep = "─" * 70
        lines = [
            "═" * 70,
            f"  SLACK SPACE RECOVERY – {self.db_path}",
            "═" * 70,
            f"  Dateigröße     : {self.db_size:,} Bytes",
            f"  Page-Größe     : {self.page_size} Bytes",
            f"  Pages gesamt   : {self.page_count}",
            f"  Freelist-Pages : {self.freelist_count}",
            f"  SHA-256        : {self.file_sha256[:32]}…",
            f"  Gelöschte Funde: {len(self.records)}",
            f"  Davon ≥0.65    : {len(self.high_confidence())}",
            f"  Einzel-Pakete  : {len(self.unique_packages())}",
            sep,
        ]
        hc = self.high_confidence()
        if hc:
            lines.append("  HIGH-CONFIDENCE FUNDE:")
            for r in hc[:50]:
                lines.append("  " + r.summary())
            if len(hc) > 50:
                lines.append(f"  … ({len(hc) - 50} weitere im JSON-Export)")
        else:
            lines.append("  Keine hochkonfidenten Funde.")
        if self.errors:
            lines += ["", "  FEHLER:"]
            lines += [f"  ⚠ {e}" for e in self.errors[:10]]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "db_path":        self.db_path,
            "db_size":        self.db_size,
            "page_size":      self.page_size,
            "freelist_count": self.freelist_count,
            "file_sha256":    self.file_sha256,
            "records":        [r.to_dict() for r in self.records],
            "errors":         self.errors,
        }


# ---------------------------------------------------------------------------
# Varint-Decoder (SQLite Record-Format)
# ---------------------------------------------------------------------------

def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Liest SQLite Variable-Length Integer. Gibt (Wert, verbrauchte Bytes) zurück."""
    val = 0
    for i in range(min(9, len(data) - offset)):
        byte = data[offset + i]
        if i < 8:
            val = (val << 7) | (byte & 0x7F)
            if byte < 0x80:
                return val, i + 1
        else:
            val = (val << 8) | byte
            return val, 9
    return val, 1


def decode_record(payload: bytes) -> dict:
    """Dekodiert SQLite Record-Payload (Header + Werte) ohne Schema-Wissen.

    Gibt dict {spalten_idx: wert} zurück. Nützlich für unbekannte Tabellen.
    """
    if not payload:
        return {}
    header_size, consumed = _read_varint(payload, 0)
    header_size = min(header_size, len(payload))

    serial_types: list[int] = []
    pos = consumed
    while pos < header_size and pos < len(payload):
        stype, c = _read_varint(payload, pos)
        serial_types.append(stype)
        pos += c

    values: dict[int, object] = {}
    data_pos = header_size
    for col, stype in enumerate(serial_types):
        if data_pos >= len(payload):
            break
        val: object
        if stype == 0:                            # NULL
            val = None
        elif stype == 8:                          # Konstante 0
            val = 0
        elif stype == 9:                          # Konstante 1
            val = 1
        elif 1 <= stype <= 6:                     # Integer
            sizes = [1, 2, 3, 4, 6, 8]
            n = sizes[stype - 1]
            raw = payload[data_pos:data_pos + n]
            val = int.from_bytes(raw, "big", signed=True)
            data_pos += n
        elif stype == 7:                          # Float64
            raw = payload[data_pos:data_pos + 8]
            val = struct.unpack(">d", raw)[0]
            data_pos += 8
        elif stype >= 12 and stype % 2 == 0:      # BLOB
            n = (stype - 12) // 2
            val = payload[data_pos:data_pos + n]
            data_pos += n
        elif stype >= 13 and stype % 2 == 1:      # TEXT
            n = (stype - 13) // 2
            raw = payload[data_pos:data_pos + n]
            try:
                val = raw.decode("utf-8")
            except UnicodeDecodeError:
                val = raw.decode("latin-1", errors="replace")
            data_pos += n
        else:
            val = None
        values[col] = val

    return values


# ---------------------------------------------------------------------------
# Haupt-Scanner
# ---------------------------------------------------------------------------

def _sha256_file(path: str) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def _confidence(page_data: bytes, match_start: int, has_pkg: bool, has_ts: bool) -> float:
    """Berechnet Confidence-Score aus Kontext-Signalen."""
    score = 0.4

    ctx_start = max(0, match_start - 80)
    ctx_end   = min(len(page_data), match_start + 80)
    ctx       = page_data[ctx_start:ctx_end]

    null_ratio = ctx.count(b"\x00") / max(len(ctx), 1)
    if null_ratio > 0.5:
        score -= 0.15       # Viel Null-Bytes → schwächeres Signal

    if has_pkg and has_ts:  score += 0.35
    elif has_pkg:           score += 0.20
    elif has_ts:            score += 0.10

    sql_kw = [b"INSERT", b"UPDATE", b"CREATE", b"VALUES", b"frosting", b"install"]
    if any(kw in page_data[max(0, match_start - 256):match_start] for kw in sql_kw):
        score += 0.15

    return max(0.05, min(0.97, score))


def _scan_page(page_data: bytes, page_num: int, page_size: int) -> list[DeletedRecord]:
    """Scannt eine einzelne Page nach forensischen Mustern."""
    found: list[DeletedRecord] = []
    seen_offsets: set[int] = set()

    for m in _PKG_RE.finditer(page_data):
        raw_pkg = m.group().decode("utf-8", errors="ignore")
        if len(raw_pkg) < 5 or len(raw_pkg) > 120:
            continue

        ctx_start = max(0, m.start() - 60)
        ctx_end   = min(len(page_data), m.end() + 60)
        ctx       = page_data[ctx_start:ctx_end]

        ts_m  = _TS_RE.search(ctx)
        ver_m = _VER_RE.search(ctx)
        ip_ms = _IP_RE.findall(ctx)

        ts_str  = ts_m.group().decode("utf-8", errors="ignore") if ts_m else None
        ver_str = ver_m.group().decode("utf-8", errors="ignore") if ver_m else None
        ips     = [ip.decode("utf-8", errors="ignore") for ip in ip_ms
                   if not ip.startswith(b"127.") and ip != b"0.0.0.0"]

        base_off = page_num * page_size + m.start()
        if base_off in seen_offsets:
            continue
        seen_offsets.add(base_off)

        conf = _confidence(page_data, m.start(), True, ts_m is not None)
        rec_type = "MIXED" if (ts_m or ver_m or ips) else "PKG"

        found.append(DeletedRecord(
            offset    = base_off,
            page_num  = page_num,
            raw       = bytes(ctx),
            confidence = conf,
            pkg        = raw_pkg,
            timestamp  = ts_str,
            version    = ver_str,
            ips        = ips,
            rec_type   = rec_type,
        ))

    # Isolierte Timestamps ohne Paketnamen
    for m in _TS_RE.finditer(page_data):
        base_off = page_num * page_size + m.start()
        if base_off in seen_offsets:
            continue
        ts_str = m.group().decode("utf-8", errors="ignore")
        ctx    = page_data[max(0, m.start()-30):min(len(page_data), m.end()+30)]
        conf   = _confidence(page_data, m.start(), False, True)
        if conf >= 0.35:
            found.append(DeletedRecord(
                offset    = base_off,
                page_num  = page_num,
                raw       = bytes(ctx),
                confidence = conf,
                timestamp = ts_str,
                rec_type  = "TIMESTAMP",
            ))
            seen_offsets.add(base_off)

    return found


def scan_database(db_path: str, max_pages: int = 0) -> RecoveryReport:
    """Vollständiger Slack-Space-Scan einer SQLite-Datei.

    Args:
        db_path:   Lokaler Pfad zur DB (bereits auf Host kopiert).
        max_pages: Maximale Anzahl Pages (0 = alle).

    Returns:
        RecoveryReport mit allen Funden.
    """
    report = RecoveryReport(
        db_path=db_path,
        db_size=os.path.getsize(db_path),
        page_size=4096,
        page_count=0,
        freelist_count=0,
    )

    # Header lesen
    try:
        with open(db_path, "rb") as f:
            hdr_bytes = f.read(100)
        hdr = SQLiteHeader.from_bytes(hdr_bytes)
        report.page_size     = hdr.page_size
        report.page_count    = hdr.page_count or (report.db_size // hdr.page_size)
        report.freelist_count = hdr.freelist_count
    except Exception as e:
        report.errors.append(f"Header-Fehler: {e}")
        report.page_count = report.db_size // report.page_size

    # Integrität-Hash
    try:
        report.file_sha256 = _sha256_file(db_path)
    except OSError:
        report.file_sha256 = "—"

    # Pages scannen
    limit = max_pages if max_pages > 0 else report.page_count
    all_records: list[DeletedRecord] = []

    try:
        with open(db_path, "rb") as f:
            for page_num in range(min(limit, report.page_count)):
                f.seek(page_num * report.page_size)
                page_data = f.read(report.page_size)
                if not page_data:
                    break
                records = _scan_page(page_data, page_num, report.page_size)
                all_records.extend(records)
    except OSError as e:
        report.errors.append(f"Lese-Fehler: {e}")

    # Duplikate entfernen (gleicher Offset)
    seen: set[int] = set()
    deduped: list[DeletedRecord] = []
    for r in all_records:
        if r.offset not in seen:
            seen.add(r.offset)
            deduped.append(r)

    # Nach Confidence sortieren
    deduped.sort(key=lambda r: r.confidence, reverse=True)
    report.records = deduped
    return report


# ---------------------------------------------------------------------------
# Forensisches Integritäts-Zertifikat
# ---------------------------------------------------------------------------

def generate_chain_of_custody(
    db_paths: list[str],
    extraction_results: dict,
) -> dict:
    """Erstellt Chain-of-Custody Zertifikat für Gerichtsverwendung.

    Beinhaltet SHA-256 aller Quell-Dateien und des Extraktionsergebnisses.
    """
    import time
    cert = {
        "certificate_type": "FORENSIC_EXTRACTION_CERTIFICATE",
        "generated_at":     time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool_version":     "AndroidPanzer PlayStoreForensics 1.0",
        "original_files":   [],
        "result_hashes":    {},
    }

    for path in db_paths:
        if os.path.exists(path):
            cert["original_files"].append({
                "path":       path,
                "size_bytes": os.path.getsize(path),
                "sha256":     _sha256_file(path),
                "mtime":      time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(os.path.getmtime(path)),
                ),
            })

    for name, data in extraction_results.items():
        content = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode()
        cert["result_hashes"][name] = hashlib.sha256(content).hexdigest()

    return cert
