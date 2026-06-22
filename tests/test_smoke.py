"""Smoke-Test: alle Module importieren & Registry ist konsistent."""
from __future__ import annotations

import importlib
import pkgutil

import apz


def test_all_modules_import():
    mods = [m.name for m in pkgutil.iter_modules(apz.__path__)]
    for m in mods:
        importlib.import_module(f"apz.{m}")
    assert len(mods) >= 25


def test_registry_counts():
    from apz import registry
    assert len(registry.CATEGORIES) == 45
    total = sum(len(feats) for _icon, _name, feats in registry.CATEGORIES)
    assert total == 450


def test_registry_kinds_known():
    from apz import registry
    known = {"cmd", "rootcmd", "ask", "fn", "info", "sdr", "danger"}
    for _icon, _name, feats in registry.CATEGORIES:
        for ft in feats:
            assert ft["k"] in known, f"unbekannte Art: {ft['k']}"
            assert "n" in ft and "t" in ft


def test_no_unsafe_fstring_shell_calls():
    """Regressionsschutz: keine unsanitierten Variablen mehr in adb.shell-f-Strings.

    Sucht nach shell(f"... {var} ...") wo var kein Literal/kein shq()/keine
    Zahl ist – ein grober, aber wirksamer Wächter gegen neue Injection-Stellen.
    """
    import os
    import re

    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apz")
    # erlaubte Interpolationen in Shell-f-Strings
    # Erlaubt sind nur Tokens, die NACHWEISLICH sicher sind:
    #  • shq(...)            – per shlex gequotet
    #  • secs/code/xy/v      – VALIDIERTE numerische UI-Eingaben (as_int/is_coords/isdigit
    #                          in handlers.tap/swipe/keyevent/screenrecord)
    #  • verb/key/SERVER_PATH/proxy/cert/q/query/tmp/remote/uri/sort/projection/flags
    #                        – code-kontrollierte Literale/Konstanten
    #  • esc                 – text_input: Quotes entfernt, in '' gekapselt
    #  • i/d/rp/n            – Schleifen-Indizes / konstante bzw. shq-gequotete Werte
    allow = re.compile(r"\{(shq\([^}]*\)|q|query|tmp|remote|secs|code|xy|v|esc|n|"
                       r"flags|i|d|rp|uri|sort|projection|verb|SERVER_PATH|key|proxy|cert)\}")
    pat = re.compile(r"shell\(f([\"'])(.*?)\1")
    offenders = []
    for fn in os.listdir(root):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(root, fn), encoding="utf-8") as _fh:
            text = _fh.read()
        for m in pat.finditer(text):
            body = m.group(2)
            # alle {…}-Vorkommen prüfen
            for br in re.finditer(r"\{[^}]*\}", body):
                token = br.group(0)
                if not allow.search(token):
                    offenders.append(f"{fn}: {token}  in  shell(f{m.group(1)}{body[:60]}…)")
    assert not offenders, "Unsichere Interpolation gefunden:\n" + "\n".join(offenders)
