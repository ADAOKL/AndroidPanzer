"""Tests für das App-Inventar: dumpsys-Blockparser + Anomalie-Erkennung (Mock-ADB)."""
from __future__ import annotations

from apz import appscan

DUMP = """Packages:
  Package [com.good.app] (aaa):
    codePath=/data/app/~~x==/com.good.app-1
    primaryCpuAbi=arm64-v8a
    versionName=2.0
    flags=[ HAS_CODE ALLOW_CLEAR_USER_DATA ]
    installerPackageName=com.android.vending
    requested permissions:
      android.permission.INTERNET
    install permissions:
      android.permission.INTERNET: granted=true
  Package [com.evil.spy] (bbb):
    codePath=/data/app/~~y==/com.evil.spy-1
    primaryCpuAbi=x86
    versionName=0.1
    flags=[ DEBUGGABLE HAS_CODE ]
    installerPackageName=null
    requested permissions:
      android.permission.RECORD_AUDIO
      android.permission.ACCESS_FINE_LOCATION
      android.permission.READ_SMS
      android.permission.READ_CONTACTS
      android.permission.SYSTEM_ALERT_WINDOW
    install permissions:
      android.permission.RECORD_AUDIO: granted=true
      android.permission.ACCESS_FINE_LOCATION: granted=true
      android.permission.READ_SMS: granted=true
      android.permission.READ_CONTACTS: granted=true
  Package [com.android.systemservice] (ccc):
    codePath=/data/app/~~z==/com.android.systemservice-1
    primaryCpuAbi=arm64-v8a
    versionName=1.0
    flags=[ HAS_CODE ]
    installerPackageName=com.android.shell
    requested permissions:
      android.permission.READ_SMS
    install permissions:
      android.permission.READ_SMS: granted=true
"""

RESPONSES = [
    ("pm list packages -s", ""),                    # keine System-Apps
    ("pm list packages -d", ""),                    # keine deaktivierten
    ("pm list packages", "package:com.good.app\npackage:com.evil.spy\npackage:com.android.systemservice\n"),
    ("query-activities", "com.good.app/.Main\n"),   # nur die gute App hat ein Launcher-Icon
    ("enabled_accessibility_services", "com.evil.spy/.SpyService"),
    ("enabled_notification_listeners", "null"),
    ("device_policy", ""),
    ("dumpsys package packages", DUMP),
]

DATA = {"abi": "arm64-v8a", "abilist": "arm64-v8a,armeabi-v7a,armeabi"}


def _apps(mock_adb):
    return {a.pkg: a for a in appscan.scan(mock_adb(RESPONSES), DATA)}


class TestBlockParser:
    def test_fields(self):
        b = appscan._parse_package_blocks(DUMP)
        assert set(b) == {"com.good.app", "com.evil.spy", "com.android.systemservice"}
        assert b["com.evil.spy"]["abi"] == "x86"
        assert "DEBUGGABLE" in b["com.evil.spy"]["flags"]
        assert "RECORD_AUDIO" in b["com.evil.spy"]["granted"]
        assert b["com.good.app"]["installer"] == "com.android.vending"
        assert b["com.android.systemservice"]["installer"] == "com.android.shell"


class TestScan:
    def test_counts(self, mock_adb):
        apps = _apps(mock_adb)
        assert len(apps) == 3

    def test_good_app_clean(self, mock_adb):
        good = _apps(mock_adb)["com.good.app"]
        assert not good.flagged
        assert good.score == 0

    def test_evil_app_flagged(self, mock_adb):
        evil = _apps(mock_adb)["com.evil.spy"]
        whats = " | ".join(w for w, _ in evil.anomalies)
        assert evil.flagged and evil.severity == "crit"
        assert "x86" in whats                     # Architektur-Mismatch
        assert "Sideloaded" in whats              # Herkunft
        assert "DEBUGGABLE" in whats              # Signatur/Build
        assert "Accessibility" in whats           # aktives Privileg
        assert "Stalkerware-Rechte-Kombi" in whats

    def test_masquerade_and_known_stalkerware(self, mock_adb):
        svc = _apps(mock_adb)["com.android.systemservice"]
        whats = " | ".join(w for w, _ in svc.anomalies)
        assert svc.severity == "crit"
        assert "Stalkerware-Datenbank" in whats   # bekannter Paketname
        assert "Maskerade" in whats or "System-artiger" in whats

    def test_flagged_sorted_first(self, mock_adb):
        apps = appscan.scan(mock_adb(RESPONSES), DATA)
        # höchster Score zuerst, saubere App zuletzt
        assert apps[0].score >= apps[-1].score
        assert apps[-1].pkg == "com.good.app"


class TestComponentParsers:
    def test_comp_pkgs(self):
        v = "com.evil.spy/.SpyService:com.other.app/.Listener"
        assert appscan._comp_pkgs(v) == {"com.evil.spy", "com.other.app"}

    def test_comp_pkgs_null(self):
        assert appscan._comp_pkgs("null") == set()
        assert appscan._comp_pkgs("") == set()

    def test_admin_pkgs_only_admin_lines(self):
        dump = (
            "Device policy state:\n"
            "  android stuff with ComponentInfo{com.noise.app/.X} not an admin line\n"
            "  Enabled Device Admins (User 0):\n"
            "    admin=DeviceAdminInfo{ComponentInfo{com.real.admin/.Receiver}}\n"
        )
        pkgs = appscan._admin_pkgs(dump)
        assert "com.real.admin" in pkgs
        assert "com.noise.app" not in pkgs   # KEIN Substring-/Zufallstreffer


# Regression: die echte Hardware (Samsung S10e) markierte 138 System-Apps rot,
# weil pkg gegen den ganzen device_policy-Dump ge-substringt wurde ('android'
# steckt überall). System-Apps dürfen NICHT für Rechte-Kombis/Privilegien rot werden.
SYS_DUMP = """Packages:
  Package [android] (fff):
    codePath=/system/framework/framework-res.apk
    primaryCpuAbi=arm64-v8a
    versionName=12
    flags=[ SYSTEM HAS_CODE ]
    installerPackageName=null
    requested permissions:
      android.permission.RECORD_AUDIO
      android.permission.ACCESS_FINE_LOCATION
      android.permission.READ_SMS
      android.permission.READ_CONTACTS
      android.permission.REQUEST_INSTALL_PACKAGES
      android.permission.SYSTEM_ALERT_WINDOW
    install permissions:
      android.permission.RECORD_AUDIO: granted=true
      android.permission.ACCESS_FINE_LOCATION: granted=true
      android.permission.READ_SMS: granted=true
      android.permission.READ_CONTACTS: granted=true
"""

SYS_RESPONSES = [
    ("pm list packages -s", "package:android\n"),                 # 'android' IST System
    ("pm list packages -d", ""),
    ("pm list packages", "package:android\n"),
    ("query-activities", ""),
    ("enabled_accessibility_services", "null"),
    ("enabled_notification_listeners", "null"),
    ("device_policy", "ComponentInfo{android/.SomeReceiver} admin=ComponentInfo{android/.X}"),
    ("dumpsys package packages", SYS_DUMP),
]


class TestSystemAppNotFlooded:
    def test_framework_android_not_flagged(self, mock_adb):
        apps = {a.pkg: a for a in appscan.scan(mock_adb(SYS_RESPONSES), DATA)}
        andr = apps["android"]
        # Trotz aller sensiblen Rechte + Admin-Zeile: System-Paket bleibt unmarkiert.
        assert not andr.flagged, [w for w, _ in andr.anomalies]
        assert andr.score == 0


class TestBenignInstaller:
    def test_omcagent_not_sideloaded(self, mock_adb):
        dump = ("Packages:\n"
                "  Package [au.com.vodafone.app] (a):\n"
                "    codePath=/data/app/x\n"
                "    primaryCpuAbi=arm64-v8a\n"
                "    versionName=1.0\n"
                "    flags=[ HAS_CODE ]\n"
                "    installerPackageName=com.samsung.android.app.omcagent\n"
                "    requested permissions:\n"
                "      android.permission.INTERNET\n")
        resp = [("pm list packages -s", ""), ("pm list packages -d", ""),
                ("pm list packages", "package:au.com.vodafone.app\n"),
                ("query-activities", "au.com.vodafone.app/.Main"),
                ("enabled_accessibility_services", "null"),
                ("enabled_notification_listeners", "null"),
                ("device_policy", ""), ("dumpsys package packages", dump)]
        app = appscan.scan(mock_adb(resp), DATA)[0]
        assert not app.flagged   # Carrier-Preload-Installer = legitime Quelle
