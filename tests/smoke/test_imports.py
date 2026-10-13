"""Smoke: every pipeline module imports without error."""

import importlib

import pytest

MODULES = [
    "src.utils.engine",
    "src.utils.connection",
    "src.utils.logger",
    "src.jobs.sql_test",
    "src.jobs.run_dbt_models",
    "src.jobs.ci_seed_bronze",
    "gx.context",
    "gx.run",
    "gx.suites.bronze_suites",
    "gx.suites.silver_suites",
    "gx.suites.gold_suites",
    "dashboard.lib.db",
    "dashboard.lib.filters",
    "dashboard.lib.charts",
    "dashboard.lib.queries",
    "dashboard.helpers.components",
    "dashboard.helpers.theme",
    "dashboard.helpers.queries",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)


def test_extract_imports():
    """extract.py needs pyspark; skip cleanly where it is absent."""
    pytest.importorskip("pyspark", reason="pyspark required for extract import")
    importlib.import_module("src.jobs.extract")
