"""Tests für Dashboard-Schnell-Triage (Sicherheits-Ampel)."""
from __future__ import annotations

from apz import dashboard as dash


class TestPatchAge:
    def test_known_old(self):
        assert dash._patch_age("2020-01-05") >= 12

    def test_unknown(self):
        assert dash._patch_age("") == 0
        assert dash._patch_age("kaputt") == 0


class TestTriage:
    def test_unlocked_bootloader_is_critical(self):
        tri = dash._triage({"bootloader_unlocked": "0", "verifiedboot": "orange"})
        assert any(s == "crit" and "ENTSPERRT" in t for s, t in tri)

    def test_adb_wifi_critical(self):
        tri = dash._triage({"adb_wifi": "1"})
        assert any(s == "crit" and "WLAN-ADB" in t for s, t in tri)

    def test_unencrypted_critical(self):
        tri = dash._triage({"crypto": "unencrypted"})
        assert any(s == "crit" for s, t in tri)

    def test_accessibility_warns(self):
        tri = dash._triage({"a11y": "com.evil/.SpyService"})
        assert any(s == "warn" and "Accessibility" in t for s, t in tri)

    def test_root_warns(self):
        tri = dash._triage({"root": True})
        assert any("GEROOTET" in t for s, t in tri)

    def test_clean_device_no_flags(self):
        clean = {"bootloader_unlocked": "1", "verifiedboot": "green", "crypto": "encrypted",
                 "adb_wifi": "0", "root": False, "unknown_src": "0", "a11y": "null",
                 "admins": "0", "proxy": "null", "security_patch": "2099-01-01",
                 "vpn_app": "null", "dev_opts": "0"}
        assert dash._triage(clean) == []

    def test_proxy_and_admins_warn(self):
        tri = dash._triage({"proxy": "10.0.0.1:8080", "admins": "2"})
        texts = " ".join(t for _, t in tri)
        assert "Proxy" in texts and "Device-Admin" in texts
