"""Auto-Analyse: sammelt sofort nach Geräteerkennung die wichtigsten Kennzahlen
und rendert ein Übersichts-Dashboard."""
from __future__ import annotations

import re

from . import ui
from .adb import ADB, Device


class Dashboard:
    """Dashboard für System-Übersicht."""

    def __init__(self, adb: ADB = None):
        """Initialisiere Dashboard."""
        self.adb = adb
        self.data = {}

    def show_dashboard(self) -> None:
        """Zeige Dashboard."""
        ui.clear()
        ui.banner(subtitle="📊 SYSTEM DASHBOARD")
        print("\n  System ist betriebsbereit!\n")
        ui.pause()

    def collect_data(self) -> dict:
        """Sammle Dashboard-Daten."""
        return {"status": "collected"}


def _first(*vals) -> str:
    for v in vals:
        if v and v.strip() and v.strip().lower() not in ("unknown", "0"):
            return v.strip()
    return ""


def collect(adb: ADB, dev: Device) -> dict:
    """Sammelt die Kerndaten. Schnell gehaltene, fehlertolerante Reads."""
    g = adb.getprop
    d: dict = {}

    # Hardware & Identität
    d["model"] = _first(g("ro.product.model"), g("ro.product.vendor.model"))
    d["brand"] = _first(g("ro.product.brand"), g("ro.product.manufacturer"))
    d["device"] = _first(g("ro.product.device"), g("ro.product.vendor.device"))
    d["serial"] = _first(g("ro.serialno"), dev.serial)
    d["abi"] = _first(g("ro.product.cpu.abi"))
    d["abilist"] = g("ro.product.cpu.abilist")

    # Android / Build
    d["android"] = g("ro.build.version.release")
    d["sdk"] = g("ro.build.version.sdk")
    d["security_patch"] = g("ro.build.version.security_patch")
    d["build"] = g("ro.build.display.id")
    d["fingerprint"] = g("ro.build.fingerprint")

    # Kernel & Chipsatz (für Hersteller-Flash-Zweige)
    d["kernel"] = adb.shell("uname -r -m")
    d["platform"] = _first(g("ro.board.platform"), g("ro.hardware"))
    d["hardware"] = g("ro.hardware")
    plat = (d["platform"] + d["hardware"]).lower()
    d["is_mtk"] = plat.startswith("mt") or "mt6" in plat or "mt8" in plat or "mediatek" in plat
    d["is_qcom"] = any(x in plat for x in ("qcom", "msm", "sdm", "sm6", "sm7", "sm8", "kona", "lahaina"))

    # Hersteller-Flags für brand-spezifische Menüs
    brand_lc = d["brand"].lower()
    d["is_xiaomi"]  = brand_lc in ("xiaomi", "redmi", "poco")
    d["is_pixel"]   = brand_lc in ("google",)
    d["is_oneplus"] = brand_lc in ("oneplus", "oppo", "realme")
    d["is_motorola"] = brand_lc in ("motorola", "moto", "lenovo")
    d["is_huawei"]  = brand_lc in ("huawei", "honor")

    # Bootloader / Verschlüsselung / Slot
    d["bootloader_unlocked"] = _first(g("ro.boot.flash.locked"), g("ro.boot.verifiedbootstate"), g("sys.oem_unlock_allowed"))
    d["verifiedboot"] = g("ro.boot.verifiedbootstate")
    d["slot"] = _first(g("ro.boot.slot_suffix"))
    d["crypto"] = _first(g("ro.crypto.state"), g("ro.crypto.type"))
    d["selinux"] = adb.shell("getenforce")

    # Akku
    bat = adb.shell("dumpsys battery")
    d["bat_level"] = _grep(bat, r"level:\s*(\d+)")
    d["bat_temp"] = _temp(_grep(bat, r"temperature:\s*(\d+)"))
    d["bat_volt"] = _volt(_grep(bat, r"voltage:\s*(\d+)"))
    d["bat_health"] = _health(_grep(bat, r"health:\s*(\d+)"))
    d["bat_plug"] = _plug(bat)
    d["bat_tech"] = _grep(bat, r"technology:\s*(\S+)")

    # RAM
    mem = adb.shell("cat /proc/meminfo")
    total = _int(_grep(mem, r"MemTotal:\s*(\d+)"))
    avail = _int(_grep(mem, r"MemAvailable:\s*(\d+)"))
    if total:
        d["ram_total"] = f"{total/1024/1024:.1f} GB"
        if avail:
            d["ram_free"] = f"{avail/1024/1024:.1f} GB frei ({avail*100//total}%)"

    # Speicher (interner /data)
    dfout = adb.shell("df -h /data")
    d["storage"] = _df_data(dfout)

    # Display
    size = adb.shell("wm size")
    dens = adb.shell("wm density")
    d["display"] = _first(_grep(size, r"Physical size:\s*(\S+)"), _grep(size, r"size:\s*(\S+)"))
    d["dpi"] = _first(_grep(dens, r"Physical density:\s*(\d+)"), _grep(dens, r"density:\s*(\d+)"))

    # Netzwerk
    d["wifi_ip"] = _ip(adb.shell("ip -f inet addr show wlan0"))
    d["mobile_ip"] = _ip(adb.shell("ip -f inet addr show rmnet_data0")) or _ip(adb.shell("ip -f inet addr show rmnet0"))
    d["wifi_mac"] = _first(adb.shell("cat /sys/class/net/wlan0/address"))

    # Mobilfunk / SIM
    d["operator"] = _first(g("gsm.operator.alpha"), g("gsm.sim.operator.alpha"))
    d["net_type"] = g("gsm.network.type")
    d["sim_state"] = g("gsm.sim.state")
    d["country"] = _first(g("gsm.operator.iso-country"), g("gsm.sim.operator.iso-country"))
    d["baseband"] = g("gsm.version.baseband")

    # Root (setzt zugleich adb.root_mode)
    mode, detail = adb.root_method()
    d["root"] = mode != "none"
    d["root_mode"] = mode
    d["root_detail"] = detail
    d["su_bin"] = adb.shell("command -v su 2>/dev/null || which su 2>/dev/null")
    d["magisk"] = adb.shell("magisk -V 2>/dev/null").strip() or (detail if mode == "magisk" else "")

    # Schnell-Triage-Signale (wenige schnelle, read-only Reads)
    s = adb.shell
    d["dev_opts"] = s("settings get global development_settings_enabled").strip()
    d["adb_wifi"] = s("settings get global adb_wifi_enabled").strip()
    d["unknown_src"] = s("settings get secure install_non_market_apps").strip()
    d["a11y"] = s("settings get secure enabled_accessibility_services").strip()
    d["vpn_app"] = s("settings get global always_on_vpn_app 2>/dev/null").strip()
    d["proxy"] = s("settings get global http_proxy").strip()
    d["admins"] = s("dumpsys device_policy 2>/dev/null | grep -ciE 'Active admin|admin='").strip()
    d["n_third"] = str(sum(1 for ln in s("pm list packages -3").splitlines() if "package:" in ln))
    d["n_accounts"] = str(len(re.findall(r"Account\s*\{", s("dumpsys account"))))

    return d


# --- kleine Parser-Helfer -------------------------------------------------
def _grep(text: str, pat: str) -> str:
    m = re.search(pat, text or "")
    return m.group(1) if m else ""


def _int(s: str) -> int:
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


def _temp(s: str) -> str:
    return f"{int(s)/10:.1f} °C" if s.isdigit() else ""


def _volt(s: str) -> str:
    return f"{int(s)/1000:.3f} V" if s.isdigit() else ""


def _health(s: str) -> str:
    return {"1": "Unbekannt", "2": "Gut", "3": "Überhitzt", "4": "Defekt",
            "5": "Überspannung", "6": "Fehler", "7": "Kalt"}.get(s, s)


def _plug(bat: str) -> str:
    if re.search(r"AC powered:\s*true", bat):
        return "lädt (AC)"
    if re.search(r"USB powered:\s*true", bat):
        return "lädt (USB)"
    if re.search(r"Wireless powered:\s*true", bat):
        return "lädt (Wireless)"
    return "Akku"


def _df_data(dfout: str) -> str:
    for line in dfout.splitlines():
        if "/data" in line or line.split()[-1:] == ["/data"]:
            parts = line.split()
            if len(parts) >= 5:
                return f"{parts[2]} / {parts[1]} belegt ({parts[4]})"
    return ""


def _ip(text: str) -> str:
    return _grep(text, r"inet (\d+\.\d+\.\d+\.\d+)")


def _patch_age(patch: str) -> int:
    """Alter des Sicherheits-Patches in Monaten (0 wenn unbekannt)."""
    import time as _t
    m = re.match(r"(\d{4})-(\d{2})", patch or "")
    if not m:
        return 0
    y, mo = int(m.group(1)), int(m.group(2))
    now = _t.localtime()
    return max(0, (now.tm_year - y) * 12 + (now.tm_mon - mo))


def _triage(d: dict) -> list:
    """Schnell-Triage: Liste von (schwere, text). schwere ∈ crit|warn|info."""
    out = []
    bl = (d.get("bootloader_unlocked", "") or "").lower()
    if bl in ("0", "false", "unlocked", "orange") or (d.get("verifiedboot", "") or "").lower() == "orange":
        out.append(("crit", "Bootloader ENTSPERRT – Gerät könnte modifiziert/geflasht worden sein"))
    if "unencrypted" in (d.get("crypto", "") or "").lower():
        out.append(("crit", "Datenpartition UNVERSCHLÜSSELT"))
    if d.get("adb_wifi") == "1":
        out.append(("crit", "WLAN-ADB (kabellos) AKTIV – Fernzugriff möglich"))
    if d.get("root"):
        out.append(("warn", "Gerät GEROOTET – System-Integrität nicht garantiert"))
    if d.get("unknown_src") == "1":
        out.append(("warn", "Installation aus unbekannten Quellen erlaubt"))
    a11y = d.get("a11y", "")
    if a11y and a11y.lower() not in ("null", ""):
        out.append(("warn", f"Accessibility-Dienste aktiv (Keylogger-/Spy-Risiko): {a11y[:60]}"))
    if _int(d.get("admins", "0")) > 0:
        out.append(("warn", f"{d.get('admins')} Device-Admin(s) aktiv (Geräteverwaltung)"))
    proxy = d.get("proxy", "")
    if proxy and proxy not in ("null", ":0", ""):
        out.append(("warn", f"HTTP-Proxy gesetzt: {proxy} (Traffic-Umleitung möglich)"))
    age = _patch_age(d.get("security_patch", ""))
    if age >= 6:
        out.append(("warn", f"Sicherheits-Patch {age} Monate alt (veraltet)"))
    vpn = d.get("vpn_app", "")
    if vpn and vpn not in ("null", ""):
        out.append(("info", f"Always-on-VPN aktiv: {vpn}"))
    if d.get("dev_opts") == "1":
        out.append(("info", "Entwickleroptionen aktiviert"))
    return out


# --- Rendering ------------------------------------------------------------
def render(adb: ADB, dev: Device, d: dict) -> None:
    ui.clear()
    title = f"{d.get('brand','?')} {d.get('model','?')}".strip()
    ui.banner(subtitle=f"Verbunden: {title}  •  {dev.transport.upper()}  •  {dev.serial}")

    ui.rule("Hardware & Identität", ui.CYAN)
    ui.kv("Modell", f"{d.get('brand','')} {d.get('model','')} ({d.get('device','')})")
    ui.kv("Seriennummer", d.get("serial"))
    ui.kv("CPU-Architektur (ABI)", f"{d.get('abi','')}   {ui.GREY}{d.get('abilist','')}{ui.RESET}")
    ui.kv("Kernel", d.get("kernel"))

    ui.rule("Android & Sicherheit", ui.CYAN)
    ui.kv("Android-Version", f"{d.get('android','')}   (API {d.get('sdk','')})")
    ui.kv("Build", d.get("build"))
    ui.kv("Security-Patch", d.get("security_patch"))
    ui.kv("SELinux", d.get("selinux"))
    ui.kv("Verschlüsselung", d.get("crypto"))

    bl = d.get("bootloader_unlocked", "")
    bl_txt = _bootloader_text(bl, d.get("verifiedboot", ""))
    ui.kv("Bootloader", bl_txt)
    ui.kv("Aktiver Slot (A/B)", d.get("slot") or "—  (kein A/B)")

    # Root prominent
    if d.get("root"):
        mode = d.get("root_mode", "")
        label = {"adb-root": "adb-root / Fakeroot", "magisk": "Magisk",
                 "su": "su-Binary"}.get(mode, mode)
        det = f"  •  {d.get('root_detail','')}" if d.get("root_detail") else ""
        ui.kv("ROOT-STATUS", f"{ui.BGREEN}{ui.BOLD}● GEROOTET{ui.RESET} ({label}){det}"
              f"  {ui.BYELLOW}→ ROOT-ARSENAL: Menüpunkt X{ui.RESET}")
    else:
        ui.kv("ROOT-STATUS", f"{ui.GREY}○ nicht gerootet{ui.RESET}  {ui.DIM}(Assistent: Menüpunkt R){ui.RESET}")

    ui.rule("Akku & Leistung", ui.CYAN)
    lvl = d.get("bat_level", "")
    ui.kv("Akku", f"{_battery_bar(lvl)}  {d.get('bat_plug','')}")
    ui.kv("Temperatur / Spannung", f"{d.get('bat_temp','')}   {d.get('bat_volt','')}   {ui.GREY}{d.get('bat_health','')}{ui.RESET}")
    ui.kv("RAM", f"{d.get('ram_free','?')}  von  {d.get('ram_total','?')}")
    ui.kv("Speicher (/data)", d.get("storage"))
    ui.kv("Display", f"{d.get('display','')}  @ {d.get('dpi','')} dpi")

    ui.rule("Netzwerk & Mobilfunk", ui.CYAN)
    ui.kv("WLAN-IP / MAC", f"{d.get('wifi_ip','—')}   {ui.GREY}{d.get('wifi_mac','')}{ui.RESET}")
    ui.kv("Mobil-IP", d.get("mobile_ip"))
    ui.kv("Netzbetreiber", f"{d.get('operator','—')}  ({d.get('country','')})")
    ui.kv("Netztyp / SIM", f"{d.get('net_type','—')}   SIM: {d.get('sim_state','—')}")
    ui.kv("Baseband", d.get("baseband"))

    # Schnell-Triage / Sicherheits-Ampel
    tri = _triage(d)
    ncrit = sum(1 for s, _ in tri if s == "crit")
    ui.rule(f"🔎 Schnell-Triage (Sicherheit & Auffälligkeiten) – {len(tri)} Punkte"
            + (f", {ncrit} KRITISCH" if ncrit else ""), ui.YELLOW)
    if not tri:
        ui.ok("Keine offensichtlichen Auffälligkeiten in der Schnellprüfung.")
    for sev, txt in tri:
        if sev == "crit":
            ui.crit(txt)
        elif sev == "warn":
            print(f"  {ui.BYELLOW}⚠{ui.RESET} {txt}")
        else:
            print(f"  {ui.BCYAN}ℹ{ui.RESET} {txt}")
    ui.kv("Drittanbieter-Apps", d.get("n_third"), key_w=26)
    ui.kv("Konten", d.get("n_accounts"), key_w=26)
    print()


def _bootloader_text(flag: str, vbstate: str) -> str:
    f = (flag or "").lower()
    if f in ("0", "false", "unlocked", "orange") or vbstate.lower() == "orange":
        return ui.pulse("● ENTSPERRT (unlocked)")
    if f in ("1", "true", "locked", "green") or vbstate.lower() == "green":
        return f"{ui.BGREEN}● gesperrt (locked){ui.RESET}"
    return flag or "unbekannt"


def _battery_bar(level: str) -> str:
    try:
        lv = int(level)
    except (TypeError, ValueError):
        return "—"
    filled = lv * 10 // 100
    bar = "█" * filled + "░" * (10 - filled)
    col = ui.BGREEN if lv > 50 else ui.BYELLOW if lv > 20 else ui.BRED
    return f"{col}{bar}{ui.RESET} {lv}%"
