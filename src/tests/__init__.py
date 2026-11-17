"""Unit tests. Run from the project root with:

    python -m unittest discover -s src/tests -t src

Importing this package puts ``src`` on the import path, so the tests also
run from an IDE with ``src`` marked as the sources root.
"""

import logging
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Keep test output clean: without a handler Python would print warnings to the
# console. Tests that check logging use assertLogs, which still sees everything.
logging.getLogger().addHandler(logging.NullHandler())
