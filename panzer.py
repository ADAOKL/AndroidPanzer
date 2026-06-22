#!/usr/bin/env python3
"""Android Panzer – Start-Launcher.

Aufruf:   python3 panzer.py
Voraussetzung: adb (Android platform-tools) im PATH, USB-Debugging am Gerät.
"""
import sys

if sys.version_info < (3, 8):
    sys.exit("Python 3.8+ erforderlich.")

from apz import lang        # noqa: E402
from apz.main import run    # noqa: E402

if __name__ == "__main__":
    try:
        lang.select_language()
        sys.exit(run())
    except KeyboardInterrupt:
        msg = lang.t("startup_aborted")
        print(f"\n\033[0m🛡  {msg}")
        sys.exit(130)
