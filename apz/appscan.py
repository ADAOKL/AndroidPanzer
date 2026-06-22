"""Vollständiges App-Inventar mit Architektur-/Verhaltens-Anomalie-Markierung
und interaktivem Mehrfach-Export (Leertaste-Auswahl).

Listet ALLE installierten Apps (System + Drittanbieter). Apps mit Auffälligkeiten
in Architektur/Signatur/Rechten/Verhalten werden ROT markiert – dahinter steht in
Kurzform, WAS auffällig ist und der konkrete VERDACHT. Per Leertaste lassen sich
einzelne Apps auswählen; danach werden die gewählten (oder alle) Apps vollständig
und nachvollziehbar exportiert (APK-Splits + Metadaten + SHA-256, via forensics).

Alles read-only bis zum bewusst bestätigten Export. Keine erfundenen Befunde –
fehlt eine Datenquelle (z.B. Architektur ohne Root/aapt), wird das nicht als
Auffälligkeit gewertet.
"""
from __future__ import annotations

import re

from . import forensics, ui
from .adb import ADB
from .apkscan import (BENIGN_INSTALLERS as _BENIGN_INSTALLERS, DANGEROUS_PERMS,
                      KNOWN_STALKERWARE, STALKER_COMBO, admin_pkgs as _admin_pkgs,
                      comp_pkgs as _comp_pkgs)
from .util import LOG

# Geräte-/Plattform-ABIs, die als „nativ passend" gelten (alles andere ist verdächtig,
# wenn es als primaryCpuAbi einer App auftaucht).
_ARM_ABIS = {"arm64-v8a", "armeabi-v7a", "armeabi"}
_X86_ABIS = {"x86", "x86_64"}

# Paket-Präfixe echter System-/Plattform-Apps. Trägt eine NICHT unter /system bzw.
# nicht als System-Flag laufende App so einen Namen, ist das Maskerade-Verdacht.
_SYSTEMISH_PREFIXES = ("com.android.", "com.google.android.", "android.",
                       "com.samsung.android.", "com.sec.android.", "com.qualcomm.")

# Installer-Werte, die „keine echte Quelle" bedeuten (sideloaded/adb/unbekannt).
# _BENIGN_INSTALLERS, _comp_pkgs, _admin_pkgs kommen geteilt aus apkscan (oben importiert).
_NO_REAL_INSTALLER = ("", "com.android.shell")


# --------------------------------------------------------------------------- #
#  dumpsys-package-Blockparser (ein Dump → pro Paket strukturierte Felder)
# --------------------------------------------------------------------------- #
def _parse_package_blocks(dump: str) -> dict:
    """Zerlegt einen ``dumpsys package``-Dump in {pkg: {feld: wert, ...}}.

    Extrahiert je Paket: primaryCpuAbi, flags, versionName, installer und die
    Menge granted/angeforderter Permissions. Defensiv – fehlende Felder bleiben
    leer, statt den ganzen Scan zu kippen.
    """
    blocks: dict = {}
    # Blockgrenzen: '  Package [com.x] (hash):'
    parts = re.split(r"\n  Package \[([^\]]+)\] \([^)]*\):", "\n" + dump)
    # parts = [vorspann, pkg1, body1, pkg2, body2, ...]
    for i in range(1, len(parts) - 1, 2):
        pkg = parts[i].strip()
        body = parts[i + 1]
        abi = _grep(body, r"primaryCpuAbi=(\S+)")
        flags = set(re.findall(r"\b([A-Z][A-Z0-9_]+)\b", _grep(body, r"\n\s*flags=\[([^\]]*)\]")))
        pflags = set(re.findall(r"\b([A-Z][A-Z0-9_]+)\b", _grep(body, r"privateFlags=\[([^\]]*)\]")))
        perms = set(re.findall(r"android\.permission\.(\w+)", body))
        granted = set(re.findall(r"android\.permission\.(\w+): granted=true", body))
        installer = _grep(body, r"installerPackageName=(\S+)")
        blocks[pkg] = {
            "abi": "" if abi in ("null", "") else abi,
            "flags": flags | pflags,
            "perms": perms,
            "granted": granted,
            "version": _grep(body, r"versionName=(\S+)"),
            "installer": "" if installer in ("null", "") else installer,
            "codePath": _grep(body, r"codePath=(\S+)"),
        }
    return blocks


def _grep(text: str, pat: str) -> str:
    m = re.search(pat, text or "")
    return (m.group(1) if m else "").strip()


# --------------------------------------------------------------------------- #
#  Scan & Anomalie-Erkennung
# --------------------------------------------------------------------------- #
class App:
    """Eine installierte App samt Befunden (Anomalien)."""

    __slots__ = ("pkg", "system", "disabled", "version", "abi", "installer",
                 "code_path", "perms", "anomalies", "score")

    def __init__(self, pkg: str) -> None:
        self.pkg = pkg
        self.system = False
        self.disabled = False
        self.version = ""
        self.abi = ""
        self.installer = ""
        self.code_path = ""
        self.perms: set[str] = set()
        self.anomalies: list[tuple[str, str]] = []   # (was, verdacht)
        self.score = 0

    @property
    def flagged(self) -> bool:
        return bool(self.anomalies)

    @property
    def severity(self) -> str:
        return "crit" if self.score >= 8 else "warn" if self.score >= 4 else "info"


def _detect_anomalies(app: App, info: dict, ctx: dict) -> None:
    """Füllt app.anomalies/app.score anhand Architektur-, Signatur- & Verhaltensindikatoren."""
    short = info.get("perms", set()) | info.get("granted", set())
    flags = info.get("flags", set())

    def add(points: int, was: str, verdacht: str) -> None:
        app.score += points
        app.anomalies.append((was, verdacht))

    # 1) ARCHITEKTUR – native ABI passt nicht zur Geräte-ABI
    abi = app.abi
    if abi:
        dev_abis = ctx["dev_abis"]
        if dev_abis and abi not in dev_abis:
            # Fremd-Architektur (z.B. x86-Lib auf ARM-Gerät) → läuft nur emuliert / untypisch
            arch_class = "x86" if abi in _X86_ABIS else "ARM" if abi in _ARM_ABIS else abi
            add(5, f"Fremd-Architektur {abi} (Gerät: {', '.join(sorted(dev_abis))})",
                f"Native {arch_class}-Bibliotheken passen nicht zur CPU – untergeschobener/"
                "manipulierter Build oder Emulator-Malware möglich")

    # 2) SIGNATUR / HERKUNFT
    inst = app.installer
    sideloaded = (not app.system) and (inst not in _BENIGN_INSTALLERS)
    if sideloaded:
        add(2, f"Sideloaded (Quelle: {inst or 'unbekannt'})",
            "nicht aus einem bekannten App-Store installiert – Herkunft prüfen")
    if "DEBUGGABLE" in flags:
        add(2, "DEBUGGABLE-Flag gesetzt",
            "Test-/Entwickler-Build – in Stores untypisch, erleichtert Manipulation")
    if "TEST_ONLY" in flags:
        add(3, "TEST-ONLY-APK",
            "nur via 'adb install -t' installierbar – kein regulärer Store-Build")
    # Maskerade: System-artiger Name, aber OHNE legitime Quelle als Drittanbieter unter /data.
    # Nur bei FEHLENDER echter Installer-Quelle – GMS-/OMC-gepushte Komponenten sind ausgenommen.
    cp = app.code_path or ""
    if (any(app.pkg.startswith(p) for p in _SYSTEMISH_PREFIXES)
            and not app.system and inst in _NO_REAL_INSTALLER
            and "/system" not in cp and "/product" not in cp):
        add(6, "System-artiger Paketname ohne legitime Installer-Quelle",
            "Tarnung als System-App (Maskerade) – typisches Spyware-Verhalten")

    # 3) BEKANNTE STALKERWARE (für alle Apps – auch als System getarnt)
    if app.pkg in KNOWN_STALKERWARE:
        add(8, "Paketname in Stalkerware-Datenbank",
            "bekannte kommerzielle Überwachungs-/Spionage-App")

    # Heuristiken 4) + 5) gelten NUR für Drittanbieter-Apps. OS-/System-Komponenten
    # (z.B. das Framework-Paket 'android', Launcher, Telefon) halten Rechte-Kombis,
    # Overlay-, Install- und Notification-Rechte legitim → sonst Rot-Flut an False-Positives.
    if not app.system:
        # 4) AKTIVE PRIVILEGIEN (geräteweit gebunden)
        if app.pkg in ctx["a11y"]:
            add(4, "Accessibility-Dienst AKTIV",
                "kann Bildschirm mitlesen & Eingaben protokollieren (Keylogger-Risiko)")
        if app.pkg in ctx["admins"]:
            add(4, "Device-Admin AKTIV",
                "erhöhte Geräteverwaltung – kann Sperren/Wipe erzwingen, schwer entfernbar")
        if app.pkg in ctx["notif"]:
            add(3, "Notification-Listener AKTIV",
                "liest alle Benachrichtigungen mit (z.B. 2FA-Codes, Nachrichten)")

        # 5) RECHTE-KOMBINATIONEN
        if all(c in short for c in STALKER_COMBO):
            add(5, "Stalkerware-Rechte-Kombi (Audio+Standort+SMS+Kontakte)",
                "vollständiges Überwachungsprofil in EINER App")
        if "REQUEST_INSTALL_PACKAGES" in short:
            add(2, "Darf weitere APKs installieren",
                "Dropper-Risiko – kann Schadsoftware nachladen")
        if "SYSTEM_ALERT_WINDOW" in short:
            add(2, "Overlay-Recht (SYSTEM_ALERT_WINDOW)",
                "Tapjacking/Overlay-Phishing möglich (gefälschte Eingabemasken)")
        # versteckt (kein Launcher-Icon) + sensible Rechte
        sens = [p for p in short if p in DANGEROUS_PERMS]
        if app.pkg not in ctx["launchers"] and len(sens) >= 3:
            add(3, f"Kein Launcher-Icon, aber {len(sens)} sensible Rechte",
                "läuft versteckt im Hintergrund – bewusst unsichtbar gehalten")


def scan(adb: ADB, data: dict | None = None) -> list[App]:
    """Sammelt ALLE Apps + Metadaten in wenigen ADB-Aufrufen und bewertet sie."""
    data = data or {}
    # Paketmengen (je ein schneller Aufruf)
    installed = forensics._pkgs(adb)
    system = forensics._pkgs(adb, "-s")
    disabled = forensics._pkgs(adb, "-d")
    launchers = forensics._launcher_pkgs(adb)

    # geräteweite Privilegien-Bindungen (einmalig) – als exakte Paket-Mengen,
    # NICHT als Substring gegen den Gesamt-Dump (sonst matcht 'android' überall).
    a11y = _comp_pkgs(adb.shell("settings get secure enabled_accessibility_services"))
    notif = _comp_pkgs(adb.shell("settings get secure enabled_notification_listeners"))
    admins = _admin_pkgs(adb.shell("dumpsys device_policy 2>/dev/null", timeout=20))

    dev_abis = {a.strip() for a in (data.get("abilist", "") or data.get("abi", "")).split(",") if a.strip()}

    # ein großer dumpsys-Dump → pro Paket geparst (statt hunderter Einzelaufrufe)
    dump = adb.shell("dumpsys package packages", timeout=90) or adb.shell("dumpsys package", timeout=90)
    blocks = {}
    try:
        blocks = _parse_package_blocks(dump)
    except Exception as e:  # noqa: BLE001
        LOG.exception("appscan dumpsys-parse", e)

    ctx = {"a11y": a11y, "notif": notif, "admins": admins,
           "launchers": launchers, "dev_abis": dev_abis}

    apps: list[App] = []
    for pkg in sorted(installed):
        info = blocks.get(pkg, {})
        app = App(pkg)
        app.system = pkg in system
        app.disabled = pkg in disabled
        app.version = info.get("version", "")
        app.abi = info.get("abi", "")
        app.installer = info.get("installer", "")
        app.code_path = info.get("codePath", "")
        app.perms = info.get("perms", set()) | info.get("granted", set())
        _detect_anomalies(app, info, ctx)
        apps.append(app)
    # auffällige zuerst, nach Score sortiert; danach Rest alphabetisch
    apps.sort(key=lambda a: (-a.score, a.pkg))
    return apps


# --------------------------------------------------------------------------- #
#  Darstellung & interaktive Auswahl
# --------------------------------------------------------------------------- #
def _row(app: App, idx: int, selected: bool, cursor: bool) -> str:
    box = f"{ui.BGREEN}[x]{ui.RESET}" if selected else f"{ui.GREY}[ ]{ui.RESET}"
    arrow = f"{ui.NEON}❯{ui.RESET}" if cursor else " "
    tag = (f"{ui.GREY}sys{ui.RESET}" if app.system else f"{ui.BCYAN}app{ui.RESET}")
    if app.disabled:
        tag = f"{ui.GREY}off{ui.RESET}"
    name = app.pkg
    if app.flagged:
        col = ui.BRED if app.severity == "crit" else ui.BYELLOW
        was = app.anomalies[0][0]
        extra = f" {ui.GREY}(+{len(app.anomalies)-1})" if len(app.anomalies) > 1 else ""
        marker = ui.pulse("⚠") if app.severity == "crit" else f"{ui.BYELLOW}⚠{ui.RESET}"
        return (f" {arrow} {box} {marker} {col}{name:<46}{ui.RESET}"
                f"{ui.GREY}│{ui.RESET} {col}{was}{ui.RESET}{extra}")
    return f" {arrow} {box}   {tag} {ui.WHITE}{name:<46}{ui.RESET}{ui.GREY}│ {app.version or '—'}{ui.RESET}"


def _show_details(app: App) -> None:
    ui.clear()
    ui.rule(f"Details · {app.pkg}", ui.CYAN)
    ui.kv("Typ", "System-App" if app.system else "Drittanbieter")
    ui.kv("Version", app.version or "—")
    ui.kv("Architektur (ABI)", app.abi or "—  (keine nativen Libs)")
    ui.kv("Installer", app.installer or "unbekannt/sideloaded")
    ui.kv("Pfad", app.code_path or "—")
    ui.kv("Status", "deaktiviert" if app.disabled else "aktiv")
    print()
    if app.flagged:
        ui.rule(f"Auffälligkeiten ({len(app.anomalies)}) · Score {app.score}", ui.YELLOW)
        for was, verdacht in app.anomalies:
            if app.severity == "crit":
                ui.crit(was)
            else:
                print(f"  {ui.BYELLOW}⚠{ui.RESET} {ui.BOLD}{was}{ui.RESET}")
            print(f"     {ui.GREY}↳ Verdacht: {verdacht}{ui.RESET}")
    else:
        ui.ok("Keine Auffälligkeiten erkannt.")
    ui.pause()


def menu(adb: ADB, dev, st: dict, data: dict | None = None) -> None:
    ui.clear()
    ui.banner(subtitle="🗃  App-Inventar · Architektur-/Spyware-Anomalien · Export")
    probe = adb.shell("echo ok", timeout=8)
    if "ok" not in probe:
        ui.err("Kein ADB-Zugriff auf das Gerät.")
        ui.info("USB-Debugging am Handy AN? RSA-Dialog bestätigt? Danach Hauptmenü '0' (Gerät neu wählen).")
        ui.pause(); return

    ui.info("Scanne alle installierten Apps & prüfe Architektur/Signatur/Rechte … (read-only)")
    apps = scan(adb, data or {})
    if not apps:
        ui.err("Gerät liefert keine Paketliste – ADB-Verbindung prüfen.")
        ui.pause(); return
    flagged = [a for a in apps if a.flagged]
    ui.ok(f"{len(apps)} Apps gescannt · {ui.BRED}{len(flagged)} auffällig{ui.RESET}")
    ui.pause("Weiter zur Auswahlliste (Leertaste wählt) – ENTER")

    help_line = ("↑/↓ bewegen · LEERTASTE wählen · a alle · n keine · i invertieren · "
                 "d Details · f nur Auffällige · ENTER exportieren · q zurück")
    # Vorauswahl: alle auffälligen Apps sind vorgewählt (häufigster Wunsch)
    preselected = {i for i, a in enumerate(apps) if a.flagged}
    sel = _select_loop(apps, preselected, help_line, flagged_only_avail=bool(flagged))
    if sel is None:
        return
    if not sel:
        ui.warn("Nichts ausgewählt."); ui.pause(); return

    chosen = [apps[i].pkg for i in sel]
    ui.clear()
    ui.rule(f"Export · {len(chosen)} App(s)", ui.CYAN)
    for p in chosen[:40]:
        print(f"   {ui.GREY}• {p}{ui.RESET}")
    if len(chosen) > 40:
        print(f"   {ui.GREY}… und {len(chosen)-40} weitere{ui.RESET}")
    ui.info("Export = alle APK-Splits + Metadaten + SHA-256 je App, _INDEX.tsv für VirusTotal-Abgleich.")
    if ui.confirm(f"\n{len(chosen)} App(s) jetzt vollständig & sicher exportieren?", True):
        forensics.export_apps(adb, chosen, st)


def _select_loop(apps: list[App], preselected: set, help_line: str,
                 flagged_only_avail: bool) -> list[int] | None:
    """Auswahlschleife mit Zusatztasten d (Details) und f (Filter auf Auffällige)."""
    if not ui.can_raw_key():
        # Pipe/Test: direkte Mehrfachauswahl ohne Sondertasten
        return ui.multiselect(apps, _row, title="App-Inventar",
                              help_line=help_line, preselected=preselected)
    import shutil

    view = list(range(len(apps)))        # angezeigte Indizes (für Filter f)
    selected = set(preselected)
    cursor = 0
    top = 0
    flagged_only = False
    while True:
        ui.clear()
        ttl = "App-Inventar – Auffällige zuerst"
        if flagged_only:
            ttl += "  (Filter: nur Auffällige)"
        ui.rule(ttl, ui.YELLOW)
        n = len(view)
        if n == 0:
            print(f"  {ui.GREY}(keine Einträge im Filter){ui.RESET}")
        vis = max(8, shutil.get_terminal_size((100, 30)).lines - 8)
        cursor = max(0, min(cursor, n - 1)) if n else 0
        if cursor < top:
            top = cursor
        elif cursor >= top + vis:
            top = cursor - vis + 1
        for vi in range(top, min(n, top + vis)):
            real = view[vi]
            print(_row(apps[real], real, real in selected, vi == cursor))
        more = n - (top + vis)
        if more > 0:
            print(f"  {ui.GREY}… {more} weitere (↓){ui.RESET}")
        print(f"\n  {ui.BOLD}{ui.NEON}{len(selected)}/{len(apps)} gewählt{ui.RESET}   {ui.GREY}{help_line}{ui.RESET}")
        try:
            k = ui.getkey()
        except KeyboardInterrupt:
            return None
        if not n and k not in ("f", "q", "ESC", "a", "n"):
            continue
        if k in ("DOWN", "j"):
            cursor = (cursor + 1) % n if n else 0
        elif k in ("UP", "k"):
            cursor = (cursor - 1) % n if n else 0
        elif k == "PGDN":
            cursor = min(n - 1, cursor + vis)
        elif k == "PGUP":
            cursor = max(0, cursor - vis)
        elif k == "HOME":
            cursor = 0
        elif k == "END":
            cursor = n - 1
        elif k == "SPACE" and n:
            selected.symmetric_difference_update({view[cursor]})
        elif k == "a":
            selected.update(view)
        elif k == "n":
            selected.difference_update(view)
        elif k == "i":
            selected.symmetric_difference_update(view)
        elif k == "d" and n:
            _show_details(apps[view[cursor]])
        elif k == "f" and flagged_only_avail:
            flagged_only = not flagged_only
            view = [i for i, a in enumerate(apps) if a.flagged] if flagged_only else list(range(len(apps)))
            cursor, top = 0, 0
        elif k == "ENTER":
            return sorted(selected)
        elif k in ("q", "ESC"):
            return None
