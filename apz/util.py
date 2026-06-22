"""Gemeinsame Helfer für alle Module: sichere Shell-Quoting, Eingabe-Validierung,
zentrales Lauf-Logging, robuste Pfade und Hash-Funktionen.

Bewusst ohne externe Abhängigkeiten – nur Standard-Python.
"""
from __future__ import annotations

import atexit
import functools
import hashlib
import os
import re
import shlex
import tarfile
import time

# --------------------------------------------------------------------------- #
#  Projektbasis & Ausgabeverzeichnisse
# --------------------------------------------------------------------------- #
# Robust aus dem Paketpfad abgeleitet (apz/util.py → Projektwurzel), statt einen
# fest verdrahteten HOME-Pfad anzunehmen. Per Umgebungsvariable überschreibbar.
BASE = os.environ.get("PANZER_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def outdir(*parts: str) -> str:
    """Erzeugt (falls nötig) ein Unterverzeichnis unter der Projektbasis und gibt es zurück."""
    p = os.path.join(BASE, *parts)
    os.makedirs(p, exist_ok=True)
    return p


# --------------------------------------------------------------------------- #
#  Shell-Sicherheit  (gegen Command-Injection in adb-shell-Strings)
# --------------------------------------------------------------------------- #
# Android-Paketname; optional ein Prozess-Suffix (":remote") für Komponenten.
_PKG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.]*(:[A-Za-z0-9_.\-]+)?$")
# Android-Permission / Komponenten-Name.
_PERM_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./.\-]*$")


def shq(s) -> str:
    """shlex.quote: bettet einen beliebigen Wert sicher in einen Shell-String ein.

    Ersetzt die unsichere f-String-Interpolation ``f"... {pkg}"`` durch
    ``f"... {shq(pkg)}"``. Liefert immer korrektes Quoting inkl. Leerzeichen/
    Sonderzeichen und verhindert Command-Injection.
    """
    return shlex.quote(str(s))


def valid_pkg(pkg: str) -> bool:
    """True, wenn *pkg* wie ein gültiger Android-Paket-/Prozessname aussieht."""
    return bool(_PKG_RE.match(pkg or ""))


def valid_perm(perm: str) -> bool:
    """True, wenn *perm* wie eine gültige Permission/Komponente aussieht."""
    return bool(_PERM_RE.match(perm or ""))


def clean_pkg(pkg: str) -> str:
    """Gibt den Paketnamen zurück, falls gültig – sonst ``""`` (für stillen Skip)."""
    pkg = (pkg or "").strip()
    return pkg if valid_pkg(pkg) else ""


_COORDS_RE = re.compile(r"^\d+(?:\s+\d+)*$")


def as_int(s, default: int = 0, lo: int | None = None, hi: int | None = None) -> int:
    """Parst Nutzereingabe robust zu int (mit Default & optionalem Clamping).

    Verhindert ``int('')``-/``int('abc')``-Abstürze bei UI-Eingaben und macht die
    anschließende Einbettung in Shell-Kommandos sicher (ein int hat keine
    Shell-Metazeichen)."""
    try:
        v = int(str(s).strip())
    except (TypeError, ValueError):
        v = default
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


def is_coords(s: str) -> bool:
    """True, wenn *s* nur aus Zahlen (durch Leerzeichen getrennt) besteht –
    sichere Form für ``input tap/swipe``-Koordinaten (keine Shell-Metazeichen)."""
    return bool(_COORDS_RE.match((s or "").strip()))


# --------------------------------------------------------------------------- #
#  Zentrales Lauf-Logging
# --------------------------------------------------------------------------- #
class Logger:
    """Schreibt ein Logfile pro Programmlauf nach ``<BASE>/logs/``.

    Forensisch wichtig: Fehler (nicht lesbare Pfade, fehlende Rechte, Timeouts)
    werden protokolliert statt verschluckt – „keine Daten" und „Zugriff
    verweigert" bleiben unterscheidbar.
    """

    def __init__(self) -> None:
        self._fh = None
        self.path: str | None = None

    def _ensure(self) -> None:
        if self._fh is None:
            d = outdir("logs")
            self.path = os.path.join(d, time.strftime("panzer_%Y%m%d_%H%M%S.log"))
            self._fh = open(self.path, "a", encoding="utf-8")
            self._fh.write(f"# Android Panzer Log · gestartet {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._fh.flush()
            atexit.register(self.close)      # Handle bei Programmende sauber schließen

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:  # noqa: BLE001
                pass
            self._fh = None

    def _w(self, level: str, msg: str) -> None:
        try:
            self._ensure()
            self._fh.write(f"{time.strftime('%H:%M:%S')} {level:<5} {msg}\n")  # type: ignore[union-attr]
            self._fh.flush()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001 – Logging darf nie das Programm abbrechen
            pass

    def info(self, msg: str) -> None:
        self._w("INFO", msg)

    def warn(self, msg: str) -> None:
        self._w("WARN", msg)

    def error(self, msg: str) -> None:
        self._w("ERROR", msg)

    def exception(self, ctx: str, exc: BaseException) -> None:
        self._w("ERROR", f"{ctx}: {type(exc).__name__}: {exc}")


LOG = Logger()


def safe(default=None, ctx: str = ""):
    """Decorator: fängt & protokolliert Exceptions und gibt *default* zurück.

    Für Forensik-Teilschritte, die einzeln fehlschlagen dürfen, ohne den ganzen
    Scan abzubrechen – im Gegensatz zu nacktem ``except: pass`` bleibt der Fehler
    aber im Logfile nachvollziehbar.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*a, **k):
            try:
                return fn(*a, **k)
            except Exception as e:  # noqa: BLE001
                LOG.exception(ctx or fn.__name__, e)
                return default
        return wrap
    return deco


def log_call(label: str, fn, *args, default=None, **kwargs):
    """Ruft *fn* auf, protokolliert Exceptions unter *label* und gibt bei Fehler
    *default* zurück. Inline-Variante von :func:`safe`."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        LOG.exception(label, e)
        return default


# --------------------------------------------------------------------------- #
#  Hashing  (Chain-of-Custody / Beweissicherung)
# --------------------------------------------------------------------------- #
def sha256_file(path: str, bufsize: int = 1 << 20) -> str:
    """SHA-256-Hex eines Datei-Inhalts (gepuffert, auch für große Images)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(bufsize), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """SHA-256-Hex eines Strings (UTF-8)."""
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


# --------------------------------------------------------------------------- #
#  Sicherheit: Dateinamen, Archiv-Extraktion (Tar-/Zip-Slip), Downloads
# --------------------------------------------------------------------------- #
def safe_name(s, maxlen: int = 80, default: str = "out") -> str:
    """Sicherer Dateiname-Bestandteil aus beliebigem (Geräte-)String.

    Entfernt Pfadanteile und Sonderzeichen → verhindert Pfad-Traversal, wenn
    Geräte-Daten (Paket-/Kontonamen) in Ausgabedateinamen einfließen."""
    s = os.path.basename(str(s or ""))          # killt /, \, Pfadanteile
    s = re.sub(r"[^A-Za-z0-9._-]", "_", s).strip("._")
    return (s or default)[:maxlen]


def is_within(base: str, target: str) -> bool:
    """True, wenn *target* (aufgelöst) innerhalb von *base* liegt."""
    base = os.path.realpath(base)
    target = os.path.realpath(target)
    return target == base or target.startswith(base + os.sep)


def safe_join(base: str, name: str) -> str:
    """Validiert einen Archiv-Eintragsnamen gegen Tar-/Zip-Slip und liefert den
    sicheren Zielpfad (wirft ValueError bei absolutem Pfad / ``..``-Ausbruch).
    Anders als :func:`safe_extract_member` extrahiert es NICHT – nützlich für
    eigenes Streaming-Entpacken mit Fortschrittsanzeige."""
    norm = os.path.normpath(name)
    if os.path.isabs(name) or name.startswith(("/", "\\")) or norm.startswith(".."):
        raise ValueError(f"Unsicherer Archiv-Pfad (Traversal): {name!r}")
    target = os.path.join(base, norm)
    if not is_within(base, target):
        raise ValueError(f"Archiv-Pfad verlässt Zielordner: {name!r}")
    return target


def safe_extract_member(arch, member, dest: str) -> str:
    """Extrahiert EIN Archiv-Member sicher gegen Tar-/Zip-Slip.

    *arch* = offene tarfile.TarFile / zipfile.ZipFile, *member* = TarInfo oder
    Name (zip). Lehnt absolute Pfade, ``..``-Ausbrüche und (bei tar) Symlinks/
    Hardlinks/Devices ab. Gibt den Zielpfad zurück oder wirft ValueError.
    """
    name = getattr(member, "name", member)
    norm = os.path.normpath(name)
    if os.path.isabs(name) or name.startswith(("/", "\\")) or norm.startswith(".."):
        raise ValueError(f"Unsicherer Archiv-Pfad (Traversal): {name!r}")
    target = os.path.join(dest, norm)
    if not is_within(dest, target):
        raise ValueError(f"Archiv-Pfad verlässt Zielordner: {name!r}")
    # Tar: keine Symlinks/Hardlinks/Geräte-Knoten extrahieren
    for chk in ("issym", "islnk", "isdev"):
        fn = getattr(member, chk, None)
        if callable(fn) and fn():
            raise ValueError(f"Unsicherer Archiv-Eintrag ({chk}): {name!r}")
    if isinstance(arch, tarfile.TarFile):
        try:
            arch.extract(member, dest, filter="data")   # härtet + Python-3.14-konform
        except TypeError:                                # filter erst ab Python 3.12
            arch.extract(member, dest)
    else:
        arch.extract(member, dest)
    return target


def https_only(url: str) -> None:
    """Wirft ValueError, wenn *url* nicht HTTPS ist (Ausnahme: localhost)."""
    from urllib.parse import urlparse
    u = urlparse(url)
    if u.scheme != "https" and (u.hostname not in ("localhost", "127.0.0.1")):
        raise ValueError(f"Unsicherer Download (nicht HTTPS): {url}")


def safe_download(url: str, dst: str, timeout: int = 180, progress=None) -> str:
    """Lädt *url* → *dst* erzwingt HTTPS, lehnt leere/HTML-Fehlerseiten ab und
    gibt die SHA-256 der Datei zurück (zur Integritätsprüfung durch den Operator).
    """
    import urllib.request
    https_only(url)
    req = urllib.request.Request(url, headers={"User-Agent": "panzer"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (https erzwungen)
        data = r.read()
    if not data:
        raise ValueError("Leere Antwort vom Server.")
    if data[:64].lstrip().lower().startswith((b"<!doctype", b"<html")):
        raise ValueError("Server lieferte HTML (Fehlerseite) statt der Binärdatei.")
    with open(dst, "wb") as f:
        f.write(data)
    return sha256_file(dst)


def human_size(n: int) -> str:
    """Bytes → lesbare Größe (1.2 MB)."""
    f = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024 or unit == "TB":
            return f"{f:.0f} {unit}" if unit == "B" else f"{f:.1f} {unit}"
        f /= 1024
    return f"{f:.1f} TB"
