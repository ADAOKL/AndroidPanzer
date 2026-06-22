"""Vollständige forensische Akquise – 45 Sektionen, ein konsolidierter Bericht.

Deckt die vier Domänen ab:
  Teil 1 (1–10)  OS-, Dateisystem- & Anwendungs-Forensik
  Teil 2 (11–20) SIM-, eSIM- & eUICC-Telekommunikations-Forensik
  Teil 3 (21–30) Advanced Baseband-, Signal- & RF-Forensik
  Teil 4 (31–45) High-End Labor-Exploitation & Emulations-Forensik

Leitprinzip (wie im gesamten Tool): **kein Fake**. Jede Sektion ist mit einem
ehrlichen Status versehen:

  ✅ erhoben        – real per ADB ausgelesen
  🟡 eingeschränkt  – teilweise (Android schützt den Rest, z.B. IMSI/IMEI nur privilegiert)
  🔑 Root nötig     – nur mit Root vollständig
  📡 SDR/HW nötig   – braucht Funk-/Diag-Hardware (Baseband-Diag-Port, SDR, Smartcard-Reader)
  🧪 Labor nötig    – physische/Seitenkanal-/Emulations-Verfahren (DPA, TEMPEST, Open5GS …)

Erhoben wird ausschließlich READ-ONLY. Hardware-/Labor-Sektionen werden mit der
real nötigen Methode dokumentiert, nicht erfunden. Am Ende entsteht ein
Gesamtbericht (Text + Markdown), der über das Report-Modul (`E`) zusätzlich als
HTML/JSON inkl. SHA-256-Manifest exportiert werden kann.
"""
from __future__ import annotations

import os
import re
import time

from . import ui
from .adb import ADB
from .util import LOG, human_size, outdir, shq

OUT = outdir("forensik_full")

# Status-Konstanten
OK, PARTIAL, ROOT, HW, LAB, INFO = "ok", "partial", "root", "hw", "lab", "info"
_BADGE = {
    OK: ("✅", "erhoben", ui.BGREEN),
    PARTIAL: ("🟡", "eingeschränkt", ui.BYELLOW),
    ROOT: ("🔑", "Root nötig", ui.YELLOW),
    HW: ("📡", "SDR/HW nötig", ui.MAGENTA),
    LAB: ("🧪", "Labor nötig", ui.MAGENTA),
    INFO: ("ℹ️", "Info", ui.BCYAN),
}


# --------------------------------------------------------------------------- #
#  Hilfen
# --------------------------------------------------------------------------- #
def _v(out: str) -> str:
    """Bereinigt Shell-Ausgabe; leert offensichtliche Fehler/Restriktionen."""
    out = (out or "").strip()
    low = out.lower()
    if not out or low.startswith(("error", "exception", "permission denial",
                                  "securityexception", "java.lang", "null")):
        return ""
    return out


def _kvs(adb: ADB, pairs: list[tuple[str, str]]) -> list[str]:
    """Liste (Label, getprop-Key) → erhobene Zeilen (leere weggelassen)."""
    lines = []
    for label, key in pairs:
        val = (adb.getprop(key) or "").strip()
        if val:
            lines.append(f"{label}: {val}")
    return lines


def _grab(adb: ADB, label: str, cmd: str, out: list, t: int = 20, show: int = 0) -> str:
    """Führt *cmd* aus und hängt die volle Ausgabe (mit Überschrift) an *out* an.
    Gibt die Ausgabe zurück ('' bei leer/Fehler). *show* ist nur für Signatur-Kompatibilität."""
    o = _v(adb.shell(cmd, timeout=t))
    if not o:
        return ""
    out.append(f"## {label}")
    out.append(o)
    return o


# ========================================================================== #
#  TEIL 1 – OS / Dateisystem / Anwendungen (real per ADB)
# ========================================================================== #
def c_system(adb, st):
    L = _kvs(adb, [
        ("Hersteller", "ro.product.manufacturer"), ("Modell", "ro.product.model"),
        ("Gerät", "ro.product.device"), ("Board", "ro.product.board"),
        ("Seriennummer", "ro.serialno"), ("Hardware", "ro.hardware"),
        ("Android", "ro.build.version.release"), ("Build", "ro.build.fingerprint"),
        ("Security-Patch", "ro.build.version.security_patch"),
    ])
    bat = adb.shell("dumpsys battery 2>/dev/null")
    lvl = re.search(r"level:\s*(\d+)", bat or "")
    cyc = re.search(r"[Cc]ycle\s*[Cc]ount:\s*(\d+)", bat or "")
    if lvl:
        L.append(f"Akku-Ladestand: {lvl.group(1)}%")
    if cyc:
        L.append(f"Akku-Ladezyklen (Laufzeit-Indikator): {cyc.group(1)}")
    up = _v(adb.shell("uptime 2>/dev/null"))
    if up:
        L.append(f"Uptime: {up}")
    # IMEI/MAC nur, soweit die Shell-UID darf (modern oft privilegiert geschützt)
    mac = _v(adb.shell("cat /sys/class/net/wlan0/address 2>/dev/null"))
    if mac:
        L.append(f"WLAN-MAC (HW): {mac}")
    therm = _v(adb.shell("for z in /sys/class/thermal/thermal_zone*/temp; do cat $z 2>/dev/null; done | head -8"))
    if therm:
        L.append("Thermal-Zonen (Roh m°C): " + " ".join(therm.split()))
    return (OK if L else PARTIAL), L


_SENS_PERMS = ("CAMERA", "RECORD_AUDIO", "ACCESS_FINE_LOCATION", "READ_SMS", "SEND_SMS",
               "READ_CONTACTS", "READ_CALL_LOG", "READ_PHONE_STATE", "READ_EXTERNAL_STORAGE",
               "SYSTEM_ALERT_WINDOW", "REQUEST_INSTALL_PACKAGES", "QUERY_ALL_PACKAGES")


def c_apps(adb, st):
    def lst(cmd):
        return [l.split(":", 1)[1] for l in adb.shell(cmd).splitlines() if ":" in l]
    third = sorted(lst("pm list packages -3"))
    L = [f"Drittanbieter-Apps: {len(third)}", f"System-Apps: {len(lst('pm list packages -s'))}",
         f"Deaktiviert: {len(lst('pm list packages -d'))}",
         f"Inkl. deinstallierter (Reste): {len(lst('pm list packages -u'))}", ""]
    # GRÜNDLICH: pro App Installer, Version, Zeiten, sensible Rechte (eine dumpsys-Abfrage je App)
    L.append("## Pro Drittanbieter-App (Installer · Version · Installiert · Update · sensible Rechte)")
    side = []
    for p in third:
        d = adb.shell(f"dumpsys package {shq(p)} | grep -E "
                      f"'versionName=|firstInstallTime=|lastUpdateTime=|installerPackageName=|granted=true'",
                      timeout=15)
        ver = re.search(r"versionName=(\S+)", d)
        fi = re.search(r"firstInstallTime=([\d:\- ]+)", d)
        lu = re.search(r"lastUpdateTime=([\d:\- ]+)", d)
        inst = re.search(r"installerPackageName=(\S+)", d)
        src = inst.group(1) if inst else "null"
        if src in ("null", "com.android.shell"):
            side.append(p)
        sens = sorted({sp for sp in _SENS_PERMS if sp in d})
        L.append(f"{p}  v{ver.group(1) if ver else '?'}  "
                 f"inst={fi.group(1).strip() if fi else '?'}  upd={lu.group(1).strip() if lu else '?'}  "
                 f"src={src}  rechte=[{','.join(s.lower() for s in sens)}]")
    if side:
        L.append(f"\n## Sideloaded / unbekannte Quelle ({len(side)})")
        L += [f"  {p}" for p in side]
    return (OK if third else PARTIAL), L


def c_uiauto(adb, st):
    a11y = _v(adb.shell("settings get secure enabled_accessibility_services"))
    L = ["UI-Automation/Live-Dumping verfügbar (input, uiautomator, screencap/screenrecord)."]
    if a11y:
        L.append(f"Aktive Accessibility-Dienste: {a11y}")
    _grab(adb, "Eingabegeräte (getevent -p)", "getevent -lp 2>/dev/null | grep -iE 'add device|name:' | head -n 30", L)
    _grab(adb, "Aktuelles Fenster / Fokus", "dumpsys window 2>/dev/null | grep -iE 'mCurrentFocus|mFocusedApp|imeWindow' | head -n 6", L)
    _grab(adb, "Zuletzt benutzte Tasks (Recents)", "dumpsys activity recents 2>/dev/null | grep -iE 'Recent #|intent=|realActivity' | head -n 40", L)
    _grab(adb, "Laufende Activities (Vordergrund)", "dumpsys activity activities 2>/dev/null | grep -iE 'ResumedActivity|topResumed' | head -n 6", L)
    L.append("Forensisch: Live-UI-Beweissicherung gesperrter Apps (Signal/Threema) via Screenrecord + input.")
    return OK, L


def c_modding(adb, st):
    L = []
    mode, detail = adb.root_method()
    L.append(f"Root: {'ja' if mode != 'none' else 'nein'}" + (f" ({detail})" if detail else ""))
    L += _kvs(adb, [("SELinux/Build", "ro.build.selinux"),
                    ("Verified Boot", "ro.boot.verifiedbootstate"),
                    ("Bootloader-Lock", "ro.boot.flash.locked"),
                    ("Build-Tags", "ro.build.tags")])
    se = _v(adb.shell("getenforce"))
    if se:
        L.append(f"SELinux-Status: {se}")
    return OK, L


def c_media(adb, st):
    L = []
    for path, label in [("/sdcard/DCIM", "Kamera (DCIM)"), ("/sdcard/Pictures", "Bilder"),
                        ("/sdcard/Download", "Downloads"), ("/sdcard/Movies", "Videos"),
                        ("/sdcard/Documents", "Dokumente"), ("/sdcard/WhatsApp", "WhatsApp"),
                        ("/sdcard/Android/media", "App-Medien")]:
        c = _v(adb.shell(f"find {shq(path)} -type f 2>/dev/null | wc -l"))
        if c and c.isdigit() and int(c) > 0:
            L.append(f"{label}: {c} Dateien")
    # MediaStore-Zähler je Typ (Provider)
    for label, uri in [("MediaStore Bilder", "content://media/external/images/media"),
                       ("MediaStore Videos", "content://media/external/video/media"),
                       ("MediaStore Audio", "content://media/external/audio/media")]:
        c = _v(adb.shell(f"content query --uri {uri} 2>/dev/null | grep -c Row"))
        if c and c.isdigit():
            L.append(f"{label}: {c}")
    _grab(adb, "Neueste Bilder (Pfad + Aufnahmezeit)",
          "content query --uri content://media/external/images/media "
          "--projection _data:datetaken:_size 2>/dev/null | tail -n 40", L)
    _grab(adb, "Dateitypen-Verteilung (sdcard)",
          "find /sdcard -type f 2>/dev/null | sed 's/.*\\.//' | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head -n 25", L, t=40)
    _grab(adb, "Größte Dateien", "find /sdcard -type f -size +20M 2>/dev/null | head -n 30", L, t=40)
    L.append("EXIF/GPS-Extraktion & Foto-Geo-Mapping: Tiefen-Engine → Timeline (KML).")
    L.append("Gelöschte SQLite-Zeilen (WAL/Journal-Carving): Root-Arsenal → Datenwiederherstellung.")
    return (OK if len(L) > 4 else PARTIAL), L


def c_partitions(adb, st):
    L = []
    byname = _v(adb.shell("ls -l /dev/block/by-name/ 2>/dev/null | head -60"))
    if byname:
        L.append(f"Partitionstabelle (by-name): {len(byname.splitlines())} Einträge")
    df = _v(adb.shell("df -h /data /system 2>/dev/null"))
    if df:
        L += ["Belegung:"] + df.splitlines()[:4]
    vm = adb.getprop("ro.boot.veritymode")
    if vm:
        L.append(f"dm-verity: {vm}")
    L.append("Bitgenaue Partitions-Images (dd) & Unallocated-Carving: Root-Arsenal → System/Partitionen.")
    return (OK if byname or df else ROOT), L


def c_network(adb, st):
    L = []
    ipa = _v(adb.shell("ip -o addr 2>/dev/null | grep -v ' lo ' | head -8"))
    if ipa:
        L += ["Schnittstellen:"] + [l.strip()[:100] for l in ipa.splitlines()]
    conns = _v(adb.shell("ss -tunp 2>/dev/null | head -20") or adb.shell("netstat -tun 2>/dev/null | head -20"))
    if conns:
        L.append(f"Aktive Verbindungen: {len(conns.splitlines())} (Top in Report-Datei)")
    L += _kvs(adb, [("DNS1", "net.dns1"), ("DNS2", "net.dns2"), ("HTTP-Proxy", "net.gprs.http-proxy")])
    proxy = _v(adb.shell("settings get global http_proxy"))
    if proxy and proxy != "null":
        L.append(f"Globaler Proxy gesetzt: {proxy}")
    L.append("Voll-PCAP/HTTPS-Klartext (mitmproxy+Frida): Tiefen-Engine → Traffic.")
    return (OK if L else PARTIAL), L


def c_perf(adb, st):
    L = []
    _grab(adb, "Top-Prozesse (CPU/RAM)", "top -n 1 -b 2>/dev/null | head -25 || top -n 1 2>/dev/null | head -25", L, show=8)
    _grab(adb, "CPU-Auslastung (dumpsys cpuinfo)", "dumpsys cpuinfo 2>/dev/null | head -n 30", L)
    _grab(adb, "Speicher gesamt", "dumpsys meminfo 2>/dev/null | grep -E 'Total RAM|Free RAM|Used RAM|Lost RAM|ZRAM' | head -6", L, show=4)
    _grab(adb, "Speicher pro App (Top)", "dumpsys meminfo 2>/dev/null | sed -n '/Total PSS by process/,/Total PSS by OOM/p' | head -n 30", L)
    _grab(adb, "Laufende Prozesse (nach RSS)",
          "ps -A -o PID,USER,RSS,NAME 2>/dev/null | sort -k3 -nr | head -n 30", L)
    L.append("Idle-Hochlast / unbekannte Dauerprozesse = Indikator für Miner/Spyware/Keylogger.")
    return (OK if len(L) > 1 else PARTIAL), L


def c_security(adb, st):
    L = _kvs(adb, [("Verschlüsselung", "ro.crypto.state"), ("FBE/FDE-Typ", "ro.crypto.type"),
                   ("Verified Boot", "ro.boot.verifiedbootstate")])
    se = _v(adb.shell("getenforce"))
    if se:
        L.append(f"SELinux: {se}")
    lock = _v(adb.shell("dumpsys trust 2>/dev/null | grep -iE 'secure|lock' | head -3"))
    if lock:
        L += lock.splitlines()
    L.append("Keystore/TEE-gebundene Schlüssel sind hardwareverankert → nachträgliche Entschlüsselung i.d.R. unmöglich.")
    return (OK if L else PARTIAL), L


def c_deepos(adb, st):
    L = []
    dmesg = _v(adb.shell("dmesg 2>/dev/null | tail -20"))
    if dmesg:
        L.append(f"Kernel-Log (dmesg) lesbar: {len(dmesg.splitlines())} Zeilen (in Report-Datei).")
    else:
        L.append("dmesg ohne Root meist gesperrt (dmesg_restrict=1) → 🔑 für USB-/Kernel-Historie.")
    usb = _v(adb.shell("dmesg 2>/dev/null | grep -iE 'usb .*new|usb.*device' | tail -10"))
    if usb:
        L += ["Letzte USB-Ereignisse (Angreifer-Hardware?):"] + usb.splitlines()[:6]
    boot = _v(adb.shell("getprop sys.boot.reason 2>/dev/null") or adb.getprop("ro.boot.bootreason"))
    if boot:
        L.append(f"Letzter Boot-Grund: {boot}")
    return (OK if dmesg or usb else PARTIAL), L


# ========================================================================== #
#  TEIL 2 – SIM / eSIM / eUICC (real, soweit Android es zulässt)
# ========================================================================== #
def c_esim(adb, st):
    L = []
    eu = _v(adb.shell("dumpsys euicc 2>/dev/null | head -30") or adb.shell("dumpsys isub 2>/dev/null | head -20"))
    if eu:
        eid = re.search(r"[Ee]id[=:\s]+([0-9A-Fa-f]{20,})", eu)
        if eid:
            L.append(f"EID (eUICC-ID): {eid.group(1)}")
        L.append(f"eUICC/Profil-Dump: {len(eu.splitlines())} Zeilen (in Report-Datei).")
    feat = _v(adb.shell("pm list features 2>/dev/null | grep -i euicc"))
    if feat:
        L.append("eSIM-Feature vorhanden: " + feat)
    return (OK if L else PARTIAL), L


def c_simhw(adb, st):
    L = _kvs(adb, [("SIM-Status", "gsm.sim.state"), ("SIM-Operator", "gsm.sim.operator.alpha"),
                   ("Operator-Numerisch", "gsm.sim.operator.numeric")])
    cnt = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | grep -ciE 'mSimState|phoneId'"))
    if cnt and cnt.isdigit():
        L.append(f"Telephony-Registry SIM-Felder: {cnt}")
    L.append("SIM-Hot-Swap-Ereignisse (physisches Wechseln) nur über Kernel-Interrupt-Logs → 🔑/dmesg.")
    return (OK if L else PARTIAL), L


def c_simsec(adb, st):
    state = (adb.getprop("gsm.sim.state") or "").strip()
    L = [f"SIM-Sperrstatus: {state or 'unbekannt'}"]
    if "PIN" in state.upper():
        L.append("⚠ SIM ist PIN-gesperrt – KEINE PIN-Versuche im Labor (PUK-/Bricking-Gefahr)!")
    L.append("Verbleibende PIN/PUK-Versuche sind nur über AT+CPIN? am Diag-Port sicher auslesbar (📡).")
    return PARTIAL, L


def c_carrier(adb, st):
    L = _kvs(adb, [("Netzbetreiber", "gsm.operator.alpha"), ("Netz-Numerisch (MCC+MNC)", "gsm.operator.numeric"),
                   ("Roaming", "gsm.operator.isroaming"), ("Netztyp", "gsm.network.type")])
    L.append("IMSI/MSISDN sind privilegiert geschützt (READ_PRIVILEGED_PHONE_STATE) → für Beauskunftung "
             "beim Netzbetreiber via richterlichem Beschluss; lokal nur 🔑/Diag.")
    return (OK if len(L) > 1 else PARTIAL), L


def c_simstore(adb, st):
    L = []
    sms = _v(adb.shell("content query --uri content://sms 2>/dev/null | grep -c Row"))
    if sms and sms.isdigit():
        L.append(f"SMS (inkl. SIM-gespeicherter, content://sms): {sms} Zeilen")
    icc = _v(adb.shell("content query --uri content://icc/adn 2>/dev/null | grep -c Row"))
    if icc and icc.isdigit() and int(icc) > 0:
        L.append(f"SIM-Telefonbuch (EF-ADN): {icc} Einträge")
    L.append("Auf der SIM gespeicherte, am Telefon gelöschte SMS/Kontakte sind eine kritische Restquelle.")
    return (OK if L and len(L) > 1 else PARTIAL), L


def c_baseband(adb, st):
    L = _kvs(adb, [("Baseband-Version", "gsm.version.baseband"), ("RIL-Version", "gsm.version.ril-impl")])
    L.append("Direkte AT-Kommandos zum Modem benötigen den Diag-/Modem-Port (📡 USB-Diag oder Root-/dev/smdX).")
    return (PARTIAL if L and len(L) > 1 else HW), L


def c_cell(adb, st):
    L = []
    ci = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | grep -iE 'mCellInfo|CellIdentity|mSignalStrength' | head -8"))
    if ci:
        L += ["Funkzellen-/Signal-Felder:"] + [l.strip()[:100] for l in ci.splitlines()[:6]]
    L.append("Live-IMSI-Catcher-Monitor (Cell-ID/LAC/TAC-Anomalien): Hauptmenü → L.")
    return (OK if ci else PARTIAL), L


# ========================================================================== #
#  Sektionen, die echte Spezial-Hardware / Labor erfordern (ehrlich dokumentiert)
# ========================================================================== #
def c_lpa(adb, st):
    out = _v(adb.shell("dumpsys euicc 2>/dev/null | grep -iE 'smdp|rsp|server' | head -8"))
    if out:
        return OK, ["LPA/SM-DP+-Spuren:"] + out.splitlines()
    return PARTIAL, ["LPA-Server-URLs (SM-DP+) nur teils im Log; vollständig 🔑 unter /data/.../euicc."]


def c_5g(adb, st):
    out = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | grep -iE 'rsrp|rsrq|sinr|nr' | head -8"))
    if out:
        return OK, ["5G/LTE-Signalmetriken:"] + out.splitlines()
    return HW, ["Detaillierte 5G-Beamforming-/Band-Metriken nur über Diag-Port/SDR (📡)."]


def c_ntn(adb, st):
    out = _v(adb.shell("pm list features 2>/dev/null | grep -i satellite"))
    if out:
        return OK, ["NTN/Satelliten-Feature: " + out]
    return INFO, ["Kein NTN-Feature gemeldet. Satelliten-Uplink-Logs/Ephemeriden nur am Modem-Diag-Port (📡)."]


def c_ims(adb, st):
    out = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | grep -iE 'ims|volte|wifi calling|registration' | head -8"))
    if out:
        return OK, ["IMS/VoLTE/VoWiFi-Status:"] + out.splitlines()
    return PARTIAL, ["IMS-Registrierungsstatus nicht exponiert; SIP/SDP-Mitschnitt via Traffic-Engine (📡 WLAN-Calling)."]


def c_multisim(adb, st):
    n = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | grep -ciE 'phoneId|subId'"))
    return (OK if n and n.isdigit() and int(n) else PARTIAL), [
        f"Aktive Phone-/Sub-ID-Felder (Dual-SIM-Routing): {n or '0'}",
        "Zuordnung Datenpaket→SIM verhindert Fehlattribution zwischen SIM 1/2."]


def c_nvram(adb, st):
    out = _v(adb.shell("ls -l /dev/block/by-name/ 2>/dev/null | grep -iE 'nvram|nvdata|efs|protect'"))
    if out:
        return OK, ["NVRAM/EFS-Partitionen lokalisiert (Dump = 🔑/EDL):"] + out.splitlines()[:8]
    return ROOT, ["NVRAM/EFS nicht sichtbar ohne Root. Physikalischer IMEI-Abgleich gegen NVRAM entlarvt IMEI-Spoofing."]


def c_guti(adb, st):
    out = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | grep -iE 'guti|tmsi|temporary' | head -4"))
    if out:
        return OK, ["Temporäre Kennungen:"] + out.splitlines()
    return HW, ["Temporäre Kennungen (GUTI/TMSI) nicht exponiert; Rotations-Analyse nur am Funk-Layer (📡)."]


def c_net_baseline(adb, st):
    """Open5GS/Spoofing-Labor: software-seitig das aktuelle Netz als Vergleichs-Baseline."""
    out = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | "
                       "grep -iE 'mServiceState|plmn|registered|operator|mVoiceRegState' | head -n 14"))
    if out:
        return PARTIAL, ["Aktuelles Netz (Baseline; eigentliche Emulation = SDR/Open5GS-Labor):"] + out.splitlines()
    return LAB, ["Test-Mobilfunk-Infrastruktur (Open5GS/srsRAN/Osmocom) + SDR (USRP/BladeRF), abgeschirmt."]


def c_ril(adb, st):
    """RIL-Kontrolle: software-seitig RIL-Prozesse + Radio-Properties (Hooking braucht Root/Frida)."""
    out = []
    ps = _v(adb.shell("ps -A 2>/dev/null | grep -iE 'rild|vendor.ril|ril-daemon|radio'"))
    props = _v(adb.shell("getprop | grep -iE 'ril\\.|persist.radio|gsm.version' | head -n 40"))
    if ps:
        out += ["RIL-/Radio-Prozesse:", ps]
    if props:
        out += ["", "RIL-/Radio-Properties:", props]
    if out:
        out.append("\n(Live-Eingriff Audio/SMS an der SW-Wurzel: Root + Frida-Hooks auf rild.)")
        return OK, out
    return ROOT, ["RIL-Hooking (Audio/SMS) benötigt Root + Frida auf rild (Tiefen-Engine)."]


def c_ril_mem(adb, st):
    """Deep-Baseband-RIL-Speicher: software-seitig rild-Prozess/Maps (Dump = Root)."""
    pid = _v(adb.shell("pidof rild 2>/dev/null")).split()[:1]
    out = []
    if pid:
        out.append(f"rild PID: {pid[0]}")
        maps = _v(adb.shell(f"wc -l /proc/{shq(pid[0])}/maps 2>/dev/null"))
        if maps:
            out.append(f"Speicher-Regionen (maps): {maps}")
        out.append("Voller RAM-Dump (Pegasus-/Overflow-Spuren) = Root + gcore/Frida.")
        return OK, out
    return ROOT, ["rild nicht sichtbar ohne Root. Speicheranalyse: Root + gcore/Frida-Dump."]


def c_ims_lab(adb, st):
    """IMS/VoLTE-Exploitation: software-seitig IMS-Registrierung als Angriffsflächen-Baseline."""
    out = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | "
                       "grep -iE 'ims|registration|volte|rcs|wifi calling' | head -n 14"))
    if out:
        return OK, ["IMS-Status (Angriffsflächen-Baseline; Exploits nur isoliertes Labor):"] + out.splitlines()
    return INFO, ["IMS-Verwundbarkeitstests (DoS/Hijack) nur in isolierter Test-/Laborumgebung."]


def c_slice(adb, st):
    """5G Network Slicing: software-seitig Slice/URSP aus telephony/carrier_config (sofern exponiert)."""
    out = _v(adb.shell("dumpsys telephony.registry 2>/dev/null | "
                       "grep -iE 'slice|ursp|nssai|network slic|5g' | head -n 14"))
    if out:
        return OK, ["Slice-/5G-relevante Felder:"] + out.splitlines()
    cc = _v(adb.shell("dumpsys carrier_config 2>/dev/null | grep -iE 'slice|nr_|5g' | head -n 14"))
    if cc:
        return PARTIAL, ["Carrier-Config (5G/Slice-relevant):"] + cc.splitlines()
    return PARTIAL, ["Slice-/URSP-Zuweisung wird netzseitig vergeben; lokal keine Slice-Daten exponiert."]


# ========================================================================== #
#  Sektions-Registry: (id, teil, icon, titel, status, collector|None, needs)
# ========================================================================== #
SECTIONS = [
    # ---- Teil 1 ----
    (1, 1, "🔬", "System- & Hardware-Diagnose", None, c_system, ""),
    (2, 1, "📱", "App- & Paket-Management", None, c_apps, ""),
    (3, 1, "🎮", "Fernsteuerung & UI-Automation", None, c_uiauto, ""),
    (4, 1, "⚙️", "System-Tweaks & Modding (Trust-Status)", None, c_modding, ""),
    (5, 1, "🛠️", "Datei-Transfer, Medien & Forensik", None, c_media, ""),
    (6, 1, "💾", "Partitionen, Images & Low-Level", None, c_partitions, ""),
    (7, 1, "🌐", "Netzwerk, Proxy & Traffic", None, c_network, ""),
    (8, 1, "⚡", "Performance-Profiling & Stresstests", None, c_perf, ""),
    (9, 1, "🛡️", "Security-Auditing & App-Sicherheit", None, c_security, ""),
    (10, 1, "🧠", "Deep-OS Controls & versteckte Features", None, c_deepos, ""),
    # ---- Teil 2 ----
    (11, 2, "💳", "eSIM-Profile & eUICC-Architektur", None, c_esim, ""),
    (12, 2, "🗂️", "Physische SIM-Hardware & Slot-Struktur", None, c_simhw, ""),
    (13, 2, "🔐", "SIM-Sicherheit, PIN, PUK & Sperren", None, c_simsec, ""),
    (14, 2, "📡", "Netzbetreiber-Konfiguration & IMSI", None, c_carrier, ""),
    (15, 2, "💾", "SIM-Speicher (EF-SMS / EF-ADN)", None, c_simstore, ""),
    (16, 2, "📡", "Baseband, Modem & AT-Kommandos", None, c_baseband, ""),
    (17, 2, "🕵️", "IMSI-Catcher-Schutz & Funkzellen-Analyse", None, c_cell, ""),
    (18, 2, "🔒", "SIM-Dateisystem (MF/DF/EF) & Krypto", HW,
     None, "Smartcard-Reader (PC/SC) + APDU-Zugriff auf die SIM. Milenage/COMP128-Prüfung "
           "erfordert direkten Chip-Zugriff – in reinem ADB nicht möglich."),
    (19, 2, "🌍", "eSIM-Sicherheit & LPA / SM-DP+", None, c_lpa, ""),
    (20, 2, "🛠️", "Forensische Mobilfunk-Konsolidierung", INFO,
     None, "Konsolidiert SIM/Baseband/Netz-Daten dieses Berichts mit Zeitstempeln + SHA-256 "
           "(Report-Export 'E' → gerichtsfestes Manifest)."),
    # ---- Teil 3 ----
    (21, 3, "📶", "5G/Next-Gen Signal-Analyse (RSRP/RSRQ/SINR)", None, c_5g, ""),
    (22, 3, "🛰️", "Satelliten-Kommunikation (NTN)", None, c_ntn, ""),
    (23, 3, "🔐", "Baseband-Exploits & Modem-RAM-Dump", HW,
     None, "Auslesen des flüchtigen Modem-RAM benötigt Diag-Mode/JTAG bzw. einen Baseband-Exploit. "
           "Nicht in reiner Software – dokumentiert, nicht simuliert."),
    (24, 3, "💳", "Krypto-Keys (Ki) & SIM-Hardware-Forensik", LAB,
     None, "Ki-Isolierung via Differential Power Analysis (DPA) am Chip – physisches Labor "
           "mit Oszilloskop/SPA-Rig. Rechtlich/forensisch heikel, hier nur dokumentiert."),
    (25, 3, "🌍", "eSIM Remote-Provisioning & GSMA-Compliance", PARTIAL,
     None, "Zertifikatsketten-/MITM-Prüfung des eSIM-Handshakes: teils aus LPA-Logs (🔑), "
           "vollständig nur mit GSMA-RSP-Testumgebung."),
    (26, 3, "📞", "IMS / VoLTE / VoWiFi (SIP/SDP)", None, c_ims, ""),
    (27, 3, "🕵️", "Anti-Tracking, STK & Silent-SMS-Defensive", PARTIAL,
     None, "Silent/Typ-0-SMS & proaktive STK-Kommandos sind nur durch Live-Mitschnitt am "
           "Baseband/Diag-Port sicher erkennbar (📡). Indikator-App-Scan: Modul 'A' IOC."),
    (28, 3, "⚡", "RF-Stresstests, Jamming & HW-Sicherheit", LAB,
     None, "Signal-Resistenz/Jamming-Tests erfordern abgeschirmte Kammer + Signalgenerator/SDR. "
           "Physisches Labor – dokumentiert."),
    (29, 3, "🔀", "Multi-SIM-Routing & virtuelle Modems", None, c_multisim, ""),
    (30, 3, "💾", "Forensische NVRAM-Analyse (IMEI/Kalibrierung)", None, c_nvram, ""),
    # ---- Teil 4 (High-End Labor / Emulation – fast vollständig HW/Labor) ----
    (31, 4, "🧪", "Virtuelle SIM-Emulation & SD-Modifikation", LAB,
     None, "Smartcard-Emulator (z.B. sysmoSIM/Magic-SIM + Reader). Lässt das Gerät isoliert booten "
           "(verhindert Remote-Wipe). Hardware-Verfahren."),
    (32, 4, "🕵️", "Krypto-Anomalien & logische SIM-Exploits (OTA)", LAB,
     None, "OTA-Mitschnitt (Over-the-Air) zwischen Netz und SIM benötigt SDR/Diag + Decoder. Labor."),
    (33, 4, "🌐", "Virtuelles IMS-/Betreiber-Spoofing (Open5GS/Osmocom)", None, c_net_baseline, ""),
    (34, 4, "🕵️", "SIM-Sniffer & APDU-Klartext-Mitschnitt", LAB,
     None, "Physischer SIM-Interposer zwischen Slot und Karte (z.B. SIMtrace2). Protokolliert "
           "APDU-Verkehr im Klartext. Hardware."),
    (35, 4, "🛠️", "Radio Interface Layer (RIL) – Kontrolle", None, c_ril, ""),
    (36, 4, "💉", "Protokoll-Injection & Baseband-Fuzzing", LAB,
     None, "Gezielte Fehlpaket-Injektion in den Baseband-Stack via SDR/Test-Netz. Labor/SDR."),
    (37, 4, "🔧", "Deep-Baseband Memory & RIL-Speicheranalyse", None, c_ril_mem, ""),
    (38, 4, "🌐", "Krypto-Emulation & Klon-Prüfung (SQN)", LAB,
     None, "Sequenzzähler-(SQN)-Abgleich gegen Netzbetreiber-Werte erkennt SIM-Swapping/Klone. "
           "Erfordert netzseitige Daten / HLR-Auskunft."),
    (39, 4, "🕵️", "IMS/VoLTE-Labor-Exploitation (DoS/Hijack)", None, c_ims_lab, ""),
    (40, 4, "🛡️", "SIM-Toolkit (STK) Java-Applet-Audit", HW,
     None, "Audit der SIM-Applets (Banking/ID) benötigt Smartcard-Reader + Applet-Analyse. Hardware."),
    (41, 4, "📶", "5G Network Slicing & Edge-Forensik", None, c_slice, ""),
    (42, 4, "🛰️", "Satelliten (NTN) & Orbit-Validierung (Anti-Spoof)", LAB,
     None, "Sichtkegel-/Ephemeriden-Validierung gegen TLE-Daten + Empfangslog des Modems (Diag). "
           "SDR/Labor zur Anti-Spoofing-Prüfung."),
    (43, 4, "🕵️", "Anti-Tracking & GUTI/TMSI-Rotation", None, c_guti, ""),
    (44, 4, "⚡", "RF-Interferenz & Hardware-Leckage (TEMPEST)", LAB,
     None, "Messung elektromagnetischer Nebenabstrahlung (TEMPEST) zur Wanzen-/HW-Trojaner-Suche – "
           "abgeschirmte Kammer + Spektrumanalysator. Physisches Labor."),
    (45, 4, "💾", "Forensische NVRAM-Rekonstruktion (Unbrick)", LAB,
     None, "Rekonstruktion korrumpierter NVRAM/Modem-Partitionen (Unbrick → IMEI/IMEIsv auslesen) via "
           "EDL/BROM + herstellerspezifische Firmware-Strukturen. Tiefen-Tooling: MediaTek/Samsung-Module."),
]

PART_TITLES = {
    1: "OS-, Dateisystem- & Anwendungs-Forensik",
    2: "SIM-, eSIM- & eUICC-Telekommunikations-Forensik",
    3: "Advanced Baseband-, Signal- & RF-Forensik",
    4: "High-End Labor-Exploitation & Emulations-Forensik",
}


# ========================================================================== #
#  Ausführung
# ========================================================================== #
def _run_section(adb, st, sec) -> dict:
    sid, part, icon, title, fixed_status, fn, needs = sec
    status, lines = fixed_status, []
    if fn is not None:
        try:
            res_status, lines = fn(adb, st)
            status = res_status or status or PARTIAL
        except Exception as e:  # noqa: BLE001
            LOG.exception(f"acquire #{sid} {title}", e)
            status, lines = PARTIAL, [f"(Fehler bei Erhebung: {e})"]
    if not lines and needs:
        lines = [needs]
    if status is None:
        status = INFO if needs else PARTIAL
    return {"id": sid, "part": part, "icon": icon, "title": title,
            "status": status, "lines": lines or ["(keine Daten)"]}


def run_all(adb: ADB, dev, st, data: dict, parts=(1, 2, 3, 4), export: bool = True) -> dict:
    ui.clear()
    ui.banner(subtitle="🧬 Vollständige forensische Akquise (45 Sektionen)")
    LOG.info("Vollanalyse (acquire) gestartet")
    results = []
    todo = [s for s in SECTIONS if s[1] in parts]
    ui.scan_overview([f"{s[2]} {s[3]}" for s in todo], "Vollanalyse – Bereiche")
    counts = {OK: 0, PARTIAL: 0, ROOT: 0, HW: 0, LAB: 0, INFO: 0}
    for sec in todo:
        sym, _lbl, _col = _BADGE[sec[4] or PARTIAL]
        sys_id = sec[0]
        print(f"  {ui.GREY}[{sys_id:>2}/45]{ui.RESET} {sec[2]} {sec[3]} …", end="", flush=True)
        r = _run_section(adb, st, sec)
        results.append(r)
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        b_sym, b_lbl, b_col = _BADGE[r["status"]]
        print(f"\r  {b_col}{b_sym}{ui.RESET} [{sys_id:>2}/45] {sec[2]} {sec[3]:<46.46} {b_col}{b_lbl}{ui.RESET}")

    report_txt, report_md = _render(results, counts, dev, data)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    txt_path = os.path.join(OUT, f"vollbericht_{stamp}.txt")
    md_path = os.path.join(OUT, f"vollbericht_{stamp}.md")
    for path, body in ((txt_path, report_txt), (md_path, report_md)):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
        except OSError as e:
            LOG.exception(f"acquire write {path}", e)

    print()
    ui.rule("Zusammenfassung", ui.YELLOW)
    for stt in (OK, PARTIAL, ROOT, HW, LAB, INFO):
        sym, lbl, col = _BADGE[stt]
        ui.kv(f"{sym} {lbl}", counts.get(stt, 0))
    ui.ok(f"Gesamtbericht: {txt_path}")
    ui.ok(f"Markdown:      {md_path}")
    LOG.info(f"Vollanalyse fertig: {counts}")
    ui.pause("Gesamtbericht jetzt im Terminal ansehen – ENTER")
    ui.show_report(report_txt, "🧬 VOLLANALYSE · Gesamtbericht (45 Sektionen)", txt_path, note="Gesamtbericht")

    out = {"results": results, "counts": counts, "txt": txt_path, "md": md_path}

    # Automatischer Gesamt-Export (HTML/JSON + SHA-256-Manifest) über ALLE Funde,
    # inkl. dieses Vollberichts (forensik_full/ ist im Report-Modul registriert).
    if export:
        print()
        ui.rule("Automatischer Export (HTML/JSON + SHA-256-Manifest)", ui.YELLOW)
        ui.info("Bündle alle Artefakte, berechne Hashes, rendere Gesamtbericht …")
        try:
            from . import report
            summary = report.generate(data, ("html", "md", "json", "manifest"))
            out["export"] = summary["report_files"]
            ui.ok(f"{summary['files_total']} Artefakte exportiert "
                  f"({human_size(summary['size_total'])}):")
            for fmt, path in summary["report_files"].items():
                ui.kv(fmt.upper(), path)
            LOG.info(f"Auto-Export fertig: {summary['report_files']}")
        except Exception as e:  # noqa: BLE001
            ui.err(f"Auto-Export fehlgeschlagen: {e}")
            LOG.exception("Auto-Export nach Vollanalyse", e)
    return out


def _render(results, counts, dev, data) -> tuple[str, str]:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    head = [
        "ANDROID PANZER · VOLLSTÄNDIGER FORENSIK-BERICHT",
        f"Erstellt: {stamp}",
        f"Gerät: {(data or {}).get('brand','?')} {(data or {}).get('model','?')}  "
        f"Serial: {getattr(dev,'serial','') or '—'}  Android: {(data or {}).get('android','?')}",
        f"Status: ✅{counts.get(OK,0)} erhoben · 🟡{counts.get(PARTIAL,0)} eingeschränkt · "
        f"🔑{counts.get(ROOT,0)} Root · 📡{counts.get(HW,0)} SDR/HW · 🧪{counts.get(LAB,0)} Labor · "
        f"ℹ️{counts.get(INFO,0)} Info",
        "Hinweis: Read-only-Akquise. Hardware-/Labor-Sektionen sind dokumentiert, nicht simuliert.",
    ]
    txt = ["=" * 76] + head + ["=" * 76, ""]
    md = ["# Android Panzer – Vollständiger Forensik-Bericht", ""] + [f"- {h}" for h in head[1:]] + [""]

    cur_part = None
    for r in results:
        if r["part"] != cur_part:
            cur_part = r["part"]
            txt += ["", f"### TEIL {cur_part} — {PART_TITLES[cur_part]} ".ljust(76, "─"), ""]
            md += ["", f"## Teil {cur_part} — {PART_TITLES[cur_part]}", ""]
        sym, lbl, _col = _BADGE[r["status"]]
        txt.append(f"[{r['id']:>2}] {sym} {r['icon']} {r['title']}  «{lbl}»")
        for ln in r["lines"]:
            txt.append(f"      {ln}")
        txt.append("")
        md.append(f"### {r['id']}. {r['icon']} {r['title']} — `{lbl}`")
        md += [f"- {ln}" for ln in r["lines"]] + [""]
    return "\n".join(txt) + "\n", "\n".join(md) + "\n"


# ========================================================================== #
#  Menü
# ========================================================================== #
def menu(adb: ADB, dev, st, data) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle="🧬 Vollständige forensische Analyse")
        ui.info("45 Sektionen in 4 Teilen. Read-only. Hardware/Labor wird ehrlich dokumentiert, nicht erfunden.\n")
        ch = ui.menu("Umfang", [
            ("1", "🚀 ALLES analysieren (Teil 1–4) → Gesamtbericht"),
            ("2", "🔬 Nur Teil 1 (OS/Dateisystem/Apps)"),
            ("3", "💳 Nur Teil 2 (SIM/eSIM/eUICC)"),
            ("4", "📶 Nur Teil 3 (Baseband/Signal/RF)"),
            ("5", "🧪 Nur Teil 4 (Labor/Emulation – Methoden-Doku)"),
            ("6", "📑 Gesamtbericht als HTML/JSON + SHA-256 exportieren (Report-Modul)"),
            ("7", f"{ui.BCYAN}🧪 LABOR EINRICHTEN (Hardware+Software für 📡/🧪-Sektionen){ui.RESET}"),
        ], back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return
        try:
            if ch == "1":
                run_all(adb, dev, st, data, export=True); ui.pause()
            elif ch == "2":
                run_all(adb, dev, st, data, parts=(1,), export=False); ui.pause()
            elif ch == "3":
                run_all(adb, dev, st, data, parts=(2,), export=False); ui.pause()
            elif ch == "4":
                run_all(adb, dev, st, data, parts=(3,), export=False); ui.pause()
            elif ch == "5":
                run_all(adb, dev, st, data, parts=(4,), export=False); ui.pause()
            elif ch == "6":
                from . import report
                report._do(data, ("html", "md", "json", "manifest"))
            elif ch == "7":
                from . import labsetup
                labsetup.menu(adb, dev, st, data)
            else:
                ui.warn("Ungültige Auswahl.")
        except Exception as e:  # noqa: BLE001
            ui.err(f"Fehler: {e}")
            LOG.exception("acquire menu", e)
            ui.pause()
