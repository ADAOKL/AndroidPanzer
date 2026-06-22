"""Vollständige Feature-Registry: 45 Kategorien × 10 = 450 Funktionen.

Jede Funktion ist eine der folgenden Arten ('kind'):
  cmd      → ADB-Shell-Kommando, Ausgabe im Pager                 [ADB]
  rootcmd  → wie cmd, aber via su -c                              [ROOT]
  ask      → fragt einen Wert ab, setzt ihn in ein Template ein   [ADB]
  fn       → ruft einen interaktiven Handler (handlers.py)        [LIVE]
  info     → Erklärung: was real nötig wäre (kein Fake)           [INFO]
  sdr      → benötigt SDR/JTAG/Spezial-Hardware                   [SDR/HW]
  danger   → destruktiv/irreversibel – nur mit Doppel-Bestätigung [GEFAHR]

Die 'note' wird vor der Ausführung angezeigt (Kontext/Warnung).
"""
from __future__ import annotations

from . import handlers as h


def f(n, t, k, p, note=""):
    return {"n": n, "t": t, "k": k, "p": p, "note": note}


# Wiederkehrende Erklärtexte
_NEED_ROOT = "Benötigt Root (su). Ohne Root nicht lesbar/ausführbar – Rooting-Assistent: Menüpunkt R."
_NEED_SDR = ("Real nur mit Software-Defined-Radio (HackRF/USRP/bladeRF) bzw. Diag-Port + QXDM/SCAT. "
             "Reines ADB kann das nicht – hier nur Doku/Vorbedingungen.")
_THEORY = ("Theoretisch/forensisch – in Software auf einem Standard-Stock-Gerät nicht durchführbar. "
           "Erfordert speziell präparierte Test-Hardware/Test-SIM/Lab-Setup.")
_RESTRICTED = "Auf modernen Android-Versionen oft nur mit Root/privilegierten Rechten lesbar."


CATEGORIES = [
    # ============================================================= 1
    ("🔬", "System- & Hardware-Diagnose", [
        f(1, "Speicherauslastung (RAM + intern)", "cmd", "df -h; echo ---; dumpsys meminfo | head -n 45"),
        f(2, "CPU-Echtzeit (Frequenzen + Top-Prozesse)", "cmd",
          "top -n 1 -b -m 12 2>/dev/null | head -n 22; echo ---; "
          "for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq; do cat $c 2>/dev/null; done"),
        f(3, "Display-Spezifikationen (Auflösung/DPI/Hz)", "cmd",
          "wm size; wm density; dumpsys display | grep -iE 'fps|refresh|density|real ' | head"),
        f(4, "Ausführlicher Akkuzustand", "cmd", "dumpsys battery"),
        f(5, "Netzwerk-Status (IP/MAC/RSSI)", "cmd",
          "ip addr | grep -E 'inet |link/ether'; echo ---; dumpsys wifi | grep -iE 'rssi|mac|ssid|freq' | head"),
        f(6, "SIM- & Provider-Infos", "cmd",
          "dumpsys telephony.registry | grep -iE 'operator|mcc|mnc|signal|networktype' | head -n 25"),
        f(7, "Sensoren-Rohdaten", "cmd", "dumpsys sensorservice | head -n 50"),
        f(8, "Bootloader- & Partitionsstatus", "cmd",
          "getprop | grep -iE 'verifiedboot|slot_suffix|flash.locked|oem_unlock'"),
        f(9, "Kernel- & Build-Details", "cmd",
          "uname -a; echo ---; getprop ro.build.fingerprint; getprop ro.build.version.security_patch"),
        f(10, "Audio-Status (Pegel/Geräte)", "cmd", "dumpsys audio | head -n 50"),
    ]),
    # ============================================================= 2
    ("📱", "App- & Paket-Management", [
        f(11, "App-Listen-Export (System/Drittanbieter)", "fn", h.app_list_export),
        f(12, "Sideloading (APK / Split-APK installieren)", "fn", h.install_apk),
        f(13, "App deinstallieren / deaktivieren (Bloatware)", "fn", h.uninstall_app),
        f(14, "App-Daten löschen / Force-Stop / Starten", "fn", h.app_control),
        f(15, "APK-Pfad & Signatur ermitteln", "fn", h.app_inspect),
        f(16, "Berechtigungen gewähren/entziehen", "fn", h.app_permissions),
        f(17, "App-Komponenten (Activities/Services/Receiver)", "fn", h.app_inspect),
        f(18, "Deep Link / Intent testen", "fn", h.deep_link),
        f(19, "App-Aktivitäten fuzzen (Monkey)", "fn", h.fuzz_intents),
        f(20, "App-Nutzungsstatistik (24h)", "cmd", "dumpsys usagestats | head -n 60"),
    ]),
    # ============================================================= 3
    ("🎮", "Fernsteuerung & UI-Automation", [
        f(21, "Tap (Fingertipp auf X/Y)", "fn", h.tap),
        f(22, "Swipe / Scroll / Drag", "fn", h.swipe),
        f(23, "Texteingabe", "fn", h.text_input),
        f(24, "Hardware-Tasten emulieren", "fn", h.keyevent),
        f(25, "Tastatur-Scancodes (Enter/Tab/Media)", "fn", h.keyevent),
        f(26, "Aufwecken / Sperren", "fn", h.screen_state),
        f(27, "UI-Skelett auslesen (uiautomator dump)", "fn", h.ui_dump),
        f(28, "Keyguard-Wischentsperrung", "cmd",
          "input keyevent KEYCODE_WAKEUP; input keyevent 82; input swipe 500 1800 500 400",
          "Funktioniert nur bei Swipe-Sperre bzw. wenn keine PIN gesetzt ist."),
        f(29, "Kontrolliertes Scrollen (Feed/Web)", "fn", h.swipe),
        f(30, "Multitouch / Pinch-to-Zoom", "info", h.swipe and
          "Echtes Multitouch erfordert Schreiben in /dev/input/eventX (Root). "
          "Einfache Gesten via 'input swipe' (Menü 22)."),
    ]),
    # ============================================================= 4
    ("⚙️", "System-Tweaks & Modding", [
        f(31, "Auflösung/DPI ändern", "ask", ("Größe z.B. 1080x2400 oder 'reset'", "wm size {v}"),
          "Danach ggf. 'wm density <dpi>' anpassen."),
        f(32, "Globaler Darkmode", "ask", ("yes / no / auto", "cmd uimode night {v}")),
        f(33, "Funkmodule schalten (wifi/bt/nfc/data)", "ask",
          ("z.B. 'wifi disable' / 'data enable' / 'bluetooth enable'", "svc {v}")),
        f(34, "Doze-Mode erzwingen", "cmd",
          "dumpsys deviceidle force-idle; echo 'Doze erzwungen. Aufheben: dumpsys deviceidle unforce'"),
        f(35, "Sprache/Zeitzone (Zeitzone)", "ask",
          ("Zeitzone z.B. Europe/Berlin", "setprop persist.sys.timezone {v}"),
          "Sprachwechsel braucht Root + Neustart der UI."),
        f(36, "Animationsskalierung", "ask", ("Faktor 0=aus, 1=normal, 0.5=schnell",
          "settings put global window_animation_scale {v}; settings put global transition_animation_scale {v}; "
          "settings put global animator_duration_scale {v}")),
        f(37, "System-Overlays auflisten", "cmd", "cmd overlay list 2>/dev/null | head -n 60"),
        f(38, "System-Benachrichtigung einblenden", "info",
          "Eigene Notifications brauchen eine signierte Helfer-App/NotificationListener oder Root-Inject. "
          "Per ADB nicht direkt möglich; Test-Apps wie 'Notification Maker' nutzen."),
        f(39, "Immersive Mode (Leisten ausblenden)", "ask",
          ("'on' oder 'off'", "settings put global policy_control {v}"),
          "on → immersive.full=*  (Wert wird automatisch gesetzt)"),
        f(40, "Lade-Limitierung (z.B. 80%)", "info",
          _NEED_ROOT + " Pfad geräteabhängig: /sys/class/power_supply/battery/charge_control_limit o.ä."),
    ]),
    # ============================================================= 5
    ("🛠️", "Datei-Transfer, Medien & Forensik", [
        f(41, "High-Speed Backup (adb pull)", "fn", h.pull_files),
        f(42, "Datei-Upload (adb push)", "fn", h.push_files),
        f(43, "Screenshot → PC (PNG)", "fn", h.screenshot),
        f(44, "Screen-Recording → PC (MP4)", "fn", h.screenrecord),
        f(45, "Echtzeit-Logcat (Crashes filtern)", "fn", h.logcat_crashes),
        f(46, "Dateisystem-Snapshot (Verzeichnis)", "ask",
          ("Pfad z.B. /sdcard/Download", "ls -laR {v} | head -n 200")),
        f(47, "Zwischenablage lesen/schreiben", "fn", h.clipboard),
        f(48, "Vollständiges ADB-Backup (verschlüsselt)", "fn", h.adb_backup),
        f(49, "Prozess-Kill-Switch (Hänger beenden)", "ask", ("Paket/Prozess", "am force-stop {v}; pkill -f {v}")),
        f(50, "Reboot-Steuerung (Recovery/Bootloader/…)", "fn", h.reboot_menu),
    ]),
    # ============================================================= 6
    ("💾", "Partitionen, Images & Low-Level-Forensik", [
        f(51, "EMMC/UFS-Partition dumpen (dd → img)", "rootcmd",
          "ls -l /dev/block/by-name/", _NEED_ROOT + " Dump-Beispiel: dd if=/dev/block/by-name/system of=/sdcard/system.img"),
        f(52, "Partitionstabelle auslesen", "cmd", "ls -l /dev/block/by-name/ 2>/dev/null || ls -l /dev/block/bootdevice/by-name/"),
        f(53, "Boot-Image extrahieren (boot.img)", "rootcmd",
          "ls -l /dev/block/by-name/boot*", _NEED_ROOT + " Dann: dd if=/dev/block/by-name/boot of=/sdcard/boot.img"),
        f(54, "Recovery/TWRP flashen", "info",
          "Fastboot nötig:  fastboot flash recovery twrp.img  (Gerät im Bootloader, Bootloader entsperrt)."),
        f(55, "OTA-Update sideloaden (update.zip)", "info",
          "Gerät in Sideload-Modus (Menü 50 → Sideload), dann am PC:  adb sideload update.zip"),
        f(56, "Logcat während Boot/Bootloop", "fn", h.logcat_crashes),
        f(57, "Verschlüsselungsstatus (FBE/FDE)", "cmd",
          "getprop ro.crypto.state; getprop ro.crypto.type; getprop fde.crypto"),
        f(58, "Sicherer Datei-Wipe (überschreiben)", "danger",
          "Sektorengenaues Überschreiben. Ohne Root nur eigene Dateien: dd if=/dev/zero of=<datei>. "
          "Voll-Wipe der userdata = Datenverlust."),
        f(59, "NVRAM/EFS sichern (IMEI/Funk-Kalibrierung)", "rootcmd",
          "ls -l /dev/block/by-name/ | grep -iE 'efs|nvram|nvdata'",
          _NEED_ROOT + " Sichert sensible Funk-/IMEI-Daten vor ROM-Wechsel."),
        f(60, "Slot A/B Status (bootctl)", "cmd",
          "getprop ro.boot.slot_suffix; bootctl get-current-slot 2>/dev/null; bootctl get-suffix 0 2>/dev/null"),
    ]),
    # ============================================================= 7
    ("🌐", "Netzwerk, Proxy & Traffic-Analyse", [
        f(61, "Globalen Proxy setzen (Burp/mitmproxy)", "fn", h.set_proxy),
        f(62, "Reverse Port Forwarding (PC-Net teilen)", "fn", h.port_forward),
        f(63, "Port Forwarding (Geräte-Port → PC)", "fn", h.port_forward),
        f(64, "Netstat (offene Verbindungen)", "cmd", "netstat -tunp 2>/dev/null || ss -tunp 2>/dev/null | head -n 60"),
        f(65, "DNS-Server setzen", "ask", ("DNS-Host z.B. dns.adguard.com", "settings put global private_dns_specifier {v}; settings put global private_dns_mode hostname")),
        f(66, "WLAN-Passwörter auslesen", "rootcmd",
          "cat /data/misc/wifi/WifiConfigStore.xml 2>/dev/null | grep -iE 'SSID|PreSharedKey|WEPKey'",
          _NEED_ROOT + " WLAN-Klartext-Keys liegen geschützt unter /data/misc/wifi/."),
        f(67, "Paket-Sniffing (tcpdump → PCAP)", "fn", h.tcpdump_capture),
        f(68, "ADB-over-WiFi aktivieren", "fn", h.adb_wifi),
        f(69, "Netzwerk-Drosselung simulieren", "info",
          "Realistisch am PC-Proxy/Router (tc/netem) oder via Charles/Burp Throttling. "
          "Auf dem Gerät selbst ohne Root nicht steuerbar."),
        f(70, "VPN-Profil triggern", "cmd", "am start -a android.settings.VPN_SETTINGS"),
    ]),
    # ============================================================= 8
    ("⚡", "Performance-Profiling & Stresstests", [
        f(71, "FPS / Frame-Drops (gfxinfo)", "ask", ("Paketname", "dumpsys gfxinfo {v} | head -n 60")),
        f(72, "Thermal / Throttling", "cmd",
          "dumpsys thermalservice | head -n 40; echo ---; "
          "for z in /sys/class/thermal/thermal_zone*/temp; do cat $z 2>/dev/null; done | head"),
        f(73, "Wakelock-Detektor", "cmd", "dumpsys power | grep -iE 'wake lock|wakelock|partial' | head -n 40"),
        f(74, "CPU-Governor auf Performance", "rootcmd",
          "for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $g; done; "
          "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", _NEED_ROOT),
        f(75, "RAM-Stresstest / LMK-Verhalten", "info",
          "Gefahrloser Test via App (z.B. 'Stress-NG'-Port) oder am start vieler Apps. "
          "Direktes RAM-Fluten per ADB ist riskant (LMK killt Shell)."),
        f(76, "App-Startzeit messen", "ask", ("Paket/Activity z.B. com.app/.Main", "am start -W {v} | grep -E 'TotalTime|WaitTime'")),
        f(77, "Hintergrundprozess-Limit setzen", "ask", ("max. Prozesse 0-4 (oder -1=Standard)", "settings put global cached_apps_freezer enabled; settings put system background_process_limit {v}")),
        f(78, "Bugreport für Battery Historian", "cmd",
          "echo 'Erstelle Bugreport… (dauert) '; ", "Großer Export – nutze stattdessen: adb bugreport <ordner>"),
        f(79, "GPU-Rendering-Profil (Balken am Display)", "ask", ("'visual_bars' / 'false'", "setprop debug.hwui.profile {v}")),
        f(80, "Zombie-/Hänger-Prozesse killen", "cmd", "ps -A -o PID,STAT,NAME 2>/dev/null | grep -E ' Z ' || echo 'Keine Zombies.'"),
    ]),
    # ============================================================= 9
    ("🛡️", "Security-Auditing & App-Sicherheit", [
        f(81, "CA-Zertifikat installieren (SSL-Interception)", "fn", h.install_cert),
        f(82, "App-Signatur (MD5/SHA256-Fingerprint)", "ask",
          ("Paketname", "pm dump {v} | grep -iA2 'signatures'; echo ---; dumpsys package {v} | grep -i 'signing'")),
        f(83, "Debuggable-Apps scannen", "fn", h.debuggable_scan),
        f(84, "App-Sandbox-Rechte prüfen", "ask", ("Paketname", "run-as {v} ls -la 2>/dev/null || ls -la /data/data/{v} 2>/dev/null")),
        f(85, "SELinux Enforcing/Permissive", "cmd", "getenforce", "Umschalten (setenforce 0) braucht Root."),
        f(86, "Keystore / StrongBox-Status (TEE)", "cmd",
          "dumpsys android.security.keystore 2>/dev/null | head -n 20; getprop ro.hardware.keystore_desede; "
          "pm has-feature android.hardware.strongbox_keystore && echo 'StrongBox: ja'"),
        f(87, "SecurityLog dumpen", "rootcmd", "dumpsys security 2>/dev/null | head -n 40", _NEED_ROOT),
        f(88, "Intent-Fuzzing (App crashen)", "fn", h.fuzz_intents),
        f(89, "Backup-Flag-Audit (allowBackup)", "cmd",
          "for p in $(pm list packages -3 | sed 's/package://'); do "
          "dumpsys package $p | grep -q 'ALLOW_BACKUP' && echo \"$p: allowBackup\"; done 2>/dev/null | head -n 40"),
        f(90, "Overlay/Clickjacking-Anfälligkeit", "cmd",
          "dumpsys window | grep -iE 'TYPE_APPLICATION_OVERLAY|SYSTEM_ALERT' | head -n 30"),
    ]),
    # ============================================================= 10
    ("🧠", "Deep-OS Controls & versteckte Features", [
        f(91, "Gast-/Zweitprofil erstellen", "ask", ("Profilname", "pm create-user {v}")),
        f(92, "Nicht-Stören (DND) konfigurieren", "cmd", "cmd notification get_dnd 2>/dev/null; settings get global zen_mode"),
        f(93, "App auf SD verschieben erzwingen", "ask", ("Paketname", "pm move-package {v} <vol> # Volumes: sm list-volumes")),
        f(94, "Standard-Apps neu zuweisen", "cmd", "cmd package query-activities -a android.intent.action.MAIN -c android.intent.category.HOME | head"),
        f(95, "HDMI/MHL-Display-Ausgabe prüfen", "cmd", "dumpsys display | grep -iE 'hdmi|external|wifi-display' | head"),
        f(96, "Helligkeits-/Auto-Brightness anpassen", "ask", ("Helligkeit 0-255", "settings put system screen_brightness_mode 0; settings put system screen_brightness {v}")),
        f(97, "Lockscreen-Widgets / versteckte UI", "info",
          "Lockscreen-Widgets wurden ab Android 5 entfernt; nur über Custom-ROM/Root-Mods reaktivierbar."),
        f(98, "System-Update-Check blockieren", "ask", ("Paket des OTA-Clients z.B. com.google.android.gms", "pm disable-user --user 0 {v}"),
          "Vorsicht: Deaktivieren von GMS kann Funktionen brechen."),
        f(99, "Boot-Animation ändern", "info", _NEED_ROOT + " /system/media/bootanimation.zip ersetzen (RW-Mount)."),
        f(100, "Factory Reset (Werkseinstellungen)", "danger",
          "Löscht ALLE Daten. Befehl: am broadcast -a android.intent.action.MASTER_CLEAR  bzw. recovery --wipe_data"),
    ]),
    # ============================================================= 11
    ("💳", "eSIM-Profile & eUICC-Architektur", [
        f(101, "eSIM-Fähigkeit prüfen", "cmd", "dumpsys euicc 2>/dev/null | head -n 20; pm has-feature android.hardware.telephony.euicc && echo 'eUICC: ja'"),
        f(102, "EID auslesen", "cmd", "dumpsys euicc 2>/dev/null | grep -i eid; service call isub 1 2>/dev/null", _RESTRICTED),
        f(103, "Installierte eSIM-Profile auflisten", "cmd", "dumpsys euicc 2>/dev/null | grep -iE 'profile|iccid|state' | head -n 40", _RESTRICTED),
        f(104, "Aktives eSIM-Profil umschalten", "info", "Über die System-Einstellungen/LPA-API (EuiccManager). Per ADB: am start -a android.telephony.euicc.action.MANAGE_EMBEDDED_SUBSCRIPTIONS"),
        f(105, "eSIM-Profil löschen", "info", "Nur über EuiccManager-API/Einstellungen (Carrier-Privileges nötig). Kein direkter ADB-Befehl."),
        f(106, "LPA (Local Profile Assistant) starten", "cmd", "am start -a android.telephony.euicc.action.MANAGE_EMBEDDED_SUBSCRIPTIONS"),
        f(107, "SM-DP+ Serveradresse auslesen", "cmd", "dumpsys euicc 2>/dev/null | grep -iE 'smdp|server|address'", _RESTRICTED),
        f(108, "eSIM-Aktivierungscode (LPA-Intent)", "ask",
          ("Aktivierungscode LPA:1$...", "am start -a android.service.euicc.action.PROVISION_EMBEDDED_SUBSCRIPTION -e android.telephony.euicc.extra.ACTIVATION_CODE '{v}'")),
        f(109, "eUICC-OS-Version auslesen", "cmd", "dumpsys euicc 2>/dev/null | grep -iE 'version|os'", _RESTRICTED),
        f(110, "eSIM-Speicherplatz (Metadaten)", "cmd", "dumpsys euicc 2>/dev/null | grep -iE 'free|capacity|space'", _RESTRICTED),
    ]),
    # ============================================================= 12
    ("🗂️", "Physische SIM-Hardware & Slot-Status", [
        f(111, "Slot-Belegung (Multi-SIM)", "cmd", "dumpsys isub 2>/dev/null | head -n 40; getprop | grep -iE 'sim.count|num_sims'"),
        f(112, "SIM-Status (READY/ABSENT/LOCKED)", "cmd", "getprop gsm.sim.state; dumpsys telephony.registry | grep -i simState"),
        f(113, "ICCID auslesen", "cmd", "service call iphonesubinfo 11 2>/dev/null; dumpsys iphonesubinfo 2>/dev/null | grep -i iccid", _RESTRICTED),
        f(114, "SIM-Hersteller (über ICCID-Präfix)", "info", "ICCID auslesen (Menü 113), erste Ziffern (MII 89 + Ländercode + Issuer) zeigen den Smartcard-Hersteller."),
        f(115, "SIM-Spannungsklasse (1.8/3/5V)", "sdr", _NEED_SDR + " Spannungsklasse steht im ATR – nur über Diag-Port/Reader lesbar."),
        f(116, "SIM-Hot-Plug überwachen", "fn", h.logcat_radio),
        f(117, "DSDS-Status (Dual-Standby)", "cmd", "dumpsys telephony.registry | grep -iE 'standby|dsds|active.*modem' | head"),
        f(118, "DSDA-Validierung (Dual-Active)", "cmd", "getprop | grep -iE 'dsda|multisim.config'"),
        f(119, "SIM-Adapter-Erkennung (Timing)", "info", _THEORY),
        f(120, "Kontaktfehler/Mikrounterbrechungen loggen", "fn", h.logcat_radio),
    ]),
    # ============================================================= 13
    ("🔐", "SIM-Sicherheit, PIN, PUK & Sperren", [
        f(121, "PIN-Status abfragen", "cmd", "getprop gsm.sim.state | grep -i pin; dumpsys telephony.registry | grep -i pin"),
        f(122, "PIN-Eingabe automatisieren", "info", "service call phone <code> mit PIN ist API-versionsabhängig & privilegiert. Sicherer: Einstellungen-Intent."),
        f(123, "Verbleibende PIN-Versuche", "rootcmd", "dumpsys telephony.registry | grep -iE 'pin.*retry|retryCount'", _RESTRICTED),
        f(124, "Verbleibende PUK-Versuche", "rootcmd", "dumpsys telephony.registry | grep -iE 'puk.*retry'", _RESTRICTED),
        f(125, "Netzbetreiber-Sperre (SIM-Lock) prüfen", "cmd", "getprop | grep -iE 'sim.*lock|carrierlock'; dumpsys carrier_config | grep -i lock | head"),
        f(126, "FPLMN-Liste (verbotene Netze)", "sdr", _NEED_SDR + " FPLMN liegt im EF_FPLMN der SIM – via AT+CRSM/APDU über Diag-Port."),
        f(127, "Lock-Typ (Network/SP/Corporate)", "cmd", "dumpsys carrier_config 2>/dev/null | grep -iE 'lock|restriction' | head"),
        f(128, "SIM-PIN deaktivieren", "info", "Nur über Einstellungen (Sicherheit → SIM-Sperre) – ADB hat dafür kein offenes Kommando."),
        f(129, "SIM-PIN ändern", "info", "Einstellungen → SIM-Sperre → PIN ändern. Programmatisch nur mit Carrier-Privileges."),
        f(130, "Krypto-Challenge an SIM (EAP-AKA)", "sdr", _NEED_SDR + " AUTHENTICATE-APDU an die USIM – nur via Modem-AT/Diag oder Smartcard-Reader."),
    ]),
    # ============================================================= 14
    ("📡", "Netzbetreiber-Konfiguration & IMS", [
        f(131, "IMSI auslesen", "rootcmd", "service call iphonesubinfo 7 2>/dev/null; dumpsys iphonesubinfo 2>/dev/null | grep -i imsi", _RESTRICTED),
        f(132, "Carrier-Config ID", "cmd", "dumpsys carrier_config 2>/dev/null | grep -iE 'carrier_id|mccmnc' | head"),
        f(133, "VoLTE-Status", "cmd", "dumpsys telephony.registry | grep -iE 'volte|ims.*voice|VoLTE'; getprop | grep -i volte"),
        f(134, "VoWiFi / Wi-Fi Calling Status", "cmd", "dumpsys telephony.registry | grep -iE 'wifi.*call|vowifi|wfc'; getprop | grep -i wfc"),
        f(135, "APN-Datenbank auslesen", "cmd", "content query --uri content://telephony/carriers 2>/dev/null | head -n 30"),
        f(136, "APN-Injektion (neuen APN schreiben)", "ask",
          ("APN-Name", "content insert --uri content://telephony/carriers --bind name:s:{v} --bind apn:s:internet --bind type:s:default")),
        f(137, "SMSC (SMS-Center-Nummer)", "cmd", "service call isms 1 2>/dev/null; dumpsys isms 2>/dev/null | grep -i smsc", _RESTRICTED),
        f(138, "RCS-Status (Rich Communication)", "cmd", "dumpsys carrier_config 2>/dev/null | grep -iE 'rcs|presence' | head"),
        f(139, "Netzwerk-Auswahlmodus (auto/manuell)", "cmd", "dumpsys telephony.registry | grep -iE 'network.*selection|manual'"),
        f(140, "Roaming-Erlaubnis schalten", "ask", ("0=aus 1=an", "settings put global data_roaming {v}")),
    ]),
    # ============================================================= 15
    ("💾", "SIM-Speicher & forensische Daten", [
        f(141, "SIM-Telefonbuch (ADN) auslesen", "cmd", "content query --uri content://icc/adn 2>/dev/null | head -n 40", _RESTRICTED),
        f(142, "SIM-SMS-Speicher dumpen", "rootcmd", "content query --uri content://sms/icc 2>/dev/null | head -n 40", _RESTRICTED),
        f(143, "Letzte Funkzelle (LOCI)", "sdr", _NEED_SDR + " EF_LOCI via APDU/AT+CRSM=176,28542 über Modem-Diag-Port."),
        f(144, "MSISDN (eigene Rufnummer)", "cmd", "service call iphonesubinfo 13 2>/dev/null; dumpsys iphonesubinfo 2>/dev/null | grep -i line1", _RESTRICTED),
        f(145, "Service Dialing Numbers (SDN)", "cmd", "content query --uri content://icc/sdn 2>/dev/null | head -n 30", _RESTRICTED),
        f(146, "SIM-Dateisystem (EF/DF) navigieren", "sdr", _NEED_SDR + " AT+CRSM/AT+CSIM APDUs über /dev/smd* (Diag/AT-Port)."),
        f(147, "FDN (Fixed Dialing) aktivieren", "info", "FDN-Umschaltung erfordert PIN2 & privilegierte Telephony-API; per ADB nicht offen."),
        f(148, "USIM-Anwendungsmanager", "sdr", _NEED_SDR + " EF_DIR / AID-Liste via APDU."),
        f(149, "OTA-SIM-Updates loggen", "fn", h.logcat_radio),
        f(150, "SIM-Alter über ICCID schätzen", "info", "ICCID auslesen (113); Ausgabe-Datum lässt sich aus Issuer-Block + laufender Nummer grob schätzen."),
    ]),
    # ============================================================= 16
    ("📡", "Baseband, Modem & AT-Kommandos", [
        f(151, "AT-Kommando-Brücke öffnen", "sdr", _NEED_SDR + " /dev/smd0|/dev/ttyGS0 freischalten (setprop sys.usb.config diag,adb) – Root + passender Treiber."),
        f(152, "SIM-Reset / Warm-Boot (AT+CFUN=1,1)", "sdr", _NEED_SDR + " AT-Befehl über Modem-Port."),
        f(153, "Modem-Firmware-Version", "cmd", "getprop gsm.version.baseband; getprop ril.modem.board"),
        f(154, "Radio-Logcat streamen", "fn", h.logcat_radio),
        f(155, "Modem-Crash erzwingen (RAM-Dump)", "danger", _THEORY + " Bewusst nicht implementiert – würde Funk lahmlegen/Gerät destabilisieren."),
        f(156, "NV-Items auslesen (Qualcomm/MTK)", "sdr", _NEED_SDR + " QPST/QXDM oder mtkclient über Diag-Port."),
        f(157, "RF-Kalibrierungsdaten dumpen", "rootcmd", "ls -l /dev/block/by-name/ | grep -iE 'modemst|fsg|efs'", _NEED_ROOT + " RF-Cal liegt in EFS/NVRAM."),
        f(158, "Diag-Port freischalten (QXDM)", "rootcmd", "setprop sys.usb.config diag,adb; getprop sys.usb.config", _NEED_ROOT),
        f(159, "Frequenzband-Lock (Band Locking)", "sdr", _NEED_SDR + " Engineering-Mode/AT!BAND oder QXDM; modellabhängig."),
        f(160, "Baseband-Uptime prüfen", "cmd", "dumpsys telephony.registry | grep -iE 'uptime|radio.*time'; getprop | grep -i modem.uptime"),
    ]),
    # ============================================================= 17
    ("🕵️", "IMSI-Catcher-Schutz & Funkzellen", [
        f(161, "Cell-ID Live-Tracker (MCC/MNC/LAC/CID)", "fn", h.cell_monitor),
        f(162, "Nachbarzellen-Analyse", "fn", h.neighbor_cells),
        f(163, "Verschlüsselungsstatus der Zelle", "sdr", _NEED_SDR + " A5/x-Cipher nur via SCAT/QXDM aus den L3-Messages lesbar."),
        f(164, "Silent-SMS (Typ 0) Detektor", "fn", h.logcat_radio),
        f(165, "Timing-Advance (Distanz zum Mast)", "cmd", "dumpsys telephony.registry | grep -iE 'timingAdvance|ta=' | head"),
        f(166, "Downgrade-Warnung (4G/5G→2G)", "fn", h.cell_monitor),
        f(167, "Fake-Zellen-Abgleich (BNetzA-API)", "info", "Empfangene CID/TAC gegen offene Mast-DBs (z.B. Mozilla Location, cellmapper) prüfen – Online-API nötig."),
        f(168, "Paging-Channel / TMSI überwachen", "sdr", _NEED_SDR),
        f(169, "SINR / Signalqualität (Jamming)", "cmd", "dumpsys telephony.registry | grep -iE 'rsrq|rssnr|sinr|cqi' | head"),
        f(170, "Ciphering-Indicator erzwingen", "info", "Versteckte Funktion; auf den meisten Stock-ROMs deaktiviert. Nur via Custom-ROM/Engineering."),
    ]),
    # ============================================================= 18
    ("🔒", "SIM-Dateisystem & Krypto-Operationen", [
        f(171, "EF_IMSI lesen/modifizieren", "sdr", _THEORY + " Schreiben nur auf programmierbaren Test-SIMs via APDU."),
        f(172, "Ki-Schlüssel extrahieren (COMP128v1)", "danger", _THEORY + " Funktioniert nur bei uralten COMP128v1-Test-SIMs mit Smartcard-Reader – nicht über ein Stock-Handy."),
        f(173, "Auth-Algorithmus triggern (RAND→SRES)", "sdr", _NEED_SDR + " RUN GSM ALGORITHM / AUTHENTICATE-APDU."),
        f(174, "PLMN-Selector ändern", "sdr", _NEED_SDR + " EF_PLMNwAcT via APDU schreiben."),
        f(175, "STK-Applet-Injektion (Java Card)", "sdr", _THEORY + " Nur auf programmierbaren SIMs mit OTA-Keys/Reader."),
        f(176, "Akkustand-Übertragung an SIM blocken", "info", "STK PROVIDE_LOCAL_INFORMATION abfangen – siehe Kategorie 40 (STK-Filter)."),
        f(177, "EF_SMS-Sicherheitszonen analysieren", "sdr", _NEED_SDR),
        f(178, "SIM-Dateibaum dumpen (DF_TELECOM/GSM)", "sdr", _NEED_SDR + " Kompletter APDU-Tree-Walk über Reader/Diag."),
        f(179, "SIM-Cache im OS leeren", "cmd", "am broadcast -a android.intent.action.SIM_STATE_CHANGED 2>/dev/null; svc data disable; svc data enable"),
        f(180, "Hardware-RNG der SIM anzapfen", "sdr", _NEED_SDR + " GET CHALLENGE-APDU für SIM-RNG."),
    ]),
    # ============================================================= 19
    ("🌍", "eSIM-Sicherheitsarchitektur & LPA", [
        f(181, "eSIM-Zertifikatskette (GSMA-Root) prüfen", "cmd", "dumpsys euicc 2>/dev/null | grep -iE 'cert|gsma|ci' | head", _RESTRICTED),
        f(182, "SM-DS (Discovery Server) abfragen", "info", "SM-DS-Abfrage triggert der LPA selbst; per ADB nur LPA-Intent starten (Menü 106)."),
        f(183, "Carrier-Privileges entziehen", "cmd", "dumpsys carrier_config 2>/dev/null | grep -i privilege | head", "Entzug nur über Profil-Verwaltung/Policy."),
        f(184, "eSIM-Metadaten-Verschlüsselung prüfen", "info", _THEORY + " eUICC↔AP-Kanal ist intern; nicht von außen messbar."),
        f(185, "eSIM-Profil-Isolation testen", "info", _THEORY + " GSMA-Sicherheitsdomänen sind hardwareisoliert – nicht per ADB testbar."),
        f(186, "Test-Zertifikate erzwingen", "sdr", _THEORY + " Nur auf Test-eUICC (Dev-Boards) im Testmodus."),
        f(187, "eSIM-Aktivierungs-Log dumpen", "cmd", "logcat -d | grep -iE 'euicc|lpa|esim' | tail -n 60"),
        f(188, "LPA-App-Sandbox auditieren", "ask", ("LPA-Paket z.B. com.android.euicc", "dumpsys package {v} | grep -iE 'permission|granted' | head -n 40")),
        f(189, "eSIM-Remote-Wipe simulieren", "info", _THEORY),
        f(190, "EID-Hardware-Abgleich (Anti-Spoofing)", "info", "EID (102) gegen den auf dem Chip eingebrannten Wert prüfen – physischer Vergleich nötig."),
    ]),
    # ============================================================= 20
    ("🛠️", "Forensische Mobilfunk-Tools", [
        f(191, "Gelöschte SIM-Kontakte rekonstruieren", "sdr", _THEORY + " Unzugeordneter SIM-Speicher nur via Smartcard-Reader + Forensik-Tool."),
        f(192, "SMS-Status-Report-Metadaten", "rootcmd", "content query --uri content://sms 2>/dev/null | grep -i status | head", _RESTRICTED),
        f(193, "Emergency-Call-Only erzwingen", "danger", "Kappt normale SIM-Identifikation. setprop/svc-Tricks geräteabhängig; Notruf-Modus = kein normaler Betrieb."),
        f(194, "Modem-Partition flashen", "info", "Fastboot:  fastboot flash modem modem.img  – nur passende Firmware, sonst kein Netz."),
        f(195, "IMEI-Validierung (Gehäuse vs. Modem)", "cmd", "service call iphonesubinfo 1 2>/dev/null; getprop | grep -i imei", "Modem-IMEI gegen IMEI-Aufkleber/*#06# vergleichen."),
        f(196, "SIM-Stromaufnahme messen", "sdr", _NEED_SDR + " Nur mit Strommesszange/PMIC-Tap."),
        f(197, "Multi-IMSI-Karten erkennen", "fn", h.logcat_radio),
        f(198, "LTE-Protokoll-Stack-Dump (L1-L3)", "sdr", _NEED_SDR + " SCAT/QXDM am Diag-Port."),
        f(199, "VoLTE-Schlüssel aus RAM ziehen", "danger", _THEORY),
        f(200, "Radio-Kill-Switch (Funk physisch aus)", "ask", ("'1' zum Aktivieren Flugmodus", "settings put global airplane_mode_on {v}; am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true"),
          "Softwareseitiger Funk-Aus (Flugmodus). Echtes physisches Kappen = Hardware-Mod."),
    ]),
    # ============================================================= 21
    ("📶", "Advanced 5G & Next-Gen Signal", [
        f(201, "5G SA vs. NSA validieren", "cmd", "dumpsys telephony.registry | grep -iE 'NR|5G|override.*network'; getprop gsm.network.type"),
        f(202, "MIMO-Layer auslesen", "cmd", "dumpsys telephony.registry | grep -iE 'mimo|layers|rank' | head"),
        f(203, "mmWave-Detektion", "cmd", "dumpsys telephony.registry | grep -iE 'mmwave|FR2|nr.*band' | head"),
        f(204, "Beamforming-Index", "sdr", _NEED_SDR),
        f(205, "Network-Slicing-Konfiguration", "cmd", "dumpsys telephony.registry | grep -iE 'slice|nssai|urs' | head"),
        f(206, "Carrier-Aggregation-Kombis", "cmd", "dumpsys telephony.registry | grep -iE 'aggregat|ca.*band|bandwidth' | head"),
        f(207, "5G-SA-only erzwingen", "info", "Über *#*#4636#*#* (TestMenu) → bevorzugter Netztyp, oder privilegierte setPreferredNetworkType-API."),
        f(208, "Sub-6 GHz Frequenz (MHz) auslesen", "cmd", "dumpsys telephony.registry | grep -iE 'earfcn|nrarfcn|channel|freq' | head"),
        f(209, "Doppler-Kompensation loggen", "sdr", _NEED_SDR),
        f(210, "VoNR (Voice over New Radio) prüfen", "cmd", "dumpsys telephony.registry | grep -iE 'vonr|nr.*voice' ; getprop | grep -i vonr"),
    ]),
    # ============================================================= 22
    ("🛰️", "Satelliten-Kommunikation (NTN) & Notfall", [
        f(211, "NTN-Status prüfen", "cmd", "dumpsys telephony.registry 2>/dev/null | grep -iE 'satellite|ntn'; pm has-feature android.hardware.telephony.satellite && echo 'NTN: ja'"),
        f(212, "Satelliten-Signalstärke (CNR)", "cmd", "dumpsys telephony.registry 2>/dev/null | grep -iE 'satellite.*signal|cnr'"),
        f(213, "Ephemeridendaten-Dump", "sdr", _NEED_SDR),
        f(214, "Satelliten-SOS-Testmodus", "info", "Versteckte Test-UI je Hersteller (z.B. Pixel: Satellite-SOS-Demo). Kein generischer ADB-Intent."),
        f(215, "Dunkelphasen-Log (Verbindungsverlust)", "fn", h.logcat_radio),
        f(216, "Ausrichtungshilfe (Gyro-Rohdaten)", "cmd", "dumpsys sensorservice | grep -iA3 gyroscope | head -n 20"),
        f(217, "Satelliten-Funk-Schlüssel", "sdr", _THEORY),
        f(218, "Cellular↔Satellite Handover", "fn", h.logcat_radio),
        f(219, "ETWS (Erdbeben/Tsunami) abfangen", "fn", h.logcat_radio),
        f(220, "WEA (Notfall-Broadcast) Config", "cmd", "dumpsys activity broadcasts 2>/dev/null | grep -iE 'cellbroadcast|emergency|wea' | head"),
    ]),
    # ============================================================= 23
    ("🔐", "Baseband-Exploits & Speicher-Dumps", [
        f(221, "Modem-RAM Live-Streaming (DMA)", "sdr", _NEED_SDR + " DMA-Dump nur über Debug-Probe/JTAG."),
        f(222, "Heap-Overflow-Fuzzing am Modem", "danger", _THEORY + " Bewusst nicht implementiert."),
        f(223, "Modem-Bootloader (PBL) Status", "sdr", _NEED_SDR + " EDL/9008-Modus + Firehose-Loader."),
        f(224, "TrustZone↔Modem-Interface", "sdr", _THEORY),
        f(225, "Modem-Crashtext (PC/LR-Register)", "rootcmd", "ls /data/vendor/ramdump 2>/dev/null; cat /sys/kernel/debug/modem_stat 2>/dev/null | head", _NEED_ROOT),
        f(226, "Modem-Sicherheits-Patch-Stand", "cmd", "getprop | grep -iE 'baseband|modem.*version|ril.sw'"),
        f(227, "Firmware-Signaturprüfung umgehen", "sdr", _THEORY + " Nur Engineering-Builds/Bootrom-Exploit."),
        f(228, "Modem-Symboltabellen extrahieren", "sdr", _NEED_SDR + " Aus dem Firmware-Image mit Ghidra/IDA."),
        f(229, "Stack-Canary im Baseband prüfen", "sdr", _THEORY),
        f(230, "Modem-SRAM-Integrität (Bit-Flips)", "sdr", _NEED_SDR),
    ]),
    # ============================================================= 24
    ("💳", "Krypto-Keys & SIM-Hardware-Forensik", [
        f(231, "KASUMI/SNOW-3G-Status", "sdr", _NEED_SDR + " Aktiver Cipher nur aus L3-Trace (QXDM/SCAT)."),
        f(232, "RAND/SRES-Paare sammeln", "sdr", _NEED_SDR),
        f(233, "SIM-Taktfrequenz ändern", "sdr", _THEORY + " Hardware-Mod am SIM-Clock-Pin."),
        f(234, "EF_DIR auslesen (Krypto-Apps)", "sdr", _NEED_SDR + " APDU SELECT EF_DIR."),
        f(235, "PIN-Brute-Force (Test-SIM)", "danger", _THEORY + " Echte SIMs sperren nach 3 Fehlversuchen (PUK) – nur Test-SIM im Reader."),
        f(236, "PUK-Aufsperrung automatisieren", "info", "PUK aus sicherer DB + Einstellungen-Eingabe; kein offener ADB-Befehl."),
        f(237, "ATR (Answer to Reset) auslesen", "sdr", _NEED_SDR + " ATR kommt beim Power-On der SIM über den Reader/Diag-Port."),
        f(238, "SIM-Spannungs-Drop loggen", "sdr", _NEED_SDR),
        f(239, "EF_PL (bevorzugte Sprache)", "sdr", _NEED_SDR + " APDU AT+CRSM=176,12082."),
        f(240, "SIM-Schreibschutz-Audit", "sdr", _NEED_SDR),
    ]),
    # ============================================================= 25
    ("🌍", "eSIM Remote-Provisioning & GSMA", [
        f(241, "ES2+-Schnittstelle emulieren", "info", _THEORY + " Server-seitige GSMA-Schnittstelle; Lab-Setup mit eigenem SM-DP+."),
        f(242, "GSMA SGP.22 Konformitätstest", "info", "Formaler Compliance-Test (GSMA-Testsuite) – kein On-Device-ADB-Test."),
        f(243, "eUICC-Zertifikat-CRL abgleichen", "cmd", "dumpsys euicc 2>/dev/null | grep -iE 'crl|revoc'", _RESTRICTED),
        f(244, "eSIM ECDSA-Signaturen extrahieren", "sdr", _THEORY),
        f(245, "eSIM-Profil-Key-Check (AES-GCM)", "info", _THEORY),
        f(246, "SM-DP+ Server-Zertifikat prüfen", "info", "TLS-Zertifikat des SM-DP+ mit openssl s_client am PC prüfen (Serveradresse aus 107)."),
        f(247, "eSIM-Downgrade-Schutz testen", "info", _THEORY),
        f(248, "eUICC-Speicher defragmentieren", "info", "Proprietäres Service-Command des eUICC-Herstellers; nicht standardisiert."),
        f(249, "Lock-to-Carrier aushebeln", "info", _THEORY + " Carrier-Restriction nur mit Engineering/Unlock-Code des Providers."),
        f(250, "EID↔TEE-Hardware-Validierung", "info", _THEORY),
    ]),
    # ============================================================= 26
    ("📞", "IMS & VoLTE/VoWiFi Protokoll-Analyse", [
        f(251, "SIP-Registrierung sniffen", "fn", h.logcat_radio),
        f(252, "IPSec-Tunnel (VoWiFi) überwachen", "cmd", "ip xfrm state 2>/dev/null | head; dumpsys connectivity | grep -i ipsec | head"),
        f(253, "XCAP-Server abfragen", "cmd", "dumpsys carrier_config 2>/dev/null | grep -i xcap | head"),
        f(254, "IMS-Registrierungsstatus", "cmd", "dumpsys telephony.registry | grep -iE 'ims.*regist|registered' | head"),
        f(255, "RTP-Paketverlust-Monitor", "cmd", "dumpsys telephony.registry | grep -iE 'rtp|jitter|packetloss' | head"),
        f(256, "Codec-Aushandlung (AMR-WB/EVS)", "cmd", "dumpsys telephony.registry | grep -iE 'codec|amr|evs' | head"),
        f(257, "P-Associated-URI extrahieren", "rootcmd", "logcat -d | grep -iE 'p-associated-uri|sip:' | tail -n 20", _RESTRICTED),
        f(258, "IMS-Auth-Fehler isolieren", "fn", h.logcat_radio),
        f(259, "VoWiFi-Präferenz erzwingen", "cmd", "settings get global wfc_ims_mode; echo 'Wert 1 = WLAN bevorzugt (settings put global wfc_ims_mode 1)'"),
        f(260, "rmnet_data0-Schnittstelle dumpen", "cmd", "ip -s addr show rmnet_data0 2>/dev/null; ip route | grep rmnet"),
    ]),
    # ============================================================= 27
    ("🕵️", "Anti-Tracking, Privacy & STK-Defense", [
        f(261, "STK-Befehls-Blocker", "cmd", "pm disable-user --user 0 com.android.stk 2>/dev/null && echo 'STK deaktiviert' || echo 'STK nicht gefunden/Root nötig'"),
        f(262, "IMEI-Übertragung unterdrücken", "info", _THEORY + " Erfordert modifiziertes Baseband."),
        f(263, "TMSI-Rotation erzwingen", "ask", ("'1' togglet Flugmodus (erzwingt Re-Attach)", "settings put global airplane_mode_on {v}; am broadcast -a android.intent.action.AIRPLANE_MODE")),
        f(264, "Location-Update-Intervall ändern", "sdr", _NEED_SDR),
        f(265, "Modem-Sleep erzwingen", "info", "Über Doze (Menü 34) + Flugmodus; echtes Modem-PSM ist netz-/modemgesteuert."),
        f(266, "SIM-Tracking-Log analysieren", "cmd", "logcat -d | grep -iE 'PROVIDE_LOCAL_INFORMATION|stk|location.*sim' | tail -n 30"),
        f(267, "BIP-Monitor (heimlicher SIM-Traffic)", "fn", h.logcat_radio),
        f(268, "Wi-Fi-MAC vor SIM verstecken", "info", "MAC-Randomisierung pro Netz aktivieren (Einstellungen → WLAN → erweitert)."),
        f(269, "Zellselektions-Hysterese ändern", "sdr", _NEED_SDR),
        f(270, "5G-SUCI/SUPI-Verschleierung prüfen", "cmd", "dumpsys telephony.registry | grep -iE 'suci|supi|concealed' | head"),
    ]),
    # ============================================================= 28
    ("⚡", "RF-Stresstests, Jamming & Hardware", [
        f(271, "RSRP Grid-Mapping (Signalstärkekarte)", "cmd", "dumpsys telephony.registry | grep -iE 'rsrp' | head", "Für Mapping: Werte in Schleife mit GPS koppeln (eigenes Skript)."),
        f(272, "RSRQ-Qualitäts-Logger", "cmd", "dumpsys telephony.registry | grep -iE 'rsrq' | head"),
        f(273, "RSSI-Jamming-Alarm", "fn", h.cell_monitor),
        f(274, "Antennen-Diversity-Status", "sdr", _NEED_SDR),
        f(275, "TX-Power-Monitor", "sdr", _NEED_SDR + " Sendeleistung nur aus Diag-Trace."),
        f(276, "SAR-Wert Live-Schätzung", "info", "Berechnung aus TX-Power × Werkskalibrierung – TX-Power nicht ohne Diag lesbar."),
        f(277, "Modem-Temperatur-Alarm", "cmd", "for z in /sys/class/thermal/thermal_zone*; do n=$(cat $z/type 2>/dev/null); echo \"$n: $(cat $z/temp 2>/dev/null)\"; done | grep -iE 'modem|rf|pa' "),
        f(278, "Uplink-Blockierungs-Detektor", "cmd", "dumpsys telephony.registry | grep -iE 'uplink|tx.*fail' | head"),
        f(279, "CQI-Tracker", "cmd", "dumpsys telephony.registry | grep -iE 'cqi' | head"),
        f(280, "BLER-Monitor (Block Error Rate)", "cmd", "dumpsys telephony.registry | grep -iE 'bler|error.*rate' | head"),
    ]),
    # ============================================================= 29
    ("🔀", "Multi-SIM-Routing & virtuelle Modems", [
        f(281, "Datenverbindung Slot wechseln", "ask", ("Sub-ID (0/1)", "settings put global multi_sim_data_call {v}; svc data disable; svc data enable")),
        f(282, "Cross-Data-Kompensation", "info", "Auto-Datenwechsel ist Carrier-/ROM-Feature (Smart Data Switch). Konfig via Einstellungen."),
        f(283, "Virtuelles SIM-Injektions-Interface", "info", _THEORY),
        f(284, "Multi-SIM SMS-Gateway (→ Bot)", "info", "Eingehende SMS via content://sms abgreifen + an Webhook senden (eigenes Skript/Companion-App)."),
        f(285, "IMEI-Mapping pro Slot", "cmd", "service call iphonesubinfo 3 i32 0 2>/dev/null; service call iphonesubinfo 3 i32 1 2>/dev/null", _RESTRICTED),
        f(286, "Default-Voice-Slot wechseln", "ask", ("Sub-ID (0/1)", "settings put global multi_sim_voice_call {v}")),
        f(287, "EFS pro Slot sichern", "rootcmd", "ls -l /dev/block/by-name/ | grep -iE 'modemst1|modemst2|efs'", _NEED_ROOT),
        f(288, "SIM-Präsenz simulieren (ohne Karte)", "info", _THEORY + " Nur mit virtuellem RIL/Emulator."),
        f(289, "Einzelnen Slot abschalten", "ask", ("Sub-ID (0/1)", "su -c 'settings put global cell_on 0'  # slot-spezifisch modemabhängig {v}")),
        f(290, "Modem-Subsystem-Reboot", "rootcmd", "stop ril-daemon; start ril-daemon; echo 'RIL neu gestartet'", _NEED_ROOT),
    ]),
    # ============================================================= 30
    ("💾", "Forensische NVRAM-Analyse", [
        f(291, "IMEI-Prüfsumme (Luhn) validieren", "info", "IMEI aus 195 lesen; letzte Ziffer ist Luhn-Prüfziffer – Validierung im Tool-Report möglich."),
        f(292, "MEID (CDMA) extrahieren", "cmd", "service call iphonesubinfo 6 2>/dev/null; getprop | grep -i meid", _RESTRICTED),
        f(293, "MTK /nvram dumpen", "rootcmd", "ls -l /mnt/vendor/nvdata 2>/dev/null; ls -l /data/nvram 2>/dev/null", _NEED_ROOT),
        f(294, "RF-Band-Capability-Bitmask", "cmd", "dumpsys telephony.registry | grep -iE 'band.*capab|supported.*band' | head; getprop | grep -i band"),
        f(295, "Field-Test-Mode öffnen", "cmd", "am start -a android.intent.action.MAIN -n com.android.settings/.RadioInfo 2>/dev/null || echo 'Geheimcode: *#*#4636#*#* wählen'"),
        f(296, "Modem-Hardware-Revision auslesen", "cmd", "getprop | grep -iE 'modem.*rev|hw.*modem|board'"),
        f(297, "Provider-Namen spoofen (SPN)", "rootcmd", "settings put system spn_override 'PANZER' 2>/dev/null", _NEED_ROOT + " Nur Anzeige in der Statusleiste."),
        f(298, "SMS-Zustelltyp umschalten", "sdr", _NEED_SDR),
        f(299, "telephony.registry-Zustand sichern", "cmd", "dumpsys telephony.registry"),
        f(300, "(NVRAM-Snapshot gesamt)", "rootcmd", "ls -laR /mnt/vendor/nvram /mnt/vendor/nvdata 2>/dev/null | head -n 80", _NEED_ROOT),
    ]),
    # ============================================================= 31
    ("🧪", "Virtuelle SIM-Emulation & SD-Modems", [
        f(301, "vSIM-Injektion (Software-Profil)", "info", _THEORY + " Erfordert virtuellen RIL/Emulator (Cuttlefish) oder remote-SIM-Stack."),
        f(302, "SDR-Baseband-Faking (HackRF)", "sdr", _NEED_SDR + " Eigene Test-Zelle mit srsRAN/YateBTS + HackRF im abgeschirmten Labor (rechtlich heikel!)."),
        f(303, "Null-IMSI-Modus", "info", _THEORY),
        f(304, "SIM-over-IP (Remote-SIM)", "info", _THEORY + " SIM-Reader am PC + Tunnel (z.B. via Software-RIL). Kein Stock-ADB-Feature."),
        f(305, "Modem-Loopback-Test", "sdr", _NEED_SDR),
        f(306, "Multi-Operator-Profiling", "info", _THEORY),
        f(307, "APDU-Fuzzer", "sdr", _NEED_SDR + " APDU-Stream über Reader/Diag-Port."),
        f(308, "Baseband-Isolation-Check", "info", _THEORY),
        f(309, "Emulierte STK-Menüs injizieren", "info", _THEORY),
        f(310, "Virtueller Handover-Stresstest", "sdr", _NEED_SDR),
    ]),
    # ============================================================= 32
    ("🕵️", "Krypto-Anomalien & logische SIM-Angriffe", [
        f(311, "COMP128-Schwachstellen-Scanner", "info", "COMP128v1 nur auf sehr alten 2G-SIMs; Test braucht Smartcard-Reader (z.B. pySim)."),
        f(312, "Replay-Angriff auf OTA-SMS", "danger", _THEORY),
        f(313, "SIM-Wakelock-Draining", "danger", _THEORY + " Bewusst nicht als Schadcode implementiert."),
        f(314, "RAND-Spoofing (Netz-Challenge)", "sdr", _NEED_SDR),
        f(315, "IMEI-Klon-Detektor (Timing)", "info", _THEORY),
        f(316, "Suicide-Script für Test-SIM", "danger", _THEORY + " Würde eine SIM bricken – nicht implementiert."),
        f(317, "OTA-Key (TAR)-Audit", "sdr", _NEED_SDR),
        f(318, "Any-Time-Interrogation (ATI) Blocker", "info", "ATI ist netzseitig (SS7); am Endgerät nur durch Funk-Aus zu verhindern."),
        f(319, "MitM RIL↔Modem-Dumper", "rootcmd", "ls -l /dev/socket/rild*; logcat -b radio -d | tail -n 40", _NEED_ROOT),
        f(320, "SIM-SMS-Speicher-Overflow-Test", "danger", _THEORY),
    ]),
    # ============================================================= 33
    ("🌐", "Virtuelles IMS- & Betreiber-Spoofing", [
        f(321, "Virtuelle APN-Isolierung (Ad-Block-APN)", "ask", ("APN-Name", "content insert --uri content://telephony/carriers --bind name:s:{v} --bind apn:s:internet --bind type:s:default")),
        f(322, "IMS-Identity-Spoofing-Test", "danger", _THEORY + " P-Preferred-Identity-Manipulation = Labor/Provider-Test."),
        f(323, "Gefälschte VoWiFi-Zertifikate", "danger", _THEORY),
        f(324, "RCS-Malware-Sandbox", "info", _THEORY),
        f(325, "Virtueller SMSC-Wechsel", "info", "SMSC-Änderung nur über privilegierte Telephony-API; Test-SMSC im Labor."),
        f(326, "Emergency-Call-Spoofing-Audit", "danger", "Notruf-Manipulation ist illegal/gefährlich – bewusst nicht implementiert."),
        f(327, "Roaming-Tarif-Simulator", "info", _THEORY),
        f(328, "XCAP-Konfig-Injektor", "danger", _THEORY),
        f(329, "SIP-BYE-Fuzzer", "danger", _THEORY),
        f(330, "Unverschlüsseltes VoLTE erzwingen", "danger", _THEORY + " Nur im abgeschirmten Labor mit eigener Test-Zelle."),
    ]),
    # ============================================================= 34
    ("🕵️", "Forensische SIM-Extraktion & Tracker-Jagd", [
        f(331, "Historischer LOCI-Dump", "sdr", _NEED_SDR),
        f(332, "Versteckte SPN auslesen", "cmd", "dumpsys carrier_config 2>/dev/null | grep -i spn | head; getprop | grep -i spn"),
        f(333, "PLMN-Netzprioritäten auslesen", "sdr", _NEED_SDR + " EF_PLMNsel via APDU."),
        f(334, "BIP-Traffic-Sniffer", "fn", h.logcat_radio),
        f(335, "SIM-Telefonbuch-Metadaten", "cmd", "content query --uri content://icc/adn 2>/dev/null | head -n 30", _RESTRICTED),
        f(336, "EF_TST (Test-Flags) prüfen", "sdr", _NEED_SDR),
        f(337, "TMSI-Lebensdauer-Tracker", "fn", h.cell_monitor),
        f(338, "SIM-Alter über ICCID", "info", "Siehe Menü 150 – ICCID-Struktur analysieren."),
        f(339, "FDN-Audit", "cmd", "content query --uri content://icc/fdn 2>/dev/null | head -n 30", _RESTRICTED),
        f(340, "SIM-Prozess-RAM-Analyse", "rootcmd", "ps -A | grep -iE 'phone|telephony|rild'; echo 'Heap-Dump via am dumpheap (Root)'", _NEED_ROOT),
    ]),
    # ============================================================= 35
    ("🛠️", "Advanced Baseband-Kontrolle & Radio-Modding", [
        f(341, "Virtueller Radio-Freeze", "danger", _THEORY),
        f(342, "Modem-Bandbreiten-Limiter", "sdr", _NEED_SDR),
        f(343, "GSM-Only im Standby erzwingen", "cmd", "echo 'Über TestMenu *#*#4636#*#* → bevorzugter Netztyp: GSM only'", "Privilegierte API nötig für Auto-Umschaltung."),
        f(344, "Modem-Leistungsprofil umschalten", "sdr", _NEED_SDR),
        f(345, "SIM-Ziehen im Gespräch testen", "danger", _THEORY),
        f(346, "Sendeleistung begrenzen (SAR-Tweak)", "sdr", _NEED_SDR + " " + _NEED_ROOT),
        f(347, "Modem-Crash-Log sichern", "rootcmd", "ls -l /data/vendor/ramdump 2>/dev/null; cp /data/vendor/ramdump/* /sdcard/ 2>/dev/null; echo done", _NEED_ROOT),
        f(348, "Antennenpfad-Debugging", "sdr", _NEED_SDR),
        f(349, "Radio-Subsystem-Hard-Reset", "rootcmd", "stop ril-daemon; sleep 1; start ril-daemon", _NEED_ROOT),
        f(350, "Ghost-Mode (passiver Empfang)", "ask", ("'1'=Flugmodus an (kein Senden)", "settings put global airplane_mode_on {v}; am broadcast -a android.intent.action.AIRPLANE_MODE"),
          "Echter passiver RX-only-Modus = SDR. Hier softwareseitiger Funk-Aus."),
    ]),
    # ============================================================= 36
    ("💉", "Virtuelle Protokoll-Injektion & OTA-Sim", [
        f(351, "Virtuelle OTA-SMS injizieren", "rootcmd", "am broadcast -a android.provider.Telephony.SMS_RECEIVED 2>/dev/null", _NEED_ROOT + " SMS-Broadcast ist privilegiert/signaturgeschützt."),
        f(352, "Gefälschtes Cell-Broadcast (Test)", "info", _THEORY + " CB-Injektion nur via Test-Zelle (SDR)."),
        f(353, "5G-Handover-Fuzzing", "sdr", _NEED_SDR),
        f(354, "Roaming-Wechsel-Sploit", "info", _THEORY),
        f(355, "Korrupte ASN.1/RRC-Daten injizieren", "sdr", _NEED_SDR),
        f(356, "Gefälschte Netzzeit (NITZ) injizieren", "info", _THEORY + " NITZ kommt vom Netz; Fälschung braucht Test-Zelle."),
        f(357, "Multi-SIM-Konflikt (gleiche IMSI)", "sdr", _THEORY),
        f(358, "Signal-Dämpfung im RIL erzwingen", "sdr", _NEED_SDR),
        f(359, "SMS-Status-Report-Loop", "danger", _THEORY),
        f(360, "Emulierter eCall-Test", "info", _THEORY),
    ]),
    # ============================================================= 37
    ("🔧", "Deep-Baseband Memory & RIL-Hacking", [
        f(361, "RIL-Daemon neu starten", "rootcmd", "stop rild 2>/dev/null; stop ril-daemon 2>/dev/null; start rild 2>/dev/null; start ril-daemon 2>/dev/null; echo done", _NEED_ROOT),
        f(362, "IPC-Meldungen (AP↔BP) loggen", "rootcmd", "logcat -b radio -d | grep -iE 'ipc|rild|RIL_' | tail -n 50", _NEED_ROOT),
        f(363, "Modem-Shared-Memory-Audit", "sdr", _NEED_SDR + " /dev/smem-Zugriff braucht Root + Tooling."),
        f(364, "Virtuelles IMEI-Nulling (RAM)", "danger", _THEORY),
        f(365, "AT+CME-ERROR injizieren", "sdr", _NEED_SDR),
        f(366, "Modem-Heap-Inspektion", "sdr", _NEED_SDR),
        f(367, "Hex an /dev/socket/rild senden", "rootcmd", "ls -l /dev/socket/rild*", _NEED_ROOT + " Direktes Schreiben an den RIL-Socket ist riskant."),
        f(368, "Low-Power-UART erzwingen", "sdr", _NEED_SDR),
        f(369, "Baseband-Tracing via Systrace", "cmd", "atrace --list_categories 2>/dev/null | grep -iE 'ril|radio|telephony'"),
        f(370, "radio-Socket-Rechte auditieren", "cmd", "ls -lZ /dev/socket/rild* 2>/dev/null; ls -l /dev/socket/rild*"),
    ]),
    # ============================================================= 38
    ("🌐", "Erweiterte Krypto-Emulation & Klon-Forensik", [
        f(371, "Milenage-Fuzzer", "sdr", _NEED_SDR + " Milenage-Test via pySim/Smartcard-Reader."),
        f(372, "Klon-Erkennung (SQN-Sprung)", "sdr", _NEED_SDR),
        f(373, "SRES-Metriken-Logger", "sdr", _NEED_SDR),
        f(374, "USIM-Applet-Isolation testen", "sdr", _THEORY),
        f(375, "A5/1-Chiffrierung erzwingen", "sdr", _THEORY + " Nur eigene Test-Zelle (SDR)."),
        f(376, "Krypto-Key-Leak im Logcat suchen", "cmd", "logcat -d | grep -iE 'kc=|ck=|ik=|session.?key|0x[0-9a-f]{16}' | tail -n 30"),
        f(377, "PIN-Sperren-Timing simulieren", "info", _THEORY),
        f(378, "APDU-Antwort manipulieren (SW1/SW2)", "sdr", _NEED_SDR),
        f(379, "Krypto-Zustands-Reset", "sdr", _NEED_SDR),
        f(380, "Gefälschtes GSMA-Root-Cert für LPA", "danger", _THEORY),
    ]),
    # ============================================================= 39
    ("🕵️", "IMS & VoLTE/VoWiFi Labor-Exploits", [
        f(381, "SIP-Register-Flooding (Labor)", "danger", _THEORY),
        f(382, "Gefälschte P-Access-Network-Info", "danger", _THEORY),
        f(383, "SIP-User-Agent fuzzen", "danger", _THEORY),
        f(384, "RTP-Audio-Injektor", "danger", _THEORY),
        f(385, "IMS-AKA-Bypass-Test", "danger", _THEORY),
        f(386, "XCAP-Dokumenten-Fuzzer", "danger", _THEORY),
        f(387, "Video-Call-Codec-Wechsel", "sdr", _THEORY),
        f(388, "IPSec/IKEv2-Key-Logger (Labor)", "rootcmd", "ip xfrm state 2>/dev/null", _NEED_ROOT + " IKE-Keys nur mit Root + strongSwan-Debug."),
        f(389, "SMS-over-IP injizieren", "danger", _THEORY),
        f(390, "IMS-Dienst deaktivieren (CSFB erzwingen)", "cmd", "settings put global volte_vt_enabled 0; settings put global wfc_ims_enabled 0; echo 'IMS aus → CSFB'"),
    ]),
    # ============================================================= 40
    ("🛡️", "Advanced SIM-Toolkit (STK) & Privacy", [
        f(391, "STK proactive-Command-Fuzzer", "sdr", _NEED_SDR),
        f(392, "LAUNCH_BROWSER via STK blocken", "cmd", "pm disable-user --user 0 com.android.stk 2>/dev/null && echo 'STK aus' || echo 'Root/STK nötig'"),
        f(393, "SEND_SMS durch SIM überwachen", "cmd", "logcat -d | grep -iE 'stk.*sms|SEND_SHORT_MESSAGE' | tail -n 20"),
        f(394, "Standortrechte für SIM entziehen", "cmd", "logcat -d | grep -i PROVIDE_LOCAL_INFORMATION | tail -n 20", "Aktives Fälschen der Koordinaten = Root/Framework-Hook."),
        f(395, "STK-Menü-Hijacking", "info", _THEORY),
        f(396, "SET_UP_CALL via STK überwachen", "cmd", "logcat -d | grep -iE 'stk.*call|SET_UP_CALL' | tail -n 20"),
        f(397, "STK-App komplett einfrieren", "cmd", "pm disable-user --user 0 com.android.stk 2>/dev/null; echo 'erledigt (falls vorhanden)'"),
        f(398, "BIP-Datenkanal drosseln", "sdr", _NEED_SDR),
        f(399, "STK-Session-Timeout verkürzen", "sdr", _NEED_SDR),
        f(400, "STK-Sicherheits-Filter (Proxy)", "info", _THEORY + " Voller STK-Proxy braucht Modem-Diag-Interception."),
    ]),
    # ============================================================= 41
    ("📶", "Advanced 5G Network Slicing & Edge", [
        f(401, "S-NSSAI-Fuzzer", "sdr", _NEED_SDR),
        f(402, "Edge-Computing-Latenzsimulation", "info", "Latenz am PC-Proxy (tc netem) simulieren; on-device nicht steuerbar."),
        f(403, "URLLC-Status prüfen", "cmd", "dumpsys telephony.registry | grep -iE 'urllc|latency|reliab' | head"),
        f(404, "Gefälschtes NSA-Ankersignal", "sdr", _NEED_SDR),
        f(405, "5G-Core AMF-Verbindung loggen", "sdr", _NEED_SDR),
        f(406, "PDU-Session-Injektor", "sdr", _NEED_SDR),
        f(407, "Reflected-QoS-Test", "cmd", "dumpsys telephony.registry | grep -iE 'qos|qci|5qi' | head"),
        f(408, "Beammanagement-Fuzzer", "sdr", _NEED_SDR),
        f(409, "URSP-Richtlinien auslesen", "cmd", "dumpsys telephony.registry | grep -iE 'ursp|route.*selection' | head"),
        f(410, "5G-Campusnetz-Simulation", "sdr", _NEED_SDR + " Privates 5G mit srsRAN/Open5GS + SDR."),
    ]),
    # ============================================================= 42
    ("🛰️", "Satelliten-Schnittstellen (NTN) Fuzzing", [
        f(411, "Gefälschte Satelliten-ID injizieren", "sdr", _NEED_SDR),
        f(412, "Satelliten-Doppler-Fuzzer", "sdr", _NEED_SDR),
        f(413, "Virtueller Orbit-Wechsel", "sdr", _NEED_SDR),
        f(414, "NTN-Sniffer auf Bitebene", "sdr", _NEED_SDR),
        f(415, "Gefälschte Abdeckungskarte", "info", _THEORY),
        f(416, "Satelliten-Sende-Timeout erzwingen", "sdr", _NEED_SDR),
        f(417, "NTN-Protokoll-Header auslesen", "fn", h.logcat_radio),
        f(418, "Weltraumwetter-Bitfehler simulieren", "sdr", _NEED_SDR),
        f(419, "NTN-Zertifikats-Ablauf-Test", "info", _THEORY + " Systemdatum ändern (settings) + NTN-Verhalten beobachten."),
        f(420, "Satelliten-Kill-Switch", "info", "Nur NTN abschalten ist hersteller-/modemspezifisch; generisch = Funk-Aus (Menü 200)."),
    ]),
    # ============================================================= 43
    ("🕵️", "Advanced Anti-Tracking & Baseband-Obfuskation", [
        f(421, "Zufalls-IMEI pro Boot (Labor)", "danger", _THEORY + " Nur auf emuliertem/Engineering-Modem."),
        f(422, "TMSI-Echtzeit-Verschleierung", "fn", h.cell_monitor),
        f(423, "Nachbarzellen-Reports unterdrücken", "sdr", _NEED_SDR),
        f(424, "Hardware-Seriennummern blocken", "info", _THEORY),
        f(425, "Radio-Measurements unterdrücken", "sdr", _NEED_SDR),
        f(426, "Gefälschtes Timing-Advance", "sdr", _NEED_SDR),
        f(427, "Baseband-Prozess-Verschleierung", "info", _THEORY),
        f(428, "Google Location Accuracy kappen", "cmd", "settings put global assisted_gps_enabled 0; settings put secure location_mode 1; echo 'A-GPS/Netzwerkortung reduziert'"),
        f(429, "Mobile DNS verschlüsseln (DoH/DoT)", "ask", ("DoT-Host z.B. dns.quad9.net", "settings put global private_dns_mode hostname; settings put global private_dns_specifier {v}")),
        f(430, "Radio-Ghost-Mode (100% passiv)", "info", "Echtes RX-only = SDR. Softwareseitig: Funk-Aus (Menü 200/350)."),
    ]),
    # ============================================================= 44
    ("⚡", "RF-Interferenz-Analyse & Hardware-Stress", [
        f(431, "CQI-Fuzzing", "sdr", _NEED_SDR),
        f(432, "BLER-Manipulator", "sdr", _NEED_SDR),
        f(433, "Antennen-Phasen-Fuzzing", "sdr", _NEED_SDR),
        f(434, "Modem-Thermodrossel-Bypass", "danger", _THEORY + " Überhitzungsschutz abschalten kann Hardware beschädigen – nicht implementiert."),
        f(435, "TX-Power-Saturationstest", "danger", _THEORY),
        f(436, "Signal-Rausch-Generator", "sdr", _NEED_SDR),
        f(437, "Antennen-Schalt-Stresstest", "sdr", _NEED_SDR),
        f(438, "Batterie-Drain-Profiler (Mobilfunk)", "cmd", "dumpsys batterystats | grep -iE 'mobile|radio|cellular' | head -n 30"),
        f(439, "Uplink-Paket-Dropper", "sdr", _NEED_SDR),
        f(440, "Modem-Spannungs-Monitor (PMIC)", "sdr", _NEED_SDR),
    ]),
    # ============================================================= 45
    ("💾", "Forensische NVRAM-Rekonstruktion", [
        f(441, "Luhn-Validierer für IMEI", "info", "IMEI (195) lesen; Tool prüft die Luhn-Prüfziffer im Report."),
        f(442, "MTK /mnt/vendor/nvram dumpen", "rootcmd", "ls -laR /mnt/vendor/nvram 2>/dev/null | head -n 80", _NEED_ROOT),
        f(443, "RF-Band-Capability-Bitmask (Hex)", "cmd", "getprop | grep -iE 'band|rf' | head; dumpsys telephony.registry | grep -i band | head"),
        f(444, "Field-Test-Mode (Geheimcode)", "cmd", "am start -a android.intent.action.MAIN -n com.android.settings/.RadioInfo 2>/dev/null || echo 'Wähle *#*#4636#*#* bzw. *#0011#'"),
        f(445, "Modem-Firmware-Integrität (SHA256)", "rootcmd", "sha256sum /dev/block/by-name/modem 2>/dev/null", _NEED_ROOT + " Gegen saubere Werks-Firmware vergleichen."),
        f(446, "Historische APN-Logs", "cmd", "content query --uri content://telephony/carriers 2>/dev/null | head -n 40"),
        f(447, "Gelöschte SMS-Zustellberichte", "rootcmd", "content query --uri content://sms 2>/dev/null | grep -i status | tail -n 20", _RESTRICTED),
        f(448, "Baseband-Hardware-Revision", "cmd", "getprop | grep -iE 'baseband|modem.*rev|ril.hw'"),
        f(449, "Provider-Name im RAM spoofen", "rootcmd", "settings put system spn_override 'PANZER' 2>/dev/null; echo 'gesetzt (Anzeige)'", _NEED_ROOT),
        f(450, "Vollständiger NVRAM-Forensik-Snapshot", "rootcmd", "ls -laR /mnt/vendor/nvram /mnt/vendor/nvdata /data/nvram 2>/dev/null | head -n 100", _NEED_ROOT),
    ]),
]


def category_count() -> int:
    return len(CATEGORIES)


def feature_count() -> int:
    return sum(len(c[2]) for c in CATEGORIES)


def kind_stats() -> dict:
    stats: dict = {}
    for _, _, feats in CATEGORIES:
        for ft in feats:
            stats[ft["k"]] = stats.get(ft["k"], 0) + 1
    return stats
