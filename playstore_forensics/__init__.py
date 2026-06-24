"""PlayStore Forensics – Artifact Extraction Package für AndroidPanzer."""
import sys
from pathlib import Path

# Projekt-Root (AndroidPanzer/) in sys.path – einmalig hier, nie in den Submodulen
_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from .main import menu, full_scan

__all__ = ["menu", "full_scan"]
__version__ = "1.0.0"
