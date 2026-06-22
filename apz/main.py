"""Hauptprogramm: Geräteerkennung → Auto-Analyse → Menüführung → Dispatch."""
from __future__ import annotations

import sys
import time

from . import (acquire, aishell, apkscan, appscan, bootloop, brands, casedb, customfw,
               dashboard, dataforensics, filetree, forensics, frida_engine,
               labsetup, lang, mediatek, messenger, modeswitch, registry, report, rescue,
               rooting, rootkit, rootprep, samsung, timeline, traffic, ui, usb)
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
    """Führt ein einzelnes Feature je nach 'kind' aus."""
    ui.clear()
    k = ft["k"]
    ui.rule(f"#{ft['n']} · {ft['t']}  {ui.badge(_badge_for(k))}", ui.CYAN)
    note = ft.get("note")
    if note and k not in ("info", "sdr", "danger"):
        ui.info(note)
        print()

    try:
        if k == "cmd":
            out = adb.shell(ft["p"], timeout=60)
            ui.pager(out or "(keine Ausgabe)", "")
            ui.pause()

        elif k == "rootcmd":
            if not st.get("is_root"):
                ui.warn(lang.t("feature_root_required"))
                ui.info(note or "")
                ui.info(lang.t("feature_root_hint"))
                if ui.confirm(lang.t("feature_try_no_root"), False):
                    ui.pager(adb.shell(ft["p"], timeout=60) or lang.t("ui_no_output"), "")
                ui.pause()
            else:
                ui.pager(adb.shell(ft["p"], timeout=60, root=True) or lang.t("ui_no_output"), "")
                ui.pause()

        elif k == "ask":
            prompt, template = ft["p"]
            val = ui.ask(prompt)
            if val == "" and "{v}" in template:
                ui.warn(lang.t("feature_aborted"))
            else:
                cmd = template.replace("{v}", val)
                ui.info(f"{lang.t('feature_executing')} {cmd}")
                ui.pager(adb.shell(cmd, timeout=60) or lang.t("feature_executed"), "")
            ui.pause()

        elif k == "fn":
            ft["p"](adb, dev, st)

        elif k in ("info",):
            ui.info(ft["p"])
            ui.pause()

        elif k == "sdr":
            ui.warn(lang.t("feature_sdr_required"))
            ui.info(ft["p"])
            ui.pause()

        elif k == "danger":
            ui.danger(lang.t("feature_destructive"))
            ui.info(ft["p"])
            ui.warn(lang.t("feature_destructive_note"))
            ui.pause()
        else:
            ui.err(f"Unbekannte Art: {k}")
            ui.pause()
    except AdbError as e:
        ui.err(f"{lang.t('feature_adb_error')} {e}")
        LOG.exception(f"ADB-Fehler in Feature #{ft.get('n')} {ft.get('t')}", e)
        ui.pause()
    except KeyboardInterrupt:
        ui.warn(f"\n{lang.t('feature_aborted_ctrl_c')}")
    except Exception as e:  # noqa: BLE001
        ui.err(f"{lang.t('feature_error')} {e}")
        LOG.exception(f"Feature #{ft.get('n')} {ft.get('t')}", e)
        ui.pause()


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
            ch = ui.menu(lang.t("menu_main_title"), entries,
                         back_label=lang.t("menu_back_choose_device"))
            if ch == "quit":
                return
            if ch == "back":
                return
            if ch == "d":
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
