"""
scripts/run_update_contract.py
==============================
Sync per-table data contracts in contracts/<layer>/*.yml against the live
Postgres warehouse and stamp them with real observed state -- no guesses.

WHAT IT DOES
------------
Two-way dynamic sync (DB is the source of truth for names/counts/types):
1. Schemas come from .env via src/utils/engine.py (POSTGRES_SCHEMA_BRONZE /
   _SILVER / _GOLD), never hardcoded. A contract's dataset.schema wins when
   set, otherwise the layer's env schema is used.
2. Discovers live tables per schema from information_schema, so a brand-new
   table (e.g. bronze.etl_logs) gets a fresh bronze/etl_logs.yml on the next
   run -- no code change needed.
3. For every contract file: reads live existence, row count, native column
   types/nullability, plus per-column null/distinct stats in ONE aggregate
   query per table (--no-column-stats skips stats for speed).
4. Writes observations back into the same YAML without touching human-owned
   fields (description, transformation, tests): only dataset.row_count /
   column_count_observed / last_observed_at and per-column observed_* /
   null_count / null_fraction / distinct_count / sync_status. DB columns the
   contract doesn't know are appended with in_contract: false for review.
5. --fix-types overwrites the contract's declared data_type/nullable with
   the observed DB values (use after verifying the DB is right; clears
   type_mismatch drift). Without it, mismatches are only reported.
6. Prints a Rich report + drift list. --check-only writes nothing and exits
   1 on drift (CI gate). --no-create disables auto-creation of missing files.

USAGE
-----
    uv run python scripts/run_update_contract.py
    uv run python scripts/run_update_contract.py --layer silver
    uv run python scripts/run_update_contract.py --layer gold --table dim_orders
    uv run python scripts/run_update_contract.py --check-only
    uv run python scripts/run_update_contract.py --fix-types
    uv run python scripts/run_update_contract.py --no-column-stats --no-create
"""

from __future__ import annotations

import argparse
import re
import sys
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import engine as config
from src.utils.connection import get_postgres_engine
from src.utils.logger import get_logger

console = Console()
log = get_logger("sync_contracts")

DEFAULT_CONTRACTS_DIR = PROJECT_ROOT / "contracts"
LAYERS = ("bronze", "silver", "gold")

LAYER_OWNERS = {
    "bronze": "data-engineering",
    "silver": "analytics-engineering",
    "gold": "analytics-engineering",
}
LAYER_DOMAINS = {
    "bronze": "retail-ingestion",
    "silver": "retail-warehouse",
    "gold": "retail-analytics",
}

# Contract identifiers become SQL identifiers -- reject anything else so the
# COUNT(*) queries built with quoted names can't be injection vectors.
_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class ColumnDrift:
    """One mismatch between contract and live database state."""

    column: str
    kind: str  # type_mismatch | missing_in_db | missing_in_contract | not_null_violation | nullable_mismatch
    detail: str


@dataclass
class ContractResult:
    """Outcome of syncing a single contract file."""

    file: Path
    layer: str
    table: str
    schema: str
    exists: bool = False
    row_count: int = 0
    contract_columns: int = 0
    db_columns: int = 0
    drifts: list[ColumnDrift] = field(default_factory=list)
    status: str = "OK"  # OK | DRIFT | CREATED | MISSING TABLE | FAILED | SKIPPED
    error: str | None = None
    wrote: bool = False


def parse_args() -> argparse.Namespace:
    """Parse CLI flags for layer/table selection and run mode."""
    parser = argparse.ArgumentParser(
        description="Sync contracts/<layer>/*.yml against live Postgres (row counts + real types)."
    )
    parser.add_argument(
        "--layer",
        choices=[*LAYERS, "all"],
        default="all",
        help="Which contracts subfolder to sync (default: all).",
    )
    parser.add_argument(
        "--table",
        default=None,
        help="Only sync this table (matches dataset.table or file stem).",
    )
    parser.add_argument(
        "--contracts-dir",
        default=str(DEFAULT_CONTRACTS_DIR),
        help="Contracts root (default: ./contracts).",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Detect drift and report it, but do not write any YAML files.",
    )
    parser.add_argument(
        "--no-column-stats",
        action="store_true",
        help="Skip per-column null/distinct stats (schema + row counts only). Faster.",
    )
    parser.add_argument(
        "--fix-types",
        action="store_true",
        help="Overwrite contract data_type/nullable with observed DB values (clears type drift).",
    )
    parser.add_argument(
        "--no-create",
        action="store_true",
        help="Do not auto-create contract files for DB tables that lack one.",
    )
    return parser.parse_args()


def resolve_layer_schema(layer: str) -> str:
    """Return the Postgres schema for a layer from .env, falling back to the layer name."""
    env_map = {
        "bronze": getattr(config, "POSTGRES_SCHEMA_BRONZE", None),
        "silver": getattr(config, "POSTGRES_SCHEMA_SILVER", None),
        "gold": getattr(config, "POSTGRES_SCHEMA_GOLD", None),
    }
    return env_map.get(layer) or layer


def discover_db_tables(engine: Engine, schema: str) -> list[str]:
    """Return all live base-table names in a schema, alphabetically."""
    assert_safe_ident(schema)
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                ),
                {"schema": schema},
            )
            .scalars()
            .all()
        )
    return [str(r) for r in rows]


def build_new_contract(
    layer: str,
    schema: str,
    table: str,
    db_columns: list[dict],
    row_count: int,
    stats: dict[str, dict],
    observed_at: str,
) -> dict:
    """Build a full contract dict for a DB table that has no contract file yet."""
    columns = []
    for live_col in db_columns:
        col_stats = stats.get(live_col["name"], {})
        columns.append(
            {
                "name": live_col["name"],
                "data_type": normalize_type(live_col["data_type"]),
                "nullable": live_col["nullable"],
                "unique": False,
                "in_contract": True,
                "auto_generated": True,
                "sync_status": "ok",
                "observed_data_type": normalize_type(live_col["data_type"]),
                "observed_nullable": live_col["nullable"],
                "null_count": col_stats.get("null_count", 0),
                "null_fraction": col_stats.get("null_fraction", 0.0),
                "distinct_count": col_stats.get("distinct_count", 0),
                "description": "Auto-created by sync: present in DB, needs human review.",
            }
        )
    return {
        "apiVersion": "1.0.0",
        "kind": "DataContract",
        "metadata": {
            "name": f"{schema}.{table}",
            "layer": layer,
            "version": "1.0.0",
            "status": "active",
            "owner": LAYER_OWNERS.get(layer, "data-engineering"),
            "domain": LAYER_DOMAINS.get(layer, "retail"),
            "description": f"Auto-created from live {schema}.{table}. Review types, keys, grain.",
        },
        "dataset": {
            "server": "postgres-prod",
            "database": config.POSTGRES_DATABASE,
            "schema": schema,
            "table": table,
            "grain": "unknown -- set the business grain after review",
            "upstream": f"{schema} (auto-discovered)",
            "row_count": row_count,
            "column_count_contract": len(columns),
            "column_count_observed": len(columns),
            "table_exists": True,
            "last_observed_at": observed_at,
        },
        "columns": columns,
        "observation": {
            "observed_at": observed_at,
            "database": config.POSTGRES_DATABASE,
            "schema": schema,
            "table": table,
            "row_count": row_count,
            "drifts": [],
        },
        "terms": {
            "breakingChange": "auto-created contract -- confirm grain, keys, and types before relying on it.",
        },
    }


def normalize_type(raw: str | None) -> str:
    """Upper-case a Postgres type for comparison (varchar == CHARACTER VARYING)."""
    if not raw:
        return ""
    t = raw.strip().upper()
    return {
        "CHARACTER VARYING": "VARCHAR",
        "CHARACTER": "CHAR",
        "DOUBLE PRECISION": "FLOAT8",
        "TIMESTAMP WITHOUT TIME ZONE": "TIMESTAMP",
        "TIMESTAMP WITH TIME ZONE": "TIMESTAMPTZ",
    }.get(t, t)


def types_match(contract_type: str | None, observed_type: str | None) -> bool:
    """Compare contract vs live type, treating common aliases as equal."""
    if not contract_type or not observed_type:
        return True  # nothing declared -- nothing to contradict
    aliases = {
        "INT": {
            "INT",
            "INTEGER",
            "INT4",
            "INT8",
            "BIGINT",
            "INT2",
            "SMALLINT",
            "SERIAL",
            "BIGSERIAL",
        },
        "VARCHAR": {"VARCHAR", "TEXT"},
        "NUMERIC": {"NUMERIC", "DECIMAL"},
        "TIMESTAMP": {"TIMESTAMP", "TIMESTAMPTZ"},
        "BOOLEAN": {"BOOLEAN", "BOOL"},
    }
    c, o = normalize_type(contract_type), normalize_type(observed_type)
    if c == o:
        return True
    return any(c in group and o in group for group in aliases.values())


def assert_safe_ident(value: str) -> str:
    """Reject non-identifier schema/table/column names before SQL interpolation."""
    if not _SAFE_IDENT.match(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def get_db_columns(engine: Engine, schema: str, table: str) -> list[dict]:
    """Return live columns (name, type, nullable) in ordinal order."""
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table "
                    "ORDER BY ordinal_position"
                ),
                {"schema": schema, "table": table},
            )
            .mappings()
            .all()
        )
    return [
        {
            "name": r["column_name"],
            "data_type": r["data_type"],
            "nullable": r["is_nullable"] == "YES",
        }
        for r in rows
    ]


def get_row_count(engine: Engine, schema: str, table: str) -> int:
    """Return live row count for a schema-qualified table."""
    assert_safe_ident(schema)
    assert_safe_ident(table)
    with engine.connect() as conn:
        return int(
            conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')).scalar()
            or 0
        )


def get_column_stats(
    engine: Engine, schema: str, table: str, columns: list[str]
) -> dict[str, dict]:
    """Compute null/distinct stats for columns in a single aggregate query.

    Returns {column: {null_count, null_fraction, distinct_count}}. Empty
    dict when the table is empty or has no columns -- callers treat missing
    entries as zeros.
    """
    for name in (schema, table, *columns):
        assert_safe_ident(name)
    if not columns:
        return {}
    with engine.connect() as conn:
        total = (
            conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')).scalar()
            or 0
        )
    if total == 0:
        return {}
    select_parts = []
    for col in columns:
        select_parts.append(f'COUNT(*) FILTER (WHERE "{col}" IS NULL) AS "null__{col}"')
        select_parts.append(f'COUNT(DISTINCT "{col}") AS "distinct__{col}"')
    query = f'SELECT {", ".join(select_parts)} FROM "{schema}"."{table}"'
    with engine.connect() as conn:
        row = conn.execute(text(query)).mappings().first() or {}
    stats: dict[str, dict] = {}
    for col in columns:
        nulls = int(row.get(f"null__{col}") or 0)
        stats[col] = {
            "null_count": nulls,
            "null_fraction": round(nulls / total, 4) if total else 0.0,
            "distinct_count": int(row.get(f"distinct__{col}") or 0),
        }
    return stats


def sync_one_contract(
    engine: Engine,
    path: Path,
    layer: str,
    table_filter: str | None,
    skip_stats: bool,
    check_only: bool,
    fix_types: bool = False,
) -> ContractResult:
    """Sync a single contract YAML against live Postgres; optionally write back."""
    try:
        contract = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return ContractResult(
            file=path,
            layer=layer,
            table="?",
            schema="?",
            status="FAILED",
            error=f"YAML parse error: {exc}",
        )
    dataset = contract.get("dataset", {})
    table = str(dataset.get("table") or path.stem)
    schema = str(dataset.get("schema") or resolve_layer_schema(layer))
    result = ContractResult(file=path, layer=layer, table=table, schema=schema)

    if table_filter and table_filter not in (table, path.stem):
        result.status = "SKIPPED"
        return result

    try:
        assert_safe_ident(schema)
        assert_safe_ident(table)
        db_columns = get_db_columns(engine, schema, table)
    except Exception as exc:  # noqa: BLE001 -- per-file failure must not stop the run
        result.status = "FAILED"
        result.error = str(exc)[:220]
        log.error(f"[{schema}.{table}] introspection failed: {result.error}")
        return result

    result.exists = bool(db_columns)
    result.db_columns = len(db_columns)
    contract_cols: list[dict] = contract.get("columns", []) or []
    result.contract_columns = len(contract_cols)

    if not result.exists:
        result.status = "MISSING TABLE"
        result.drifts.append(
            ColumnDrift(
                column="-",
                kind="missing_table",
                detail=f"{schema}.{table} not found in database",
            )
        )
        return result

    result.row_count = get_row_count(engine, schema, table)
    stats = (
        {}
        if skip_stats
        else get_column_stats(engine, schema, table, [c["name"] for c in db_columns])
    )
    observed_at = datetime.now(UTC).isoformat(timespec="seconds")
    by_name = {c["name"]: c for c in db_columns}

    for entry in contract_cols:
        name = entry.get("name")
        live = by_name.get(name)
        if live is None:
            entry["sync_status"] = "missing_in_db"
            entry.pop("observed_data_type", None)
            result.drifts.append(
                ColumnDrift(
                    column=name,
                    kind="missing_in_db",
                    detail="contract declares it, DB has no such column",
                )
            )
            continue
        entry["observed_data_type"] = normalize_type(live["data_type"])
        entry["observed_nullable"] = live["nullable"]
        entry["in_contract"] = True
        col_stats = stats.get(name, {})
        entry["null_count"] = col_stats.get("null_count", 0)
        entry["null_fraction"] = col_stats.get("null_fraction", 0.0)
        entry["distinct_count"] = col_stats.get("distinct_count", 0)
        if fix_types and not check_only:
            # DB is the source of truth for physical types -- adopt them so
            # the next run is drift-free (human reviews the diff in git).
            entry["data_type"] = normalize_type(live["data_type"])
            entry["nullable"] = live["nullable"]
        if not types_match(entry.get("data_type"), live["data_type"]):
            entry["sync_status"] = "type_mismatch"
            result.drifts.append(
                ColumnDrift(
                    column=name,
                    kind="type_mismatch",
                    detail=f"contract {entry.get('data_type')} vs "
                    f"DB {normalize_type(live['data_type'])}",
                )
            )
        elif entry.get("nullable") is False and entry["null_count"] > 0:
            entry["sync_status"] = "not_null_violation"
            result.drifts.append(
                ColumnDrift(
                    column=name,
                    kind="not_null_violation",
                    detail=f"{entry['null_count']} NULL rows but contract says nullable: false",
                )
            )
        else:
            entry["sync_status"] = "ok"

    contracted_names = {c.get("name") for c in contract_cols}
    for live_col in db_columns:
        if live_col["name"] not in contracted_names:
            col_stats = stats.get(live_col["name"], {})
            contract_cols.append(
                {
                    "name": live_col["name"],
                    "data_type": normalize_type(live_col["data_type"]),
                    "nullable": live_col["nullable"],
                    "unique": False,
                    "in_contract": False,
                    "sync_status": "missing_in_contract",
                    "observed_data_type": normalize_type(live_col["data_type"]),
                    "observed_nullable": live_col["nullable"],
                    "null_count": col_stats.get("null_count", 0),
                    "null_fraction": col_stats.get("null_fraction", 0.0),
                    "distinct_count": col_stats.get("distinct_count", 0),
                    "description": "Auto-added by sync: present in DB, not yet reviewed.",
                }
            )
            result.drifts.append(
                ColumnDrift(
                    column=live_col["name"],
                    kind="missing_in_contract",
                    detail="DB has it, contract does not -- review and document",
                )
            )

    if result.row_count == 0:
        result.drifts.append(
            ColumnDrift(column="-", kind="empty_table", detail="table has 0 rows")
        )

    dataset["row_count"] = result.row_count
    dataset["column_count_contract"] = result.contract_columns
    dataset["column_count_observed"] = result.db_columns
    dataset["table_exists"] = True
    dataset["last_observed_at"] = observed_at
    contract["columns"] = contract_cols
    contract["observation"] = {
        "observed_at": observed_at,
        "database": config.POSTGRES_DATABASE,
        "schema": schema,
        "table": table,
        "row_count": result.row_count,
        "drifts": [f"{d.column}:{d.kind} ({d.detail})" for d in result.drifts],
    }
    result.status = "DRIFT" if result.drifts else "OK"

    if not check_only:
        path.write_text(
            yaml.safe_dump(contract, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        result.wrote = True
    return result


def discover_contracts(contracts_dir: Path, layer: str) -> list[tuple[str, Path]]:
    """List (layer, path) contract files for the requested layer selection."""
    layers = LAYERS if layer == "all" else (layer,)
    found: list[tuple[str, Path]] = []
    for lyr in layers:
        folder = contracts_dir / lyr
        if not folder.is_dir():
            log.warning(f"Contracts folder missing: {folder} -- skipped")
            continue
        found.extend((lyr, p) for p in sorted(folder.glob("*.yml")))
    return found


def render_report(results: list[ContractResult], check_only: bool) -> None:
    """Print a Rich per-table summary plus a drift detail table."""
    console.print()
    console.print(
        Panel.fit(
            "[bold]Contract Sync Report[/bold]\n"
            f"Mode: [cyan]{'CHECK ONLY (no writes)' if check_only else 'SYNC + UPDATE'}[/cyan]\n"
            f"Finished: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            border_style="cyan",
        )
    )
    table = Table(title="Per-Table Detail", box=box.SIMPLE_HEAVY)
    for col in ("Contract", "Rows", "Cols C/DB", "Drifts", "Status", "Wrote"):
        table.add_column(col, justify="right" if col != "Contract" else "left")
    for r in results:
        if r.status == "SKIPPED":
            continue
        style = {"OK": "green", "DRIFT": "yellow", "CREATED": "cyan"}.get(
            r.status, "red"
        )
        table.add_row(
            f"{r.layer}/{r.table}",
            f"{r.row_count:,}",
            f"{r.contract_columns}/{r.db_columns}",
            str(len(r.drifts)),
            f"[{style}]{r.status}[/{style}]",
            "yes" if r.wrote else "-",
        )
    console.print(table)

    drifts = [r for r in results if r.drifts]
    if drifts:
        dtable = Table(title="Drift Detail", box=box.MINIMAL, style="yellow")
        dtable.add_column("Contract")
        dtable.add_column("Column")
        dtable.add_column("Kind")
        dtable.add_column("Detail", overflow="fold", max_width=80)
        for r in drifts:
            for d in r.drifts:
                dtable.add_row(f"{r.layer}/{r.table}", d.column, d.kind, d.detail)
        console.print(dtable)

    failed = [r for r in results if r.status in ("FAILED", "MISSING TABLE")]
    if failed:
        ftable = Table(title="Failures / Missing Tables", box=box.MINIMAL, style="red")
        ftable.add_column("Contract")
        ftable.add_column("Problem", overflow="fold", max_width=90)
        for r in failed:
            problem = r.error or "; ".join(d.detail for d in r.drifts) or r.status
            ftable.add_row(f"{r.layer}/{r.table}", problem)
        console.print(ftable)


def main() -> int:
    """Run the sync across selected contracts; return process exit code."""
    args = parse_args()
    contracts_dir = Path(args.contracts_dir)
    layers = LAYERS if args.layer == "all" else (args.layer,)

    try:
        engine = get_postgres_engine()
    except Exception:  # noqa: BLE001 -- any connection failure must report, not crash
        console.print("[bold red]Could not connect to Postgres (see logs/).[/bold red]")
        console.print(traceback.format_exc(limit=3))
        return 2

    results: list[ContractResult] = []
    for layer in layers:
        schema = resolve_layer_schema(layer)
        folder = contracts_dir / layer
        folder.mkdir(parents=True, exist_ok=True)

        # Live tables are the source of truth for names -- contracts follow.
        try:
            db_tables = discover_db_tables(engine, schema)
        except Exception as exc:  # noqa: BLE001 -- one bad schema must not stop others
            log.error(f"[{schema}] table discovery failed: {exc}")
            continue
        if args.table:
            db_tables = [t for t in db_tables if t == args.table]

        contracted = {p.stem for p in folder.glob("*.yml")}
        targets = sorted(contracted | set(db_tables))
        if args.table:
            targets = [t for t in targets if t == args.table]

        for table in targets:
            path = folder / f"{table}.yml"
            if not path.exists():
                # Brand-new table (e.g. bronze.etl_logs): create its contract
                # from live state instead of guessing.
                if args.no_create or args.check_only:
                    results.append(
                        ContractResult(
                            file=path,
                            layer=layer,
                            table=table,
                            schema=schema,
                            exists=True,
                            status="DRIFT",
                            drifts=[
                                ColumnDrift(
                                    column="-",
                                    kind="missing_contract",
                                    detail=f"{schema}.{table} has no contract file",
                                )
                            ],
                        )
                    )
                    continue
                try:
                    db_columns = get_db_columns(engine, schema, table)
                    row_count = get_row_count(engine, schema, table)
                    col_stats = (
                        {}
                        if args.no_column_stats
                        else get_column_stats(
                            engine, schema, table, [c["name"] for c in db_columns]
                        )
                    )
                    observed_at = datetime.now(UTC).isoformat(timespec="seconds")
                    contract = build_new_contract(
                        layer,
                        schema,
                        table,
                        db_columns,
                        row_count,
                        col_stats,
                        observed_at,
                    )
                    path.write_text(
                        yaml.safe_dump(contract, sort_keys=False, allow_unicode=True),
                        encoding="utf-8",
                    )
                    results.append(
                        ContractResult(
                            file=path,
                            layer=layer,
                            table=table,
                            schema=schema,
                            exists=True,
                            row_count=row_count,
                            contract_columns=len(db_columns),
                            db_columns=len(db_columns),
                            status="CREATED",
                            wrote=True,
                        )
                    )
                    log.info(f"[{layer}/{table}] CREATED contract ({row_count:,} rows)")
                except Exception as exc:  # noqa: BLE001 -- per-table failure never stops run
                    results.append(
                        ContractResult(
                            file=path,
                            layer=layer,
                            table=table,
                            schema=schema,
                            status="FAILED",
                            error=str(exc)[:220],
                        )
                    )
                continue

            res = sync_one_contract(
                engine,
                path,
                layer,
                None,
                skip_stats=args.no_column_stats,
                check_only=args.check_only,
                fix_types=args.fix_types,
            )
            results.append(res)
            log.info(
                f"[{layer}/{res.table}] rows={res.row_count:,} "
                f"drifts={len(res.drifts)} status={res.status}"
            )

    if not results:
        console.print("[yellow]No contract files matched.[/yellow]")
        return 0
    render_report(results, args.check_only)

    if args.check_only and any(
        r.drifts or r.status in ("FAILED", "MISSING TABLE") for r in results
    ):
        return 1
    if any(r.status == "FAILED" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 -- top-level guard prints traceback, exits 2
        console.print("[bold red]Unhandled error:[/bold red]")
        console.print(traceback.format_exc())
        sys.exit(2)
