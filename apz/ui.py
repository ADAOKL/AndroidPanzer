"""Leichtgewichtige Terminal-UI: ANSI-Farben, Banner, Menüs, Tabellen, Pager.

Bewusst ohne externe Abhängigkeiten, damit das Tool überall (auch per SSH /
NetHunter-Terminal) sofort läuft.
"""
from __future__ import annotations

import os
import shutil
import sys

# --- Farb-Erkennung -------------------------------------------------------
_NO_COLOR = bool(os.environ.get("NO_COLOR")) or not sys.stdout.isatty()


def _c(code: str) -> str:
    return "" if _NO_COLOR else code


def _t(r: int, g: int, b: int) -> str:
    """24-Bit-Truecolor-Vordergrund."""
    return _c(f"\033[38;2;{r};{g};{b}m")


RESET = _c("\033[0m")
BOLD = _c("\033[1m")
DIM = _c("\033[2m")
BLINK = _c("\033[5m")       # Pulsieren (ANSI-Blink) für kritische Treffer

# ───────────────  DARK BLACK-GRAY THEME  ───────────────
NEON = _t(180, 190, 200)    # Hauptakzent – helles Grau
NEONB = _t(210, 220, 230)   # noch heller Grau
CRIMSON = _t(150, 160, 170) # mittleres Grau
BLOOD = _t(40, 45, 55)      # sehr dunkles Grau
DARKRED = _t(20, 22, 28)    # fast schwarz

# Chrome (cyan/blau) → graue Töne
CYAN = _t(160, 170, 180)
BCYAN = _t(200, 210, 220)
BLUE = _t(140, 150, 160)
BBLUE = _t(180, 190, 200)
MAGENTA = _t(120, 130, 140)
BMAGENTA = _t(200, 150, 200)  # helles Magenta

# Status – graue Abstufungen
RED = _t(170, 50, 50)       # dunkles Rot (Fehler)
BRED = _t(200, 100, 100)    # helleres Rot
GREEN = _t(80, 160, 100)    # gedämpftes Grün (Erfolg)
BGREEN = _t(120, 200, 140)  # helleres Grün
YELLOW = _t(200, 160, 80)   # gedämpftes Gelb (Warnung)
BYELLOW = _t(230, 190, 120) # helleres Gelb
WHITE = _t(200, 200, 200)   # hell-grau
GREY = _t(100, 110, 120)    # mittleres Grau


def width() -> int:
    return shutil.get_terminal_size((100, 30)).columns


def clear() -> None:
    if not _NO_COLOR:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        print("\n" * 2)


def banner(subtitle: str = "") -> None:
    w = width()
    art = [
        r"   ▄▄▄       ███▄    █ ▓█████▄  ██▀███   ▒█████   ██▓▓█████▄ ",
        r"  ▒████▄     ██ ▀█   █ ▒██▀ ██▌▓██ ▒ ██▒▒██▒  ██▒▓██▒▒██▀ ██▌",
        r"  ▒██  ▀█▄  ▓██  ▀█ ██▒░██   █▌▓██ ░▄█ ▒▒██░  ██▒▒██▒░██   █▌",
        r"  ░██▄▄▄▄██ ▓██▒  ▐▌██▒░▓█▄   ▌▒██▀▀█▄  ▒██   ██░░██░░▓█▄   ▌",
        r"   ▓█   ▓██▒▒██░   ▓██░░▒████▓ ░██▓ ▒██▒░ ████▓▒░░██░░▒████▓ ",
    ]
    # Grau-Schichten: dunkelster Grau → mittlerer → hellster (von oben nach unten)
    glow = [DARKRED, BLOOD, CRIMSON, NEON, NEONB]
    bar = "▬" * (w - 1)
    spike = "▰▱" * ((w - 1) // 2)
    print()
    print(f"{DARKRED}{spike}{RESET}")
    for i, ln in enumerate(art):
        print(f"{BOLD}{glow[i % len(glow)]}{ln}{RESET}")
    print(f"{BLOOD}{bar}{RESET}")
    title = (f"  {BOLD}{NEONB}◆{RESET}  {BOLD}{NEON}A N D R O I D   P A N Z E R{RESET}  "
             f"{BOLD}{NEONB}◆{RESET}   {DIM}{CRIMSON}// total device dominance{RESET}")
    print(title)
    if subtitle:
        print(f"  {CYAN}▸▸{RESET} {BOLD}{WHITE}{subtitle}{RESET}")
    print(f"{BLOOD}{bar}{RESET}")


def rule(title: str = "", color: str = CYAN) -> None:
    w = width() - 1
    if title:
        t = f" {title} "
        pad = w - len(t) - 2
        left = 2
        print(f"{color}{'─'*left}{BOLD}{t}{RESET}{color}{'─'*max(0,pad)}{RESET}")
    else:
        print(f"{color}{'─'*w}{RESET}")


def kv(key: str, val, key_w: int = 26, color=CYAN) -> None:
    val = "—" if val in (None, "") else val
    print(f"  {color}{key:<{key_w}}{RESET}{GREY}│{RESET} {val}")


def info(msg: str) -> None:
    print(f"{BBLUE}ℹ {RESET}{msg}")


def ok(msg: str) -> None:
    print(f"{BGREEN}✔ {RESET}{msg}")


def warn(msg: str) -> None:
    print(f"{BYELLOW}⚠ {RESET}{msg}")


def err(msg: str) -> None:
    print(f"{BRED}✖ {RESET}{msg}")


def pulse(text) -> str:
    """Inline: lässt Text rot pulsieren (für kritische Werte mitten im Satz)."""
    return f"{BLINK}{BOLD}{BRED}{text}{RESET}"


def crit(msg: str) -> None:
    """Kritischer, pulsierend-roter Befund – überall einsetzbar."""
    print(f"{BLINK}{BOLD}{BRED}🚨 {msg}{RESET}")


def danger(msg: str) -> None:
    print(f"{BLINK}{BRED}{BOLD}☠ {msg}{RESET}")


def badge(kind: str) -> str:
    try:
        from . import lang as _lb
        danger_word = _lb.t("badge_danger")
    except Exception:  # noqa: BLE001
        danger_word = "GEFAHR"
    m = {
        "adb": f"{GREEN}[ADB]{RESET}",
        "root": f"{YELLOW}[ROOT]{RESET}",
        "fastboot": f"{MAGENTA}[FASTBOOT]{RESET}",
        "sdr": f"{MAGENTA}[SDR/HW]{RESET}",
        "danger": f"{BRED}[{danger_word}]{RESET}",
        "info": f"{BLUE}[INFO]{RESET}",
        "live": f"{BCYAN}[LIVE]{RESET}",
    }
    return m.get(kind, f"[{kind.upper()}]")


# --- Eingabe --------------------------------------------------------------
def ask(prompt: str, default: str = "") -> str:
    sfx = f" {GREY}[{default}]{RESET}" if default else ""
    try:
        v = input(f"{BOLD}{NEON}☠ ❯{RESET} {prompt}{sfx}: ").strip()
    except EOFError:
        return default
    return v or default


def confirm(prompt: str, default: bool = False) -> bool:
    try:
        from . import lang as _lang
        d = _lang.t("ui_yes_no_true") if default else _lang.t("ui_yes_no_false")
        yes_words = set(_lang.t("ui_yes_answers").split())
    except Exception:  # noqa: BLE001
        d = "J/n" if default else "j/N"
        yes_words = {"j", "ja", "y", "yes"}
    v = ask(f"{prompt} ({d})").lower()
    if not v:
        return default
    return v in yes_words


def pause(msg: str = "") -> None:
    if not msg:
        try:
            from . import lang as _lang
            msg = _lang.t("ui_pause")
        except Exception:  # noqa: BLE001
            msg = "Weiter mit ENTER"
    try:
        input(f"\n{GREY}{msg}…{RESET}")
    except EOFError:
        pass


def pager(text: str, title: str = "") -> None:
    """Gibt langen Text seitenweise aus (einfacher interner Pager)."""
    if title:
        rule(title)
    try:
        from . import lang as _lang
        _no_out = _lang.t("ui_no_output")
    except Exception:  # noqa: BLE001
        _no_out = "(keine Ausgabe)"
    lines = text.splitlines() or [_no_out]
    # Ohne interaktives TTY (Pipe/Test/Redirect): alles am Stück ausgeben – kein
    # input() (das würde blockieren bzw. OSError werfen, z.B. unter pytest).
    if _NO_COLOR or not sys.stdin.isatty():
        print("\n".join(lines))
        return
    h = max(10, shutil.get_terminal_size((100, 30)).lines - 4)
    i = 0
    while i < len(lines):
        chunk = lines[i:i + h]
        print("\n".join(chunk))
        i += h
        if i < len(lines):
            try:
                try:
                    from . import lang as _lp
                    _more_msg = _lp.t("ui_pager_more", done=i, total=len(lines))
                except Exception:  # noqa: BLE001
                    _more_msg = f"-- mehr ({i}/{len(lines)}) -- ENTER=weiter, q=Ende --"
                k = input(f"{GREY}{_more_msg}{RESET}")
            except (EOFError, OSError):
                break
            if k.strip().lower() == "q":
                break


def show_report(body: str, title: str = "", path: str | None = None, note: str = "Bericht") -> None:
    """Zeigt einen Text-Bericht DIREKT im Terminal (seitenweise) und – falls *path*
    gesetzt – einen Speicher-Hinweis. Vereinheitlicht „im Terminal sehen statt
    Datei öffnen". Das Schreiben der Datei macht der Aufrufer."""
    pager(body, title)
    if path:
        ok(f"{note} oben angezeigt · gespeichert: {path}")


def scan_overview(names: list[str], title: str = "Diese Bereiche werden gescannt") -> None:
    """Listet vor einem Scan ALLE Bereiche auf, die durchlaufen werden (1-/2-spaltig)."""
    rule(f"{title} ({len(names)})", YELLOW)
    w = width()
    col = 2 if w >= 90 else 1
    half = (len(names) + 1) // 2 if col == 2 else len(names)
    for i in range(half):
        left = f"{CYAN}{i+1:>2}{RESET} {DIM}{names[i][:40]}{RESET}"
        if col == 2 and i + half < len(names):
            r = names[i + half]
            print(f"  {left:<52} {CYAN}{i+half+1:>2}{RESET} {DIM}{r[:40]}{RESET}")
        else:
            print(f"  {left}")
    print()


def progress(done: int, total: int, label: str = "", width: int = 28) -> None:
    """Einzeiliger %-Fortschrittsbalken (überschreibt sich selbst). Bei done>=total
    wird die Zeile mit Zeilenumbruch abgeschlossen. Ohne TTY: stille No-Op."""
    if _NO_COLOR:
        return
    total = max(1, total)
    frac = min(1.0, max(0.0, done / total))
    filled = int(frac * width)
    bar = f"{BCYAN}{'█' * filled}{GREY}{'░' * (width - filled)}{RESET}"
    sys.stdout.write(f"\r  {bar} {BOLD}{int(frac * 100):3d}%{RESET}  {GREY}{label[:46]}{RESET}\033[K")
    sys.stdout.flush()
    if done >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()


def progress_bytes(done: int, total: int, label: str = "", width: int = 28) -> None:
    """%-Balken für Byte-Mengen (zeigt MB). total<=0 → nur MB-Zähler."""
    if _NO_COLOR:
        return
    mb = done / 1048576
    if total and total > 0:
        frac = min(1.0, done / total)
        filled = int(frac * width)
        bar = f"{BCYAN}{'█' * filled}{GREY}{'░' * (width - filled)}{RESET}"
        line = f"\r  {bar} {BOLD}{int(frac * 100):3d}%{RESET}  {GREY}{mb:.1f}/{total/1048576:.1f} MB {label[:30]}{RESET}\033[K"
        sys.stdout.write(line)
        if done >= total:
            sys.stdout.write("\n")
    else:
        sys.stdout.write(f"\r  {BCYAN}⟳{RESET} {mb:.1f} MB  {GREY}{label[:40]}{RESET}\033[K")
    sys.stdout.flush()


def scan_start(i: int, total: int, label: str) -> None:
    """Zeigt 'läuft gerade' für den aktuellen Bereich (überschreibbar)."""
    if _NO_COLOR:
        return
    sys.stdout.write(f"\r  {GREY}[{i:>2}/{total}]{RESET} {BCYAN}⟳{RESET} {BOLD}{label}{RESET} … ")
    sys.stdout.flush()


def scan_done(i: int, total: int, label: str, ok: bool = True, note: str = "") -> None:
    """Schließt die Zeile des aktuellen Bereichs mit Status ab."""
    sym = f"{BGREEN}✓{RESET}" if ok else f"{BRED}✗{RESET}"
    line = f"  {GREY}[{i:>2}/{total}]{RESET} {sym} {label:<34.34}"
    if note:
        line += f" {GREY}{note}{RESET}"
    if _NO_COLOR:
        print(line)
    else:
        sys.stdout.write("\r" + line + "\033[K\n")
        sys.stdout.flush()


def can_raw_key() -> bool:
    """True, wenn echtes Einzeltasten-Lesen (cbreak) möglich ist (interaktives TTY)."""
    try:
        import termios  # noqa: F401
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:  # noqa: BLE001  – kein POSIX-TTY (Windows/Pipe/Test)
        return False


def getkey() -> str:
    """Liest EINE Taste (cbreak, ohne ENTER) und gibt einen logischen Namen zurück.

    Rückgaben: 'UP' 'DOWN' 'LEFT' 'RIGHT' 'SPACE' 'ENTER' 'ESC' 'HOME' 'END'
    'PGUP' 'PGDN' – sonst das Zeichen selbst (Buchstaben kleingeschrieben).
    Fällt ohne TTY (Pipe/Test) auf zeilenweises ``input`` zurück.
    """
    if not can_raw_key():
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            return "q"
        return {"": "ENTER", " ": "SPACE"}.get(line.strip(), (line.strip()[:1] or "ENTER").lower())
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":                      # Escape-Sequenz (Pfeile/Pos1/Ende)
            seq = sys.stdin.read(1)
            if seq != "[":
                return "ESC"
            code = sys.stdin.read(1)
            if code.isdigit():                # z.B. ESC[5~ (PgUp) – abschließendes '~' konsumieren
                sys.stdin.read(1)
            return {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT",
                    "H": "HOME", "F": "END", "5": "PGUP", "6": "PGDN"}.get(code, "ESC")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if ch in ("\r", "\n"):
        return "ENTER"
    if ch == " ":
        return "SPACE"
    if ch == "\x03":                          # STRG+C
        raise KeyboardInterrupt
    if ch in ("\x7f", "\b"):
        return "BACKSPACE"
    return ch.lower() if ch.isalpha() else ch


def multiselect(items: list, render, title: str = "", help_line: str = "",
                page: int = 0, preselected: set | None = None) -> list[int] | None:
    """Interaktive Mehrfachauswahl mit Cursor + Leertaste.

    *items*  – beliebige Objekte. *render(item, idx, selected, cursor)* liefert die
    fertig formatierte Zeile (eine Zeile pro Eintrag). Steuerung: ↑/↓ bzw. j/k,
    Leertaste = an/aus, a = alle, n = keine, i = invertieren, ENTER = übernehmen,
    q/ESC = abbrechen. Gibt die Indizes der gewählten Einträge zurück (oder None
    bei Abbruch). Ohne TTY: Fallback auf Komma-Indizes per Zeilen-Eingabe.
    """
    n = len(items)
    if n == 0:                                # leere Liste → kein Modulo durch 0 / nichts zu wählen
        return []
    selected = set(preselected or ())
    if not can_raw_key():                     # Pipe/Test: einfache Indexeingabe
        for i, it in enumerate(items):
            print(render(it, i, i in selected, False))
        try:
            from . import lang as _lms
            _ms_fb = _lms.t("ui_multiselect_fallback")
        except Exception:  # noqa: BLE001
            _ms_fb = "Auswahl-Nrn (Komma, 'all', leer=Abbruch)"
        raw = ask(_ms_fb)
        if not raw:
            return None
        if raw.strip().lower() in ("all", "alle", "*"):
            return list(range(n))
        out = []
        for tok in raw.replace(" ", ",").split(","):
            if tok.strip().isdigit():
                k = int(tok) - 1
                if 0 <= k < n:
                    out.append(k)
        return out
    cursor = 0
    vis = max(8, shutil.get_terminal_size((100, 30)).lines - 8)
    top = 0
    while True:
        clear()
        if title:
            rule(title, YELLOW)
        if cursor < top:
            top = cursor
        elif cursor >= top + vis:
            top = cursor - vis + 1
        for i in range(top, min(n, top + vis)):
            print(render(items[i], i, i in selected, i == cursor))
        more = n - (top + vis)
        if more > 0:
            print(f"  {GREY}… {more} weitere (↓){RESET}")
        sel_n = len(selected)
        try:
            from . import lang as _lhl
            _hl_default = _lhl.t("ui_multiselect_help")
            _sel_txt = _lhl.t("ui_selected_count", sel=sel_n, total=n)
        except Exception:  # noqa: BLE001
            _hl_default = "↑/↓ bewegen · LEERTASTE wählen · a alle · n keine · i invertieren · ENTER export · q Abbruch"
            _sel_txt = f"{sel_n}/{n} gewählt"
        hl = help_line or _hl_default
        print(f"\n  {BOLD}{NEON}{_sel_txt}{RESET}   {GREY}{hl}{RESET}")
        try:
            k = getkey()
        except KeyboardInterrupt:
            return None
        if k in ("DOWN", "j"):
            cursor = (cursor + 1) % n
        elif k in ("UP", "k"):
            cursor = (cursor - 1) % n
        elif k == "PGDN":
            cursor = min(n - 1, cursor + vis)
        elif k == "PGUP":
            cursor = max(0, cursor - vis)
        elif k == "HOME":
            cursor = 0
        elif k == "END":
            cursor = n - 1
        elif k == "SPACE":
            selected.symmetric_difference_update({cursor})
        elif k == "a":
            selected = set(range(n))
        elif k == "n":
            selected.clear()
        elif k == "i":
            selected = set(range(n)) - selected
        elif k == "ENTER":
            return sorted(selected)
        elif k in ("q", "ESC"):
            return None


def menu(title: str, entries: list[tuple[str, str]], back_label: str = "Zurück",
         note: str = "") -> str:
    """Zeigt ein nummeriertes Menü. entries = [(key, label), ...].
    Gibt den gewählten key zurück, '0'/'b' => back_label-key 'back', 'q' => 'quit'.
    """
    rule(title, color=YELLOW)
    if note:
        print(f"  {DIM}{note}{RESET}\n")
    for key, label in entries:
        print(f"  {BOLD}{CYAN}{key:>3}{RESET}  {label}")
    try:
        from . import lang as _lmenu
        _quit_lbl = _lmenu.t("ui_quit")
        _back_kw = set(_lmenu.t("ui_back_keywords").split())
    except Exception:  # noqa: BLE001
        _quit_lbl = "Beenden"
        _back_kw = {"zurück", "back"}
    print(f"\n  {BOLD}{GREY}  0{RESET}  {back_label}    {GREY}q{RESET}  {_quit_lbl}")
    choice = ask("Auswahl").lower()
    if choice in {"0", "b"} | _back_kw:
        return "back"
    if choice in ("q", "quit", "exit"):
        return "quit"
    return choice
