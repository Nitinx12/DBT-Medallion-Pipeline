"""
scripts/simulate_orders.py
==========================
Demo order simulator: inserts a few synthetic orders into the LOCAL bronze
layer so the dashboard visibly moves without touching MongoDB.

WHAT IT DOES
------------
1. Samples live dimension values from silver (customers, stores, products
   with prices, payment methods) so every FK/join keeps working.
2. Builds N new orders + 1..M lines each, shaped exactly like extract.py's
   raw output (string timestamps, "Y" flags, fresh uuid _ids).
3. Inserts them into <bronze>.orders / <bronze>.order_items. The next
   incremental `dbt run --select silver/gold` carries them through, which
   demonstrates the pipeline end to end.

WHAT IT DOES NOT DO
-------------------
- Never touches MongoDB, watermarks, or etl_logs.
- Never runs dbt itself (run `uv run python src/jobs/run_dbt_models.py`
  afterwards, or wait for the scheduled pipeline).
- A later `--full-refresh` extract TRUNCATES bronze and wipes simulated
  rows. Demo data only, never present it as real business data.

USAGE
-----
    uv run python scripts/simulate_orders.py --orders 10
    uv run python scripts/simulate_orders.py --orders 5 --max-items 2 --seed 42
    uv run python scripts/simulate_orders.py --orders 10 --dry-run
"""

from __future__ import annotations

import argparse
import random
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from sqlalchemy import text

from src.utils import engine as config
from src.utils.connection import get_postgres_engine
from src.utils.logger import get_logger

log = get_logger("simulate_orders")

TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_args() -> argparse.Namespace:
    """Parse simulator flags."""
    parser = argparse.ArgumentParser(
        description="Insert synthetic demo orders into bronze."
    )
    parser.add_argument(
        "--orders", type=int, default=10, help="How many orders to create."
    )
    parser.add_argument("--max-items", type=int, default=4, help="Max lines per order.")
    parser.add_argument(
        "--seed", type=int, default=None, help="RNG seed for repeat runs."
    )
    parser.add_argument("--dry-run", action="store_true", help="Print, do not insert.")
    return parser.parse_args()


def load_pools(engine) -> dict:
    """Load live ID pools + prices from silver; fail clearly when empty."""
    silver = getattr(config, "POSTGRES_SCHEMA_SILVER", None) or "silver"
    with engine.connect() as conn:
        customers = pd.read_sql(
            text(f"SELECT customer_id FROM {silver}.customers"), conn
        )
        stores = pd.read_sql(text(f"SELECT store_id FROM {silver}.stores"), conn)
        products = pd.read_sql(
            text(f"SELECT product_id, price FROM {silver}.products"), conn
        )
        payments = pd.read_sql(
            text(f"SELECT payment_method_name FROM {silver}.payment_methods"), conn
        )
        statuses = pd.read_sql(
            text(f"SELECT DISTINCT order_status FROM {silver}.orders"), conn
        )
        next_order = conn.execute(
            text(f"SELECT COALESCE(MAX(order_id), 0) + 1 FROM {silver}.orders")
        ).scalar()
        next_item = conn.execute(
            text(
                f"SELECT COALESCE(MAX(order_item_id), 0) + 1 FROM {silver}.order_items"
            )
        ).scalar()
    pools = {
        "customers": customers["customer_id"].tolist(),
        "stores": stores["store_id"].tolist(),
        "products": products.to_dict("records"),
        "payments": payments["payment_method_name"].tolist(),
        "statuses": statuses["order_status"].tolist(),
        "next_order": int(next_order),
        "next_item": int(next_item),
    }
    empty = [
        k
        for k in ("customers", "stores", "products", "payments", "statuses")
        if not pools[k]
    ]
    if empty:
        raise RuntimeError(
            f"Silver pools empty ({', '.join(empty)}); build the warehouse first."
        )
    return pools


def build_orders(
    pools: dict, n: int, max_items: int, rng: random.Random
) -> tuple[list, list]:
    """Build (orders, items) row dicts in raw bronze shape."""
    now = datetime.now(UTC).strftime(TS_FORMAT)
    orders, items = [], []
    order_id, item_id = pools["next_order"], pools["next_item"]
    for _ in range(n):
        lines = []
        total = 0.0
        for _ in range(rng.randint(1, max_items)):
            product = rng.choice(pools["products"])
            qty = rng.randint(1, 3)
            price = float(product["price"])
            line = round(qty * price, 2)
            total += line
            lines.append(
                {
                    "_id": uuid.uuid4().hex,
                    "order_item_id": item_id,
                    "order_id": order_id,
                    "product_id": int(product["product_id"]),
                    "is_active": "Y",
                    "quantity": qty,
                    "unit_price": price,
                    "line_amount": line,
                    "created_timestamp": now,
                    "updated_timestamp": now,
                }
            )
            item_id += 1
        orders.append(
            {
                "_id": uuid.uuid4().hex,
                "order_id": order_id,
                "store_id": int(rng.choice(pools["stores"])),
                "customer_id": int(rng.choice(pools["customers"])),
                "order_status": rng.choice(pools["statuses"]),
                "is_active": "Y",
                "payment_method": rng.choice(pools["payments"]),
                "total_amount": round(total, 2),
                "order_timestamp": now,
                "created_timestamp": now,
                "updated_timestamp": now,
            }
        )
        items.extend(lines)
        order_id += 1
    return orders, items


def insert_rows(engine, bronze: str, table: str, rows: list) -> None:
    """Insert row dicts with a parameterized multi-row INSERT."""
    columns = list(rows[0].keys())
    names = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    stmt = text(f'INSERT INTO "{bronze}"."{table}" ({names}) VALUES ({placeholders})')
    with engine.begin() as conn:
        conn.execute(stmt, rows)


def main() -> int:
    """Generate and insert synthetic orders; return process exit code."""
    args = parse_args()
    if args.orders < 1 or args.max_items < 1:
        print("--orders and --max-items must be >= 1")
        return 2
    rng = random.Random(args.seed)
    engine = get_postgres_engine()
    bronze = getattr(config, "POSTGRES_SCHEMA_BRONZE", None) or "bronze"

    print("DEMO ORDER SIMULATOR — synthetic rows for the local warehouse only.")
    pools = load_pools(engine)
    orders, items = build_orders(pools, args.orders, args.max_items, rng)
    total = sum(o["total_amount"] for o in orders)
    print(
        f"Prepared {len(orders)} orders / {len(items)} lines "
        f"(${total:,.2f}) into {bronze}.orders + {bronze}.order_items."
    )
    if args.dry_run:
        print("Dry run: nothing written.")
        return 0
    insert_rows(engine, bronze, "orders", orders)
    insert_rows(engine, bronze, "order_items", items)
    log.info(f"Inserted {len(orders)} demo orders ({len(items)} lines) into {bronze}.")
    print("Next: uv run python src/jobs/run_dbt_models.py --layer all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
