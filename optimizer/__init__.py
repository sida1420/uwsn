"""Isolated D-ACO parameter research; never changes production defaults."""
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
# Optional local dependencies used by the implementation smoke tests.
if (PACKAGE / '.deps').is_dir():
    sys.path.insert(0, str(PACKAGE / '.deps'))
sys.path.insert(0, str(ROOT / 'src'))
