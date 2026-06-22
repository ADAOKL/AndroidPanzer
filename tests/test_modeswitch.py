"""Tests für den automatischen Modus-Wechsel (ohne echtes Gerät, via Mock)."""
from __future__ import annotations

from apz import modeswitch
from apz.adb import Device


class TestTables:
    def test_satisfy_and_sub_consistent(self):
        # Jeder Zielmodus hat eine adb-reboot-Zuordnung und eine Erfüllungsmenge.
        assert set(modeswitch._SATISFY) == set(modeswitch._ADB_SUB)
        assert set(modeswitch._SATISFY) <= set(modeswitch._LABEL)

    def test_phys_samsung_download(self):
        lines = " ".join(modeswitch._phys("samsung", "download"))
        assert "Vol-Hoch" in lines and "Download" in lines or "blau" in lines

    def test_phys_samsung_has_no_fastboot(self):
        assert "KEINEN Fastboot" in " ".join(modeswitch._phys("Samsung", "fastboot"))


class TestCurrentAndWait:
    def test_current_matches_serial(self, monkeypatch):
        devs = [Device(serial="AAA", mode="adb"), Device(serial="BBB", mode="fastboot")]
        monkeypatch.setattr(modeswitch.usb, "detect_all", lambda: devs)
        assert modeswitch.current("BBB").serial == "BBB"

    def test_wait_returns_on_match(self, monkeypatch):
        monkeypatch.setattr(modeswitch.usb, "detect_all",
                            lambda: [Device(serial="", mode="odin")])
        d = modeswitch.wait_for_mode({"odin"}, timeout=5)
        assert d is not None and d.mode == "odin"

    def test_wait_times_out(self, monkeypatch):
        monkeypatch.setattr(modeswitch.usb, "detect_all", lambda: [])
        assert modeswitch.wait_for_mode({"odin"}, timeout=0) is None


class _FakeADB:
    """Minimaler ADB-Ersatz, der reboot-Aufrufe mitschreibt."""
    def __init__(self, state):
        self.calls = []
        self._state = state

    def raw(self, args, timeout=None, check=False):
        self.calls.append(" ".join(args))
        if args[:1] == ["reboot"]:
            self._state["rebooted"] = True
        return (0, "", "")

    def getprop(self, key, fresh=False):
        return "samsung" if "brand" in key else ""


class TestEnsure:
    def test_already_in_target_is_noop(self, monkeypatch):
        monkeypatch.setattr(modeswitch.usb, "detect_all",
                            lambda: [Device(serial="AAA", mode="adb")])
        adb = _FakeADB({})
        ok, dev = modeswitch.ensure(adb, Device(serial="AAA", mode="adb"), "system")
        assert ok and dev.mode == "adb"
        assert adb.calls == []          # KEIN Reboot nötig

    def test_auto_reboot_to_download(self, monkeypatch):
        state = {"rebooted": False}

        def detect():
            # vor Reboot: ADB-Gerät; nach Reboot: Download-Modus (odin)
            return ([Device(serial="", mode="odin")] if state["rebooted"]
                    else [Device(serial="AAA", mode="adb")])
        monkeypatch.setattr(modeswitch.usb, "detect_all", detect)
        adb = _FakeADB(state)
        ok, dev = modeswitch.ensure(adb, Device(serial="AAA", mode="adb"), "download", timeout=5)
        assert ok and dev.mode == "odin"
        assert any("reboot download" in c for c in adb.calls)

    def test_unknown_target(self):
        ok, dev = modeswitch.ensure(_FakeADB({}), Device(serial="X", mode="adb"), "quatsch")
        assert ok is False and dev is None
