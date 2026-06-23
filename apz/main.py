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
               account_scanner, frp_scanner, progress, sim_toolkit)
from .adb import ADB, AdbError, Device
from .util import LOG


def _connect() -> Device | None:
    """Erkennt jedes Android-Gerät in JEDEM Modus (adb/fastboot/edl/mtk/odin/nodebug)."""
    ADB.start_server()
    ui.clear()
    ui.banner(subtitle=lang.t("connect_title"))

    devs = usb.detect_all()
    if not devs:
        ui.info(lang.t("connect_no_device"))
        ui.info(lang.t("connect_detects"))
        print()
        ui.info(lang.t("connect_prompt_line"))
        c = ui.ask(lang.t("ui_select"), "").lower()
        if c == "q":
            return None
        if c == "m":
            bootloop.monitor()
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
    sel = ui.ask(lang.t("connect_choose_device"), "1")
    try:
        return devs[int(sel) - 1]
    except (ValueError, IndexError):
        return devs[0]


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


def _numeric_main_menu(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    """Hauptmenü NUR MIT ZAHLEN (1-40)."""
    # Module die KEIN aktives ADB-Gerät brauchen (nur lokale Logik / Einstellungen)
    _no_adb_needed = {"4", "5", "42", "49", "q", "55"}
    while True:
        try:
            num_menu = numeric_menu.create_numeric_menu(adb)

            ui.clear()
            # Verbindungsstatus in der Banner-Zeile anzeigen
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

            if choice == "Q":
                return
            if choice == "0":
                return

            # Map numbers to handlers
            choice_lower = choice.lower()

            # Für ADB-pflichtige Module: Verbindung sicherstellen
            if choice_lower not in _no_adb_needed:
                if not _check_and_reconnect(adb, dev):
                    ui.pause()
                    continue

            # ── Live-Balken-Wrapper: für ALLE 54 Module automatisch ──────────
            _bar = progress.run_steps
            _s   = progress.get_steps

            if choice_lower == "1":
                _bar("🔬 TIEFE ANALYSE", _s("1"))
                scanner = deep_analysis_scan.create_deep_analysis_scan(adb)
                result = scanner.run_complete_scan()
                scanner.show_scan_dashboard()
                ui.pause()
            elif choice_lower == "2":
                _bar("📊 DASHBOARD", _s("2"))
                dashboard.render(adb, dev, data)
                ui.pause()
            elif choice_lower == "3":
                _bar("📋 KATEGORIEN", _s("3"))
                _categories_overview(adb, dev, st)
            elif choice_lower == "4":
                _bar("🎨 UI THEME", _s("4"))
                settings_manager.show_settings(adb)
            elif choice_lower == "5":
                _bar("⚙️  EINSTELLUNGEN", _s("5"))
                settings_manager.show_settings(adb)
            elif choice_lower == "6":
                _bar("🎙️  MICROPHONE TAP", _s("6"))
                mic_tap = microphone_tap.create_microphone_tap(adb)
                mic_tap.show_microphone_menu()
            elif choice_lower == "7":
                _bar("📷 CAMERA TAP", _s("7"))
                cam_tap = camera_tap.create_camera_tap(adb)
                cam_tap.show_camera_menu()
            elif choice_lower == "8":
                _bar("🌐 NETWORK ANALYZER", _s("8"))
                net_analyzer = network_analyzer.create_network_analyzer(adb)
                net_analyzer.show_network_menu()
            elif choice_lower == "9":
                _bar("🔍 FORENSIK SUITE", _s("9"))
                forensics.menu(adb, st)
            elif choice_lower == "10":
                _bar("📦 APK SCANNER", _s("10"))
                apkscan.menu(adb, dev, st)
            elif choice_lower == "11":
                _bar("🗃️  APP SCANNER", _s("11"))
                appscan.menu(adb, dev, st, data)
            elif choice_lower == "12":
                _bar("📁 DATEI TREE", _s("12"))
                filetree.menu(adb, dev, st)
            elif choice_lower == "13":
                _bar("💾 DATEN FORENSIK", _s("13"))
                dataforensics.menu(adb, dev, st)
            elif choice_lower == "14":
                _bar("🎯 TIEFE ENGINE", _s("14"))
                _depth_engine(adb, dev, st)
            elif choice_lower == "15":
                _bar("🗂️  CASE DATABASE", _s("15"))
                casedb.menu(adb, dev, st, data)
            elif choice_lower == "16":
                _bar("📄 REPORT GENERATOR", _s("16"))
                report.menu(adb, dev, st, data)
            elif choice_lower == "17":
                _bar("🔄 MODE SWITCH", _s("17"))
                modeswitch.menu(adb, dev, st, data)
            elif choice_lower == "18":
                _bar("🔧 CUSTOM FIRMWARE", _s("18"))
                customfw.show_custom_firmware(adb, dev, st, data)
            elif choice_lower == "19":
                _bar("🌐 ROOTKIT SCANNER", _s("19"))
                rootkit.menu(adb, dev, st)
            elif choice_lower == "20":
                _bar("🚀 ROOTING TOOLS", _s("20"))
                rooting.show_and_offer(adb, dev, data, st)
                st["is_root"] = adb.check_root()
                data["root"] = st["is_root"]
            elif choice_lower == "21":
                _bar("📸 DATA ACQUISITION", _s("21"))
                acquire.menu(adb, dev, st, data)
            elif choice_lower == "22":
                _bar("🔓 APP DECRYPTION", _s("22"))
                app_decryption.menu(adb)
            elif choice_lower == "23":
                _bar("🔨 BRUTE FORCE", _s("23"))
                brute_force.menu(adb)
            elif choice_lower == "24":
                _bar("📡 WIFI HANDSHAKE", _s("24"))
                wifi_handshake.menu(adb)
            elif choice_lower == "25":
                _bar("🛡️  DNS GUARDIAN", _s("25"))
                dns_guardian.menu(adb)
            elif choice_lower == "26":
                _bar("🎯 TRACKER SYSTEM", _s("26"))
                tracker_system.menu(adb)
            elif choice_lower == "27":
                _bar("🧠 INTELLIGENT ENGINE", _s("27"))
                intelligent_engine.menu(adb)
            elif choice_lower == "28":
                _bar("💾 DATABASE SCANNER", _s("28"))
                database_scanner.menu(adb)
            elif choice_lower == "29":
                _bar("🧪 LAB MANAGER", _s("29"))
                lab_manager.menu(adb)
            elif choice_lower == "30":
                _bar("🌐 3D WIFI SCANNER", _s("30"))
                wifi_room_scanner_3d.menu(adb)
            elif choice_lower == "31":
                _bar("🔍 ADULT DETECTOR", _s("31"))
                adult_activity_detector.menu(adb)
            elif choice_lower == "32":
                _bar("🔴 ANOMALY DETECTOR", _s("32"))
                anomaly_detector.menu(adb)
            elif choice_lower == "33":
                _bar("🏥 AI DOCTOR", _s("33"))
                ai_doctor.menu(adb)
            elif choice_lower == "34":
                _bar("🔬 FORENSIC ANALYZER", _s("34"))
                forensic_audio_analyzer.menu(adb)
            elif choice_lower == "35":
                _bar("🔐 SECURITY FRAMEWORK", _s("35"))
                security_framework.menu(adb)
            elif choice_lower == "36":
                _bar("🔑 PASSWORD MANAGER", _s("36"))
                password_manager.menu(adb)
            elif choice_lower == "37":
                _bar("🎵 AUDIO PLAYBACK", _s("37"))
                audio_playback.menu(adb)
            elif choice_lower == "38":
                _bar("🐚 ADB SHELL", _s("38"))
                adb_shell.menu(adb)
            elif choice_lower == "39":
                _bar("🔓 AUTO ROOT ENGINE", _s("39"))
                auto_root_engine.menu(adb)
            elif choice_lower == "40":
                _bar("🎤 KEYWORD RECORDER", _s("40"))
                keyword_recorder.menu(adb)
            elif choice_lower == "41":
                _bar("🚑 AUTO-RESCUE", _s("41"))
                rescue.auto_rescue(dev)
            elif choice_lower == "42":
                _bar("📡 BOOTLOOP-MONITOR", _s("42"))
                bootloop.monitor()
            elif choice_lower == "43":
                _bar("🕵  OSINT-TOOLKIT", _s("43"))
                osint.menu(adb, dev, st)
            elif choice_lower == "44":
                _bar("🤖 KI-ADB-SHELL", _s("44"))
                aishell.menu(adb, dev, st)
            elif choice_lower == "45":
                _bar("📱 SAMSUNG TOOLS", _s("45"))
                samsung.menu(adb, dev, st, data)
            elif choice_lower == "46":
                _bar("🔶 MEDIATEK ROOT", _s("46"))
                mediatek.menu(adb, dev, st, data)
            elif choice_lower == "47":
                _bar("🏷  HERSTELLER-TOOLS", _s("47"))
                brands.menu(adb, dev, st, data)
            elif choice_lower == "48":
                _bar("📶 MOBILFUNK-MONITOR", _s("48"))
                handlers.cell_monitor(adb, dev, st)
            elif choice_lower == "49":
                _bar("🧪 LABOR-EINRICHTUNG", _s("49"))
                labsetup.menu(adb, dev, st)
            elif choice_lower == "50":
                _bar("🔬 DEEP-FORENSIK", _s("50"))
                deepforensics.menu(adb, dev, st)
            elif choice_lower == "51":
                _bar("📞 TELEFON-OSINT", _s("51"))
                phoneosint.menu(adb, dev, st)
            elif choice_lower == "52":
                _bar("🔑 GOOGLE-KONTEN", _s("52"))
                google_account_scanner.menu(adb)
            elif choice_lower == "53":
                _bar("📱 KONTO-SCANNER", _s("53"))
                account_scanner.menu(adb)
            elif choice_lower == "54":
                _bar("🔒 FRP-SCANNER", _s("54"))
                frp_scanner.menu(adb)
            elif choice_lower == "55":
                _bar("💳 SIM-TOOLKIT", _s("55"))
                sim_toolkit.menu(adb, dev, st)
            else:
                ui.warn("Ungültige Option!")
                time.sleep(0.5)

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


def run() -> int:
    # 🎨 MODERN STARTUP SCREEN + vollständiger 54-Modul-Scan
    _startup_failures = modern_startup.animate_startup()
    if _startup_failures:
        LOG.warning("Startup: %d Module fehlerhaft: %s",
                    len(_startup_failures),
                    [f"[{n}] {name}" for n, name, _ in _startup_failures])

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

        if not st["is_root"]:
            ui.info(lang.t("run_not_rooted"))
        ui.pause(lang.t("run_go_menu"))

        _main_menu(adb, dev, st, data)

        if not ui.confirm(lang.t("run_other_device"), False):
            ui.clear()
            ui.ok(f"{lang.t('run_goodbye')} 🛡")
            return 0


if __name__ == "__main__":
    sys.exit(run())
