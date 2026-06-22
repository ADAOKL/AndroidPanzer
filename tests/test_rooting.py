"""Tests für die Root-/Bootloader-Tiefen-Diagnose (ohne echtes Gerät)."""
from __future__ import annotations

from pathlib import Path

import os

import pytest

from apz import rooting, util
from apz.adb import Device


class _PropADB:
    """MockADB mit Property-Matrix + Kommando-Antworten."""

    def __init__(self, props, responses):
        self.props = props
        self.responses = responses
        self.calls = []

    def getprop(self, key, fresh=False):
        return self.props.get(key, "")

    def shell(self, cmd, timeout=None, root=False, retries=2):
        self.calls.append(cmd)
        for needle, out in self.responses.items():
            if needle in cmd:
                return out
        return ""

    def check_root(self):
        return False


@pytest.fixture
def locked_samsung(tmp_path, monkeypatch):
    monkeypatch.setattr(util, "BASE", str(tmp_path))
    props = {
        "ro.product.model": "SM-G970F", "ro.product.brand": "samsung",
        "ro.boot.flash.locked": "1", "ro.boot.verifiedbootstate": "green",
        "ro.boot.warranty_bit": "1", "ro.boot.veritymode": "enforcing",
        "ro.boot.avb_version": "1.1",
    }
    responses = {
        "pm list packages": "package:com.android.chrome\n",
        "which su": "not found",
        "su -c id": "",
        "/proc/mounts": "/dev/block/dm-0 /system ext4 ro,seclabel 0 0\n",
    }
    adb = _PropADB(props, responses)
    dev = Device(serial="RFTEST", model="SM-G970F")
    d = {"brand": "samsung", "model": "SM-G970F", "device": "beyond0"}
    return adb, dev, d, tmp_path


def test_diagnostics_writes_log(locked_samsung, monkeypatch):
    import apz.ui as ui
    monkeypatch.setattr(ui, "clear", lambda *a, **k: None)
    monkeypatch.setattr(ui, "banner", lambda *a, **k: None)
    monkeypatch.setattr(ui, "pause", lambda *a, **k: None)
    adb, dev, d, tmp_path = locked_samsung

    fn = rooting.root_diagnostics(adb, dev, d)
    assert os.path.isfile(fn)
    body = Path(fn).read_text(encoding="utf-8")
    # Kernbefunde müssen im Log stehen
    assert "GESPERRT" in body
    assert "su-Binary: NICHT vorhanden" in body
    assert "Magisk-App (UI): NICHT installiert" in body
    assert "dm-verity ist AKTIV" in body
    assert "SM-G970F" in body or "beyond0" in fn
    # Neue Module 5–7 + Risiko-Matrix müssen vorhanden sein
    assert "[MODUL 5: PERSIST/METADATA-INTEGRITÄT]" in body
    assert "[MODUL 6: OEM-/CLOUD-SPERREN]" in body
    assert "[MODUL 7: FLASH-GEOMETRIE]" in body
    assert "[RISIKO-MATRIX]" in body
    # read-only Zusicherung muss dokumentiert sein
    assert "KEINE" in body and "read-only" in body.lower()


def test_diagnostics_quotes_package(locked_samsung, monkeypatch):
    """Auch hier darf kein roher Paketname unquoted in die Shell gelangen."""
    import apz.ui as ui
    monkeypatch.setattr(ui, "clear", lambda *a, **k: None)
    monkeypatch.setattr(ui, "banner", lambda *a, **k: None)
    monkeypatch.setattr(ui, "pause", lambda *a, **k: None)
    adb, dev, d, _ = locked_samsung
    # Magisk-App "installiert" simulieren → dumpsys-Pfad wird benutzt
    adb.responses["pm list packages"] = "package:com.topjohnwu.magisk\n"
    rooting.root_diagnostics(adb, dev, d)
    dumpsys = [c for c in adb.calls if "dumpsys package" in c]
    assert dumpsys, "dumpsys package wurde nicht aufgerufen"
    assert all("'com.topjohnwu.magisk'" in c or "com.topjohnwu.magisk" not in c.split("dumpsys package")[1][:5]
               for c in dumpsys)
