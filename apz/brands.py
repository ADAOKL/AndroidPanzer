"""Hersteller-spezifische Anleitungen für alle Android-Geräte außer Samsung/MTK.

Zeigt schrittweise Unlock-/Root-Anleitungen für erkannte Marken:
Xiaomi/Redmi/POCO, Google Pixel, OnePlus/OPPO/Realme, Motorola/Lenovo, Huawei/Honor.
"""
from __future__ import annotations

from . import lang, rooting, ui
from .adb import ADB, Device


def menu(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    brand = data.get("brand", "").lower()
    if brand in ("xiaomi", "redmi", "poco"):
        _xiaomi(adb, dev, st, data)
    elif brand in ("google",):
        _pixel(adb, dev, st, data)
    elif brand in ("oneplus", "oppo", "realme"):
        _oneplus(adb, dev, st, data)
    elif brand in ("motorola", "moto", "lenovo"):
        _motorola(adb, dev, st, data)
    elif brand in ("huawei", "honor"):
        _huawei(adb, dev, st, data)
    else:
        _generic(adb, dev, st, data)


# ──────────────────────────────────────────────────────────────────────────────

def _show_info(adb: ADB, dev: Device, st: dict, data: dict, title: str, lines: list[str]) -> None:
    ui.clear()
    ui.banner(subtitle=title)
    for ln in lines:
        if ln.startswith("!!"):
            ui.warn(ln[2:].strip())
        elif ln.startswith("✔"):
            ui.ok(ln)
        elif ln.startswith("ℹ"):
            ui.info(ln[1:].strip())
        else:
            print(f"  {ln}")
    print()
    if ui.confirm(lang.t("brand_continue_rooting"), False):
        rooting.show_and_offer(adb, dev, data, st)
        st["is_root"] = adb.check_root()
        data["root"] = st["is_root"]
    else:
        ui.pause()


def _xiaomi(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    sdk = data.get("sdk", "")
    _show_info(adb, dev, st, data,
        f"Xiaomi/MIUI – {model}",
        [
            "Schritt 1 – Mi-Konto verknüpfen:",
            "  • Einstellungen → Mein Konto → Bei Mi-Konto anmelden (falls noch nicht geschehen).",
            "  • Einstellungen → Entwickleroptionen → Mi Unlock Status → Konto verknüpfen.",
            "",
            "Schritt 2 – Entsperr-Wartezeit abwarten:",
            "!! Xiaomi erzwingt eine Wartezeit (72–168 Stunden / bis zu 7 Tage) zwischen",
            "!! Kontoverbindung und Unlock. Die genaue Dauer hängt vom Modell ab.",
            "",
            "Schritt 3 – Mi Unlock Tool (nur Windows):",
            "  • Download: https://www.miui.com/unlock/download.html",
            "  • Gerät in Fastboot bringen (Vol-Runter + Power), USB verbinden.",
            "  • Im Mi Unlock Tool: Mit Mi-Konto anmelden → Entsperren.",
            "  • WARNUNG: Entsperren LÖSCHT ALLE DATEN (Factory Reset).",
            "",
            "Schritt 4 – Root via Magisk:",
            "  • Passendes boot.img aus MIUI Fastboot-ROM (gleicher Build!) extrahieren.",
            "  • Magisk-App → boot.img patchen → gepatchtes Image per fastboot flash boot.",
            "",
            f"ℹ Modell: {model}  SDK: {sdk}",
            "ℹ Kein Windows? Mi Unlock unter Wine teilweise nutzbar; 3rd-Party-Tool 'xiaomi-adb-miui-debloater' hilft nicht beim Unlock.",
        ])


def _pixel(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    android = data.get("android", "")
    try:
        ver = int(str(android).split(".")[0])
    except (ValueError, AttributeError):
        ver = 0
    img_name = "init_boot.img" if ver >= 13 else "boot.img"
    _show_info(adb, dev, st, data,
        f"Google Pixel – {model}",
        [
            "Google Pixel unterstützt OEM-Unlock nativ. Kein Tool von Drittanbietern nötig.",
            "",
            "Schritt 1 – OEM-Unlock aktivieren:",
            "  • Einstellungen → Entwickleroptionen → OEM-Entsperrung aktivieren.",
            "  • Bei Pixel-6+-Modellen: Gerät muss mindestens 7 Tage alt sein.",
            "",
            "Schritt 2 – Bootloader entsperren:",
            "  • Gerät in Fastboot bringen: adb reboot bootloader",
            "  • fastboot flashing unlock",
            "!! WARNUNG: Entsperren LÖSCHT ALLE DATEN.",
            "",
            f"Schritt 3 – {img_name} patchen (Android {android}):",
            f"  • Passendes {img_name} von https://developers.google.com/android/images herunterladen.",
            f"  • Magisk-App → {img_name} patchen → gepatchtes Image zurück auf den PC kopieren.",
            f"  • fastboot flash {img_name.replace('.img','')} magisk_patched_*.img",
            "",
            "Schritt 4 – Neustart:",
            "  • fastboot reboot → Gerät startet, Magisk-App öffnen → 'Direct Install'.",
            "",
            f"ℹ Android {android} · Zu patchendes Image: {img_name}",
        ])


def _oneplus(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    brand = data.get("brand", "OnePlus")
    _show_info(adb, dev, st, data,
        f"{brand.title()} – {model}",
        [
            f"{brand.title()} / OPPO / Realme: Standard-Fastboot-Entsperrung.",
            "",
            "Schritt 1 – OEM-Unlock freischalten:",
            "  • Einstellungen → Über das Telefon → 7× auf Build-Nummer tippen.",
            "  • Einstellungen → Entwickleroptionen → OEM-Entsperrung aktivieren.",
            "  • Manche OPPO/Realme-Modelle brauchen ein Entwicklerkonto auf der Hersteller-Website.",
            "",
            "Schritt 2 – Bootloader entsperren:",
            "  • adb reboot bootloader",
            "  • fastboot flashing unlock   (ältere Geräte: fastboot oem unlock)",
            "!! WARNUNG: Entsperren LÖSCHT ALLE DATEN.",
            "",
            "Schritt 3 – boot.img patchen:",
            "  • OTA-Payload-Datei des passenden Builds herunterladen (XDA Developers).",
            "  • payload_dumper.py verwenden, um boot.img zu extrahieren.",
            "  • Magisk-App → boot.img patchen → fastboot flash boot magisk_patched.img",
            "",
            f"ℹ Modell: {model} · Hersteller: {brand.title()}",
            "ℹ OnePlus-Geräte ab OxygenOS 14 (2023+): Unlock manchmal nur mit Hersteller-Tool.",
        ])


def _motorola(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    _show_info(adb, dev, st, data,
        f"Motorola – {model}",
        [
            "Motorola verwendet ein Unlock-Code-System (kein freier Fastboot-Unlock).",
            "",
            "Schritt 1 – Bootloader-ID auslesen:",
            "  • Gerät in Fastboot bringen: adb reboot bootloader",
            "  • fastboot oem get_unlock_data",
            "  • Den angezeigten langen Code notieren.",
            "",
            "Schritt 2 – Unlock-Code bei Motorola anfordern:",
            "  • https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device-a",
            "  • Unlock-Daten einfügen → Motorola schickt einen Code per E-Mail.",
            "",
            "Schritt 3 – Entsperren:",
            "  • fastboot oem unlock <CODE-VON-MOTOROLA>",
            "!! WARNUNG: Entsperren LÖSCHT ALLE DATEN.",
            "",
            "Schritt 4 – Root:",
            "  • Passendes boot.img aus Stock-ROM herunterladen.",
            "  • Magisk-App → patchen → fastboot flash boot magisk_patched.img",
            "",
            f"ℹ Modell: {model}",
            "ℹ Nicht alle Motorola-Modelle unterstützen Bootloader-Unlock (Carrier-locked).",
        ])


def _huawei(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    model = data.get("model", "")
    _show_info(adb, dev, st, data,
        f"Huawei/Honor – {model}",
        [
            "!! Wichtig: Huawei hat den Bootloader-Unlock-Service seit Mai 2018 eingestellt.",
            "!! Für die meisten Geräte nach 2018 gibt es keinen offiziellen Entsperr-Weg mehr.",
            "",
            "Möglichkeiten (je nach Modell):",
            "  1. dc-unlocker / HCU Client (kostenpflichtig, inoffizielle Tools) – auf Gerät prüfen.",
            "  2. Für alte Geräte (vor 2018): Unlock-Code über Huawei-Portal (abgeschaltet).",
            "  3. EDL-Exploit (Kirin 9xx) – sehr modellspezifisch, hohes Brick-Risiko.",
            "  4. Manche Geräte: TWRP via ADB-Sideload (nur wenn bereits entsperrt).",
            "",
            "ℹ Ehrliche Einschätzung: Huawei/Honor-Geräte neuerer Baujahr sind de facto",
            "ℹ nicht rootbar ohne kostenpflichtige Drittanbieter-Tools oder Hardware-Eingriff.",
            "",
            f"ℹ Modell: {model}",
            "ℹ Forensik-Funktionen über ADB (ohne Root) sind weiterhin nutzbar.",
        ])


def _generic(adb: ADB, dev: Device, st: dict, data: dict) -> None:
    brand = data.get("brand", "")
    model = data.get("model", "")
    _show_info(adb, dev, st, data,
        f"{brand} {model} – Allgemeiner Root-Weg",
        [
            "Generischer Android-Root-Weg (Fastboot + Magisk):",
            "",
            "Schritt 1 – OEM-Unlock freischalten:",
            "  • Einstellungen → Über das Telefon → 7× auf Build-Nummer tippen.",
            "  • Einstellungen → Entwickleroptionen → OEM-Entsperrung aktivieren.",
            "",
            "Schritt 2 – Bootloader entsperren:",
            "  • adb reboot bootloader",
            "  • fastboot flashing unlock   (ältere: fastboot oem unlock)",
            "!! WARNUNG: Entsperren LÖSCHT ALLE DATEN.",
            "",
            "Schritt 3 – boot.img patchen:",
            "  • Stock-ROM des exakt passenden Builds herunterladen (XDA / Hersteller).",
            "  • boot.img / init_boot.img extrahieren.",
            "  • Magisk-App → boot.img patchen → gepatchtes Image zurück auf PC.",
            "  • fastboot flash boot magisk_patched_*.img",
            "",
            "Schritt 4 – Neustart & Magisk abschließen:",
            "  • fastboot reboot → Magisk-App öffnen → 'Direct Install' (falls nötig).",
            "",
            f"ℹ Marke: {brand}  Modell: {model}",
            "ℹ Für modellspezifische Anleitungen: XDA Developers Forum durchsuchen.",
        ])
