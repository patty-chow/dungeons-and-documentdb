"""Convenience runners for setting up and seeding the realm."""
import sys
from pathlib import Path

# Make `from src...` work when these scripts are run as `python scripts/foo.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
