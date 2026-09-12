"""Backward compat shim — use scripts/python/extract.py."""

import warnings

warnings.warn(
    "scripts/extract.py is deprecated, use scripts/python/extract.py or 'python -m scripts.python.extract'",
    DeprecationWarning,
    stacklevel=2,
)

from scripts.python.extract import *
from scripts.python.extract import main

if __name__ == "__main__":
    import sys

    sys.exit(main())
