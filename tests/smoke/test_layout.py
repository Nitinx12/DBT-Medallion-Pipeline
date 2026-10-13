"""Smoke: required repo layout (files the runners assume) exists."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "src/jobs/extract.py",
    "src/jobs/sql_test.py",
    "src/jobs/ci_seed_bronze.py",
    "src/jobs/run_dbt_models.py",
    "src/utils/engine.py",
    "src/utils/connection.py",
    "src/utils/logger.py",
    "gx/run.py",
    "gx/context.py",
    "gx/great_expectations.yml",
    "dbt/dbt_project.yml",
    "dbt/profiles.yml",
    "docker/compose.yml",
    "docker/Dockerfile.pipeline",
    "docker/Dockerfile.airflow",
    "docker/entrypoint.sh",
    "airflow/dags/walmart_pipeline_dag.py",
    "airflow/dags/walmart_health_dag.py",
    "pipeline/run_pipeline.ps1",
    "main.py",
    ".env.example",
]

REQUIRED_DIRS = [
    "tests/data-quality/bronze",
    "tests/data-quality/silver",
    "tests/data-quality/gold",
    "tests/fixtures",
    "dashboard/pages",
    "dashboard/lib",
]


@pytest.mark.parametrize("rel", REQUIRED_FILES)
def test_required_file_exists(rel):
    assert (ROOT / rel).is_file(), f"missing: {rel}"


@pytest.mark.parametrize("rel", REQUIRED_DIRS)
def test_required_dir_exists(rel):
    assert (ROOT / rel).is_dir(), f"missing dir: {rel}"


def test_env_example_has_required_keys():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DATABASE",
        "POSTGRES_USERNAME",
        "POSTGRES_PASSWORD",
        "MONGO_URI",
        "MONGO_DB",
    ]:
        assert key in text, f".env.example missing {key}"


def test_data_quality_suites_not_empty():
    for layer in ["bronze", "silver", "gold"]:
        sql_files = list((ROOT / "tests" / "data-quality" / layer).glob("*.sql"))
        assert sql_files, f"no .sql files in tests/data-quality/{layer}"
