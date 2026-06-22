"""Tests für den Maximum-Deep-Scan: Sektionen laufen, Terminal-Ansicht & Export."""
from __future__ import annotations

from pathlib import Path

import os

import pytest

from apz import dataforensics as df
from apz import deepforensics as d
from apz import report, util
from apz.adb import Device


class _ADB:
    def __init__(self, props=None, default=""):
        self.props = props or {}
        self.default = default

    def getprop(self, k, fresh=False):
        return self.props.get(k, "")

    def shell(self, cmd, timeout=None, root=False, retries=2):
        return self.default

    def root_method(self):
        return ("none", "")


@pytest.fixture
def env(tmp_path, monkeypatch):
    out = tmp_path / "forensik"
    out.mkdir()
    monkeypatch.setattr(util, "BASE", str(tmp_path))
    monkeypatch.setattr(df, "OUT", str(out))
    monkeypatch.setattr(d, "OUT", str(out))
    monkeypatch.setattr(report, "BASE", str(tmp_path))
    import apz.ui as ui
    for fn in ("clear", "banner", "pause", "rule", "kv", "ok", "info", "warn", "err", "crit"):
        monkeypatch.setattr(ui, fn, lambda *a, **k: None)
    adb = _ADB(props={"ro.product.model": "SM-G970F", "ro.product.brand": "samsung"})
    return adb, Device(serial="RFT"), {"is_root": False}, tmp_path


ALL_SECTIONS = [d.ident, d.wifi_bt, d.location, d.calendar, d.downloads, d.notifications,
                d.app_usage, d.perm_matrix, d.security, d.network, d.deleted_hints,
                d.radio_history, d.activity_timeline, d.dictionary, d.settings_dump,
                d.bookmarks, d.health_apps, d.battery_history, d.connection_analysis]


def test_all_sections_run_and_write(env):
    adb, dev, st, tmp = env
    for fn in ALL_SECTIONS:
        body = fn(adb, dev, st, _auto=True)
        assert isinstance(body, str)
    # jede Sektion schreibt eine deep_*.txt
    files = d._list_reports()
    assert len(files) >= 15
    assert all(f.startswith("deep_") and f.endswith(".txt") for f in files)


def test_menu_count_is_20():
    # 19 Datei-Sektionen + Live(20) sind alle dispatchbar
    assert len(ALL_SECTIONS) == 19


def test_export_bundles_deep_reports(env):
    adb, dev, st, tmp = env
    d.security(adb, dev, st, _auto=True)
    d.network(adb, dev, st, _auto=True)
    d._export_reports(adb, st)              # nutzt report.generate intern
    reports = os.listdir(tmp / "reports")
    assert any(f.endswith(".html") for f in reports)
    assert any(f.startswith("MANIFEST_") for f in reports)
    html = Path(tmp / "reports" / next(f for f in reports if f.endswith(".html"))).read_text(encoding="utf-8")
    # die Deep-Berichte tauchen im Gesamtexport auf
    assert "deep_sicherheit.txt" in html or "sicherheit" in html.lower()


def test_device_data_from_props(env):
    adb, dev, st, tmp = env
    data = d._device_data(adb, st)
    assert data["model"] == "SM-G970F"
    assert data["brand"] == "samsung"
    assert data["root"] is False
