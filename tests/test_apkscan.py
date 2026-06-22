"""Tests für die APK-Analyse: AXML-Parser, Scoring, IOC, Quoting."""
from __future__ import annotations

import os

import pytest

from apz import apkscan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_APK = os.path.join(ROOT, "samsung", "app-debug.apk")
has_sample = os.path.isfile(SAMPLE_APK)


class TestScoring:
    def test_stalkerware_combo_scores_high(self):
        perms = [f"android.permission.{p}" for p in
                 ("RECORD_AUDIO", "ACCESS_FINE_LOCATION", "READ_SMS", "READ_CONTACTS")]
        score, reasons = apkscan._score_perms(perms)
        assert score >= 5
        assert any("Stalkerware" in r for r in reasons)

    def test_benign_app_low_score(self):
        score, reasons = apkscan._score_perms(["android.permission.INTERNET"])
        assert score == 0

    def test_install_packages_flagged(self):
        score, reasons = apkscan._score_perms(["android.permission.REQUEST_INSTALL_PACKAGES"])
        assert score >= 3
        assert any("install" in r.lower() for r in reasons)


class TestAXMLParserSynthetic:
    def test_garbage_returns_empty(self):
        r = apkscan.parse_manifest(b"not an axml file at all")
        assert r["package"] == ""
        assert r["permissions"] == []

    def test_empty(self):
        r = apkscan.parse_manifest(b"")
        assert r["package"] == ""


@pytest.mark.skipif(not has_sample, reason="Beispiel-APK nicht vorhanden")
class TestAXMLParserReal:
    @pytest.fixture(scope="class")
    def result(self):
        return apkscan.analyze_apk_file(SAMPLE_APK)

    def test_ok(self, result):
        assert result["ok"] is True

    def test_package_extracted(self, result):
        # Echtes binäres AndroidManifest muss einen plausiblen Paketnamen liefern
        assert result["manifest"]["package"].count(".") >= 1

    def test_permissions_parsed(self, result):
        perms = result["manifest"]["permissions"]
        assert len(perms) >= 1
        assert all(p.startswith(("android.permission.", "com.", "android.")) or "." in p
                   for p in perms)

    def test_sha256_present(self, result):
        assert len(result["sha256"]) == 64

    def test_signed_detected(self, result):
        assert "signed" in result


class TestQuotingInDeviceCalls:
    def test_analyze_installed_quotes_pkg(self, mock_adb):
        # Ein bösartiger Paketname darf nicht unescaped in die Shell gelangen.
        evil = "x; rm -rf /"
        adb = mock_adb(responses=[("pm path", "")], default="")
        # leere pm-path-Antwort → Funktion bricht sauber ab; uns interessiert der call
        import apz.ui as ui
        ui.ask = lambda *a, **k: evil          # Eingabe simulieren
        ui.pause = lambda *a, **k: None
        try:
            apkscan.analyze_installed(adb, {})
        except Exception:
            pass
        joined = "\n".join(adb.calls)
        # Der rohe gefährliche String darf nicht unquoted erscheinen
        assert "pm path x; rm -rf /" not in joined
