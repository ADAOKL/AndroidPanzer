"""GOOGLE-KONTO-SCANNER: Alle angemeldeten Google-Konten auflisten.

Erkennt:
  • Aktive Google-Konten (com.google) via dumpsys account (kein Root nötig)
  • Alle anderen Account-Typen (Samsung, Microsoft, WhatsApp, ...)
  • Sync-Status je Konto (Gmail, Kontakte, Kalender, Drive, Fotos)
  • FRP-Schutz-Konto (Factory Reset Protection)
  • Mit Root: gelöschte/abgemeldete Konten aus accounts_ce.db
  • Export als TXT/JSON
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict

from . import ui
from .adb import ADB


# ─── Sync-Adapter-Namen verschönern ────────────────────────────────────────
_SYNC_LABELS: Dict[str, str] = {
    "com.google.android.gm":              "Gmail",
    "com.google.android.calendar":        "Kalender",
    "com.google.android.contacts":        "Kontakte",
    "com.google.android.apps.photos":     "Google Fotos",
    "com.google.android.apps.drive":      "Drive",
    "com.google.android.youtube":         "YouTube",
    "com.google.android.gms.people":      "Google People/Kontakte",
    "com.google.android.talk":            "Google Chat",
    "com.google.android.keep":            "Keep Notes",
    "com.google.android.location":        "Standort-History",
    "com.google.android.apps.fitness":    "Google Fit",
    "com.google.android.apps.maps":       "Maps",
    "com.android.contacts":               "Gerätekontakte",
    "com.android.calendar":               "Gerätkalender",
    "com.samsung.android.contacts.sync":  "Samsung Kontakte",
}


@dataclass
class SyncAdapter:
    authority: str
    label: str
    enabled: bool
    last_sync: str = ""


@dataclass
class GoogleAccount:
    email: str
    account_type: str
    is_google: bool
    sync_adapters: List[SyncAdapter] = field(default_factory=list)
    is_frp_account: bool = False
    deleted: bool = False
    added_time: str = ""          # Zeitstempel Erstanmeldung (Root: DB)
    last_auth_time: str = ""      # Letzter Auth-Token-Zeitstempel
    last_sync_time: str = ""      # Letzter erfolgreicher Sync
    login_count: int = 0          # Anzahl erkannter Auth-Ereignisse
    token_count: int = 0          # Anzahl aktiver Auth-Tokens
    auth_failures: int = 0        # Anzahl fehlgeschlagener Auth-Versuche
    google_id: str = ""           # Google-Account-ID (falls abrufbar)
    gaia_id: str = ""             # GAIA-ID aus GMS (Root)
    services: List[str] = field(default_factory=list)  # aktive Google-Dienste
    raw_block: str = ""


class GoogleAccountScanner:
    """Scannt alle auf dem Gerät angemeldeten Konten."""

    def __init__(self, adb: ADB):
        self.adb = adb
        self.accounts: List[GoogleAccount] = []
        self.has_root = False
        self.frp_email: str = ""
        self.scan_time: str = ""
        self.device_info: Dict[str, str] = {}

    # ─── Gerätedaten sammeln ──────────────────────────────────────────────
    def _collect_device_info(self) -> None:
        """Sammelt erweiterte Gerätedaten: Zeit, Modell, Android, Netzwerk, Akku."""
        self.scan_time = datetime.now().strftime("%d.%m.%Y  %H:%M:%S")

        def _prop(key: str) -> str:
            return self.adb.shell(f"getprop {key} 2>/dev/null", timeout=6).strip()

        def _sh(cmd: str) -> str:
            return self.adb.shell(cmd + " 2>/dev/null", timeout=8).strip()

        self.device_info = {
            # Identität
            "Marke":             _prop("ro.product.brand"),
            "Modell":            _prop("ro.product.model"),
            "Gerätename":        _prop("ro.product.device"),
            "Android-Version":   _prop("ro.build.version.release"),
            "API-Level":         _prop("ro.build.version.sdk"),
            "Build":             _prop("ro.build.display.id"),
            "Sicherheitspatch":  _prop("ro.build.version.security_patch"),
            # Netzwerk
            "WLAN SSID":         _sh("dumpsys wifi | grep -m1 'SSID:' | sed 's/.*SSID: //'"),
            "IP-Adresse (WLAN)": _sh("ip -4 addr show wlan0 | grep 'inet ' | awk '{print $2}' | head -1"),
            "IP-Adresse (LTE)":  _sh("ip -4 addr show rmnet0 | grep 'inet ' | awk '{print $2}' | head -1"),
            "MAC-Adresse":       _sh("cat /sys/class/net/wlan0/address"),
            # Gerätezustand
            "Akku (%)":          _sh("dumpsys battery | grep level | awk '{print $2}'"),
            "Akku-Status":       _sh("dumpsys battery | grep status | awk '{print $2}'"),
            "Bildschirm":        _sh("dumpsys power | grep -m1 'Display Power' | sed 's/.*state=//'"),
            "Uptime":            _sh("uptime -p"),
            "Systemzeit (Gerät)": _sh("date '+%d.%m.%Y %H:%M:%S'"),
            # IMEI / Telefonie
            "IMEI":              _sh("dumpsys iphonesubinfo | grep 'Device ID' | cut -d'=' -f2"),
            "SIM-Betreiber":     _sh("getprop gsm.operator.alpha"),
            "SIM-ISO":           _sh("getprop gsm.operator.iso-country"),
            # Root
            "Root-Status":       "JA" if self.has_root else "NEIN",
            "ADB-Status":        "Verbunden",
        }

    # ─── Öffentliche Methode ───────────────────────────────────────────────
    def show_menu(self) -> None:
        while True:
            ui.clear()
            ui.banner(subtitle="🔍 GOOGLE-KONTO-SCANNER")
            print()
            entries = [
                ("1", "🔍  Alle Konten scannen (kein Root nötig)"),
                ("2", "🔐  Tiefen-Scan inkl. gelöschter Konten (Root)"),
                ("3", "📋  Letzten Scan anzeigen"),
                ("4", "💾  Export als TXT / JSON"),
            ]
            ch = ui.menu("Konto-Scanner", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return
            if ch == "1":
                self._run_scan(root=False)
            elif ch == "2":
                self._run_scan(root=True)
            elif ch == "3":
                if self.accounts:
                    self._display_results()
                else:
                    ui.warn("Noch kein Scan durchgeführt.")
                    ui.pause()
            elif ch == "4":
                self._export_menu()

    # ─── Scan-Logik ───────────────────────────────────────────────────────
    def _run_scan(self, root: bool = False) -> None:
        ui.clear()
        ui.rule("🔍 KONTO-SCAN LÄUFT …", ui.BCYAN)
        print()

        self.accounts = []
        self.has_root = root and self.adb.check_root()

        steps = [
            ("🖥  Gerätedaten abrufen …",      self._collect_device_info),
            ("📋 dumpsys account lesen …",     self._parse_dumpsys),
            ("🔒 FRP-Schutz prüfen …",         self._detect_frp),
            ("🔄 Sync-Adapter lesen …",        self._enrich_sync_adapters),
            ("🔑 Auth-History analysieren …",  self._enrich_auth_history),
        ]
        if self.has_root:
            steps.insert(2, ("💾 accounts_ce.db (Root) …", self._parse_accounts_db))

        total = len(steps)
        for i, (label, fn) in enumerate(steps, 1):
            from . import progress
            pct = i / total
            filled = int(36 * pct)
            bar = "▰" * filled + "▱" * (36 - filled)
            import sys
            sys.stdout.write(f"\r  \033[96m│{bar}│\033[0m {pct*100:5.1f}%  {label:<40}")
            sys.stdout.flush()
            fn()
        print()
        print()
        self._display_results()

    # ─── dumpsys account Parser ──────────────────────────────────────────
    def _parse_dumpsys(self) -> None:
        raw = self.adb.shell("dumpsys account 2>/dev/null", timeout=30)
        if not raw:
            ui.warn("dumpsys account lieferte keine Ausgabe.")
            return

        # Jedes Konto-Block beginnt mit "Account {name=... type=..."
        blocks = re.split(r"(?=Account\s*\{)", raw)
        seen = set()

        for block in blocks:
            m = re.search(r"name=([^,}\s]+)", block)
            t = re.search(r"type=([^,}\s]+)", block)
            if not m or not t:
                continue
            email = m.group(1).strip()
            atype = t.group(1).strip()
            if email in seen:
                continue
            seen.add(email)

            acc = GoogleAccount(
                email=email,
                account_type=atype,
                is_google=(atype == "com.google"),
                raw_block=block[:300],
            )
            self.accounts.append(acc)

    # ─── Root: accounts_ce.db ────────────────────────────────────────────
    def _parse_accounts_db(self) -> None:
        dbs = [
            "/data/system_ce/0/accounts_ce.db",
            "/data/system_de/0/accounts_de.db",
            "/data/system/accounts.db",
        ]
        seen_emails = {a.email for a in self.accounts}

        for db_path in dbs:
            exists = self.adb.shell(f"[ -f '{db_path}' ] && echo yes 2>/dev/null", root=True)
            if "yes" not in exists:
                continue

            # Aktive Konten mit Zeitstempel
            rows = self.adb.shell(
                f"sqlite3 '{db_path}' 'SELECT name,type,last_password_entry_time_millis_epoch "
                f"FROM accounts' 2>/dev/null",
                root=True, timeout=20
            )
            for line in rows.splitlines():
                parts = line.strip().split("|")
                if len(parts) < 2:
                    continue
                email, atype = parts[0].strip(), parts[1].strip()
                ts = parts[2].strip() if len(parts) > 2 else ""
                added = _ms_to_str(ts)
                if email not in seen_emails:
                    self.accounts.append(GoogleAccount(
                        email=email, account_type=atype,
                        is_google=(atype == "com.google"),
                        added_time=added,
                    ))
                    seen_emails.add(email)
                else:
                    for a in self.accounts:
                        if a.email == email:
                            a.added_time = added

            # Gelöschte Konten via .recover
            recovered = self.adb.shell(
                f"sqlite3 '{db_path}' '.recover' 2>/dev/null | grep -i 'com\\.google\\|@gmail\\|@' | head -50",
                root=True, timeout=20
            )
            for line in recovered.splitlines():
                if "@" not in line and "com.google" not in line:
                    continue
                # Versuche E-Mail zu extrahieren
                em = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", line)
                if em and em.group(0) not in seen_emails:
                    self.accounts.append(GoogleAccount(
                        email=em.group(0), account_type="com.google",
                        is_google=True, deleted=True,
                    ))
                    seen_emails.add(em.group(0))
            break  # erste gefundene DB reicht

    # ─── FRP-Erkennung (alle 10 Methoden via frp_scanner) ────────────────
    def _detect_frp(self) -> None:
        from . import frp_scanner as _frp_mod
        scanner = _frp_mod.FrpScanner(self.adb)

        ui.info("FRP-Scan: 10 Methoden werden ausgeführt …")
        methods = [
            scanner._method_1_settings_secure,
            scanner._method_2_settings_global,
            scanner._method_3_content_provider,
            scanner._method_4_device_policy_dump,
            scanner._method_5_frp_partition,
            scanner._method_6_getprop_frp,
            scanner._method_7_device_policies_xml,
            scanner._method_8_accounts_db,
            scanner._method_9_activity_stack,
            scanner._method_10_gms_db,
        ]
        for i, method in enumerate(methods, 1):
            ui.progress(i, 10, f"FRP-Methode {i}/10 …")
            try:
                finding = method()
                if finding.found and finding.email and not self.frp_email:
                    self.frp_email = finding.email
            except Exception:
                pass

        # FRP-Flag auf passendes Konto setzen
        if self.frp_email:
            for acc in self.accounts:
                if acc.email.lower() == self.frp_email.lower():
                    acc.is_frp_account = True

    # ─── Sync-Adapter anreichern ─────────────────────────────────────────
    def _enrich_sync_adapters(self) -> None:
        raw = self.adb.shell("dumpsys account 2>/dev/null", timeout=30)
        if not raw:
            return

        # Sync-Status aus "Active sync:" und "Status" Blöcken
        for acc in self.accounts:
            adapters: List[SyncAdapter] = []
            # Suche nach diesem Konto im Dump
            pattern = re.escape(acc.email)
            # Alle authority-Zeilen nach dem E-Mail-Vorkommen sammeln
            section = ""
            in_section = False
            for line in raw.splitlines():
                if acc.email in line:
                    in_section = True
                    section = ""
                if in_section:
                    section += line + "\n"
                    if line.strip() == "}" and section.count("{") <= section.count("}"):
                        break

            seen_auth = set()
            for auth_m in re.finditer(r"authority=([^\s,}]+)", section):
                auth = auth_m.group(1).strip()
                if auth in seen_auth:
                    continue
                seen_auth.add(auth)
                label = _SYNC_LABELS.get(auth, auth.split(".")[-1])
                # enabled?
                enabled = True
                adapters.append(SyncAdapter(authority=auth, label=label, enabled=enabled))

            if not adapters:
                # Fallback: Standard-Google-Sync-Adapter anzeigen wenn Google-Konto
                if acc.is_google:
                    for auth, label in _SYNC_LABELS.items():
                        if "google" in auth:
                            adapters.append(SyncAdapter(authority=auth, label=label, enabled=True))

            acc.sync_adapters = adapters[:10]  # max 10

    # ─── Auth-History anreichern ─────────────────────────────────────────
    def _enrich_auth_history(self) -> None:
        """Sammelt An-/Abmelde-Häufigkeit, Tokens, letzte Auth-Zeitstempel."""

        # 1. Auth-Token-Anzahl aus dumpsys account (authTokens Blöcke)
        dump = self.adb.shell("dumpsys account 2>/dev/null", timeout=30)
        for acc in self.accounts:
            if not acc.is_google or acc.deleted:
                continue
            # Token-Blöcke zählen
            pattern = re.escape(acc.email)
            in_sec = False
            token_count = 0
            failure_count = 0
            last_auth = ""
            last_sync = ""
            for line in dump.splitlines():
                if acc.email in line:
                    in_sec = True
                if in_sec:
                    if "authToken" in line or "authtoken" in line.lower():
                        token_count += 1
                    if "syncFailed" in line or "ERROR" in line.upper():
                        failure_count += 1
                    # Zeitstempel
                    ts_m = re.search(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", line)
                    if ts_m:
                        ts = ts_m.group(1)
                        if "sync" in line.lower() and not last_sync:
                            last_sync = ts
                        elif not last_auth:
                            last_auth = ts
                    # Nächster Konto-Block → Ende
                    if re.match(r"\s*Account\s*\{", line) and acc.email not in line:
                        break

            acc.token_count   = max(token_count, 0)
            acc.auth_failures = failure_count
            if last_auth:
                acc.last_auth_time = last_auth
            if last_sync:
                acc.last_sync_time = last_sync

        # 2. logcat: letzte Anmeldungen (ohne Root, begrenzte History)
        logcat = self.adb.shell(
            "logcat -d -t 500 2>/dev/null | grep -i 'AccountManager\\|signin\\|signout\\|logout\\|login' | tail -30",
            timeout=15
        )
        for acc in self.accounts:
            if not acc.is_google or acc.deleted:
                continue
            email_short = acc.email.split("@")[0]
            count = len([l for l in logcat.splitlines()
                         if acc.email in l or email_short in l])
            acc.login_count = count

        # 3. Root: accounts_ce.db für genaue Zeitstempel
        if self.has_root:
            db = "/data/system_ce/0/accounts_ce.db"
            for acc in self.accounts:
                if not acc.is_google or acc.deleted:
                    continue
                # Last-auth-time aus der DB
                rows = self.adb.shell(
                    f"sqlite3 '{db}' \"SELECT last_password_time FROM accounts "
                    f"WHERE name='{acc.email}' LIMIT 1\" 2>/dev/null",
                    root=True, timeout=10
                ).strip()
                if rows and rows.isdigit():
                    ts_ms = int(rows)
                    if ts_ms > 0:
                        from datetime import timezone
                        dt = datetime.fromtimestamp(ts_ms / 1000)
                        acc.last_auth_time = dt.strftime("%d.%m.%Y  %H:%M:%S")

                # GAIA-ID aus extras-Spalte
                extras = self.adb.shell(
                    f"sqlite3 '{db}' \"SELECT extras FROM accounts "
                    f"WHERE name='{acc.email}' LIMIT 1\" 2>/dev/null",
                    root=True, timeout=10
                )
                gaia_m = re.search(r"userGaiaId[=:](\d+)", extras)
                if gaia_m:
                    acc.gaia_id = gaia_m.group(1)

        # 4. Aktive Google-Dienste aus pm list packages
        gms_pkgs = self.adb.shell(
            "pm list packages 2>/dev/null | grep 'com.google' | sed 's/package://'",
            timeout=12
        )
        pkg_nice = {
            "com.google.android.gm":             "Gmail",
            "com.google.android.calendar":       "Google Kalender",
            "com.google.android.contacts":       "Google Kontakte",
            "com.google.android.apps.photos":    "Google Fotos",
            "com.google.android.apps.drive":     "Google Drive",
            "com.google.android.youtube":        "YouTube",
            "com.google.android.maps":           "Google Maps",
            "com.google.android.keep":           "Google Keep",
            "com.google.android.music":          "Google Musik",
            "com.google.android.apps.fitness":   "Google Fit",
            "com.google.android.dialer":         "Google Dialer",
            "com.google.android.apps.messaging": "Google Messages",
            "com.google.android.documentsui":    "Dateien",
            "com.google.android.play.games":     "Play Games",
            "com.google.android.googlequicksearchbox": "Google-Suche",
        }
        installed_services = []
        for pkg in gms_pkgs.splitlines():
            pkg = pkg.strip()
            if pkg in pkg_nice:
                installed_services.append(pkg_nice[pkg])
        for acc in self.accounts:
            if acc.is_google and not acc.deleted:
                acc.services = installed_services

    # ─── Anzeige ─────────────────────────────────────────────────────────
    def _display_results(self) -> None:
        ui.clear()
        ui.banner(subtitle="📋 KONTO-SCAN ERGEBNISSE")

        google_accs  = [a for a in self.accounts if a.is_google and not a.deleted]
        other_accs   = [a for a in self.accounts if not a.is_google and not a.deleted]
        deleted_accs = [a for a in self.accounts if a.deleted]

        # ══ SCAN-KOPF: Datum / Uhrzeit / Gerät ════════════════════════
        ui.rule("🕐 SCAN-INFORMATION", ui.BCYAN)
        print()
        di = self.device_info
        _kv = lambda k, v: print(f"  {ui.BOLD}{k:<22}{ui.RESET}  {v}") if v else None

        _kv("Scan-Zeitpunkt",     f"{ui.BYELLOW}{self.scan_time}{ui.RESET}")
        _kv("Marke / Modell",     f"{di.get('Marke','')} {di.get('Modell','')}")
        _kv("Android-Version",    f"{di.get('Android-Version','')}  (API {di.get('API-Level','')})")
        _kv("Build / Patch",      f"{di.get('Build','')}  ·  Patch: {di.get('Sicherheitspatch','')}")
        _kv("Systemzeit Gerät",   di.get("Systemzeit (Gerät)", ""))
        _kv("Uptime",             di.get("Uptime", ""))
        print()

        # ══ NETZWERK ══════════════════════════════════════════════════
        ui.rule("🌐 NETZWERK", ui.CYAN)
        print()
        _kv("WLAN SSID",          di.get("WLAN SSID", ""))
        _kv("IP (WLAN)",          di.get("IP-Adresse (WLAN)", ""))
        _kv("IP (LTE/Mobil)",     di.get("IP-Adresse (LTE)", ""))
        _kv("MAC-Adresse",        di.get("MAC-Adresse", ""))
        _kv("SIM-Betreiber",      di.get("SIM-Betreiber", ""))
        _kv("SIM-Land",           di.get("SIM-ISO", ""))
        _kv("IMEI",               di.get("IMEI", ""))
        print()

        # ══ GERÄTEZUSTAND ═════════════════════════════════════════════
        ui.rule("🔋 GERÄTEZUSTAND", ui.CYAN)
        print()
        akku = di.get("Akku (%)", "")
        akku_color = ui.BGREEN if akku.isdigit() and int(akku) > 30 else ui.BRED
        _kv("Akku",               f"{akku_color}{akku}%{ui.RESET}  Status: {di.get('Akku-Status','')}")
        _kv("Bildschirm",         di.get("Bildschirm", ""))
        _kv("Root-Zugang",        f"{ui.BGREEN}JA{ui.RESET}" if self.has_root else f"{ui.GREY}NEIN{ui.RESET}")
        _kv("ADB",                f"{ui.BGREEN}Verbunden{ui.RESET}")
        print()

        # ══ GOOGLE-KONTEN ═════════════════════════════════════════════
        ui.rule(f"🔑 GOOGLE-KONTEN ({len(google_accs)})", ui.BGREEN)
        print()
        if google_accs:
            for idx, acc in enumerate(google_accs, 1):
                frp_badge = f"  {ui.BRED}🔒 FRP-KONTO{ui.RESET}" if acc.is_frp_account else ""
                print(f"  {ui.BGREEN}[{idx}]{ui.RESET}  {ui.BOLD}{ui.BYELLOW}{acc.email}{ui.RESET}{frp_badge}")
                print(f"       {ui.GREY}{'─'*60}{ui.RESET}")

                # Zeitstempel
                if acc.added_time:
                    print(f"       {ui.BOLD}Erstanmeldung:  {ui.RESET}{acc.added_time}")
                if acc.last_auth_time:
                    print(f"       {ui.BOLD}Letzte Auth:    {ui.RESET}{acc.last_auth_time}")
                if acc.last_sync_time:
                    print(f"       {ui.BOLD}Letzter Sync:   {ui.RESET}{acc.last_sync_time}")

                # Login-Aktivität
                lc_color = ui.BYELLOW if acc.login_count > 5 else ui.GREY
                print(f"       {ui.BOLD}Login-Ereignisse (logcat):{ui.RESET}  "
                      f"{lc_color}{acc.login_count}{ui.RESET}")
                tc_color = ui.BGREEN if acc.token_count > 0 else ui.GREY
                print(f"       {ui.BOLD}Aktive Auth-Tokens:{ui.RESET}  "
                      f"{tc_color}{acc.token_count}{ui.RESET}")
                if acc.auth_failures > 0:
                    print(f"       {ui.BOLD}Auth-Fehler:{ui.RESET}  {ui.BRED}{acc.auth_failures}×{ui.RESET}")
                if acc.gaia_id:
                    print(f"       {ui.BOLD}GAIA-ID:{ui.RESET}  {ui.GREY}{acc.gaia_id}{ui.RESET}")

                # Sync-Adapter
                if acc.sync_adapters:
                    labels = [
                        f"{ui.BGREEN}✓{ui.RESET} {s.label}" if s.enabled
                        else f"{ui.GREY}✗ {s.label}{ui.RESET}"
                        for s in acc.sync_adapters
                    ]
                    for chunk in [labels[i:i+4] for i in range(0, len(labels), 4)]:
                        print(f"       {ui.GREY}Sync:{ui.RESET}  {'  │  '.join(chunk)}")

                # Installierte Google-Dienste
                if acc.services:
                    svc_str = "  •  ".join(acc.services[:8])
                    print(f"       {ui.GREY}Google-Apps:{ui.RESET}  {svc_str}")
                    if len(acc.services) > 8:
                        print(f"       {ui.GREY}             … +{len(acc.services)-8} weitere{ui.RESET}")

                print()
        else:
            print(f"  {ui.GREY}Keine Google-Konten gefunden.{ui.RESET}\n")

        # ══ FRP-SCHUTZ ════════════════════════════════════════════════
        if self.frp_email:
            ui.rule("🔒 FRP-SCHUTZ – ACHTUNG!", ui.BRED)
            print()
            print(f"  {ui.BRED}{ui.BOLD}  Schützendes Konto:  {self.frp_email}{ui.RESET}")
            print(f"  {ui.GREY}  → Nach einem Werksreset wird dieses Konto zum Entsperren benötigt!{ui.RESET}")
            print()

        # ══ WEITERE KONTEN ════════════════════════════════════════════
        if other_accs:
            ui.rule(f"📱 WEITERE KONTEN ({len(other_accs)})", ui.CYAN)
            print()
            type_groups: Dict[str, List[str]] = {}
            for acc in other_accs:
                type_groups.setdefault(acc.account_type, []).append(acc.email)
            for atype, emails in sorted(type_groups.items()):
                label = _type_label(atype)
                print(f"  {ui.BOLD}{label:<22}{ui.RESET}  {ui.GREY}{atype}{ui.RESET}")
                for em in emails:
                    print(f"    {ui.CYAN}•{ui.RESET}  {em}")
            print()

        # ══ GELÖSCHTE KONTEN (Root) ═══════════════════════════════════
        if deleted_accs:
            ui.rule(f"🗑  GELÖSCHTE / ABGEMELDETE KONTEN ({len(deleted_accs)})  [Root]", ui.BYELLOW)
            print()
            for acc in deleted_accs:
                print(f"  {ui.GREY}✗  {acc.email:<40}  {acc.account_type}{ui.RESET}")
            print()

        # ══ ZUSAMMENFASSUNG ═══════════════════════════════════════════
        ui.rule("📊 ZUSAMMENFASSUNG", ui.BCYAN)
        print()
        total_accs = len(google_accs) + len(other_accs)
        ui.kv("Scan-Zeitpunkt",          self.scan_time)
        ui.kv("Gerät",                   f"{di.get('Marke','')} {di.get('Modell','')}  (Android {di.get('Android-Version','')})")
        ui.kv("Sicherheitspatch",        di.get("Sicherheitspatch", ""))
        ui.kv("WLAN / IP",               f"{di.get('WLAN SSID','')}  •  {di.get('IP-Adresse (WLAN)','')}")
        ui.kv("SIM-Betreiber",           di.get("SIM-Betreiber", ""))
        ui.kv("Akku",                    f"{di.get('Akku (%)','?')}%")
        print()
        ui.kv("Google-Konten (aktiv)",   str(len(google_accs)))
        ui.kv("Weitere Konten",          str(len(other_accs)))
        ui.kv("Konten gesamt",           str(total_accs))
        if deleted_accs:
            ui.kv("Gelöschte Konten [Root]", str(len(deleted_accs)))
        print()
        # Pro Google-Konto: Auth-Zusammenfassung
        for acc in google_accs:
            ui.kv(f"  {acc.email[:30]}",
                  f"Tokens: {acc.token_count}  │  Logins: {acc.login_count}  │  Fehler: {acc.auth_failures}")
            if acc.last_auth_time:
                ui.kv("    Letzte Auth", acc.last_auth_time)
        print()
        ui.kv("FRP-Schutz",
              f"{ui.BRED}JA – {self.frp_email}{ui.RESET}" if self.frp_email
              else f"{ui.BGREEN}Kein FRP erkannt{ui.RESET}")
        ui.kv("Root-Zugang",             "JA" if self.has_root else "NEIN")
        print()
        ui.pause()

    # ─── Export ──────────────────────────────────────────────────────────
    def _export_menu(self) -> None:
        if not self.accounts:
            ui.warn("Zuerst Scan durchführen (Option 1 oder 2).")
            ui.pause()
            return

        ui.clear()
        ui.rule("💾 EXPORT", ui.BCYAN)
        outdir = os.path.expanduser("~/panzer_exports/google_accounts")
        os.makedirs(outdir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # TXT
        txt_path = os.path.join(outdir, f"accounts_{ts}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("AndroidPanzer – Google-Konto-Scanner\n")
            f.write(f"Erstellt: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            for acc in self.accounts:
                status = "GELÖSCHT" if acc.deleted else "AKTIV"
                frp = " [FRP]" if acc.is_frp_account else ""
                f.write(f"[{status}]{frp} {acc.email}  ({acc.account_type})\n")
                if acc.added_time:
                    f.write(f"  Hinzugefügt: {acc.added_time}\n")
                if acc.sync_adapters:
                    f.write(f"  Sync: {', '.join(s.label for s in acc.sync_adapters)}\n")
                f.write("\n")
        ui.ok(f"TXT gespeichert: {txt_path}")

        # JSON
        json_path = os.path.join(outdir, f"accounts_{ts}.json")
        data = {
            "scan_time": datetime.now().isoformat(),
            "frp_email": self.frp_email,
            "accounts": [asdict(a) for a in self.accounts],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        ui.ok(f"JSON gespeichert: {json_path}")
        print()
        ui.pause()


# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def _ms_to_str(ms_str: str) -> str:
    try:
        ms = int(ms_str)
        if ms > 0:
            return datetime.fromtimestamp(ms / 1000).strftime("%d.%m.%Y %H:%M")
    except (ValueError, OSError):
        pass
    return ""


def _type_label(atype: str) -> str:
    mapping = {
        "com.samsung.android.sm.otherdevices.accounts": "Samsung",
        "com.samsung.android.easysetup.accounts":       "Samsung Easy Setup",
        "com.microsoft.exchangeactivesync":             "Exchange / Outlook",
        "com.whatsapp":                                 "WhatsApp",
        "org.telegram.messenger":                       "Telegram",
        "com.facebook.auth.login":                      "Facebook",
        "com.instagram.auth":                           "Instagram",
        "com.twitter.android.auth":                     "Twitter/X",
        "com.spotify.mobile":                           "Spotify",
        "com.netflix.mediaclient":                      "Netflix",
    }
    return mapping.get(atype, atype.split(".")[-2] if "." in atype else atype)


# ─── Modul-Einstieg ──────────────────────────────────────────────────────────

def create_scanner(adb: ADB) -> GoogleAccountScanner:
    return GoogleAccountScanner(adb)


def menu(adb=None) -> None:
    if adb is None:
        ui.warn("Kein ADB-Gerät verbunden.")
        ui.pause()
        return
    scanner = GoogleAccountScanner(adb)
    scanner.show_menu()
