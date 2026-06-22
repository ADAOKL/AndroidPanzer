"""Tests für Parser/Helfer der Forensik-Module (ohne echtes Gerät, via MockADB)."""
from __future__ import annotations

from apz import dashboard, dataforensics


class TestTimestamp:
    def test_seconds(self):
        # 2021-01-01 00:00:00 UTC = 1609459200 s
        out = dataforensics._ts("1609459200")
        assert out.startswith("2021-01-01") or out.startswith("2020-12-31")  # lokale TZ

    def test_milliseconds(self):
        out = dataforensics._ts("1609459200000")
        assert "2021" in out or "2020" in out

    def test_invalid(self):
        assert dataforensics._ts("nichts") == "—"
        assert dataforensics._ts("0") == "—"


class TestContentQuery:
    SAMPLE = (
        "Row: 0 _id=1, name=Alice, number=+49123\n"
        "Row: 1 _id=2, name=Bob, number=+49456\n"
    )

    def test_parses_rows(self, mock_adb):
        adb = mock_adb(responses=[("content query", self.SAMPLE)])
        rows = dataforensics._query(adb, "content://contacts")
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[1]["number"] == "+49456"

    def test_permission_error_returns_empty(self, mock_adb):
        adb = mock_adb(responses=[("content query", "Error: Permission Denial")])
        assert dataforensics._query(adb, "content://sms") == []

    def test_limit(self, mock_adb):
        adb = mock_adb(responses=[("content query", self.SAMPLE)])
        rows = dataforensics._query(adb, "content://contacts", limit=1)
        assert len(rows) == 1


class TestDashboardHelpers:
    def test_grep(self):
        assert dashboard._grep("level: 87", r"level:\s*(\d+)") == "87"
        assert dashboard._grep("nichts", r"level:\s*(\d+)") == ""

    def test_temp_volt(self):
        assert dashboard._temp("305") == "30.5 °C"
        assert dashboard._volt("4123") == "4.123 V"
        assert dashboard._temp("abc") == ""

    def test_health(self):
        assert dashboard._health("2") == "Gut"
        assert dashboard._health("4") == "Defekt"

    def test_plug(self):
        assert dashboard._plug("AC powered: true") == "lädt (AC)"
        assert dashboard._plug("USB powered: true") == "lädt (USB)"
        assert dashboard._plug("nichts geladen") == "Akku"

    def test_first(self):
        assert dashboard._first("", "unknown", "0", "echt") == "echt"
        assert dashboard._first("", "  ") == ""
