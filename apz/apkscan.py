"""APK-Statik-Analyse · Permission-Risk-Scoring · geräteweiter IOC-Scan.

Drei Bausteine – alle ohne Fremdpakete (reines Standard-Python):

  1. APK-Statik-Analyse  – zieht eine App-APK (oder nimmt eine lokale Datei),
     öffnet sie als ZIP und wertet sie OFFLINE aus: Paketname & angeforderte
     Permissions aus dem *binären* AndroidManifest.xml (eigener AXML-Parser),
     Signatur-/Zertifikatsdateien, native Bibliotheken, DEX-Übersicht, SHA-256
     (inkl. VirusTotal-Link) und IOC-Strings (URLs/IPs) aus den DEX-Daten.

  2. Risk-Inventar       – bewertet alle Drittanbieter-Apps am Gerät nach
     Gefahren-Indikatoren (sensible Rechte-Kombis, Accessibility/Device-Admin,
     Autostart, Overlay, sideloaded, debuggable) und sortiert nach Score.

  3. IOC-Scan            – geräteweiter Indikatoren-Sweep: hosts-Hijack,
     Accessibility-/Device-Admin-/Notification-Listener-Bindings, bekannte
     Stalkerware-Pakete, verdächtige Rechte-Kombinationen.

Alles read-only. Nichts wird gefälscht – fehlt Zugriff, sagt das Tool es klar.
"""
from __future__ import annotations

import os
import re
import struct
import time
import zipfile

from . import ui
from .adb import ADB
from .util import LOG, human_size, outdir, sha256_file, shq, valid_pkg

OUT = outdir("apkscan")

# --------------------------------------------------------------------------- #
#  Risk-Gewichte & Indikatoren
# --------------------------------------------------------------------------- #
DANGEROUS_PERMS = {
    "READ_SMS": 3, "RECEIVE_SMS": 3, "SEND_SMS": 3,
    "RECORD_AUDIO": 3, "CAMERA": 2,
    "ACCESS_FINE_LOCATION": 2, "ACCESS_BACKGROUND_LOCATION": 3,
    "READ_CONTACTS": 2, "READ_CALL_LOG": 3, "PROCESS_OUTGOING_CALLS": 3,
    "READ_PHONE_STATE": 1, "REQUEST_INSTALL_PACKAGES": 3,
    "SYSTEM_ALERT_WINDOW": 2, "BIND_ACCESSIBILITY_SERVICE": 4,
    "BIND_DEVICE_ADMIN": 4, "BIND_NOTIFICATION_LISTENER_SERVICE": 3,
    "READ_EXTERNAL_STORAGE": 1, "WRITE_EXTERNAL_STORAGE": 1,
    "QUERY_ALL_PACKAGES": 2, "RECEIVE_BOOT_COMPLETED": 1,
    "FOREGROUND_SERVICE": 1, "WRITE_SETTINGS": 2,
}

# Stalkerware/Spyware-typische Rechte-Kombination (Audio + Standort + Nachrichten + Kontakte)
STALKER_COMBO = ("RECORD_AUDIO", "ACCESS_FINE_LOCATION", "READ_SMS", "READ_CONTACTS")

# Bekannte Stalkerware-/Spyware-Paketnamen (Auszug, erweiterbar).
KNOWN_STALKERWARE = {
    "com.mspy.lite", "com.mspy", "net.flexispy.android", "com.flexispy",
    "com.thetruthspy", "com.cymobile.spy", "com.spyhuman.app",
    "com.hellospy.system", "com.wt.cs", "com.android.systemservice",
    "com.android.core.mate", "com.system.service", "com.ws.dm",
    "com.cerberusapp", "com.android.protect",
}

# IOC-Regex für DEX-/Textinhalt.
RE_URL = re.compile(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{4,}")
RE_IP = re.compile(rb"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
# offensichtlich harmlose Hosts ausfiltern (Plattform-Standards).
IOC_DENY = ("schemas.android.com", "www.w3.org", "ns.adobe.com", "java.sun.com",
            "xmlpull.org", "127.0.0.1", "0.0.0.0", "255.255.255", "goo.gl/")

# Legitime Installer/Update-Quellen (Stores + Plattform-Pusher) → NICHT sideloaded.
BENIGN_INSTALLERS = {
    "com.android.vending", "com.google.android.packageinstaller",
    "com.android.packageinstaller", "com.google.android.gms",
    "com.sec.android.app.samsungapps", "com.amazon.venezia",
    "com.huawei.appmarket", "com.xiaomi.market", "com.aurora.store",
    "org.fdroid.fdroid", "com.samsung.android.app.omcagent",
    "com.samsung.android.app.omcage", "com.wssyncmldm", "com.sec.android.preloadinstaller",
}


# --------------------------------------------------------------------------- #
#  Präzise geräteweite Privilegien-Erkennung (kein Substring-Match!)
#  Geteilt mit appscan – 'pkg in dumpsys_dump' ist falsch: 'android' steckt überall.
# --------------------------------------------------------------------------- #
def comp_pkgs(value: str) -> set:
    """Paketnamen aus einer Komponentenliste 'pkg/.Svc:pkg2/.Svc' (settings-Werte)."""
    if not value or value.strip().lower() in ("null", "none", ""):
        return set()
    return {m.split("/", 1)[0] for m in re.findall(r"[a-zA-Z0-9_.]+/[A-Za-z0-9_.$]+", value)}


def admin_pkgs(dump: str) -> set:
    """Pakete AKTIVER Device-Admins aus 'dumpsys device_policy' (nur echte Admins).

    Substring-Matching gegen den Gesamt-Dump ist falsch ('android' steckt überall) –
    daher gezielt die Admin-Bindungen ziehen: ``admin=ComponentInfo{pkg/..}`` /
    ``Admin: ComponentInfo{pkg/..}`` sowie die eingerückte Sektion „Enabled Device
    Admins …:". Unbekannte Formate → WENIGER Treffer (sichere Richtung), nie mehr.
    """
    pkgs: set = set()
    pkgs.update(re.findall(
        r"(?:admin=|Admin:\s*)(?:DeviceAdminInfo\{\s*)?ComponentInfo\{([a-zA-Z0-9_.]+)/", dump))
    in_section = False
    for line in dump.splitlines():
        low = line.lower()
        if ("device admins" in low or "active admins" in low) and line.rstrip().endswith(":"):
            in_section = True
            continue
        if in_section:
            m = re.match(r"\s{2,}([a-zA-Z0-9_.]+)/[A-Za-z0-9_.$]+:\s*$", line)
            if m:
                pkgs.add(m.group(1))
            elif line.strip() and not line[:1].isspace():
                in_section = False
    return pkgs


def launcher_pkgs(adb) -> set:
    """Pakete mit sichtbarem Launcher-Icon (MAIN/LAUNCHER)."""
    out = adb.shell("cmd package query-activities --brief "
                    "-a android.intent.action.MAIN -c android.intent.category.LAUNCHER")
    return set(re.findall(r"([a-zA-Z0-9_.]+)/", out))


def privilege_context(adb) -> dict:
    """Präzise geräteweite Privilegien-Bindungen als exakte Paket-Mengen."""
    return {
        "a11y": comp_pkgs(adb.shell("settings get secure enabled_accessibility_services")),
        "notif": comp_pkgs(adb.shell("settings get secure enabled_notification_listeners")),
        "admins": admin_pkgs(adb.shell("dumpsys device_policy 2>/dev/null", timeout=20)),
        "launchers": launcher_pkgs(adb),
    }


# ========================================================================== #
#  Binärer AndroidManifest-Parser (AXML)  – eigenständig, ohne aapt
# ========================================================================== #
def _axml_strings(data: bytes, pos: int) -> list[str]:
    """Liest den String-Pool eines AXML-Chunks (UTF-8 & UTF-16)."""
    count = struct.unpack_from("<I", data, pos + 8)[0]
    flags = struct.unpack_from("<I", data, pos + 16)[0]
    str_start = struct.unpack_from("<I", data, pos + 20)[0]
    is_utf8 = bool(flags & 0x100)
    offs = [struct.unpack_from("<I", data, pos + 28 + i * 4)[0] for i in range(count)]
    base = pos + str_start
    out: list[str] = []
    for off in offs:
        p = base + off
        try:
            if is_utf8:
                # zwei Längenfelder (Zeichenzahl, Bytezahl) – je 1–2 Bytes
                p, _ = _len8(data, p)
                p, blen = _len8(data, p)
                out.append(data[p:p + blen].decode("utf-8", "replace"))
            else:
                n = struct.unpack_from("<H", data, p)[0]
                p += 2
                if n & 0x8000:
                    n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", data, p)[0]
                    p += 2
                out.append(data[p:p + n * 2].decode("utf-16-le", "replace"))
        except Exception:  # noqa: BLE001 – einzelner String-Fehler darf Rest nicht killen
            out.append("")
    return out


def _len8(data: bytes, p: int) -> tuple[int, int]:
    n = data[p]
    p += 1
    if n & 0x80:
        n = ((n & 0x7F) << 8) | data[p]
        p += 1
    return p, n


def parse_manifest(data: bytes) -> dict:
    """Parst binäres AndroidManifest.xml → {package, version, permissions, features}.

    Liefert auch bei Teilfehlern, was extrahiert werden konnte (defensiv).
    """
    res = {"package": "", "version": "", "permissions": [], "features": [], "min_sdk": ""}
    if len(data) < 8 or struct.unpack_from("<H", data, 0)[0] != 0x0003:
        return res
    strings: list[str] = []
    pos = 8
    end = min(len(data), struct.unpack_from("<I", data, 4)[0] or len(data))
    while pos + 8 <= end:
        ctype, _hdr, csize = struct.unpack_from("<HHI", data, pos)
        if csize < 8 or pos + csize > end:
            break
        if ctype == 0x0001:                      # RES_STRING_POOL_TYPE
            strings = _axml_strings(data, pos)
        elif ctype == 0x0102:                    # RES_XML_START_ELEMENT_TYPE
            _read_start_tag(data, pos, strings, res)
        pos += csize
    # Dedupe, kürze android.permission.-Präfix für Lesbarkeit beim Scoring später nicht.
    res["permissions"] = sorted(set(res["permissions"]))
    res["features"] = sorted(set(res["features"]))
    return res


def _read_start_tag(data: bytes, pos: int, strings: list[str], res: dict) -> None:
    def s(idx: int) -> str:
        return strings[idx] if 0 <= idx < len(strings) else ""
    try:
        name = s(struct.unpack_from("<I", data, pos + 20)[0])   # Node(16)+ns(4) → name
        attr_start = struct.unpack_from("<H", data, pos + 24)[0]
        attr_size = struct.unpack_from("<H", data, pos + 26)[0] or 20
        attr_count = struct.unpack_from("<H", data, pos + 28)[0]
        attrs: dict[str, str] = {}
        base = pos + 16 + attr_start
        for i in range(attr_count):
            a = base + i * attr_size
            a_name = s(struct.unpack_from("<I", data, a + 4)[0])
            raw = struct.unpack_from("<I", data, a + 8)[0]
            dtype = data[a + 15]
            dval = struct.unpack_from("<I", data, a + 16)[0]
            if raw != 0xFFFFFFFF:
                val = s(raw)
            elif dtype == 0x03:                  # TYPE_STRING
                val = s(dval)
            else:
                val = str(dval)
            attrs[a_name] = val
    except Exception as e:  # noqa: BLE001
        LOG.exception("AXML start-tag", e)
        return

    if name == "manifest":
        if attrs.get("package"):
            res["package"] = attrs["package"]
        if attrs.get("versionName"):
            res["version"] = attrs["versionName"]
    elif name == "uses-permission" or name == "uses-permission-sdk-23":
        if attrs.get("name"):
            res["permissions"].append(attrs["name"])
    elif name == "uses-feature":
        if attrs.get("name"):
            res["features"].append(attrs["name"])
    elif name == "uses-sdk":
        if attrs.get("minSdkVersion"):
            res["min_sdk"] = attrs["minSdkVersion"]


# ========================================================================== #
#  APK-Statik-Analyse
# ========================================================================== #
def _score_perms(perms: list[str]) -> tuple[int, list[str]]:
    short = [p.rsplit(".", 1)[-1] for p in perms]
    score, reasons = 0, []
    for p in short:
        score += DANGEROUS_PERMS.get(p, 0)
    sens = [p for p in short if p in DANGEROUS_PERMS]
    if len(sens) >= 4:
        reasons.append(f"{len(sens)} sensible Rechte")
    if all(c in short for c in STALKER_COMBO):
        score += 5
        reasons.append("Stalkerware-Rechte-Kombi (Audio+Standort+SMS+Kontakte)")
    for flag, txt in [("BIND_ACCESSIBILITY_SERVICE", "Accessibility-Dienst"),
                      ("BIND_DEVICE_ADMIN", "Device-Admin"),
                      ("REQUEST_INSTALL_PACKAGES", "kann APKs installieren"),
                      ("SYSTEM_ALERT_WINDOW", "Overlay")]:
        if flag in short:
            reasons.append(txt)
    return score, reasons


def analyze_apk_file(path: str) -> dict:
    """Offline-Analyse einer lokalen APK-Datei."""
    r: dict = {"path": path, "ok": False}
    if not os.path.isfile(path):
        r["error"] = "Datei nicht gefunden"
        return r
    r["size"] = os.path.getsize(path)
    try:
        r["sha256"] = sha256_file(path)
    except OSError as e:
        LOG.exception(f"apk sha {path}", e)
        r["sha256"] = ""
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        r["error"] = f"kein gültiges ZIP/APK: {e}"
        return r
    with zf:
        names = zf.namelist()
        r["entries"] = len(names)
        r["dex"] = sorted(n for n in names if n.endswith(".dex"))
        r["libs"] = sorted({n.split("/")[1] for n in names
                            if n.startswith("lib/") and n.count("/") >= 2})
        r["native_libs"] = sorted({os.path.basename(n) for n in names
                                   if n.startswith("lib/") and n.endswith(".so")})
        r["certs"] = sorted(n for n in names
                            if n.startswith("META-INF/") and n.lower().endswith((".rsa", ".dsa", ".ec")))
        r["signed"] = bool(r["certs"]) or any(n.startswith("META-INF/") and "SIG" in n.upper() for n in names)
        # Manifest
        try:
            r["manifest"] = parse_manifest(zf.read("AndroidManifest.xml"))
        except (KeyError, OSError) as e:
            LOG.exception(f"apk manifest {path}", e)
            r["manifest"] = {"package": "", "permissions": [], "features": [], "version": "", "min_sdk": ""}
        # IOC-Strings aus DEX (begrenzt, um Speicher zu schonen)
        iocs: set[str] = set()
        for dex in r["dex"][:4]:
            try:
                blob = zf.read(dex)
            except (KeyError, OSError):
                continue
            for m in RE_URL.findall(blob)[:4000]:
                u = m.decode("ascii", "replace")
                if not any(d in u for d in IOC_DENY):
                    iocs.add(u)
            for m in RE_IP.findall(blob)[:4000]:
                ip = m.decode("ascii", "replace")
                if not any(ip.startswith(d) for d in IOC_DENY) and not ip.startswith(("0.", "255.")):
                    iocs.add(ip)
        r["iocs"] = sorted(iocs)[:200]
    perms = r["manifest"].get("permissions", [])
    r["score"], r["reasons"] = _score_perms(perms)
    r["ok"] = True
    return r


def _render_apk_report(r: dict) -> str:
    m = r.get("manifest", {})
    lines = ["# APK-STATIK-ANALYSE", "",
             f"Datei:        {r['path']}",
             f"Größe:        {human_size(r.get('size', 0))}",
             f"SHA-256:      {r.get('sha256', '')}",
             f"VirusTotal:   https://www.virustotal.com/gui/file/{r.get('sha256', '')}",
             f"Paket:        {m.get('package', '—')}",
             f"Version:      {m.get('version', '—')}   minSdk: {m.get('min_sdk', '—')}",
             f"Signiert:     {'ja' if r.get('signed') else 'NEIN (!)'}   Zerts: {', '.join(r.get('certs', [])) or '—'}",
             f"ZIP-Einträge: {r.get('entries', 0)}   DEX: {len(r.get('dex', []))}",
             f"Native Libs:  {', '.join(r.get('libs', [])) or '—'}",
             "",
             f"== RISIKO-SCORE: {r.get('score', 0)} ==",
             "Gründe: " + (", ".join(r.get("reasons", [])) or "keine besonderen"),
             "",
             f"== ANGEFORDERTE PERMISSIONS ({len(m.get('permissions', []))}) =="]
    for p in m.get("permissions", []):
        short = p.rsplit(".", 1)[-1]
        mark = "  ⚠" if short in DANGEROUS_PERMS else ""
        lines.append(f"  {p}{mark}")
    iocs = r.get("iocs", [])
    lines += ["", f"== IOC-KANDIDATEN aus DEX ({len(iocs)}) =="]
    lines += [f"  {x}" for x in iocs] or ["  (keine)"]
    return "\n".join(lines) + "\n"


def analyze_installed(adb: ADB, st: dict) -> None:
    pkg = ui.ask("Paketname (leer = Liste der Drittanbieter-Apps)").strip()
    if not pkg:
        pkgs = [l.split(":", 1)[1] for l in adb.shell("pm list packages -3").splitlines() if ":" in l]
        for i, p in enumerate(sorted(pkgs)[:60], 1):
            print(f"  {ui.CYAN}{i:>2}{ui.RESET} {p}")
        sel = ui.ask("Nr. wählen").strip()
        try:
            pkg = sorted(pkgs)[int(sel) - 1]
        except (ValueError, IndexError):
            ui.warn("Abgebrochen."); ui.pause(); return
    paths = [ln.split("package:", 1)[1].strip()
             for ln in adb.shell(f"pm path {shq(pkg)}").splitlines() if "package:" in ln]
    if not paths:
        ui.err("Kein APK-Pfad (deaktiviert/kein solches Paket?)."); ui.pause(); return
    base_apk = next((p for p in paths if p.endswith("base.apk")), paths[0])
    local = os.path.join(OUT, f"{pkg}.apk")
    ui.info(f"Ziehe {base_apk} …")
    rc, out, err = adb.raw(["pull", base_apk, local], timeout=300)
    if not os.path.isfile(local):
        ui.err(f"Pull fehlgeschlagen: {(out + err).strip()}"); ui.pause(); return
    _analyze_and_show(local)


def analyze_local(adb=None, dev=None, st=None) -> None:
    path = os.path.expanduser(ui.ask("Pfad zur lokalen .apk").strip())
    if not path:
        return
    _analyze_and_show(path)


def _analyze_and_show(local: str) -> None:
    ui.info("Analysiere (offline) …")
    r = analyze_apk_file(local)
    if not r.get("ok"):
        ui.err(r.get("error", "Analyse fehlgeschlagen")); ui.pause(); return
    txt = _render_apk_report(r)
    pkg = r["manifest"].get("package") or os.path.basename(local)
    outp = os.path.join(OUT, f"apk_{re.sub(r'[^A-Za-z0-9_.]', '_', pkg)}.txt")
    with open(outp, "w", encoding="utf-8") as f:
        f.write(txt)
    ui.pager(txt, f"APK-Analyse: {pkg}")
    ui.ok(f"Report → {outp}")
    ui.pause()


# ========================================================================== #
#  Risk-Inventar (geräteseitig)
# ========================================================================== #
def _collect_risk(adb: ADB, ctx: dict | None = None) -> tuple[list, int, dict]:
    """Bewertet alle Drittanbieter-Apps (präzise Privilegien). → (ranking, total, ctx)."""
    pkgs = sorted(l.split(":", 1)[1] for l in adb.shell("pm list packages -3").splitlines() if ":" in l)
    if ctx is None:
        ctx = privilege_context(adb)
    results = []
    for i, pkg in enumerate(pkgs, 1):
        ui.progress(i, len(pkgs), f"prüfe {pkg}")
        d = adb.shell(f"dumpsys package {shq(pkg)} | grep -E "
                      f"'granted=true|DEBUGGABLE|TEST_ONLY|installerPackageName' | head -n 120")
        perms = re.findall(r"android\.permission\.(\w+): granted=true", d)
        score, reasons = _score_perms([f"android.permission.{p}" for p in perms])
        m = re.search(r"installerPackageName=(\S+)", d)
        inst = m.group(1) if m else "null"
        if inst not in BENIGN_INSTALLERS:
            score += 2; reasons.append(f"sideloaded ({inst if inst not in ('null', '') else 'unbekannt'})")
        if "DEBUGGABLE" in d:
            score += 2; reasons.append("debuggable")
        if "TEST_ONLY" in d:
            score += 3; reasons.append("test-only")
        if pkg in ctx["a11y"]:
            score += 4; reasons.append("Accessibility AKTIV")
        if pkg in ctx["admins"]:
            score += 4; reasons.append("Device-Admin AKTIV")
        if pkg in ctx["notif"]:
            score += 3; reasons.append("Notification-Listener AKTIV")
        if pkg in KNOWN_STALKERWARE:
            score += 8; reasons.append("BEKANNTE STALKERWARE")
        if score >= 3:
            results.append({"pkg": pkg, "score": score, "reasons": reasons or ["sensible Rechte"]})
    results.sort(key=lambda x: -x["score"])
    return results, len(pkgs), ctx


def _deep_analyze(adb: ADB, pkg: str, ctx: dict) -> list[str]:
    """Präziser Tiefen-Block für EINE App (Quelle, ABI, Privilegien, gefährliche Rechte)."""
    d = adb.shell(f"dumpsys package {shq(pkg)}", timeout=25)
    granted = sorted(set(re.findall(r"android\.permission\.(\w+): granted=true", d)))
    dangerous = [p for p in granted if p in DANGEROUS_PERMS]
    m = re.search(r"installerPackageName=(\S+)", d); inst = m.group(1) if m else "null"
    ma = re.search(r"primaryCpuAbi=(\S+)", d); abi = ma.group(1) if ma and ma.group(1) != "null" else "—"
    mv = re.search(r"versionName=(\S+)", d); ver = mv.group(1) if mv else "?"
    fl = re.search(r"\n\s*flags=\[([^\]]*)\]", d)
    flagset = set(re.findall(r"[A-Z_]{3,}", fl.group(1))) if fl else set()
    privs = [n for n, s in (("Accessibility", "a11y"), ("Device-Admin", "admins"),
                            ("Notification-Listener", "notif")) if pkg in ctx[s]]
    hidden = pkg not in ctx["launchers"]
    src = ("legitim" if inst in BENIGN_INSTALLERS else
           "unbekannt/sideloaded" if inst in ("null", "com.android.shell") else inst)
    return [
        f"  ▸ {pkg}  v{ver}",
        f"      Installer-Quelle  : {inst}  ({src})",
        f"      Architektur (ABI) : {abi}",
        f"      Launcher-Icon     : {'NEIN – läuft versteckt' if hidden else 'ja'}",
        f"      Aktive Privilegien: {', '.join(privs) or 'keine'}",
        f"      Auffällige Flags  : {', '.join(sorted(flagset & {'DEBUGGABLE', 'TEST_ONLY'})) or '—'}",
        f"      Gefährliche Rechte ({len(dangerous)}): {', '.join(dangerous) or '—'}",
    ]


def risk_inventory(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("App-Risiko-Inventar", ui.CYAN)
    ui.info("Bewerte alle Drittanbieter-Apps (präzise Privilegien-Erkennung) … (kann dauern)")
    results, total, ctx = _collect_risk(adb)
    out = [f"# APP-RISIKO-INVENTAR ({len(results)} auffällige von {total} Apps)",
           f"# {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    for r in results:
        sev = "KRITISCH" if r["score"] >= 8 else "HOCH" if r["score"] >= 5 else "MITTEL"
        out.append(f"[{r['score']:>2}] {sev:<8} {r['pkg']} — {', '.join(r['reasons'])}")
    crit = [r for r in results if r["score"] >= 8]
    if crit:
        out += ["", "=" * 64, f"TIEFEN-ANALYSE der {len(crit)} kritischen (blinkenden) App(s):", ""]
        for i, r in enumerate(crit, 1):
            ui.progress(i, len(crit), f"Tiefen-Analyse {r['pkg']}")
            out += _deep_analyze(adb, r["pkg"], ctx) + [""]
    body = "\n".join(out) + "\n"
    p = os.path.join(OUT, "risk_inventory.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    if not results:
        ui.ok("Keine auffälligen Apps gefunden."); ui.pause(); return
    ui.show_report(body, "App-Risiko-Inventar · Ranking + Tiefen-Analyse", p, note=f"{len(results)} auffällige Apps")
    ui.info("Eine App KOMPLETT (Statik + alle Verzeichnisse) analysieren: Menü → 5")
    ui.pause()


# ========================================================================== #
#  Komplett-Analyse EINER App – bis ins letzte Verzeichnis
# ========================================================================== #
def _app_locations(adb: ADB, pkg: str) -> list[str]:
    """Alle Speicherorte einer App (Code, Daten, External, OBB, Media)."""
    locs = []
    for ln in adb.shell(f"pm path {shq(pkg)}").splitlines():
        if "package:" in ln:
            locs.append(os.path.dirname(ln.split("package:", 1)[1].strip()))
    locs += [f"/data/data/{pkg}", f"/sdcard/Android/data/{pkg}",
             f"/sdcard/Android/obb/{pkg}", f"/sdcard/Android/media/{pkg}"]
    return list(dict.fromkeys(x for x in locs if x))


def _dir_tree(adb: ADB, path: str, root: bool = False) -> str:
    """Rekursives, vollständiges Verzeichnis-Listing (bis ins letzte Verzeichnis)."""
    return adb.shell(f"ls -laR {shq(path)} 2>/dev/null", root=root, timeout=120)


def deep_analyze_app(adb: ADB, dev, st: dict, pkg: str) -> None:
    pkg = (pkg or "").strip()
    if not valid_pkg(pkg):
        ui.err("Ungültiger Paketname."); ui.pause(); return
    ui.clear(); ui.rule(f"Komplett-Analyse · {pkg}", ui.CYAN)
    is_root = bool(st.get("is_root"))
    ctx = privilege_context(adb)
    steps = 5
    lines = [f"# KOMPLETT-ANALYSE · {pkg}", f"# {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"# Root: {'ja' if is_root else 'nein (Sandbox /data/data eingeschränkt)'}", ""]

    ui.progress(1, steps, "Status & Privilegien")
    lines += ["== STATUS & PRIVILEGIEN =="] + _deep_analyze(adb, pkg, ctx) + [""]

    ui.progress(2, steps, "APK ziehen & Statik-Analyse")
    paths = [ln.split("package:", 1)[1].strip()
             for ln in adb.shell(f"pm path {shq(pkg)}").splitlines() if "package:" in ln]
    if paths:
        base = next((x for x in paths if x.endswith("base.apk")), paths[0])
        local = os.path.join(OUT, re.sub(r"[^A-Za-z0-9_.]", "_", pkg) + ".apk")
        adb.raw(["pull", base, local], timeout=300)
        if os.path.isfile(local):
            r = analyze_apk_file(local)
            if r.get("ok"):
                lines += ["== STATIK-ANALYSE (APK, offline) ==", _render_apk_report(r), ""]

    ui.progress(3, steps, "Komponenten")
    comp = adb.shell(f"dumpsys package {shq(pkg)} | grep -E "
                     f"'Activity|Service|Receiver|Provider' | head -n 120")
    lines += ["== KOMPONENTEN (Activities/Services/Receiver/Provider) ==", comp or "(keine)", ""]

    ui.progress(4, steps, "Verzeichnisse rekursiv (bis ins letzte)")
    lines.append("== VERZEICHNIS-INVENTAR (rekursiv · bis ins letzte Verzeichnis) ==")
    locs = _app_locations(adb, pkg)
    for j, loc in enumerate(locs, 1):
        ui.progress(j, len(locs), f"liste {loc}")
        tree = _dir_tree(adb, loc, root=is_root)
        if not tree.strip() and loc.startswith("/data/data") and not is_root:
            ra = adb.shell(f"run-as {shq(pkg)} ls -laR 2>/dev/null")
            tree = ra if ra.strip() else "(nicht lesbar – /data/data ist sandboxed; Root nötig)"
        if not tree.strip():
            tree = "(leer / nicht vorhanden / Zugriff verweigert)"
        lines += [f"--- {loc} ---", tree, ""]

    ui.progress(5, steps, "Bericht erzeugen")
    body = "\n".join(lines) + "\n"
    p = os.path.join(OUT, f"deep_{re.sub(r'[^A-Za-z0-9_.]', '_', pkg)}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    ui.show_report(body, f"Komplett-Analyse · {pkg}", p, note="Komplett-Analyse")
    ui.pause()


def deep_risk_menu(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("Risiko-App KOMPLETT analysieren (bis ins letzte Verzeichnis)", ui.CYAN)
    ui.info("Ermittle Risiko-Ranking …")
    results, total, ctx = _collect_risk(adb)
    if results:
        for i, r in enumerate(results[:40], 1):
            badge = (ui.pulse(f"[{r['score']:>2}]") if r["score"] >= 8
                     else f"{ui.BYELLOW}[{r['score']:>2}]{ui.RESET}" if r["score"] >= 5
                     else f"{ui.WHITE}[{r['score']:>2}]{ui.RESET}")
            print(f"  {ui.CYAN}{i:>2}{ui.RESET} {badge} {r['pkg']}  "
                  f"{ui.GREY}{', '.join(r['reasons'])[:58]}{ui.RESET}")
    else:
        ui.warn("Keine auffälligen Apps – du kannst trotzdem einen Paketnamen eingeben.")
    sel = ui.ask("Nr. für KOMPLETT-Analyse (oder Paketname, leer = Abbruch)").strip()
    if not sel:
        return
    pkg = results[int(sel) - 1]["pkg"] if (sel.isdigit() and 1 <= int(sel) <= len(results)) else sel
    deep_analyze_app(adb, dev, st, pkg)


# ========================================================================== #
#  6. Tiefen-String-Scan (URLs / E-Mails / Base64 / API-Keys / IPs)
# ========================================================================== #

_RE_EMAIL  = re.compile(rb"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_RE_B64    = re.compile(rb"[A-Za-z0-9+/]{32,}={0,2}")
_RE_APIKEY = re.compile(
    rb"(?:api[_-]?key|apikey|secret|token|access[_-]?key|auth[_-]?key)"
    rb"[\"':\s=]+([A-Za-z0-9+/._-]{16,})", re.IGNORECASE)


def _extract_deep_strings(apk_path: str) -> dict:
    """Extrahiert URLs, E-Mails, IPs, Base64-Blobs und API-Key-Kandidaten aus APK."""
    urls: set = set()
    emails: set = set()
    ips: set = set()
    b64: list = []
    apikeys: list = []
    try:
        with zipfile.ZipFile(apk_path) as zf:
            entries = [n for n in zf.namelist() if n.endswith((".dex", ".js", ".xml", ".json", ".properties"))]
            for name in entries[:10]:
                try:
                    data = zf.read(name)
                except (KeyError, OSError):
                    continue
                for m in RE_URL.findall(data)[:3000]:
                    u = m.decode("ascii", "replace")
                    if not any(d in u for d in IOC_DENY):
                        urls.add(u)
                for m in RE_IP.findall(data)[:3000]:
                    ip = m.decode("ascii", "replace")
                    if not ip.startswith(("127.", "0.", "255.", "10.")):
                        ips.add(ip)
                for m in _RE_EMAIL.findall(data)[:500]:
                    emails.add(m.decode("ascii", "replace"))
                for m in _RE_B64.findall(data)[:200]:
                    try:
                        import base64 as _b64
                        dec = _b64.b64decode(m + b"==").decode("utf-8", "replace")
                        if sum(c.isprintable() for c in dec[:30]) > 20:
                            b64.append((m.decode("ascii", "replace")[:40], dec[:80]))
                    except Exception:  # noqa: BLE001
                        pass
                for m in _RE_APIKEY.findall(data)[:50]:
                    apikeys.append(m.decode("ascii", "replace")[:60])
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    return {
        "urls":    sorted(urls)[:300],
        "emails":  sorted(emails)[:100],
        "ips":     sorted(ips)[:100],
        "b64":     b64[:30],
        "apikeys": list(set(apikeys))[:30],
    }


def deep_string_scan(adb: ADB, dev, st) -> None:
    path = os.path.expanduser(ui.ask("Pfad zur APK (oder leer für installierte App)").strip())
    if not path:
        pkg = ui.ask("Paketname").strip()
        if not pkg:
            return
        paths = [ln.split("package:", 1)[1].strip()
                 for ln in adb.shell(f"pm path {pkg}").splitlines() if "package:" in ln]
        if not paths:
            ui.err("Kein APK-Pfad."); ui.pause(); return
        base = next((x for x in paths if x.endswith("base.apk")), paths[0])
        path = os.path.join(OUT, f"ds_{pkg}.apk")
        adb.raw(["pull", base, path], timeout=300)
    if not os.path.isfile(path):
        ui.err("Datei nicht gefunden."); ui.pause(); return
    ui.info("Analysiere Strings (URLs/E-Mails/Base64/API-Keys) …")
    res = _extract_deep_strings(path)
    if "error" in res:
        ui.err(res["error"]); ui.pause(); return
    out = [f"# STRING-TIEFENSCAN: {path}", f"# {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    out += [f"== URLS ({len(res['urls'])}) =="] + [f"  {u}" for u in res["urls"]] + [""]
    out += [f"== IPS ({len(res['ips'])}) =="] + [f"  {ip}" for ip in res["ips"]] + [""]
    out += [f"== E-MAILS ({len(res['emails'])}) =="] + [f"  {e}" for e in res["emails"]] + [""]
    if res["apikeys"]:
        out += [f"== API-KEY-KANDIDATEN ({len(res['apikeys'])}) ACHTUNG! =="] + \
               [f"  {k}" for k in res["apikeys"]] + [""]
    if res["b64"]:
        out += [f"== BASE64-KANDIDATEN ({len(res['b64'])}) =="] + \
               [f"  {r[0]} → {r[1]}" for r in res["b64"]] + [""]
    body = "\n".join(out) + "\n"
    p = os.path.join(OUT, f"strings_{int(time.time())}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    ui.show_report(body, "String-Tiefenscan", p)
    ui.pause()


# ========================================================================== #
#  7. Zertifikat-Analyse
# ========================================================================== #

def _parse_cert_info(raw: bytes) -> str:
    """Extrahiert lesbare Strings aus einem DER/PEM-Zertifikat (ohne cryptography-Lib)."""
    lines = []
    # Aus dem Rohdaten bekannte OID-Werte suchen und darstellen
    text = raw.decode("latin-1", errors="replace")
    strings = re.findall(r"[\x20-\x7e]{4,}", text)
    readable = [s for s in strings if len(s) > 5 and not s.startswith("0\x82")]
    sha1 = __import__("hashlib").sha1(raw).hexdigest().upper()
    sha256 = __import__("hashlib").sha256(raw).hexdigest().upper()
    size = len(raw)
    lines.append(f"  Größe:   {size} Bytes")
    lines.append(f"  SHA-1:   {':'.join(sha1[i:i+2] for i in range(0,40,2))}")
    lines.append(f"  SHA-256: {sha256[:32]}…")
    # Erkennbare Textfelder aus dem Zertifikat
    for s in readable[:30]:
        if any(c.isalpha() for c in s) and s not in ("UTF-8", "BouncyCastle", "2.5.4"):
            lines.append(f"  {s}")
    return "\n".join(lines)


def cert_analysis(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Paketname (leer = Datei-Pfad eingeben)").strip()
    local = ""
    if pkg:
        paths = [ln.split("package:", 1)[1].strip()
                 for ln in adb.shell(f"pm path {pkg}").splitlines() if "package:" in ln]
        if not paths:
            ui.err("Paket nicht gefunden."); ui.pause(); return
        base = next((x for x in paths if x.endswith("base.apk")), paths[0])
        local = os.path.join(OUT, f"cert_{pkg}.apk")
        adb.raw(["pull", base, local], timeout=300)
    else:
        local = os.path.expanduser(ui.ask("APK-Pfad").strip())
    if not os.path.isfile(local):
        ui.err("Datei nicht gefunden."); ui.pause(); return
    ui.clear(); ui.rule("Zertifikat-Analyse", ui.CYAN)
    try:
        with zipfile.ZipFile(local) as zf:
            certs = [n for n in zf.namelist()
                     if n.startswith("META-INF/") and n.lower().endswith((".rsa", ".dsa", ".ec"))]
            if not certs:
                ui.warn("Keine Zertifikat-Dateien in META-INF/ – unsignierte APK?")
                ui.pause(); return
            for cert_name in certs:
                raw = zf.read(cert_name)
                print(f"\n  {ui.BCYAN}{ui.BOLD}■ {cert_name}{ui.RESET}")
                print(_parse_cert_info(raw))
            # V2/V3 Signatur erkennbar?
            v2 = any("APK Sig Block" in zf.comment.decode("utf-8", "replace")
                     if zf.comment else False for _ in [1])
            # Prüfe ob APK-Signing-Block vorhanden (simpel per Magic)
            with open(local, "rb") as f:
                apk_bytes = f.read()
            has_v2 = b"APK Sig Block 42" in apk_bytes
            print(f"\n  Signatur-Schema v1 (JAR): {'ja' if certs else 'nein'}")
            print(f"  Signatur-Schema v2/v3:    {'ja (APK Sig Block 42 gefunden)' if has_v2 else 'unklar (ohne aapt)'}")
    except Exception as e:  # noqa: BLE001
        ui.err(str(e))
    print()
    # Externe Tool-Ausgabe wenn verfügbar
    if __import__("shutil").which("keytool"):
        try:
            out = __import__("subprocess").check_output(
                ["keytool", "-printcert", "-jarfile", local],
                stderr=__import__("subprocess").DEVNULL, text=True, timeout=15
            )
            print(f"  {ui.BCYAN}keytool-Ausgabe:{ui.RESET}")
            print(out[:2000])
        except Exception:  # noqa: BLE001
            pass
    ui.pause()


# ========================================================================== #
#  8. Tracker-SDK-Erkennung
# ========================================================================== #

KNOWN_TRACKERS = {
    "com.google.firebase":       "Firebase Analytics",
    "com.google.android.gms.analytics": "Google Analytics",
    "com.adjust.sdk":            "Adjust",
    "io.branch.referral":        "Branch.io",
    "com.appsflyer":             "AppsFlyer",
    "com.facebook.appevents":    "Facebook Analytics",
    "com.facebook.ads":          "Facebook Audience Network",
    "com.mopub":                 "MoPub",
    "com.chartboost":            "Chartboost",
    "com.unity3d.ads":           "Unity Ads",
    "com.ironsource":            "ironSource",
    "com.applovin":              "AppLovin",
    "com.vungle":                "Vungle",
    "com.inmobi":                "InMobi",
    "com.amazon.device.ads":     "Amazon Ads",
    "com.moat":                  "Moat Analytics",
    "com.criteo":                "Criteo",
    "com.kochava":               "Kochava",
    "com.singular.sdk":          "Singular",
    "io.radar.sdk":              "Radar.io (Geo-Tracking)",
    "com.onesignal":             "OneSignal (Push/Tracking)",
    "com.urbanairship":          "Airship (Urban Airship)",
    "com.crashlytics":           "Crashlytics/Firebase Crashlytics",
    "com.bugsnag":               "Bugsnag",
    "io.sentry":                 "Sentry",
    "com.mixpanel":              "Mixpanel",
    "com.amplitude.api":         "Amplitude Analytics",
    "com.segment.analytics":     "Segment",
    "com.intercom.android":      "Intercom",
    "com.braze":                 "Braze (Appboy)",
    "com.clevertap":             "CleverTap",
    "com.localytics":            "Localytics",
    "com.quantcast":             "Quantcast",
    "com.comscore":              "Comscore",
    "com.flurry.android":        "Yahoo Flurry",
    "com.tapjoy":                "Tapjoy",
    "com.adcolony":              "AdColony",
    "com.startapp.android":      "StartApp",
    "com.waps":                  "WAPS",
    "com.mobvista":              "Mintegral/Mobvista",
    "com.mintegral":             "Mintegral",
    "net.pubnative":             "PubNative",
    "com.taboola":               "Taboola",
    "com.outbrain":              "Outbrain",
    "com.revenuecat.purchases":  "RevenueCat (IAP-Tracking)",
    "com.android.installreferrer": "Install Referrer (Google)",
    "com.tenjin":                "Tenjin",
    "com.liftoff":               "Liftoff",
    "com.datadog.android":       "Datadog",
    "com.newrelic.agent":        "New Relic",
}

PRIVACY_RISK_TRACKERS = {
    "io.radar.sdk", "com.onesignal", "com.adjust.sdk", "com.appsflyer",
    "com.kochava", "com.singular.sdk", "com.facebook.appevents",
    "com.facebook.ads", "com.flurry.android",
}


def tracker_sdk_scan(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Paketname (leer = lokale APK-Datei)").strip()
    local = ""
    if pkg:
        paths = [ln.split("package:", 1)[1].strip()
                 for ln in adb.shell(f"pm path {pkg}").splitlines() if "package:" in ln]
        if not paths:
            ui.err("Paket nicht gefunden."); ui.pause(); return
        base = next((x for x in paths if x.endswith("base.apk")), paths[0])
        local = os.path.join(OUT, f"tk_{pkg}.apk")
        ui.info("Lade APK …")
        adb.raw(["pull", base, local], timeout=300)
    else:
        local = os.path.expanduser(ui.ask("APK-Pfad").strip())
    if not os.path.isfile(local):
        ui.err("Datei nicht gefunden."); ui.pause(); return
    ui.clear(); ui.rule("Tracker-SDK-Erkennung", ui.CYAN)
    ui.info("Durchsuche DEX-Klassen nach bekannten SDK-Signaturen …")
    found: dict[str, str] = {}
    try:
        with zipfile.ZipFile(local) as zf:
            dex_files = [n for n in zf.namelist() if n.endswith(".dex")]
            for dex in dex_files[:5]:
                try:
                    data = zf.read(dex).decode("latin-1", errors="replace")
                    for pkg_prefix, sdk_name in KNOWN_TRACKERS.items():
                        if pkg_prefix.replace(".", "/") in data or pkg_prefix in data:
                            found[pkg_prefix] = sdk_name
                except (KeyError, OSError):
                    pass
    except Exception as e:  # noqa: BLE001
        ui.err(str(e)); ui.pause(); return
    print()
    if not found:
        ui.ok("Keine bekannten Tracker-SDKs erkannt.")
    else:
        high_risk = {k: v for k, v in found.items() if k in PRIVACY_RISK_TRACKERS}
        normal = {k: v for k, v in found.items() if k not in PRIVACY_RISK_TRACKERS}
        if high_risk:
            print(f"  {ui.BRED}{ui.BOLD}⚠ DATENSCHUTZ-RISIKO ({len(high_risk)} SDKs):{ui.RESET}")
            for k, v in sorted(high_risk.items()):
                print(f"   {ui.BRED}■{ui.RESET} {v}  {ui.GREY}({k}){ui.RESET}")
            print()
        if normal:
            print(f"  {ui.BYELLOW}TRACKING-SDKs ({len(normal)}):{ui.RESET}")
            for k, v in sorted(normal.items()):
                print(f"   {ui.BYELLOW}○{ui.RESET} {v}  {ui.GREY}({k}){ui.RESET}")
    out_body = (f"# TRACKER-SDK-SCAN: {local}\n# {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                + "\n".join(f"{v} ({k})" for k, v in sorted(found.items())) + "\n")
    p = os.path.join(OUT, f"trackers_{int(time.time())}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(out_body)
    print(); ui.ok(f"Gesamt: {len(found)} SDK(s) erkannt → {p}")
    ui.pause()


# ========================================================================== #
#  9. DEX-Statistik & Obfuskierungs-Score
# ========================================================================== #

def _dex_stats(data: bytes) -> dict:
    """Liest DEX-Header und schätzt Obfuskierungs-Score."""
    if len(data) < 112 or data[:3] != b"dex":
        return {}
    string_ids_size = struct.unpack_from("<I", data, 56)[0]
    type_ids_size   = struct.unpack_from("<I", data, 64)[0]
    proto_ids_size  = struct.unpack_from("<I", data, 72)[0]
    field_ids_size  = struct.unpack_from("<I", data, 80)[0]
    method_ids_size = struct.unpack_from("<I", data, 88)[0]
    class_defs_size = struct.unpack_from("<I", data, 96)[0]
    # Obfuskierungs-Indikator: kurze Klassennamen (a/b/c/...) dominieren?
    strings_raw = data[
        struct.unpack_from("<I", data, 60)[0]:
        struct.unpack_from("<I", data, 60)[0] + min(string_ids_size * 4, 50000)
    ]
    short_strings = len(re.findall(rb"\x00[a-z]\x00", strings_raw))
    obf_score = min(100, short_strings * 5)
    return {
        "strings": string_ids_size,
        "types":   type_ids_size,
        "protos":  proto_ids_size,
        "fields":  field_ids_size,
        "methods": method_ids_size,
        "classes": class_defs_size,
        "obf_score": obf_score,
        "obf_level": ("STARK" if obf_score > 60 else "MITTEL" if obf_score > 20 else "GERING"),
    }


def dex_statistics(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Paketname (leer = lokale APK)").strip()
    local = ""
    if pkg:
        paths = [ln.split("package:", 1)[1].strip()
                 for ln in adb.shell(f"pm path {pkg}").splitlines() if "package:" in ln]
        if not paths:
            ui.err("Paket nicht gefunden."); ui.pause(); return
        base = next((x for x in paths if x.endswith("base.apk")), paths[0])
        local = os.path.join(OUT, f"dex_{pkg}.apk")
        ui.info("Lade APK …")
        adb.raw(["pull", base, local], timeout=300)
    else:
        local = os.path.expanduser(ui.ask("APK-Pfad").strip())
    if not os.path.isfile(local):
        ui.err("Datei nicht gefunden."); ui.pause(); return
    ui.clear(); ui.rule("DEX-Statistik & Obfuskierungs-Score", ui.CYAN)
    total_methods = 0
    total_classes = 0
    try:
        with zipfile.ZipFile(local) as zf:
            dex_files = sorted(n for n in zf.namelist() if n.endswith(".dex"))
            for dex in dex_files:
                try:
                    data = zf.read(dex)
                    stats = _dex_stats(data)
                    if not stats:
                        continue
                    total_methods += stats["methods"]
                    total_classes += stats["classes"]
                    obf_color = (ui.BRED if stats["obf_score"] > 60
                                 else ui.BYELLOW if stats["obf_score"] > 20
                                 else ui.BGREEN)
                    print(f"\n  {ui.BCYAN}{ui.BOLD}■ {dex}{ui.RESET}  ({len(data):,} Bytes)")
                    print(f"    Klassen:   {stats['classes']:>6,}")
                    print(f"    Methoden:  {stats['methods']:>6,}")
                    print(f"    Felder:    {stats['fields']:>6,}")
                    print(f"    Typen:     {stats['types']:>6,}")
                    print(f"    Strings:   {stats['strings']:>6,}")
                    print(f"    Obfusk.:   {obf_color}{stats['obf_level']} (Score: {stats['obf_score']}/100){ui.RESET}")
                except (KeyError, OSError):
                    pass
    except Exception as e:  # noqa: BLE001
        ui.err(str(e)); ui.pause(); return
    print(f"\n  {ui.BOLD}GESAMT: {total_classes:,} Klassen · {total_methods:,} Methoden{ui.RESET}")
    if total_methods > 65536:
        ui.warn(f"MULTIDEX! {total_methods:,} Methoden > 65536 Limit → mehrere DEX-Files erforderlich")
    print()
    ui.pause()


# ========================================================================== #
#  10. App-Kommunikations-Analyse (Live ADB)
# ========================================================================== #

def app_communication(adb: ADB, dev, st) -> None:
    pkg = ui.ask("Paketname").strip()
    if not pkg:
        return
    ui.clear(); ui.rule(f"App-Kommunikations-Analyse · {pkg}", ui.CYAN)
    lines = [f"# APP-KOMMUNIKATION: {pkg}", f"# {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]

    # Netzwerkverbindungen
    ui.info("Netzwerkverbindungen (netstat) …")
    netstat = adb.shell("cat /proc/net/tcp /proc/net/tcp6 2>/dev/null | head -n 100")
    pid = adb.shell(f"pidof {pkg} 2>/dev/null").strip()
    pid_conns = ""
    if pid:
        pid_conns = adb.shell(f"cat /proc/{pid}/net/tcp /proc/{pid}/net/tcp6 2>/dev/null | head -n 50")
    lines += ["== NETZWERKVERBINDUNGEN ==",
              f"PID: {pid or 'App läuft nicht'}",
              pid_conns or netstat or "(keine)", ""]

    # DNS-Abfragen über logcat
    ui.info("DNS-Abfragen (logcat) …")
    dns = adb.shell(f"logcat -d -t 200 -s 'NetworkSecurityConfig,ConnectivityManager,DnsResolver' 2>/dev/null "
                    f"| grep -i '{pkg}\\|dns\\|connect' | tail -n 30")
    lines += ["== DNS / NETZWERK-LOG ==", dns or "(keine Einträge)", ""]

    # Exportierte Aktivitäten / Einstiegspunkte
    ui.info("Exportierte Aktivitäten …")
    exported = adb.shell(
        f"dumpsys package {pkg} | grep -A2 'Activity\\|Service\\|Receiver' | grep 'permission\\|exported' | head -n 40"
    )
    lines += ["== EXPORTIERTE KOMPONENTEN ==", exported or "(keine / nicht abrufbar)", ""]

    # Offene Dateien
    ui.info("Offene Dateien (procfs) …")
    open_files = ""
    if pid:
        open_files = adb.shell(f"ls -la /proc/{pid}/fd 2>/dev/null | head -n 50")
    lines += ["== OFFENE DATEIEN ==", open_files or "(App läuft nicht oder kein Zugriff)", ""]

    # Wakelock-Status
    ui.info("Wakelock-Status …")
    wakelock = adb.shell(f"dumpsys power 2>/dev/null | grep -i '{pkg}' | head -n 10")
    lines += ["== WAKELOCK (Hintergrundaktivität) ==", wakelock or "(keine Wakelocks)", ""]

    body = "\n".join(lines) + "\n"
    p = os.path.join(OUT, f"comms_{re.sub(r'[^A-Za-z0-9_]', '_', pkg)}_{int(time.time())}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    ui.show_report(body, f"App-Kommunikation · {pkg}", p)
    ui.pause()


# ========================================================================== #
#  IOC-Scan (geräteweit)
# ========================================================================== #
def ioc_scan(adb: ADB, dev, st) -> None:
    ui.clear(); ui.rule("IOC-Scan (Indicators of Compromise)", ui.CYAN)
    findings = []

    # 1) hosts-Hijack
    hosts = adb.shell("cat /system/etc/hosts 2>/dev/null")
    extra = [l for l in hosts.splitlines()
             if l.strip() and not l.strip().startswith("#")
             and l.split() and l.split()[0] not in ("127.0.0.1", "::1")]
    if extra:
        findings.append(("hosts-Datei manipuliert", "\n".join(extra[:20])))

    # 2) Accessibility / Device-Admin / Notification-Listener
    for label, cmd in [
        ("Accessibility-Dienste", "settings get secure enabled_accessibility_services"),
        ("Notification-Listener", "settings get secure enabled_notification_listeners"),
    ]:
        v = adb.shell(cmd).strip()
        if v and v.lower() not in ("null", ""):
            findings.append((label, v))
    admin_set = admin_pkgs(adb.shell("dumpsys device_policy 2>/dev/null", timeout=20))
    if admin_set:
        findings.append(("Aktive Device-Admins (Pakete)", "\n".join(sorted(admin_set))))

    # 3) Bekannte Stalkerware-Pakete installiert?
    installed = adb.shell("pm list packages")
    hits = [p for p in KNOWN_STALKERWARE if f"package:{p}" in installed]
    if hits:
        findings.append(("BEKANNTE STALKERWARE installiert", "\n".join(hits)))

    # 4) Apps mit kritischer Rechte-Kombi + versteckt (ohne Launcher-Icon).
    #    Exakte Launcher-Paket-MENGE statt Substring-Test (sonst matchen Teil-Namen falsch).
    third = [l.split(":", 1)[1] for l in adb.shell("pm list packages -3").splitlines() if ":" in l]
    launchers = launcher_pkgs(adb)
    combo_hidden = []
    for pkg in third:
        granted = set(re.findall(r"android\.permission\.(\w+)",
                                 adb.shell(f"dumpsys package {shq(pkg)} | grep granted=true | head -n 60")))
        if all(c in granted for c in STALKER_COMBO) and pkg not in launchers:
            combo_hidden.append(pkg)
    if combo_hidden:
        findings.append(("Versteckte Apps mit Stalkerware-Rechten", "\n".join(combo_hidden)))

    # Ausgabe – vollständiger Bericht direkt im Terminal
    out = ["# IOC-SCAN", f"# {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    if not findings:
        out.append("Keine Indikatoren gefunden.")
    for title, detail in findings:
        out += [f"== {title} ==", detail, ""]
    body = "\n".join(out) + "\n"
    p = os.path.join(OUT, "ioc_scan.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    if not findings:
        ui.ok("Keine Indikatoren gefunden.")
    else:
        ui.warn(f"{len(findings)} Indikator-Gruppe(n) gefunden – vollständig unten:")
    ui.show_report(body, "IOC-Scan · vollständiger Bericht", p, note="IOC-Bericht")
    ui.pause()


# ========================================================================== #
#  Menü
# ========================================================================== #
def menu(adb: ADB, dev, st) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🧪 APK-Analyse · Risk-Scoring · IOC · Tracker · DEX · Zertifikat")
        ch = ui.menu("Module", [
            ("1",  "📦 Installierte App analysieren (APK ziehen → Offline-Statik)"),
            ("2",  "📂 Lokale .apk-Datei analysieren"),
            ("3",  "📊 App-Risiko-Inventar (alle Apps bewerten & ranken + Tiefen-Analyse)"),
            ("4",  "🚨 IOC-Scan (hosts/Accessibility/Device-Admin/Stalkerware)"),
            ("5",  f"{ui.BCYAN}{ui.BOLD}🔬 Risiko-App KOMPLETT analysieren (Statik + ALLE Verzeichnisse){ui.RESET}"),
            ("6",  "🔍 Tiefen-String-Scan (URLs/E-Mails/Base64/API-Keys aus DEX)"),
            ("7",  "📜 Zertifikat-Analyse (Signier-Cert, Fingerprint, Schema v1/v2/v3)"),
            ("8",  "📡 Tracker-SDK-Erkennung (50+ bekannte SDKs: Adjust/Firebase/AppLovin …)"),
            ("9",  "📊 DEX-Statistik & Obfuskierungs-Score (Klassen/Methoden/MultiDEX)"),
            ("10", "🌐 App-Kommunikations-Analyse (Live: Netzwerk/DNS/Dateien/Wakelock)"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        try:
            if ch == "1":
                analyze_installed(adb, st)
            elif ch == "2":
                analyze_local(adb, dev, st)
            elif ch == "3":
                risk_inventory(adb, dev, st)
            elif ch == "4":
                ioc_scan(adb, dev, st)
            elif ch == "5":
                deep_risk_menu(adb, dev, st)
            elif ch == "6":
                deep_string_scan(adb, dev, st)
            elif ch == "7":
                cert_analysis(adb, dev, st)
            elif ch == "8":
                tracker_sdk_scan(adb, dev, st)
            elif ch == "9":
                dex_statistics(adb, dev, st)
            elif ch == "10":
                app_communication(adb, dev, st)
            else:
                ui.warn("Ungültige Auswahl.")
        except Exception as e:  # noqa: BLE001
            ui.err(f"Fehler: {e}")
            LOG.exception("apkscan", e)
            ui.pause()
