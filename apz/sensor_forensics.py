"""Sensor-Forensik – Accelerometer-History, Barometer, Biometrie, NFC-Log.

Quellen: dumpsys sensorservice, dumpsys fingerprint, /proc/bus/usb/devices,
         Android SensorManager via dumpsys, NFC-Dienst-Logs
"""
from __future__ import annotations

from . import ui


def menu(adb=None, dev=None, st: dict | None = None) -> None:
    """Hauptmenü: Sensor-Forensik."""
    if st is None:
        st = {}

    while True:
        ui.clear()
        ui.banner(subtitle="🧬 SENSOR-FORENSIK")
        print()
        ui.rule("Optionen", ui.CYAN)
        print("  [1] Sensor-Übersicht (alle Sensoren)")
        print("  [2] Biometrie-Status (Fingerprint/Face)")
        print("  [3] NFC-Status und Logs")
        print("  [4] Bewegungssensor-Aktivität")
        print("  [5] Barometer / Umgebungssensoren")
        print("  [6] Sensor-Zugriffsberechtigungen je App")
        print("  [7] Komplettstatus")
        print()
        print("  [0] Zurück")
        print()
        choice = ui.ask("Auswahl", "0")

        if choice == "0":
            return
        elif choice == "1":
            _sensor_overview(adb, st)
        elif choice == "2":
            _biometrics(adb, st)
        elif choice == "3":
            _nfc_status(adb, st)
        elif choice == "4":
            _motion_sensors(adb, st)
        elif choice == "5":
            _environmental_sensors(adb, st)
        elif choice == "6":
            _sensor_permissions(adb, st)
        elif choice == "7":
            _full_report(adb, st)
        else:
            ui.warn("Ungültige Auswahl")


def _sensor_overview(adb, st: dict) -> None:
    ui.clear(); ui.rule("Sensor-Übersicht", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    sensors = adb.shell(
        "dumpsys sensorservice 2>/dev/null | grep -E 'Sensor|Type|Vendor|Version' | head -40",
        timeout=10
    ).strip()

    if sensors:
        print(f"  Registrierte Sensoren:\n")
        for line in sensors.splitlines()[:30]:
            print(f"    {line.strip()}")
    else:
        # Fallback via getprop
        sensor_list = adb.shell(
            "getprop | grep -i sensor | head -15", timeout=5
        ).strip()
        if sensor_list:
            for line in sensor_list.splitlines():
                print(f"  {line.strip()}")
        else:
            print(f"  ℹ  Sensor-Daten nicht direkt lesbar")

    ui.pause()


def _biometrics(adb, st: dict) -> None:
    ui.clear(); ui.rule("Biometrie-Status", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # Fingerprint
    fp_status = adb.shell(
        "dumpsys fingerprint 2>/dev/null | grep -E 'enrolled|enabled|error|maxFingerCount' | head -10",
        timeout=8
    ).strip()

    # Face recognition
    face_status = adb.shell(
        "dumpsys face 2>/dev/null | grep -E 'enrolled|enabled|error' | head -5 || "
        "getprop ro.face.recognition.capability 2>/dev/null",
        timeout=8
    ).strip()

    # Biometrik-Fähigkeiten
    biometric_cap = adb.shell(
        "dumpsys biometric 2>/dev/null | head -20",
        timeout=8
    ).strip()

    print(f"  Fingerabdruck-Status:")
    if fp_status:
        for line in fp_status.splitlines():
            print(f"    {line.strip()}")
    else:
        print(f"    ℹ  Nicht verfügbar oder nicht konfiguriert")

    print(f"\n  Gesichts-Erkennung:")
    if face_status:
        for line in face_status.splitlines()[:5]:
            print(f"    {line.strip()}")
    else:
        print(f"    ℹ  Nicht verfügbar")

    # Anzahl eingespeicherter Fingerabdrücke
    fp_count = adb.shell(
        "dumpsys fingerprint 2>/dev/null | grep -c 'fingerId'", timeout=5
    ).strip()
    if fp_count and fp_count != "0":
        print(f"\n  ⚠️  Gespeicherte Fingerabdrücke: {fp_count}")

    ui.pause()


def _nfc_status(adb, st: dict) -> None:
    ui.clear(); ui.rule("NFC-Status und Logs", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    nfc_enabled = adb.shell(
        "settings get global nfc_on 2>/dev/null || "
        "dumpsys nfc 2>/dev/null | grep -E 'mState|enabled|disabled' | head -5",
        timeout=8
    ).strip()

    nfc_secure = adb.shell(
        "settings get global nfc_payment_default_component 2>/dev/null",
        timeout=5
    ).strip()

    nfc_tags = adb.shell(
        "logcat -d -t 100 2>/dev/null | grep -i 'NFC\\|NDEF\\|IsoDep\\|MifareClassic' | head -10",
        timeout=8
    ).strip()

    icon = "🟢" if nfc_enabled in ("1", "enabled") else "🔴" if nfc_enabled in ("0", "disabled") else "⚪"
    print(f"  {icon} NFC Status       : {nfc_enabled or '—'}")
    print(f"  💳 NFC-Payment App  : {nfc_secure or '—'}")

    if nfc_tags:
        print(f"\n  Letzte NFC-Aktivitäten (logcat):")
        for line in nfc_tags.splitlines()[:8]:
            print(f"    {line.strip()}")
    else:
        print(f"\n  ℹ  Keine NFC-Aktivitäten im Logcat")

    ui.pause()


def _motion_sensors(adb, st: dict) -> None:
    ui.clear(); ui.rule("Bewegungssensor-Aktivität", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # Aktive Sensor-Subscriptions
    subscriptions = adb.shell(
        "dumpsys sensorservice 2>/dev/null | "
        "grep -E 'Connection|sensor=|package=|WakeLock' | head -30",
        timeout=10
    ).strip()

    print(f"  Aktive Sensor-Subscriptions:")
    if subscriptions:
        for line in subscriptions.splitlines()[:20]:
            print(f"    {line.strip()}")
    else:
        print(f"    ℹ  Keine aktiven Subscriptions gefunden")

    # Recent logcat für Sensor-Events
    sensor_log = adb.shell(
        "logcat -d -t 50 2>/dev/null | grep -iE 'sensor|accelero|gyro|motion' | head -10",
        timeout=8
    ).strip()
    if sensor_log:
        print(f"\n  Sensor-Logcat (letzte Events):")
        for line in sensor_log.splitlines()[:8]:
            print(f"    {line.strip()}")

    ui.pause()


def _environmental_sensors(adb, st: dict) -> None:
    ui.clear(); ui.rule("Barometer / Umgebungssensoren", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    env_sensors = adb.shell(
        "dumpsys sensorservice 2>/dev/null | "
        "grep -iE 'pressure|barometer|temperature|humidity|light|proximity' | head -20",
        timeout=10
    ).strip()

    if env_sensors:
        print(f"  Umgebungssensoren:\n")
        for line in env_sensors.splitlines():
            print(f"    {line.strip()}")
    else:
        print(f"  ℹ  Umgebungssensor-Details nicht direkt lesbar")

    # Licht-Sensor Status (für Bildschirm-Helligkeit)
    light = adb.shell(
        "dumpsys display 2>/dev/null | grep -i 'ambientLux\\|currentLux\\|ambientBrightness' | head -5",
        timeout=5
    ).strip()
    if light:
        print(f"\n  Licht-Sensor:")
        for line in light.splitlines():
            print(f"    {line.strip()}")

    ui.pause()


def _sensor_permissions(adb, st: dict) -> None:
    ui.clear(); ui.rule("Sensor-Zugriffsberechtigungen", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # BODY_SENSORS Berechtigung
    body_sensor_apps = adb.shell(
        "pm list packages -3 2>/dev/null | while read p; do p=${p#package:}; "
        "pm dump $p 2>/dev/null | grep -q 'BODY_SENSORS' && echo $p; "
        "done 2>/dev/null | head -10",
        timeout=15
    ).strip()

    # ACTIVITY_RECOGNITION
    activity_apps = adb.shell(
        "pm list packages -3 2>/dev/null | while read p; do p=${p#package:}; "
        "pm dump $p 2>/dev/null | grep -q 'ACTIVITY_RECOGNITION' && echo $p; "
        "done 2>/dev/null | head -10",
        timeout=15
    ).strip()

    print(f"  Apps mit BODY_SENSORS:")
    if body_sensor_apps:
        for pkg in body_sensor_apps.splitlines():
            print(f"    🧬 {pkg}")
    else:
        print(f"    (keine)")

    print(f"\n  Apps mit ACTIVITY_RECOGNITION:")
    if activity_apps:
        for pkg in activity_apps.splitlines():
            print(f"    🏃 {pkg}")
    else:
        print(f"    (keine)")

    ui.pause()


def _full_report(adb, st: dict) -> None:
    ui.clear(); ui.rule("Sensor-Forensik Komplettstatus", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    lines = ["=== SENSOR-FORENSIK KOMPLETTSTATUS ===\n"]

    # NFC
    nfc = adb.shell("settings get global nfc_on 2>/dev/null", timeout=5).strip()
    lines.append(f"  NFC aktiv           : {'ja' if nfc == '1' else 'nein' if nfc == '0' else '—'}")

    # Biometrie
    fp = adb.shell("dumpsys fingerprint 2>/dev/null | grep -c fingerId", timeout=5).strip()
    lines.append(f"  Fingerabdrücke      : {fp or '0'}")

    # Sensor-Count
    sensor_count = adb.shell(
        "dumpsys sensorservice 2>/dev/null | grep -c 'Type ='", timeout=5
    ).strip()
    lines.append(f"  Sensoren gesamt     : {sensor_count or '—'}")

    # Aktive Sensor-Subscriptions
    sub_count = adb.shell(
        "dumpsys sensorservice 2>/dev/null | grep -c 'Connection'", timeout=5
    ).strip()
    lines.append(f"  Aktive Subscriptions: {sub_count or '0'}")

    # Body-Sensor-Apps
    body_apps = adb.shell(
        "pm list packages -3 2>/dev/null | while read p; do p=${p#package:}; "
        "pm dump $p 2>/dev/null | grep -q 'BODY_SENSORS' && echo $p; done 2>/dev/null | wc -l",
        timeout=15
    ).strip()
    lines.append(f"  Apps mit BODY_SENSORS: {body_apps or '0'}")

    report_text = "\n".join(lines)
    ui.pager(report_text, "Sensor-Forensik Bericht")
    ui.pause()
