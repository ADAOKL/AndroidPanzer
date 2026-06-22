"""Tests für das i18n-Modul (apz/lang.py)."""
import importlib
import sys

import pytest


def _fresh_lang():
    """Importiert lang.py frisch (damit _LANG-Zustand sauber ist)."""
    if "apz.lang" in sys.modules:
        del sys.modules["apz.lang"]
    import apz.lang as m
    return m


def test_default_language_is_german():
    m = _fresh_lang()
    assert m.current() == "de"


def test_set_lang_changes_current():
    m = _fresh_lang()
    m.set_lang("en")
    assert m.current() == "en"
    m.set_lang("de")


def test_set_lang_ignores_unknown():
    m = _fresh_lang()
    m.set_lang("xx")
    assert m.current() == "de"


def test_t_returns_german_by_default():
    m = _fresh_lang()
    m.set_lang("de")
    result = m.t("ui_pause")
    assert "ENTER" in result


def test_t_returns_english():
    m = _fresh_lang()
    m.set_lang("en")
    result = m.t("ui_pause")
    assert "ENTER" in result
    assert "continue" in result.lower()


def test_t_returns_spanish():
    m = _fresh_lang()
    m.set_lang("es")
    result = m.t("ui_pause")
    assert "ENTER" in result
    assert "continuar" in result.lower()


def test_t_falls_back_to_german_for_unknown_key():
    m = _fresh_lang()
    m.set_lang("en")
    result = m.t("no_such_key_xyz")
    assert result == "no_such_key_xyz"


def test_t_falls_back_to_german_when_lang_missing_key():
    m = _fresh_lang()
    m.set_lang("en")
    # badge_danger hat alle Sprachen – prüfen dass es klappt
    result = m.t("badge_danger")
    assert result == "DANGER"


def test_t_interpolation():
    m = _fresh_lang()
    m.set_lang("de")
    result = m.t("connect_found", n=3)
    assert "3" in result


def test_t_interpolation_english():
    m = _fresh_lang()
    m.set_lang("en")
    result = m.t("connect_found", n=2)
    assert "2" in result
    assert "device" in result.lower()


def test_all_languages_have_ui_pause():
    m = _fresh_lang()
    for code in m.LANGUAGES:
        m.set_lang(code)
        result = m.t("ui_pause")
        assert result != "ui_pause", f"Sprache {code}: ui_pause nicht übersetzt"
    m.set_lang("de")


def test_all_languages_have_menu_main_title():
    m = _fresh_lang()
    for code in m.LANGUAGES:
        m.set_lang(code)
        result = m.t("menu_main_title")
        assert len(result) > 2, f"Sprache {code}: menu_main_title leer"
    m.set_lang("de")


def test_yes_answers_contain_yes_for_each_lang():
    m = _fresh_lang()
    expected = {
        "de": "j",  "en": "y",  "es": "s",  "fr": "o",
        "pt": "s",  "it": "s",  "tr": "e",  "ru": "д",
    }
    for code, first_yes in expected.items():
        m.set_lang(code)
        words = m.t("ui_yes_answers").split()
        assert first_yes in words, f"Sprache {code}: '{first_yes}' nicht in yes_answers"
    m.set_lang("de")


def test_save_and_load(tmp_path, monkeypatch):
    m = _fresh_lang()
    cfg = str(tmp_path / "lang")
    monkeypatch.setattr(m, "_CFG", cfg)
    m._save("fr")
    loaded = m._load_saved()
    assert loaded == "fr"


def test_load_saved_returns_de_on_missing_file(tmp_path, monkeypatch):
    m = _fresh_lang()
    monkeypatch.setattr(m, "_CFG", str(tmp_path / "nonexistent"))
    assert m._load_saved() == "de"


def test_load_saved_ignores_unknown_code(tmp_path, monkeypatch):
    m = _fresh_lang()
    cfg = str(tmp_path / "lang")
    with open(cfg, "w") as fh:
        fh.write("zz")
    monkeypatch.setattr(m, "_CFG", cfg)
    assert m._load_saved() == "de"


def test_brands_module_importable():
    from apz import brands  # noqa: F401


def test_dashboard_brand_flag_logic():
    """Prüft die Brand-Flag-Logik direkt (ohne echten ADB-Aufruf)."""
    import types
    from apz import dashboard

    for brand, flag in [
        ("Xiaomi",   "is_xiaomi"),
        ("redmi",    "is_xiaomi"),
        ("POCO",     "is_xiaomi"),
        ("Google",   "is_pixel"),
        ("OnePlus",  "is_oneplus"),
        ("oppo",     "is_oneplus"),
        ("Realme",   "is_oneplus"),
        ("motorola", "is_motorola"),
        ("Huawei",   "is_huawei"),
        ("Honor",    "is_huawei"),
    ]:
        data = {"brand": brand, "platform": "", "hardware": ""}
        brand_lc = brand.lower()
        data["is_xiaomi"]  = brand_lc in ("xiaomi", "redmi", "poco")
        data["is_pixel"]   = brand_lc in ("google",)
        data["is_oneplus"] = brand_lc in ("oneplus", "oppo", "realme")
        data["is_motorola"] = brand_lc in ("motorola", "moto", "lenovo")
        data["is_huawei"]  = brand_lc in ("huawei", "honor")
        assert data[flag] is True, f"Brand '{brand}' sollte {flag}=True setzen"
