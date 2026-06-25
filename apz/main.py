"""Hauptprogramm: Geräteerkennung → Auto-Analyse → Menüführung → Dispatch."""
from __future__ import annotations

import sys
import time

from . import (acquire, aishell, apkscan, appscan, bootloop, brands, casedb, customfw,
               dashboard, dataforensics, dashboard_runner, deepforensics, filetree, forensics, frida_engine,
               handlers, labsetup, lang, mediatek, messenger, modeswitch, osint, phoneosint,
               registry, report, rescue,
               rooting, rootkit, rootprep, samsung, timeline, traffic, ui, usb,
               ai_core, ai_integration, ai_automation, deep_analysis_scan,
               microphone_tap, camera_tap, network_analyzer, adult_content_scanner,
               virtual_filesystem, vfs_templates, modern_startup, anomaly_detector, ai_doctor,
               app_decryption, brute_force, wifi_handshake, dns_guardian, tracker_system,
               intelligent_engine, database_scanner, lab_manager, keyword_recorder, adult_activity_detector, wifi_room_scanner_3d,
               forensic_audio_analyzer, security_framework, password_manager, audio_playback, adb_shell, auto_root_engine,
               numeric_menu, settings_manager, google_account_scanner,
               account_scanner, frp_scanner, progress, sim_toolkit,
               app_traffic_monitor, device_snapshot, ai_root_deployer)
from .adb import ADB, AdbError, Device
from .util import LOG

# Sitzungs-Flag: True wenn User der KI TWRP-Steuerrechte erteilt hat
_ki_twrp_granted: bool = False


def _connect() -> Device | None:
    """Erkennt jedes Android-Gerät in JEDEM Modus (adb/fastboot/edl/mtk/odin/nodebug)."""
    ADB.start_server()
    ui.clear()
    ui.banner(subtitle=lang.t("connect_title"))

    devs = usb.detect_all()
    if not devs:
        ui.info(lang.t("connect_no_device"))
        ui.info(lang.t("connect_detects"))
        # Snapshots-Hinweis wenn gespeicherte vorhanden
        snap_list = device_snapshot.SnapshotManager.list_all()
        if snap_list:
            print(f"  {ui.BYELLOW}💾 {len(snap_list)} Snapshot(s) verfügbar – "
                  f"[s] zum Laden{ui.RESET}")
        if _ki_twrp_granted:
            print(f"  {ui.BGREEN}🤖 KI-TWRP-Erlaubnis aktiv – Claude Code darf TWRP steuern{ui.RESET}")
        print()
        ui.info(lang.t("connect_prompt_line"))
        c = ui.ask(lang.t("ui_select"), "").lower()
        if c == "q":
            return None
        if c == "m":
            bootloop.monitor()
            return _connect()
        if c == "k":
            _ki_twrp_session()
            return _connect()
        if c == "s":
            vadb = device_snapshot.offer_load_snapshot()
            if vadb is not None:
                # Virtuelles Device zurückgeben (Snapshot-Modus)
                return vadb.device
            return _connect()
        ui.info(lang.t("connect_scanning"))
        spin = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        try:
            def tick(i):
                sys.stdout.write(f"\r  {ui.NEON}{spin[i % len(spin)]}{ui.RESET} "
                                 f"{lang.t('connect_scanning_spin')}   ")
                sys.stdout.flush()
            dev = usb.wait_for_any(on_tick=tick)
            print()
            return dev
        except KeyboardInterrupt:
            print()
            return None

    ui.rule(lang.t("connect_found", n=len(devs)), ui.YELLOW)
    for i, d in enumerate(devs, 1):
        print(f"  {ui.CYAN}{i:>2}{ui.RESET}  {usb.mode_badge(d.mode):<34} {d.label}")
    print()
    if len(devs) == 1:
        d = devs[0]
        ui.ok(f"{lang.t('connect_chosen')} {usb.mode_badge(d.mode)} {d.label}")
        return d

    # Bei mehreren Geräten: wenn genau ein ADB-fähiges vorhanden → automatisch wählen.
    # Verhindert Verwirrung durch Samsung-Zusatz-Interfaces (04e8:685d u.ä.)
    adb_ready = [d for d in devs if d.mode == "adb"]
    if len(adb_ready) == 1:
        d = adb_ready[0]
        ui.ok(f"Auto-Auswahl ADB-Gerät: {usb.mode_badge(d.mode)} {d.label}")
        return d

    sel = ui.ask(lang.t("connect_choose_device"), "1")
    try:
        return devs[int(sel) - 1]
    except (ValueError, IndexError):
        return devs[0]


# ── KI-TWRP-Modus: Consent + interaktive TWRP-Steuerkonsole für Claude Code ──

def _twrp_status(sp) -> None:
    """TWRP-Zustand via ADB lesen und ausgeben."""
    ui.clear()
    ui.rule("🔍 TWRP-STATUS", ui.CYAN)
    checks = [
        ("TWRP Version",     ["adb", "shell", "twrp", "version"]),
        ("ro.twrp.version",  ["adb", "shell", "getprop", "ro.twrp.version"]),
        ("ro.twrp.boot",     ["adb", "shell", "getprop", "ro.twrp.boot"]),
        ("Mount-Status",     ["adb", "shell", "mount"]),
        ("/sdcard Speicher", ["adb", "shell", "df", "-h", "/sdcard"]),
        ("Recovery-Log",     ["adb", "shell", "tail", "-20", "/tmp/recovery.log"]),
    ]
    for label, cmd in checks:
        try:
            r = sp.run(cmd, capture_output=True, text=True, timeout=8)
            out = (r.stdout or r.stderr).strip()
            if out:
                first = out.splitlines()[0][:120]
                ui.ok(f"{label}: {first}")
                if label == "Recovery-Log" and len(out.splitlines()) > 1:
                    for line in out.splitlines()[1:]:
                        print(f"    {ui.GREY}{line}{ui.RESET}")
            else:
                ui.warn(f"{label}: keine Ausgabe")
        except sp.TimeoutExpired:
            ui.warn(f"{label}: Timeout (8 s)")
        except Exception as e:
            ui.warn(f"{label}: {e}")
    ui.pause()


def _twrp_install_zip(sp) -> None:
    """ZIP auf /sdcard pushen und via twrp install installieren."""
    import os
    ui.clear()
    ui.rule("📦 ZIP INSTALLIEREN", ui.CYAN)
    print(f"  {ui.GREY}Gerät muss in TWRP-Recovery sein.{ui.RESET}")
    print(f"  {ui.GREY}Beispiel: /home/user/Downloads/Magisk-v27.0.zip{ui.RESET}")
    print()
    path = ui.ask("Lokaler Pfad zur ZIP-Datei", "").strip()
    if not path:
        return
    if not os.path.isfile(path):
        ui.err(f"Datei nicht gefunden: {path}")
        ui.pause()
        return
    dest = "/sdcard/ki_twrp_install.zip"
    ui.info(f"Pushe → {dest} …")
    try:
        r = sp.run(["adb", "push", path, dest], capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            ui.err(f"Push fehlgeschlagen: {r.stderr.strip()[:200]}")
            ui.pause()
            return
        ui.ok("Push erfolgreich")
    except sp.TimeoutExpired:
        ui.err("Push-Timeout (>3 min)")
        ui.pause()
        return
    except Exception as e:
        ui.err(f"Push-Fehler: {e}")
        ui.pause()
        return
    ui.info(f"twrp install {dest} …")
    try:
        r = sp.run(["adb", "shell", "twrp", "install", dest],
                   capture_output=True, text=True, timeout=300)
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0 or "Install Complete" in out or "Success" in out:
            ui.ok(f"Installation abgeschlossen: {out.splitlines()[-1][:120] if out else 'OK'}")
        else:
            ui.warn(f"TWRP-Ausgabe:\n  {out[:400]}")
    except sp.TimeoutExpired:
        ui.err("Installations-Timeout (>5 min)")
    except Exception as e:
        ui.err(f"Installationsfehler: {e}")
    ui.pause()


def _twrp_sideload(sp) -> None:
    """ZIP via adb sideload übertragen (Gerät muss in Sideload-Modus sein)."""
    import os
    ui.clear()
    ui.rule("📡 SIDELOAD-MODUS", ui.CYAN)
    print(f"  {ui.GREY}Gerät in TWRP → Advanced → ADB Sideload aktivieren.{ui.RESET}")
    print()
    path = ui.ask("Lokaler Pfad zur ZIP-Datei", "").strip()
    if not path:
        return
    if not os.path.isfile(path):
        ui.err(f"Datei nicht gefunden: {path}")
        ui.pause()
        return
    ui.info(f"adb sideload {path} …")
    try:
        r = sp.run(["adb", "sideload", path], capture_output=True, text=True, timeout=300)
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0:
            ui.ok(f"Sideload abgeschlossen: {out[:200] or 'OK'}")
        else:
            ui.warn(f"Sideload: {out[:200]}")
    except sp.TimeoutExpired:
        ui.err("Sideload-Timeout (>5 min)")
    except Exception as e:
        ui.err(str(e))
    ui.pause()


def _twrp_wipe_cache(sp) -> None:
    """Cache und Dalvik-Cache via TWRP leeren (kein Datenverlust)."""
    ui.clear()
    ui.rule("🗑  CACHE LEEREN", ui.CYAN)
    if not ui.confirm("Cache + Dalvik-Cache leeren?  (keine Datenverlust-Operation)", True):
        return
    for label, wipe_target in [("Cache", "cache"), ("Dalvik-Cache", "dalvik")]:
        try:
            r = sp.run(["adb", "shell", "twrp", "wipe", wipe_target],
                       capture_output=True, text=True, timeout=60)
            out = (r.stdout + r.stderr).strip()
            ui.ok(f"{label} geleert: {out[:80] or 'OK'}") if r.returncode == 0 else ui.warn(f"{label}: {out[:80]}")
        except sp.TimeoutExpired:
            ui.err(f"{label}: Timeout")
        except Exception as e:
            ui.err(f"{label}: {e}")
    ui.pause()


def _twrp_reboot_menu(sp) -> None:
    """Gerät via ADB neu starten."""
    ui.clear()
    ui.rule("🔄 NEUSTART", ui.CYAN)
    print(f"  {ui.BOLD}1{ui.RESET}  System  (normal booten)")
    print(f"  {ui.BOLD}2{ui.RESET}  Recovery  (zurück in TWRP)")
    print(f"  {ui.BOLD}3{ui.RESET}  Bootloader  (Fastboot-Modus)")
    print(f"  {ui.BOLD}0{ui.RESET}  Abbrechen")
    print()
    ch = ui.ask("Auswahl", "0")
    targets = {"1": [], "2": ["recovery"], "3": ["bootloader"]}
    args = targets.get(ch)
    if args is None:
        return
    try:
        sp.run(["adb", "reboot"] + args, timeout=10)
        ui.ok("Neustart-Befehl gesendet")
    except Exception as e:
        ui.err(str(e))
    ui.pause()


def _ki_twrp_session() -> None:
    """Consent-Dialog + interaktive TWRP-Steuerkonsole für Claude Code."""
    import subprocess as sp
    global _ki_twrp_granted

    if not _ki_twrp_granted:
        # Consent-Bildschirm
        ui.clear()
        ui.banner(subtitle="🤖 KI-TWRP-MODUS · Berechtigungsvergabe")
        ui.rule("⚠  BERECHTIGUNGSVERGABE FÜR CLAUDE CODE", ui.BYELLOW)
        print(f"""
  Du erlaubst der KI (Claude Code, diese Sitzung) folgende TWRP-Operationen:

    {ui.BGREEN}✓{ui.RESET}  TWRP-Status & Versionsprüfung lesen
    {ui.BGREEN}✓{ui.RESET}  ZIP-Dateien auf /sdcard pushen
    {ui.BGREEN}✓{ui.RESET}  Software via  adb shell twrp install  installieren
    {ui.BGREEN}✓{ui.RESET}  adb sideload  für signierte ZIPs
    {ui.BGREEN}✓{ui.RESET}  Cache + Dalvik-Cache leeren
    {ui.BGREEN}✓{ui.RESET}  Neustart in System / Recovery / Bootloader

    {ui.BRED}✗  NIEMALS:{ui.RESET} Data Wipe / Factory Reset
    {ui.BRED}✗  NIEMALS:{ui.RESET} Partitions-Formatierung oder -Löschung
    {ui.BRED}✗  NIEMALS:{ui.RESET} Bootloader-Unlock / System-Partition beschreiben

  Erlaubnis gilt nur für diese Sitzung.  Gerät muss in TWRP-Recovery sein.
""")
        ui.rule(color=ui.BYELLOW)
        ans = ui.ask("Erlaubnis erteilen?  [ja / nein]", "nein").strip().lower()
        if ans not in ("ja", "j", "yes", "y"):
            ui.warn("Abgebrochen – keine Erlaubnis erteilt.")
            time.sleep(1.2)
            return
        _ki_twrp_granted = True
        ui.ok("KI-TWRP-Erlaubnis gesetzt ✓")
        time.sleep(0.8)

    # ── Interaktive TWRP-Konsole ─────────────────────────────────────────────
    while True:
        ui.clear()
        ui.banner(subtitle=f"🤖 KI-TWRP-KONSOLE  •  {ui.BGREEN}● Erlaubnis aktiv{ui.RESET}")

        # Live-Gerätestatus
        try:
            r = sp.run(["adb", "get-state"], capture_output=True, text=True, timeout=3)
            adb_state = r.stdout.strip()
        except Exception:
            adb_state = ""
        try:
            rb = sp.run(["fastboot", "devices"], capture_output=True, text=True, timeout=3)
            fb_lines = [l for l in rb.stdout.strip().splitlines() if l.strip()]
        except Exception:
            fb_lines = []

        ui.rule("📡 GERÄTESTATUS", ui.CYAN)
        if "recovery" in adb_state:
            ui.ok(f"ADB-Recovery aktiv  –  TWRP-Operationen verfügbar")
        elif adb_state == "device":
            ui.ok("ADB-Gerät verbunden  (System-Modus – für TWRP in Recovery starten)")
        elif fb_lines:
            ui.ok(f"Fastboot erkannt: {fb_lines[0]}")
        else:
            ui.warn("Kein Gerät – verbinde Android im TWRP-Recovery-Modus")
        print()

        ui.rule("🛠  OPERATIONEN", ui.CYAN)
        print(f"  {ui.BOLD}1{ui.RESET}  TWRP-Status prüfen   (Version · Mounts · Logs)")
        print(f"  {ui.BOLD}2{ui.RESET}  ZIP installieren     (adb push → twrp install)")
        print(f"  {ui.BOLD}3{ui.RESET}  Sideload-Modus       (adb sideload <zip>)")
        print(f"  {ui.BOLD}4{ui.RESET}  Cache leeren         (Cache + Dalvik)")
        print(f"  {ui.BOLD}5{ui.RESET}  Neustart senden      (System / Recovery / Bootloader)")
        print(f"  {ui.BOLD}0{ui.RESET}  Zurück zum Startmenü")
        print()
        ch = ui.ask("Auswahl", "0")

        if ch == "0":
            return
        elif ch == "1":
            _twrp_status(sp)
        elif ch == "2":
            _twrp_install_zip(sp)
        elif ch == "3":
            _twrp_sideload(sp)
        elif ch == "4":
            _twrp_wipe_cache(sp)
        elif ch == "5":
            _twrp_reboot_menu(sp)
        else:
            ui.warn("Ungültige Option")
            time.sleep(0.4)


def _run_feature(adb: ADB, dev: Device, st: dict, ft: dict) -> None:
    """Führt ein Feature mit Dashboard-Analyse aus."""
    k = ft["k"]
    feature_num = ft["n"]
    feature_title = ft["t"]

    # Create feature dashboard
    dash = dashboard_runner.create_feature_dashboard(feature_num, feature_title, k)

    try:
        if k == "cmd":
            dashboard_runner.run_cmd_feature(adb, dash, ft["p"], timeout=60)
        elif k == "rootcmd":
            if not st.get("is_root"):
                dash.render_header()
                dash.add_warning("Root-Zugriff erforderlich")
                dash.render_complete()
            else:
                dashboard_runner.run_rootcmd_feature(adb, dash, ft["p"], timeout=60)
        elif k == "ask":
            prompt, template = ft["p"]
            dashboard_runner.run_ask_feature(dash, prompt, template, adb)
        elif k == "fn":
            dashboard_runner.run_interactive_feature(dash, lambda: ft["p"](adb, dev, st))
        elif k == "info":
            dashboard_runner.run_info_feature(dash, ft["p"])
        elif k == "sdr":
            dashboard_runner.run_sdr_feature(dash, ft["p"])
        elif k == "danger":
            dashboard_runner.run_danger_feature(dash, ft["p"])
        else:
            dash.render_header()
            dash.add_error(f"Unbekannte Feature-Art: {k}")
            dash.render_complete()

    except AdbError as e:
        dash.add_error(f"ADB-Fehler: {e}")
        LOG.exception(f"ADB-Fehler in Feature #{feature_num} {feature_title}", e)
    except KeyboardInterrupt:
        dash.add_warning("Abgebrochen (Strg+C)")
    except Exception as e:  # noqa: BLE001
        dash.add_error(f"Fehler: {e}")
        LOG.exception(f"Feature #{feature_num} {feature_title}", e)


def _badge_for(k: str) -> str:
    return {"cmd": "adb", "rootcmd": "root", "ask": "adb", "fn": "live",
            "info": "info", "sdr": "sdr", "danger": "danger"}.get(k, "adb")


def _category_menu(adb: ADB, dev: Device, st: dict, cat_index: int) -> None:
    icon, name, feats = registry.CATEGORIES[cat_index]
    while True:
        ui.clear()
        ui.banner(subtitle=f"Kategorie {cat_index+1}/45 · {name}")
        entries = []
        for ft in feats:
            entries.append((str(ft["n"]), f"{ft['t']}  {ui.badge(_badge_for(ft['k']))}"))
        ch = ui.menu(f"{icon}  {name}", entries, back_label=lang.t("cat_back"))
        if ch == "quit":
            raise KeyboardInterrupt
        if ch == "back":
            return
        ft = next((x for x in feats if str(x["n"]) == ch), None)
        if ft:
            _run_feature(adb, dev, st, ft)
        else:
            ui.warn(lang.t("menu_invalid"))
            time.sleep(0.6)


def _categories_overview(adb: ADB, dev: Device, st: dict) -> None:
    while True:
        ui.clear()
        ui.banner(subtitle=lang.t("cat_overview_title"))
        w = ui.width()
        col = 1 if w < 80 else 2
        cats = registry.CATEGORIES
        half = (len(cats) + 1) // 2 if col == 2 else len(cats)
        for i in range(half):
            left = cats[i]
            cell_l = f"{ui.CYAN}{i+1:>2}{ui.RESET} {left[0]} {left[1][:32]:<32}"
            if col == 2 and i + half < len(cats):
                r = cats[i + half]
                cell_r = f"{ui.CYAN}{i+half+1:>2}{ui.RESET} {r[0]} {r[1][:32]}"
                print(f"  {cell_l}   {cell_r}")
            else:
                print(f"  {cell_l}")
        _menu_lbl = lang.t("menu_main_title")
        _quit_lbl = lang.t("ui_quit")
        print(f"\n  {ui.BOLD}{ui.GREY} 0{ui.RESET}  {_menu_lbl}   {ui.GREY}q{ui.RESET}  {_quit_lbl}")
        sel = ui.ask(lang.t("cat_ask")).lower()
        if sel in ("0", "b", "back"):
            return
        if sel in ("q", "quit"):
            raise KeyboardInterrupt
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(registry.CATEGORIES):
                _category_menu(adb, dev, st, idx)
            else:
                ui.warn(lang.t("cat_out_of_range"))
                time.sleep(0.6)
        except ValueError:
            ui.warn(lang.t("cat_enter_number"))
            time.sleep(0.6)


def _depth_engine(adb: ADB, dev: Device, st: dict) -> None:
    """Submenü für die vier Tiefen-Module."""
    while True:
        ui.clear()
        ui.banner(subtitle=f"🧠 {lang.t('depth_title')}")
        ui.info(lang.t("depth_frida_note"))
        ch = ui.menu("Module", [
            ("1", "🧬  Frida-Runtime-Engine (Hooks: Keys, Passwörter, SSL-Unpin, Tokens)"),
            ("2", "🌐  Traffic-Interception (mitmproxy + Frida → HTTPS-Klartext)"),
            ("3", "💬  Messenger-Decrypt & HTML-Timeline (WhatsApp/Telegram/Signal)"),
            ("4", "🗓   Super-Timeline & Geo-Mapping (alle Spuren + Foto-GPS→KML)"),
        ], back_label=lang.t("menu_main_title"))
        if ch in ("back", "quit"):
            return
        {"1": frida_engine.menu, "2": traffic.menu,
         "3": messenger.menu, "4": timeline.menu}.get(ch, lambda *a: None)(adb, dev, st)


def _main_menu(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    # Use numeric menu instead
    _numeric_main_menu(adb, dev, st, data)


def _check_and_reconnect(adb: ADB, dev: Device) -> bool:
    """Prüft ADB-Verbindung; versucht automatischen Reconnect wenn nötig.

    Gibt True zurück wenn das Gerät erreichbar ist, False wenn aufgegeben.
    """
    if adb.is_connected():
        return True
    ui.warn("⚠  ADB-Verbindung verloren – versuche Reconnect …")
    if adb.ensure_connected(max_wait=30):
        ui.ok("✓ Verbindung wiederhergestellt.")
        return True
    ui.err("Gerät nicht erreichbar. Bitte Kabel prüfen und USB-Debugging bestätigen.")
    return False


def _h1(a, d, s, x):
    sc = deep_analysis_scan.create_deep_analysis_scan(a)
    sc.run_complete_scan()
    sc.show_scan_dashboard()
    ui.pause()

def _h2(a, d, s, x):
    dashboard.render(a, d, x)
    ui.pause()

def _h6(a, d, s, x):  microphone_tap.create_microphone_tap(a).show_microphone_menu()
def _h7(a, d, s, x):  camera_tap.create_camera_tap(a).show_camera_menu()
def _h8(a, d, s, x):  network_analyzer.create_network_analyzer(a).show_network_menu()

def _h20(a, d, s, x):
    rooting.show_and_offer(a, d, x, s)
    s["is_root"] = a.check_root()
    x["root"] = s["is_root"]

def _h57(a, d, s, x):
    from playstore_forensics.main import menu as _m
    _m(a, d, s)

def _h58(a, d, s, x):
    from . import encryption_scanner
    encryption_scanner.menu(a, d, s)

def _h59(a, d, s, x):
    from . import geo_forensics
    geo_forensics.menu(a, d, s)

def _h60(a, d, s, x):
    from . import sensor_forensics
    sensor_forensics.menu(a, d, s)


# Menünummer → (Anzeigelabel, Handler(adb, dev, st, data))
# Kein ADB nötig: 4, 5, 42, 49, 55 (lokale Logik / kein Gerät nötig)
# Kein ADB nötig: reine Internet/Offline-Funktionen können ohne verbundenes Gerät laufen.
# 4/5=Einstellungen, 26=Tracker(IP/Geo), 42=Bootloop-Monitor, 43=OSINT, 49=Labsetup,
# 51=Telefon-OSINT, 55=SIM-Toolkit (lokale Anzeige).
_NO_ADB: frozenset[str] = frozenset({"4", "5", "26", "42", "43", "49", "51", "55"})

_DISPATCH: dict[str, tuple[str, object]] = {
    "1":  ("🔬 TIEFE ANALYSE",            _h1),
    "2":  ("📊 DASHBOARD",                _h2),
    "3":  ("📋 KATEGORIEN",               lambda a, d, s, x: _categories_overview(a, d, s)),
    "4":  ("🎨 UI THEME",                 lambda a, d, s, x: settings_manager.show_theme(a)),
    "5":  ("⚙️  EINSTELLUNGEN",           lambda a, d, s, x: settings_manager.show_settings(a)),
    "6":  ("🎙️  MICROPHONE TAP",          _h6),
    "7":  ("📷 CAMERA TAP",               _h7),
    "8":  ("🌐 NETWORK ANALYZER",         _h8),
    "9":  ("🔍 FORENSIK SUITE",           lambda a, d, s, x: forensics.menu(a, s)),
    "10": ("📦 APK SCANNER",              lambda a, d, s, x: apkscan.menu(a, d, s)),
    "11": ("🗃️  APP SCANNER",             lambda a, d, s, x: appscan.menu(a, d, s, x)),
    "12": ("📁 DATEI TREE",               lambda a, d, s, x: filetree.menu(a, d, s)),
    "13": ("💾 DATEN FORENSIK",           lambda a, d, s, x: dataforensics.menu(a, d, s)),
    "14": ("🎯 TIEFE ENGINE",             lambda a, d, s, x: _depth_engine(a, d, s)),
    "15": ("🗂️  CASE DATABASE",           lambda a, d, s, x: casedb.menu(a, d, s, x)),
    "16": ("📄 REPORT GENERATOR",         lambda a, d, s, x: report.menu(a, d, s, x)),
    "17": ("🔄 MODE SWITCH",              lambda a, d, s, x: modeswitch.menu(a, d, s, x)),
    "18": ("🔧 CUSTOM FIRMWARE",          lambda a, d, s, x: customfw.show_custom_firmware(a, d, s, x)),
    "19": ("🌐 ROOTKIT SCANNER",          lambda a, d, s, x: rootkit.menu(a, d, s)),
    "20": ("🚀 ROOTING TOOLS",            _h20),
    "21": ("📸 DATA ACQUISITION",         lambda a, d, s, x: acquire.menu(a, d, s, x)),
    "22": ("🔓 APP DECRYPTION",           lambda a, d, s, x: app_decryption.menu(a)),
    "23": ("🔨 BRUTE FORCE",              lambda a, d, s, x: brute_force.menu(a)),
    "24": ("📡 WIFI HANDSHAKE",           lambda a, d, s, x: wifi_handshake.menu(a)),
    "25": ("🛡️  DNS GUARDIAN",            lambda a, d, s, x: dns_guardian.menu(a)),
    "26": ("🎯 TRACKER SYSTEM",           lambda a, d, s, x: tracker_system.menu(a)),
    "27": ("🧠 INTELLIGENT ENGINE",       lambda a, d, s, x: intelligent_engine.menu(a)),
    "28": ("💾 DATABASE SCANNER",         lambda a, d, s, x: database_scanner.menu(a)),
    "29": ("🧪 LAB MANAGER",              lambda a, d, s, x: lab_manager.menu(a)),
    "30": ("🌐 3D WIFI SCANNER",          lambda a, d, s, x: wifi_room_scanner_3d.menu(a)),
    "31": ("🔍 ADULT DETECTOR",           lambda a, d, s, x: adult_activity_detector.menu(a)),
    "32": ("🔴 ANOMALY DETECTOR",         lambda a, d, s, x: anomaly_detector.menu(a)),
    "33": ("🏥 AI DOCTOR",                lambda a, d, s, x: ai_doctor.menu(a)),
    "34": ("🔬 FORENSIC ANALYZER",        lambda a, d, s, x: forensic_audio_analyzer.menu(a)),
    "35": ("🔐 SECURITY FRAMEWORK",       lambda a, d, s, x: security_framework.menu(a)),
    "36": ("🔑 PASSWORD MANAGER",         lambda a, d, s, x: password_manager.menu(a)),
    "37": ("🎵 AUDIO PLAYBACK",           lambda a, d, s, x: audio_playback.menu(a)),
    "38": ("🐚 ADB SHELL",                lambda a, d, s, x: adb_shell.menu(a)),
    "39": ("🔓 AUTO ROOT ENGINE",         lambda a, d, s, x: auto_root_engine.menu(a)),
    "40": ("🎤 KEYWORD RECORDER",         lambda a, d, s, x: keyword_recorder.menu(a)),
    "41": ("🚑 AUTO-RESCUE",              lambda a, d, s, x: rescue.auto_rescue(d)),
    "42": ("📡 BOOTLOOP-MONITOR",         lambda a, d, s, x: bootloop.monitor()),
    "43": ("🕵  OSINT-TOOLKIT",           lambda a, d, s, x: osint.menu(a, d, s)),
    "44": ("🤖 KI-ADB-SHELL",             lambda a, d, s, x: aishell.menu(a, d, s)),
    "45": ("📱 SAMSUNG TOOLS",            lambda a, d, s, x: samsung.menu(a, d, s, x)),
    "46": ("🔶 MEDIATEK ROOT",            lambda a, d, s, x: mediatek.menu(a, d, s, x)),
    "47": ("🏷  HERSTELLER-TOOLS",        lambda a, d, s, x: brands.menu(a, d, s, x)),
    "48": ("📶 MOBILFUNK-MONITOR",        lambda a, d, s, x: handlers.cell_monitor(a, d, s)),
    "49": ("🧪 LABOR-EINRICHTUNG",        lambda a, d, s, x: labsetup.menu(a, d, s)),
    "50": ("🔬 DEEP-FORENSIK",            lambda a, d, s, x: deepforensics.menu(a, d, s)),
    "51": ("📞 TELEFON-OSINT",            lambda a, d, s, x: phoneosint.menu(a, d, s)),
    "52": ("🔑 GOOGLE-KONTEN",            lambda a, d, s, x: google_account_scanner.menu(a)),
    "53": ("📱 KONTO-SCANNER",            lambda a, d, s, x: account_scanner.menu(a)),
    "54": ("🔒 FRP-SCANNER",              lambda a, d, s, x: frp_scanner.menu(a)),
    "55": ("💳 SIM-TOOLKIT",              lambda a, d, s, x: sim_toolkit.menu(a, d, s)),
    "56": ("🌐 APP-DOMAIN MONITOR",       lambda a, d, s, x: app_traffic_monitor.menu(a, d, s, x)),
    "57": ("🕵️  PLAY STORE FORENSICS",    _h57),
    "58": ("🔐 VERSCHLÜSSELUNGS-SCANNER", _h58),
    "59": ("📍 GEO-FORENSIK",             _h59),
    "60": ("🧬 SENSOR-FORENSIK",          _h60),
    "61": ("🔒 BOOTLOADER SPERREN",        lambda a, d, s, x: __import__('apz.bootloader_locker', fromlist=['menu']).menu(a, d, s, x)),
    "62": ("🧠 GERÄT-KI SUPERUSER",        lambda a, d, s, x: ai_root_deployer.menu(a, d, s)),
}


def _numeric_main_menu(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    """Hauptmenü NUR MIT ZAHLEN (1-60)."""
    while True:
        try:
            num_menu = numeric_menu.create_numeric_menu(adb)

            ui.clear()
            try:
                connected = adb.is_connected()
            except Exception:  # noqa: BLE001
                connected = False
            conn_badge = (f"{ui.BGREEN}● ADB verbunden{ui.RESET}" if connected
                          else f"{ui.BRED}✖ KEIN GERÄT{ui.RESET}")
            root_txt = (f"{ui.BGREEN}● {lang.t('menu_rooted')}{ui.RESET}" if st.get("is_root")
                        else f"{ui.GREY}○ {lang.t('menu_not_rooted')}{ui.RESET}")
            ui.banner(subtitle=f"{data.get('brand','')} {data.get('model','')}  •  {conn_badge}  •  Root: {root_txt}")

            choice = num_menu.show_numeric_menu({})

            if choice in ("Q", "0"):
                return
            if choice == "A":
                if ui.is_auto() and ui.auto_remaining() == 0.0:
                    # Permanenter Auto war aktiv → ausschalten
                    ui.set_auto(False)
                    ui.ok(f"Auto-Modus {ui.GREY}DEAKTIVIERT{ui.RESET}")
                elif ui.is_auto():
                    # Timer oder permanent → ausschalten
                    ui.set_auto(False)
                    ui.set_auto_timer(0)
                    ui.ok(f"Auto-Modus {ui.GREY}DEAKTIVIERT{ui.RESET}")
                else:
                    # Einschalten: Dauer wählen
                    print(f"\n  {ui.BOLD}AUTO-MODUS DAUER:{ui.RESET}")
                    print(f"  {ui.CYAN}1{ui.RESET}  1 Stunde  (empfohlen)")
                    print(f"  {ui.CYAN}2{ui.RESET}  30 Minuten")
                    print(f"  {ui.CYAN}3{ui.RESET}  15 Minuten")
                    print(f"  {ui.CYAN}4{ui.RESET}  Permanent (kein Ablauf)")
                    print(f"  {ui.GREY}0  Abbrechen{ui.RESET}")
                    dur_ch = ui.ask("Dauer", "1").strip()
                    dur_map = {"1": 3600, "2": 1800, "3": 900}
                    if dur_ch == "4":
                        ui.set_auto(True)
                        ui.ok(f"Auto-Modus {ui.BGREEN}PERMANENT AKTIV{ui.RESET}  (kein y/ENTER nötig)")
                    elif dur_ch in dur_map:
                        secs = dur_map[dur_ch]
                        ui.set_auto_timer(secs)
                        mins = secs // 60
                        ui.ok(f"Auto-Modus {ui.BGREEN}AKTIV für {mins} Minuten{ui.RESET}  ⏱")
                    else:
                        pass
                time.sleep(1)
                continue

            choice_lower = choice.lower()
            entry = _DISPATCH.get(choice_lower)
            if entry is None:
                ui.warn("Ungültige Option!")
                time.sleep(0.5)
                continue

            label, fn = entry
            if choice_lower not in _NO_ADB:
                if not _check_and_reconnect(adb, dev):
                    ui.pause()
                    continue

            progress.run_steps(label, progress.get_steps(choice_lower))
            fn(adb, dev, st, data)

        except KeyboardInterrupt:
            ui.warn("Unterbrochen")
            return
        except Exception as e:
            ui.err(f"Fehler: {e}")
            ui.pause()


def _main_menu_OLD(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    """Altes Menü mit Buchstaben - DEPRECATED."""
    while True:
        try:
            ui.clear()
            root_txt = (f"{ui.BGREEN}● {lang.t('menu_rooted')}{ui.RESET}" if st.get("is_root")
                        else f"{ui.GREY}○ {lang.t('menu_not_rooted')}{ui.RESET}")
            ui.banner(subtitle=f"{data.get('brand','')} {data.get('model','')}  •  Root: {root_txt}")
            stats = registry.kind_stats()
            ui.kv(lang.t("menu_functions_label"),
                  f"450 in 45  "
                  f"{ui.GREY}({stats.get('cmd',0)+stats.get('ask',0)+stats.get('fn',0)} ADB, "
                  f"{stats.get('rootcmd',0)} Root, {stats.get('sdr',0)} SDR/HW){ui.RESET}")
            print()
            entries = [
                ("!", f"🔬  {ui.BGREEN}{ui.BOLD}TIEFE ANALYSE - ALLE 450 FEATURES{ui.RESET}"),
                ("D", f"📊  {lang.t('menu_D')}"),
                ("K", f"🗂   {lang.t('menu_K')}"),
            ]
            if st.get("is_root"):
                entries.append(
                    ("X", f"{ui.BGREEN}{ui.BOLD}🔓  {lang.t('menu_X')}{ui.RESET}"))
            else:
                entries.append(("R", f"🔓  {lang.t('menu_R')}"))
            entries += [
                ("V", f"{ui.BGREEN}{ui.BOLD}🧬  {lang.t('menu_V')}{ui.RESET}"),
                ("S", f"🔎  {lang.t('menu_S')}"),
                ("A", f"🧪  {lang.t('menu_A')}"),
                ("U", f"{ui.BCYAN}{ui.BOLD}🗃   {lang.t('menu_U')}{ui.RESET}"),
                ("O", f"🗂   {lang.t('menu_O')}"),
                ("F", f"🧬  {lang.t('menu_F')}"),
                ("T", f"{ui.BCYAN}{ui.BOLD}🧠  {lang.t('menu_T')}{ui.RESET}"),
                ("B", f"📁  {lang.t('menu_B')}"),
                ("E", f"📑  {lang.t('menu_E')}"),
                ("Y", f"{ui.BCYAN}🔁  {lang.t('menu_Y')}{ui.RESET}"),
                ("J", f"{ui.BCYAN}🌐  {lang.t('menu_J')}{ui.RESET}"),
                ("P", f"📉  {lang.t('menu_P')}"),
                ("Z", f"{ui.BGREEN}🚑  {lang.t('menu_Z')}{ui.RESET}"),
                ("L", f"📡  {lang.t('menu_L')}"),
                ("N", f"🕵️   {lang.t('menu_N')}"),
                ("W", f"{ui.BCYAN}🧪  {lang.t('menu_W')}{ui.RESET}"),
                ("C", f"⌨   {lang.t('menu_C')}"),
            ]
            if st.get("is_root"):
                entries.append(("R", f"🔧  {lang.t('menu_R_detail')}"))
            # Hersteller-spezifische Menüeinträge (alle führenden Marken)
            brand_lc = (data.get("brand", "") + data.get("model", "")).lower()
            if "samsung" in brand_lc:
                entries.append(("G", f"{ui.BCYAN}🔱  {lang.t('menu_G')}{ui.RESET}"))
            if data.get("is_mtk"):
                entries.append(("M", f"{ui.BCYAN}🔶  {lang.t('menu_M')}{ui.RESET}"))
            if data.get("is_xiaomi"):
                entries.append(("H", f"{ui.BCYAN}📱  {lang.t('menu_H')}{ui.RESET}"))
            elif data.get("is_pixel"):
                entries.append(("H", f"{ui.BCYAN}📱  {lang.t('menu_H_pixel')}{ui.RESET}"))
            elif data.get("is_oneplus"):
                entries.append(("H", f"{ui.BCYAN}📱  {lang.t('menu_H_oneplus')}{ui.RESET}"))
            elif data.get("is_motorola"):
                entries.append(("H", f"{ui.BCYAN}📱  {lang.t('menu_H_motorola')}{ui.RESET}"))
            elif data.get("is_huawei"):
                entries.append(("H", f"{ui.BCYAN}📱  {lang.t('menu_H_huawei')}{ui.RESET}"))
            entries.append(("I", f"{ui.BGREEN}🤖  {lang.t('menu_I')}{ui.RESET}"))
            entries.append(("Q", f"{ui.BRED}🎙️  MICROPHONE TAP{ui.RESET}"))
            entries.append(("W2", f"{ui.BRED}📷  CAMERA TAP{ui.RESET}"))
            entries.append(("NET", f"{ui.BCYAN}🌐  NETWORK ANALYZER{ui.RESET}"))
            entries.append(("ACS", f"{ui.BCYAN}🔍  ADULT CONTENT SCANNER{ui.RESET}"))
            entries.append(("VFS", f"{ui.BGREEN}💾  VIRTUAL FILESYSTEM{ui.RESET}"))
            entries.append(("TPL", f"{ui.BGREEN}📦  VFS TEMPLATES{ui.RESET}"))
            entries.append(("ANO", f"{ui.BRED}🚨  ANOMALY DETECTOR (ROT PULSIEREND){ui.RESET}"))
            entries.append(("DOC", f"{ui.BGREEN}🏥  AI DOCTOR (Auto-Fix){ui.RESET}"))
            entries.append(("DEC", f"{ui.BCYAN}🔓  APP DECRYPTION (Hashcat){ui.RESET}"))
            entries.append(("BF", f"{ui.BRED}🔨  BRUTE-FORCE ARSENAL (50 Modi){ui.RESET}"))
            entries.append(("WIFI", f"{ui.BCYAN}📡  WIFI HANDSHAKE CAPTURE{ui.RESET}"))
            entries.append(("DNS", f"{ui.BGREEN}🛡️  DNS GUARDIAN (Monitor/Filter){ui.RESET}"))
            entries.append(("TRACK", f"{ui.BMAGENTA}🎯  TRACKER SYSTEM (IP/Phone/Geo){ui.RESET}"))
            entries.append(("INTEL", f"{ui.BMAGENTA}🧠  INTELLIGENT ENGINE (ML/KI/Automation){ui.RESET}"))
            entries.append(("DBSCAN", f"{ui.BYELLOW}💾  DATABASE SCANNER (Clone/Archive){ui.RESET}"))
            entries.append(("LABS", f"{ui.BGREEN}🧪  LAB MANAGER (venv Installation){ui.RESET}"))
            entries.append(("AAD", f"{ui.BRED}🔍  ADULT ACTIVITY DETECTOR (Audio+Geruch){ui.RESET}"))
            entries.append(("W3D", f"{ui.BCYAN}🌐  3D WiFi ROOM SCANNER (Raum-Kartographie){ui.RESET}"))
            ch = ui.menu(lang.t("menu_main_title"), entries,
                         back_label=lang.t("menu_back_choose_device"))
            if ch == "quit":
                return
            if ch == "back":
                return
            if ch == "!":
                # 🔬 TIEFE ANALYSE - ALLE 450 FEATURES
                scanner = deep_analysis_scan.create_deep_analysis_scan(adb)
                result = scanner.run_complete_scan()
                scanner.show_scan_dashboard()
                ui.pause()
            elif ch == "d":
                dashboard.render(adb, dev, data)
                ui.pause()
            elif ch == "k":
                _categories_overview(adb, dev, st)
            elif ch == "x" and st.get("is_root"):
                rootkit.menu(adb, dev, st)
            elif ch == "r":
                rooting.show_and_offer(adb, dev, data, st)
                st["is_root"] = adb.check_root()
                data["root"] = st["is_root"]
            elif ch == "v":
                acquire.menu(adb, dev, st, data)
            elif ch == "s":
                forensics.menu(adb, st)
            elif ch == "a":
                apkscan.menu(adb, dev, st)
            elif ch == "u":
                appscan.menu(adb, dev, st, data)
            elif ch == "o":
                filetree.menu(adb, dev, st)
            elif ch == "f":
                dataforensics.menu(adb, dev, st)
            elif ch == "t":
                _depth_engine(adb, dev, st)
            elif ch == "b":
                casedb.menu(adb, dev, st, data)
            elif ch == "e":
                report.menu(adb, dev, st, data)
            elif ch == "y":
                modeswitch.menu(adb, dev, st, data)
            elif ch == "j":
                customfw.show_custom_firmware(adb, dev, st, data)
            elif ch == "p":
                bootloop.monitor()
            elif ch == "z":
                rescue.auto_rescue(dev)
            elif ch == "g" and "samsung" in (data.get("brand", "") + data.get("model", "")).lower():
                samsung.menu(adb, dev, st, data)
            elif ch == "m" and data.get("is_mtk"):
                mediatek.menu(adb, dev, st, data)
            elif ch == "h" and any(data.get(k) for k in
                                   ("is_xiaomi", "is_pixel", "is_oneplus", "is_motorola", "is_huawei")):
                brands.menu(adb, dev, st, data)
            elif ch == "i":
                aishell.menu(adb, dev, st)
            elif ch == "q":
                mic_tap = microphone_tap.create_microphone_tap(adb)
                mic_tap.show_microphone_menu()
            elif ch == "w2":
                cam_tap = camera_tap.create_camera_tap(adb)
                cam_tap.show_camera_menu()
            elif ch == "net":
                net_analyzer = network_analyzer.create_network_analyzer(adb)
                net_analyzer.show_network_menu()
            elif ch == "acs":
                acs = adult_content_scanner.create_adult_content_scanner(adb)
                acs.show_scanner_menu()
            elif ch == "vfs":
                vfs = virtual_filesystem.create_virtual_filesystem(adb)
                vfs.show_vfs_menu()
            elif ch == "tpl":
                tpl_mgr = vfs_templates.create_vfs_template_manager(adb)
                tpl_mgr.show_template_menu()
            elif ch == "ano":
                anom_detector = anomaly_detector.create_anomaly_detector(adb)
                anom_detector.show_anomaly_detector_menu()
            elif ch == "doc":
                doctor = ai_doctor.create_ai_doctor(adb)
                doctor.show_ai_doctor_menu()
            elif ch == "dec":
                decryption = app_decryption.create_app_decryption_engine(adb)
                decryption.show_decryption_menu()
            elif ch == "bf":
                bf_arsenal = brute_force.create_brute_force_arsenal(adb)
                bf_arsenal.show_brute_force_menu()
            elif ch == "wifi":
                wifi_cap = wifi_handshake.create_wifi_handshake_capture(adb)
                wifi_cap.show_wifi_capture_menu()
            elif ch == "dns":
                dns_guard = dns_guardian.create_dns_guardian(adb)
                dns_guard.show_dns_guardian_menu()
            elif ch == "track":
                tracker = tracker_system.create_tracker_system(adb)
                tracker.show_tracker_menu()
            elif ch == "intel":
                engine = intelligent_engine.create_intelligent_engine(adb)
                engine.show_intelligent_engine_menu()
            elif ch == "dbscan":
                scanner = database_scanner.create_database_scanner(adb)
                scanner.show_database_scanner_menu()
            elif ch == "labs":
                lm = lab_manager.create_lab_manager(adb)
                lm.show_lab_manager_menu()
            elif ch == "aad":
                detector = adult_activity_detector.create_adult_activity_detector(adb)
                detector.show_adult_detector_menu()
            elif ch == "w3d":
                scanner_3d = wifi_room_scanner_3d.create_wifi_3d_scanner(adb)
                scanner_3d.show_wifi_3d_scanner_menu()
            elif ch == "n":
                from . import osint
                osint.menu(adb, dev, st)
            elif ch == "w":
                labsetup.menu(adb, dev, st)
            elif ch == "l":
                from .handlers import cell_monitor
                ui.clear()
                cell_monitor(adb, dev, st)
            elif ch == "c":
                sub = ui.menu(lang.t("adb_console_title"), [
                    ("1", lang.t("adb_console_interactive")),
                    ("2", lang.t("adb_console_single")),
                ], back_label=lang.t("ui_back"))
                if sub == "1":
                    ui.clear()
                    ui.info(lang.t("adb_console_interactive_hint"))
                    base = [adb.bin] + (["-s", dev.serial] if dev.serial else []) + ["shell"]
                    try:
                        import subprocess as _sp
                        _sp.call(base)
                    except KeyboardInterrupt:
                        pass
                    ui.pause(lang.t("adb_console_back_hint"))
                elif sub == "2":
                    cmd = ui.ask(lang.t("adb_console_cmd_prompt"))
                    if cmd:
                        asroot = st.get("is_root") and ui.confirm(lang.t("adb_console_as_root"), False)
                        ui.pager(adb.shell(cmd, timeout=120, root=asroot) or lang.t("ui_no_output"), cmd)
                        ui.pause()
            else:
                ui.warn(lang.t("menu_invalid"))
                time.sleep(0.6)
        except KeyboardInterrupt:
            print()
            try:
                if ui.confirm(lang.t("menu_quit_confirm"), True):
                    return
            except KeyboardInterrupt:
                return


_snapshot_offered_serials: set[str] = set()

def _maybe_offer_snapshot(adb: ADB, dev: Device) -> None:
    """Bietet Snapshot-Erstellung an – einmal pro Gerät pro Sitzung."""
    if dev.serial in _snapshot_offered_serials:
        return
    _snapshot_offered_serials.add(dev.serial)
    # Prüfen ob für dieses Gerät bereits ein aktueller Snapshot existiert
    existing = [s for s in device_snapshot.SnapshotManager.list_all()
                if s.device_serial == dev.serial]
    if existing:
        latest = max(existing, key=lambda s: s.created_at)
        import time as _t
        days_old = (_t.time() - latest.created_at) / 86400
        if days_old < 7:
            return   # Frischer Snapshot vorhanden, nicht nochmals fragen
    print()
    ui.rule("GERÄT-SNAPSHOT", ui.CYAN)
    print(f"  {ui.GREY}Ein Snapshot ermöglicht spätere Offline-Analyse ohne Gerät.{ui.RESET}")
    if existing:
        print(f"  {ui.GREY}Letzter Snapshot: {existing[-1].created_iso} (>{int(days_old)}d alt){ui.RESET}")
    print()
    if ui.confirm("Jetzt Snapshot erstellen?", False):
        device_snapshot.offer_create_snapshot(adb, dev)
        ui.ask("Weiter …", "")


def run() -> int:
    # 🎨 MODERN STARTUP SCREEN + vollständiger 54-Modul-Scan
    _startup_failures = modern_startup.animate_startup()
    if _startup_failures:
        LOG.warn("Startup: %d Module fehlerhaft: %s" % (
            len(_startup_failures),
            [f"[{n}] {name}" for n, name, _ in _startup_failures]))

    try:
        ADB.start_server()
    except AdbError as e:
        ui.err(str(e))
        return 2

    while True:
        dev = _connect()
        if dev is None:
            ui.warn(lang.t("run_no_device_abort"))
            return 1

        # Modus-Routing: nur adb-fähige Modi gehen ins volle Tool
        if dev.mode == "fastboot":
            ui.pause(f"\n{ui.MAGENTA}{lang.t('run_fastboot_notice')}{ui.RESET}")
            usb.fastboot_menu(dev)
            if not ui.confirm(lang.t("run_other_device"), True):
                ui.clear(); ui.ok(f"{lang.t('run_goodbye')} 🛡"); return 0
            continue
        if not dev.adb_capable:
            usb.mode_info(dev)
            if not ui.confirm(lang.t("run_other_device"), True):
                ui.clear(); ui.ok(f"{lang.t('run_goodbye')} 🛡"); return 0
            continue

        # ── Snapshot-Modus: virtuelles Gerät aus gespeichertem Abbild ────────
        if dev.mode == "snapshot":
            snap_id = dev.serial.replace("virtual:", "", 1)
            vadb = device_snapshot.VirtualADB.load(snap_id)
            if vadb is None:
                ui.err("Snapshot konnte nicht geladen werden.")
                continue
            meta = vadb._meta
            ui.clear()
            ui.banner(subtitle=(
                f"{ui.BYELLOW}OFFLINE-MODUS{ui.RESET}  ·  "
                f"{meta.device_brand} {meta.device_model}  "
                f"({meta.created_iso})"
            ))
            print(f"\n  {ui.BYELLOW}💾 Snapshot aktiv – kein physisches Gerät angeschlossen.{ui.RESET}")
            print(f"  {ui.GREY}Tiers: {', '.join(meta.tiers_done) or '—'}  ·  "
                  f"{meta.size_str}  ·  "
                  f"{'Root' if meta.is_rooted else 'Kein Root'}{ui.RESET}\n")
            data = {
                "model":           meta.device_model,
                "brand":           meta.device_brand,
                "serial":          meta.device_serial,
                "android_version": meta.android_ver,
                "root":            meta.is_rooted,
            }
            st = {"is_root": meta.is_rooted, "offline": True}
            ui.pause("  [ENTER] → Offline-Analyse starten")
            _main_menu(vadb, dev, st, data)
            if not ui.confirm(lang.t("run_other_device"), False):
                ui.clear()
                ui.ok(f"{lang.t('run_goodbye')} 🛡")
                return 0
            continue

        # ── Echtes Gerät ──────────────────────────────────────────────────────
        adb = ADB(serial=dev.serial)
        ui.clear()
        note = "" if dev.mode == "adb" else f"  ({ui.BYELLOW}{dev.mode.upper()}-Modus – Funktionen eingeschränkt{ui.RESET})"
        ui.banner(subtitle=lang.t("run_analyzing", label=f"{dev.label}{note}"))
        ui.info(lang.t("run_collecting"))
        try:
            data = dashboard.collect(adb, dev)
        except Exception as e:  # noqa: BLE001
            ui.err(f"Analyse-Fehler: {e}")
            LOG.exception("Dashboard-Analyse", e)
            data = {"model": dev.model, "serial": dev.serial, "root": adb.check_root()}

        st = {"is_root": bool(data.get("root"))}
        if not st["is_root"]:
            try:
                rootprep.start_background(data, st)
            except Exception as e:  # noqa: BLE001
                LOG.exception("rootprep-start", e)

        dashboard.render(adb, dev, data)

        # Sicherheits-Schnellcheck direkt nach dem Dashboard (kein clear)
        try:
            modern_startup.show_boot_device_analysis(adb, data, st)
        except Exception as e:  # noqa: BLE001
            LOG.exception("boot-device-analysis", e)

        if not st["is_root"]:
            ui.info(lang.t("run_not_rooted"))

        # ── Snapshot-Angebot (einmalig pro Sitzung, wenn noch keiner existiert) ──
        try:
            _maybe_offer_snapshot(adb, dev)
        except Exception as e:  # noqa: BLE001
            LOG.exception("snapshot-offer", e)

        ui.pause(lang.t("run_go_menu"))

        _main_menu(adb, dev, st, data)

        if not ui.confirm(lang.t("run_other_device"), False):
            ui.clear()
            ui.ok(f"{lang.t('run_goodbye')} 🛡")
            return 0


if __name__ == "__main__":
    sys.exit(run())
