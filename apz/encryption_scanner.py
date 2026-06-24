"""Verschlüsselungs-Scanner – Disk-Encryption, TLS-Zertifikate, VPN-Erkennung.

Quellen: getprop, dumpsys, /proc/net, /data/misc/vpn
Kein Root benötigt für Basis-Checks; Root erweitert TLS-Zertifikat-Analyse.
"""
from __future__ import annotations

from . import ui


def menu(adb=None, dev=None, st: dict | None = None) -> None:
    """Hauptmenü: Verschlüsselungs-Scanner."""
    if st is None:
        st = {}
    is_root = st.get("is_root", False)

    while True:
        ui.clear()
        ui.banner(subtitle="🔐 VERSCHLÜSSELUNGS-SCANNER")
        print()
        ui.rule("Optionen", ui.CYAN)
        print("  [1] Disk-Encryption Status")
        print("  [2] TLS/SSL-Zertifikate (System + User-CAs)")
        print("  [3] VPN-Erkennung (aktive Tunnel)")
        print("  [4] Keystore-Analyse (AndroidKeyStore)")
        print("  [5] SELinux + Secure Boot Status")
        print("  [6] Komplettbericht")
        print()
        print("  [0] Zurück")
        print()
        choice = input(f"{ui.PROMPT} Auswahl: ").strip()

        if choice == "0":
            return
        elif choice == "1":
            _disk_encryption(adb, st)
        elif choice == "2":
            _tls_certificates(adb, st)
        elif choice == "3":
            _vpn_detection(adb, st)
        elif choice == "4":
            _keystore_analysis(adb, st)
        elif choice == "5":
            _selinux_status(adb, st)
        elif choice == "6":
            _full_report(adb, st)
        else:
            ui.warn("Ungültige Auswahl")


def _disk_encryption(adb, st: dict) -> None:
    ui.clear(); ui.rule("Disk-Encryption Status", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    props = {
        "ro.crypto.state":        "Verschlüsselungs-Status",
        "ro.crypto.type":         "Typ (block/file)",
        "ro.crypto.fs_type":      "Dateisystem",
        "vold.decrypt":           "Vold-Decrypt",
        "ro.product.first_api_level": "First API Level",
    }
    for prop, label in props.items():
        val = adb.getprop(prop) or "—"
        icon = "🔒" if val not in ("", "—", "unencrypted") else "🔓"
        print(f"  {icon} {label:<30} {val}")

    # FBE / FDE Erkennung
    fbe = adb.shell("ls /data/misc/vold/user_keys/ 2>/dev/null | head -5", timeout=5)
    if fbe.strip():
        print(f"\n  ✅ File-Based Encryption (FBE) aktiv")
        print(f"     User-Keys: {len(fbe.splitlines())} gefunden")
    else:
        print(f"\n  ℹ  FBE-Verzeichnis nicht lesbar (Root benötigt)")

    ui.pause()


def _tls_certificates(adb, st: dict) -> None:
    ui.clear(); ui.rule("TLS/SSL-Zertifikate", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # System-CAs zählen
    sys_certs = adb.shell("ls /system/etc/security/cacerts/ 2>/dev/null | wc -l", timeout=5).strip()
    user_certs = adb.shell("ls /data/misc/user/0/cacerts-added/ 2>/dev/null | wc -l", timeout=5).strip()
    removed = adb.shell("ls /data/misc/user/0/cacerts-removed/ 2>/dev/null | wc -l", timeout=5).strip()

    print(f"  🏛️  System-CAs         : {sys_certs or '—'}")
    print(f"  👤 User-installierte CAs: {user_certs or '0'}")
    print(f"  ❌ Entfernte System-CAs : {removed or '0'}")

    # Warnung wenn User-CAs vorhanden
    try:
        if int(user_certs or 0) > 0:
            print(f"\n  ⚠️  WARNUNG: {user_certs} User-CA(s) können MITM-Angriffe ermöglichen!")
    except (ValueError, TypeError):
        pass

    # Erste User-CAs anzeigen
    if adb.shell("test -d /data/misc/user/0/cacerts-added/ && echo YES", timeout=3).strip() == "YES":
        certs = adb.shell(
            "ls /data/misc/user/0/cacerts-added/ 2>/dev/null | head -5", timeout=5
        ).strip()
        if certs:
            print(f"\n  User-CAs:")
            for c in certs.splitlines():
                print(f"    • {c}")

    ui.pause()


def _vpn_detection(adb, st: dict) -> None:
    ui.clear(); ui.rule("VPN-Erkennung", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    # tun/ppp Interfaces
    tun = adb.shell("ip link show 2>/dev/null | grep -E 'tun|ppp|wg|ipsec'", timeout=8).strip()
    vpn_apps = adb.shell(
        "dumpsys connectivity 2>/dev/null | grep -i 'vpn\\|tunnel' | head -10", timeout=10
    ).strip()
    vpn_pkg = adb.shell(
        "dumpsys package 2>/dev/null | grep -l 'BIND_VPN_SERVICE' | head -5", timeout=10
    ).strip()
    vpn_perms = adb.shell(
        "pm list packages 2>/dev/null | while read p; do "
        "pm dump ${p#package:} 2>/dev/null | grep -q 'BIND_VPN_SERVICE' && echo ${p#package:}; "
        "done 2>/dev/null | head -5",
        timeout=15
    ).strip()

    if tun:
        print(f"  🔴 Aktive VPN-Interfaces gefunden:")
        for line in tun.splitlines()[:5]:
            print(f"    • {line.strip()}")
    else:
        print(f"  ✅ Keine aktiven VPN-Tunnel erkannt")

    if vpn_perms:
        print(f"\n  Apps mit VPN-Berechtigung:")
        for pkg in vpn_perms.splitlines():
            print(f"    • {pkg}")

    ui.pause()


def _keystore_analysis(adb, st: dict) -> None:
    ui.clear(); ui.rule("AndroidKeyStore-Analyse", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    hw_backed = adb.getprop("ro.hardware.keystore") or adb.getprop("ro.hardware") or "—"
    print(f"  Hardware-Keystore   : {hw_backed}")

    strongbox = adb.shell(
        "getprop | grep -i 'strongbox\\|keymaster\\|keymint' 2>/dev/null | head -5", timeout=5
    ).strip()
    if strongbox:
        for line in strongbox.splitlines():
            k, _, v = line.partition("]:")
            k = k.lstrip("[")
            print(f"  {k.strip():<35} {v.strip().strip('[').strip(']')}")
    else:
        print(f"  StrongBox/KeyMint-Props nicht gefunden")

    ui.pause()


def _selinux_status(adb, st: dict) -> None:
    ui.clear(); ui.rule("SELinux + Secure Boot", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    selinux = adb.shell("getenforce 2>/dev/null || cat /sys/fs/selinux/enforce 2>/dev/null", timeout=5).strip()
    bootloader = adb.getprop("ro.boot.verifiedbootstate") or adb.getprop("ro.boot.flash.locked") or "—"
    verified = adb.getprop("ro.boot.veritymode") or "—"
    dm_verity = adb.shell("cat /proc/mounts 2>/dev/null | grep -c 'dm-'", timeout=5).strip()

    icon_sel = "🟢" if selinux.lower() == "enforcing" else "🔴"
    icon_bl  = "🔒" if bootloader in ("green", "1", "locked") else "🔓"

    print(f"  {icon_sel} SELinux Status    : {selinux or '—'}")
    print(f"  {icon_bl} Bootloader        : {bootloader}")
    print(f"  🛡️  Verified Boot     : {verified}")
    print(f"  💾 DM-Verity Mounts  : {dm_verity or '0'}")

    ui.pause()


def _full_report(adb, st: dict) -> None:
    ui.clear(); ui.rule("Verschlüsselungs-Komplettstatus", ui.CYAN)
    if adb is None:
        ui.warn("Kein Gerät verbunden"); ui.pause(); return

    lines = ["=== VERSCHLÜSSELUNGS-SCANNER ===\n"]

    # Schnell-Check aller wichtigen Props
    checks = [
        ("ro.crypto.state",             "Disk-Encryption"),
        ("ro.crypto.type",              "Crypto-Typ"),
        ("ro.boot.verifiedbootstate",   "Verified Boot"),
        ("ro.boot.flash.locked",        "Bootloader-Lock"),
        ("ro.hardware.keystore",        "Keystore-HW"),
    ]
    for prop, label in checks:
        val = adb.getprop(prop) or "—"
        lines.append(f"  {label:<30} {val}")

    selinux = adb.shell("getenforce 2>/dev/null", timeout=5).strip()
    lines.append(f"  {'SELinux':<30} {selinux or '—'}")

    user_certs = adb.shell("ls /data/misc/user/0/cacerts-added/ 2>/dev/null | wc -l", timeout=5).strip()
    lines.append(f"  {'User-CAs':<30} {user_certs or '0'}")

    tun = adb.shell("ip link show 2>/dev/null | grep -cE 'tun|ppp|wg'", timeout=5).strip()
    lines.append(f"  {'VPN-Interfaces':<30} {tun or '0'}")

    report_text = "\n".join(lines)
    ui.pager(report_text, "Verschlüsselungs-Komplettstatus")
    ui.pause()
