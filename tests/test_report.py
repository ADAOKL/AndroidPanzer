"""Tests für den einheitlichen Report/Export (HTML/MD/JSON + Manifest)."""
from __future__ import annotations

from pathlib import Path

import os

import pytest

from apz import report, util


@pytest.fixture
def fake_base(tmp_path, monkeypatch):
    """Leitet die Projektbasis auf ein temporäres Verzeichnis um und legt
    ein paar Artefakte an."""
    monkeypatch.setattr(util, "BASE", str(tmp_path))
    monkeypatch.setattr(report, "BASE", str(tmp_path))
    fdir = tmp_path / "forensik"
    fdir.mkdir()
    (fdir / "konten.txt").write_text("Konto: test@example.com\n", encoding="utf-8")
    (fdir / "sms.txt").write_text("SMS: hallo welt\n", encoding="utf-8")
    osint = tmp_path / "osint"
    osint.mkdir()
    (osint / "ip_8.8.8.8.txt").write_text("Google DNS\n", encoding="utf-8")
    return tmp_path


def test_collect_finds_files(fake_base):
    items = report.collect()
    names = {i["name"] for i in items}
    assert {"konten.txt", "sms.txt", "ip_8.8.8.8.txt"} <= names
    for it in items:
        assert len(it["sha256"]) == 64
        assert it["preview"] is not None  # kleine Textdateien werden eingebettet


def test_generate_all_formats(fake_base):
    summary = report.generate(data={"brand": "Test", "model": "X", "serial": "S1",
                                    "android": "14", "root": True})
    assert summary["files_total"] == 3
    rf = summary["report_files"]
    assert set(rf) == {"html", "md", "json", "manifest"}
    for path in rf.values():
        assert os.path.isfile(path)
    # HTML enthält Gerätedaten und eine Sektion
    html = Path(rf["html"]).read_text(encoding="utf-8")
    assert "FORENSIK-REPORT" in html
    assert "Test" in html


def test_manifest_is_sha256sum_compatible(fake_base):
    summary = report.generate(formats=("manifest",))
    man = summary["report_files"]["manifest"]
    lines = [l for l in Path(man).read_text(encoding="utf-8").splitlines() if l]
    assert lines
    for line in lines:
        h, sep, rel = line.partition("  ")
        assert sep == "  "
        assert len(h) == 64
        # Pfad relativ zur Basis und Datei existiert
        assert os.path.isfile(os.path.join(summary["base"], rel))


def test_manifest_detects_tampering(fake_base):
    """Nach Erzeugen des Manifests eine Datei ändern → Verifikation muss anschlagen."""
    summary = report.generate(formats=("manifest",))
    man_lines = Path(summary["report_files"]["manifest"]).read_text(encoding="utf-8").splitlines()
    # Eine der gelisteten Dateien manipulieren
    rel = man_lines[0].split("  ", 1)[1]
    target = os.path.join(str(fake_base), rel)
    with open(target, "a", encoding="utf-8") as f:
        f.write("MANIPULIERT\n")
    # Neu hashen und mit altem Manifest vergleichen
    new_hash = util.sha256_file(target)
    old_hash = man_lines[0].split("  ", 1)[0]
    assert new_hash != old_hash
