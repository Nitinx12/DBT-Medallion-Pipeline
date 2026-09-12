"""Backward compat shim — use scripts/python/sync_gold_to_databricks.py."""

import warnings

warnings.warn(
    "scripts/sync_gold_to_databricks.py is deprecated, use scripts/python/sync_gold_to_databricks.py",
    DeprecationWarning,
    stacklevel=2,
)
from scripts.python.sync_gold_to_databricks import *
