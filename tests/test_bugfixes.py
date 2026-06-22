"""Regressionstests für während der Bug-Jagd gefundene latente Crashes."""
from __future__ import annotations

from apz import aishell, ui


def test_multiselect_empty_no_zerodivision():
    # Früher: cursor % n mit n==0 → ZeroDivisionError. Jetzt: leere Auswahl.
    assert ui.multiselect([], lambda *a: "") == []


def test_random_recipe_empty_no_zerodivision():
    # Früher: % len(allr) mit leerem Katalog → ZeroDivisionError. Jetzt: None.
    assert aishell._random_recipe([]) is None
    assert aishell._random_recipe([("Kat", [])]) is None


def test_random_recipe_nonempty_returns_item():
    cats = [("Kat", ["a", "b", "c"])]
    assert aishell._random_recipe(cats) in ("a", "b", "c")
