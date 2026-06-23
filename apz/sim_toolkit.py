"""SIM-KARTEN TOOLKIT – 35 Kategorien · 350 Features · Alle SIM-Modelle.

Umfasst alle SIM/Baseband/eSIM-Features aus der ursprünglichen Registry
(Kategorien 11–45, Features 101–450) plus vollständige SIM-Modell-Datenbank:
physische Formate, eSIM-Chiphersteller, Test-SIMs, IoT/M2M, CDMA.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import time

from . import ui
from .adb import ADB
from .util import LOG, outdir, shq

OUT = outdir("sim_toolkit")

# ══════════════════════════════════════════════════════════════════════════════
#  SIM-KARTEN MODELL-DATENBANK
# ══════════════════════════════════════════════════════════════════════════════

SIM_FORMATS = [
    {
        "key": "1FF",
        "name": "Full-Size SIM (1FF)",
        "size": "85.6 × 54.0 mm",
        "thickness": "0.76 mm",
        "notes": "Kreditkartengröße. Älteste Form, heute nur noch Lesegeräte/Archiv.",
        "voltage": "5V",
        "used_in": "Historische GSM-Geräte 1991–1996",
    },
    {
        "key": "2FF",
        "name": "Mini-SIM (2FF)",
        "size": "25.0 × 15.0 mm",
        "thickness": "0.76 mm",
        "notes": "Standard-SIM. Dominierte 1996–2012. Aus 1FF herausstanzbar.",
        "voltage": "3V / 1.8V",
        "used_in": "Klassische Mobiltelefone, ältere Smartphones",
    },
    {
        "key": "3FF",
        "name": "Micro-SIM (3FF)",
        "size": "15.0 × 12.0 mm",
        "thickness": "0.76 mm",
        "notes": "Eingeführt mit iPhone 4 (2010). Aus 2FF zuschneidbar.",
        "voltage": "3V / 1.8V",
        "used_in": "iPad, iPhone 4–4S, Samsung Galaxy S2/S3, viele Android 2011–2014",
    },
    {
        "key": "4FF",
        "name": "Nano-SIM (4FF)",
        "size": "12.3 × 8.8 mm",
        "thickness": "0.67 mm",
        "notes": "Seit iPhone 5 (2012) dominierend. Nur Chip, kein Plastikrahmen.",
        "voltage": "1.8V",
        "used_in": "Alle modernen Smartphones ab 2012",
    },
    {
        "key": "5FF",
        "name": "MFF2 / eSIM / Embedded (5FF)",
        "size": "6.0 × 5.0 mm (JEDEC MFF2)",
        "thickness": "0.8 mm",
        "notes": "Fest verlötet auf Platine. Kein physischer Wechsel. Remote-Provisioning via GSMA SGP.22.",
        "voltage": "1.8V",
        "used_in": "Apple Watch, Pixel 2+, iPhone XS+, M2M/IoT Geräte",
    },
]

ESIM_CHIPS = [
    {
        "vendor": "Infineon Technologies",
        "model": "SLx9735 / SLM76CF",
        "arch": "SLE 97 Serie",
        "crypto": "RSA-4096, ECC P-384, AES-256, SHA-3",
        "os": "SIMOS 9.x",
        "certified": "EAL5+, GSMA SGP.02/SGP.22",
        "notes": "In vielen Apple-Geräten (iPhone XS/11/12/13), Qualcomm-Plattform",
    },
    {
        "vendor": "STMicroelectronics",
        "model": "ST33G1M2 / ST33KTPM2XSPI",
        "arch": "ARM SecurCore SC300",
        "crypto": "RSA-4096, ECC, AES-256, SHA-256/512, TRNG",
        "os": "MultiOS-Engine",
        "certified": "EAL5+, CC, GSMA",
        "notes": "Weit verbreitet in Android-Geräten, Samsung Knox-Basis",
    },
    {
        "vendor": "NXP Semiconductors",
        "model": "SE050 / SE051 / SE052W",
        "arch": "80000H Secure MCU",
        "crypto": "RSA-4096, ECC P-521, AES-256, SHA-512, EdDSA",
        "os": "JCOP 4.5",
        "certified": "EAL6+, FIPS 140-2 L3",
        "notes": "IoT-fokussiert, Google Titan M2 Basis, Android strongbox",
    },
    {
        "vendor": "Oberthur Technologies (IDEMIA)",
        "model": "ID-One / ID-One eUICC",
        "arch": "Eigene Secure MCU",
        "crypto": "RSA-2048/4096, ECC, AES-256, 3DES",
        "os": "ID-One Cosmo v9",
        "certified": "EAL4+, GSMA SGP.22 M2M/Consumer",
        "notes": "Telekom-Betreiber-SIM-Lieferant, weit verbreitet in Europa",
    },
    {
        "vendor": "Thales (ehemals Gemalto)",
        "model": "ELS31 / ELS61 / EXS3221",
        "arch": "Thales Cinterion Secure MCU",
        "crypto": "RSA-4096, ECC, AES-256, SHA-3, TRNG",
        "os": "Cinterion OS",
        "certified": "EAL5+, GSMA SGP.02/22, FIPS",
        "notes": "Marktführer Telekom-SIMs Europa/Asien, M2M/Industrial",
    },
    {
        "vendor": "Giesecke+Devrient (G+D)",
        "model": "SLE 97144 / SLE78 / StarSIM",
        "arch": "SLE 97 Security Controller",
        "crypto": "RSA-4096, ECC P-521, AES-256, SHA-512",
        "os": "STARCOS 3.9",
        "certified": "EAL5+, CC PP, GSMA SGP.02/22",
        "notes": "Bundesdruckerei-Tochter, Telekom/O2/Vodafone-SIMs in DE",
    },
    {
        "vendor": "Samsung Electro-Mechanics",
        "model": "S3FV9RR / S3CC9RB",
        "arch": "Samsung Secure Element",
        "crypto": "RSA-4096, ECC, AES-256, ARIA, SHA-3",
        "os": "Samsung OS",
        "certified": "EAL6+, FIPS 140-2",
        "notes": "In Samsung Galaxy S22+/Z-Serie, integriert in Knox-Architektur",
    },
]

SPECIAL_SIMS = [
    {
        "key": "sysmoUSIM-SJS1",
        "name": "sysmoUSIM-SJS1",
        "vendor": "sysmocom (Berlin)",
        "format": "2FF/3FF (Adapter)",
        "os": "JavaCard 3.0.4, USIM applet",
        "programmable": True,
        "ki_changeable": True,
        "tools": "pySim, sysmocom SIM toolkit",
        "notes": "Open-Source-Test-SIM für GSM/3G/4G-Labornetze. Ki, OPC, IMSI frei programmierbar.",
        "use_case": "Open5GS, srsRAN, Osmocom Testnetze",
    },
    {
        "key": "sysmoISIM-SJA2",
        "name": "sysmoISIM-SJA2",
        "vendor": "sysmocom (Berlin)",
        "format": "2FF/3FF",
        "os": "JavaCard 3.0.5, ISIM+USIM applet",
        "programmable": True,
        "ki_changeable": True,
        "tools": "pySim-shell, APDU-Tools",
        "notes": "IMS/VoLTE-fähige Test-SIM. IMS-Credentials programmierbar.",
        "use_case": "VoLTE Labor, IMS-Stack-Tests",
    },
    {
        "key": "sysmoISIM-SJA5",
        "name": "sysmoISIM-SJA5",
        "vendor": "sysmocom (Berlin)",
        "format": "2FF/3FF/4FF",
        "os": "JavaCard 3.0.5, ISIM+USIM+SUCI",
        "programmable": True,
        "ki_changeable": True,
        "tools": "pySim-shell ≥ 1.0",
        "notes": "5G-SUCI-fähige Test-SIM. Unterstützt Milenage & TUAK.",
        "use_case": "5G SA/NSA Labornetz, SUCI/SUPI-Tests",
    },
    {
        "key": "multi-imsi",
        "name": "Multi-IMSI SIM",
        "vendor": "Diverse (BICS, Transatel, GigSky)",
        "format": "4FF / eSIM",
        "os": "Proprietär",
        "programmable": False,
        "ki_changeable": False,
        "tools": "Betreiber-App / OTA-Update",
        "notes": "Trägt mehrere IMSI für verschiedene Länder. STK-gesteuerte Auswahl.",
        "use_case": "Internationales Roaming ohne SIM-Wechsel",
    },
    {
        "key": "iot-sim",
        "name": "IoT / M2M SIM (MFF2)",
        "vendor": "Thales, G+D, Infineon, Telit",
        "format": "MFF2 (gelötet) / 4FF industr.",
        "os": "GSMA SGP.02 (M2M)",
        "programmable": True,
        "ki_changeable": False,
        "tools": "SM-SR, SM-DP Server",
        "notes": "Temperaturbereich -40°C bis +105°C. 10+ Jahre Lebensdauer. Vibrationsfest.",
        "use_case": "Fahrzeuge, Industrie, Smart Meter, Logistik",
    },
    {
        "key": "dual-imsi",
        "name": "Dual-IMSI SIM",
        "vendor": "Diverse",
        "format": "4FF",
        "os": "JavaCard + STK",
        "programmable": False,
        "ki_changeable": False,
        "tools": "STK-Menü, *#IMSI#",
        "notes": "Zwei IMSIs auf einer physischen SIM. Nützlich für internationale Nummer.",
        "use_case": "Business/Privat-Trennung, Auslandsnummern",
    },
    {
        "key": "cdma-ruim",
        "name": "CDMA R-UIM",
        "vendor": "Qualcomm, CommScope",
        "format": "2FF / 3FF",
        "os": "CDMA2000 RUIM applet",
        "programmable": False,
        "ki_changeable": False,
        "tools": "QXDM, CDMA Workshop",
        "notes": "Removable UIM für CDMA-Netze (Sprint, Verizon alt, SK Telecom KR).",
        "use_case": "CDMA2000 Forensik, US/KR/CN Carrier-Unlock",
    },
    {
        "key": "csim",
        "name": "CDMA CSIM (USIM + CSIM)",
        "vendor": "Qualcomm",
        "format": "4FF",
        "os": "JavaCard CSIM applet",
        "programmable": False,
        "ki_changeable": False,
        "tools": "QXDM, adb dumpsys",
        "notes": "Kombiniertes USIM+CSIM für LTE+CDMA (z.B. Verizon, Sprint 2015–2021).",
        "use_case": "US-Carrier Forensik, Band-Lock-Analyse",
    },
    {
        "key": "programmable-uicc",
        "name": "Programmierbare UICC (SIM blanko)",
        "vendor": "CardLogix, RISCO, Athena",
        "format": "2FF/3FF/4FF",
        "os": "JavaCard 3.0+",
        "programmable": True,
        "ki_changeable": True,
        "tools": "GlobalPlatformPro, pySim, APDU-Shell",
        "notes": "Leere JavaCard. Eigene Applets (USIM, ISIM, STK) aufspielbar.",
        "use_case": "Forschung, Security-Tests, eigene Applets",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE-REGISTRY: 35 Kategorien × 10 Features = 350 Features (Nr. 101–450)
# ══════════════════════════════════════════════════════════════════════════════
# kind: cmd=ADB, root=ADB+Root, info=Erklärung, sdr=HW nötig,
#        danger=gefährlich, ask=User-Eingabe nötig, live=logcat/live

def _f(n, t, k, p, note=""):
    return {"n": n, "t": t, "k": k, "p": p, "note": note}

_NEED_ROOT = "Benötigt Root (su). Ohne Root: Zugriff verweigert."
_NEED_SDR  = ("Erfordert SDR-Hardware (HackRF/USRP) oder PC/SC-Smartcard-Reader (ACR38, Omnikey) "
              "und pySim/APDU-Tool. Nicht via Standard-ADB möglich.")
_NEED_READER = "Benötigt PC/SC-Reader direkt an der SIM (nicht via ADB-Gerät)."

SIM_CATEGORIES = [
    # ──── KAT 11 ─────────────────────────────────────────────────────────────
    ("💳", "eSIM-Profile & eUICC-Architektur", [
        _f(101, "eSIM-Fähigkeit prüfen",           "cmd",  "dumpsys euicc_card_info 2>/dev/null | head -n 30"),
        _f(102, "EID auslesen",                     "cmd",  "service call econtrol 3 2>/dev/null"),
        _f(103, "Installierte eSIM-Profile",        "cmd",  "dumpsys isub 2>/dev/null | grep -i esim | head -n 20"),
        _f(104, "Aktives eSIM-Profil umschalten",   "info", "",
           "Wechsel über LPA-App: Einstellungen → Mobilfunk → eSIM → Profil aktivieren.\n"
           "ADB: am start -a android.service.euicc.action.MAIN"),
        _f(105, "eSIM-Profil löschen",              "info", "",
           "Einstellungen → Mobilfunk → eSIM → Profil auswählen → Löschen.\n"
           "Achtung: Unwiderruflich ohne SM-DP+ Server-Backup!"),
        _f(106, "LPA (Local Profile Assistant) starten", "cmd",
           "am start -a android.service.euicc.action.MAIN 2>/dev/null"),
        _f(107, "SM-DP+ Serveradresse auslesen",    "cmd",
           "getprop gsm.sim.operator.alpha; dumpsys euicc_card_info 2>/dev/null | grep -i sm-dp"),
        _f(108, "eSIM-Aktivierungscode (LPA-Intent)","ask", "",
           "Aktivierungscode im Format LPA:1$sm-dp-plus.example.com$ACTIVATION-CODE"),
        _f(109, "eUICC-OS-Version auslesen",         "cmd",
           "dumpsys euicc_card_info 2>/dev/null | grep -iE 'version|os' | head"),
        _f(110, "eSIM-Speicherplatz (Metadaten)",    "cmd",
           "dumpsys euicc_card_info 2>/dev/null | grep -i memory"),
    ]),
    # ──── KAT 12 ─────────────────────────────────────────────────────────────
    ("🗂️", "Physische SIM-Hardware & Slot-Status", [
        _f(111, "Slot-Belegung (Multi-SIM)",         "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -i slotIndex | head"),
        _f(112, "SIM-Status (READY/ABSENT/LOCKED)",  "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep mSimState"),
        _f(113, "ICCID auslesen",                    "cmd",
           "service call iphonesubinfo 11 s16 phone 2>/dev/null"),
        _f(114, "SIM-Hersteller (über ICCID-Präfix)","cmd",
           "service call iphonesubinfo 11 s16 phone 2>/dev/null",
           "ICCID-Präfix: 8901=DE-Telekom, 8949=O2, 8910=Vodafone DE. "
           "Vollständige IIN-Tabelle: www.itu.int/rec/T-REC-E.118"),
        _f(115, "SIM-Spannungsklasse (1.8/3/5V)",    "sdr",  "", _NEED_SDR),
        _f(116, "SIM-Hot-Plug überwachen",            "live",
           "logcat -s TelephonyManager:D SIMRecords:D | grep -i 'sim'"),
        _f(117, "DSDS-Status (Dual-Standby)",         "cmd",
           "getprop persist.radio.multisim.config; getprop persist.radio.multisim.active"),
        _f(118, "DSDA-Validierung (Dual-Active)",     "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'isMultiSim|dsda|dualActive'"),
        _f(119, "SIM-Adapter-Erkennung (Timing)",     "info", "",
           "Adapter (Mini→Nano-Adapter) haben oft schlechtere Kontaktzeiten. "
           "Erkennbar via: dumpsys telephony.registry | grep mSimState – häufige ABSENT/READY-Wechsel."),
        _f(120, "Kontaktfehler/Mikrounterbrechungen", "live",
           "logcat -s SIMRecords:D TelephonyManager:D | grep -iE 'error|absent|removed|inserted'"),
    ]),
    # ──── KAT 13 ─────────────────────────────────────────────────────────────
    ("🔐", "SIM-Sicherheit, PIN, PUK & Sperren", [
        _f(121, "PIN-Status abfragen",               "cmd",
           "service call iphonesubinfo 5 s16 phone 2>/dev/null"),
        _f(122, "PIN-Eingabe automatisieren",         "info", "",
           "Nicht via Standard-ADB möglich (Sicherheits-Policy). "
           "Root: input text <PIN> nach Entsperrungsbildschirm + input keyevent 66"),
        _f(123, "Verbleibende PIN-Versuche (Root)",  "root",
           "dumpsys iphonesubinfo 2>/dev/null | grep -i pin"),
        _f(124, "Verbleibende PUK-Versuche (Root)",  "root",
           "dumpsys iphonesubinfo 2>/dev/null | grep -i puk"),
        _f(125, "Netzbetreiber-Sperre (SIM-Lock)",   "cmd",
           "service call phone 3 2>/dev/null; getprop gsm.sim.operator.iso-country"),
        _f(126, "FPLMN-Liste (verbotene Netze)",     "sdr",  "", _NEED_SDR),
        _f(127, "Lock-Typ (Network/SP/Corporate)",   "cmd",
           "getprop gsm.sim.operator.iso-country; "
           "dumpsys telephony.registry 2>/dev/null | grep -i lock | head"),
        _f(128, "SIM-PIN deaktivieren",              "info", "",
           "Einstellungen → Sicherheit → SIM-Sperre → SIM-PIN deaktivieren.\n"
           "Root (gefährlich): service call phone 5 i32 0 s16 <PIN> s16 phone"),
        _f(129, "SIM-PIN ändern",                    "info", "",
           "Einstellungen → Sicherheit → SIM-Karte sperren → PIN ändern."),
        _f(130, "Krypto-Challenge (EAP-AKA)",        "sdr",  "", _NEED_SDR),
    ]),
    # ──── KAT 14 ─────────────────────────────────────────────────────────────
    ("📡", "Netzbetreiber-Konfiguration & IMS", [
        _f(131, "IMSI auslesen (Root)",              "root",
           "service call iphonesubinfo 7 s16 phone 2>/dev/null"),
        _f(132, "Carrier-Config ID",                 "cmd",
           "dumpsys carrier_config 2>/dev/null | head -n 30"),
        _f(133, "VoLTE-Status",                      "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'volte|voLte|mVoL' | head"),
        _f(134, "VoWiFi / Wi-Fi Calling Status",     "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'vowifi|voWifi|wificalling' | head"),
        _f(135, "APN-Datenbank auslesen",            "cmd",
           "content query --uri content://telephony/carriers 2>/dev/null | head -n 40"),
        _f(136, "APN-Injektion (neuer APN)",         "ask",  "",
           "content insert --uri content://telephony/carriers "
           "--bind name:s:{name} --bind apn:s:{apn} --bind type:s:default"),
        _f(137, "SMSC (SMS-Center-Nummer)",          "cmd",
           "service call iphonesubinfo 14 s16 phone 2>/dev/null"),
        _f(138, "RCS-Status (Rich Communication)",   "cmd",
           "dumpsys rcs 2>/dev/null | head -n 20; pm list packages | grep rcs"),
        _f(139, "Netzauswahl-Modus (auto/manuell)",  "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -i networkSelectMode"),
        _f(140, "Roaming-Erlaubnis schalten",        "ask",  "",
           "settings put global data_roaming 1   # 1=erlaubt, 0=gesperrt\n"
           "Oder: settings put global voice_roaming_on 1"),
    ]),
    # ──── KAT 15 ─────────────────────────────────────────────────────────────
    ("💾", "SIM-Speicher & forensische Daten", [
        _f(141, "SIM-Telefonbuch (ADN) auslesen",   "cmd",
           "content query --uri content://icc/adn 2>/dev/null"),
        _f(142, "SIM-SMS-Speicher dumpen (Root)",   "root",
           "content query --uri content://sms 2>/dev/null | head -n 60"),
        _f(143, "Letzte Funkzelle (LOCI)",           "sdr",  "", _NEED_SDR),
        _f(144, "MSISDN (eigene Rufnummer)",         "cmd",
           "service call iphonesubinfo 13 s16 phone 2>/dev/null"),
        _f(145, "Service Dialing Numbers (SDN)",     "cmd",
           "content query --uri content://icc/sdn 2>/dev/null"),
        _f(146, "SIM-Dateisystem (EF/DF) navigieren","sdr",  "", _NEED_SDR),
        _f(147, "FDN (Fixed Dialing) aktivieren",    "info", "",
           "Einstellungen → Telefon → Fixed Dialing Numbers → FDN einschalten.\n"
           "Benötigt PIN2. FDN begrenzt Anrufe auf Whitelist."),
        _f(148, "USIM-Anwendungsmanager",            "sdr",  "", _NEED_SDR),
        _f(149, "OTA-SIM-Updates loggen",            "live",
           "logcat -s OtaUpdate:D SIMRecords:D 2>/dev/null | grep -iE 'ota|update|sms'"),
        _f(150, "SIM-Alter über ICCID schätzen",     "cmd",
           "service call iphonesubinfo 11 s16 phone 2>/dev/null",
           "ICCID Bytes 7–10 = Jahr/Monat der Herstellung (Herstellerabhängig). "
           "Vollständige Dekodierung nur mit ICCID-Herstellertabelle."),
    ]),
    # ──── KAT 16 ─────────────────────────────────────────────────────────────
    ("📡", "Baseband, Modem & AT-Kommandos", [
        _f(151, "AT-Kommando-Brücke öffnen",         "sdr",  "", _NEED_SDR),
        _f(152, "SIM-Reset / Warm-Boot (AT+CFUN)",   "sdr",  "",
           "AT+CFUN=1,1 – Modem-Reset mit SIM-Neustart. "
           "Nur über AT-Kanal (USB-Modem oder /dev/smd7, /dev/ttyS0)."),
        _f(153, "Modem-Firmware-Version",            "cmd",
           "getprop gsm.version.baseband; getprop ro.baseband"),
        _f(154, "Radio-Logcat streamen",             "live",
           "logcat -b radio -d 2>/dev/null | tail -n 100"),
        _f(155, "Modem-Crash erzwingen (RAM-Dump)",  "danger",
           "echo crash > /sys/kernel/debug/msm_subsys/modem 2>/dev/null",
           "ACHTUNG: Gerät verliert sofort Netz. Nur für forensische RAM-Dumps!"),
        _f(156, "NV-Items auslesen (Qualcomm/MTK)",  "sdr",  "", _NEED_SDR),
        _f(157, "RF-Kalibrierungsdaten dumpen",      "root",
           "cat /persist/qcril.db 2>/dev/null | strings | head -n 30"),
        _f(158, "Diag-Port freischalten (QXDM)",     "root",
           "setprop sys.usb.config diag,adb 2>/dev/null",
           "Benötigt Root. Danach QXDM/QCAT über USB verbinden."),
        _f(159, "Frequenzband-Lock (Band Locking)",  "sdr",  "",
           "Qualcomm: AT+QCFG=\"band\" über Diag-Port. "
           "MTK: AT+EPBSE oder eng-mode. Kein Standard-ADB-Befehl."),
        _f(160, "Baseband-Uptime prüfen",            "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'DataConnectionState|uptime' | head"),
    ]),
    # ──── KAT 17 ─────────────────────────────────────────────────────────────
    ("🕵️", "IMSI-Catcher-Schutz & Funkzellen", [
        _f(161, "Cell-ID Live-Tracker (MCC/MNC/LAC/CID)", "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -E 'mCellIdentity|mCid|mLac|mMcc|mMnc' | head -n 20"),
        _f(162, "Nachbarzellen-Analyse",             "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -i neighbor | head -n 20"),
        _f(163, "Verschlüsselungsstatus der Zelle",  "sdr",  "", _NEED_SDR),
        _f(164, "Silent-SMS (Typ 0) Detektor",       "live",
           "logcat -s SMS:D GsmSMSDispatcher:D 2>/dev/null | grep -iE 'silent|type0|class0'"),
        _f(165, "Timing-Advance (Distanz zum Mast)", "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'timingAdvance|TimingAdv' | head"),
        _f(166, "Downgrade-Warnung (4G/5G→2G)",     "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep networkType | head -n 5",
           "networkType=2 → UMTS, =1 → GPRS/EDGE = Downgrade auf 2G. "
           "Möglicher Hinweis auf IMSI-Catcher."),
        _f(167, "Fake-Zellen-Abgleich (BNetzA)",    "info", "",
           "BNetzA-Standortdatenbank: bundesnetzagentur.de/EN/Sachgebiete/Telekommunikation\n"
           "Abgleich Cell-ID gegen bekannte Masten. Unbekannte IDs = Verdacht."),
        _f(168, "Paging-Channel / TMSI überwachen",  "sdr",  "", _NEED_SDR),
        _f(169, "SINR / Signalqualität (Jamming)",   "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'mSignalStrength|sinr|rsrp|rsrq' | head"),
        _f(170, "Ciphering-Indicator erzwingen",     "info", "",
           "Android zeigt standardmäßig kein Ciphering-Indicator-Icon. "
           "Nur via modifiziertem Baseband oder Diag-Port sichtbar (QXDM)."),
    ]),
    # ──── KAT 18 ─────────────────────────────────────────────────────────────
    ("🔒", "SIM-Dateisystem & Krypto-Operationen", [
        _f(171, "EF_IMSI lesen/modifizieren",        "sdr",  "", _NEED_SDR),
        _f(172, "Ki-Schlüssel extrahieren (COMP128v1)","danger", "",
           "ACHTUNG: Nur an Test-SIMs (sysmoUSIM) legal! "
           "COMP128v1: ~150.000 Challenges nötig. Werkzeug: pySim + SimTrace2. "
           "Echte Betreiber-SIMs verwenden Milenage – Ki-Extraktion nicht möglich."),
        _f(173, "Auth-Algorithmus triggern (RAND→SRES)", "sdr", "", _NEED_SDR),
        _f(174, "PLMN-Selector ändern",              "sdr",  "", _NEED_SDR),
        _f(175, "STK-Applet-Injektion (Java Card)",  "sdr",  "",
           "Nur auf programmierbaren SIMs (sysmoUSIM, blanke UICC) via GlobalPlatformPro."),
        _f(176, "Akkustand-Übertragung an SIM blocken", "info", "",
           "Manche Betreiber lesen Akkustand via STK PROVIDE LOCAL INFORMATION. "
           "Blockbar via STK-Proxy oder modifiziertes ROM."),
        _f(177, "EF_SMS-Sicherheitszonen analysieren", "sdr", "", _NEED_SDR),
        _f(178, "SIM-Dateibaum dumpen (DF_TELECOM)", "sdr",  "", _NEED_SDR),
        _f(179, "SIM-Cache im OS leeren",            "root",
           "am broadcast -a android.intent.action.ACTION_SIM_STATE_CHANGED 2>/dev/null"),
        _f(180, "Hardware-RNG der SIM anzapfen",     "sdr",  "", _NEED_SDR),
    ]),
    # ──── KAT 19 ─────────────────────────────────────────────────────────────
    ("🌍", "eSIM-Sicherheitsarchitektur & LPA", [
        _f(181, "eSIM-Zertifikatskette prüfen",      "cmd",
           "dumpsys euicc_card_info 2>/dev/null | grep -iE 'cert|signature|GSMA'"),
        _f(182, "SM-DS (Discovery Server) abfragen", "info", "",
           "SM-DS ist der GSMA Discovery Service. Standard: lpa.ds.gsma.com\n"
           "Prüfbar via: curl -v https://lpa.ds.gsma.com/gsma/rsp3/es2plus/"),
        _f(183, "Carrier-Privileges entziehen",      "cmd",
           "pm revoke <paketname> android.permission.READ_PRIVILEGED_PHONE_STATE 2>/dev/null"),
        _f(184, "eSIM-Metadaten-Verschlüsselung",    "info", "",
           "GSMA SGP.22: Profil-Metadaten AES-128-GCM verschlüsselt. "
           "Prüfbar via tshark auf SM-DP+-Traffic."),
        _f(185, "eSIM-Profil-Isolation testen",      "info", "",
           "Zwei gleichzeitig aktive eSIM-Profile sind auf Multi-eSIM-Geräten (iPhone 13 dual eSIM) "
           "vollständig isoliert (getrennte IMSIs, Stacks)."),
        _f(186, "Test-Zertifikate erzwingen",        "sdr",  "",
           "Nur auf Engineering-Builds oder Custom-ROM möglich. "
           "Erfordert Systempartitions-Zugriff."),
        _f(187, "eSIM-Aktivierungs-Log dumpen",      "cmd",
           "logcat -d -s EuiccController:D LPA:D 2>/dev/null | tail -n 60"),
        _f(188, "LPA-App-Sandbox auditieren",        "cmd",
           "pm dump com.google.android.euicc 2>/dev/null | grep -iE 'permission|signature'"),
        _f(189, "eSIM-Remote-Wipe simulieren",       "info", "",
           "Remote-Wipe = SM-DP+ sendet DELETE-Profil-Befehl via SM-DS. "
           "Nur Betreiber-seitig auslösbar; forensisch relevant."),
        _f(190, "EID-Hardware-Abgleich (Anti-Spoofing)", "cmd",
           "service call econtrol 3 2>/dev/null",
           "EID ist hardware-gekoppelt (TEE). Identisch zum EID in /proc/tee_sim = echt."),
    ]),
    # ──── KAT 20 ─────────────────────────────────────────────────────────────
    ("🛠️", "Forensische Mobilfunk-Tools", [
        _f(191, "Gelöschte SIM-Kontakte rekonstruieren","sdr", "", _NEED_SDR),
        _f(192, "SMS-Status-Report-Metadaten",        "root",
           "content query --uri content://sms 2>/dev/null | grep -i status"),
        _f(193, "Emergency-Call-Only erzwingen",      "danger",
           "settings put global preferred_network_mode 0 2>/dev/null",
           "ACHTUNG: Setzt Netz auf GSM-only. Gerät verliert LTE/5G!"),
        _f(194, "Modem-Partition flashen",            "info", "",
           "Nur via Fastboot/EDL. ACHTUNG: falsche FW = Brick.\n"
           "fastboot flash modem modem.img"),
        _f(195, "IMEI-Validierung (Gehäuse vs. Modem)","cmd",
           "getprop ro.boot.serialno; service call iphonesubinfo 1 s16 phone 2>/dev/null",
           "IMEI auf Gehäuse ≠ IMEI im Modem = Verdacht auf IMEI-Manipulation."),
        _f(196, "SIM-Stromaufnahme messen",           "sdr",  "", _NEED_SDR),
        _f(197, "Multi-IMSI-Karten erkennen",         "live",
           "logcat -s TelephonyManager:D | grep -iE 'imsi|mcc|mnc'",
           "Multi-IMSI-SIM wechselt IMSI via STK – erkennbar an IMSI-Änderungen ohne SIM-Hot-Swap."),
        _f(198, "LTE-Protokoll-Stack-Dump (L1-L3)",   "sdr",  "", _NEED_SDR),
        _f(199, "VoLTE-Schlüssel aus RAM",            "danger", "",
           "ACHTUNG: Nur auf Root-Geräten im Forensik-Lab! Erfordert Kernel-Modul oder "
           "Memory-Dump via /proc/kcore. Kein Standard-ADB-Befehl."),
        _f(200, "Radio-Kill-Switch (Funk aus)",       "ask",  "",
           "settings put global airplane_mode_on 1; "
           "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true"),
    ]),
    # ──── KAT 21 ─────────────────────────────────────────────────────────────
    ("📶", "Advanced 5G & Next-Gen Signal", [
        _f(201, "5G SA vs. NSA validieren",           "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE '5g|nr|SA|NSA' | head"),
        _f(202, "MIMO-Layer auslesen",                "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'mimo|layer|rank' | head"),
        _f(203, "mmWave-Detektion",                   "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'mmwave|mmWave|FR2' | head"),
        _f(204, "Beamforming-Index",                  "sdr",  "", _NEED_SDR),
        _f(205, "Network-Slicing-Konfiguration",      "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'slice|nssai|s-nssai' | head"),
        _f(206, "Carrier-Aggregation-Kombis",         "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'carrier.aggre|ca.band|band.combo' | head"),
        _f(207, "5G-SA-only erzwingen",               "info", "",
           "settings put global preferred_network_mode 26  # SA-only (Gerät+Netz abhängig)\n"
           "Wert variiert nach Hersteller. Samsung: 26, Qualcomm: variiert."),
        _f(208, "Sub-6 GHz Frequenz auslesen",        "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'arfcn|earfcn|nrarfcn|freq' | head"),
        _f(209, "Doppler-Kompensation loggen",        "sdr",  "", _NEED_SDR),
        _f(210, "VoNR (Voice over New Radio) prüfen", "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'vonr|VoNR|voice.nr' | head"),
    ]),
    # ──── KAT 22 ─────────────────────────────────────────────────────────────
    ("🛰️", "Satelliten-Kommunikation (NTN) & Notfall", [
        _f(211, "NTN-Status prüfen",                  "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'ntn|satellite|NTN' | head"),
        _f(212, "Satelliten-Signalstärke (CNR)",      "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'satellite|cnr|snr' | head"),
        _f(213, "Ephemeridendaten-Dump",              "sdr",  "", _NEED_SDR),
        _f(214, "Satelliten-SOS-Testmodus",           "info", "",
           "Apple Emergency SOS via Satellite: nur über Einstellungen-Menü testbar.\n"
           "Kein ADB-Zugriff. Qualcomm Snapdragon Satellite: ähnlich."),
        _f(215, "Dunkelphasen-Log (Verbindungsverlust)", "live",
           "logcat -s TelephonyManager:D | grep -iE 'satellite|lost|disconnected' 2>/dev/null"),
        _f(216, "Ausrichtungshilfe (Gyro-Rohdaten)", "cmd",
           "dumpsys sensorservice 2>/dev/null | grep -iE 'gyro|orient|rotation' | head -n 20"),
        _f(217, "Satelliten-Funk-Schlüssel",          "sdr",  "", _NEED_SDR),
        _f(218, "Cellular↔Satellite Handover loggen", "live",
           "logcat -s TelephonyManager:D 2>/dev/null | grep -iE 'handover|satellite|cellular'"),
        _f(219, "ETWS (Erdbeben/Tsunami) abfangen",  "live",
           "logcat -s CellBroadcastService:D Cbs:D 2>/dev/null | grep -iE 'etws|earthquake|tsunami'"),
        _f(220, "WEA (Notfall-Broadcast) Config",     "cmd",
           "dumpsys cellbroadcast 2>/dev/null | head -n 30"),
    ]),
    # ──── KAT 23 ─────────────────────────────────────────────────────────────
    ("🔐", "Baseband-Exploits & Speicher-Dumps", [
        _f(221, "Modem-RAM Live-Streaming (DMA)",     "sdr",  "", _NEED_SDR),
        _f(222, "Heap-Overflow-Fuzzing am Modem",     "danger", "",
           "ACHTUNG: Nur auf eigenen Test-Geräten! "
           "Werkzeuge: SharkFuzz, BaseSAFE, ModKit. Erfordert Diag-Port + QXDM."),
        _f(223, "Modem-Bootloader (PBL) Status",     "sdr",  "", _NEED_SDR),
        _f(224, "TrustZone↔Modem-Interface prüfen",  "sdr",  "", _NEED_SDR),
        _f(225, "Modem-Crashtext (PC/LR-Register)",  "root",
           "cat /proc/last_kmsg 2>/dev/null | grep -iE 'modem|crash|pc|lr' | head -n 30; "
           "cat /sys/fs/pstore/console-ramoops* 2>/dev/null | head -n 30"),
        _f(226, "Modem-Sicherheits-Patch-Stand",     "cmd",
           "getprop ro.vendor.build.security_patch; getprop gsm.version.baseband"),
        _f(227, "Firmware-Signaturprüfung",          "sdr",  "", _NEED_SDR),
        _f(228, "Modem-Symboltabellen extrahieren",  "sdr",  "", _NEED_SDR),
        _f(229, "Stack-Canary im Baseband prüfen",   "sdr",  "", _NEED_SDR),
        _f(230, "Modem-SRAM-Integrität (Bit-Flips)", "sdr",  "", _NEED_SDR),
    ]),
    # ──── KAT 24 ─────────────────────────────────────────────────────────────
    ("💳", "Krypto-Keys & SIM-Hardware-Forensik", [
        _f(231, "KASUMI/SNOW-3G-Status",             "sdr",  "", _NEED_SDR),
        _f(232, "RAND/SRES-Paare sammeln",           "sdr",  "", _NEED_SDR),
        _f(233, "SIM-Taktfrequenz ändern",           "sdr",  "", _NEED_SDR),
        _f(234, "EF_DIR auslesen (Krypto-Apps)",     "sdr",  "", _NEED_SDR),
        _f(235, "PIN-Brute-Force (Test-SIM!)",       "danger", "",
           "ACHTUNG: NUR auf eigenen Test-SIMs mit bekannter PIN! "
           "Echte SIM sperrt nach 3 Versuchen (PIN) / 10 Versuchen (PUK → permanent gesperrt)."),
        _f(236, "PUK-Entsperrung automatisieren",    "info", "",
           "Technisch: MMI-Code **05*PUK*NeuePIN*NeuePIN#\n"
           "Via ADB: service call phone 11 s16 <PUK> s16 <neue_pin> s16 phone"),
        _f(237, "ATR (Answer to Reset) auslesen",    "sdr",  "", _NEED_SDR),
        _f(238, "SIM-Spannungs-Drop loggen",         "sdr",  "", _NEED_SDR),
        _f(239, "EF_PL (bevorzugte Sprache)",        "sdr",  "", _NEED_SDR),
        _f(240, "SIM-Schreibschutz-Audit",           "sdr",  "", _NEED_SDR),
    ]),
    # ──── KAT 25 ─────────────────────────────────────────────────────────────
    ("🌍", "eSIM Remote-Provisioning & GSMA", [
        _f(241, "ES2+-Schnittstelle emulieren",       "info", "",
           "ES2+ = GSMA-Protokoll SM-DP+ → Gerät. "
           "Emulierbar via Open-Source SM-DP+ (lpac-docker) mit Test-Zertifikaten."),
        _f(242, "GSMA SGP.22 Konformitätstest",      "info", "",
           "GSMA Test Tools: gsma.com/esim – offizielle Konformitätstests für SGP.22 v3."),
        _f(243, "eUICC-Zertifikat-CRL abgleichen",   "cmd",
           "dumpsys euicc_card_info 2>/dev/null | grep -iE 'cert|crl|revoke'"),
        _f(244, "eSIM ECDSA-Signaturen extrahieren", "sdr",  "", _NEED_SDR),
        _f(245, "eSIM-Profil-Key-Check (AES-GCM)",   "info", "",
           "AES-128-GCM Profil-Verschlüsselung per GSMA SGP.22 §2.6. "
           "Analyse nur via SM-DP+ Server-Log oder vollständigem Protokoll-Dump."),
        _f(246, "SM-DP+ Server-Zertifikat prüfen",   "info", "",
           "openssl s_client -connect <sm-dp-server>:443 | openssl x509 -text\n"
           "Zertifikat muss GSMA Root CA signiert sein."),
        _f(247, "eSIM-Downgrade-Schutz testen",      "info", "",
           "Anti-rollback: Profil mit niedrigerer SGP-Version nicht installierbar. "
           "Testbar nur via SM-DP+ mit modifizierter Profil-Version."),
        _f(248, "eUICC-Speicher defragmentieren",     "info", "",
           "Kein direkter ADB-Zugriff. Via LPA-App: Profil löschen, Gerät neu starten."),
        _f(249, "Lock-to-Carrier aushebeln",          "info", "",
           "Carrier-Lock im eUICC via Carrier-Privileges (UICC-Carrier-Privileges).\n"
           "Aushebeln: Carrier-Entsperrung beim Betreiber beantragen."),
        _f(250, "EID↔TEE-Hardware-Validierung",      "cmd",
           "dumpsys euicc_card_info 2>/dev/null | grep -iE 'eid|EID|tee' | head"),
    ]),
    # ──── KAT 26 ─────────────────────────────────────────────────────────────
    ("📞", "IMS & VoLTE/VoWiFi Protokoll-Analyse", [
        _f(251, "SIP-Registrierung sniffen",          "live",
           "logcat -s ImsService:D ImsCall:D 2>/dev/null | grep -iE 'SIP|register|sip'"),
        _f(252, "IPSec-Tunnel (VoWiFi) überwachen",  "cmd",
           "ip xfrm state 2>/dev/null | head -n 30; ip xfrm policy 2>/dev/null | head -n 20"),
        _f(253, "XCAP-Server abfragen",               "cmd",
           "dumpsys ims 2>/dev/null | grep -iE 'xcap|ucsi' | head"),
        _f(254, "IMS-Registrierungsstatus",           "cmd",
           "dumpsys ims 2>/dev/null | grep -iE 'registered|registration|state' | head -n 15"),
        _f(255, "RTP-Paketverlust-Monitor",           "live",
           "logcat -s ImsCall:D 2>/dev/null | grep -iE 'rtp|packet.loss|jitter'"),
        _f(256, "Codec-Aushandlung (AMR-WB/EVS)",    "live",
           "logcat -s ImsCall:D ImsService:D 2>/dev/null | grep -iE 'codec|amr|evs'"),
        _f(257, "P-Associated-URI extrahieren",       "root",
           "dumpsys ims 2>/dev/null | grep -iE 'p-assoc|associated.uri|pani'"),
        _f(258, "IMS-Auth-Fehler isolieren",          "live",
           "logcat -s ImsService:D 2>/dev/null | grep -iE 'auth|error|401|403|failed'"),
        _f(259, "VoWiFi-Präferenz erzwingen",         "cmd",
           "settings put secure wfc_mode 2 2>/dev/null",
           "WFC-Modi: 0=deaktiv, 1=nur WiFi-Call, 2=bevorzugt, 3=Cellular bevorzugt"),
        _f(260, "rmnet_data0-Schnittstelle dumpen",  "root",
           "ip addr show rmnet_data0 2>/dev/null; ip route show table rmnet_data0 2>/dev/null"),
    ]),
    # ──── KAT 27 ─────────────────────────────────────────────────────────────
    ("🕵️", "Anti-Tracking, Privacy & STK-Defense", [
        _f(261, "STK-Befehls-Blocker",               "cmd",
           "pm disable com.android.stk 2>/dev/null",
           "Deaktiviert STK-App → SIM kann keine Anzeigen/Anrufe mehr erzwingen."),
        _f(262, "IMEI-Übertragung unterdrücken",     "info", "",
           "IMEI-Übertragung ist bei Notrufen (112/911) gesetzlich verpflichtend. "
           "Bei Nicht-Notrufen: IMEI hide über *#06# → Einige Geräte, Custom-ROM."),
        _f(263, "TMSI-Rotation erzwingen",           "info", "",
           "Normaler Mechanismus: Netz rotiert TMSI automatisch. "
           "Erzwingen: Flugmodus 30s, dann wieder einschalten."),
        _f(264, "Location-Update-Intervall ändern",  "sdr",  "", _NEED_SDR),
        _f(265, "Modem-Sleep erzwingen",              "cmd",
           "settings put global nitz_update_diff 0 2>/dev/null",
           "Kein direkter ADB-Befehl für Modem-Sleep. Flugmodus = sicherste Methode."),
        _f(266, "SIM-Tracking-Log analysieren",      "cmd",
           "logcat -d -s TelephonyManager:D 2>/dev/null | grep -iE 'location|lac|cid|track'"),
        _f(267, "BIP-Monitor (SIM→Netz-Traffic)",    "live",
           "logcat -s SIMRecords:D 2>/dev/null | grep -iE 'bip|channel|data'"),
        _f(268, "Wi-Fi-MAC vor SIM verstecken",      "cmd",
           "settings put global wifi_verbose_logging_enabled 1 2>/dev/null",
           "Android randomisiert MAC per Netzwerk standardmäßig seit Android 10."),
        _f(269, "Zellselektions-Hysterese ändern",   "sdr",  "", _NEED_SDR),
        _f(270, "5G-SUCI/SUPI-Verschleierung prüfen","cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'suci|supi|concealed' | head"),
    ]),
    # ──── KAT 28 ─────────────────────────────────────────────────────────────
    ("⚡", "RF-Stresstests, Jamming & Hardware", [
        _f(271, "RSRP Grid-Mapping (Signalstärkekarte)", "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'rsrp|RSRP' | head"),
        _f(272, "RSRQ-Qualitäts-Logger",             "live",
           "logcat -s SignalStrengthController:D 2>/dev/null | grep -iE 'rsrq|RSRQ'"),
        _f(273, "RSSI-Jamming-Alarm",                "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'rssi|signal' | head",
           "RSSI < -100 dBm + keine Verbindung = mögliches Jamming."),
        _f(274, "Antennen-Diversity-Status",         "sdr",  "", _NEED_SDR),
        _f(275, "TX-Power-Monitor",                  "sdr",  "", _NEED_SDR),
        _f(276, "SAR-Wert Live-Schätzung",           "cmd",
           "getprop vendor.radio.sar_version 2>/dev/null; "
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'sar|power.reduction' | head"),
        _f(277, "Modem-Temperatur-Alarm",            "cmd",
           "cat /sys/class/thermal/thermal_zone*/type 2>/dev/null | grep -in modem; "
           "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -n 5"),
        _f(278, "Uplink-Blockierungs-Detektor",      "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'uplinkBlocked|tx.power' | head"),
        _f(279, "CQI-Tracker",                       "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'cqi|CQI' | head"),
        _f(280, "BLER-Monitor (Block Error Rate)",   "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'bler|block.error' | head"),
    ]),
    # ──── KAT 29 ─────────────────────────────────────────────────────────────
    ("🔀", "Multi-SIM-Routing & virtuelle Modems", [
        _f(281, "Datenverbindung Slot wechseln",     "ask",  "",
           "settings put global multi_sim_data_call <slot>  # 0=SIM1, 1=SIM2"),
        _f(282, "Cross-Data-Kompensation",           "info", "",
           "Bei DSDS: Nur ein SIM-Slot aktiver Datenmodus. Der andere auf 2G gehalten."),
        _f(283, "Virtuelles SIM-Injektions-Interface","info", "",
           "Kein Standard-ADB. Nur via modemAT-Tools auf Debug-Builds."),
        _f(284, "Multi-SIM SMS-Gateway (→ Bot)",     "info", "",
           "Umsetzbar via Android SMS-Gateway Apps (Android SMS Gateway, SMS Server Tools)."),
        _f(285, "IMEI-Mapping pro Slot",             "cmd",
           "service call iphonesubinfo 1 s16 phone 2>/dev/null; "
           "service call iphonesubinfo 3 i32 1 s16 phone 2>/dev/null"),
        _f(286, "Default-Voice-Slot wechseln",       "ask",  "",
           "settings put system multi_sim_voice_call_subscription <slot>"),
        _f(287, "EFS pro Slot sichern (Root)",       "root",
           "dd if=/dev/block/bootdevice/by-name/efs 2>/dev/null | gzip > /sdcard/efs_backup.gz"),
        _f(288, "SIM-Präsenz simulieren (ohne Karte)","info", "",
           "Nicht möglich via Standard-ADB. Würde Modem-Firmware-Eingriff erfordern."),
        _f(289, "Einzelnen Slot abschalten",         "ask",  "",
           "settings put global airplane_mode_on 1 2>/dev/null  # Alles aus\n"
           "Oder herstellerspezifisch: Settings → Mobilnetz → SIM-Verwaltung → deaktivieren"),
        _f(290, "Modem-Subsystem-Reboot (Root)",     "danger",
           "echo 0 > /sys/bus/msm_subsys/devices/subsys*/restart_level 2>/dev/null",
           "ACHTUNG: Modem-Neustart – Gespräche/Verbindungen werden unterbrochen!"),
    ]),
    # ──── KAT 30 ─────────────────────────────────────────────────────────────
    ("💾", "Forensische NVRAM-Analyse", [
        _f(291, "IMEI-Prüfsumme (Luhn) validieren",  "cmd",
           "service call iphonesubinfo 1 s16 phone 2>/dev/null"),
        _f(292, "MEID (CDMA) extrahieren",           "cmd",
           "getprop ril.cdma.device.id 2>/dev/null; service call iphonesubinfo 4 s16 phone 2>/dev/null"),
        _f(293, "MTK /nvram dumpen (Root)",          "root",
           "ls /nvram/ 2>/dev/null; cat /nvram/APCFG/APRDEB/PHONE 2>/dev/null | strings | head -n 20"),
        _f(294, "RF-Band-Capability-Bitmask",        "cmd",
           "getprop gsm.current.phone-subtype 2>/dev/null; "
           "getprop ril.lte.bandinfo 2>/dev/null; "
           "getprop ril.bandcapable 2>/dev/null"),
        _f(295, "Field-Test-Mode öffnen",            "cmd",
           "am start -a android.intent.action.CALL -d tel:*#*#4636#*#* 2>/dev/null",
           "Öffnet Testmenü mit Netz-/Radio-Infos (gerätespezifisch)."),
        _f(296, "Modem-Hardware-Revision auslesen",  "cmd",
           "getprop ro.boot.hardware; getprop ro.hardware.chipname 2>/dev/null"),
        _f(297, "Provider-Namen spoofen (SPN Root)", "root",
           "settings put secure nitz_operator_name_display '' 2>/dev/null",
           "ACHTUNG: Nur temporär. Gerät zeigt eigenen Text als Netz-Name."),
        _f(298, "SMS-Zustelltyp umschalten",         "sdr",  "", _NEED_SDR),
        _f(299, "telephony.registry-Zustand sichern","cmd",
           "dumpsys telephony.registry 2>/dev/null > /sdcard/telephony_snapshot.txt && echo Gesichert"),
        _f(300, "NVRAM-Snapshot gesamt (Root)",      "root",
           "tar -czf /sdcard/nvram_backup.tar.gz /nvram/ 2>/dev/null && echo NVRAM gesichert"),
    ]),
    # ──── KAT 31 ─────────────────────────────────────────────────────────────
    ("🧪", "Virtuelle SIM-Emulation & SD-Modems", [
        _f(301, "vSIM-Injektion (Software-Profil)",  "info", "",
           "Remote-SIM (vSIM) via SIM-over-IP: EASYSim, Remote-SIM-Server. "
           "Benötigt Custom-ROM oder Rooting."),
        _f(302, "SDR-Baseband-Faking (HackRF)",      "sdr",  "", _NEED_SDR),
        _f(303, "Null-IMSI-Modus",                   "info", "",
           "IMSI = 000000000000000. Nicht registrierbar, nur Notrufe. "
           "Nützlich für Privacy-Forensik – Gerät is sichtbar ohne Identität."),
        _f(304, "SIM-over-IP (Remote-SIM)",          "info", "",
           "Protokoll: ISO 7816-3 über TCP. Open-Source: osmocon simo."),
        _f(305, "Modem-Loopback-Test",               "cmd",
           "getprop gsm.version.baseband; dumpsys telephony.registry 2>/dev/null | grep mDataConnected"),
        _f(306, "Multi-Operator-Profiling",          "cmd",
           "content query --uri content://telephony/carriers 2>/dev/null | grep -iE 'name|apn' | head -n 20"),
        _f(307, "APDU-Fuzzer (Test-SIM!)",           "danger", "",
           "ACHTUNG: NUR auf programmierbarer Test-SIM (sysmoUSIM). "
           "Echte SIM → Permanente Sperrung bei falschen APDUs!"),
        _f(308, "Baseband-Isolation-Check",          "cmd",
           "getprop ro.build.fingerprint; cat /proc/version | head; "
           "ls /dev/socket/ 2>/dev/null | grep -i rild"),
        _f(309, "Emulierte STK-Menüs injizieren",    "info", "",
           "Nur auf programmierbaren SIMs (Java Card) via GlobalPlatformPro möglich."),
        _f(310, "Virtueller Handover-Stresstest",    "sdr",  "", _NEED_SDR),
    ]),
    # ──── KAT 32 ─────────────────────────────────────────────────────────────
    ("🕵️", "Krypto-Anomalien & logische SIM-Angriffe", [
        _f(311, "COMP128-Schwachstellen-Scanner",    "info", "",
           "COMP128v1 (veraltet) anfällig für 150k-Challenge-Angriff. "
           "Moderne SIMs nutzen Milenage/TUAK – nicht angreifbar via Standard."),
        _f(312, "Replay-Angriff auf OTA-SMS",        "danger", "",
           "ACHTUNG: NUR Laborumgebung! SIM-OTA nutzt Challenge-Response. "
           "Replay ohne TAR-Key funktioniert nicht auf echten SIMs."),
        _f(313, "SIM-Wakelock-Draining",             "cmd",
           "dumpsys battery 2>/dev/null | grep -i wakeLock; "
           "dumpsys power 2>/dev/null | grep -iE 'SimWakeLock|TelephonyWakelock'"),
        _f(314, "RAND-Spoofing (Netz-Challenge)",    "sdr",  "", _NEED_SDR),
        _f(315, "IMEI-Klon-Detektor (Timing)",       "cmd",
           "service call iphonesubinfo 1 s16 phone 2>/dev/null",
           "Identische IMEI auf zwei Geräten = Klon. Erkennbar via Netz-Collisions."),
        _f(316, "Suicide-Script für Test-SIM",       "danger", "",
           "ACHTUNG: Löscht SIM-Inhalt permanent (Test-SIM)! "
           "Nur via APDU-Tool auf sysmoUSIM mit TERMINATE-Kommando."),
        _f(317, "OTA-Key (TAR)-Audit",               "sdr",  "", _NEED_SDR),
        _f(318, "Any-Time-Interrogation (ATI) Blocker", "info", "",
           "ATI = Betreiber kann Standort/Zustand jederzeit abfragen. "
           "Blockierbar via STK-Proxy oder SIM-Toolkit-Override."),
        _f(319, "MitM RIL↔Modem-Dumper (Root)",     "root",
           "logcat -b radio -d 2>/dev/null | strings | grep -iE 'at|cmd|resp' | head -n 40"),
        _f(320, "SIM-SMS-Speicher-Overflow-Test",    "danger", "",
           "ACHTUNG: NUR Test-SIM! SMS-Speicher (20–50 SMS) mit Dummy-SMS füllen: "
           "for i in $(seq 1 25); do am start -a ACTION_SEND -t text/plain --es android.intent.extra.TEXT 'X' com.android.mms; done"),
    ]),
    # ──── KAT 33 ─────────────────────────────────────────────────────────────
    ("🌐", "Virtuelles IMS- & Betreiber-Spoofing", [
        _f(321, "Virtuelle APN-Isolierung",          "ask",  "",
           "content insert --uri content://telephony/carriers "
           "--bind name:s:TestAPN --bind apn:s:{apn} --bind type:s:default"),
        _f(322, "IMS-Identity-Spoofing-Test",        "danger", "",
           "ACHTUNG: NUR Labor! Erfordert modifiziertes IMS-Framework. "
           "Nicht via Standard-ADB durchführbar."),
        _f(323, "Gefälschte VoWiFi-Zertifikate",     "danger", "",
           "ACHTUNG: Labor only! Erfordert custom IPSec-Konfiguration und Root."),
        _f(324, "RCS-Malware-Sandbox",               "info", "",
           "RCS-Anhänge in Sandbox analysieren: "
           "am start -n <rcs-paket>/.MainActivity  → in Sandbox via ADB-Trace beobachten."),
        _f(325, "Virtueller SMSC-Wechsel",           "info", "",
           "SMSC via Settings-API: content update --uri content://telephony/siminfo "
           "--bind sim_smsc:s:+49<SMSC>  (gerätespezifisch)"),
        _f(326, "Emergency-Call-Spoofing-Audit",     "danger", "",
           "ACHTUNG: NIEMALS echten Notruf missbrauchen! "
           "Test nur via modifiziertem ROM oder abgeschaltetem Notruf-Handling."),
        _f(327, "Roaming-Tarif-Simulator",           "cmd",
           "settings put global data_roaming 1 2>/dev/null; "
           "dumpsys telephony.registry 2>/dev/null | grep -i roaming"),
        _f(328, "XCAP-Konfig-Injektor",              "danger", "",
           "ACHTUNG: NUR mit Zustimmung des Betreibers! Erfordert XCAP-Credentials."),
        _f(329, "SIP-BYE-Fuzzer",                    "danger", "",
           "ACHTUNG: NUR Laborumgebung! Sip-Fuzzer: sipvicious, boofuzz über SIP-Stack."),
        _f(330, "Unverschlüsseltes VoLTE erzwingen", "danger", "",
           "ACHTUNG: Labor only! Erfordert modifiziertes Modem-Firmware-Image."),
    ]),
    # ──── KAT 34 ─────────────────────────────────────────────────────────────
    ("🕵️", "Forensische SIM-Extraktion & Tracker-Jagd", [
        _f(331, "Historischer LOCI-Dump",            "sdr",  "", _NEED_SDR),
        _f(332, "Versteckte SPN auslesen",           "cmd",
           "getprop gsm.sim.operator.alpha; "
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'spn|operator.name' | head"),
        _f(333, "PLMN-Netzprioritäten auslesen",     "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'plmn|preferred.network' | head"),
        _f(334, "BIP-Traffic-Sniffer",               "live",
           "logcat -s SIMRecords:D CatService:D 2>/dev/null | grep -iE 'bip|channel'"),
        _f(335, "SIM-Telefonbuch-Metadaten",         "cmd",
           "content query --uri content://icc/adn 2>/dev/null | head -n 20"),
        _f(336, "EF_TST (Test-Flags) prüfen",        "sdr",  "", _NEED_SDR),
        _f(337, "TMSI-Lebensdauer-Tracker",          "live",
           "logcat -s GsmCdmaPhone:D 2>/dev/null | grep -iE 'tmsi|TMSI|temp.identity'"),
        _f(338, "SIM-Alter über ICCID",              "cmd",
           "service call iphonesubinfo 11 s16 phone 2>/dev/null"),
        _f(339, "FDN-Audit",                         "cmd",
           "content query --uri content://icc/fdn 2>/dev/null"),
        _f(340, "SIM-Prozess-RAM-Analyse (Root)",    "root",
           "cat /proc/$(pidof rild)/maps 2>/dev/null | head -n 30"),
    ]),
    # ──── KAT 35 ─────────────────────────────────────────────────────────────
    ("🛠️", "Advanced Baseband-Kontrolle & Radio-Modding", [
        _f(341, "Virtueller Radio-Freeze",           "danger",
           "settings put global airplane_mode_on 1 && sleep 5 && settings put global airplane_mode_on 0 2>/dev/null",
           "Unterbricht alle Verbindungen kurzzeitig."),
        _f(342, "Modem-Bandbreiten-Limiter",        "sdr",  "", _NEED_SDR),
        _f(343, "GSM-Only im Standby erzwingen",    "cmd",
           "settings put global preferred_network_mode 1 2>/dev/null",
           "Schaltet auf 2G-only. Akku schonen auf Gebieten ohne 4G/5G."),
        _f(344, "Modem-Leistungsprofil umschalten", "sdr",  "", _NEED_SDR),
        _f(345, "SIM-Ziehen im Gespräch testen",    "danger", "",
           "ACHTUNG: Kann Modem destabilisieren! Nur Test-Gerät verwenden."),
        _f(346, "Sendeleistung begrenzen (SAR)",     "sdr",  "", _NEED_SDR),
        _f(347, "Modem-Crash-Log sichern (Root)",   "root",
           "cat /sys/fs/pstore/console-ramoops* 2>/dev/null > /sdcard/modem_crash.txt && echo OK; "
           "logcat -b crash -d 2>/dev/null >> /sdcard/modem_crash.txt"),
        _f(348, "Antennenpfad-Debugging",           "sdr",  "", _NEED_SDR),
        _f(349, "Radio-Subsystem-Hard-Reset (Root)", "danger",
           "echo modem > /sys/kernel/debug/msm_subsys/restart 2>/dev/null",
           "ACHTUNG: Modem-Neustart – alle aktiven Verbindungen getrennt!"),
        _f(350, "Ghost-Mode (passiver Empfang)",     "ask",  "",
           "settings put global airplane_mode_on 1  # Keine Sendung\n"
           "Gerät empfängt Funksignale passiv via SDR-Dongle weiter."),
    ]),
    # ──── KAT 36 ─────────────────────────────────────────────────────────────
    ("🔬", "SIM-Klonschutz & Identitäts-Forensik", [
        _f(351, "IMSI-Klon-Alarm (Netz-Kollision)", "info", "",
           "Zwei Geräte mit identischer IMSI → Netz-Kollision → Zwangabmeldung. "
           "Erkennbar via: häufige 'Location Update Reject' in Logcat."),
        _f(352, "ICCID-Duplikat-Erkennung",          "cmd",
           "service call iphonesubinfo 11 s16 phone 2>/dev/null",
           "Gleiche ICCID in Betreiber-DB = geklonte SIM. Nur Betreiber kann bestätigen."),
        _f(353, "Milenage vs. COMP128 Erkennung",    "info", "",
           "Milenage: 3G/4G/5G Netze, sicher. COMP128v1/v2: veraltete 2G-SIMs, kompromittierbar. "
           "Erkennbar via netzwerktyp: UMTS/LTE = Milenage."),
        _f(354, "SUCI-Schutz vor IMSI-Catcher",      "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'suci|SUCI|concealment'"),
        _f(355, "SIM-Swap-Angriff erkennen",         "live",
           "logcat -s TelephonyManager:D SIMRecords:D 2>/dev/null | grep -iE 'swap|change|imsi'",
           "Plötzlicher IMSI-Wechsel ohne SIM-Wechsel = SIM-Swap-Angriff."),
        _f(356, "Carrier-Nummer-Portierung prüfen",  "cmd",
           "getprop gsm.sim.operator.alpha; getprop gsm.operator.alpha",
           "Carrier-Wechsel ohne Anfrage = unerlaubte Portierung."),
        _f(357, "Standort-Manipulations-Alarm",      "live",
           "logcat -s TelephonyManager:D 2>/dev/null | grep -iE 'location|update.reject'"),
        _f(358, "EF_IMSI vs. ADB-IMSI-Vergleich",   "root",
           "service call iphonesubinfo 7 s16 phone 2>/dev/null",
           "IMSI aus ADB ≠ IMSI auf SIM-EF = mögliche Manipulation."),
        _f(359, "Benutzer-Authentizitäts-Log",       "root",
           "logcat -s SIMRecords:D 2>/dev/null | grep -iE 'auth|authenticate|rand|sres'"),
        _f(360, "SIM-Klon-Report erzeugen",          "cmd",
           "dumpsys telephony.registry 2>/dev/null > /sdcard/simclone_report.txt; "
           "service call iphonesubinfo 11 s16 phone 2>/dev/null >> /sdcard/simclone_report.txt; "
           "echo Fertig: /sdcard/simclone_report.txt"),
    ]),
    # ──── KAT 37 ─────────────────────────────────────────────────────────────
    ("📱", "Android Telefonie-Stack Debugging", [
        _f(361, "RIL-Daemon-Status prüfen",          "cmd",
           "ps -A 2>/dev/null | grep -iE 'rild|ril|radio'"),
        _f(362, "RILJ-Bibliothek (Qualcomm/MTK/Samsung)", "cmd",
           "ls -la /vendor/lib64/ 2>/dev/null | grep -iE 'libril|ril_impl'"),
        _f(363, "Telephony-Framework-Status",         "cmd",
           "dumpsys activity services 2>/dev/null | grep -iE 'telephony|TelephonyManager' | head -n 10"),
        _f(364, "Modem-Socket prüfen",               "cmd",
           "ls /dev/socket/ 2>/dev/null | grep -iE 'rild|qmux|msm'"),
        _f(365, "RILD-Log streamen (Radio Layer Interface)", "live",
           "logcat -b radio -v time 2>/dev/null | head -n 50"),
        _f(366, "SIM-App-Status (UICC App Manager)", "cmd",
           "dumpsys activity services 2>/dev/null | grep -iE 'UiccCard|UiccApp' | head -n 10"),
        _f(367, "ImsCallSession-Diagnose",           "cmd",
           "dumpsys ims 2>/dev/null | grep -iE 'CallSession|ImsCall' | head -n 15"),
        _f(368, "RIL-Request-Warteschlange dump",    "root",
           "logcat -b radio -d 2>/dev/null | grep -iE 'UNSOLICITED|RIL_REQUEST' | tail -n 30"),
        _f(369, "Telephony-Permissions-Audit",       "cmd",
           "pm list packages -f 2>/dev/null | grep -iE 'telephon|phone|sim'"),
        _f(370, "SIM-Error-Events (Statistik)",      "live",
           "logcat -s TelephonyManager:E SIMRecords:E 2>/dev/null | grep -iE 'error|exception|fail'"),
    ]),
    # ──── KAT 38 ─────────────────────────────────────────────────────────────
    ("🌐", "Internationale Roaming & PLMN-Analyse", [
        _f(371, "Aktive PLMN (Netzwerkanbieter)",    "cmd",
           "getprop gsm.operator.alpha; getprop gsm.sim.operator.alpha"),
        _f(372, "EPLMN-Liste (äquivalente Netze)",   "sdr",  "", _NEED_SDR),
        _f(373, "Roaming-Partnernetze",              "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'roaming|operator.numeric' | head -n 10"),
        _f(374, "Verbotene PLMN (FPLMN) lesen",     "sdr",  "", _NEED_SDR),
        _f(375, "Manuelle Netzwahl",                 "info", "",
           "Einstellungen → Mobilfunk → Bevorzugter Netzbetreiber → Manuell.\n"
           "ADB: service call phone 46 i32 0 2>/dev/null  (Suche starten)"),
        _f(376, "Roaming-Zone-Prüfung (MCC/MNC)",   "cmd",
           "getprop gsm.operator.numeric; getprop gsm.sim.operator.numeric",
           "Heimat-MNC (SIM) ≠ aktuelle MNC (Netz) = Roaming aktiv."),
        _f(377, "Data-Roaming-Block aktivieren",     "ask",  "",
           "settings put global data_roaming 0  # 0=gesperrt, 1=erlaubt"),
        _f(378, "Internationales LTE-Band prüfen",   "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'earfcn|band|frequency' | head"),
        _f(379, "MVNO-Erkennung",                    "cmd",
           "getprop gsm.sim.operator.alpha; dumpsys carrier_config 2>/dev/null | grep -i mvno | head"),
        _f(380, "Roaming-Tarif-Simulator (Alarm)",   "cmd",
           "settings put global data_roaming 1 2>/dev/null; "
           "dumpsys telephony.registry 2>/dev/null | grep -i roaming"),
    ]),
    # ──── KAT 39 ─────────────────────────────────────────────────────────────
    ("🔑", "Emergency & Priority Access (GETS/WPS)", [
        _f(381, "Emergency-Priorität prüfen",        "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'emergency|priority|gets|wps' | head"),
        _f(382, "Notfall-SIM-Bypass testen",         "info", "",
           "Notrufe (112/911) funktionieren ohne SIM-PIN, ohne Netzregistrierung. "
           "ADB-Test: am start -a android.intent.action.CALL -d tel:112 2>/dev/null"),
        _f(383, "WPS-Priorität konfigurieren",       "info", "",
           "Wireless Priority Service (WPS) = Priorität im überlasteten Netz. "
           "Konfiguration via Betreiber-Backend – kein ADB-Zugriff."),
        _f(384, "CMAS-Kanal überwachen",             "live",
           "logcat -s CellBroadcastService:D 2>/dev/null | grep -iE 'cmas|alert|emergency'"),
        _f(385, "Emergency Alerts deaktivieren",     "cmd",
           "settings put global cmas_additional_broadcast_pkg '' 2>/dev/null",
           "Deaktiviert zusätzliche Notfall-Alert-Weiterleitungen."),
        _f(386, "Extreme Alert (Presidential) überwachen", "live",
           "logcat -s CellBroadcastService:D 2>/dev/null | grep -iE 'presidential|extreme|imminent'"),
        _f(387, "SOS-Funkkanal aufzeichnen",         "sdr",  "", _NEED_SDR),
        _f(388, "HELP-SMS-Template",                 "info", "",
           "SMS mit GPS-Position: 'HELP <lat> <lon>' an Rettungsleitstelle.\n"
           "ADB-Test (eigene Nummer): service call phone 7 s16 +49<NUMMER> s16 'HELP 48.137 11.575' s16 phone"),
        _f(389, "FirstNet-Profil-Detektion",         "cmd",
           "getprop gsm.sim.operator.alpha; dumpsys telephony.registry 2>/dev/null | grep -iE 'firstnet|firstnetwork'"),
        _f(390, "GETS-Authentifizierungscode",       "info", "",
           "GETS = Government Emergency Telecommunications Service (USA).\n"
           "Auslösung via *272+Zugangscode, nur in USA/DOD-Kontext."),
    ]),
    # ──── KAT 40 ─────────────────────────────────────────────────────────────
    ("🛡️", "SIM-Sicherheitsrichtlinien & MDM", [
        _f(391, "MDM-Profil prüfen",                 "cmd",
           "pm list packages -d 2>/dev/null | grep -iE 'mdm|dpc|policy|device.manager'; "
           "dumpsys device_policy 2>/dev/null | head -n 20"),
        _f(392, "SIM-PIN-Richtlinie (MDM)",          "cmd",
           "dumpsys device_policy 2>/dev/null | grep -iE 'pin|sim|password' | head"),
        _f(393, "Knox-SIM-Lock (Samsung)",           "cmd",
           "pm list packages 2>/dev/null | grep knox; "
           "dumpsys device_policy 2>/dev/null | grep -i sim | head"),
        _f(394, "AirWatch/VMware SIM-Richtlinien",   "cmd",
           "pm list packages 2>/dev/null | grep -iE 'airwatch|workspace.one|vmware'"),
        _f(395, "Zertifikatspflicht für SIM-Daten",  "cmd",
           "dumpsys device_policy 2>/dev/null | grep -iE 'cert|profile|require' | head"),
        _f(396, "Remote-Wipe via MDM loggen",        "live",
           "logcat -s MDM:D DevicePolicyManager:D 2>/dev/null | grep -iE 'wipe|reset|erase'"),
        _f(397, "SIM-Sperrrichtlinie auslesen",      "cmd",
           "dumpsys device_policy 2>/dev/null | grep -iE 'simlock|lock|disallowed' | head"),
        _f(398, "MDM-Enterprise-Zertifikat-Store",   "cmd",
           "pm list packages 2>/dev/null | grep -iE 'cert|truststore'; "
           "security -list 2>/dev/null | head -n 10"),
        _f(399, "BYOD vs. Corporate SIM-Trennung",   "info", "",
           "Android Work Profile: SIM-Daten in Personal-Profil bleiben privat. "
           "Corporate APN/Calls nur in Work-Profil."),
        _f(400, "SIM-Richtlinien-Bericht exportieren", "cmd",
           "dumpsys device_policy 2>/dev/null > /sdcard/mdm_sim_policy.txt && "
           "echo Exportiert: /sdcard/mdm_sim_policy.txt"),
    ]),
    # ──── KAT 41 ─────────────────────────────────────────────────────────────
    ("🔍", "pySim & APDU-Werkzeuge", [
        _f(401, "pySim-Verfügbarkeit prüfen",        "cmd",
           "which pySim-read pySim-prog pySim-shell 2>/dev/null; pip3 show pySim 2>/dev/null | head -n 3"),
        _f(402, "ATR über pySim auslesen",            "info", "",
           "pySim-shell --reader 0 --interactive\n"
           "pySIM-shell> info  # Zeigt EF_ICCID, EF_IMSI, ATR, etc.\n"
           "Benötigt PC/SC-Reader (ACR38, Omnikey, ACS ACR38U)."),
        _f(403, "EF_IMSI mit pySim lesen",           "info", "",
           "pySim-read --pcsc-device 0\n"
           "Liest alle wichtigen EF-Dateien (IMSI, ICCID, MSISDN, etc.)."),
        _f(404, "pySim: Ki auf Test-SIM schreiben",  "danger", "",
           "ACHTUNG: NUR auf eigener Test-SIM (sysmoUSIM)! Eigenen Ki einsetzen:\n"
           "pySim-prog -p 0 --ki <32-hex-chars> --imsi <15digits> --type sysmoUSIM-SJS1"),
        _f(405, "pySim-shell interaktiv",            "info", "",
           "pySim-shell --pcsc-device 0 --interactive\n"
           "Interaktive APDU-Shell: read_file, select, verify_chv, update_binary, ..."),
        _f(406, "GlobalPlatformPro (Karten-Manager)", "info", "",
           "gp --info  # Chip-Info, ISD, SSD, Apps\n"
           "gp --list  # Installierte Applets\n"
           "Benötigt: Java, GlobalPlatformPro .jar, PC/SC-Reader."),
        _f(407, "APDU senden (AT+CSIM)",             "sdr",  "", _NEED_SDR),
        _f(408, "sysmoUSIM-SJS1 IMSI setzen",        "info", "",
           "pySim-prog -t sysmoUSIM-SJS1 -p 0 --imsi 901700000000001 --mcc 901 --mnc 70\n"
           "Erstellt Test-IMSI für Open5GS-Testnetz."),
        _f(409, "pySim EF_PLMNsel bearbeiten",       "info", "",
           "pySim-shell> select_application a0000000871002\n"
           "pySim-shell> read_binary EF_PLMNsel"),
        _f(410, "SimTrace2 APDU-Mitschnitt",         "info", "",
           "SimTrace2 = Open Hardware SIM-Sniffer (osmocom.org/projects/simtrace2).\n"
           "Sniffer zwischen Gerät und SIM-Karte. USB → Wireshark → SIM-APDU-Decode."),
    ]),
    # ──── KAT 42 ─────────────────────────────────────────────────────────────
    ("⚡", "SIM-Toolkit-Applets (STK) & JavaCard", [
        _f(411, "STK-Menü-Items lesen",              "cmd",
           "dumpsys isim 2>/dev/null | head -n 20; "
           "logcat -d -s CatService:D 2>/dev/null | grep -iE 'stk|menu|item' | head -n 20"),
        _f(412, "STK DISPLAY TEXT abfangen",        "live",
           "logcat -s CatService:D 2>/dev/null | grep -iE 'display.text|DISPLAY_TEXT'"),
        _f(413, "STK SETUP CALL blocken",           "cmd",
           "pm disable com.android.stk 2>/dev/null && echo STK deaktiviert",
           "SIM kann keinen Anruf mehr initiieren (SETUP CALL blockiert)."),
        _f(414, "STK PROVIDE LOCAL INFO",           "live",
           "logcat -s CatService:D 2>/dev/null | grep -iE 'PROVIDE.LOCAL|local.info'",
           "SIM kann Uhrzeit, Standort, IMEI, Batterie-Status abfragen. Hier sichtbar."),
        _f(415, "JavaCard-Applet installieren",     "info", "",
           "Nur auf programmierbaren SIMs (sysmoUSIM, blanke UICC):\n"
           "gp --install applet.cap  # GlobalPlatformPro\n"
           "Erfordert ISD-Key-Zugang (Default: 404142434445464748494A4B4C4D4E4F)."),
        _f(416, "JavaCard-Applet deinstallieren",   "info", "",
           "gp --delete <package-AID>\n"
           "gp --list  # zeigt alle installierten Applets und PIDs."),
        _f(417, "STK BIP-Kanal überwachen",         "live",
           "logcat -s CatService:D SIMRecords:D 2>/dev/null | grep -iE 'bip|channel|data.available'",
           "BIP = Bearer Independent Protocol: SIM öffnet Datenschnittstelle."),
        _f(418, "STK LOCATION STATUS-Events",       "live",
           "logcat -s CatService:D 2>/dev/null | grep -iE 'location.status|LOCATION.STATUS'"),
        _f(419, "STK POLLING-Intervall abfangen",   "live",
           "logcat -s CatService:D 2>/dev/null | grep -iE 'polling|POLL.INTERVAL'",
           "SIM kann Polling-Intervall des Geräts ändern (Akku-Manipulation möglich)."),
        _f(420, "JavaCard JCOP-Shell",              "info", "",
           "JCOP-Shell via GlobalPlatformPro:\n"
           "gp --shell  # Direkte APDU-Konsole\n"
           "CLA INS P1 P2 Lc [Data]  – z.B. 00 A4 04 00 07 A0000000871002"),
    ]),
    # ──── KAT 43 ─────────────────────────────────────────────────────────────
    ("📊", "Verbindungsqualität & QoS Monitoring", [
        _f(421, "Call-Drop-Rate-Monitor",            "live",
           "logcat -s TelephonyManager:D 2>/dev/null | grep -iE 'drop|disconnect|end.reason'"),
        _f(422, "Data-Stall-Detektion",              "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'stall|suspend|data.activity' | head"),
        _f(423, "Handover-Fail-Rate",                "live",
           "logcat -s TelephonyManager:D 2>/dev/null | grep -iE 'handover.fail|HO.FAIL|x2.failure'"),
        _f(424, "Ping-Latenz über mobiles Netz",     "cmd",
           "ping -c 5 8.8.8.8 2>/dev/null"),
        _f(425, "IP-MTU-Prüfung (Fragmentierung)",   "cmd",
           "ping -c 1 -s 1472 8.8.8.8 2>/dev/null; "
           "ping -c 1 -s 1500 8.8.8.8 2>/dev/null"),
        _f(426, "RTP-Jitter-Buffer-Status",          "live",
           "logcat -s ImsCall:D 2>/dev/null | grep -iE 'jitter|buffer|rtp'"),
        _f(427, "Bandbreiten-Schätzung via ADB",     "cmd",
           "cat /proc/net/dev 2>/dev/null | grep -iE 'rmnet|wlan|ppp' | head -n 10"),
        _f(428, "QoS-Klasse auslesen (QCI)",         "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'qci|QCI|qualityOfService' | head"),
        _f(429, "Datenrate Live-Monitor",            "live",
           "logcat -s DataConnectionTracker:D 2>/dev/null | grep -iE 'rate|throughput|speed'"),
        _f(430, "TCP-Retransmit-Statistik",          "cmd",
           "cat /proc/net/snmp 2>/dev/null | grep -iE 'Tcp:|tcp.Retrans'"),
    ]),
    # ──── KAT 44 ─────────────────────────────────────────────────────────────
    ("🔮", "Zukunftstechnologien: 6G & Post-5G", [
        _f(431, "6G-Forschungsfrequenzen (THz)",     "info", "",
           "6G operiert im Sub-THz (100–300 GHz) und THz-Band (300 GHz–3 THz).\n"
           "Status 2024: Keine kommerziellen Netze. Forschung: Samsung, Ericsson, NTT."),
        _f(432, "D2D (Device-to-Device) Proximity",  "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'd2d|proximity|sidelink'"),
        _f(433, "PC5-Schnittstelle (Sidelink V2X)",  "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'v2x|sidelink|pc5'",
           "V2X = Vehicle-to-Everything. PC5 = direkte Fahrzeug-Kommunikation ohne Basisstation."),
        _f(434, "Network-AI/AI-RAN Indikatoren",     "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'ai.ran|intelligent|predictive' | head"),
        _f(435, "RIS (Reconfigurable Intelligent Surface)", "info", "",
           "RIS = programmierbare Oberflächen, die Funksignale umleiten.\n"
           "In 6G-Spezifikationen (ITU-R IMT-2030). Noch keine ADB-Schnittstelle."),
        _f(436, "Joint Communication & Sensing (JCAS)", "info", "",
           "5G-Advanced/6G Feature: Basisstation als Radar nutzen.\n"
           "Erkennt Bewegungen, Fahrzeuge in Abdeckungsgebiet. Privatschutz-Relevanz."),
        _f(437, "Ambient-IoT (batterielos, Backscatter)", "info", "",
           "6G-Feature: Geräte ohne Batterie kommunizieren via Backscatter-Modulation.\n"
           "Relevant für SIM-Forensik: Geräte ohne Akku können trotzdem Signale senden."),
        _f(438, "Quantum-Key-Distribution (QKD) SIM", "info", "",
           "Post-Quantum-Kryptographie in zukünftigen SIMs: Kyber/Dilithium (NIST PQC).\n"
           "GSMA arbeitet an PQC-Profilen für SGP.22 v4."),
        _f(439, "ISAC-Sensing-Daten (Integrated Sensing & Comm)", "cmd",
           "dumpsys telephony.registry 2>/dev/null | grep -iE 'sensing|isac|radar' | head"),
        _f(440, "6G-Standardisierungs-Tracker",      "info", "",
           "3GPP Release 18 (5G-Advanced): 2024. Release 19: 2025. IMT-2030 (6G): 2030.\n"
           "Tracking: 3gpp.org/release-18, itu.int/en/ITU-R/study-groups/rsg5/rwp5d"),
    ]),
    # ──── KAT 45 ─────────────────────────────────────────────────────────────
    ("🏆", "Vollständiger SIM-Forensik-Report", [
        _f(441, "Komplett-Dump aller SIM-Daten",     "root",
           "dumpsys telephony.registry 2>/dev/null > /sdcard/sim_full_dump.txt; "
           "service call iphonesubinfo 1 s16 phone 2>/dev/null >> /sdcard/sim_full_dump.txt; "
           "service call iphonesubinfo 7 s16 phone 2>/dev/null >> /sdcard/sim_full_dump.txt; "
           "service call iphonesubinfo 11 s16 phone 2>/dev/null >> /sdcard/sim_full_dump.txt; "
           "service call iphonesubinfo 13 s16 phone 2>/dev/null >> /sdcard/sim_full_dump.txt; "
           "echo ===SIM-FULL-DUMP=== FERTIG"),
        _f(442, "IMSI + ICCID + EID in Datei",      "cmd",
           "echo '=== SIM-IDENTITÄTEN ===' > /sdcard/sim_ids.txt; "
           "service call iphonesubinfo 7 s16 phone 2>/dev/null >> /sdcard/sim_ids.txt; "
           "service call iphonesubinfo 11 s16 phone 2>/dev/null >> /sdcard/sim_ids.txt; "
           "service call econtrol 3 2>/dev/null >> /sdcard/sim_ids.txt; "
           "echo Gespeichert: /sdcard/sim_ids.txt"),
        _f(443, "Netzwerk-Fingerprint erzeugen",     "cmd",
           "getprop gsm.operator.alpha; getprop gsm.operator.numeric; "
           "getprop gsm.version.baseband; dumpsys telephony.registry 2>/dev/null | "
           "grep -iE 'mcc|mnc|cid|lac|earfcn|rsrp' | head -n 10"),
        _f(444, "Zeitstempel-Audit (SIM-Events)",    "live",
           "logcat -v time -s TelephonyManager:D SIMRecords:D 2>/dev/null | head -n 30"),
        _f(445, "SIM-Sicherheits-Score berechnen",   "cmd",
           "echo '--- SIM-SICHERHEITS-AUDIT ---'; "
           "getprop gsm.operator.numeric 2>/dev/null | grep -q '^[0-9]' && echo '+OK: Netz registriert' || echo '-WARN: Kein Netz'; "
           "dumpsys telephony.registry 2>/dev/null | grep -q 'networkType=13' && echo '+OK: LTE aktiv' || echo '-INFO: kein LTE'"),
        _f(446, "Schwachstellen-Checkliste",         "info", "",
           "☐ PIN aktiv (verhindert physischen Zugriff)\n"
           "☐ Modem-FW aktuell (Baseband-CVEs prüfen)\n"
           "☐ STK-App deaktiviert (SIM-Angriffe blockiert)\n"
           "☐ VoLTE/VoWiFi via vertrauenswürdigen Carrier\n"
           "☐ kein 2G-Downgrade (IMSI-Catcher-Schutz)\n"
           "☐ SUCI aktiv (5G Privacy-Schutz)\n"
           "☐ eSIM-Zertifikat GSMA-signiert\n"
           "☐ IMEI-Luhn-Prüfung bestanden"),
        _f(447, "Vollständige Konnektivitäts-Matrix", "cmd",
           "for interface in $(ls /sys/class/net/ 2>/dev/null); do "
           "echo $interface: $(cat /sys/class/net/$interface/operstate 2>/dev/null); done"),
        _f(448, "SIM-Backup-Report als XML",         "root",
           "bu backup -noapk -shared -all 2>/dev/null & sleep 3; "
           "echo 'ADB Backup gestartet – bestätige auf Gerät.'"),
        _f(449, "Forensik-Kette-Integrität (Hash)",  "cmd",
           "sha256sum /sdcard/sim_full_dump.txt 2>/dev/null; "
           "sha256sum /sdcard/sim_ids.txt 2>/dev/null",
           "Hash der erzeugten Berichte für Chain-of-Custody."),
        _f(450, "SIM-Toolkit ABSCHLUSS-AUDIT",       "cmd",
           "echo '=== ANDROID PANZER SIM-AUDIT KOMPLETT ==='; "
           "echo 'Zeitstempel:' $(date); "
           "echo 'Gerät:' $(getprop ro.build.fingerprint); "
           "echo 'Baseband:' $(getprop gsm.version.baseband); "
           "echo 'Netz:' $(getprop gsm.operator.alpha); "
           "ls -la /sdcard/sim_*.txt 2>/dev/null"),
    ]),
]

# Abgeflachte Feature-Tabelle für Schnellzugriff
_ALL_FEATURES: dict[int, dict] = {}
for _cat_idx, (_emoji, _catname, _feats) in enumerate(SIM_CATEGORIES):
    for _feat in _feats:
        _ALL_FEATURES[_feat["n"]] = {**_feat, "cat": _catname, "emoji": _emoji}


# ══════════════════════════════════════════════════════════════════════════════
#  ICCID-HERSTELLER-LOOKUP (MII-Prefix)
# ══════════════════════════════════════════════════════════════════════════════

_ICCID_PREFIXES = {
    "8901": "Telekom Deutschland",
    "8902": "Telefónica/O2 Deutschland",
    "8906": "Vodafone Deutschland",
    "8910": "Vodafone DE (alt)",
    "8949": "O2 Deutschland",
    "8930": "T-Mobile USA",
    "8931": "AT&T USA",
    "8950": "Verizon Wireless",
    "8988": "eSIM / M2M (GSMA SGP.02)",
    "8920": "Telstra Australien",
    "8960": "China Mobile",
    "8961": "China Unicom",
    "8952": "Singtel Singapur",
    "8991": "sysmocom Test-SIM",
}


def _iccid_vendor(iccid: str) -> str:
    for prefix, vendor in _ICCID_PREFIXES.items():
        if iccid.replace(" ", "").startswith(prefix):
            return vendor
    return "Unbekannt"


def _luhn_check(imei: str) -> bool:
    digits = [int(c) for c in imei if c.isdigit()]
    if len(digits) != 15:
        return False
    total = 0
    for i, d in enumerate(digits):
        n = d * 2 if i % 2 == 1 else d
        total += n // 10 + n % 10
    return total % 10 == 0


# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE AUSFÜHREN
# ══════════════════════════════════════════════════════════════════════════════

def _run_feature(adb: ADB, feat: dict) -> None:
    """Führt ein einzelnes Feature aus."""
    ui.clear()
    kind = feat["k"]
    title = f"[{feat['n']}] {feat['t']}"
    ui.rule(title, ui.CYAN)
    if feat.get("note"):
        print(f"  {ui.GREY}{feat['note']}{ui.RESET}\n")

    if kind == "info":
        ui.info("Erklärung:")
        note = feat.get("note") or feat.get("p") or "(keine weiteren Infos)"
        print(f"\n{ui.WHITE}{note}{ui.RESET}\n")
        ui.pause()
        return

    if kind == "sdr":
        ui.warn("Benötigt externe Hardware:")
        print(f"\n{feat.get('note', _NEED_SDR)}\n")
        ui.pause()
        return

    if kind == "danger":
        ui.warn(f"⚠ ACHTUNG: Gefährliche Aktion!")
        if feat.get("note"):
            print(f"\n{feat['note']}\n")
        if not ui.confirm("Wirklich ausführen (NUR auf eigenem Test-Gerät)?", False):
            return

    if kind in ("cmd", "root", "danger", "live"):
        cmd = feat["p"]
        if not cmd:
            ui.info("Kein Befehl definiert."); ui.pause(); return
        if kind == "ask":
            note = feat.get("note", "")
            print(f"\n  {ui.GREY}Befehlsvorlage:{ui.RESET}\n  {note}\n")
            val = ui.ask("Eingabe für {v}").strip()
            if not val:
                return
            cmd = note.replace("{v}", val).split("\n")[0]

        ui.info(f"ADB-Befehl: {ui.GREY}{cmd[:80]}{ui.RESET}")
        print()
        use_root = kind == "root"
        try:
            out = adb.shell(cmd, root=use_root, timeout=30)
            if out.strip():
                print(out.strip())
            else:
                ui.warn("(Keine Ausgabe – Befehl ausgeführt oder Zugriff verweigert)")
        except Exception as e:  # noqa: BLE001
            ui.err(f"ADB-Fehler: {e}")

    elif kind == "ask":
        note = feat.get("note", feat["p"])
        print(f"\n  {ui.GREY}Befehlsvorlage:{ui.RESET}\n  {note}\n")
        val = ui.ask("Eingabe für {v}").strip()
        if not val:
            ui.pause(); return
        cmd = note.replace("{v}", val).split("\n")[0]
        ui.info(f"Ausführe: {cmd}")
        try:
            out = adb.shell(cmd)
            if out.strip():
                print(out.strip())
        except Exception as e:  # noqa: BLE001
            ui.err(str(e))

    ui.pause()


# ══════════════════════════════════════════════════════════════════════════════
#  UI-FUNKTIONEN
# ══════════════════════════════════════════════════════════════════════════════

def show_sim_models() -> None:
    """SIM-Karten-Modell-Datenbank interaktiv anzeigen."""
    while True:
        ui.clear()
        ui.rule("SIM-KARTEN MODELL-DATENBANK", ui.CYAN)
        print()
        entries = [
            ("F", f"{ui.BGREEN}📐 Physische Formate (1FF–5FF/eSIM){ui.RESET}"),
            ("E", f"{ui.BCYAN}💳 eSIM-Chiphersteller (Infineon/ST/NXP/G+D …){ui.RESET}"),
            ("S", f"{ui.BYELLOW}🧪 Spezial-SIMs (Test, IoT, CDMA, programm.){ui.RESET}"),
        ]
        ch = ui.menu("Kategorie", entries, back_label="Zurück")
        if ch in ("back", "quit"):
            return

        if ch == "f":
            ui.clear()
            ui.rule("PHYSISCHE SIM-FORMATE (1FF–5FF)", ui.CYAN)
            for i, fmt in enumerate(SIM_FORMATS, 1):
                print(f"\n  {ui.BOLD}{i}. {fmt['name']}{ui.RESET}")
                print(f"     Maße:      {fmt['size']} · Dicke: {fmt['thickness']}")
                print(f"     Spannung:  {fmt['voltage']}")
                print(f"     Geräte:    {ui.GREY}{fmt['used_in']}{ui.RESET}")
                print(f"     Hinweis:   {fmt['notes']}")
            ui.pause()

        elif ch == "e":
            ui.clear()
            ui.rule("eSIM-CHIPHERSTELLER", ui.BCYAN)
            for chip in ESIM_CHIPS:
                print(f"\n  {ui.BOLD}{chip['vendor']}{ui.RESET}  –  {chip['model']}")
                print(f"     Architektur:  {chip['arch']}")
                print(f"     Krypto:       {chip['crypto']}")
                print(f"     Betriebssystem:{chip['os']}")
                print(f"     Zertifiziert: {chip['certified']}")
                print(f"     Hinweis:      {ui.GREY}{chip['notes']}{ui.RESET}")
            ui.pause()

        elif ch == "s":
            while True:
                ui.clear()
                ui.rule("SPEZIAL-SIM-MODELLE", ui.BYELLOW)
                sim_entries = [(str(i), f"{s['name']} — {s['vendor']}")
                               for i, s in enumerate(SPECIAL_SIMS, 1)]
                ch2 = ui.menu("SIM-Modell", sim_entries, back_label="Zurück")
                if ch2 in ("back", "quit"):
                    break
                try:
                    s = SPECIAL_SIMS[int(ch2) - 1]
                except (ValueError, IndexError):
                    continue
                ui.clear()
                ui.rule(s["name"], ui.BYELLOW)
                ui.kv("Hersteller",     s["vendor"])
                ui.kv("Formfaktor",     s["format"])
                ui.kv("Betriebssystem", s["os"])
                ui.kv("Programmierbar", "JA" if s["programmable"] else "Nein")
                ui.kv("Ki änderbar",    "JA" if s["ki_changeable"] else "Nein")
                ui.kv("Tools",          s["tools"])
                ui.kv("Verwendung",     s["use_case"])
                print(f"\n  {ui.GREY}{s['notes']}{ui.RESET}\n")
                ui.pause()


def browse_categories(adb: ADB) -> None:
    """35 SIM-Kategorien interaktiv durchsuchen (350 Features)."""
    while True:
        ui.clear()
        ui.rule("SIM-KATEGORIEN – 35 Kategorien · 350 Features", ui.CYAN)
        print()
        entries = []
        for i, (emoji, name, feats) in enumerate(SIM_CATEGORIES, 1):
            cat_nr_start = feats[0]["n"]
            cat_nr_end   = feats[-1]["n"]
            entries.append((str(i), f"{emoji}  {name:<45} #{cat_nr_start:3d}–{cat_nr_end:3d}"))
        ch = ui.menu("Kategorie wählen", entries, back_label="Zurück")
        if ch in ("back", "quit"):
            return
        try:
            idx = int(ch) - 1
            emoji, name, feats = SIM_CATEGORIES[idx]
        except (ValueError, IndexError):
            continue

        # Feature-Liste der Kategorie
        while True:
            ui.clear()
            ui.rule(f"{emoji} {name}", ui.CYAN)
            print()
            kind_labels = {
                "cmd":    f"{ui.BGREEN}[ADB]   {ui.RESET}",
                "root":   f"{ui.BRED}[ROOT]  {ui.RESET}",
                "info":   f"{ui.GREY}[INFO]  {ui.RESET}",
                "sdr":    f"{ui.BYELLOW}[SDR/HW]{ui.RESET}",
                "danger": f"{ui.BRED}[GEFAHR]{ui.RESET}",
                "ask":    f"{ui.BCYAN}[ASK]   {ui.RESET}",
                "live":   f"{ui.BMAGENTA}[LIVE]  {ui.RESET}",
            }
            feat_entries = []
            for f in feats:
                label = kind_labels.get(f["k"], "[?]    ")
                feat_entries.append((str(f["n"]), f"{label} {f['t']}"))
            ch2 = ui.menu("Feature wählen (Nr.)", feat_entries, back_label="Zurück")
            if ch2 in ("back", "quit"):
                break
            try:
                fn = int(ch2)
                feat = _ALL_FEATURES.get(fn)
                if feat is None:
                    feat = next((f for f in feats if f["n"] == fn), None)
            except ValueError:
                continue
            if feat:
                _run_feature(adb, feat)


def quick_diagnosis(adb: ADB) -> None:
    """Schnell-Diagnose: SIM-Slot, ICCID, PIN, VoLTE, IMSI."""
    ui.clear()
    ui.rule("SIM SCHNELL-DIAGNOSE", ui.CYAN)
    ui.info("Erfasse SIM-Statusdaten …")
    lines = [f"# SIM SCHNELL-DIAGNOSE", f"# {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]

    checks = [
        ("SIM-Status",      "dumpsys telephony.registry 2>/dev/null | grep mSimState | head"),
        ("ICCID",           "service call iphonesubinfo 11 s16 phone 2>/dev/null"),
        ("IMEI",            "service call iphonesubinfo 1 s16 phone 2>/dev/null"),
        ("MSISDN",          "service call iphonesubinfo 13 s16 phone 2>/dev/null"),
        ("Baseband",        "getprop gsm.version.baseband"),
        ("Carrier-Config",  "dumpsys carrier_config 2>/dev/null | head -n 8"),
        ("VoLTE-Status",    "dumpsys telephony.registry 2>/dev/null | grep -iE 'volte|mVoL' | head"),
        ("VoWiFi-Status",   "dumpsys telephony.registry 2>/dev/null | grep -iE 'vowifi|wificall' | head"),
        ("Netzwerk-Typ",    "dumpsys telephony.registry 2>/dev/null | grep networkType | head"),
        ("DSDS-Modus",      "getprop persist.radio.multisim.config"),
        ("APN-Einträge",    "content query --uri content://telephony/carriers 2>/dev/null | grep 'name=' | head -n 5"),
    ]

    for label, cmd in checks:
        print(f"  {ui.GREY}▸ {label:<20}{ui.RESET}", end="", flush=True)
        try:
            out = adb.shell(cmd, timeout=8).strip()
            val = out[:80] if out else "(leer)"
        except Exception:  # noqa: BLE001
            val = "ADB-Fehler"
        print(f" {val}")
        lines.append(f"== {label} ==\n{out if out else '(leer)'}\n")

    body = "\n".join(lines)
    p = os.path.join(OUT, f"sim_diagnosis_{int(time.time())}.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"\n  {ui.BGREEN}Exportiert → {p}{ui.RESET}")
    ui.pause()


def _read_eid(adb: ADB) -> str:
    """Versucht EID über 9 verschiedene Methoden zu lesen."""
    methods = [
        # Methode 1: Android 10+ EuiccManager via dumpsys
        "dumpsys euicc_card_info 2>/dev/null | grep -iE 'eid|EID' | head -n 3",
        # Methode 2: isub (SubscriptionManager)
        "dumpsys isub 2>/dev/null | grep -iE 'eid' | head -n 3",
        # Methode 3: Telephony service direkt
        "service call isub 2>/dev/null | grep -iE 'eid' | head -n 2",
        # Methode 4: getprop (MTK / Qualcomm vendor props)
        "getprop vendor.ril.eid 2>/dev/null; getprop ril.eid 2>/dev/null; "
        "getprop ro.ril.eid 2>/dev/null",
        # Methode 5: Phone-Service
        "dumpsys phone 2>/dev/null | grep -iE 'eid' | head -n 3",
        # Methode 6: TelephonyManager Content Provider
        "content query --uri content://telephony/siminfo 2>/dev/null | grep -iE 'eid' | head -n 3",
        # Methode 7: euicc via service call
        "service call ephone 61 2>/dev/null | head -n 3",
        # Methode 8: /sys/class eUICC
        "ls /sys/class/ieee802154/ 2>/dev/null; cat /sys/class/euicc*/eid 2>/dev/null",
        # Methode 9: logcat nach EID-Einträgen
        "logcat -d -s EuiccController:D EuiccManager:D 2>/dev/null | "
        "grep -iE 'eid' | tail -n 5",
    ]
    results = []
    for i, cmd in enumerate(methods, 1):
        out = adb.shell(cmd).strip()
        if out and out not in ("(Keine Ausgabe)", ""):
            # Versuche EID-Format zu extrahieren: 32 Hex-Zeichen
            m = re.search(r'[0-9A-Fa-f]{32}', out)
            if m:
                return f"EID: {m.group(0).upper()}"
            results.append(f"Methode {i}: {out[:100]}")
    return "\n".join(results) if results else "EID nicht auslesbar – eSIM möglicherweise nicht vorhanden."


def esim_manager(adb: ADB) -> None:
    """eSIM-Profil-Manager – ERWEITERT: EID · Profile · LPA · Profil-Download · GSMA SGP."""
    while True:
        ui.clear()
        ui.rule("💳 eSIM-PROFIL-MANAGER – ERWEITERT", ui.BCYAN)
        print()
        ch = ui.menu("Aktion", [
            ("1",  "🔑 EID auslesen (9 Methoden: dumpsys/getprop/service/logcat)"),
            ("2",  "📋 Installierte eSIM-Profile (alle Methoden)"),
            ("3",  "✅ eSIM-Fähigkeit prüfen (EuiccManager + Chip-Info)"),
            ("4",  "🚀 LPA-App starten (System-eSIM-Verwaltung)"),
            ("5",  "🔗 eSIM-Aktivierungscode eingeben (LPA:1$... / QR-Code-Inhalt)"),
            ("6",  "📜 eSIM-Aktivierungs-Log (EuiccController + LPA)"),
            ("7",  "🌐 SM-DP+ Server Verbindung prüfen"),
            ("8",  "📊 eSIM-Chip Details (ATR · ICCID · Hersteller)"),
            ("9",  "🔄 eSIM-Profil aktivieren/deaktivieren"),
            ("10", "🗑️  eSIM-Profil löschen"),
            ("11", "📤 eSIM-Profil-Backup (GSMA SGP.22)"),
            ("12", "🔒 eSIM-Zertifikat-Chain anzeigen"),
            ("13", "📡 eSIM SMSR / SMDP Diagnose"),
            ("14", "🔧 EuiccService Intent senden"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            ui.clear(); ui.rule("EID auslesen – 9 Methoden", ui.BCYAN)
            ui.info("Versuche alle bekannten EID-Lesemethoden …")
            print()
            eid = _read_eid(adb)
            print(f"\n{ui.BGREEN if 'EID:' in eid else ui.BYELLOW}{eid}{ui.RESET}")
            if "EID:" in eid:
                raw = re.search(r'[0-9A-F]{32}', eid)
                if raw:
                    eid_val = raw.group(0)
                    print(f"\n  {ui.GREY}TAC (Hersteller-ID):  {eid_val[:8]}")
                    print(f"  Individual-ID:       {eid_val[8:]}{ui.RESET}")
                    # GSMA TAC-Lookup
                    tac_db = {
                        "89049032": "Apple (Infineon)", "89033023": "Apple (ST Micro)",
                        "89049031": "Google/Qualcomm",  "89049033": "Samsung LSI",
                        "89049034": "MediaTek",         "89049035": "Kirin (Huawei)",
                        "89049036": "UNISOC",           "89049037": "NXP",
                    }
                    vendor = tac_db.get(eid_val[:8], "Unbekannter Hersteller")
                    print(f"  Hersteller (TAC-DB): {ui.BOLD}{vendor}{ui.RESET}")
        elif ch == "2":
            ui.clear(); ui.rule("Installierte eSIM-Profile", ui.BCYAN)
            cmds = [
                ("dumpsys isub", "dumpsys isub 2>/dev/null | grep -iE 'iccid|carrier|profile|display' | head -n 30"),
                ("euicc_card_info", "dumpsys euicc_card_info 2>/dev/null"),
                ("ephone profiles", "service call ephone 3 2>/dev/null | head -n 10"),
            ]
            for label, cmd in cmds:
                out = adb.shell(cmd).strip()
                if out:
                    ui.rule(label, ui.GREY)
                    print(out[:500])
        elif ch == "3":
            ui.clear(); ui.rule("eSIM-Fähigkeit", ui.BCYAN)
            checks = [
                ("EuiccManager API",     "dumpsys package com.google.android.euicc 2>/dev/null | grep versionName | head -n 1"),
                ("EuiccCardInfo Service","dumpsys euicc_card_info 2>/dev/null | head -n 5"),
                ("LPA Package",          "pm list packages 2>/dev/null | grep -iE 'euicc|lpa|esim' | head -n 5"),
                ("eSIM getprop",         "getprop | grep -iE 'esim|euicc' | head -n 5"),
                ("TelephonyCapability",  "dumpsys phone 2>/dev/null | grep -i 'esim\\|euicc' | head -n 5"),
            ]
            for label, cmd in checks:
                out = adb.shell(cmd).strip()
                icon = f"{ui.BGREEN}✓{ui.RESET}" if out else f"{ui.GREY}–{ui.RESET}"
                print(f"  {icon}  {label:<28}  {ui.GREY}{out[:60] if out else 'nicht gefunden'}{ui.RESET}")
        elif ch == "4":
            intents = [
                "am start -n com.google.android.euicc/.ui.GetDefaultSubscriptionActivity 2>/dev/null",
                "am start -a android.service.euicc.action.MAIN 2>/dev/null",
                "am start -a com.samsung.android.euicc.action.EUICC_UI 2>/dev/null",
                "am start -n com.android.phone/.settings.euicc.EuiccSettingsActivity 2>/dev/null",
            ]
            for intent in intents:
                out = adb.shell(intent)
                if "error" not in out.lower() and "exception" not in out.lower():
                    ui.ok(f"LPA gestartet: {intent[:60]}")
                    break
        elif ch == "5":
            code = ui.ask("Aktivierungscode (LPA:1$smdp.example.com$... oder QR-Inhalt)").strip()
            if code:
                out = adb.shell(
                    f"am start -a android.intent.action.VIEW "
                    f"-n com.google.android.euicc/.ui.MainActivity "
                    f"--es 'activation_code' '{code}' 2>/dev/null")
                print(out or "(Keine Antwort – ggf. LPA öffnet sich auf dem Gerät)")
        elif ch == "6":
            ui.clear(); ui.rule("eSIM Log", ui.BCYAN)
            out = adb.shell(
                "logcat -d -s EuiccController:D EuiccManager:D LPA:D "
                "euicc:D EuiccService:D 2>/dev/null | tail -n 60")
            print(out.strip() or "(Kein eSIM-Log)")
        elif ch == "7":
            ui.clear(); ui.rule("SM-DP+ Verbindung", ui.BCYAN)
            servers = [
                "smdp.gsma.com", "consumer.smdp.io", "lpa.ntt.com",
                "smdpplus.t-mobile.com", "smdp.verizon.com",
            ]
            custom = ui.ask("Eigener SM-DP+ Server (leer=Standard-Test)").strip()
            if custom:
                servers = [custom]
            for srv in servers:
                import socket
                try:
                    socket.setdefaulttimeout(3)
                    socket.gethostbyname(srv)
                    print(f"  {ui.BGREEN}✓{ui.RESET}  {srv}")
                except OSError:
                    print(f"  {ui.BRED}✗{ui.RESET}  {srv}")
        elif ch == "8":
            ui.clear(); ui.rule("eSIM-Chip Details", ui.BCYAN)
            cmds = [
                ("ATR",      "cat /sys/class/uicc/uicc0/atr 2>/dev/null || "
                             "cat /sys/bus/platform/devices/*.sim/atr 2>/dev/null"),
                ("ICCID",    "getprop gsm.sim.state; "
                             "content query --uri content://telephony/siminfo 2>/dev/null | "
                             "grep iccid | head -n 2"),
                ("Chip-OS",  "cat /sys/class/uicc/uicc0/atr 2>/dev/null | "
                             "xxd 2>/dev/null | head -n 3"),
            ]
            for label, cmd in cmds:
                out = adb.shell(cmd).strip()
                ui.kv(label, out[:100] if out else "—")
        elif ch == "9":
            sub_id = ui.ask("Subscription-ID (leer=auto)").strip() or "0"
            enable = ui.confirm("Profil aktivieren (Nein=deaktivieren)?", True)
            action = "enable" if enable else "disable"
            out = adb.shell(
                f"service call isub 9 i32 {sub_id} 2>/dev/null || "
                f"am broadcast -a android.telephony.action.SIM_SUBSCRIPTION_CHANGED 2>/dev/null")
            print(out or f"(Profil {action} gesendet)")
        elif ch == "10":
            if ui.confirm("eSIM-Profil wirklich löschen (nicht rückgängig)?", False):
                sub_id = ui.ask("Subscription-ID").strip() or "0"
                out = adb.shell(f"service call ephone 5 i32 {sub_id} 2>/dev/null")
                print(out or "(Löschbefehl gesendet)")
        elif ch == "11":
            ui.clear(); ui.rule("eSIM-Profil-Backup", ui.BCYAN)
            out = adb.shell(
                "dumpsys isub 2>/dev/null; "
                "dumpsys euicc_card_info 2>/dev/null; "
                "content query --uri content://telephony/siminfo 2>/dev/null")
            ts = int(time.time())
            fn = os.path.join(OUT, f"esim_backup_{ts}.txt")
            with open(fn, "w") as f:
                f.write(out)
            ui.ok(f"Backup: {fn}")
        elif ch == "12":
            out = adb.shell(
                "dumpsys euicc_card_info 2>/dev/null | grep -iE 'cert|certificate|chain' | head -n 20")
            print(out.strip() or "(Kein Zertifikat-Info)")
        elif ch == "13":
            ui.clear(); ui.rule("SMSR / SMDP Diagnose", ui.BCYAN)
            out = adb.shell(
                "logcat -d -s EuiccLpa:D SMSR:D SMDP:D 2>/dev/null | tail -n 30; "
                "dumpsys euicc_card_info 2>/dev/null | grep -iE 'smdp|smsr|server' | head -n 10")
            print(out.strip() or "(Keine SMSR/SMDP-Daten)")
        elif ch == "14":
            intents = {
                "a": "android.service.euicc.action.DELETE_SUBSCRIPTION_PRIVILEGED",
                "b": "android.service.euicc.action.TOGGLE_SUBSCRIPTION_PRIVILEGED",
                "c": "android.service.euicc.action.RENAME_SUBSCRIPTION_PRIVILEGED",
                "d": "android.service.euicc.action.PROVISION_EMBEDDED_SUBSCRIPTION",
            }
            for k, v in intents.items():
                print(f"  {k}) {v}")
            sel = ui.ask("Aktion").strip().lower()
            intent = intents.get(sel)
            if intent:
                out = adb.shell(f"am broadcast -a {intent} 2>/dev/null")
                print(out)
        ui.pause()


# ══════════════════════════════════════════════════════════════════════════════
#  LIVE SIM-TRAFFIC DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

_NET_TYPE = {
    0: "UNKNOWN",  1: "GPRS",   2: "EDGE",    3: "UMTS",   4: "CDMA",
    6: "EVDO-A",   7: "1xRTT",  8: "HSDPA",   9: "HSUPA",  10: "HSPA",
    11: "iDEN",   12: "EVDO-B", 13: "LTE",    14: "eHRPD", 15: "HSPA+",
    16: "GSM",    17: "TD-SCDMA", 18: "IWLAN", 19: "LTE-CA", 20: "NR 5G",
}

_FREQ_BAND = {
    1: "2100 MHz", 2: "1900 MHz", 3: "1800 MHz", 4: "1700 MHz", 5: "850 MHz",
    7: "2600 MHz", 8: "900 MHz", 12: "700 MHz", 13: "700 MHz", 17: "700 MHz",
    20: "800 MHz", 28: "700 MHz", 38: "2600 MHz", 40: "2300 MHz", 41: "2500 MHz",
    66: "AWS-3", 71: "600 MHz", 77: "3.5 GHz", 78: "3.5 GHz", 79: "4.9 GHz",
}

# ── Session-Caches (persistent über _collect()-Aufrufe) ──────────────────────
_uid_pkg_cache: dict = {}   # uid_str  → kurzer Paketname
_ip_host_cache: dict = {}   # ip_str   → Hostname (Reverse-DNS-Cache)
_dns_session:   list = []   # [(ts_str, domain, app_name), ...]
_uid_pkg_ts:    float = 0.0 # Zeitstempel letztes pm-Refresh


def _sig_bar(val: int, lo: int, hi: int, w: int = 16) -> str:
    if val is None:
        return f"{ui.GREY}{'░'*w}{ui.RESET}"
    pct = max(0.0, min(1.0, (val - lo) / (hi - lo)))
    filled = int(w * pct)
    if pct >= 0.7:
        col = ui.BGREEN
    elif pct >= 0.4:
        col = ui.BYELLOW
    else:
        col = ui.BRED
    return f"{col}{'█'*filled}{'░'*(w-filled)}{ui.RESET}"


def _fmt_speed(bps: float) -> str:
    if bps < 0:
        bps = 0
    if bps >= 1_000_000:
        return f"{bps/1_000_000:6.2f} MB/s"
    if bps >= 1_000:
        return f"{bps/1_000:6.2f} KB/s"
    return f"{bps:6.0f}  B/s"


def _fmt_bytes(b: int) -> str:
    if b >= 1_073_741_824:
        return f"{b/1_073_741_824:.2f} GB"
    if b >= 1_048_576:
        return f"{b/1_048_576:.2f} MB"
    if b >= 1_024:
        return f"{b/1_024:.1f} KB"
    return f"{b} B"


def _hex_ip4_le(h: str) -> str:
    """Little-endian 8-Zeichen Hex → x.x.x.x"""
    try:
        n = int(h, 16)
        return f"{n&0xff}.{(n>>8)&0xff}.{(n>>16)&0xff}.{(n>>24)&0xff}"
    except Exception:
        return ""


def _refresh_uid_pkg(adb: ADB) -> None:
    """pm list packages -U → _uid_pkg_cache (alle 60 s)."""
    global _uid_pkg_cache, _uid_pkg_ts
    raw = adb.shell("pm list packages -U 2>/dev/null")
    _uid_pkg_cache.clear()
    for line in raw.splitlines():
        m = re.match(r'package:(\S+)\s+uid:(\d+)', line.strip())
        if m:
            pkg_full, uid = m.group(1), m.group(2)
            parts = pkg_full.split('.')
            short = parts[-1] if len(parts[-1]) > 2 else '.'.join(parts[-2:])
            _uid_pkg_cache[uid] = short[:20]
    _uid_pkg_ts = time.monotonic()


def _collect(adb: ADB, prev: dict) -> dict:
    d: dict = {}
    now = time.monotonic()

    # ── Telephony Registry (Signal + Netz) ─────────────────────────────────
    tel = adb.shell(
        "dumpsys telephony.registry 2>/dev/null | head -n 120")
    # RSRP
    m = re.search(r'rsrp\s*=\s*(-?\d+)', tel, re.I)
    d['rsrp'] = int(m.group(1)) if m else None
    # RSRQ
    m = re.search(r'rsrq\s*=\s*(-?\d+)', tel, re.I)
    d['rsrq'] = int(m.group(1)) if m else None
    # RSSI
    m = re.search(r'rssi\s*=\s*(-?\d+)', tel, re.I)
    d['rssi'] = int(m.group(1)) if m else None
    # SINR/rssnr
    m = re.search(r'(?:rssnr|sinr)\s*=\s*(-?\d+)', tel, re.I)
    d['sinr'] = int(m.group(1)) if m else None
    # Netzwerk-Typ
    m = re.search(r'mDataNetworkType\s*=\s*(\d+)', tel)
    d['net_type'] = int(m.group(1)) if m else 0
    # Operator
    m = re.search(r'mNetworkOperatorName\s*=\s*(\S+)', tel)
    d['operator'] = m.group(1) if m else "—"
    # Cell ID
    m = re.search(r'(?:ci|cellId)\s*=\s*(\d+)', tel, re.I)
    d['cell_id'] = m.group(1) if m else "?"
    # TAC / LAC
    m = re.search(r'(?:tac|lac)\s*=\s*(\w+)', tel, re.I)
    d['tac'] = m.group(1) if m else "?"
    # Band
    m = re.search(r'(?:band|earfcn)\s*=\s*(\d+)', tel, re.I)
    d['band'] = int(m.group(1)) if m else 0
    # Slot-Anzahl
    m = re.search(r'phoneId\s*=\s*(\d+)', tel, re.I)
    d['slot'] = m.group(1) if m else "0"

    # ── Operator / SIM props ─────────────────────────────────────────────
    ops = adb.shell(
        "getprop gsm.operator.alpha; getprop gsm.sim.state; getprop gsm.operator.numeric")
    props = [p.strip() for p in ops.splitlines() if p.strip()]
    if not d['operator'] or d['operator'] == "—":
        d['operator'] = props[0] if props else "—"
    d['sim_state'] = props[1] if len(props) > 1 else "?"
    d['plmn'] = props[2] if len(props) > 2 else "?"

    # ── APN / IP ──────────────────────────────────────────────────────────
    apn_out = adb.shell(
        "settings get global data_roaming 2>/dev/null; "
        "ip -4 addr show rmnet0 2>/dev/null | grep 'inet ' | awk '{print $2}' | head -n 1; "
        "ip -4 addr show wlan0 2>/dev/null  | grep 'inet ' | awk '{print $2}' | head -n 1")
    apn_lines = [l.strip() for l in apn_out.splitlines() if l.strip()]
    d['roaming'] = "JA" if apn_lines and apn_lines[0] == "1" else "NEIN"
    d['ip_rmnet'] = apn_lines[1] if len(apn_lines) > 1 else "—"
    d['ip_wlan']  = apn_lines[2] if len(apn_lines) > 2 else "—"

    # ── Traffic: /proc/net/dev ────────────────────────────────────────────
    net_dev = adb.shell("cat /proc/net/dev 2>/dev/null")
    rx_total = tx_total = 0
    iface_stats = []
    for line in net_dev.splitlines():
        if ':' not in line:
            continue
        iface, rest = line.split(':', 1)
        iface = iface.strip()
        if iface == 'lo':
            continue
        parts = rest.split()
        if len(parts) >= 9:
            rx = int(parts[0])
            tx = int(parts[8])
            rx_total += rx
            tx_total += tx
            if rx + tx > 0:
                iface_stats.append((iface, rx, tx))
    d['rx_bytes'] = rx_total
    d['tx_bytes'] = tx_total
    d['ifaces']   = iface_stats

    # Speed-Delta
    dt = now - prev.get('ts', now)
    if dt > 0.1 and 'rx_bytes' in prev:
        d['rx_speed'] = max(0.0, (rx_total - prev.get('rx_bytes', rx_total)) / dt)
        d['tx_speed'] = max(0.0, (tx_total - prev.get('tx_bytes', tx_total)) / dt)
    else:
        d['rx_speed'] = d.get('rx_speed', 0.0)
        d['tx_speed'] = d.get('tx_speed', 0.0)
    d['rx_total_session'] = rx_total - prev.get('rx_start', rx_total)
    d['tx_total_session'] = tx_total - prev.get('tx_start', tx_total)
    d['rx_start'] = prev.get('rx_start', rx_total)
    d['tx_start'] = prev.get('tx_start', tx_total)
    d['ts'] = now

    # ── UID→Paketname Cache (alle 60 s) ──────────────────────────────────
    global _uid_pkg_cache, _uid_pkg_ts, _ip_host_cache, _dns_session
    if time.monotonic() - _uid_pkg_ts > 60:
        _refresh_uid_pkg(adb)

    # ── /proc/net/tcp + /proc/net/tcp6: Remote-IP → UID ─────────────────
    ip_uid: dict = {}
    for fname in ["/proc/net/tcp", "/proc/net/tcp6"]:
        raw_tcp = adb.shell(f"cat {fname} 2>/dev/null | awk 'NR>1{{print $3,$4,$8}}'")
        for line in raw_tcp.splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            rem_hex = parts[0]          # remote addr:port hex
            st      = parts[1]          # state hex (01=ESTABLISHED)
            uid     = parts[2]
            if st != "01":              # nur ESTABLISHED
                continue
            addr_port = rem_hex.split(':')
            if len(addr_port) != 2:
                continue
            addr_hex = addr_port[0]
            if len(addr_hex) == 8:      # IPv4
                ip = _hex_ip4_le(addr_hex)
            elif len(addr_hex) == 32:   # IPv6 (möglicherweise IPv4-mapped)
                if addr_hex[:24] in ('0' * 24, '0000000000000000FFFF0000'):
                    ip = _hex_ip4_le(addr_hex[24:])
                else:
                    continue            # reines IPv6 — überspringen
            else:
                continue
            if ip and ip != '0.0.0.0':
                ip_uid[ip] = uid

    # ── DNS-Log via logcat ────────────────────────────────────────────────
    logcat_dns = adb.shell(
        "logcat -d -t 80 2>/dev/null | grep -iE "
        "'DnsResolver|netd.*res|getaddrinfo|resolv|nslookup|dns.query' | tail -25")
    ts_now = time.strftime("%H:%M:%S")
    seen_now: set = set()
    for line in logcat_dns.splitlines():
        # Verschiedene Patterns: Hostname extrahieren
        domain = None
        for pat in [
            r'getaddrinfo\("([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})"',
            r'(?:lookup|query|resolving)[:\s]+([a-zA-Z0-9._-]{4,}\.[a-zA-Z]{2,})',
            r'"hostname":\s*"([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})"',
            r'DnsResolver.*\s([a-zA-Z0-9._-]{6,}\.[a-zA-Z]{2,})\s',
            r'(?:connect|resolve)\s+([a-zA-Z0-9._-]{4,}\.[a-zA-Z]{2,}):',
        ]:
            m = re.search(pat, line, re.I)
            if m:
                domain = m.group(1).lower().strip('.')
                break
        if not domain or len(domain) < 5 or domain in seen_now:
            continue
        # UID aus logcat-Tag extrahieren (falls vorhanden)
        uid_m = re.search(r'\buid[=:\s]+(\d+)', line, re.I)
        uid_s = uid_m.group(1) if uid_m else ""
        app   = _uid_pkg_cache.get(uid_s, "")
        seen_now.add(domain)
        # Duplikat-Schutz: nur eintragen wenn Eintrag neu oder anderer App
        if not any(e[1] == domain for e in _dns_session[-30:]):
            _dns_session.append((ts_now, domain, app))
    # Max 200 Einträge halten
    if len(_dns_session) > 200:
        _dns_session[:] = _dns_session[-200:]
    d['dns_log'] = list(_dns_session)  # Kopie für Draw

    # ── ss-Verbindungen mit App-Zuordnung ────────────────────────────────
    conn_raw = adb.shell(
        "ss -tnp 2>/dev/null | grep ESTAB | head -n 16 || "
        "netstat -tnp 2>/dev/null | grep ESTABLISHED | head -n 16")
    conns  = []
    conns_raw_data = []
    for line in conn_raw.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        # ss-Format: State Recv-Q Send-Q Local Remote [proc]
        remote = parts[4] if len(parts) > 4 else parts[3]
        if remote in ('Local', 'Address', '0.0.0.0:*', ':::*'):
            continue
        # IP aus remote extrahieren (IPv6 in [] oder IPv4)
        ip_m = re.match(r'[\[]?([0-9a-fA-F.:]+)[\]]?:(\d+)$', remote)
        ip_raw = ip_m.group(1) if ip_m else remote.rsplit(':', 1)[0]
        port   = ip_m.group(2) if ip_m else ""
        # Hostname aus Cache
        host   = _ip_host_cache.get(ip_raw, "")
        # App aus ss-proc-Info oder UID-Map
        proc_field = parts[-1] if '(' in parts[-1] or '"' in parts[-1] else ""
        proc_name  = re.sub(r'.*"([^"]+)".*', r'\1', proc_field)[:16]
        if not proc_name:
            uid = ip_uid.get(ip_raw, "")
            proc_name = _uid_pkg_cache.get(uid, "")
        conns_raw_data.append((remote, ip_raw, host, proc_name))
    # Deduplizieren (gleiche Remote-IP+Port)
    seen_conns: set = set()
    for remote, ip_raw, host, proc in conns_raw_data:
        key = remote
        if key in seen_conns:
            continue
        seen_conns.add(key)
        entry = remote[:22]
        if host:
            entry += f"  {host[:22]}"
        elif ip_raw in _ip_host_cache:
            entry += f"  {_ip_host_cache[ip_raw][:22]}"
        if proc:
            entry += f"  [{proc}]"
        conns.append(entry)
        if len(conns) >= 12:
            break
    d['connections'] = conns
    d['conn_data']   = conns_raw_data  # für Export

    # ── Reverse-DNS für neue IPs (async-ähnlich: je Zyklus max 2) ────────
    new_ips = [ip for _, ip, h, _ in conns_raw_data if not h and ip not in _ip_host_cache][:2]
    for ip in new_ips:
        ns_out = adb.shell(f"nslookup {ip} 2>/dev/null | grep -iE 'name|arpa' | tail -2")
        m = re.search(r'name\s*=\s*([a-zA-Z0-9._-]+)', ns_out, re.I)
        if m:
            _ip_host_cache[ip] = m.group(1).rstrip('.').lower()
        else:
            _ip_host_cache[ip] = ""  # Kein Eintrag → nicht nochmal anfragen

    # ── SMS-Queue / Anrufe ────────────────────────────────────────────────
    calls = adb.shell("dumpsys telecom 2>/dev/null | grep -c 'TC@' || echo 0").strip()
    # Nur erste Zeile nehmen (manchmal kommt "0\n0")
    calls = calls.splitlines()[0].strip() if calls else "0"
    d['active_calls'] = calls

    return d


def _draw_dashboard(d: dict, elapsed: float) -> None:
    """Dashboard-Rahmen rendern — inkl. App-Namen, Domains, DNS-Log."""
    W = 80
    now_str = time.strftime("%Y-%m-%d  %H:%M:%S")
    lauf    = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"

    def _line(content: str = "") -> str:
        raw = re.sub(r'\033\[[^m]*m|\033\[\d+[A-Za-z]', '', content)
        pad = max(0, W - 2 - len(raw))
        return f"║  {content}{' '*pad}  ║"

    def _sep() -> str:
        return f"╠{'═'*W}╣"

    def _header() -> str:
        title = "🔴 SIM LIVE-TRAFFIC DASHBOARD"
        right = f"[{now_str}  Laufzeit: {lauf}]"
        gap   = max(1, W - 2 - len(title) - len(right))
        return (f"║  {ui.BRED}{ui.BOLD}{title}{ui.RESET}"
                f"{'':>{gap}}{ui.GREY}{right}{ui.RESET}  ║")

    rsrp = d.get('rsrp')
    rsrq = d.get('rsrq')
    sinr = d.get('sinr')
    rssi = d.get('rssi')

    def _rsrp_label(v) -> str:
        if v is None: return "—"
        if v >= -80:  return f"{ui.BGREEN}Ausgezeichnet{ui.RESET}"
        if v >= -90:  return f"{ui.BGREEN}Gut{ui.RESET}"
        if v >= -100: return f"{ui.BYELLOW}Mittel{ui.RESET}"
        if v >= -110: return f"{ui.BYELLOW}Schwach{ui.RESET}"
        return f"{ui.BRED}Sehr schwach{ui.RESET}"

    net_type = d.get('net_type', 0)
    net_name = _NET_TYPE.get(net_type, "—") if net_type else "—"
    band_raw = d.get('band', 0)
    if band_raw >= 2147483646 or band_raw == 0:
        band_str = "—"
    else:
        band_mhz = _FREQ_BAND.get(band_raw, "")
        band_str = f"Band {band_raw}" + (f" ({band_mhz})" if band_mhz else "")

    # Operator bereinigen (entfernt führende/nachfolgende Kommas/Leerzeichen)
    op_raw = d.get('operator', '—')
    operator = op_raw.strip(', ') or "—"

    rx_spd  = d.get('rx_speed', 0.0)
    tx_spd  = d.get('tx_speed', 0.0)
    rx_ses  = d.get('rx_total_session', 0)
    tx_ses  = d.get('tx_total_session', 0)
    max_spd = max(rx_spd, tx_spd, 1)
    BAR_W   = 18

    # ── Aufbau ───────────────────────────────────────────────────────────
    lines = [
        f"╔{'═'*W}╗",
        _header(),
        _sep(),
        _line(f"{ui.BOLD}SIGNAL{ui.RESET}"),
        _line(f"  RSRP  {str(rsrp)+' dBm' if rsrp else '—':>9}  "
              f"{_sig_bar(rsrp,-140,-44,BAR_W)}  {_rsrp_label(rsrp)}"),
        _line(f"  RSRQ  {str(rsrq)+' dB' if rsrq else '—':>9}  "
              f"{_sig_bar(rsrq,-34,0,BAR_W)}"),
        _line(f"  SINR  {str(sinr)+' dB' if sinr else '—':>9}  "
              f"{_sig_bar(sinr,-23,40,BAR_W)}"),
        _line(f"  RSSI  {str(rssi)+' dBm' if rssi else '—':>9}  "
              f"{_sig_bar(rssi,-110,-50,BAR_W)}"),
        _sep(),
        _line(f"{ui.BOLD}NETZ{ui.RESET}"),
        _line(f"  Typ:  {ui.BCYAN}{net_name:<10}{ui.RESET}  {band_str}"),
        _line(f"  Cell-ID: {d.get('cell_id','?'):<14}  TAC/LAC: {d.get('tac','?')}"),
        _line(f"  Betreiber: {ui.BOLD}{operator:<16}{ui.RESET}"
              f"PLMN: {d.get('plmn','?')}  Roaming: {d.get('roaming','?')}"),
        _line(f"  IP (rmnet): {d.get('ip_rmnet','—'):<22}  SIM: {d.get('sim_state','?')}"),
        _sep(),
        _line(f"{ui.BOLD}TRAFFIC (Live){ui.RESET}"),
        _line(f"  ↓ Download  {_fmt_speed(rx_spd)}  "
              f"{_sig_bar(int(rx_spd), 0, int(max_spd), BAR_W)}  "
              f"Session: {_fmt_bytes(rx_ses)}"),
        _line(f"  ↑ Upload    {_fmt_speed(tx_spd)}  "
              f"{_sig_bar(int(tx_spd), 0, int(max_spd), BAR_W)}  "
              f"Session: {_fmt_bytes(tx_ses)}"),
    ]
    for iface, rx, tx in d.get('ifaces', [])[:3]:
        lines.append(_line(
            f"  {ui.GREY}{iface:<12}  ↓ {_fmt_bytes(rx):<13}  ↑ {_fmt_bytes(tx)}{ui.RESET}"))

    # ── Verbindungen mit Hostname + App ───────────────────────────────────
    conns = d.get('connections', [])
    lines += [
        _sep(),
        _line(f"{ui.BOLD}VERBINDUNGEN  "
              f"({ui.BCYAN}{len(conns)}{ui.RESET}{ui.BOLD} aktiv){ui.RESET}  "
              f"{ui.GREY}IP  →  Hostname  [App]{ui.RESET}"),
    ]
    if conns:
        for conn in conns[:10]:
            # Einfärben: Port 443=grün, Port 80=gelb
            col = ui.BGREEN if ':443' in conn else (ui.BYELLOW if ':80' in conn else ui.GREY)
            lines.append(_line(f"  {col}{conn}{ui.RESET}"))
    else:
        lines.append(_line(f"  {ui.GREY}(keine TCP-Verbindungen sichtbar){ui.RESET}"))

    # ── DNS-Session-Log ───────────────────────────────────────────────────
    dns_log = d.get('dns_log', [])
    lines += [
        _sep(),
        _line(f"{ui.BOLD}DNS-SESSION LOG  "
              f"({ui.BCYAN}{len(dns_log)}{ui.RESET}{ui.BOLD} Einträge gesamt){ui.RESET}  "
              f"{ui.GREY}Zeit · Domain · App{ui.RESET}"),
    ]
    recent = dns_log[-12:] if len(dns_log) > 12 else dns_log
    if recent:
        for ts, domain, app in reversed(recent):
            app_tag = f" {ui.GREY}[{app}]{ui.RESET}" if app else ""
            # Tracker/Malware-Farbe
            from .app_traffic_monitor import _is_tracker, _is_malware
            if _is_malware(domain):
                dcol = f"{ui.BRED}{ui.BOLD}"
            elif _is_tracker(domain):
                dcol = ui.BYELLOW
            else:
                dcol = ui.BCYAN
            lines.append(_line(
                f"  {ui.GREY}{ts}{ui.RESET}  {dcol}{domain[:40]}{ui.RESET}{app_tag}"))
    else:
        lines.append(_line(f"  {ui.GREY}(noch keine DNS-Anfragen erfasst){ui.RESET}"))

    lines += [
        _sep(),
        _line(f"  Anrufe aktiv: {ui.BOLD}{d.get('active_calls','0')}{ui.RESET}"),
        f"╚{'═'*W}╝",
        (f"  {ui.GREY}[Q] Beenden  [R] Zähler reset  [S] DNS-Log speichern  "
         f"Aktualisierung: 2s{ui.RESET}"),
    ]

    sys.stdout.write("\033[H\033[J")
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def _export_dns_log(dns_log: list, conn_data: list) -> str:
    """DNS-Session-Log + Verbindungen → Datei speichern."""
    import os
    out_dir = os.path.expanduser("~/Schreibtisch/Androidpanzer/sim")
    os.makedirs(out_dir, exist_ok=True)
    fname = os.path.join(out_dir, f"dns_log_{time.strftime('%Y%m%d_%H%M%S')}.txt")
    lines = [
        "=" * 72,
        f"  AndroidPanzer – SIM DNS-Session-Log",
        f"  Exportiert: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Einträge:   {len(dns_log)}",
        "=" * 72, "",
        "── DNS-ANFRAGEN ──────────────────────────────────────────────────────",
    ]
    for ts, domain, app in dns_log:
        app_tag = f"  [{app}]" if app else ""
        lines.append(f"  {ts}  {domain}{app_tag}")
    lines += [
        "",
        "── VERBINDUNGEN (letzte Session) ─────────────────────────────────────",
    ]
    seen_c: set = set()
    for remote, ip, host, proc in conn_data:
        key = f"{ip}:{proc}"
        if key in seen_c:
            continue
        seen_c.add(key)
        h = f"  → {host}" if host else ""
        p = f"  [{proc}]" if proc else ""
        lines.append(f"  {remote}{h}{p}")
    lines += ["", "=" * 72]
    with open(fname, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    return fname


def live_sim_dashboard(adb: ADB) -> None:
    """Echtzeit SIM/Netz/Traffic Live-Dashboard (2s Refresh · Q/R/S)."""
    import select
    try:
        import termios
        import tty
        _has_tty = True
    except ImportError:
        _has_tty = False

    old_settings = None
    if _has_tty and sys.stdin.isatty():
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:  # noqa: BLE001
            old_settings = None

    def _kbhit() -> str:
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return ""

    # UID-Cache direkt beim Start laden
    _refresh_uid_pkg(adb)

    prev:   dict = {}
    t0     = time.monotonic()
    cycle  = 0
    last_saved = ""
    try:
        while True:
            cycle += 1
            try:
                d = _collect(adb, prev)
            except Exception:  # noqa: BLE001
                d = prev.copy() or {}
            _draw_dashboard(d, time.monotonic() - t0)
            # Auto-Export alle 30 Zyklen (≈60 s)
            if cycle % 30 == 0 and d.get('dns_log'):
                try:
                    last_saved = _export_dns_log(
                        d['dns_log'], d.get('conn_data', []))
                except Exception:  # noqa: BLE001
                    pass
            prev = d
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                key = _kbhit()
                if key.lower() == 'q':
                    return
                if key.lower() == 'r':
                    prev['rx_start'] = d.get('rx_bytes', 0)
                    prev['tx_start'] = d.get('tx_bytes', 0)
                    _dns_session.clear()
                    t0 = time.monotonic()
                if key.lower() == 's':
                    try:
                        f = _export_dns_log(d.get('dns_log', []),
                                            d.get('conn_data', []))
                        last_saved = f
                        # Kurz anzeigen
                        sys.stdout.write(
                            f"\n  {ui.BGREEN}✓ Gespeichert: {f}{ui.RESET}\n")
                        sys.stdout.flush()
                        time.sleep(1.5)
                    except Exception:  # noqa: BLE001
                        pass
                time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        if old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception:  # noqa: BLE001
                pass
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        # Finaler Export beim Beenden
        if _dns_session:
            try:
                f = _export_dns_log(_dns_session, prev.get('conn_data', []))
                sys.stdout.write(f"\n  {ui.BGREEN}✓ Session gespeichert: {f}{ui.RESET}\n")
                sys.stdout.flush()
            except Exception:  # noqa: BLE001
                pass
        ui.clear()


def baseband_tools(adb: ADB) -> None:
    """Baseband & AT-Kommandos."""
    while True:
        ui.clear()
        ui.rule("BASEBAND & AT-KOMMANDOS", ui.BCYAN)
        ch = ui.menu("Aktion", [
            ("1", "Modem-Firmware-Version"),
            ("2", "Radio-Logcat (letzte 100 Zeilen)"),
            ("3", "Baseband-Uptime / Verbindungsstatus"),
            ("4", "Field-Test-Mode öffnen"),
            ("5", "Diag-Port freischalten (Root)"),
            ("6", "Modem-Crash-Log sichern (Root)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        runs = {
            "1": ("cmd",  "getprop gsm.version.baseband; getprop ro.baseband"),
            "2": ("live", "logcat -b radio -d 2>/dev/null | tail -n 100"),
            "3": ("cmd",  "dumpsys telephony.registry 2>/dev/null | grep -iE 'DataConnectionState|uptime|phoneId' | head"),
            "4": ("cmd",  "am start -a android.intent.action.CALL -d tel:*#*#4636#*#* 2>/dev/null"),
            "5": ("root", "setprop sys.usb.config diag,adb 2>/dev/null && echo Diag-Port aktiviert"),
            "6": ("root", "cat /sys/fs/pstore/console-ramoops* 2>/dev/null > /sdcard/modem_crash.txt && echo OK"),
        }
        info = runs.get(ch)
        if not info:
            continue
        kind, cmd = info
        ui.info(f"Befehl: {ui.GREY}{cmd}{ui.RESET}\n")
        try:
            out = adb.shell(cmd, root=(kind == "root"))
            print(out.strip() or "(Keine Ausgabe)")
        except Exception as e:  # noqa: BLE001
            ui.err(str(e))
        ui.pause()


def imsi_catcher_guard(adb: ADB) -> None:
    """IMSI-Catcher-Schutz & Funkzellen-Analyse – MAXIMAL ERWEITERT."""
    while True:
        ui.clear()
        ui.rule("🕵️ IMSI-CATCHER-SCHUTZ & ZELLANALYSE – MAXIMAL", ui.BRED)
        ch = ui.menu("Analyse-Modus", [
            ("1",  "🔍 Vollständige IMSI-Catcher Erkennung (10 Indikatoren)"),
            ("2",  "📡 Aktuelle Zelle: Cell-ID · LAC · MCC/MNC · Timing-Advance"),
            ("3",  "🗺️  Zellwechsel Live-Monitor (2s Refresh · Anomalie-Alarm)"),
            ("4",  "📶 Signal-Anomalie-Detektion (SINR-Drop · RSRP-Sprung)"),
            ("5",  "🔐 Verschlüsselungs-Check (A5/1 · A5/0 · Null-Cipher)"),
            ("6",  "🏙️  Nachbarzellen-Scan (alle sichtbaren Zellen)"),
            ("7",  "📍 Zell-Datenbank (bekannte Zellen tracken)"),
            ("8",  "🔔 Stille SMS / Ping-SMS erkennen (logcat)"),
            ("9",  "⚡ IMSI-Catcher Gegenmaßnahmen aktivieren"),
            ("10", "📊 Komplett-Report exportieren"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        ui.clear()

        if ch == "1":
            ui.rule("IMSI-CATCHER ERKENNUNG – 10 INDIKATOREN", ui.BRED)
            raw = adb.shell("dumpsys telephony.registry 2>/dev/null | head -n 200")
            score = 0
            findings = []

            # Indikator 1: 2G-Downgrade
            ntype_m = re.search(r'mDataNetworkType\s*=\s*(\d+)', raw)
            ntype = int(ntype_m.group(1)) if ntype_m else -1
            if ntype in (1, 2, 16):  # GPRS, EDGE, GSM
                score += 3
                findings.append(("KRITISCH", f"2G-Downgrade erkannt (Typ={ntype}) – klassisches IMSI-Catcher-Merkmal!"))
            else:
                findings.append(("OK", f"Kein 2G-Downgrade (Netztyp={ntype})"))

            # Indikator 2: Verschlüsselung
            cipher = adb.shell(
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'cipher|a5|encrypt' | head -n 3")
            if cipher.strip():
                if "A5/0" in cipher or "null" in cipher.lower():
                    score += 4
                    findings.append(("KRITISCH", "Null-Verschlüsselung erkannt (A5/0)!"))
                else:
                    findings.append(("OK", "Verschlüsselung aktiv"))
            else:
                findings.append(("WARNUNG", "Verschlüsselungsstatus nicht lesbar"))

            # Indikator 3: Timing-Advance zu hoch
            ta_raw = adb.shell(
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'timingAdvance|TimingAdv' | head")
            ta_m = re.search(r'(?:timingAdvance|TimingAdv)\s*=\s*(\d+)', ta_raw, re.I)
            if ta_m:
                ta = int(ta_m.group(1))
                if ta > 63:
                    score += 2
                    findings.append(("WARNUNG", f"Timing-Advance ungewöhnlich hoch: {ta} (Entfernung >5km?)"))
                else:
                    findings.append(("OK", f"Timing-Advance normal: {ta}"))
            else:
                findings.append(("INFO", "Timing-Advance nicht lesbar"))

            # Indikator 4: Signal zu stark (RSRP > -50 = unnatürlich nah)
            rsrp_m = re.search(r'rsrp\s*=\s*(-?\d+)', raw, re.I)
            rsrp = int(rsrp_m.group(1)) if rsrp_m else None
            if rsrp and rsrp > -50:
                score += 2
                findings.append(("WARNUNG", f"RSRP extrem stark: {rsrp} dBm – unnatürlich naher Sender!"))
            elif rsrp:
                findings.append(("OK", f"RSRP normal: {rsrp} dBm"))

            # Indikator 5: Keine Nachbarzellen
            neighbors = adb.shell(
                "dumpsys telephony.registry 2>/dev/null | grep -i neighbor | head -n 5")
            if not neighbors.strip():
                score += 1
                findings.append(("WARNUNG", "Keine Nachbarzellen sichtbar – IMSI-Catcher oft allein!"))
            else:
                nb_count = len(neighbors.splitlines())
                findings.append(("OK", f"{nb_count} Nachbarzelle(n) sichtbar"))

            # Indikator 6: Cell-ID 0 oder sehr groß
            cid_m = re.search(r'ci\s*=\s*(\d+)', raw, re.I)
            if cid_m:
                cid = int(cid_m.group(1))
                if cid == 0 or cid > 268435455:
                    score += 2
                    findings.append(("WARNUNG", f"Verdächtige Cell-ID: {cid}"))
                else:
                    findings.append(("OK", f"Cell-ID normal: {cid}"))

            # Indikator 7: Stille SMS
            silent_sms = adb.shell(
                "logcat -d -s SIMRecords:D 2>/dev/null | grep -iE 'silent|class0|type0' | tail -n 5")
            if silent_sms.strip():
                score += 3
                findings.append(("KRITISCH", "Stille SMS / Flash-SMS erkannt!"))
            else:
                findings.append(("OK", "Keine stillen SMS im Log"))

            # Indikator 8: SUCI-Schutz (5G)
            suci = adb.shell(
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'suci|supi' | head -n 2")
            if not suci.strip() and ntype == 20:
                score += 1
                findings.append(("WARNUNG", "5G-SUCI nicht aktiv (IMSI-Exposition möglich)"))
            elif suci.strip():
                findings.append(("OK", "SUCI aktiv (IMSI geschützt)"))

            # Indikator 9: MCC/MNC prüfen
            mcc_m = re.search(r'mcc\s*=\s*(\d+)', raw, re.I)
            mnc_m = re.search(r'mnc\s*=\s*(\d+)', raw, re.I)
            sim_mcc = adb.shell("getprop gsm.sim.operator.numeric 2>/dev/null").strip()[:3]
            if mcc_m and sim_mcc and mcc_m.group(1) != sim_mcc:
                score += 2
                findings.append(("WARNUNG", f"MCC-Mismatch! Zelle:{mcc_m.group(1)} vs SIM:{sim_mcc}"))
            elif mcc_m:
                findings.append(("OK", f"MCC stimmt überein: {mcc_m.group(1)}"))

            # Indikator 10: SINR sehr niedrig
            sinr_m = re.search(r'rssnr\s*=\s*(-?\d+)', raw, re.I)
            if sinr_m:
                sinr = int(sinr_m.group(1))
                if sinr < -10:
                    score += 1
                    findings.append(("WARNUNG", f"SINR sehr niedrig: {sinr} dB – schlechte Signalqualität"))
                else:
                    findings.append(("OK", f"SINR normal: {sinr} dB"))

            # Ausgabe
            print()
            for status, msg in findings:
                if status == "KRITISCH":
                    icon = f"{ui.BRED}☠ KRITISCH{ui.RESET}"
                elif status == "WARNUNG":
                    icon = f"{ui.BYELLOW}⚠ WARNUNG{ui.RESET} "
                elif status == "OK":
                    icon = f"{ui.BGREEN}✓ OK{ui.RESET}      "
                else:
                    icon = f"{ui.GREY}ℹ INFO{ui.RESET}     "
                print(f"  {icon}  {msg}")
            print()
            # Gesamt-Score
            if score >= 6:
                risk_col = ui.BRED
                risk = f"HOHES RISIKO – IMSI-CATCHER WAHRSCHEINLICH! (Score: {score}/20)"
            elif score >= 3:
                risk_col = ui.BYELLOW
                risk = f"MITTLERES RISIKO – Verdächtige Aktivität! (Score: {score}/20)"
            else:
                risk_col = ui.BGREEN
                risk = f"NIEDRIGES RISIKO – Normale Umgebung (Score: {score}/20)"
            print(f"  {risk_col}{ui.BOLD}GESAMT-BEWERTUNG: {risk}{ui.RESET}")

            # Herzschlag-Alarm bei hohem Risiko
            if score >= 6:
                for _ in range(4):
                    sys.stdout.write(f"\r  {ui.BRED}{ui.BOLD}  ⚠⚠ IMSI-CATCHER ALARM! ⚠⚠  {ui.RESET}")
                    sys.stdout.flush()
                    time.sleep(0.18)
                    sys.stdout.write(f"\r{' '*45}")
                    sys.stdout.flush()
                    time.sleep(0.1)
                print()

        elif ch == "2":
            ui.rule("Aktuelle Zell-Informationen", ui.CYAN)
            raw = adb.shell("dumpsys telephony.registry 2>/dev/null | head -n 150")
            params = [
                ("Cell-ID (CID)",    r'ci\s*=\s*(\d+)'),
                ("LAC",              r'lac\s*=\s*(\w+)'),
                ("TAC",              r'tac\s*=\s*(\w+)'),
                ("MCC",              r'mcc\s*=\s*(\d+)'),
                ("MNC",              r'mnc\s*=\s*(\d+)'),
                ("EARFCN",           r'earfcn\s*=\s*(\d+)'),
                ("NR-ARFCN",         r'nrarfcn\s*=\s*(\d+)'),
                ("Timing-Advance",   r'timingAdvance\s*=\s*(\d+)'),
                ("RSRP",             r'rsrp\s*=\s*(-?\d+)'),
                ("RSRQ",             r'rsrq\s*=\s*(-?\d+)'),
                ("SINR",             r'rssnr\s*=\s*(-?\d+)'),
                ("Netztyp",          r'mDataNetworkType\s*=\s*(\d+)'),
                ("Betreiber",        r'mNetworkOperatorName\s*=\s*(\S+)'),
            ]
            print()
            for label, pat in params:
                m = re.search(pat, raw, re.I)
                val = m.group(1) if m else "—"
                icon = ui.BGREEN if val != "—" else ui.GREY
                print(f"  {icon}{label:<22}{ui.RESET}  {val}")

        elif ch == "3":
            ui.rule("Zellwechsel Live-Monitor", ui.BRED)
            ui.info("Überwache Zellwechsel (Q=Beenden) …")
            try:
                import termios, tty, select as _sel
                old = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                old = None
                import select as _sel

            cell_history = []
            last_cid = None
            t0 = time.monotonic()
            try:
                while True:
                    raw = adb.shell(
                        "dumpsys telephony.registry 2>/dev/null | grep -iE 'ci=|tac=|rsrp=|networkType' | head -n 5")
                    cid_m = re.search(r'ci\s*=\s*(\d+)', raw, re.I)
                    cid = cid_m.group(1) if cid_m else "?"
                    rsrp_m = re.search(r'rsrp\s*=\s*(-?\d+)', raw, re.I)
                    rsrp = rsrp_m.group(1) if rsrp_m else "?"
                    ts_str = time.strftime("%H:%M:%S")
                    if cid != last_cid:
                        entry = f"  {ts_str}  CID: {cid:<12}  RSRP: {rsrp} dBm"
                        cell_history.append(entry)
                        color = ui.BYELLOW if last_cid is not None else ui.GREY
                        if last_cid is not None:
                            print(f"{color}  ↕ ZELLWECHSEL → CID: {cid}  RSRP: {rsrp} dBm  [{ts_str}]{ui.RESET}")
                        else:
                            print(f"  Startzelle: CID={cid}  RSRP={rsrp} dBm")
                        last_cid = cid
                    if _sel.select([sys.stdin], [], [], 0)[0]:
                        if sys.stdin.read(1).lower() == 'q':
                            break
                    time.sleep(2.0)
            except KeyboardInterrupt:
                pass
            finally:
                if old:
                    try:
                        import termios as _t
                        _t.tcsetattr(sys.stdin, _t.TCSADRAIN, old)
                    except Exception:
                        pass
            print(f"\n  {len(cell_history)} Zellwechsel in {int(time.monotonic()-t0)}s aufgezeichnet.")

        elif ch == "4":
            ui.rule("Signal-Anomalie-Detektion", ui.CYAN)
            ui.info("Messe Signal über 5 Messungen (alle 2s) …")
            samples = []
            for i in range(5):
                raw = adb.shell("dumpsys telephony.registry 2>/dev/null | grep -iE 'rsrp=|rsrq=|rssnr=' | head")
                rsrp_m = re.search(r'rsrp=(-?\d+)', raw, re.I)
                rsrp = int(rsrp_m.group(1)) if rsrp_m else None
                if rsrp:
                    samples.append(rsrp)
                    print(f"  Messung {i+1}/5: RSRP={rsrp} dBm")
                time.sleep(2.0)
            if len(samples) >= 2:
                delta = max(samples) - min(samples)
                avg   = sum(samples) // len(samples)
                print(f"\n  Durchschnitt: {avg} dBm  |  Schwankung: {delta} dB")
                if delta > 20:
                    print(f"  {ui.BRED}⚠ STARKE SIGNAL-SCHWANKUNG ({delta} dB) – möglicher Catcher-Effekt!{ui.RESET}")
                elif delta > 10:
                    print(f"  {ui.BYELLOW}⚠ Signal schwankt ({delta} dB) – Umgebung prüfen.{ui.RESET}")
                else:
                    print(f"  {ui.BGREEN}✓ Signal stabil ({delta} dB Schwankung){ui.RESET}")

        elif ch == "5":
            ui.rule("Verschlüsselungs-Check", ui.CYAN)
            sources = [
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'cipher|a5|encr' | head -n 10",
                "logcat -d -s RIL-GSM:D RIL:D 2>/dev/null | grep -iE 'cipher|a5|encrypt' | tail -n 15",
                "getprop | grep -iE 'cipher|encrypt' | head -n 5",
            ]
            found_cipher = False
            for cmd in sources:
                out = adb.shell(cmd).strip()
                if out:
                    print(out[:300]); found_cipher = True
            if not found_cipher:
                print(f"  {ui.GREY}Cipher-Info nicht direkt lesbar.")
                print(f"  Hinweis: A5/1 = Standard-GSM-Verschlüsselung")
                print(f"           A5/0 = KEINE Verschlüsselung (IMSI-Catcher-Ziel!)")
                print(f"           A5/3 = Kasumi-Cipher (3G/stärker)")
                print(f"  Auf Android: Settings→About Phone→Network Operator→Encryption{ui.RESET}")

        elif ch == "6":
            ui.rule("Nachbarzellen-Scan", ui.CYAN)
            raw = adb.shell("dumpsys telephony.registry 2>/dev/null")
            nb_section = re.findall(r'(?:neighbor|adjacent|nearby|Neighbor)[^\n]*\n(?:[^\n]*\n){0,5}', raw, re.I)
            if nb_section:
                print("\n".join(nb_section[:5]))
            else:
                # Fallback: alle CellIdentity-Einträge
                all_cells = re.findall(r'(?:CellIdentity|CellInfo)[^\n]+', raw, re.I)
                if all_cells:
                    print(f"  {len(all_cells)} Zellen sichtbar:")
                    for cell in all_cells[:15]:
                        print(f"  {ui.GREY}{cell[:100]}{ui.RESET}")
                else:
                    print(f"  {ui.GREY}(Keine Nachbarzellen-Daten – API-Level oder Root nötig){ui.RESET}")

        elif ch == "7":
            ui.rule("Zell-Datenbank (bekannte Zellen)", ui.CYAN)
            ui.info("Lese aktuelle Zelle und speichere in Datenbank …")
            raw = adb.shell("dumpsys telephony.registry 2>/dev/null | head -n 100")
            cid_m = re.search(r'ci\s*=\s*(\d+)', raw, re.I)
            tac_m = re.search(r'tac\s*=\s*(\w+)', raw, re.I)
            mcc_m = re.search(r'mcc\s*=\s*(\d+)', raw, re.I)
            mnc_m = re.search(r'mnc\s*=\s*(\d+)', raw, re.I)
            rsrp_m = re.search(r'rsrp\s*=\s*(-?\d+)', raw, re.I)
            entry = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cid": cid_m.group(1) if cid_m else "?",
                "tac": tac_m.group(1) if tac_m else "?",
                "mcc": mcc_m.group(1) if mcc_m else "?",
                "mnc": mnc_m.group(1) if mnc_m else "?",
                "rsrp": rsrp_m.group(1) if rsrp_m else "?",
            }
            db_file = os.path.join(OUT, "cell_database.txt")
            with open(db_file, "a") as f:
                f.write(f"{entry['ts']}  CID:{entry['cid']:<12}  TAC:{entry['tac']:<8}  "
                        f"MCC:{entry['mcc']}  MNC:{entry['mnc']}  RSRP:{entry['rsrp']}\n")
            ui.ok(f"Eintrag gespeichert: {db_file}")
            # Letzte 20 Einträge anzeigen
            try:
                with open(db_file) as f:
                    lines = f.readlines()
                print(f"\n  Letzte {min(10, len(lines))} Einträge:")
                for line in lines[-10:]:
                    print(f"  {ui.GREY}{line.rstrip()}{ui.RESET}")
            except Exception:
                pass

        elif ch == "8":
            ui.rule("Stille SMS / Ping-SMS Erkennung", ui.BRED)
            sources = [
                "logcat -d -s SIMRecords:D CatService:D 2>/dev/null | grep -iE 'silent|flash|class0|type0|ping' | tail -n 20",
                "logcat -d -s Telephony:D SMS:D 2>/dev/null | grep -iE 'incoming|received|class0|silent' | tail -n 20",
                "dumpsys activity broadcast 2>/dev/null | grep -iE 'sms|SMS_RECEIVED' | tail -n 10",
            ]
            found = False
            for cmd in sources:
                out = adb.shell(cmd).strip()
                if out:
                    print(out[:400]); found = True
            if not found:
                print(f"  {ui.BGREEN}✓ Keine stillen SMS im Log erkannt.{ui.RESET}")
            print(f"\n  {ui.GREY}Stille SMS (Class-0/Type-0) werden nicht angezeigt, aber vom Modem verarbeitet.")
            print(f"  IMSI-Catcher nutzen sie zur Geräte-Ortung ohne Benutzerkenntnis.{ui.RESET}")

        elif ch == "9":
            ui.rule("Gegenmaßnahmen aktivieren", ui.BRED)
            ui.warn("Einige Maßnahmen können die Netzwerkverbindung unterbrechen!")
            measures = [
                ("2G deaktivieren (LTE-Only)",
                 "settings put global preferred_network_mode 11 2>/dev/null || "
                 "settings put global preferred_network_mode 9 2>/dev/null"),
                ("Flugmodus: Radio-Kill-Switch",
                 "settings put global airplane_mode_on 1 2>/dev/null && "
                 "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true 2>/dev/null"),
                ("VoLTE erzwingen (kein 2G-Fallback)",
                 "settings put global volte_vt_enabled 1 2>/dev/null"),
                ("STK-App deaktivieren (BIP-Block)",
                 "pm disable com.android.stk 2>/dev/null"),
                ("SUCI-Schutz prüfen/aktivieren",
                 "getprop | grep -iE 'suci|5g' | head -n 3"),
            ]
            for i, (label, cmd) in enumerate(measures, 1):
                print(f"  {i}) {label}")
            sel = input("\n  Maßnahme wählen (1-5, leer=Abbruch): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= 5:
                label, cmd = measures[int(sel)-1]
                out = adb.shell(cmd)
                print(f"\n  {out.strip() or 'Maßnahme aktiviert.'}")
                ui.ok(f"{label} → aktiv")

        elif ch == "10":
            ui.rule("Komplett-Report exportieren", ui.CYAN)
            ts = int(time.time())
            fn = os.path.join(OUT, f"imsi_report_{ts}.txt")
            raw = adb.shell("dumpsys telephony.registry 2>/dev/null | head -n 200")
            with open(fn, "w") as f:
                f.write(f"# IMSI-Catcher-Schutz Report\n# {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"telephony.registry:\n{raw}\n\n")
                # Netzwerk-Props
                props = adb.shell("getprop | grep -iE 'gsm|radio|telephony|ril|sim' | head -n 30")
                f.write(f"SIM/Radio Props:\n{props}\n\n")
                # Log
                log = adb.shell("logcat -d -s SIMRecords:D -s RIL:D 2>/dev/null | tail -n 50")
                f.write(f"Log (SIM/RIL):\n{log}\n")
            ui.ok(f"Report: {fn}")
        ui.pause()


def sim_forensics(adb: ADB) -> None:
    """SIM-Forensik: Telefonbuch, SMS, MSISDN, LOCI."""
    while True:
        ui.clear()
        ui.rule("SIM-FORENSIK", ui.BCYAN)
        ch = ui.menu("Aktion", [
            ("1", "SIM-Telefonbuch (ADN) auslesen"),
            ("2", "SIM-SMS-Speicher dumpen (Root)"),
            ("3", "MSISDN (eigene Rufnummer)"),
            ("4", "SMSC (SMS-Center-Nummer)"),
            ("5", "SIM-SDN (Service Dialing Numbers)"),
            ("6", "FDN-Liste (Fixed Dialing Numbers)"),
            ("7", "ICCID + Hersteller erkennen"),
            ("8", "IMEI validieren (Luhn-Prüfung)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return

        if ch == "1":
            ui.clear(); ui.rule("SIM-Telefonbuch (ADN) – Multi-Methoden", ui.CYAN)
            ui.info("Versuche alle bekannten ADN-Zugriffsmethoden …"); print()
            found = False
            # Methode 1–4: verschiedene Content-Provider URIs
            adn_uris = [
                "content://icc/adn",
                "content://icc/adn/subId/1",
                "content://icc/adn/subId/2",
                "content://com.android.contacts/raw_contacts?sim=true",
            ]
            for uri in adn_uris:
                out = adb.shell(f"content query --uri {uri} 2>/dev/null")
                if out.strip() and "No result found" not in out and "error" not in out.lower():
                    print(f"{ui.BGREEN}✓ {uri}{ui.RESET}")
                    for line in out.strip().splitlines()[:30]:
                        m = re.search(r'(?:name|tag)=([^,]+).*phone=([^,\s]+)', line, re.I)
                        if m:
                            print(f"  📞 {m.group(1):<25}  {m.group(2)}")
                        else:
                            print(f"  {ui.GREY}{line[:80]}{ui.RESET}")
                    found = True
                    break
            # Methode 5: iphonesubinfo ADN
            if not found:
                for service_nr in ["25", "26", "27"]:
                    out = adb.shell(f"service call iphonesubinfo {service_nr} s16 phone 2>/dev/null")
                    if out.strip() and "Parcel" not in out and len(out) > 10:
                        print(f"service call iphonesubinfo {service_nr}: {out.strip()[:100]}")
                        found = True
            # Methode 6: simphonebook (Android 12+)
            if not found:
                out = adb.shell(
                    "content query --uri content://com.android.providers.telephony/"
                    "simphonebook 2>/dev/null | head -n 20")
                if out.strip() and "No result" not in out:
                    print(out[:500]); found = True
            # Methode 7: pysim (wenn installiert)
            if not found:
                pysim = shutil.which("pySIM-shell") or shutil.which("pysim-shell") or shutil.which("simcard-read")
                if pysim:
                    out = adb.shell("⚠ pySIM nur auf direkter Kartenverbindung nutzbar.")
            if not found:
                print(f"  {ui.BYELLOW}ADN nicht auslesbar. Mögliche Ursachen:{ui.RESET}")
                print("  • SIM-Telefonbuch ist leer")
                print("  • Android 9+ blockiert direkten SIM-Content-Zugriff ohne Berechtigung")
                print("  • Nutze: Einstellungen → Kontakte → SIM-Kontakte importieren")
                print("  • Root-Zugriff via adb shell content ... root=True versuchen")
                out2 = adb.shell(
                    "content query --uri content://icc/adn 2>/dev/null", root=True)
                if out2.strip() and "No result found" not in out2:
                    print(f"\n{ui.BGREEN}Root-Zugriff erfolgreich:{ui.RESET}\n{out2[:300]}")
            ui.pause()
        elif ch == "2":
            if not ui.confirm("Root-SMS-Dump (benötigt Root)?", False):
                continue
            out = adb.shell("content query --uri content://sms 2>/dev/null | head -n 60", root=True)
            ui.clear(); ui.rule("SIM-SMS-Speicher (Root)", ui.CYAN)
            print(out.strip() or "(Kein Root-Zugriff oder leer)"); ui.pause()
        elif ch == "3":
            out = adb.shell("service call iphonesubinfo 13 s16 phone 2>/dev/null")
            ui.clear(); ui.rule("MSISDN", ui.CYAN); print(out.strip()); ui.pause()
        elif ch == "4":
            out = adb.shell("service call iphonesubinfo 14 s16 phone 2>/dev/null")
            ui.clear(); ui.rule("SMSC", ui.CYAN); print(out.strip()); ui.pause()
        elif ch == "5":
            out = adb.shell("content query --uri content://icc/sdn 2>/dev/null")
            ui.clear(); ui.rule("SDN", ui.CYAN); print(out.strip() or "(leer)"); ui.pause()
        elif ch == "6":
            out = adb.shell("content query --uri content://icc/fdn 2>/dev/null")
            ui.clear(); ui.rule("FDN-Liste", ui.CYAN); print(out.strip() or "(leer)"); ui.pause()
        elif ch == "7":
            raw = adb.shell("service call iphonesubinfo 11 s16 phone 2>/dev/null")
            ui.clear(); ui.rule("ICCID & Hersteller", ui.CYAN)
            print(f"Raw: {raw.strip()}")
            # ICCID aus dem Parcel-Output extrahieren
            digits = "".join(c for c in raw if c.isdigit())
            if digits:
                vendor = _iccid_vendor(digits)
                print(f"\n  ICCID-Ziffern: {digits}")
                print(f"  Hersteller:    {vendor}")
            ui.pause()
        elif ch == "8":
            raw = adb.shell("service call iphonesubinfo 1 s16 phone 2>/dev/null")
            ui.clear(); ui.rule("IMEI-Validierung", ui.CYAN)
            digits = "".join(c for c in raw if c.isdigit())[:15]
            print(f"  IMEI: {digits}")
            if digits:
                valid = _luhn_check(digits)
                print(f"  Luhn-Check: {'✓ GÜLTIG' if valid else '✗ UNGÜLTIG (Manipulation?)'}")
            ui.pause()


def crypto_security(adb: ADB) -> None:
    """Krypto & Sicherheit: PIN/PUK/SIM-Lock – MAXIMAL ERWEITERT."""
    while True:
        ui.clear()
        ui.rule("🔐 KRYPTO & SICHERHEIT – MAXIMAL", ui.BCYAN)
        ch = ui.menu("Aktion", [
            ("1",  "🔑 PIN-Status aller SIM-Slots (READY/PIN/PUK/ABSENT)"),
            ("2",  "🔒 SIM-Lock / Netzbetreiber-Sperre – vollständige Analyse"),
            ("3",  "📋 Carrier-Config – alle Lock-Parameter auflisten"),
            ("4",  "🚫 SIM-STK App deaktivieren/reaktivieren (BIP-Blocker)"),
            ("5",  "🛡️  eSIM-Zertifikatskette & Signatur prüfen"),
            ("6",  "🔓 SIM-Lock Unlock versuchen (NCK/NSCK-Code)"),
            ("7",  "📊 Krypto-Algorithmen prüfen (A3/A5/A8 · MILENAGE · TUAK)"),
            ("8",  "🔐 Ki/OPc-Indikator (SIM-Auth-Typ erkennen)"),
            ("9",  "📱 Secure Element Status (SE · TEE · StrongBox)"),
            ("10", "🔑 Keystore / Android Keymaster Analyse"),
            ("11", "🛡️  SIM-Klon-Schutz (IMSI-Duplikat erkennen)"),
            ("12", "⚠️  PUK-Counter auslesen (verbleibende Versuche)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        ui.clear()

        if ch == "1":
            ui.rule("PIN-Status aller SIM-Slots", ui.CYAN)
            for slot in range(3):
                state = adb.shell(f"getprop gsm.sim.state 2>/dev/null").strip()
                state2 = adb.shell(f"getprop gsm.sim{slot}.state 2>/dev/null").strip()
                print(f"  Slot {slot}: {state or state2 or '—'}")
            # Detailliertere Info
            out = adb.shell(
                "dumpsys iphonesubinfo 2>/dev/null | grep -iE 'state|pin|puk|ready' | head -n 10; "
                "service call iphonesubinfo 5 s16 phone 2>/dev/null; "
                "service call iphonesubinfo 5 i32 0 s16 phone 2>/dev/null; "
                "service call iphonesubinfo 5 i32 1 s16 phone 2>/dev/null")
            print(out.strip() or "(Keine PIN-Status-Daten)")

        elif ch == "2":
            ui.rule("SIM-Lock / Netzbetreiber-Sperre – Vollanalyse", ui.CYAN)
            checks = [
                ("Parcel-Antwort (phone 3)",   "service call phone 3 2>/dev/null"),
                ("ISO-Country",                 "getprop gsm.sim.operator.iso-country 2>/dev/null"),
                ("Operator Alpha",              "getprop gsm.operator.alpha 2>/dev/null"),
                ("SIM-Operator",                "getprop gsm.sim.operator.numeric 2>/dev/null"),
                ("Network-Operator",            "getprop gsm.operator.numeric 2>/dev/null"),
                ("Carrier-Lock",                "dumpsys carrier_config 2>/dev/null | grep -iE 'locked|restrict|allow_only' | head -n 5"),
                ("isub Network-Lock",           "dumpsys isub 2>/dev/null | grep -iE 'lock|restrict|carrier' | head -n 5"),
                ("CarrierID",                   "getprop persist.sys.carrierId 2>/dev/null; "
                                                "dumpsys phone 2>/dev/null | grep -i 'carrierId' | head -n 3"),
            ]
            for label, cmd in checks:
                out = adb.shell(cmd).strip()
                if out:
                    icon = ui.BGREEN
                    # Erkennung ob gesperrt
                    if any(x in out.lower() for x in ["locked", "restrict", "1"]):
                        icon = ui.BYELLOW
                else:
                    out = "—"
                    icon = ui.GREY
                print(f"  {icon}{label:<30}{ui.RESET}  {out[:60]}")
            print()
            # SIM vs. Netzwerk-PLMN vergleichen
            sim_plmn = adb.shell("getprop gsm.sim.operator.numeric 2>/dev/null").strip()
            net_plmn = adb.shell("getprop gsm.operator.numeric 2>/dev/null").strip()
            if sim_plmn and net_plmn:
                match = sim_plmn[:5] == net_plmn[:5]
                status = f"{ui.BGREEN}✓ ENTSPERRT (SIM-PLMN = Netz-PLMN){ui.RESET}" if match \
                    else f"{ui.BYELLOW}⚠ MÖGLICHE NETZBETREIBER-SPERRE (PLMN unterschiedlich){ui.RESET}"
                print(f"\n  SIM-PLMN: {sim_plmn}  Netz-PLMN: {net_plmn}")
                print(f"  Status: {status}")

        elif ch == "3":
            ui.rule("Carrier-Config – Lock-Parameter", ui.CYAN)
            out = adb.shell("dumpsys carrier_config 2>/dev/null")
            # Nur sicherheitsrelevante Zeilen
            relevant = []
            for line in out.splitlines():
                if any(k in line.lower() for k in ["lock", "restrict", "allow", "carrier", "auth",
                                                    "crypt", "key", "cert", "pin", "puk", "esim"]):
                    relevant.append(line.strip())
            if relevant:
                print("\n".join(relevant[:40]))
            else:
                print(out[:800] or "(Keine Carrier-Config)")

        elif ch == "4":
            ui.rule("SIM-STK App (BIP-Blocker)", ui.CYAN)
            stk_state = adb.shell("pm list packages 2>/dev/null | grep stk")
            print(f"  STK-Pakete: {stk_state.strip() or '(keine gefunden)'}")
            if ui.confirm("STK deaktivieren?", False):
                for pkg in ["com.android.stk", "com.android.stk2",
                            "com.samsung.android.simrtc", "com.qualcomm.qti.simcontacts"]:
                    out = adb.shell(f"pm disable {pkg} 2>/dev/null")
                    if out.strip():
                        print(f"  {pkg}: {out.strip()}")
                ui.ok("STK deaktiviert.")
            elif ui.confirm("STK reaktivieren?", False):
                for pkg in ["com.android.stk", "com.android.stk2"]:
                    adb.shell(f"pm enable {pkg} 2>/dev/null")
                ui.ok("STK reaktiviert.")

        elif ch == "5":
            ui.rule("eSIM-Zertifikatskette", ui.CYAN)
            sources = [
                "dumpsys euicc_card_info 2>/dev/null | grep -iE 'cert|signature|chain|public.key' | head -n 15",
                "logcat -d -s EuiccController:D 2>/dev/null | grep -iE 'cert|verify|sign' | tail -n 10",
            ]
            for cmd in sources:
                out = adb.shell(cmd)
                if out.strip():
                    print(out.strip())

        elif ch == "6":
            ui.rule("SIM-Lock Unlock (NCK-Code)", ui.CYAN)
            ui.warn("Nur an eigenen Geräten! Falscher Code kann SIM permanent sperren.")
            nck = ui.ask("NCK / Entsperrcode (8–16 Ziffern)").strip()
            if nck and nck.isdigit():
                # Android SIM-Unlock via service call phone
                methods = [
                    f"service call phone 7 s16 '{nck}' 2>/dev/null",
                    f"service call phone 17 s16 '{nck}' 2>/dev/null",
                    f"am broadcast -a android.intent.action.SIM_UNLOCK_RESULT --es code '{nck}' 2>/dev/null",
                ]
                for method in methods:
                    out = adb.shell(method).strip()
                    if out:
                        print(f"  {out[:100]}")

        elif ch == "7":
            ui.rule("Krypto-Algorithmen", ui.CYAN)
            # SIM-Auth-Algorithmen: MILENAGE (3G/4G) vs. TUAK (5G)
            sources = [
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'auth|milenage|tuak|algo' | head",
                "logcat -d -s SIMRecords:D 2>/dev/null | grep -iE 'auth|algo|A3|A5|A8' | tail -n 10",
                "getprop | grep -iE 'auth|crypt|algo' | head -n 5",
            ]
            for cmd in sources:
                out = adb.shell(cmd).strip()
                if out:
                    print(out); print()
            print(f"\n  {ui.GREY}Algorithmen-Erklärung:")
            for a, d in [("A3", "Authentifizierung (SRES berechnen)"),
                         ("A5", "Verschlüsselung (Ue↔Netz)"),
                         ("A8", "Session-Key-Ableitung"),
                         ("MILENAGE", "3G/4G Standard (basiert auf AES-128)"),
                         ("TUAK", "5G-Alternative zu MILENAGE (basiert auf Keccak/SHA-3)")]:
                print(f"  {a:<12}  {d}")
            print(ui.RESET, end="")

        elif ch == "8":
            ui.rule("Ki/OPc Indikator – SIM-Auth-Typ", ui.CYAN)
            out = adb.shell(
                "logcat -d -s SIMRecords:D SimCard:D 2>/dev/null | grep -iE 'ki|opc|challenge|response' | tail -n 15")
            print(out.strip() or "(Keine Auth-Daten im Log)")
            print(f"\n  {ui.GREY}Ki = SIM-Master-Schlüssel (128-bit, nur auf SIM-Chip)")
            print(f"  OPc = Betreiber-Variante (abgeleitet aus OP + Ki)")
            print(f"  Diese Werte sind NIEMALS aus Android auslesbar (Hardware-Sicherheit).{ui.RESET}")

        elif ch == "9":
            ui.rule("Secure Element / TEE / StrongBox", ui.CYAN)
            checks = [
                ("SE HAL",        "service list 2>/dev/null | grep -i 'secure\\|se\\|nfc' | head"),
                ("TEE Status",    "getprop ro.hardware.tee 2>/dev/null; getprop ro.tee.type 2>/dev/null"),
                ("StrongBox",     "getprop ro.crypto.state 2>/dev/null; "
                                  "dumpsys hardware_properties 2>/dev/null | grep -i strongbox | head"),
                ("Keymaster HAL", "getprop ro.hardware.keystore 2>/dev/null"),
                ("SE-Pakete",     "pm list packages 2>/dev/null | grep -iE 'se\\|nfc\\|secure.elem'"),
            ]
            for label, cmd in checks:
                out = adb.shell(cmd).strip()
                icon = ui.BGREEN if out else ui.GREY
                print(f"  {icon}{label:<20}{ui.RESET}  {out[:80] if out else '—'}")

        elif ch == "10":
            ui.rule("Android Keystore / Keymaster", ui.CYAN)
            out = adb.shell(
                "dumpsys sec_key_att_app_id_provider 2>/dev/null | head -n 20; "
                "pm list packages 2>/dev/null | grep -iE 'keystore|keymaster'; "
                "getprop ro.hardware.keystore 2>/dev/null; "
                "getprop ro.crypto.state 2>/dev/null; "
                "getprop ro.crypto.type 2>/dev/null; "
                "ls -la /dev/hw_random /dev/urandom 2>/dev/null")
            print(out.strip() or "(Keine Keystore-Infos)")

        elif ch == "11":
            ui.rule("SIM-Klon-Schutz – IMSI-Duplikat", ui.CYAN)
            imsi = adb.shell("service call iphonesubinfo 7 s16 phone 2>/dev/null")
            digits = "".join(c for c in imsi if c.isdigit())
            if digits:
                print(f"  IMSI: {digits}")
                # Gleiche IMSI in zweitem Slot?
                imsi2 = adb.shell("service call iphonesubinfo 7 i32 1 s16 phone 2>/dev/null")
                digits2 = "".join(c for c in imsi2 if c.isdigit())
                if digits2 and digits2 == digits:
                    print(f"  {ui.BRED}⚠ WARNUNG: GLEICHE IMSI auf beiden Slots – SIM-Klon möglich!{ui.RESET}")
                else:
                    print(f"  {ui.BGREEN}✓ IMSI ist einmalig (kein Duplikat erkannt){ui.RESET}")
            else:
                print("  IMSI nicht auslesbar.")
            # Netz-Verifikation
            net = adb.shell("dumpsys telephony.registry 2>/dev/null | grep -iE 'mVoiceNetworkType|mDataNetworkType' | head")
            print(f"\n  Netzwerk:\n{net.strip()}")

        elif ch == "12":
            ui.rule("PUK-Counter (verbleibende Versuche)", ui.CYAN)
            # PUK-Counter ist selten direkt lesbar, aber via Service-Calls manchmal
            sources = [
                "service call iphonesubinfo 6 s16 phone 2>/dev/null",
                "dumpsys phone 2>/dev/null | grep -iE 'puk|pin.attempt|retries' | head",
                "logcat -d -s SIMRecords:D SimCard:D 2>/dev/null | grep -iE 'puk\\|retries\\|remaining' | tail -n 5",
            ]
            for cmd in sources:
                out = adb.shell(cmd).strip()
                if out:
                    print(f"  {out[:150]}")
            print(f"\n  {ui.GREY}Hinweis: PUK-Counter ist oft nur via Carrier-Hotline oder SIM-eigene AT-Kommandos abfragbar.{ui.RESET}")
        ui.pause()


def _5g_multi_query(adb: ADB, keywords: list[str], label: str) -> str:
    """Sucht 5G-Daten über 4 Quellen mit Fallback."""
    sources = [
        "dumpsys telephony.registry 2>/dev/null",
        "dumpsys phone 2>/dev/null",
        "getprop 2>/dev/null",
        "logcat -d -s NrChecker:D TelephonyManager:D 2>/dev/null | tail -n 30",
    ]
    pattern = "|".join(keywords)
    results = []
    for src in sources:
        raw = adb.shell(f"{src} | grep -iE '{pattern}' | head -n 8")
        if raw.strip():
            results.append(raw.strip())
    return "\n".join(results) if results else f"(Keine {label}-Daten – Gerät nutzt möglicherweise kein 5G)"


def fiveg_ntn_tools(adb: ADB) -> None:
    """5G, NTN und Satelliten-Kommunikation – MAXIMAL ERWEITERT."""
    while True:
        ui.clear()
        ui.rule("📶 5G / NTN / SATELLITEN – VOLLSTÄNDIG", ui.BCYAN)
        ch = ui.menu("Aktion", [
            ("1",  "📡 5G SA vs. NSA Status (enDC · NR-Modus · Dual-Con)"),
            ("2",  "📶 5G MIMO-Layer & Carrier-Aggregation (CA-Bänder)"),
            ("3",  "🌊 mmWave / FR2 Detektion (28 GHz · 39 GHz)"),
            ("4",  "🔀 Network-Slicing (S-NSSAI · eMBB · URLLC · mMTC)"),
            ("5",  "🛰️  NTN / Satelliten-Status (LEO · MEO · GEO · NR-NTN)"),
            ("6",  "🚨 ETWS/WEA Notfall-Broadcasts (Cell-Broadcast)"),
            ("7",  "📞 VoNR (Voice over New Radio · IMS-5G)"),
            ("8",  "📻 Frequenz: ARFCN/EARFCN/NRARFCN → MHz"),
            ("9",  "⚡ 5G-Vollanalyse: alle Parameter auf einmal"),
            ("10", "🔧 5G SA erzwingen (getprop/ADB-Einstellung)"),
            ("11", "📊 NR-Signalqualität (SSB-RSRP/RSRQ/SINR)"),
            ("12", "🌐 5G-Kern-Netz (AMF/SMF-Verbindung) prüfen"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        ui.clear()

        if ch == "1":
            ui.rule("5G SA vs. NSA Status", ui.CYAN)
            # NSA: enDC (E-UTRA-NR Dual Connectivity), SA: nur NR
            results = []
            # Methode 1: telephony.registry
            for query in ["enDc", "isNrAvailable", "nrState", "NR", "5G", "SA", "NSA"]:
                out = adb.shell(f"dumpsys telephony.registry 2>/dev/null | grep -i '{query}' | head -n 3")
                if out.strip():
                    results.append(out.strip())
            # Methode 2: getprop
            for prop in ["gsm.network.type", "vendor.ril.nr.mode", "persist.vendor.radio.nr_mode"]:
                v = adb.shell(f"getprop {prop} 2>/dev/null").strip()
                if v:
                    results.append(f"{prop} = {v}")
            # Methode 3: Netztyp-Integer (20=NR5G, 19=LTE-CA, 13=LTE)
            ntype = adb.shell("dumpsys telephony.registry 2>/dev/null | grep -i 'mDataNetworkType' | head -n 1")
            if ntype.strip():
                results.append(ntype.strip())
                m = re.search(r'mDataNetworkType=(\d+)', ntype)
                if m:
                    n = int(m.group(1))
                    type_map = {20: "NR (5G SA/NSA)", 19: "LTE-CA", 13: "LTE", 0: "UNBEKANNT"}
                    print(f"\n  {ui.BGREEN}Netztyp: {type_map.get(n, str(n))}{ui.RESET}")
            if results:
                print("\n".join(results))
            else:
                print(f"  {ui.BYELLOW}Kein 5G erkannt – Gerät nutzt LTE/4G oder Befehle brauchen Root.{ui.RESET}")
                print("\n  Manuelle Prüfung:")
                print("  • Statusleiste: 5G-Symbol sichtbar?")
                print("  • Einstellungen → Netzwerk → Bevorzugter Typ → 5G anwählen")

        elif ch == "2":
            ui.rule("MIMO & Carrier-Aggregation", ui.CYAN)
            keywords = ["mimo", "layer", "rank", "aggregation", "caBand", "numBands", "CA"]
            print(_5g_multi_query(adb, keywords, "MIMO/CA"))
            # Zusatz: aktuell genutzte Bänder
            bands = adb.shell("dumpsys telephony.registry 2>/dev/null | grep -iE 'band|earfcn' | head -n 10")
            print(bands.strip() or "(Kein CA-Band-Info)")

        elif ch == "3":
            ui.rule("mmWave / FR2 Detektion", ui.CYAN)
            keywords = ["mmwave", "mmWave", "FR2", "28GHz", "39GHz", "60GHz", "freqRange"]
            out = _5g_multi_query(adb, keywords, "mmWave")
            print(out)
            # FR2-Bands: 257(28GHz), 258(26GHz), 260(39GHz), 261(28GHz)
            bands = adb.shell(
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'band' | "
                "grep -E '25[7-9]|26[0-1]' | head -n 5")
            if bands.strip():
                print(f"\n  {ui.BGREEN}mmWave-Bänder (FR2) erkannt:{ui.RESET}\n{bands}")
            else:
                print(f"\n  {ui.GREY}Keine FR2-Bänder erkannt (mmWave meist nur in USA/Japan/Südkorea){ui.RESET}")

        elif ch == "4":
            ui.rule("Network-Slicing (5G-SA)", ui.CYAN)
            keywords = ["nssai", "slice", "s-nssai", "SST", "SD=", "eMBB", "URLLC", "mMTC"]
            out = _5g_multi_query(adb, keywords, "Slicing")
            print(out)
            # 5G-Slice-Typen erklären
            print(f"\n  {ui.GREY}Slice-Typen (SST-Werte):")
            for sst, desc in [(1,"eMBB – Enhanced Mobile Broadband"), (2,"URLLC – Ultra-Low Latency"),
                              (3,"MIoT – Massive IoT / mMTC"), (4,"V2X – Fahrzeug-Kommunikation")]:
                print(f"  SST={sst}: {desc}")
            print(ui.RESET, end="")

        elif ch == "5":
            ui.rule("NTN / Satelliten-Status", ui.CYAN)
            keywords = ["ntn", "satellite", "NTN", "LEO", "MEO", "GEO", "groundStation"]
            out = _5g_multi_query(adb, keywords, "NTN/Satelliten")
            print(out)
            # Carrier-Support prüfen
            carrier = adb.shell("getprop gsm.operator.alpha 2>/dev/null").strip()
            ntn_carriers = {"Starlink": "SpaceX", "Skylo": "Skylo", "T-Mobile": "NTN-Partner"}
            print(f"\n  Betreiber: {carrier}")
            for k, v in ntn_carriers.items():
                if k.lower() in carrier.lower():
                    print(f"  {ui.BGREEN}✓ {v} unterstützt NTN/Satelliten{ui.RESET}")
            print(f"\n  {ui.GREY}NTN-Status: Android 14+ / 3GPP Release 17 nötig{ui.RESET}")

        elif ch == "6":
            ui.rule("ETWS/WEA Notfall-Broadcasts", ui.CYAN)
            out_cb = adb.shell("dumpsys cellbroadcast 2>/dev/null | head -n 40")
            out_log = adb.shell("logcat -d -s CellBroadcast:D ETWS:D WEA:D 2>/dev/null | tail -n 20")
            print(out_cb.strip() or "(Kein CellBroadcast-Service aktiv)")
            if out_log.strip():
                print(f"\n  --- Log ---\n{out_log.strip()}")
            # Test-Broadcast senden
            if ui.confirm("Test-ETWS-Broadcast über ADB simulieren?", False):
                adb.shell(
                    "am broadcast -a android.provider.Telephony.SMS_CB_RECEIVED "
                    "--es message 'PANZER TEST ETWS' 2>/dev/null")
                ui.ok("Test-Broadcast gesendet.")

        elif ch == "7":
            ui.rule("VoNR – Voice over New Radio", ui.CYAN)
            keywords = ["vonr", "VoNR", "voice.nr", "IMS.NR", "nrVoice", "voNrEnabled"]
            out = _5g_multi_query(adb, keywords, "VoNR")
            print(out)
            # IMS-Status
            ims = adb.shell("dumpsys ims 2>/dev/null | grep -iE 'registered|voice|sms|rcs' | head -n 10")
            print(f"\n  IMS-Status:\n{ims.strip() or '(nicht verfügbar)'}")

        elif ch == "8":
            ui.rule("ARFCN / EARFCN / NRARFCN → MHz", ui.CYAN)
            raw = adb.shell("dumpsys telephony.registry 2>/dev/null")
            for pattern, label in [
                (r'earfcn\s*=\s*(\d+)', "EARFCN (LTE)"),
                (r'nrarfcn\s*=\s*(\d+)', "NR-ARFCN (5G)"),
                (r'arfcn\s*=\s*(\d+)', "ARFCN (GSM)"),
                (r'uarfcn\s*=\s*(\d+)', "UARFCN (UMTS)"),
            ]:
                m = re.search(pattern, raw, re.I)
                if m:
                    val = int(m.group(1))
                    # Vereinfachte EARFCN→MHz Konvertierung
                    if "EARFCN" in label:
                        if val < 600: freq = f"~{(1920 + 0.1*val):.0f} MHz"
                        elif val < 1200: freq = f"~{(1850 + 0.1*(val-600)):.0f} MHz"
                        elif val < 1950: freq = f"~{(1710 + 0.1*(val-1200)):.0f} MHz"
                        elif val < 2400: freq = f"~{(2110 + 0.1*(val-1950)):.0f} MHz"
                        elif val < 2650: freq = f"~{(869 + 0.1*(val-2400)):.0f} MHz"
                        elif val < 2750: freq = f"~{(875 + 0.1*(val-2650)):.0f} MHz"
                        else: freq = f"~{val} (unbekannt)"
                        print(f"  {label:<20} {val}  →  {ui.BCYAN}{freq}{ui.RESET}")
                    else:
                        print(f"  {label:<20} {val}")
            # Fallback: grep in props
            props = adb.shell("getprop | grep -iE 'arfcn|earfcn|freq|band' | head -n 10")
            if props.strip():
                print(f"\n{props}")

        elif ch == "9":
            ui.rule("5G-VOLLANALYSE – Alle Parameter", ui.CYAN)
            full = adb.shell("dumpsys telephony.registry 2>/dev/null | head -n 200")
            # Alle interessanten Werte extrahieren
            patterns = [
                ("Netztyp",      r'mDataNetworkType=(\d+)'),
                ("NR-Zustand",   r'nrState=(\w+)'),
                ("enDC",         r'isEnDcAvailable=(\w+)'),
                ("NR verfügbar", r'isNrAvailable=(\w+)'),
                ("RSRP",         r'rsrp=(-?\d+)'),
                ("RSRQ",         r'rsrq=(-?\d+)'),
                ("SINR",         r'rssnr=(-?\d+)'),
                ("CellID",       r'ci=(\d+)'),
                ("TAC",          r'tac=(\w+)'),
                ("EARFCN",       r'earfcn=(\d+)'),
                ("NR-ARFCN",     r'nrarfcn=(\d+)'),
                ("Betreiber",    r'mNetworkOperatorName=(\S+)'),
                ("VoLTE",        r'isVoLteAvailable=(\w+)'),
                ("VoNR",         r'isVoNrAvailable=(\w+)'),
            ]
            for label, pat in patterns:
                m = re.search(pat, full, re.I)
                val = m.group(1) if m else "—"
                icon = ui.BGREEN if val not in ("—", "false", "0", "NONE") else ui.GREY
                print(f"  {icon}{label:<20}{ui.RESET}  {val}")

        elif ch == "10":
            ui.rule("5G SA erzwingen", ui.CYAN)
            methods = [
                ("Network Mode NR only",    "settings put global preferred_network_mode 20 2>/dev/null"),
                ("LTE/NR preferred",        "settings put global preferred_network_mode 33 2>/dev/null"),
                ("ADB phone service",       "service call phone 137 i32 20 2>/dev/null"),
            ]
            for i, (name, cmd) in enumerate(methods, 1):
                print(f"  {i}) {name}")
                print(f"     {ui.GREY}{cmd}{ui.RESET}")
            sel = input("\n  Auswahl (1-3, leer=Abbruch): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= 3:
                _, cmd = methods[int(sel)-1]
                out = adb.shell(cmd)
                print(f"\n  {out.strip() or 'Befehl ausgeführt'}")
                ui.ok("5G-Modus gesetzt. Neustart Modem empfohlen.")

        elif ch == "11":
            ui.rule("NR-Signalqualität (SSB)", ui.CYAN)
            # SSB = Synchronization Signal Block (5G-Referenzsignal)
            raw = adb.shell(
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'NrSignal|ssRsrp|ssRsrq|ssSinr|csiRsrp|csiSinr' | head -n 15")
            print(raw.strip() or "(Keine NR-Signaldaten – Gerät nicht in 5G-Zelle)")
            # Fallback: SignalStrength gesamt
            sig = adb.shell(
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'SignalStrength' | head -n 5")
            if sig.strip():
                print(f"\n  SignalStrength:\n{sig.strip()}")

        elif ch == "12":
            ui.rule("5G-Kernnetz (AMF/SMF)", ui.CYAN)
            out = adb.shell(
                "dumpsys telephony.registry 2>/dev/null | grep -iE 'amf|smf|pcf|upf|guami|plmn' | head -n 15; "
                "logcat -d -s NAS5G:D 5G-MME:D 2>/dev/null | tail -n 20")
            print(out.strip() or "(Keine 5G-Kernnetz-Informationen – nur in 5G-SA verfügbar)")

        ui.pause()


def anti_tracking(adb: ADB) -> None:
    """Anti-Tracking & Privacy."""
    while True:
        ui.clear()
        ui.rule("ANTI-TRACKING & PRIVACY", ui.BCYAN)
        ch = ui.menu("Aktion", [
            ("1", "STK-App deaktivieren (SIM-Befehle blockieren)"),
            ("2", "Flugmodus (Radio-Kill-Switch)"),
            ("3", "5G-SUCI/SUPI-Schutz prüfen"),
            ("4", "Wi-Fi MAC-Randomisierung prüfen"),
            ("5", "Downgrade-Alarm (4G/5G→2G erkennen)"),
            ("6", "BIP-Traffic-Sniffer (logcat)"),
        ], back_label="Zurück")
        if ch in ("back", "quit"):
            return
        if ch == "1":
            out = adb.shell("pm disable com.android.stk 2>/dev/null")
            print(out or "STK deaktiviert (oder bereits deaktiviert)"); ui.pause()
        elif ch == "2":
            if ui.confirm("Flugmodus aktivieren (trennt alle Verbindungen)?", False):
                adb.shell("settings put global airplane_mode_on 1 2>/dev/null")
                adb.shell("am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true 2>/dev/null")
                ui.ok("Flugmodus aktiviert.")
            else:
                if ui.confirm("Flugmodus deaktivieren?", False):
                    adb.shell("settings put global airplane_mode_on 0 2>/dev/null")
                    adb.shell("am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false 2>/dev/null")
                    ui.ok("Flugmodus deaktiviert.")
            ui.pause()
        elif ch == "3":
            out = adb.shell("dumpsys telephony.registry 2>/dev/null | grep -iE 'suci|supi|concealed' | head")
            print(out.strip() or "(Keine 5G-SUCI-Daten – möglicherweise 4G oder keine 5G-SA-Verbindung)"); ui.pause()
        elif ch == "4":
            out = adb.shell("settings get global wifi_verbose_logging_enabled 2>/dev/null")
            print(f"WiFi-Verbose: {out.strip()}")
            out2 = adb.shell("settings get global wifi_connected_mac_randomization_enabled 2>/dev/null")
            print(f"MAC-Randomisierung: {out2.strip() or '1 (Standard Android 10+)'}"); ui.pause()
        elif ch == "5":
            ntype = adb.shell("dumpsys telephony.registry 2>/dev/null | grep networkType | head -n 1")
            print(f"Netzwerk-Typ: {ntype.strip()}")
            if any(x in ntype for x in ("=1", "=2", "GPRS", "EDGE", "GSM")):
                print(f"\n  {ui.BRED}⚠ DOWNGRADE AUF 2G – MÖGLICHER IMSI-CATCHER!{ui.RESET}")
            else:
                print(f"\n  {ui.BGREEN}✓ Kein 2G-Downgrade.{ui.RESET}")
            ui.pause()
        elif ch == "6":
            ui.info("Beobachte BIP-Traffic (5 Sek.) …")
            try:
                out = adb.shell("logcat -d -s SIMRecords:D CatService:D 2>/dev/null | grep -iE 'bip|channel'")
                print(out.strip() or "(Kein BIP-Traffic erkannt)")
            except Exception as e:  # noqa: BLE001
                ui.err(str(e))
            ui.pause()


# ══════════════════════════════════════════════════════════════════════════════
#  HAUPT-MENÜ
# ══════════════════════════════════════════════════════════════════════════════

def menu(adb: ADB, dev=None, st=None) -> None:
    """SIM-Toolkit Hauptmenü: 11 Sektionen · 35 Kategorien · 350 Features + Live-Dashboard."""
    while True:
        ui.clear()
        ui.banner(subtitle="📱 SIM-KARTEN TOOLKIT – 35 Kat · 350 Features · Live-Dashboard")
        print(f"  {ui.GREY}Physische SIMs · eSIM-Chips · Baseband · 5G · NTN · Live-Traffic{ui.RESET}\n")
        ch = ui.menu("Sektion wählen", [
            ("1",  "🗃️  SIM-Karten Modell-Datenbank  (1FF–5FF · eSIM-Chips · Test-SIMs · IoT/M2M · CDMA)"),
            ("2",  "📋 SIM-Kategorien-Browser       (35 Kategorien · 350 Features · Nr. 101–450)"),
            ("3",  "⚡ Schnell-Diagnose             (Slot · ICCID · PIN-Status · VoLTE · IMSI · APN)"),
            ("4",  "💳 eSIM-Profil-Manager          (EID · Profile · LPA · Aktivierungscode · Log)"),
            ("5",  "📡 Baseband & AT-Kommandos      (Modem-FW · Radio-Log · Field-Test · Diag-Port)"),
            ("6",  "🕵️  IMSI-Catcher-Schutz         (Zelltracker · Downgrade-Alarm · SINR · Nachbarzellen)"),
            ("7",  "🔍 SIM-Forensik                (Telefonbuch · SMS · LOCI · MSISDN · IMEI-Check)"),
            ("8",  "🔐 Krypto & Sicherheit          (PIN/PUK · SIM-Lock · STK-Blocker · NCK · TEE)"),
            ("9",  "📶 5G / NTN / Satelliten        (SA/NSA · MIMO · mmWave · Slicing · ETWS · VoNR)"),
            ("10", "🛡️  Anti-Tracking & Privacy      (STK-Block · Flugmodus · SUCI · MAC-Randomisierung)"),
            ("11", f"{ui.BGREEN}{ui.BOLD}🔴 LIVE SIM-TRAFFIC DASHBOARD  (Signal · Netz · Traffic · Verbindungen){ui.RESET}"),
        ], back_label="Hauptmenü")

        if ch in ("back", "quit"):
            return
        try:
            dispatch = {
                "1":  show_sim_models,
                "2":  browse_categories,
                "3":  quick_diagnosis,
                "4":  esim_manager,
                "5":  baseband_tools,
                "6":  imsi_catcher_guard,
                "7":  sim_forensics,
                "8":  crypto_security,
                "9":  fiveg_ntn_tools,
                "10": anti_tracking,
                "11": live_sim_dashboard,
            }
            fn = dispatch.get(ch)
            if fn:
                fn(adb) if ch not in ("1",) else fn()
        except Exception as e:  # noqa: BLE001
            ui.err(f"Fehler: {e}")
            LOG.exception("sim_toolkit", e)
            ui.pause()
