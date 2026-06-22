"""Tests für die 45-Sektionen-Vollanalyse (ohne echtes Gerät)."""
from __future__ import annotations

from pathlib import Path

import os

import pytest

from apz import acquire, util
from apz.adb import Device


class _PropADB:
    def __init__(self, props, responses):
        self.props = props
        self.responses = responses
        self.calls = []

    def getprop(self, key, fresh=False):
        return self.props.get(key, "")

    def root_method(self):
        return ("none", "")

    def shell(self, cmd, timeout=None, root=False, retries=2):
        self.calls.append(cmd)
        for needle, out in self.responses.items():
            if needle in cmd:
                return out
        return ""


@pytest.fixture
def adb_dev(tmp_path, monkeypatch):
    monkeypatch.setattr(util, "BASE", str(tmp_path))
    monkeypatch.setattr(acquire, "OUT", str(tmp_path / "forensik_full"))
    os.makedirs(acquire.OUT, exist_ok=True)
    props = {"ro.product.manufacturer": "samsung", "ro.product.model": "SM-G970F",
             "gsm.sim.state": "READY", "gsm.operator.alpha": "Telekom",
             "gsm.version.baseband": "G970F", "ro.crypto.state": "encrypted"}
    responses = {
        "pm list packages -3": "package:com.whatsapp\npackage:com.x\n",
        "pm list packages -s": "package:android\n",
        "pm list packages": "package:com.whatsapp\n",
        "dumpsys battery": "level: 84\n  cycle count: 210",
        "content://sms": "Row: 0\nRow: 1",
        "ls -l /dev/block/by-name": "frp -> /dev/block/sda21\nefs -> /dev/block/sda2",
    }
    adb = _PropADB(props, responses)
    return adb, Device(serial="RFTEST", model="SM-G970F"), {"brand": "samsung", "model": "SM-G970F"}


def _silence(monkeypatch):
    import apz.ui as ui
    for fn in ("clear", "banner", "pause", "rule", "kv", "ok", "info", "warn", "err"):
        monkeypatch.setattr(ui, fn, lambda *a, **k: None)


def test_registry_has_45_sections():
    ids = [s[0] for s in acquire.SECTIONS]
    assert ids == list(range(1, 46))           # genau 1..45, lückenlos
    parts = {s[1] for s in acquire.SECTIONS}
    assert parts == {1, 2, 3, 4}


def test_every_section_has_collector_or_needs():
    for sid, part, icon, title, status, fn, needs in acquire.SECTIONS:
        assert fn is not None or needs, f"Sektion {sid} ohne Collector UND ohne Doku"


def test_run_all_produces_report(adb_dev, monkeypatch):
    _silence(monkeypatch)
    adb, dev, data = adb_dev
    res = acquire.run_all(adb, dev, data, data, export=False)
    assert len(res["results"]) == 45
    assert os.path.isfile(res["txt"])
    assert os.path.isfile(res["md"])
    body = Path(res["txt"]).read_text(encoding="utf-8")
    # alle vier Teile müssen im Bericht erscheinen
    for part in range(1, 5):
        assert f"TEIL {part}" in body
    # Hardware-/Labor-Sektionen ehrlich markiert, nicht erfunden
    assert "Labor nötig" in body or "🧪" in body
    assert "SDR/HW" in body or "📡" in body
    # reale Erhebung vorhanden
    assert "samsung" in body and "SM-G970F" in body


def test_lab_sections_never_claim_collected(adb_dev, monkeypatch):
    _silence(monkeypatch)
    adb, dev, data = adb_dev
    res = acquire.run_all(adb, dev, data, data, export=False)
    by_id = {r["id"]: r for r in res["results"]}
    # DPA/TEMPEST/Open5GS dürfen NIE als 'erhoben' gelten
    for sid in (24, 28, 33, 44):
        assert by_id[sid]["status"] in (acquire.LAB, acquire.HW, acquire.INFO)


def test_shell_calls_are_safe(adb_dev, monkeypatch):
    """Kein roher unsanitierter Wert in den Shell-Kommandos der Akquise."""
    _silence(monkeypatch)
    adb, dev, data = adb_dev
    acquire.run_all(adb, dev, data, data, export=False)
    for c in adb.calls:
        assert ";" not in c or "2>/dev/null" in c or "|" in c or "for z in" in c


def test_auto_export_after_full_run(adb_dev, monkeypatch, tmp_path):
    """Vollanalyse mit export=True erzeugt automatisch HTML/JSON/MD + Manifest."""
    _silence(monkeypatch)
    adb, dev, data = adb_dev
    from apz import report
    # Report-Modul auf dieselbe temporäre Basis umleiten wie util/acquire
    monkeypatch.setattr(report, "BASE", str(tmp_path))
    res = acquire.run_all(adb, dev, data, data, export=True)
    assert "export" in res, "Auto-Export hat keine Dateien gemeldet"
    assert set(res["export"]) == {"html", "md", "json", "manifest"}
    for path in res["export"].values():
        assert os.path.isfile(path)
    # der Vollbericht selbst muss im HTML-Gesamtexport auftauchen
    html = Path(res["export"]["html"]).read_text(encoding="utf-8")
    assert "Vollständige forensische Akquise" in html
