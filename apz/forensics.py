"""Forensischer Deep-Scan.

Sucht gründlich nach:
  • versteckten Apps (kein Launcher-Icon, suspended, hidden, disabled)
  • verborgenen Launcher-Icons (installiert, aber im App-Drawer unsichtbar)
  • Zweit-/Gast-/Work-Profilen (managed profiles, weitere User)
  • sideloaded Apps (Installer ≠ Play Store / unbekannt)
  • deinstallierten Apps mit zurückgebliebenen Datenresten
  • Nutzungs- & Installations-Verlauf (usagestats, Event-Log)
  • verdächtigen Berechtigungen (Accessibility, Device-Admin, Overlay)

Alles read-only über ADB; markiert Auffälligkeiten farblich.
"""
from __future__ import annotations

import hashlib
import os
import re
import time

from . import ui
from .adb import ADB
from .util import shq

EXPORT = os.path.expanduser("~/Schreibtisch/Androidpanzer/app_export")

# Bekannte legitime Installer-Quellen
KNOWN_STORES = {
    "com.android.vending",         # Google Play
    "com.google.android.packageinstaller",
    "com.android.packageinstaller",
    "com.sec.android.app.samsungapps",
    "com.amazon.venezia",
    "com.huawei.appmarket",
    "com.xiaomi.market",
    "com.aurora.store",
    "org.fdroid.fdroid",
}


def _pkgs(adb: ADB, flags: str = "") -> set[str]:
    out = adb.shell(f"pm list packages {flags}".strip())
    res = set()
    for ln in out.splitlines():
        ln = ln.strip()
        if ln.startswith("package:"):
            parts = ln.split("package:", 1)[1].split()   # leerer Wert → kein [0]-IndexError
            if parts:
                res.add(parts[0])
    return res


def _launcher_pkgs(adb: ADB) -> set[str]:
    """Apps mit sichtbarem Launcher-Icon (MAIN/LAUNCHER-Activity)."""
    out = adb.shell("cmd package query-activities --brief "
                    "-a android.intent.action.MAIN -c android.intent.category.LAUNCHER")
    pkgs = set(re.findall(r"([a-zA-Z0-9_.]+)/", out))
    if not pkgs:  # Fallback für ältere Androids
        out = adb.shell("pm dump-profiles 2>/dev/null; cmd package resolve-activity "
                        "-a android.intent.action.MAIN -c android.intent.category.LAUNCHER")
        pkgs = set(re.findall(r"([a-zA-Z0-9_.]+)/", out))
    return pkgs


def _installer(adb: ADB, pkg: str) -> str:
    out = adb.shell(f"pm list packages -i {shq(pkg)}")
    m = re.search(r"installer=(\S+)", out)
    inst = m.group(1) if m else "null"
    return "" if inst in ("null", "") else inst


def _users(adb: ADB) -> list[dict]:
    out = adb.shell("pm list users")
    users = []
    for m in re.finditer(r"UserInfo\{(\d+):([^:]*):([0-9a-fA-Fx]+)\}\s*(\w*)", out):
        uid, name, flags, state = m.groups()
        users.append({"id": uid, "name": name, "flags": flags, "running": state})
    if not users:  # Fallback
        for ln in out.splitlines():
            mm = re.search(r"\{(\d+):([^:]*):", ln)
            if mm:
                users.append({"id": mm.group(1), "name": mm.group(2), "flags": "?", "running": ""})
    return users


def deep_scan(adb: ADB, st: dict | None = None) -> None:
    st = st or {}
    ui.clear()
    ui.banner(subtitle="Forensischer Deep-Scan")
    ui.info("Scanne Pakete, Profile, Icons & Verlauf … (read-only)\n")
    report: list[str] = []

    # 1) Pakete einsammeln -------------------------------------------------
    ui.rule("1 · Paket-Inventar", ui.CYAN)
    third = _pkgs(adb, "-3")                 # Drittanbieter (installiert)
    disabled = _pkgs(adb, "-d")              # deaktiviert
    enabled = _pkgs(adb, "-e")               # aktiviert
    all_incl_uninstalled = _pkgs(adb, "-u")  # inkl. deinstalliert-mit-Datenrest
    system = _pkgs(adb, "-s")
    installed = _pkgs(adb)
    ui.kv("Installierte Pakete gesamt", len(installed))
    ui.kv("davon Drittanbieter", len(third))
    ui.kv("davon System", len(system))
    ui.kv("aktiviert", len(enabled))
    ui.kv("deaktiviert", f"{ui.BYELLOW}{len(disabled)}{ui.RESET}")
    ui.kv("inkl. deinstalliert (Datenrest)", len(all_incl_uninstalled))

    # 2) Versteckte Launcher-Icons ----------------------------------------
    ui.rule("2 · Verborgene Icons (App ohne Launcher-Eintrag)", ui.CYAN)
    launchers = _launcher_pkgs(adb)
    hidden_icon = sorted(p for p in third if p not in launchers and p not in disabled)
    if hidden_icon:
        ui.warn(f"{len(hidden_icon)} Drittanbieter-Apps OHNE sichtbares Icon im App-Drawer:")
        for p in hidden_icon:
            inst = _installer(adb, p)
            tag = f"  {ui.GREY}← {inst}{ui.RESET}" if inst else f"  {ui.BRED}← Installer unbekannt{ui.RESET}"
            print(f"     {ui.BYELLOW}•{ui.RESET} {p}{tag}")
        report.append(f"Verborgene Icons: {len(hidden_icon)}")
    else:
        ui.ok("Keine Drittanbieter-App ohne Launcher-Icon gefunden.")

    # 3) Suspended / hidden Flags aus dumpsys -----------------------------
    ui.rule("3 · Suspendierte / versteckte Apps (Paket-Flags)", ui.CYAN)
    pkgdump = adb.shell("dumpsys package", timeout=40)
    suspended = sorted(set(re.findall(r"Package \[([\w.]+)\][^\n]*\n(?:.*\n)*?\s*suspended=true", pkgdump)))
    flagged = _flagged_packages(pkgdump)
    if suspended:
        ui.warn(f"Suspendierte Apps ({len(suspended)}): {', '.join(suspended[:25])}"
                + (" …" if len(suspended) > 25 else ""))
        report.append(f"Suspendiert: {len(suspended)} ({', '.join(suspended[:40])})")
    if flagged:
        for kind, pkgs in flagged.items():
            if pkgs:
                ui.warn(f"{kind}: {', '.join(sorted(pkgs)[:25])}" + (" …" if len(pkgs) > 25 else ""))
                report.append(f"{kind}: {len(pkgs)}")
    if not suspended and not flagged:
        ui.ok("Keine suspendierten/versteckten Paket-Flags auffällig.")

    # 4) Zweit-/Gast-/Work-Profile ----------------------------------------
    ui.rule("4 · Nutzerprofile (Zweit-/Gast-/Work-Profil)", ui.CYAN)
    users = _users(adb)
    if len(users) <= 1:
        ui.ok(f"Nur ein Nutzerprofil (id {users[0]['id'] if users else '0'}) – keine versteckten Profile.")
    else:
        ui.warn(f"{len(users)} Nutzerprofile gefunden:")
        for u in users:
            kind = _user_kind(u["flags"])
            print(f"     {ui.BYELLOW}•{ui.RESET} id={u['id']:<3} {u['name'] or '(ohne Name)':<18} "
                  f"{ui.GREY}flags={u['flags']} {kind}{ui.RESET}")
        report.append(f"Profile: {len(users)}")
    # Managed/Work-Profil-Hinweis
    mp = adb.shell("dumpsys device_policy | grep -iE 'Profile Owner|Device Owner|managed' | head")
    if mp.strip():
        ui.warn("Geräte-/Profil-Richtlinien aktiv (MDM/Work-Profil):")
        ui.pager(mp, "") if len(mp.splitlines()) > 6 else print("     " + mp.replace("\n", "\n     "))

    # 5) Sideloaded Apps ---------------------------------------------------
    ui.rule("5 · Sideloaded / unbekannte Herkunft", ui.CYAN)
    sideloaded = []
    for p in sorted(third):
        inst = _installer(adb, p)
        if inst not in KNOWN_STORES:
            sideloaded.append((p, inst or "—"))
    if sideloaded:
        ui.warn(f"{len(sideloaded)} App(s) NICHT aus einem bekannten Store installiert:")
        for p, inst in sideloaded[:40]:
            col = ui.BRED if inst == "—" else ui.GREY
            print(f"     {ui.BYELLOW}•{ui.RESET} {p}  {col}← {inst}{ui.RESET}")
        if len(sideloaded) > 40:
            print(f"     {ui.GREY}… und {len(sideloaded)-40} weitere{ui.RESET}")
        report.append(f"Sideloaded: {len(sideloaded)}")
    else:
        ui.ok("Alle Drittanbieter-Apps stammen aus bekannten Stores.")

    # 6) Deinstalliert mit Datenrest --------------------------------------
    ui.rule("6 · Deinstalliert – aber Datenreste vorhanden", ui.CYAN)
    leftover = sorted(all_incl_uninstalled - installed)
    if leftover:
        ui.warn(f"{len(leftover)} Paket(e) deinstalliert, aber noch im System registriert (Datenrest):")
        for p in leftover[:40]:
            print(f"     {ui.BYELLOW}•{ui.RESET} {p}")
        report.append(f"Datenreste: {len(leftover)}")
    else:
        ui.ok("Keine deinstallierten Pakete mit Datenresten.")

    # 7) Verdächtige Berechtigungen ---------------------------------------
    ui.rule("7 · Hochsensible Rechte (Accessibility / Device-Admin / Overlay)", ui.CYAN)
    acc = adb.shell("settings get secure enabled_accessibility_services")
    admins = adb.shell("dpm list-owners 2>/dev/null") + "\n" + adb.shell(
        "dumpsys device_policy | grep -iE 'admin=ComponentInfo' | head")
    if acc and acc not in ("null", ""):
        ui.crit("Aktive Accessibility-Dienste (oft von Spyware/Keyloggern genutzt):")
        for svc in acc.split(":"):
            if svc.strip():
                print("     " + ui.pulse(f"• {svc.strip()}"))
        report.append("Accessibility-Dienste aktiv")
    else:
        ui.ok("Keine Accessibility-Dienste aktiv.")
    if re.search(r"ComponentInfo|admin=", admins):
        ui.crit("Aktive Device-Admin-Apps:")
        for m in re.findall(r"ComponentInfo\{([^}]+)\}", admins):
            print("     " + ui.pulse(f"• {m}"))
        report.append("Device-Admin aktiv")

    # 8) Nutzungs- & Installationsverlauf ---------------------------------
    ui.rule("8 · Verlauf (zuletzt genutzt / installiert)", ui.CYAN)
    recent = _recent_usage(adb)
    if recent:
        ui.info("Zuletzt aktive Apps (usagestats, letzte Einträge):")
        for line in recent[:12]:
            print(f"     {ui.GREY}{line}{ui.RESET}")
    events = adb.shell("logcat -d -b events -t 400 | grep -iE 'package|pm_|install' | tail -n 15")
    if events.strip():
        ui.info("Letzte Paket-Events im Event-Log (Install/Remove/Update):")
        for line in events.splitlines()[-12:]:
            print(f"     {ui.GREY}{line[:120]}{ui.RESET}")

    # 9) Risiko-Bewertung aller Drittanbieter-Apps ------------------------
    ui.rule("9 · Risiko-Bewertung (gefährliche Rechte-Kombis)", ui.CYAN)
    sideloaded_pkgs = {p for p, _ in sideloaded}
    risky = _score_apps(adb, third, set(hidden_icon), sideloaded_pkgs, acc, admins)
    if risky:
        ui.warn(f"{len(risky)} App(s) mit Risiko-Indikatoren (sortiert nach Score):")
        for r in risky[:25]:
            badge = (ui.pulse(f"[{r['score']:>2}]") if r["score"] >= 6
                     else f"{ui.BYELLOW}[{r['score']:>2}]{ui.RESET}" if r["score"] >= 3
                     else f"{ui.GREY}[{r['score']:>2}]{ui.RESET}")
            pk = ui.pulse(r["pkg"]) if r["score"] >= 6 else r["pkg"]
            print(f"     {badge} {pk:<45} {ui.GREY}{', '.join(r['reasons'][:4])}{ui.RESET}")
        report.append(f"Risiko-Apps: {len(risky)}")
    else:
        ui.ok("Keine Apps mit auffälliger Rechte-Kombination.")

    # Zusammenfassung ------------------------------------------------------
    print()
    ui.rule("Zusammenfassung", ui.YELLOW)
    if report:
        ui.warn("Auffälligkeiten: " + "  |  ".join(report))
    else:
        ui.ok("Keine Auffälligkeiten – Gerät wirkt sauber.")
    if ui.confirm("Vollständigen Bericht als Datei speichern?", False):
        _save_report(adb, hidden_icon, sideloaded, leftover, users, report)

    # ── Interaktives Aktions-Menü NACH dem Scan ──
    _post_scan(adb, st, risky, sorted(set(hidden_icon) | sideloaded_pkgs))


def _flagged_packages(pkgdump: str) -> dict:
    out = {"suspended=true": set(), "hidden=true": set(), "stopped=true": set(), "instant=true": set()}
    cur = None
    for ln in pkgdump.splitlines():
        m = re.match(r"\s*Package \[([\w.]+)\]", ln)
        if m:
            cur = m.group(1)
            continue
        if cur:
            for flag in out:
                if flag in ln:
                    out[flag].add(cur)
    return {k: v for k, v in out.items() if v}


def _user_kind(flags: str) -> str:
    try:
        f = int(flags, 16)
    except ValueError:
        return ""
    parts = []
    if f & 0x00000020:
        parts.append("MANAGED/WORK")
    if f & 0x00000004:
        parts.append("GUEST")
    if f & 0x00000008:
        parts.append("RESTRICTED")
    if f & 0x00000001:
        parts.append("PRIMARY")
    if f & 0x00000400:
        parts.append("CLONE")
    return ("→ " + ", ".join(parts)) if parts else ""


def _recent_usage(adb: ADB) -> list[str]:
    out = adb.shell("dumpsys usagestats | grep -iE 'package=|lastTimeUsed' | tail -n 40")
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[-24:]


def _save_report(adb: ADB, hidden_icon, sideloaded, leftover, users, summary) -> None:
    import os
    fn = os.path.expanduser("~/Schreibtisch/Androidpanzer/forensic_scan.txt")
    body = (
        "=== ANDROID PANZER · Forensischer Deep-Scan ===\n\n"
        "Zusammenfassung: " + ("; ".join(summary) or "keine Auffälligkeiten") + "\n\n"
        f"[Verborgene Icons] ({len(hidden_icon)})\n" + "\n".join(hidden_icon) + "\n\n"
        f"[Sideloaded] ({len(sideloaded)})\n"
        + "\n".join(f"{p}  <- {i}" for p, i in sideloaded) + "\n\n"
        f"[Datenreste deinstalliert] ({len(leftover)})\n" + "\n".join(leftover) + "\n\n"
        f"[Profile] ({len(users)})\n"
        + "\n".join(f"id={u['id']} {u['name']} flags={u['flags']}" for u in users) + "\n")
    try:
        with open(fn, "w", encoding="utf-8") as f:
            f.write(body)
    except OSError as e:
        ui.err(str(e)); return
    ui.show_report(body, "Forensischer Deep-Scan · Bericht", fn, note="Deep-Scan-Bericht")


# ====================================================================== #
#  App-Export (versteckte / verdächtige Apps komplett extrahieren)
# ====================================================================== #
def menu(adb: ADB, st: dict) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🔎 Forensik: Deep-Scan & App-Export")
        ch = ui.menu("Aktionen", [
            ("1", "Forensischer Deep-Scan (versteckte Apps/Profile/Icons)"),
            ("2", "📦 App-Export – komplette APKs + Info sichern"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            deep_scan(adb, st)
        elif ch == "2":
            export_menu(adb, st)


def export_menu(adb: ADB, st: dict) -> None:
    ui.clear()
    ui.rule("App-Export", ui.CYAN)
    # Verbindung prüfen, bevor wir „keine Apps" melden
    probe = adb.shell("echo ok", timeout=8)
    if "ok" not in probe:
        ui.err("Kein ADB-Zugriff auf das Gerät.")
        ui.info("Prüfe: USB-Debugging am Handy AN? RSA-Dialog bestätigt? Kabel/Modus 'Dateiübertragung'?")
        ui.info("Danach im Hauptmenü '0' (Gerät neu wählen).")
        ui.pause(); return
    ui.info("Welche Apps exportieren?")
    ch = ui.menu("Auswahl", [
        ("1", "Versteckte (ohne Launcher-Icon)"),
        ("2", "Sideloaded (unbekannte Herkunft)"),
        ("3", "Suspendiert/gestoppt/hidden (Paket-Flags)"),
        ("4", "Einzelne App nach Paketname"),
        ("5", "ALLE Drittanbieter-Apps"),
    ], back_label="Zurück")
    if ch in ("back", "quit"):
        return
    pkgs: list[str] = []
    if ch == "1":
        third = _pkgs(adb, "-3")
        launchers = _launcher_pkgs(adb)
        disabled = _pkgs(adb, "-d")
        pkgs = sorted(p for p in third if p not in launchers and p not in disabled)
    elif ch == "2":
        for p in sorted(_pkgs(adb, "-3")):
            if _installer(adb, p) not in KNOWN_STORES:
                pkgs.append(p)
    elif ch == "3":
        flagged = _flagged_packages(adb.shell("dumpsys package", timeout=40))
        pkgs = sorted(set().union(*flagged.values())) if flagged else []
    elif ch == "4":
        p = ui.ask("Paketname")
        pkgs = [p] if p else []
    elif ch == "5":
        pkgs = sorted(_pkgs(adb, "-3"))
    if not pkgs:
        # Kategorie 5 = ALLE Drittanbieter: leer ⇒ fast sicher Verbindungsproblem
        if ch == "5" and not _pkgs(adb):
            ui.err("Gerät liefert keine Paketliste – ADB-Verbindung weg "
                   "(USB-Debugging am Handy prüfen).")
        else:
            ui.warn("Keine App in dieser Kategorie.")
        ui.pause(); return
    ui.info(f"{len(pkgs)} App(s) zum Export:")
    for p in pkgs[:30]:
        print(f"   {ui.GREY}• {p}{ui.RESET}")
    if len(pkgs) > 30:
        print(f"   {ui.GREY}… und {len(pkgs)-30} weitere{ui.RESET}")
    if ui.confirm(f"\n{len(pkgs)} App(s) komplett exportieren?", True):
        export_apps(adb, pkgs, st)


def export_apps(adb: ADB, pkgs: list[str], st: dict | None = None) -> None:
    st = st or {}
    with_data = False
    if st.get("is_root"):
        with_data = ui.confirm("Auch App-DATEN exportieren (/data/data, Root)?", False)
    base = os.path.join(EXPORT, f"export_{int(time.time())}")
    os.makedirs(base, exist_ok=True)
    ui.info(f"\nExportiere nach: {base}\n")
    index = ["Paket\tVersion\tInstaller\tAPKs\tGröße(KB)\tSHA256(base.apk)"]
    ok = 0
    for i, pkg in enumerate(pkgs, 1):
        print(f"  {ui.BOLD}[{i}/{len(pkgs)}]{ui.RESET} {pkg}")
        paths = [ln.split("package:", 1)[1].strip()
                 for ln in adb.shell(f"pm path {shq(pkg)}").splitlines() if "package:" in ln]
        if not paths:
            print(f"     {ui.GREY}↳ kein APK-Pfad (deaktiviert?){ui.RESET}")
            continue
        pdir = os.path.join(base, pkg)
        os.makedirs(pdir, exist_ok=True)
        total = 0
        base_apk_local = ""
        for ap in paths:
            local = os.path.join(pdir, os.path.basename(ap))
            adb.raw(["pull", ap, local], timeout=180)
            if os.path.isfile(local):
                total += os.path.getsize(local)
                if os.path.basename(ap) == "base.apk" or not base_apk_local:
                    base_apk_local = local
        sha = _sha_file(base_apk_local) if base_apk_local else ""
        # Info-Report je App
        info = _app_info(adb, pkg)
        ver = re.search(r"versionName=(\S+)", info)
        inst = re.search(r"installerPackageName=(\S+)", info) or re.search(r"installer=(\S+)", info)
        with open(os.path.join(pdir, "INFO.txt"), "w", encoding="utf-8") as f:
            f.write(f"# {pkg}\nSHA-256(base.apk): {sha}\n"
                    f"(→ VirusTotal: https://www.virustotal.com/gui/file/{sha})\n\n{info}")
        # App-Daten mit Root
        if with_data:
            tmp = f"/sdcard/.{pkg}.data.tar"
            adb.shell(f"tar -cf {shq(tmp)} /data/data/{shq(pkg)} 2>/dev/null; chmod 666 {shq(tmp)}",
                      root=True, timeout=120)
            adb.raw(["pull", tmp, os.path.join(pdir, "appdata.tar")], timeout=300)
            adb.shell(f"rm -f {shq(tmp)}", root=True)
        print(f"     {ui.BGREEN}↳ {len(paths)} APK(s), {total//1024} KB, sha256 {sha[:16]}…{ui.RESET}")
        index.append(f"{pkg}\t{ver.group(1) if ver else '?'}\t"
                     f"{inst.group(1) if inst else '?'}\t{len(paths)}\t{total//1024}\t{sha}")
        ok += 1
    with open(os.path.join(base, "_INDEX.tsv"), "w", encoding="utf-8") as f:
        f.write("\n".join(index))
    print()
    ui.ok(f"{ok}/{len(pkgs)} App(s) exportiert → {base}")
    ui.info("Übersicht: _INDEX.tsv  (mit SHA-256 für VirusTotal-Abgleich)")
    ui.pause()


def _app_info(adb: ADB, pkg: str) -> str:
    out = adb.shell(
        f"dumpsys package {pkg} | grep -E "
        f"'versionName|versionCode|installerPackageName|firstInstallTime|lastUpdateTime|"
        f"targetSdk|flags=|privateFlags|requested permissions|granted=true|"
        f"Activity|Service|Receiver' | head -n 80")
    return out or "(keine Detailinfo)"


def _sha_file(path: str) -> str:
    if not path or not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ====================================================================== #
#  Risiko-Scoring & Post-Scan-Aktionen
# ====================================================================== #
_DANGEROUS_PERMS = {
    "READ_SMS": 2, "RECEIVE_SMS": 2, "SEND_SMS": 2, "READ_CALL_LOG": 2,
    "PROCESS_OUTGOING_CALLS": 2, "RECORD_AUDIO": 2, "CAMERA": 1,
    "ACCESS_FINE_LOCATION": 1, "ACCESS_BACKGROUND_LOCATION": 2, "READ_CONTACTS": 1,
    "READ_PHONE_STATE": 1, "REQUEST_INSTALL_PACKAGES": 2, "SYSTEM_ALERT_WINDOW": 2,
    "PACKAGE_USAGE_STATS": 2, "QUERY_ALL_PACKAGES": 1, "READ_EXTERNAL_STORAGE": 1,
}


def _score_apps(adb: ADB, third: set, hidden: set, sideloaded: set,
                acc: str, admins: str) -> list[dict]:
    """Bewertet jede Drittanbieter-App nach Risiko-Indikatoren."""
    from .apkscan import admin_pkgs, comp_pkgs
    acc_set = comp_pkgs(acc)        # exakte Paket-Mengen statt Substring-Test (sonst False-Positives)
    adm_set = admin_pkgs(admins)
    out = []
    for pkg in sorted(third):
        d = adb.shell(f"dumpsys package {shq(pkg)} | grep -E "
                      f"'granted=true|DEBUGGABLE|BOOT_COMPLETED|installerPackageName' | head -n 60")
        granted = set(re.findall(r"android\.permission\.(\w+)", d))
        score, reasons = 0, []
        for perm, w in _DANGEROUS_PERMS.items():
            if perm in granted:
                score += w
        danger_perms = [p for p in _DANGEROUS_PERMS if p in granted]
        if len(danger_perms) >= 4:
            reasons.append(f"{len(danger_perms)} sensible Rechte")
        if pkg in sideloaded:
            score += 2; reasons.append("sideloaded")
        if pkg in hidden:
            score += 2; reasons.append("kein Icon")
        if "DEBUGGABLE" in d:
            score += 2; reasons.append("debuggable")
        if "BOOT_COMPLETED" in d:
            score += 1; reasons.append("Autostart")
        if "SYSTEM_ALERT_WINDOW" in granted:
            reasons.append("Overlay")
        if pkg in acc_set:
            score += 3; reasons.append("Accessibility!")
        if pkg in adm_set:
            score += 3; reasons.append("Device-Admin!")
        if score >= 2:
            out.append({"pkg": pkg, "score": score, "reasons": reasons or ["Rechte"]})
    out.sort(key=lambda x: -x["score"])
    return out


def _post_scan(adb: ADB, st: dict, risky: list[dict], suspicious: list[str]) -> None:
    """Aktions-Menü nach dem Scan – Apps gezielt bearbeiten."""
    while True:
        print()
        ui.rule("Aktionen nach dem Scan", ui.YELLOW)
        ranked = risky or [{"pkg": p, "score": 0, "reasons": ["verdächtig"]} for p in suspicious]
        for i, r in enumerate(ranked[:30], 1):
            line_badge = (ui.pulse(f"[{r['score']:>2}]") if r["score"] >= 6
                          else f"{ui.BYELLOW}[{r['score']:>2}]{ui.RESET}" if r["score"] >= 3
                          else f"{ui.WHITE}[{r['score']:>2}]{ui.RESET}")
            pk = ui.pulse(r["pkg"]) if r["score"] >= 6 else r["pkg"]
            print(f"  {ui.CYAN}{i:>2}{ui.RESET} {line_badge} {pk}")
        print(f"\n  {ui.BOLD}Bulk:{ui.RESET}  {ui.CYAN}E{ui.RESET} alle exportieren   "
              f"{ui.CYAN}X{ui.RESET} alle sideloaded deaktivieren   {ui.CYAN}A{ui.RESET} KI-Gesamtanalyse   "
              f"{ui.CYAN}0{ui.RESET} zurück")
        sel = ui.ask("App-Nr oder Bulk-Aktion").lower()
        if sel in ("0", "", "back", "q"):
            return
        if sel == "e":
            export_apps(adb, [r["pkg"] for r in ranked], st); continue
        if sel == "x":
            for r in ranked:
                if "sideloaded" in r["reasons"]:
                    adb.shell(f"pm disable-user --user 0 {shq(r['pkg'])}")
            ui.ok("Alle sideloaded Apps deaktiviert."); ui.pause(); continue
        if sel == "a":
            _ai_overview(adb, ranked); continue
        try:
            app = ranked[int(sel) - 1]["pkg"]
        except (ValueError, IndexError):
            continue
        _app_action_menu(adb, st, app)


def _app_action_menu(adb: ADB, st: dict, pkg: str) -> None:
    while True:
        ui.clear()
        ui.rule(f"App: {pkg}", ui.CYAN)
        ch = ui.menu("Aktion", [
            ("1", "🔍 Details/Manifest/Rechte anzeigen"),
            ("2", "📦 Komplett exportieren (APK + Info)"),
            ("3", "⏸ Deaktivieren (disable-user)"),
            ("4", "🗑 Deinstallieren (für Nutzer 0)"),
            ("5", "⏹ Force-Stop"),
            ("6", "🚫 Alle Runtime-Rechte entziehen"),
            ("7", "🤖 Von der KI bewerten lassen"),
            ("8", "📂 In den Vordergrund starten"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            ui.pager(_app_info(adb, pkg), pkg); ui.pause()
        elif ch == "2":
            export_apps(adb, [pkg], st)
        elif ch == "3":
            ui.info(adb.shell(f"pm disable-user --user 0 {shq(pkg)}") or "deaktiviert"); ui.pause()
        elif ch == "4":
            if ui.confirm(f"{pkg} für Nutzer 0 deinstallieren?", False):
                ui.info(adb.shell(f"pm uninstall -k --user 0 {shq(pkg)}") or "ok"); ui.pause()
        elif ch == "5":
            ui.info(adb.shell(f"am force-stop {shq(pkg)}") or "gestoppt"); ui.pause()
        elif ch == "6":
            perms = re.findall(r"(android\.permission\.\w+): granted=true",
                               adb.shell(f"dumpsys package {shq(pkg)} | grep granted=true"))
            for p in perms:
                adb.shell(f"pm revoke {shq(pkg)} {shq(p)}")
            ui.ok(f"{len(perms)} Rechte entzogen."); ui.pause()
        elif ch == "7":
            _ai_one(adb, pkg)
        elif ch == "8":
            adb.shell(f"monkey -p {shq(pkg)} -c android.intent.category.LAUNCHER 1"); ui.pause()


def _ai_one(adb: ADB, pkg: str) -> None:
    try:
        from . import aishell
        if not aishell._ollama_up():
            ui.warn("KI (ollama) nicht erreichbar – 'ollama serve' starten."); ui.pause(); return
        model = aishell._pick_model()
        info = _app_info(adb, pkg)
        ans = aishell._gen(model,
            f"Android-Paket: {pkg}\n\nInfo:\n{info[:3500]}\n\n"
            "Ist diese App verdächtig (Spyware/Bloatware/Tracker)? Bewerte kurz auf Deutsch, "
            "nenne Risiko (niedrig/mittel/hoch) und eine Empfehlung.",
            "Du bist ein Android-Sicherheitsanalyst.", timeout=120)
        ui.pager(ans, f"KI-Bewertung: {pkg}")
    except Exception as e:  # noqa: BLE001
        ui.err(str(e))
    ui.pause()


def _ai_overview(adb: ADB, ranked: list[dict]) -> None:
    try:
        from . import aishell
        if not aishell._ollama_up():
            ui.warn("KI (ollama) nicht erreichbar."); ui.pause(); return
        model = aishell._pick_model()
        lst = "\n".join(f"{r['pkg']} (Score {r['score']}: {', '.join(r['reasons'])})" for r in ranked[:30])
        ans = aishell._gen(model,
            f"Diese Android-Apps fielen beim Forensik-Scan auf:\n{lst}\n\n"
            "Welche sind am wahrscheinlichsten Spyware/Stalkerware/Tracker (nicht nur Hersteller-Bloat)? "
            "Priorisiere auf Deutsch die Top-5 mit Begründung und Handlungsempfehlung.",
            "Du bist ein Android-Sicherheitsanalyst.", timeout=180)
        ui.pager(ans, "KI-Gesamtanalyse")
    except Exception as e:  # noqa: BLE001
        ui.err(str(e))
    ui.pause()
