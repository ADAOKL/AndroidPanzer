"""Regression: forensics._score_apps darf Teil-Paketnamen NICHT als
Accessibility/Device-Admin werten (früher Substring-Test gegen den Rohstring)."""
from __future__ import annotations

from apz import forensics

# Vier sensible Rechte, damit die App im Ranking überhaupt auftaucht.
PERMS = ("android.permission.RECORD_AUDIO: granted=true\n"
         "android.permission.ACCESS_FINE_LOCATION: granted=true\n"
         "android.permission.READ_SMS: granted=true\n"
         "android.permission.READ_CONTACTS: granted=true\n")


def test_score_apps_no_substring_false_positive(mock_adb):
    adb = mock_adb([("dumpsys package", PERMS)])   # gleiche Rechte für jede App
    third = {"com.foo", "com.foo.bar"}
    # Accessibility-Dienst NUR für com.foo.bar – com.foo ist nur ein Substring davon.
    acc = "com.foo.bar/.AccService"
    admins = "admin=ComponentInfo{com.foo.bar/.AdminReceiver}"
    ranked = {r["pkg"]: r["reasons"] for r in
              forensics._score_apps(adb, third, set(), set(), acc, admins)}

    assert "Accessibility!" in ranked["com.foo.bar"]
    assert "Device-Admin!" in ranked["com.foo.bar"]
    # com.foo darf NICHT fälschlich markiert werden, obwohl sein Name Substring ist
    assert "Accessibility!" not in ranked.get("com.foo", [])
    assert "Device-Admin!" not in ranked.get("com.foo", [])
