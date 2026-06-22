"""Tests für Custom-Firmware-Listing + TWRP-Versionsparser (ohne echtes Netz)."""
from __future__ import annotations

from apz import customfw, samsung

# Auszug einer dl.twrp.me-Listing-Seite (newest first), relative Links wie real.
SAMPLE_LISTING = """
<a href="twrp-3.7.0_9-2-beyond0lte.img.tar.html">x</a>
<a href="twrp-3.7.0_9-2-beyond0lte.img.html">x</a>
<a href="twrp-3.6.2_9-1-beyond0lte.img.tar.html">x</a>
"""


class TestTwrpAll:
    def test_parse_versions_and_links(self, monkeypatch):
        monkeypatch.setattr(samsung, "_http_get", lambda u, *a, **k: SAMPLE_LISTING)
        items = samsung._twrp_all(["beyond0lte"])
        assert items
        tar = next(i for i in items if i["kind"] == "tar")
        assert tar["version"] == "3.7.0_9-2"
        # .html gestrippt → echte Datei, korrekt relativ aufgelöst
        assert tar["fileurl"] == "https://dl.twrp.me/beyond0lte/twrp-3.7.0_9-2-beyond0lte.img.tar"
        assert tar["page_url"].endswith(".img.tar.html")
        # beide Formate (.img und .img.tar) erfasst
        assert {i["kind"] for i in items} == {"tar", "img"}

    def test_empty_when_no_twrp(self, monkeypatch):
        monkeypatch.setattr(samsung, "_http_get", lambda u, *a, **k: "<html>nichts</html>")
        assert samsung._twrp_all(["x"]) == []


class TestTwrpVersions:
    def test_versions_sorted(self, monkeypatch):
        monkeypatch.setattr(customfw, "_get", lambda u, *a, **k: SAMPLE_LISTING.encode())
        vers = customfw.twrp_versions("beyond0lte")
        assert vers[0] == "3.7.0_9-2" and "3.6.2_9-1" in vers


class TestCodenames:
    def test_includes_data_and_props(self, mock_adb):
        adb = mock_adb([("ro.product.device", "beyond0")])
        cs = customfw._codenames({"device": "beyond0lte"}, adb)
        assert "beyond0lte" in cs and "beyond0" in cs
