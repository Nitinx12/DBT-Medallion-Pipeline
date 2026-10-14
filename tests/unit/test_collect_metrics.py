"""Unit tests for reports/scripts/collect_metrics.py (fixture tree, no live DB)."""

from __future__ import annotations

import csv
from pathlib import Path

from reports.scripts.collect_metrics import main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _write(root / "dbt/models/silver/a.sql", "select 1")
    _write(root / "dbt/models/silver/b.sql", "select 2")
    _write(root / "dbt/models/gold/g.sql", "select 3")
    _write(
        root / "dbt/models/silver/schema.yml",
        "models:\n  - name: a\n    columns:\n      - name: id\n        tests: [not_null, unique]\n",
    )
    for layer, count in (("bronze", 1), ("silver", 2), ("gold", 1)):
        for i in range(count):
            _write(root / f"tests/data-quality/{layer}/0{i}_check.sql", "select 1")
    for layer, names in (
        ("bronze", ["orders", "stores"]),
        ("silver", ["orders", "brands"]),
        ("gold", ["dim_orders", "fact_order_items"]),
    ):
        body = "".join(f"def {n}_validation():\n    pass\n" for n in names)
        _write(root / f"gx/suites/{layer}_suites.py", body)
    for layer, tables in (
        ("bronze", {"orders": "10", "stores": "5"}),
        ("silver", {"orders": "10", "brands": "2"}),
        ("gold", {"dim_orders": "10", "fact_order_items": "7"}),
    ):
        for table, rows in tables.items():
            _write(
                root / f"contracts/{layer}/{table}.yml",
                f"dataset:\n  table: {table}\n  row_count: {rows}\n",
            )
    _write(
        root / ".github/workflows/ci.yml",
        "jobs:\n  lint: {}\n  unit:\n    needs: [lint]\n",
    )
    _write(
        root / "dashboard/pages/1_Sales.py",
        "revenue_trend_chart(df)\ndonut_chart(df)\n"
        "q = 'FROM fact_order_items JOIN dim_orders'\n",
    )
    for area in (
        "src",
        "scripts",
        "dashboard",
        "airflow",
        "dbt",
        "gx",
        "tests",
        "sql",
        "reports",
    ):
        _write(root / area / "mod.py", "x = 1\ny = 2\n")
    _write(
        root / "tests/unit/test_x.py",
        "def test_a():\n    pass\ndef test_b():\n    pass\n",
    )
    _write(root / "tests/smoke/test_y.py", "def test_c():\n    pass\n")
    _write(
        root / "logs/pipeline_2026-10-14.log",
        "2026-10-14 10:00:00 | INFO     | pipeline | STEP 0 / 7  -  PREFLIGHT\n"
        "2026-10-14 10:00:05 | INFO     | pipeline | PASS - ok\n",
    )
    return root


def _read_csv(out: Path, name: str) -> list[dict[str, str]]:
    with open(out / name, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_collect_metrics_writes_all_csvs(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    out = tmp_path / "out"
    assert main(["--root", str(root), "--out-dir", str(out)]) == 0

    components = _read_csv(out, "components_by_layer.csv")
    assert [r["layer"] for r in components] == ["bronze", "silver", "gold"]
    silver = components[1]
    assert silver["dbt_models"] == "2"
    assert silver["sql_tests"] == "2"
    assert silver["gx_validations"] == "2"
    assert silver["contracts"] == "2"
    assert components[0]["dbt_models"] == "0"

    pyramid = {r["kind"]: r["count"] for r in _read_csv(out, "tests_pyramid.csv")}
    assert pyramid["unit"] == "2"
    assert pyramid["smoke"] == "1"
    assert pyramid["sql_data_quality"] == "4"
    assert pyramid["dbt"] == "2"
    assert pyramid["gx"] == "6"

    stages = _read_csv(out, "pipeline_stages.csv")
    assert len(stages) == 8
    assert stages[0]["duration_s"] == "5"
    assert stages[1]["duration_s"] == ""

    rows = {r["table"]: r["rows"] for r in _read_csv(out, "extract_rows.csv")}
    assert rows == {"orders": "10", "stores": "5"}

    layer_rows = {r["table"]: r for r in _read_csv(out, "layer_rowcounts.csv")}
    assert layer_rows["orders"]["gold"] == "10"
    assert layer_rows["order_items"]["gold"] == "7"
    assert layer_rows["brands"]["bronze"] == ""

    jobs = {r["job"]: r["needs"] for r in _read_csv(out, "ci_jobs.csv")}
    assert jobs == {"lint": "", "unit": "lint"}

    pages = _read_csv(out, "dashboard_pages.csv")
    assert len(pages) == 1
    assert int(pages[0]["charts"]) >= 2
    assert "fact_order_items" in pages[0]["source_tables"]

    loc = {r["area"]: r for r in _read_csv(out, "loc_by_area.csv")}
    assert set(loc) == {
        "src",
        "scripts",
        "dashboard",
        "airflow",
        "dbt",
        "gx",
        "tests",
        "sql",
        "reports",
    }


def test_collect_metrics_missing_input_fails(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    assert main(["--root", str(root), "--out-dir", str(tmp_path / "out")]) == 1
