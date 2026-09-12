"""Backward compat shim — use scripts/python/inspect_gold_schema.py."""

import warnings

warnings.warn(
    "scripts/inspect_gold_schema.py is deprecated, use scripts/python/inspect_gold_schema.py",
    DeprecationWarning,
    stacklevel=2,
)
from scripts.python.inspect_gold_schema import *
