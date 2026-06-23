"""FRP-SCANNER: Factory Reset Protection – 10 Erkennungsmethoden.

FRP (Factory Reset Protection) sperrt das Gerät nach einem Werksreset auf das
zuletzt eingeloggte Google-Konto. Dieser Scanner erkennt:
  1.  Settings Secure: google_account_for_frp
  2.  Settings Global: frp_credential_alias
  3.  Content-Provider: settings/secure WHERE name='google_account_for_frp'
  4.  dumpsys device_policy (Enterprise/MDM FRP-Policy)
  5.  FRP-Partition: /dev/block/by-name/frp (raw lesen, Root)
  6.  getprop ro.frp.pst (Kernel-Property für FRP-Partition-Pfad)
  7.  /data/system/device_policies.xml (Root, Enterprise-Policy)
  8.  accounts_ce.db: letzte com.google-Konten vor Reset-Kandidaten (Root)
  9.  dumpsys activity: FRP-Setup-Wizard-Stack (läuft FRP gerade aktiv?)
  10. Google-Play-Services GmsCore DB (Root): frp_account_key
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from . import ui
from .adb import ADB


@dataclass
class FrpFinding:
    method_nr: int
    method_name: str
    found: bool
    email: str = ""
    detail: str = ""
    needs_root: bool = False
    root_available: bool = False
    raw_output: str = ""      # vollständige Rohdaten der Methode (ungekürzt)
    command: str = ""         # ADB-Befehl der ausgeführt wurde


class FrpScanner:
    """Factory Reset Protection Scanner mit 10 Erkennungsmethoden."""

    def __init__(self, adb: ADB):
        self.adb = adb
        self.findings: List[FrpFinding] = []
        self.frp_email: str = ""
        self.frp_active: bool = False
        self.has_root: bool = False

    # ─── Hauptmenü ────────────────────────────────────────────────────────
    def show_menu(self) -> None:
        while True:
            ui.clear()
            ui.banner(subtitle="🔒 FRP-SCANNER – Factory Reset Protection")
            print()
            entries = [
                ("1", "🔍  FRP-Scan (alle 10 Methoden, kein Root nötig für 1-9)"),
                ("2", "🔐  FRP-Scan + Root-Methoden (5, 8, 10)"),
                ("3", "📋  Letzten Scan anzeigen"),
                ("4", "💾  Export als TXT / JSON"),
                ("5", "ℹ️   Was ist FRP? (Erklärung)"),
            ]
            ch = ui.menu("FRP-Scanner", entries, back_label="Hauptmenü")
            if ch in ("back", "quit"):
                return
            if ch == "1":
                self._run_scan(root=False)
            elif ch == "2":
                self._run_scan(root=True)
            elif ch == "3":
                if self.findings:
                    self._display_results()
                else:
                    ui.warn("Noch kein Scan durchgeführt.")
                    ui.pause()
            elif ch == "4":
                self._export()
            elif ch == "5":
                self._show_info()

    # ─── Scan ─────────────────────────────────────────────────────────────
    def _run_scan(self, root: bool) -> None:
        ui.clear()
        ui.rule("🔒 FRP-SCAN – 10 METHODEN", ui.BRED)
        print()

        self.findings = []
        self.frp_email = ""
        self.frp_active = False
        self.has_root = root and self.adb.check_root()

        methods = [
            self._method_1_settings_secure,
            self._method_2_settings_global,
            self._method_3_content_provider,
            self._method_4_device_policy_dump,
            self._method_5_frp_partition,
            self._method_6_getprop_frp,
            self._method_7_device_policies_xml,
            self._method_8_accounts_db,
            self._method_9_activity_stack,
            self._method_10_gms_db,
        ]

        for i, method in enumerate(methods, 1):
            ui.progress(i, 10, f"Methode {i}/10 …")
            try:
                finding = method()
                self.findings.append(finding)
                if finding.found and finding.email and not self.frp_email:
                    self.frp_email = finding.email
            except Exception as e:
                self.findings.append(FrpFinding(
                    method_nr=i, method_name=f"Methode {i}",
                    found=False, detail=f"Fehler: {e}",
                ))

        print()
        self._display_results()

    # ─── Methode 1: settings get secure ──────────────────────────────────
    def _method_1_settings_secure(self) -> FrpFinding:
        cmd = "settings get secure google_account_for_frp"
        f = FrpFinding(1, "Settings Secure: google_account_for_frp", False, command=cmd)
        out = self.adb.shell(cmd + " 2>/dev/null", timeout=8)
        f.raw_output = out
        out = out.strip()
        if out and out.lower() not in ("null", ""):
            f.found = True
            f.email = out
            f.detail = f"Wert: {out}"
        else:
            f.detail = "Nicht gesetzt (Wert: null)"
        return f

    # ─── Methode 2: settings global frp_credential_alias ─────────────────
    def _method_2_settings_global(self) -> FrpFinding:
        keys = ("frp_credential_alias", "frp_credential_handle", "setup_wizard_has_run")
        f = FrpFinding(2, "Settings Global: frp_credential_alias", False,
                       command="settings get global frp_credential_alias|frp_credential_handle|setup_wizard_has_run")
        raw_parts = []
        for key in keys:
            val = self.adb.shell(f"settings get global {key} 2>/dev/null", timeout=8).strip()
            raw_parts.append(f"{key} = {val}")
            if val and val.lower() not in ("null", "0", ""):
                f.found = True
                f.detail += f"{key}={val}  "
        f.raw_output = "\n".join(raw_parts)
        if not f.found:
            f.detail = "Keine FRP-Credential-Einträge gefunden"
        return f

    # ─── Methode 3: Content-Provider ─────────────────────────────────────
    def _method_3_content_provider(self) -> FrpFinding:
        cmd = "content query --uri content://settings/secure --where \"name='google_account_for_frp'\""
        f = FrpFinding(3, "Content-Provider: settings/secure frp-Eintrag", False, command=cmd)
        out = self.adb.shell(cmd + " 2>/dev/null", timeout=10)
        f.raw_output = out
        m = re.search(r"value=([^\s,}]+)", out)
        if m:
            val = m.group(1).strip()
            if val.lower() not in ("null", ""):
                f.found = True
                f.email = val
                f.detail = f"Content-Provider Wert: {val}"
        if not f.found:
            f.detail = "Kein Eintrag im Content-Provider"
        return f

    # ─── Methode 4: dumpsys device_policy ────────────────────────────────
    def _method_4_device_policy_dump(self) -> FrpFinding:
        cmd = "dumpsys device_policy 2>/dev/null | grep -i -A3 'frp\\|factory.reset\\|account'"
        f = FrpFinding(4, "dumpsys device_policy: FRP-Policy-Einträge", False, command=cmd)
        out = self.adb.shell(cmd, timeout=15)
        f.raw_output = out
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", out)
        frp_lines = [l.strip() for l in out.splitlines() if "frp" in l.lower() or "factory" in l.lower()]
        if frp_lines or emails:
            f.found = True
            if emails:
                f.email = emails[0]
            f.detail = "; ".join(frp_lines[:3]) or f"E-Mails: {', '.join(emails[:3])}"
        else:
            f.detail = "Keine FRP-Policy in device_policy"
        return f

    # ─── Methode 5: FRP-Partition (Root) ─────────────────────────────────
    def _method_5_frp_partition(self) -> FrpFinding:
        f = FrpFinding(5, "FRP-Partition /dev/block/by-name/frp (Root)", False, needs_root=True)
        f.root_available = self.has_root
        if not self.has_root:
            f.detail = "Root nicht verfügbar – übersprungen"
            return f

        # Partition finden
        part_path = self.adb.shell(
            "ls -la /dev/block/by-name/frp 2>/dev/null || "
            "find /dev/block -name 'frp' 2>/dev/null | head -1",
            root=True, timeout=10
        ).strip()

        if not part_path:
            f.detail = "FRP-Partition nicht gefunden (/dev/block/by-name/frp)"
            return f

        # Strings aus Partition lesen
        strings_out = self.adb.shell(
            f"strings /dev/block/by-name/frp 2>/dev/null | head -50",
            root=True, timeout=15
        )
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", strings_out)
        has_data = any(c.isalnum() for c in strings_out)

        if emails:
            f.found = True
            f.email = emails[0]
            f.detail = f"E-Mail in FRP-Partition: {', '.join(set(emails))}"
        elif has_data:
            f.found = True
            f.detail = f"Partition enthält Daten (kein Klartext-E-Mail): {strings_out[:80]}"
        else:
            f.detail = "FRP-Partition leer (kein FRP aktiv oder bereits gelöscht)"
        return f

    # ─── Methode 6: getprop ro.frp.pst ───────────────────────────────────
    def _method_6_getprop_frp(self) -> FrpFinding:
        props = ("ro.frp.pst", "ro.boot.vbmeta.frp", "ro.setupwizard.mode",
                 "ro.frp.require_device_lock", "persist.sys.frp")
        f = FrpFinding(6, "getprop: ro.frp.pst / ro.boot.vbmeta.frp", False,
                       command="getprop ro.frp.pst / ro.boot.vbmeta.frp / ro.setupwizard.mode / ...")
        details = []
        raw_parts = []
        for prop in props:
            val = self.adb.shell(f"getprop {prop} 2>/dev/null", timeout=8).strip()
            raw_parts.append(f"{prop} = {val or '(leer)'}")
            if val:
                details.append(f"{prop}={val}")
                f.found = True
        wizard = self.adb.shell("getprop ro.setupwizard.mode 2>/dev/null", timeout=8).strip()
        if wizard:
            details.append(f"setup_wizard_mode={wizard}")
            raw_parts.append(f"ro.setupwizard.mode = {wizard}")
        f.raw_output = "\n".join(raw_parts)
        f.detail = "  |  ".join(details) if details else "Keine FRP-Properties gesetzt"
        return f

    # ─── Methode 7: device_policies.xml (Root) ───────────────────────────
    def _method_7_device_policies_xml(self) -> FrpFinding:
        f = FrpFinding(7, "/data/system/device_policies.xml (Root)", False, needs_root=True)
        f.root_available = self.has_root
        if not self.has_root:
            f.detail = "Root nicht verfügbar – übersprungen"
            return f

        out = self.adb.shell(
            "cat /data/system/device_policies.xml 2>/dev/null | grep -i 'frp\\|account\\|google'",
            root=True, timeout=10
        )
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", out)
        if emails:
            f.found = True
            f.email = emails[0]
            f.detail = f"E-Mail in device_policies.xml: {', '.join(set(emails))}"
        elif out.strip():
            f.found = True
            f.detail = out.strip()[:150]
        else:
            f.detail = "Keine FRP-Einträge in device_policies.xml"
        return f

    # ─── Methode 8: accounts_ce.db (Root) ────────────────────────────────
    def _method_8_accounts_db(self) -> FrpFinding:
        f = FrpFinding(8, "accounts_ce.db: Google-Konten (Root)", False, needs_root=True)
        f.root_available = self.has_root
        if not self.has_root:
            f.detail = "Root nicht verfügbar – übersprungen"
            return f

        db = "/data/system_ce/0/accounts_ce.db"
        exists = self.adb.shell(f"[ -f '{db}' ] && echo yes 2>/dev/null", root=True)
        if "yes" not in exists:
            f.detail = "accounts_ce.db nicht gefunden"
            return f

        rows = self.adb.shell(
            f"sqlite3 '{db}' \"SELECT name,type FROM accounts WHERE type='com.google'\" 2>/dev/null",
            root=True, timeout=15
        )
        emails = []
        for line in rows.splitlines():
            parts = line.strip().split("|")
            if parts and "@" in parts[0]:
                emails.append(parts[0].strip())

        if emails:
            f.found = True
            f.email = emails[0]
            f.detail = f"Google-Konten in DB: {', '.join(emails)}"
        else:
            f.detail = "Keine Google-Konten in accounts_ce.db"
        return f

    # ─── Methode 9: Activity-Stack ────────────────────────────────────────
    def _method_9_activity_stack(self) -> FrpFinding:
        cmd = "dumpsys activity activities 2>/dev/null | grep -i 'frp\\|setupwizard\\|FrpActivity'"
        f = FrpFinding(9, "dumpsys activity: FRP-Setup-Wizard aktiv?", False, command=cmd)
        out = self.adb.shell(cmd + " | head -10", timeout=15)
        f.raw_output = out
        if out.strip():
            f.found = True
            self.frp_active = True
            f.detail = f"FRP-Activity aktiv: {out.strip()[:150]}"
        else:
            wizard_running = self.adb.shell(
                "dumpsys activity activities 2>/dev/null | grep -i 'setupwizard' | head -3",
                timeout=10
            )
            f.raw_output = wizard_running or "(keine Ausgabe)"
            if wizard_running.strip():
                f.found = True
                f.detail = f"Setup-Wizard läuft: {wizard_running.strip()[:100]}"
            else:
                f.detail = "Kein FRP-Setup-Wizard aktiv (Gerät normal entsperrt)"
        return f

    # ─── Methode 10: GmsCore DB (Root) ───────────────────────────────────
    def _method_10_gms_db(self) -> FrpFinding:
        f = FrpFinding(10, "GmsCore DB: frp_account_key (Root)", False, needs_root=True)
        f.root_available = self.has_root
        if not self.has_root:
            f.detail = "Root nicht verfügbar – übersprungen"
            return f

        gms_paths = [
            "/data/data/com.google.android.gms/databases/",
            "/data/data/com.google.android.gms/shared_prefs/",
        ]
        found_something = False
        details = []

        for base in gms_paths:
            files = self.adb.shell(f"ls '{base}' 2>/dev/null", root=True)
            for fname in files.splitlines():
                fname = fname.strip()
                if not fname:
                    continue
                full = f"{base}{fname}"

                if fname.endswith(".db"):
                    tables = self.adb.shell(
                        f"sqlite3 '{full}' \".tables\" 2>/dev/null", root=True, timeout=8
                    )
                    if any(kw in tables.lower() for kw in ("frp", "account", "credential")):
                        details.append(f"GMS-DB {fname}: Tabellen={tables.strip()[:60]}")
                        found_something = True
                        # Versuche frp-spezifische Einträge zu lesen
                        for tbl in tables.split():
                            if "frp" in tbl.lower() or "credential" in tbl.lower():
                                rows = self.adb.shell(
                                    f"sqlite3 '{full}' 'SELECT * FROM {tbl} LIMIT 5' 2>/dev/null",
                                    root=True, timeout=10
                                )
                                emails = re.findall(
                                    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", rows
                                )
                                if emails:
                                    f.email = emails[0]
                                    details.append(f"FRP-E-Mail in {tbl}: {emails[0]}")

                elif fname.endswith(".xml"):
                    content = self.adb.shell(
                        f"cat '{full}' 2>/dev/null | grep -i 'frp\\|account'", root=True, timeout=8
                    )
                    if content.strip():
                        found_something = True
                        emails = re.findall(
                            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", content
                        )
                        if emails:
                            f.email = emails[0]
                            details.append(f"FRP in {fname}: {emails[0]}")

        if found_something:
            f.found = True
            f.detail = "  |  ".join(details[:4]) if details else "GmsCore-Datenbank enthält FRP-relevante Einträge"
        else:
            f.detail = "Keine FRP-Einträge in GmsCore-Datenbanken"
        return f

    # ─── Anzeige ─────────────────────────────────────────────────────────
    def _display_results(self) -> None:
        ui.clear()
        ui.banner(subtitle="🔒 FRP-SCANNER ERGEBNISSE")
        print()

        # Fazit oben
        if self.frp_email:
            ui.rule("🔴 FRP-SCHUTZ AKTIV", ui.BRED)
            print()
            print(f"  {ui.BRED}{ui.BOLD}Schützendes Konto: {self.frp_email}{ui.RESET}")
            print(f"  {ui.GREY}Nach einem Werksreset muss dieses Google-Konto zum Entsperren verwendet werden!{ui.RESET}")
        else:
            ui.rule("🟢 KEIN FRP-SCHUTZ ERKANNT", ui.BGREEN)
            print()
            print(f"  {ui.BGREEN}Kein schützendes Google-Konto gefunden.{ui.RESET}")
            if self.frp_active:
                print(f"  {ui.BYELLOW}⚠  FRP-Aktivierungs-Wizard läuft aktuell!{ui.RESET}")
        print()

        # Alle 10 Methoden
        ui.rule("📋 ALLE 10 ERKENNUNGSMETHODEN", ui.CYAN)
        print()

        for f in self.findings:
            # Status-Icon
            if f.found:
                status = f"{ui.BGREEN}✓ GEFUNDEN   {ui.RESET}"
            else:
                status = f"{ui.GREY}✗ nicht gefunden{ui.RESET}"

            root_badge = ""
            if f.needs_root:
                if f.root_available:
                    root_badge = f"  {ui.BGREEN}[Root ✓]{ui.RESET}"
                else:
                    root_badge = f"  {ui.GREY}[Root fehlt]{ui.RESET}"

            print(f"  {ui.BOLD}[{f.method_nr:02d}]{ui.RESET}  {status}  {f.method_name}{root_badge}")
            if f.email:
                print(f"        {ui.BYELLOW}→ {f.email}{ui.RESET}")
            if f.detail:
                print(f"        {ui.GREY}{f.detail[:100]}{ui.RESET}")
            print()

        # Statistik
        found_count = sum(1 for f in self.findings if f.found)
        ui.rule("📊 ZUSAMMENFASSUNG", ui.BCYAN)
        print()
        ui.kv("Methoden ausgeführt",    f"{len(self.findings)}/10")
        ui.kv("Positiv (FRP gefunden)", f"{found_count}")
        ui.kv("Root-Methoden genutzt",  "Ja" if self.has_root else "Nein (Root-Scan: Option 2)")
        if self.frp_email:
            ui.kv("FRP-Konto",          self.frp_email)
            ui.kv("Risiko",
                  f"{ui.BRED}HOCH – Gerät nach Reset gesperrt!{ui.RESET}")
        print()

        # ─── Interaktive Methoden-Auswahl ────────────────────────────
        self._interactive_method_select()

    # ─── Interaktive Methoden-Auswahl ────────────────────────────────────
    def _interactive_method_select(self) -> None:
        """Nach dem Scan: Methode 1–10 auswählen für Detailansicht."""
        _METHOD_EXPLAIN = {
            1:  ("settings get secure google_account_for_frp",
                 "Liest den FRP-E-Mail-Wert direkt aus den Android Settings (Secure-Namespace).\n"
                 "Dies ist der zuverlässigste Nicht-Root-Weg. Wert 'null' = kein FRP gesetzt.\n"
                 "Interpretation: OPTIONAL = kein FRP, E-Mail = FRP-Konto aktiv."),
            2:  ("settings get global frp_credential_alias|frp_credential_handle",
                 "Prüft globale FRP-Credential-Einträge (Enterprise-FRP / MDM).\n"
                 "setup_wizard_has_run=1 bedeutet Ersteinrichtung abgeschlossen (FRP aktiv)."),
            3:  ("content query --uri content://settings/secure --where name='google_account_for_frp'",
                 "Liest den FRP-Wert über den Android Content-Provider.\n"
                 "Zuverlässiger als 'settings get' auf manchen Custom-ROMs.\n"
                 "Gibt Row-Daten zurück mit name=, value=, ..."),
            4:  ("dumpsys device_policy | grep -i frp|factory.reset|account",
                 "Analysiert die Device-Policy (MDM/Enterprise/Knox).\n"
                 "Enterprise-Geräte haben oft FRP via MDM-Policy gesetzt.\n"
                 "E-Mails im Output = MDM-FRP-Konto."),
            5:  ("strings /dev/block/by-name/frp",
                 "Liest die physische FRP-Partition im Block-Device direkt aus.\n"
                 "Erfordert Root. Die Partition enthält Klartext-E-Mail wenn FRP aktiv.\n"
                 "Auch nach Werksreset bleibt der Wert hier bis zum FRP-Unlock erhalten."),
            6:  ("getprop ro.frp.pst / ro.boot.vbmeta.frp / ro.setupwizard.mode",
                 "Kernel-Properties geben Aufschluss über FRP-Konfiguration.\n"
                 "ro.frp.pst = Pfad der FRP-Partition (/dev/block/persistent o.ä.)\n"
                 "ro.setupwizard.mode: OPTIONAL=kein FRP | DISABLED=FRP umgangen\n"
                 "ro.boot.vbmeta.frp = FRP via Verified Boot Metadata"),
            7:  ("cat /data/system/device_policies.xml | grep frp|account|google",
                 "XML-Datei mit allen Enterprise-Device-Policies.\n"
                 "Enthält FRP-Konten wenn Gerät MDM-verwaltet ist (Samsung Knox etc.).\n"
                 "Erfordert Root."),
            8:  ("sqlite3 /data/system_ce/0/accounts_ce.db SELECT name,type FROM accounts",
                 "Direkte SQLite-Abfrage der Konto-Datenbank.\n"
                 "Enthält alle angemeldeten Konten inkl. Zeitstempel und last_password_time.\n"
                 "Erfordert Root. com.google-Einträge = potenzielle FRP-Konten."),
            9:  ("dumpsys activity activities | grep -i frp|setupwizard|FrpActivity",
                 "Prüft ob der FRP-Setup-Wizard gerade aktiv im Activity-Stack läuft.\n"
                 "FrpActivity im Stack = Gerät befindet sich aktuell im FRP-Entsperr-Prozess.\n"
                 "Normalbetrieb: keine FRP-Activity sichtbar."),
            10: ("sqlite3 /data/data/com.google.android.gms/databases/ | grep frp|account",
                 "Liest GmsCore-Datenbanken (Google Play Services intern).\n"
                 "frp_account_key-Tabelle enthält den FRP-Account-Hash.\n"
                 "Erfordert Root und aktive GMS-Installation."),
        }

        while True:
            print(f"\n{ui.BCYAN}{'─'*60}{ui.RESET}")
            print(f"  {ui.BOLD}Methode auswählen für Details:{ui.RESET}  "
                  f"[{ui.BCYAN}1-10{ui.RESET}] Methode  "
                  f"[{ui.BGREEN}E{ui.RESET}] Export  "
                  f"[{ui.GREY}Q{ui.RESET}] Zurück")
            print(f"{ui.BCYAN}{'─'*60}{ui.RESET}")
            ch = input(f"  {ui.BOLD}❯ {ui.RESET}").strip().upper()

            if ch in ("Q", ""):
                return
            if ch == "E":
                self._export()
                return

            try:
                nr = int(ch)
                if 1 <= nr <= 10:
                    self._show_method_detail(nr, _METHOD_EXPLAIN)
                else:
                    ui.warn("Bitte 1–10 eingeben.")
            except ValueError:
                ui.warn("Ungültige Eingabe – 1-10, E oder Q.")

    def _show_method_detail(self, nr: int, explain: dict) -> None:
        """Zeigt Detailansicht einer einzelnen FRP-Erkennungsmethode."""
        f = next((x for x in self.findings if x.method_nr == nr), None)
        if not f:
            ui.warn(f"Methode {nr} nicht gefunden (Scan noch nicht ausgeführt?).")
            return

        ui.clear()
        ui.banner(subtitle=f"🔒 FRP-METHODE [{nr:02d}] – DETAIL")
        print()

        # Status-Header
        if f.found:
            ui.rule(f"✓ POSITIV – FRP-Merkmal erkannt", ui.BGREEN)
        else:
            ui.rule(f"✗ NEGATIV – kein FRP-Merkmal", ui.GREY)
        print()

        # Methoden-Info
        ui.kv("Methode",    f"[{nr:02d}] {f.method_name}")
        ui.kv("Ergebnis",   f"{ui.BGREEN}GEFUNDEN{ui.RESET}" if f.found else f"{ui.GREY}nicht gefunden{ui.RESET}")
        if f.email:
            ui.kv("FRP-E-Mail", f"{ui.BRED}{ui.BOLD}{f.email}{ui.RESET}")
        if f.needs_root:
            root_s = f"{ui.BGREEN}Root vorhanden ✓{ui.RESET}" if f.root_available else f"{ui.BRED}Root fehlt ✗{ui.RESET}"
            ui.kv("Root-Zugang", root_s)
        print()

        # ADB-Befehl
        if f.command:
            ui.rule("💻 ADB-BEFEHL", ui.CYAN)
            print()
            print(f"  {ui.BCYAN}adb shell {f.command}{ui.RESET}")
            print()

        # Ergebnis-Detail
        ui.rule("📋 ERGEBNIS", ui.CYAN)
        print()
        print(f"  {f.detail}")
        print()

        # Rohdaten
        if f.raw_output and f.raw_output.strip():
            ui.rule("📄 ROHDATEN (vollständige Ausgabe)", ui.GREY)
            print()
            lines = f.raw_output.strip().splitlines()
            for line in lines[:40]:
                print(f"  {ui.GREY}{line}{ui.RESET}")
            if len(lines) > 40:
                print(f"  {ui.GREY}… (+{len(lines)-40} weitere Zeilen){ui.RESET}")
            print()
        elif f.needs_root and not f.root_available:
            ui.rule("ℹ️  ROOT ERFORDERLICH", ui.BYELLOW)
            print()
            print(f"  {ui.BYELLOW}Diese Methode benötigt Root-Zugang.{ui.RESET}")
            print(f"  {ui.GREY}→ Scan mit Option 2 'FRP-Scan + Root-Methoden' erneut ausführen.{ui.RESET}")
            print()

        # Erklärung
        if nr in explain:
            cmd_hint, explanation = explain[nr]
            ui.rule("💡 WIE FUNKTIONIERT DIESE METHODE?", ui.BCYAN)
            print()
            for line in explanation.split("\n"):
                print(f"  {line}")
            print()

        # Navigation
        print(f"{ui.BCYAN}{'─'*60}{ui.RESET}")
        prev_nr = nr - 1 if nr > 1 else None
        next_nr = nr + 1 if nr < 10 else None
        nav = []
        if prev_nr:
            nav.append(f"[{ui.GREY}←{prev_nr}{ui.RESET}] Methode {prev_nr}")
        if next_nr:
            nav.append(f"[{ui.BCYAN}{next_nr}→{ui.RESET}] Methode {next_nr}")
        nav.append(f"[{ui.GREY}Q{ui.RESET}] Zurück zur Übersicht")
        print(f"  {'  │  '.join(nav)}")
        print(f"{ui.BCYAN}{'─'*60}{ui.RESET}")

        ch = input(f"  {ui.BOLD}❯ {ui.RESET}").strip().upper()
        if ch.isdigit() and 1 <= int(ch) <= 10:
            self._show_method_detail(int(ch), explain)
        # Q oder Enter → zurück zur Auswahl

    # ─── Export ──────────────────────────────────────────────────────────
    def _export(self) -> None:
        if not self.findings:
            ui.warn("Zuerst Scan durchführen.")
            ui.pause()
            return

        outdir = os.path.expanduser("~/panzer_exports/frp_scanner")
        os.makedirs(outdir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        txt_path = os.path.join(outdir, f"frp_{ts}.txt")
        with open(txt_path, "w", encoding="utf-8") as out:
            out.write("AndroidPanzer – FRP-Scanner\n")
            out.write(f"Erstellt: {datetime.now().isoformat()}\n")
            out.write("=" * 60 + "\n\n")
            out.write(f"FRP-Konto: {self.frp_email or 'NICHT GEFUNDEN'}\n\n")
            for f in self.findings:
                status = "GEFUNDEN" if f.found else "negativ"
                out.write(f"[{f.method_nr:02d}] {status}  {f.method_name}\n")
                if f.email:
                    out.write(f"    E-Mail: {f.email}\n")
                if f.detail:
                    out.write(f"    Detail: {f.detail}\n")
                out.write("\n")
        ui.ok(f"TXT: {txt_path}")

        json_path = os.path.join(outdir, f"frp_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as out:
            json.dump({
                "scan_time": datetime.now().isoformat(),
                "frp_email": self.frp_email,
                "frp_active_wizard": self.frp_active,
                "root_used": self.has_root,
                "findings": [
                    {"method": f.method_nr, "name": f.method_name,
                     "found": f.found, "email": f.email, "detail": f.detail}
                    for f in self.findings
                ],
            }, out, indent=2, ensure_ascii=False)
        ui.ok(f"JSON: {json_path}")
        print()
        ui.pause()

    # ─── Info-Seite ──────────────────────────────────────────────────────
    def _show_info(self) -> None:
        ui.clear()
        ui.rule("ℹ️  Was ist FRP?", ui.BCYAN)
        print()
        lines = [
            "Factory Reset Protection (FRP) ist eine Sicherheitsfunktion von Android 5.1+.",
            "",
            "Wie es funktioniert:",
            "  • Wenn ein Google-Konto auf dem Gerät eingeloggt ist, speichert Android",
            "    die Konto-E-Mail in einer geschützten FRP-Partition und in Settings.",
            "  • Nach einem Werksreset (Factory Reset) verlangt Android beim Setup",
            "    die Anmeldung mit GENAU diesem Konto.",
            "  • Ohne das Passwort ist das Gerät dauerhaft gesperrt.",
            "",
            "Erkennungsmethoden dieses Scanners:",
            "  01  settings get secure        → direkter Settings-Wert",
            "  02  settings get global         → FRP-Credential-Alias",
            "  03  Content-Provider            → settings/secure Content-Query",
            "  04  dumpsys device_policy       → Enterprise/MDM FRP-Richtlinien",
            "  05  FRP-Partition (Root)        → raw /dev/block/by-name/frp lesen",
            "  06  getprop ro.frp.pst          → Kernel-Property FRP-Partitionspfad",
            "  07  device_policies.xml (Root)  → XML-Policy-Datei",
            "  08  accounts_ce.db (Root)       → SQLite Google-Konten",
            "  09  Activity-Stack              → läuft FRP-Wizard gerade?",
            "  10  GmsCore DB (Root)           → frp_account_key in GMS-Datenbank",
        ]
        for line in lines:
            print(f"  {line}")
        print()
        ui.pause()


# ─── Modul-Einstieg ──────────────────────────────────────────────────────────

def menu(adb=None) -> None:
    if adb is None:
        ui.warn("Kein ADB-Gerät verbunden.")
        ui.pause()
        return
    scanner = FrpScanner(adb)
    scanner.show_menu()
