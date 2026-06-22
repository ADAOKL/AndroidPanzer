"""Gemeinsame Test-Fixtures – u.a. ein Mock-ADB ohne echtes Gerät."""
from __future__ import annotations

import os
import sys

import pytest

# Projektwurzel in den Importpfad (Tests laufen ohne Installation).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class MockADB:
    """Minimaler ADB-Ersatz: liefert vordefinierte Ausgaben je nach Kommando.

    `responses` ist eine Liste von (substring, output)-Paaren – das erste Paar,
    dessen substring im Kommando vorkommt, gewinnt. Aufgezeichnete Kommandos
    landen in `calls` (für Injection-/Quoting-Tests).
    """

    def __init__(self, responses=None, default=""):
        self.responses = responses or []
        self.default = default
        self.calls: list[str] = []
        self.bin = "adb"
        self.serial = None
        self.root_mode = None

    def shell(self, cmd, timeout=None, root=False, retries=2):
        self.calls.append(cmd)
        for needle, out in self.responses:
            if needle in cmd:
                return out
        return self.default

    def shell_rc(self, cmd, timeout=None):
        self.calls.append(cmd)
        return 0

    def raw(self, args, timeout=None, check=False):
        self.calls.append(" ".join(args))
        return (0, "", "")

    def getprops(self, refresh=False):
        return {}

    def getprop(self, key, fresh=False):
        for needle, out in self.responses:
            if needle == key:
                return out
        return ""


@pytest.fixture
def mock_adb():
    return MockADB
