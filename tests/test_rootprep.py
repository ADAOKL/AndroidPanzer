"""Tests für die Root-Vorbereitung: Plan-Bau, Konto-/FRP-Hinweise, Link-Auflösung."""
from __future__ import annotations

from apz import rootprep


class TestBuildPlan:
    def test_bootloader_locked(self):
        p = rootprep.build_plan({"brand": "Google", "bootloader_unlocked": "1"})
        assert p["bootloader"] == "locked"

    def test_bootloader_unlocked_flag(self):
        p = rootprep.build_plan({"brand": "Google", "bootloader_unlocked": "0"})
        assert p["bootloader"] == "unlocked"

    def test_bootloader_unlocked_verifiedboot(self):
        p = rootprep.build_plan({"brand": "x", "bootloader_unlocked": "", "verifiedboot": "orange"})
        assert p["bootloader"] == "unlocked"

    def test_has_method_and_guidance(self):
        p = rootprep.build_plan({"brand": "Samsung", "model": "S21"})
        assert "unlock_cmd" in p["method"]
        assert set(p["guidance"]) >= {"vor_unlock", "nach_unlock", "vor_flash", "nach_flash"}
        assert p["status"] == "running"


class TestAccountGuidance:
    def test_samsung_knox(self):
        g = rootprep.account_guidance("samsung")
        joined = " ".join(g["vor_unlock"])
        assert "Knox" in joined

    def test_xiaomi_wait(self):
        g = rootprep.account_guidance("xiaomi")
        assert "168" in " ".join(g["vor_unlock"])

    def test_pixel_initboot(self):
        g = rootprep.account_guidance("pixel")
        assert "init_boot" in " ".join(g["vor_unlock"])

    def test_frp_mentioned_for_all(self):
        for brand in ("", "google", "oneplus", "huawei"):
            g = rootprep.account_guidance(brand)
            assert any("FRP" in ln for ln in g["vor_unlock"])


class TestResolveDownloads:
    def test_builds_candidates_without_network(self, monkeypatch):
        # Netzwerk (GitHub) ausklammern – deterministisch testen.
        monkeypatch.setattr(rootprep, "resolve_magisk_apk",
                            lambda: rootprep._dl("Magisk", "https://x/Magisk.apk", "apk"))
        p = rootprep.build_plan({"brand": "Xiaomi", "model": "Mi 11", "bootloader_unlocked": "1"})
        rootprep.resolve_downloads(p)
        kinds = [d["kind"] for d in p["downloads"]]
        assert p["status"] == "done"
        assert "apk" in kinds
        # markenspezifischer Eintrag (Xiaomi → manuelle Fastboot-ROM-Quelle)
        assert any(d["kind"] in ("manual", "search", "builtin") for d in p["downloads"])
        assert any("Xiaomi" in d["label"] for d in p["downloads"])

    def test_dl_status(self):
        ready = rootprep._dl("a", "https://x/y.apk", "apk")
        manual = rootprep._dl("b", "", "manual")
        assert ready["status"] == "bereit"
        assert manual["status"] == "manuell"
