"""Security-Regressionstests: Tar-/Zip-Slip, Dateinamen, Download-HTTPS."""
from __future__ import annotations

import io
import os
import tarfile
import zipfile

import pytest

from apz import util


class TestSafeName:
    def test_strips_path(self):
        assert "/" not in util.safe_name("../../etc/passwd")
        assert util.safe_name("../../etc/passwd") == "passwd"

    def test_strips_traversal_and_specials(self):
        assert util.safe_name("a/b/../c;rm -rf") and "/" not in util.safe_name("a/b/../c;rm -rf")
        assert util.safe_name("") == "out"
        assert ".." not in util.safe_name("....//....//x")

    def test_keeps_safe(self):
        assert util.safe_name("konto_user_gmail_com.txt") == "konto_user_gmail_com.txt"


class TestIsWithin:
    def test_within(self, tmp_path):
        assert util.is_within(str(tmp_path), str(tmp_path / "a" / "b"))

    def test_escape(self, tmp_path):
        assert not util.is_within(str(tmp_path), str(tmp_path.parent / "evil"))


class TestTarSlip:
    def _tar_with(self, tmp_path, member_name):
        p = tmp_path / "evil.tar"
        with tarfile.open(p, "w") as tf:
            info = tarfile.TarInfo(member_name)
            data = b"PWNED"
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        return p

    def test_rejects_absolute(self, tmp_path):
        p = self._tar_with(tmp_path, "/tmp/evil_abs")
        dest = tmp_path / "out"; dest.mkdir()
        with tarfile.open(p) as tf:
            m = tf.getmembers()[0]
            with pytest.raises(ValueError):
                util.safe_extract_member(tf, m, str(dest))

    def test_rejects_traversal(self, tmp_path):
        p = self._tar_with(tmp_path, "../../escape")
        dest = tmp_path / "out"; dest.mkdir()
        with tarfile.open(p) as tf:
            m = tf.getmembers()[0]
            with pytest.raises(ValueError):
                util.safe_extract_member(tf, m, str(dest))
        # nichts außerhalb geschrieben
        assert not (tmp_path / "escape").exists()

    def test_allows_safe(self, tmp_path):
        p = self._tar_with(tmp_path, "sub/ok.img")
        dest = tmp_path / "out"; dest.mkdir()
        with tarfile.open(p) as tf:
            m = tf.getmembers()[0]
            target = util.safe_extract_member(tf, m, str(dest))
        assert os.path.isfile(target)
        assert util.is_within(str(dest), target)


class TestZipSlip:
    def test_rejects_traversal(self, tmp_path):
        p = tmp_path / "evil.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("../../escape.txt", "PWNED")
        dest = tmp_path / "out"; dest.mkdir()
        with zipfile.ZipFile(p) as z:
            with pytest.raises(ValueError):
                util.safe_extract_member(z, "../../escape.txt", str(dest))
        assert not (tmp_path / "escape.txt").exists()


class TestHttpsOnly:
    def test_rejects_http(self):
        with pytest.raises(ValueError):
            util.https_only("http://evil.example/frida-server")

    def test_allows_https(self):
        util.https_only("https://github.com/frida/frida/releases/x")  # darf nicht werfen

    def test_allows_localhost(self):
        util.https_only("http://localhost:11434/api")  # ollama lokal ok
