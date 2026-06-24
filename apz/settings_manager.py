"""EINSTELLUNGEN-MANAGER: Zentrales Konfigurations-Hub mit Passwort-Verwaltung.

Speichert persistent in ~/.config/android-panzer/settings.json.
Integriert den PasswordManager als Untermenü.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict

from . import ui
from .password_manager import ModuleType, PasswordManager, PasswordValidator


# ─────────────────────────────────────────────────────────────
# Persistenz
# ─────────────────────────────────────────────────────────────
_CONFIG_PATH = os.path.expanduser("~/.config/android-panzer/settings.json")
_LOG_PATH    = os.path.expanduser("~/.config/android-panzer/session.log")

_DEFAULTS: Dict[str, Any] = {
    "theme":         "dark",
    "language":      "deutsch",
    "verbose":       False,
    "audio_quality": 44100,
    "video_quality": "1080p",
    "timeout":       30,
    "debug_mode":    False,
    "ollama_url":    "http://localhost:11434",
    "adb_host":      "localhost",
    "adb_port":      5037,
    "output_base":   "~/Schreibtisch/Androidpanzer",
    "log_level":     "INFO",
}


def _load() -> Dict[str, Any]:
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # merge: fill missing keys with defaults
            return {**_DEFAULTS, **{k: data[k] for k in _DEFAULTS if k in data}}
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save(cfg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.chmod(_CONFIG_PATH, 0o600)


# ─────────────────────────────────────────────────────────────
# Passwort-Menü
# ─────────────────────────────────────────────────────────────

# Welche Module im Einstellungs-Menü angezeigt werden
_PW_MODULES = [
    (ModuleType.CAMERA_TAP,        "📷",  "Camera TAP"),
    (ModuleType.MICROPHONE_TAP,    "🎙️ ", "Microphone TAP"),
    (ModuleType.FORENSIC_ANALYZER, "🔬",  "Forensic Analyzer"),
    (ModuleType.SECURITY_FRAMEWORK,"🛡️ ", "Security Framework"),
    (ModuleType.DATABASE_SCANNER,  "💾",  "Database Scanner"),
    (ModuleType.BRUTE_FORCE,       "🔨",  "Brute Force"),
]


def _status_badge(pm: PasswordManager, mod: ModuleType) -> str:
    st = pm.get_module_password_status(mod)
    if st["set"]:
        return f"{ui.BGREEN}● GESETZT ({st['strength']}){ui.RESET}"
    return f"{ui.GREY}○ NICHT GESETZT{ui.RESET}"


def _set_module_pw(pm: PasswordManager, mod: ModuleType, label: str) -> None:
    ui.clear()
    ui.rule(f"🔐 {label.upper()} – PASSWORT SETZEN", ui.BCYAN)
    print()
    st = pm.get_module_password_status(mod)

    if st["set"]:
        ui.info(f"Aktuell: {st['strength']}")
        old = ui.ask("Altes Passwort (oder leer lassen zum Abbrechen)")
        if not old:
            ui.warn("Abgebrochen.")
            return
        if not pm.verify_module_password(mod, old):
            ui.err("Falsches Passwort!")
            ui.pause()
            return

    _show_pw_rules()
    new_pw = ui.ask("Neues Passwort")
    if not new_pw:
        ui.warn("Leer – abgebrochen.")
        return
    confirm = ui.ask("Passwort bestätigen")
    if new_pw != confirm:
        ui.err("Passwörter stimmen nicht überein!")
        ui.pause()
        return

    strength, issues = PasswordValidator.validate_strength(new_pw)
    if issues:
        print(f"\n  {ui.BYELLOW}Hinweise:{ui.RESET}")
        for issue in issues:
            print(f"    • {issue}")
        print()

    success, msg = pm.set_module_password(mod, new_pw)
    if success:
        ui.ok(f"✓ {msg}")
    else:
        ui.err(f"✗ {msg}")
    ui.pause()


def _delete_module_pw(pm: PasswordManager, mod: ModuleType, label: str) -> None:
    ui.clear()
    ui.rule(f"🗑  {label.upper()} – PASSWORT ENTFERNEN", ui.BRED)
    print()
    st = pm.get_module_password_status(mod)
    if not st["set"]:
        ui.info("Kein Passwort gesetzt.")
        ui.pause()
        return
    old = ui.ask("Aktuelles Passwort zur Bestätigung")
    if not pm.verify_module_password(mod, old):
        ui.err("Falsches Passwort!")
        ui.pause()
        return
    pm.passwords.pop(mod, None)
    pm._save_passwords()
    ui.ok(f"✓ Passwort für {label} entfernt.")
    ui.pause()


def _show_pw_rules() -> None:
    print(f"  {ui.GREY}Anforderungen: min. 12 Zeichen, Groß+Klein+Zahl+Sonderzeichen{ui.RESET}\n")


def _password_overview(pm: PasswordManager) -> None:
    ui.clear()
    ui.banner(subtitle="🔐 MODUL-PASSWÖRTER – ÜBERSICHT")
    print()
    ui.rule("Passwort-Status aller geschützten Module", ui.CYAN)
    print()

    max_w = max(len(lbl) for _, _, lbl in _PW_MODULES)
    for mod, icon, label in _PW_MODULES:
        badge = _status_badge(pm, mod)
        print(f"  {icon}  {label:<{max_w}}  {badge}")

    print()
    print(f"  {ui.GREY}Master-Passwort: ", end="")
    if pm.master_password_set:
        print(f"{ui.BGREEN}● GESETZT{ui.RESET}")
    else:
        print(f"{ui.GREY}○ NICHT GESETZT{ui.RESET}")
    print()
    ui.pause()


def _master_password_menu(pm: PasswordManager) -> None:
    ui.clear()
    ui.rule("🔑 MASTER-PASSWORT", ui.BCYAN)
    print()
    if pm.master_password_set:
        ui.info("Master-Passwort ist gesetzt.")
        old = ui.ask("Aktuelles Passwort")
        if not pm.verify_master_password(old):
            ui.err("Falsches Passwort!")
            ui.pause()
            return
    _show_pw_rules()
    new_pw = ui.ask("Neues Master-Passwort")
    if not new_pw:
        ui.warn("Abgebrochen.")
        return
    confirm = ui.ask("Bestätigen")
    if new_pw != confirm:
        ui.err("Passwörter stimmen nicht überein!")
        ui.pause()
        return
    success, msg = pm.set_master_password(new_pw)
    if success:
        ui.ok(f"✓ {msg}")
    else:
        ui.err(f"✗ {msg}")
    ui.pause()


def _passwords_menu(pm: PasswordManager) -> None:
    """Untermenü: Modul-Passwörter verwalten."""
    while True:
        ui.clear()
        ui.banner(subtitle="🔐 PASSWORT-EINSTELLUNGEN")
        print()

        entries = [("0", f"{ui.BOLD}📊 Status aller Passwörter{ui.RESET}")]
        entries.append(("M", "🔑 Master-Passwort"))
        for i, (mod, icon, label) in enumerate(_PW_MODULES, 1):
            badge = _status_badge(pm, mod)
            entries.append((str(i), f"{icon} {label:<24} {badge}"))

        ch = ui.menu("Passwort-Verwaltung", entries, back_label="Einstellungen")
        if ch in ("back", "quit"):
            return

        if ch == "0":
            _password_overview(pm)
        elif ch == "m":
            _master_password_menu(pm)
        else:
            try:
                idx = int(ch) - 1
                if 0 <= idx < len(_PW_MODULES):
                    mod, icon, label = _PW_MODULES[idx]
                    _module_pw_action(pm, mod, label)
            except ValueError:
                ui.warn("Ungültige Eingabe.")


def _module_pw_action(pm: PasswordManager, mod: ModuleType, label: str) -> None:
    """Setzen / Ändern / Entfernen für ein Modul."""
    st = pm.get_module_password_status(mod)
    action_entries = [("1", "🔐 Passwort setzen / ändern")]
    if st["set"]:
        action_entries.append(("2", "🗑  Passwort entfernen"))

    ch = ui.menu(f"{label} – Aktion", action_entries, back_label="Zurück")
    if ch in ("back", "quit"):
        return
    if ch == "1":
        _set_module_pw(pm, mod, label)
    elif ch == "2":
        _delete_module_pw(pm, mod, label)


# ─────────────────────────────────────────────────────────────
# System-Einstellungen
# ─────────────────────────────────────────────────────────────

_SYSTEM_FIELDS = [
    ("theme",         "UI Theme",         "choice",  ["dark", "light", "custom"]),
    ("language",      "Sprache",          "choice",  ["deutsch", "english"]),
    ("verbose",       "Verbose Output",   "bool",    None),
    ("audio_quality", "Audio-Qualität",   "choice",  [16000, 44100, 48000]),
    ("video_quality", "Video-Qualität",   "choice",  ["480p", "720p", "1080p", "4k"]),
    ("timeout",       "ADB Timeout (s)",  "int",     None),
    ("debug_mode",    "Debug-Modus",      "bool",    None),
    ("log_level",     "Log-Level",        "choice",  ["DEBUG", "INFO", "WARNING", "ERROR"]),
]

_NETWORK_FIELDS = [
    ("ollama_url",    "Ollama API URL",   "str",     None),
    ("adb_host",      "ADB Host",         "str",     None),
    ("adb_port",      "ADB Port",         "int",     None),
]


def _system_settings_menu(cfg: Dict[str, Any]) -> Dict[str, Any]:
    while True:
        ui.clear()
        ui.banner(subtitle="⚙️  SYSTEM-EINSTELLUNGEN")
        print()

        entries = []
        for i, (key, label, kind, choices) in enumerate(_SYSTEM_FIELDS, 1):
            val = cfg.get(key, _DEFAULTS[key])
            val_str = str(val)
            if choices:
                val_str += f"  {ui.GREY}({' / '.join(str(c) for c in choices)}){ui.RESET}"
            entries.append((str(i), f"{label:<22}  {ui.BOLD}{val_str}{ui.RESET}"))

        ch = ui.menu("Einstellung wählen", entries, back_label="Einstellungen")
        if ch in ("back", "quit"):
            return cfg

        try:
            idx = int(ch) - 1
            if 0 <= idx < len(_SYSTEM_FIELDS):
                key, label, kind, choices = _SYSTEM_FIELDS[idx]
                cfg = _edit_field(cfg, key, label, kind, choices)
                _save(cfg)
                ui.ok(f"✓ {label} gespeichert.")
        except ValueError:
            pass


def _edit_field(cfg: Dict[str, Any], key: str, label: str, kind: str, choices) -> Dict[str, Any]:
    current = cfg.get(key, _DEFAULTS[key])
    print()
    ui.rule(f"✏️  {label}", ui.CYAN)
    print(f"  Aktuell: {ui.BOLD}{current}{ui.RESET}")

    if kind == "bool":
        val = ui.confirm(f"{label} aktivieren?", bool(current))
        cfg[key] = val
    elif kind == "choice" and choices:
        print()
        for i, c in enumerate(choices, 1):
            mark = f"{ui.BGREEN}●{ui.RESET}" if c == current else f"{ui.GREY}○{ui.RESET}"
            print(f"  {mark} {i}) {c}")
        raw = ui.ask("Nummer", "1")
        try:
            cfg[key] = choices[int(raw) - 1]
        except (ValueError, IndexError):
            ui.warn("Ungültig – unverändert.")
    elif kind == "int":
        raw = ui.ask(f"{label} (Zahl)", str(current))
        try:
            cfg[key] = int(raw)
        except ValueError:
            ui.warn("Keine gültige Zahl – unverändert.")
    else:
        raw = ui.ask(f"{label}", str(current))
        if raw:
            cfg[key] = raw

    return cfg


# ─────────────────────────────────────────────────────────────
# Theme-Auswahl (Option 4)
# ─────────────────────────────────────────────────────────────

_THEMES = ["dark", "light", "custom"]
_THEME_DESC = {
    "dark":   "Dunkles Terminal  (Standard – Cyan/Grün auf Schwarz)",
    "light":  "Helles Terminal   (Dunkel auf Weiß)",
    "custom": "Custom            (Farben manuell konfigurierbar)",
}

def show_theme(adb=None) -> None:
    """Direkter Theme-Wähler für Menüpunkt 4."""
    cfg = _load()
    while True:
        ui.clear()
        ui.banner(subtitle="🎨 UI THEME")
        print()
        ui.rule("THEME AUSWÄHLEN", ui.CYAN)
        print()
        current = cfg.get("theme", "dark")
        for i, t in enumerate(_THEMES, 1):
            mark = f"{ui.BGREEN}●{ui.RESET}" if t == current else f"{ui.GREY}○{ui.RESET}"
            print(f"  {mark} {i})  {ui.BOLD}{t:<8}{ui.RESET}  {ui.GREY}{_THEME_DESC[t]}{ui.RESET}")
        print()
        ui.rule(color=ui.CYAN)
        print(f"  {ui.GREY}  0  Zurück    q  Beenden{ui.RESET}")
        print()
        raw = input(f"  {ui.BOLD}☠ ❯ Theme (1-{len(_THEMES)}, 0): {ui.RESET}").strip().lower()
        if raw in ("0", "back", "q", "quit"):
            return
        try:
            cfg["theme"] = _THEMES[int(raw) - 1]
            _save(cfg)
            ui.ok(f"Theme auf '{cfg['theme']}' gesetzt.")
        except (ValueError, IndexError):
            ui.warn("Ungültige Auswahl.")


# ─────────────────────────────────────────────────────────────
# Haupt-Einstellungs-Menü
# ─────────────────────────────────────────────────────────────

def show_settings(adb=None) -> None:
    """Haupt-Einstellungen-Hub: System + Passwörter."""
    cfg = _load()
    pm = PasswordManager()

    while True:
        ui.clear()
        ui.banner(subtitle="⚙️  EINSTELLUNGEN")
        print()

        # Passwort-Zusammenfassung als Status-Zeile
        set_count = sum(
            1 for mod, _, _ in _PW_MODULES
            if pm.get_module_password_status(mod)["set"]
        )
        total = len(_PW_MODULES)
        pw_info = (f"{ui.BGREEN}{set_count}/{total} gesetzt{ui.RESET}"
                   if set_count > 0
                   else f"{ui.GREY}keine gesetzt{ui.RESET}")

        theme_val = cfg.get("theme", "dark")
        lang_val = cfg.get("language", "deutsch")

        ui.kv("🎨 Theme",         theme_val)
        ui.kv("🌐 Sprache",       lang_val)
        ui.kv("🔐 Modul-Passwörter", pw_info)
        print()

        entries = [
            ("1", "🔐  Modul-Passwörter verwalten"),
            ("2", "⚙️   System-Einstellungen"),
        ]

        ch = ui.menu("EINSTELLUNGEN", entries, back_label="Hauptmenü")
        if ch in ("back", "quit"):
            return

        if ch == "1":
            _passwords_menu(pm)
        elif ch == "2":
            cfg = _system_settings_menu(cfg)


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def get(key: str) -> Any:
    """Lese eine gespeicherte Einstellung."""
    return _load().get(key, _DEFAULTS.get(key))


def menu(adb=None) -> None:
    show_settings(adb)
