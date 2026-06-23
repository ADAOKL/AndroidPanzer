"""MULTI-KONTO-SCANNER: Samsung, Microsoft, Social Media und alle weiteren Konten.

Dedizierte Scanner je Plattform:
  • Samsung Account  — dumpsys + App-DB (Root) + Knox/SmartSwitch
  • Microsoft/Exchange — ActiveSync, Outlook, Intune, Teams
  • Social Media     — WhatsApp, Telegram, Instagram, Facebook, Twitter/X, TikTok
  • Streaming        — Spotify, Netflix, YouTube
  • Sonstige         — alle unbekannten Account-Typen aus dumpsys account

Jeder Scanner:
  – kein Root: dumpsys account + App-spezifische Content-Provider
  – mit Root: SQLite-Zugriff auf App-Datenbanken
  – Export TXT/JSON
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from . import ui
from .adb import ADB


# ─── Account-Typen Karte ─────────────────────────────────────────────────────
# (account_type_prefix → (Anzeigename, Icon, Kategorie))
_TYPE_MAP: Dict[str, Tuple[str, str, str]] = {
    # Samsung
    "com.osp.app.signin":                          ("Samsung Account",        "🔵", "samsung"),
    "com.samsung.android.easysetup":               ("Samsung Easy Setup",     "🔵", "samsung"),
    "com.samsung.android.sm":                      ("Samsung Connected",      "🔵", "samsung"),
    "com.samsung.android.sdk.accounts":            ("Samsung SDK",            "🔵", "samsung"),
    "samsung.com":                                 ("Samsung",                "🔵", "samsung"),
    "com.samsung":                                 ("Samsung",                "🔵", "samsung"),
    # Microsoft
    "com.microsoft.exchangeactivesync":            ("Exchange / Outlook",     "🔷", "microsoft"),
    "com.microsoft.intune":                        ("Microsoft Intune",       "🔷", "microsoft"),
    "com.microsoft.teams":                         ("Microsoft Teams",        "🔷", "microsoft"),
    "com.microsoft":                               ("Microsoft",              "🔷", "microsoft"),
    "live.com":                                    ("Microsoft Live",         "🔷", "microsoft"),
    # WhatsApp
    "com.whatsapp":                                ("WhatsApp",               "🟢", "social"),
    "com.whatsapp.w4b":                            ("WhatsApp Business",      "🟢", "social"),
    # Telegram
    "org.telegram.messenger":                      ("Telegram",               "🔹", "social"),
    "org.telegram":                                ("Telegram",               "🔹", "social"),
    # Meta
    "com.facebook.auth.login":                     ("Facebook",               "🔵", "social"),
    "com.facebook":                                ("Facebook",               "🔵", "social"),
    "com.instagram.auth":                          ("Instagram",              "🟣", "social"),
    "com.instagram":                               ("Instagram",              "🟣", "social"),
    "com.threads":                                 ("Threads",                "🟣", "social"),
    # Twitter/X
    "com.twitter.android.auth":                    ("Twitter / X",            "⚫", "social"),
    "com.twitter":                                 ("Twitter / X",            "⚫", "social"),
    # TikTok
    "com.zhiliaoapp.musically":                    ("TikTok",                 "⬛", "social"),
    "com.ss.android.ugc.trill":                    ("TikTok",                 "⬛", "social"),
    # Snapchat
    "com.snapchat.android":                        ("Snapchat",               "🟡", "social"),
    # LinkedIn
    "com.linkedin.android":                        ("LinkedIn",               "🔷", "social"),
    # Streaming
    "com.spotify.mobile":                          ("Spotify",                "🟢", "streaming"),
    "com.spotify":                                 ("Spotify",                "🟢", "streaming"),
    "com.netflix.mediaclient":                     ("Netflix",                "🔴", "streaming"),
    "com.netflix":                                 ("Netflix",                "🔴", "streaming"),
    "com.amazon.avod":                             ("Amazon Prime Video",     "🟠", "streaming"),
    "com.amazon":                                  ("Amazon",                 "🟠", "streaming"),
    # PayPal / Finanzen
    "com.paypal.android.p2pmobile":                ("PayPal",                 "🔵", "finance"),
    "com.paypal":                                  ("PayPal",                 "🔵", "finance"),
    "de.number26.android":                         ("N26",                    "🟢", "finance"),
    # VPN
    "com.nordvpn.android":                         ("NordVPN",                "🔵", "vpn"),
    "com.expressvpn":                              ("ExpressVPN",             "🔴", "vpn"),
}

_CATEGORIES = {
    "samsung":   ("SAMSUNG-KONTEN",     ui.BCYAN),
    "microsoft": ("MICROSOFT-KONTEN",   ""),
    "social":    ("SOCIAL MEDIA",       ui.BCYAN),
    "streaming": ("STREAMING-DIENSTE",  ui.BCYAN),
    "finance":   ("FINANZEN",           ui.BYELLOW),
    "vpn":       ("VPN-DIENSTE",        ui.BCYAN),
    "other":     ("SONSTIGE KONTEN",    ui.GREY),
}


@dataclass
class Account:
    name: str           # E-Mail / Benutzername
    account_type: str   # raw Android account type
    display_type: str   # lesbar
    icon: str
    category: str
    extra: Dict[str, str] = field(default_factory=dict)
    deleted: bool = False


class AccountScanner:
    """Scannt alle Nicht-Google-Konten auf dem Gerät."""

    def __init__(self, adb: ADB):
        self.adb = adb
        self.accounts: List[Account] = []
        self.has_root = False

    # ─── Hauptmenü ────────────────────────────────────────────────────────
    def show_menu(self) -> None:
        while True:
            ui.clear()
            ui.banner(subtitle="📱 MULTI-KONTO-SCANNER")
            print()
            entries = [
                ("1", "🔍  Alle Konten scannen (kein Root nötig)"),
                ("2", "🔐  Tiefen-Scan inkl. App-Datenbanken (Root)"),
                ("3", "🔵  Samsung-Konten Detail-Scan"),
                ("4", "🔷  Microsoft / Exchange Detail-Scan"),
                ("5", "💬  Social-Media Detail-Scan"),
                ("6", "📋  Letzten Scan anzeigen"),
                ("7", "💾  Export als TXT / JSON"),
            ]
            ch = ui.menu("Konto-Scanner", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return
            if ch == "1":
                self._run_scan(root=False, filter_cat=None)
            elif ch == "2":
                self._run_scan(root=True, filter_cat=None)
            elif ch == "3":
                self._run_scan(root=self.adb.check_root(), filter_cat="samsung")
                self._samsung_deep()
            elif ch == "4":
                self._run_scan(root=self.adb.check_root(), filter_cat="microsoft")
                self._microsoft_deep()
            elif ch == "5":
                self._run_scan(root=self.adb.check_root(), filter_cat="social")
                self._social_deep()
            elif ch == "6":
                if self.accounts:
                    self._display_results()
                else:
                    ui.warn("Noch kein Scan durchgeführt.")
                    ui.pause()
            elif ch == "7":
                self._export_menu()

    # ─── Haupt-Scan ───────────────────────────────────────────────────────
    def _run_scan(self, root: bool, filter_cat: Optional[str]) -> None:
        ui.clear()
        title = f"🔍 SCAN: {filter_cat.upper() if filter_cat else 'ALLE KONTEN'}"
        ui.rule(title, ui.BCYAN)
        print()

        self.has_root = root and self.adb.check_root()
        self.accounts = []

        ui.info("Lese dumpsys account …")
        self._parse_dumpsys(filter_cat=filter_cat)

        if self.has_root:
            ui.info("Lese accounts_ce.db (Root) …")
            self._parse_accounts_db(filter_cat=filter_cat)

        print()
        self._display_results(filter_cat=filter_cat)

    # ─── dumpsys Parser ───────────────────────────────────────────────────
    def _parse_dumpsys(self, filter_cat: Optional[str] = None) -> None:
        raw = self.adb.shell("dumpsys account 2>/dev/null", timeout=30)
        if not raw:
            return

        blocks = re.split(r"(?=Account\s*\{)", raw)
        seen = set()

        for block in blocks:
            m = re.search(r"name=([^,}\s]+)", block)
            t = re.search(r"type=([^,}\s]+)", block)
            if not m or not t:
                continue
            name = m.group(1).strip()
            atype = t.group(1).strip()

            # Google-Konten überspringen (werden von google_account_scanner behandelt)
            if atype == "com.google":
                continue

            key = f"{name}|{atype}"
            if key in seen:
                continue
            seen.add(key)

            display, icon, cat = _resolve_type(atype)

            if filter_cat and cat != filter_cat:
                continue

            acc = Account(
                name=name, account_type=atype,
                display_type=display, icon=icon, category=cat,
            )
            self.accounts.append(acc)

    # ─── Root DB ──────────────────────────────────────────────────────────
    def _parse_accounts_db(self, filter_cat: Optional[str] = None) -> None:
        dbs = [
            "/data/system_ce/0/accounts_ce.db",
            "/data/system_de/0/accounts_de.db",
            "/data/system/accounts.db",
        ]
        seen = {f"{a.name}|{a.account_type}" for a in self.accounts}

        for db_path in dbs:
            exists = self.adb.shell(f"[ -f '{db_path}' ] && echo yes 2>/dev/null", root=True)
            if "yes" not in exists:
                continue

            rows = self.adb.shell(
                f"sqlite3 '{db_path}' 'SELECT name,type FROM accounts' 2>/dev/null",
                root=True, timeout=20,
            )
            for line in rows.splitlines():
                parts = line.strip().split("|")
                if len(parts) < 2:
                    continue
                name, atype = parts[0].strip(), parts[1].strip()
                if atype == "com.google":
                    continue
                key = f"{name}|{atype}"
                if key in seen:
                    continue
                seen.add(key)

                display, icon, cat = _resolve_type(atype)
                if filter_cat and cat != filter_cat:
                    continue

                self.accounts.append(Account(
                    name=name, account_type=atype,
                    display_type=display, icon=icon, category=cat,
                ))
            break

    # ─── Samsung Deep-Scan ───────────────────────────────────────────────
    def _samsung_deep(self) -> None:
        ui.clear()
        ui.rule("🔵 SAMSUNG-KONTO DETAIL-SCAN", ui.BCYAN)
        print()

        # 1. Samsung Account App-Info
        ui.info("Samsung Account App prüfen …")
        pkg_info = self.adb.shell(
            "dumpsys package com.osp.app.signin 2>/dev/null | grep -E 'versionName|firstInstallTime|lastUpdateTime'",
            timeout=15
        )
        if pkg_info.strip():
            ui.kv("Samsung Account App", "")
            for line in pkg_info.strip().splitlines():
                print(f"    {line.strip()}")
            print()

        # 2. Samsung Account E-Mail aus Settings
        ui.info("Samsung E-Mail aus Settings …")
        for key in ["samsung_account_name", "sec_samsung_account"]:
            val = self.adb.shell(f"settings get secure {key} 2>/dev/null", timeout=8)
            if val.strip() and "null" not in val.lower():
                ui.kv(f"  {key}", val.strip())

        # 3. Knox-Status
        ui.info("Knox-Status prüfen …")
        knox = self.adb.shell(
            "pm list packages | grep -i knox && dumpsys package com.samsung.android.knox.containeragent 2>/dev/null | grep versionName",
            timeout=15
        )
        if knox.strip():
            ui.kv("Knox", knox.strip()[:80])
        else:
            ui.kv("Knox", "nicht installiert")

        # 4. SmartSwitch
        smart = self.adb.shell(
            "pm list packages | grep -i smartswitch", timeout=10
        )
        if smart.strip():
            ui.kv("SmartSwitch", "installiert")

        # 5. Root: Samsung Account DB
        if self.has_root:
            print()
            ui.rule("Root: Samsung Account Datenbank", ui.CYAN)
            sa_dbs = [
                "/data/data/com.osp.app.signin/databases/",
                "/data/data/com.samsung.android.samsungaccount/databases/",
            ]
            for db_dir in sa_dbs:
                dbs = self.adb.shell(f"ls '{db_dir}' 2>/dev/null", root=True)
                for db_name in dbs.splitlines():
                    db_name = db_name.strip()
                    if not db_name.endswith(".db"):
                        continue
                    full = f"{db_dir}{db_name}"
                    rows = self.adb.shell(
                        f"sqlite3 '{full}' \".tables\" 2>/dev/null", root=True, timeout=10
                    )
                    if rows.strip():
                        ui.kv(f"  {db_name}", rows.strip()[:80])

        print()
        ui.pause()

    # ─── Microsoft Deep-Scan ─────────────────────────────────────────────
    def _microsoft_deep(self) -> None:
        ui.clear()
        ui.rule("🔷 MICROSOFT / EXCHANGE DETAIL-SCAN", ui.BCYAN)
        print()

        # Exchange ActiveSync
        ui.info("Exchange-Konten aus ActiveSync …")
        ea = self.adb.shell(
            "content query --uri content://com.android.email.provider/account 2>/dev/null",
            timeout=15
        )
        if ea.strip():
            for line in ea.strip().splitlines()[:20]:
                if any(k in line for k in ["emailAddress", "displayName", "hostAuthRecv"]):
                    print(f"  {line.strip()}")
            print()
        else:
            ui.info("Kein Exchange-Content-Provider gefunden.")

        # Outlook App
        ui.info("Microsoft Outlook App …")
        outlook_pkg = "com.microsoft.office.outlook"
        outlook_info = self.adb.shell(
            f"pm list packages | grep -i '{outlook_pkg}'", timeout=10
        )
        if outlook_info.strip():
            ui.ok("Outlook ist installiert.")
            if self.has_root:
                rows = self.adb.shell(
                    f"ls /data/data/{outlook_pkg}/databases/ 2>/dev/null",
                    root=True, timeout=10
                )
                if rows.strip():
                    ui.kv("  Datenbanken", rows.strip()[:120])
        else:
            ui.info("Outlook nicht installiert.")

        # Teams
        ui.info("Microsoft Teams …")
        teams = self.adb.shell("pm list packages | grep -i teams", timeout=10)
        if teams.strip():
            ui.ok(f"Teams installiert: {teams.strip()}")
        else:
            ui.info("Teams nicht installiert.")

        print()
        ui.pause()

    # ─── Social Media Deep-Scan ──────────────────────────────────────────
    def _social_deep(self) -> None:
        ui.clear()
        ui.rule("💬 SOCIAL-MEDIA DETAIL-SCAN", ui.BCYAN)
        print()

        checks = [
            ("WhatsApp",    "com.whatsapp",              "/data/data/com.whatsapp/databases/msgstore.db"),
            ("WA Business", "com.whatsapp.w4b",          "/data/data/com.whatsapp.w4b/databases/msgstore.db"),
            ("Telegram",    "org.telegram.messenger",    "/data/data/org.telegram.messenger/files/cache4.db"),
            ("Instagram",   "com.instagram.android",     "/data/data/com.instagram.android/databases/"),
            ("Facebook",    "com.facebook.katana",       "/data/data/com.facebook.katana/databases/"),
            ("Twitter/X",   "com.twitter.android",       "/data/data/com.twitter.android/databases/"),
            ("TikTok",      "com.zhiliaoapp.musically",  "/data/data/com.zhiliaoapp.musically/databases/"),
            ("Snapchat",    "com.snapchat.android",      "/data/data/com.snapchat.android/databases/"),
            ("LinkedIn",    "com.linkedin.android",      "/data/data/com.linkedin.android/databases/"),
        ]

        for label, pkg, db_path in checks:
            installed = self.adb.shell(f"pm list packages | grep -x 'package:{pkg}' 2>/dev/null", timeout=8)
            if not installed.strip():
                print(f"  {ui.GREY}✗  {label:<16} nicht installiert{ui.RESET}")
                continue

            # Version
            ver = self.adb.shell(
                f"dumpsys package {pkg} 2>/dev/null | grep versionName | head -1", timeout=10
            )
            ver_str = ver.strip().split("=")[-1] if "=" in ver else ""

            # Login-Konto aus unserer Scan-Liste
            accs = [a for a in self.accounts if a.account_type.startswith(pkg[:15])]
            acc_str = accs[0].name if accs else "—"

            # DB vorhanden (nur mit Root)
            db_ok = ""
            if self.has_root:
                db_exists = self.adb.shell(
                    f"[ -e '{db_path}' ] && echo yes 2>/dev/null", root=True, timeout=8
                )
                db_ok = f"  {ui.BGREEN}[DB ✓]{ui.RESET}" if "yes" in db_exists else ""

            print(f"  {ui.BGREEN}●{ui.RESET}  {label:<16}  v{ver_str:<12}  Konto: {ui.BOLD}{acc_str}{ui.RESET}{db_ok}")

        print()
        ui.pause()

    # ─── Anzeige ─────────────────────────────────────────────────────────
    def _display_results(self, filter_cat: Optional[str] = None) -> None:
        ui.clear()
        ui.banner(subtitle="📋 KONTO-SCANNER ERGEBNISSE")
        print()

        if not self.accounts:
            ui.warn("Keine Konten gefunden.")
            ui.pause()
            return

        # Nach Kategorie gruppieren
        cat_groups: Dict[str, List[Account]] = {}
        for acc in self.accounts:
            cat_groups.setdefault(acc.category, []).append(acc)

        # Definierte Kategorien zuerst, dann "other"
        order = ["samsung", "microsoft", "social", "streaming", "finance", "vpn", "other"]

        for cat in order:
            if cat not in cat_groups:
                continue
            if filter_cat and cat != filter_cat:
                continue
            label, color = _CATEGORIES[cat]
            accs = cat_groups[cat]
            ui.rule(f"{label} ({len(accs)})", color or ui.CYAN)
            print()
            for acc in accs:
                deleted_badge = f"  {ui.GREY}[gelöscht]{ui.RESET}" if acc.deleted else ""
                print(f"  {acc.icon}  {ui.BOLD}{acc.name}{ui.RESET}{deleted_badge}")
                print(f"     {ui.GREY}Typ: {acc.display_type}  ({acc.account_type}){ui.RESET}")
                if acc.extra:
                    for k, v in acc.extra.items():
                        print(f"     {k}: {v}")
            print()

        # Statistik
        ui.rule("📊 ZUSAMMENFASSUNG", ui.BCYAN)
        print()
        total = len(self.accounts)
        ui.kv("Konten gesamt", str(total))
        for cat in order:
            if cat in cat_groups:
                label, _ = _CATEGORIES[cat]
                ui.kv(f"  {label}", str(len(cat_groups[cat])))
        print()
        ui.pause()

    # ─── Export ──────────────────────────────────────────────────────────
    def _export_menu(self) -> None:
        if not self.accounts:
            ui.warn("Zuerst Scan durchführen (Option 1 oder 2).")
            ui.pause()
            return

        outdir = os.path.expanduser("~/panzer_exports/account_scanner")
        os.makedirs(outdir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        txt_path = os.path.join(outdir, f"accounts_{ts}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("AndroidPanzer – Multi-Konto-Scanner\n")
            f.write(f"Erstellt: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            for acc in self.accounts:
                f.write(f"[{acc.category.upper()}] {acc.icon} {acc.name}\n")
                f.write(f"  Typ: {acc.display_type} ({acc.account_type})\n")
                if acc.deleted:
                    f.write("  STATUS: GELÖSCHT\n")
                f.write("\n")
        ui.ok(f"TXT: {txt_path}")

        json_path = os.path.join(outdir, f"accounts_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {"scan_time": datetime.now().isoformat(),
                 "accounts": [asdict(a) for a in self.accounts]},
                f, indent=2, ensure_ascii=False,
            )
        ui.ok(f"JSON: {json_path}")
        print()
        ui.pause()


# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def _resolve_type(atype: str) -> Tuple[str, str, str]:
    """Gibt (Anzeigename, Icon, Kategorie) für einen account-type zurück."""
    # Exakt
    if atype in _TYPE_MAP:
        return _TYPE_MAP[atype]
    # Prefix-Match (längsten zuerst)
    for prefix in sorted(_TYPE_MAP.keys(), key=len, reverse=True):
        if atype.startswith(prefix):
            return _TYPE_MAP[prefix]
    # Unbekannt
    short = atype.split(".")[-1] if "." in atype else atype
    return (short, "⚪", "other")


# ─── Modul-Einstieg ──────────────────────────────────────────────────────────

def menu(adb=None) -> None:
    if adb is None:
        ui.warn("Kein ADB-Gerät verbunden.")
        ui.pause()
        return
    scanner = AccountScanner(adb)
    scanner.show_menu()
