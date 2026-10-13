"""Smoke: DAG files parse and declare the expected structure (AST only)."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DAG = ROOT / "airflow" / "dags" / "walmart_pipeline_dag.py"
HEALTH_DAG = ROOT / "airflow" / "dags" / "walmart_health_dag.py"

EXPECTED_STAGES = [
    "preflight",
    "extract",
    "bronze_sql_tests",
    "dbt_silver_run",
    "dbt_silver_test",
    "silver_sql_tests",
    "dbt_gold_run",
    "dbt_gold_test",
    "gold_sql_tests",
    "great_expectations_tests",
]


def _source(path):
    return path.read_text(encoding="utf-8")


def test_pipeline_dag_parses():
    ast.parse(_source(PIPELINE_DAG))


def test_health_dag_parses():
    ast.parse(_source(HEALTH_DAG))


def test_pipeline_dag_declares_all_stages():
    source = _source(PIPELINE_DAG)
    for stage in EXPECTED_STAGES:
        assert f'task_id="{stage}"' in source, f"stage missing: {stage}"


def test_pipeline_dag_has_both_schedules():
    source = _source(PIPELINE_DAG)
    assert "walmart_mwf_morning" in source
    assert "walmart_rest_night" in source
    assert "1,3,5" in source
    assert "0,2,4,6" in source


def test_health_dag_has_hourly_schedule():
    source = _source(HEALTH_DAG)
    assert "walmart_hourly_health_check" in source
    assert "0 * * * *" in source


def test_dag_commands_reference_existing_paths():
    """Every `uv run python <path>` in DAGs must point at a real file."""
    import re

    for path in [PIPELINE_DAG, HEALTH_DAG]:
        for match in re.finditer(r"uv run python ([a-z_/]+\.py)", _source(path)):
            assert (ROOT / match.group(1)).is_file(), (
                f"{path.name}: missing {match.group(1)}"
            )
