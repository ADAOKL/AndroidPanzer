"""Tests für die zentralen Helfer (Quoting, Validierung, Hashing)."""
from __future__ import annotations

from apz import util


class TestShq:
    def test_simple_unchanged_meaning(self):
        assert util.shq("com.example.app") == "com.example.app"

    def test_spaces_quoted(self):
        assert util.shq("a b") == "'a b'"

    def test_injection_neutralised(self):
        # Klassischer Injection-Versuch darf nicht als Shell-Syntax durchschlagen.
        out = util.shq("foo; rm -rf /")
        assert ";" in out
        assert out.startswith("'") and out.endswith("'")
        assert "rm -rf" in out  # Inhalt bleibt, aber gequotet

    def test_single_quote_escaped(self):
        # shlex muss eingebettete Quotes sicher behandeln
        assert util.shq("a'b") == "'a'\"'\"'b'"

    def test_non_string(self):
        assert util.shq(500) == "500"


class TestValidators:
    def test_valid_pkg(self):
        assert util.valid_pkg("com.whatsapp")
        assert util.valid_pkg("org.telegram.messenger")
        assert util.valid_pkg("com.app:remote")

    def test_invalid_pkg(self):
        assert not util.valid_pkg("foo; rm -rf /")
        assert not util.valid_pkg("a b")
        assert not util.valid_pkg("")
        assert not util.valid_pkg(".start")  # darf nicht mit Punkt beginnen

    def test_clean_pkg(self):
        assert util.clean_pkg("  com.x  ") == "com.x"
        assert util.clean_pkg("bad name") == ""

    def test_valid_perm(self):
        assert util.valid_perm("android.permission.CAMERA")
        assert not util.valid_perm("foo;bar")


class TestHashing:
    def test_sha256_text_known(self):
        # SHA-256 von "abc"
        assert util.sha256_text("abc") == (
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_sha256_file(self, tmp_path):
        p = tmp_path / "f.bin"
        p.write_bytes(b"abc")
        assert util.sha256_file(str(p)) == util.sha256_text("abc")


class TestNumericInputValidation:
    def test_as_int_valid(self):
        assert util.as_int("42") == 42
        assert util.as_int("  7 ") == 7

    def test_as_int_invalid_uses_default(self):
        assert util.as_int("", 10) == 10
        assert util.as_int("abc", 10) == 10
        assert util.as_int(None, 5) == 5
        assert util.as_int("10; rm -rf /", 10) == 10   # Injection → Default

    def test_as_int_clamping(self):
        assert util.as_int("999", 10, lo=1, hi=180) == 180
        assert util.as_int("0", 10, lo=1, hi=180) == 1

    def test_is_coords(self):
        assert util.is_coords("540 1200")
        assert util.is_coords("500 1500 500 300 300")
        assert util.is_coords("66")

    def test_is_coords_rejects_injection(self):
        assert not util.is_coords("540; reboot")
        assert not util.is_coords("$(rm -rf /)")
        assert not util.is_coords("abc")
        assert not util.is_coords("")


class TestHumanSize:
    def test_bytes(self):
        assert util.human_size(0) == "0 B"
        assert util.human_size(512) == "512 B"

    def test_scaling(self):
        assert util.human_size(1536) == "1.5 KB"
        assert util.human_size(1048576) == "1.0 MB"
