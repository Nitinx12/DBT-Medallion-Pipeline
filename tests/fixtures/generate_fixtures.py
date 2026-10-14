"""Deterministic fixture generator for the CI bronze seed.

Writes tests/fixtures/bronze/*.json with multi-row, gate-passing data:
unique keys, resolving FKs, exact line/total arithmetic, allowed domains,
valid emails, in-range dates, no nulls (except phone_extension) and no
stray spaces. Same seed always yields the same files.

Usage:
    uv run python tests/fixtures/generate_fixtures.py [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "bronze"

FIRST = [
    "Ada",
    "Grace",
    "Alan",
    "Katherine",
    "Linus",
    "Margaret",
    "Dennis",
    "Barbara",
    "Ken",
    "Dorothy",
    "John",
    "Marie",
    "Claude",
    "Frances",
    "Edsger",
    "Anita",
    "Tim",
    "Radia",
    "Vint",
    "Lynn",
    "Bob",
    "Carol",
    "Dave",
    "Erin",
    "Frank",
]
LAST = [
    "Lovelace",
    "Hopper",
    "Turing",
    "Johnson",
    "Torvalds",
    "Hamilton",
    "Ritchie",
    "Liskov",
    "Thompson",
    "Vaughan",
    "Backus",
    "Curie",
    "Shannon",
    "Allen",
    "Dijkstra",
    "Borg",
    "Berners-Lee",
    "Perlman",
    "Cerf",
    "Conway",
    "Martin",
    "Shaw",
    "Clark",
    "Wong",
    "Patel",
]
BRANDS = ["Acme", "Northwind", "Contoso", "Fabrikam"]
CATEGORIES = ["Office", "Electronics", "Home", "Grocery"]
PRODUCT_NOUNS = [
    "Notebook",
    "Pen",
    "Lamp",
    "Mug",
    "Keyboard",
    "Chair",
    "Cable",
    "Desk",
    "Monitor",
    "Shelf",
    "Router",
    "Kettle",
    "Mouse",
    "Paper",
    "Clock",
    "Bin",
    "Speaker",
    "Tablet",
    "Mixer",
    "Frame",
]
PAYMENTS = ["Credit Card", "Debit Card", "Cash", "Gift Card", "Online"]
STATUSES = ["Completed", "Completed", "Completed", "Pending", "Returned", "Cancelled"]
COUNTRIES = ["United States", "Canada"]
CITIES = [
    ("Toronto", "ON"),
    ("Austin", "TX"),
    ("Chicago", "IL"),
    ("Vancouver", "BC"),
    ("Seattle", "WA"),
]
PRICES = [4.99, 9.99, 12.5, 19.95, 24.0, 39.99, 49.5, 79.0, 99.99, 149.0]


def ts(rng: random.Random) -> tuple[str, str]:
    """Return (created, updated) timestamp strings with updated >= created."""
    base = rng.randint(0, 335)
    day = 1 + (base % 28)
    month = 1 + ((base // 28) % 12)
    created = f"2025-{month:02d}-{day:02d} {rng.randint(8, 18):02d}:00:00"
    updated = f"2025-{month:02d}-{day:02d} {rng.randint(8, 18):02d}:00:00"
    return (created, updated) if updated >= created else (updated, created)


def build(rng: random.Random) -> dict[str, list[dict]]:
    """Build every collection; order matters for FK references."""
    stores = []
    for i in range(1, 5):
        city, prov = CITIES[(i - 1) % len(CITIES)]
        created, updated = ts(rng)
        stores.append(
            {
                "_id": f"store-{i}",
                "store_id": i,
                "store_name": f"{city} Store {i}",
                "city": city,
                "province": prov,
                "country": COUNTRIES[i % 2],
                "is_active": "Y" if i < 4 else "N",
                "created_timestamp": created,
                "updated_timestamp": updated,
            }
        )
    employees = []
    for i in range(1, 9):
        created, updated = ts(rng)
        employees.append(
            {
                "_id": f"employee-{i}",
                "employee_id": i,
                "store_id": ((i - 1) % 4) + 1,
                "first_name": FIRST[i - 1],
                "last_name": LAST[i - 1],
                "email": f"{FIRST[i - 1].lower()}.{LAST[i - 1].lower()}@example.com",
                "job_title": "Manager" if i % 4 == 1 else "Associate",
                "is_active": "Y",
                "salary": 45000 + i * 2500,
                "created_timestamp": created,
                "updated_timestamp": updated,
            }
        )
    customers = []
    for i in range(1, 26):
        city, prov = CITIES[i % len(CITIES)]
        created, updated = ts(rng)
        customers.append(
            {
                "_id": f"customer-{i}",
                "customer_id": i,
                "first_name": FIRST[(i - 1) % len(FIRST)],
                "last_name": LAST[(i * 3) % len(LAST)],
                "phone": f"555-555-{i:04d}",
                "phone_extension": f"{100 + i}" if i % 5 == 0 else None,
                "email": f"customer{i}@example.com",
                "is_active": "N" if i % 9 == 0 else "Y",
                "city": city,
                "province": prov,
                "country": COUNTRIES[i % 2],
                "created_timestamp": created,
                "updated_timestamp": updated,
            }
        )
    products = []
    for i in range(1, 21):
        created, updated = ts(rng)
        products.append(
            {
                "_id": f"product-{i}",
                "product_id": i,
                "product_name": f"{PRODUCT_NOUNS[i - 1]} {i}",
                "brand": BRANDS[(i - 1) % len(BRANDS)],
                "category": CATEGORIES[(i - 1) % len(CATEGORIES)],
                "is_active": "Y",
                "price": PRICES[(i - 1) % len(PRICES)],
                "created_timestamp": created,
                "updated_timestamp": updated,
            }
        )
    orders: list[dict] = []
    items: list[dict] = []
    item_id = 0
    for i in range(1, 31):
        created, updated = ts(rng)
        lines = []
        for _ in range(rng.randint(1, 3)):
            item_id += 1
            product = products[(item_id - 1) % len(products)]
            qty = rng.randint(1, 4)
            line = round(qty * product["price"], 2)
            lines.append((item_id, product["product_id"], qty, product["price"], line))
        total = round(sum(line for _, _, _, _, line in lines), 2)
        orders.append(
            {
                "_id": f"order-{i}",
                "order_id": i,
                "store_id": ((i - 1) % 4) + 1,
                "customer_id": ((i - 1) % 25) + 1,
                "order_status": STATUSES[(i - 1) % len(STATUSES)],
                "is_active": "Y",
                "payment_method": PAYMENTS[(i - 1) % len(PAYMENTS)],
                "total_amount": total,
                "order_timestamp": created,
                "created_timestamp": created,
                "updated_timestamp": updated,
            }
        )
        for lid, pid, qty, price, line in lines:
            items.append(
                {
                    "_id": f"order-item-{lid}",
                    "order_item_id": lid,
                    "order_id": i,
                    "product_id": pid,
                    "is_active": "Y",
                    "quantity": qty,
                    "unit_price": price,
                    "line_amount": line,
                    "created_timestamp": created,
                    "updated_timestamp": updated,
                }
            )
    return {
        "stores": stores,
        "employees": employees,
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": items,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regenerate bronze fixtures.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    collections = build(random.Random(args.seed))
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in collections.items():
        path = FIXTURE_DIR / f"{name}.json"
        path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
