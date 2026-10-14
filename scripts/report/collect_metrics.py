"""Collect repo-derived metrics into reports/data/*.csv for the LaTeX report.

Usage:
    uv run python scripts/report/collect_metrics.py [--root PATH] [--out-dir PATH]

Every number comes from the repo tree (file counts, YAML fields, log
timestamps). The script never contacts live databases and never invents
data: unknown values are written as empty cells, and a missing required
input is a non-zero exit (never a fabricated row).

CSVs written (header row, LF endings, raw integers, UTF-8):
    components_by_layer.csv  layer,dbt_models,sql_tests,gx_validations,contracts
    loc_by_area.csv          area,files,lines
    tests_pyramid.csv        kind,count
    pipeline_stages.csv      stage,name,tool,duration_s
    extract_rows.csv         table,rows
    layer_rowcounts.csv      table,bronze,silver,gold
    ci_jobs.csv              job,needs
    dashboard_pages.csv      page,charts,source_tables
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent
LAYERS = ("bronze", "silver", "gold")
LOC_AREAS = ("src", "scripts", "dashboard", "airflow", "dbt", "gx", "tests", "sql")
LOC_EXTS = {".py", ".sql", ".yml", ".yaml", ".sh", ".ps1"}
# Dependency and generated trees are not project code.
LOC_SKIP_DIRS = {
    "dbt_packages",
    "target",
    "logs",
    "__pycache__",
    ".venv",
    "node_modules",
    "build",
}

# Canonical 8 stages: number, display name, tool tag shown in the report.
STAGES: tuple[tuple[int, str, str], ...] = (
    (0, "Preflight", "pyspark"),
    (1, "Extract", "extract.py"),
    (2, "Bronze SQL tests", "SQL"),
    (3, "dbt silver", "dbt"),
    (4, "Silver SQL tests", "SQL"),
    (5, "dbt gold", "dbt"),
    (6, "Gold SQL tests", "SQL"),
    (7, "Great Expectations", "GX"),
)

# Bronze/silver tables with no cross-layer counterpart stay blank.
GOLD_TO_SILVER = {"fact_order_items": "order_items"}
SKIP_CONTRACT_TABLES = {"etl_logs", "etl_watermarks"}

# Heuristic for "charts used" in a dashboard page: calls whose name looks
# like a figure builder (shared lib/charts.py names or Streamlit chart
# methods). Documented approximation, deterministic on the same tree.
CHART_CALL = re.compile(
    r"\b\w*(chart|heatmap|treemap|pareto|bubble|waterfall|sunburst|funnel|map|scatter)\w*\(",
    re.IGNORECASE,
)
GOLD_TABLE = re.compile(r"\b((?:dim|fact)_\w+)\b")
GX_VALIDATION = re.compile(r"^def (\w+)_validation\(", re.MULTILINE)
LOG_STEP = re.compile(r"^(\S+ \S+) \| \w+ +\| pipeline \| STEP (\d+) / \d+")
LOG_PASS = re.compile(r"^(\S+ \S+) \| \w+ +\| pipeline \| PASS - ")


class MissingInputError(RuntimeError):
    """A required repo input for the collector is absent."""


def _require(path: Path, what: str) -> Path:
    if not path.exists():
        raise MissingInputError(f"missing required input {what}: {path}")
    return path


def _count_files(path: Path, pattern: str) -> int:
    return sum(1 for _ in path.glob(pattern))


def components_by_layer(root: Path) -> list[dict[str, object]]:
    rows = []
    for layer in LAYERS:
        models = _count_files(root / "dbt" / "models" / layer, "*.sql")
        sql_tests = _count_files(root / "tests" / "data-quality" / layer, "*.sql")
        suites_file = _require(
            root / "gx" / "suites" / f"{layer}_suites.py", f"GX {layer} suites"
        )
        validations = len(
            GX_VALIDATION.findall(suites_file.read_text(encoding="utf-8"))
        )
        contracts = _count_files(root / "contracts" / layer, "*.yml")
        rows.append(
            {
                "layer": layer,
                "dbt_models": models,
                "sql_tests": sql_tests,
                "gx_validations": validations,
                "contracts": contracts,
            }
        )
    return rows


def loc_by_area(root: Path) -> list[dict[str, object]]:
    rows = []
    for area in LOC_AREAS:
        area_dir = _require(root / area, f"source area {area}")
        files = [
            p
            for p in area_dir.rglob("*")
            if p.is_file()
            and p.suffix in LOC_EXTS
            and not any(part in LOC_SKIP_DIRS for part in p.parts)
        ]
        lines = 0
        for path in files:
            try:
                with open(path, encoding="utf-8", errors="ignore") as handle:
                    lines += sum(1 for _ in handle)
            except OSError:
                continue
        rows.append({"area": area, "files": len(files), "lines": lines})
    return sorted(rows, key=lambda r: int(r["lines"]), reverse=True)


def _count_dbt_tests(root: Path) -> int:
    total = 0

    def walk(node: object) -> None:
        nonlocal total
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "tests" and isinstance(value, list):
                    total += len(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for schema in root.glob("dbt/models/*/schema.yml"):
        walk(yaml.safe_load(schema.read_text(encoding="utf-8")))
    return total


def _count_py_tests(path: Path, pattern: str) -> int:
    count = 0
    for test_file in path.glob(pattern):
        text = test_file.read_text(encoding="utf-8")
        count += len(re.findall(r"^def test_", text, re.MULTILINE))
    return count


def tests_pyramid(root: Path) -> list[dict[str, object]]:
    unit_dir = _require(root / "tests" / "unit", "unit tests")
    smoke_dir = _require(root / "tests" / "smoke", "smoke tests")
    sql_total = sum(
        _count_files(root / "tests" / "data-quality" / layer, "*.sql")
        for layer in LAYERS
    )
    gx_total = sum(
        row["gx_validations"]  # type: ignore[typeddict-item]
        for row in components_by_layer(root)
    )
    return [
        {"kind": "unit", "count": _count_py_tests(unit_dir, "test_*.py")},
        {"kind": "smoke", "count": _count_py_tests(smoke_dir, "test_*.py")},
        {"kind": "sql_data_quality", "count": sql_total},
        {"kind": "dbt", "count": _count_dbt_tests(root)},
        {"kind": "gx", "count": gx_total},
    ]


def pipeline_stages(root: Path) -> list[dict[str, object]]:
    # Durations pair each STEP banner with its next PASS line by order.
    # Old logs predate the current 8-stage order, so unmatched stages
    # honestly stay blank instead of being guessed.
    durations: dict[int, int] = {}
    logs = sorted((root / "logs").glob("pipeline_*.log"))
    if logs:
        pending: list[tuple[int, datetime]] = []
        for line in logs[-1].read_text(encoding="utf-8", errors="ignore").splitlines():
            step = LOG_STEP.match(line)
            if step:
                number = int(step.group(2))
                if number == 0:
                    pending.clear()  # new run starts; drop unmatched steps
                try:
                    # Log stamps are naive local times; deltas are tz-safe.
                    at = datetime.strptime(step.group(1), "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
                except ValueError:
                    continue
                pending.append((number, at))
                continue
            if LOG_PASS.match(line) and pending:
                number, at = pending.pop(0)
                try:
                    done = datetime.strptime(line.split(" | ")[0], "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
                except ValueError:
                    continue
                durations[number] = max(0, int((done - at).total_seconds()))
    rows = []
    for number, name, tool in STAGES:
        rows.append(
            {
                "stage": number,
                "name": name,
                "tool": tool,
                "duration_s": durations.get(number, ""),
            }
        )
    return rows


def _contract_row_counts(root: Path, layer: str) -> dict[str, str]:
    contracts_dir = _require(root / "contracts" / layer, f"{layer} contracts")
    counts = {}
    for contract_file in sorted(contracts_dir.glob("*.yml")):
        data = yaml.safe_load(contract_file.read_text(encoding="utf-8")) or {}
        dataset = data.get("dataset", {}) if isinstance(data, dict) else {}
        table = str(dataset.get("table", contract_file.stem))
        row_count = dataset.get("row_count", "")
        counts[table] = "" if row_count is None else str(row_count)
    return counts


def extract_rows(root: Path) -> list[dict[str, object]]:
    counts = _contract_row_counts(root, "bronze")
    return [
        {"table": table, "rows": rows}
        for table, rows in counts.items()
        if table not in SKIP_CONTRACT_TABLES
    ]


def layer_rowcounts(root: Path) -> list[dict[str, object]]:
    bronze = _contract_row_counts(root, "bronze")
    silver = _contract_row_counts(root, "silver")
    gold = _contract_row_counts(root, "gold")
    tables = sorted(
        (
            set(bronze)
            | set(silver)
            | {GOLD_TO_SILVER.get(t, t.removeprefix("dim_")) for t in gold}
        )
        - SKIP_CONTRACT_TABLES
    )
    rows = []
    for table in tables:
        gold_key = f"dim_{table}" if f"dim_{table}" in gold else None
        if gold_key is None:
            for gtable in gold:
                if GOLD_TO_SILVER.get(gtable) == table:
                    gold_key = gtable
        rows.append(
            {
                "table": table,
                "bronze": bronze.get(table, ""),
                "silver": silver.get(table, ""),
                "gold": gold.get(gold_key, "") if gold_key else "",
            }
        )
    return rows


def ci_jobs(root: Path) -> list[dict[str, object]]:
    workflow = _require(root / ".github" / "workflows" / "ci.yml", "CI workflow")
    data = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
    jobs = data.get("jobs", {}) if isinstance(data, dict) else {}
    rows = []
    for name, job in jobs.items():
        needs = job.get("needs", []) if isinstance(job, dict) else []
        if isinstance(needs, str):
            needs = [needs]
        rows.append({"job": name, "needs": ",".join(sorted(needs))})
    return rows


def dashboard_pages(root: Path) -> list[dict[str, object]]:
    pages_dir = _require(root / "dashboard" / "pages", "dashboard pages")
    # Pages query through the shared BASE_FROM join graph in
    # helpers/queries.py, so a page that imports the query layer reads the
    # graph's tables even when it names none itself. Own-file references
    # (e.g. control tables on the health page) are always added.
    helpers = root / "dashboard" / "helpers" / "queries.py"
    # Allowlist from gold contracts so lookalikes (fact_rows, dim_id
    # variables) never pass as tables.
    known = set(_contract_row_counts(root, "gold"))
    shared = (
        set(GOLD_TABLE.findall(helpers.read_text(encoding="utf-8")))
        if helpers.is_file()
        else set()
    )
    shared &= known
    uses_layer = re.compile(r"from dashboard\.(lib|helpers)")
    rows = []
    for page in sorted(pages_dir.glob("*.py")):
        text = page.read_text(encoding="utf-8")
        tables = set(GOLD_TABLE.findall(text)) & known
        if uses_layer.search(text):
            tables |= shared
        rows.append(
            {
                "page": page.stem,
                "charts": len(CHART_CALL.findall(text)),
                # Semicolon join: pgfplotstable splits quoted comma lists
                # into phantom columns, while LaTeX still breaks lines here.
                "source_tables": "; ".join(sorted(tables)),
            }
        )
    return rows


COLLECTORS = (
    ("components_by_layer.csv", components_by_layer),
    ("loc_by_area.csv", loc_by_area),
    ("tests_pyramid.csv", tests_pyramid),
    ("pipeline_stages.csv", pipeline_stages),
    ("extract_rows.csv", extract_rows),
    ("layer_rowcounts.csv", layer_rowcounts),
    ("ci_jobs.csv", ci_jobs),
    ("dashboard_pages.csv", dashboard_pages),
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise MissingInputError(f"no rows collected for {path.name}")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect report metrics to CSV.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    out_dir = args.out_dir or (args.root / "reports" / "data")
    try:
        collected = [(name, fn(args.root)) for name, fn in COLLECTORS]
    except MissingInputError as exc:
        print(f"collect_metrics: {exc}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in collected:
        write_csv(out_dir / name, rows)
        print(f"wrote {out_dir / name} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
