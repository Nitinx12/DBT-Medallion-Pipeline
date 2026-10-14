"""Invariant tests for the deterministic bronze fixture generator (no live DB)."""

from __future__ import annotations

import importlib.util
import random
import re
from pathlib import Path

GENERATOR = Path(__file__).resolve().parent.parent / "fixtures" / "generate_fixtures.py"


def _load():
    spec = importlib.util.spec_from_file_location("generate_fixtures", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixtures_are_deterministic_and_gate_shaped() -> None:
    gen = _load()
    first = gen.build(random.Random(42))
    second = gen.build(random.Random(42))
    assert first == second
    assert {c: len(rows) for c, rows in first.items()} == {
        "stores": 4,
        "employees": 8,
        "customers": 25,
        "products": 20,
        "orders": 30,
        "order_items": len(first["order_items"]),
    }
    assert len(first["order_items"]) >= 30  # every order has a line

    ids = {
        name: [
            row[f"{name.rstrip('s')}_id"]
            if name != "order_items"
            else row["order_item_id"]
            for row in rows
        ]
        for name, rows in first.items()
    }
    for name, values in ids.items():
        assert len(set(values)) == len(values), f"duplicate keys in {name}"
        assert all(v is not None for v in values)

    stores = set(ids["stores"])
    assert {r["store_id"] for r in first["employees"]} <= stores
    assert {r["store_id"] for r in first["orders"]} <= stores
    assert {r["customer_id"] for r in first["orders"]} <= set(ids["customers"])
    assert {r["order_id"] for r in first["order_items"]} <= set(ids["orders"])
    assert {r["product_id"] for r in first["order_items"]} <= set(ids["products"])

    for row in first["order_items"]:
        assert row["line_amount"] == round(row["quantity"] * row["unit_price"], 2)
        assert row["quantity"] > 0 and row["unit_price"] > 0
    totals = {}
    for row in first["order_items"]:
        totals.setdefault(row["order_id"], 0.0)
        totals[row["order_id"]] = round(totals[row["order_id"]] + row["line_amount"], 2)
    for row in first["orders"]:
        assert row["total_amount"] > 0
        assert row["total_amount"] == totals[row["order_id"]]
    assert all(r["price"] > 0 for r in first["products"])

    assert {r["country"] for r in first["customers"]} <= {"United States", "Canada"}
    assert {r["order_status"] for r in first["orders"]} <= {
        "Completed",
        "Pending",
        "Returned",
        "Cancelled",
    }
    methods = {r["payment_method"].upper() for r in first["orders"]}
    assert methods <= {"GIFT CARD", "CASH", "ONLINE", "CREDIT CARD", "DEBIT CARD"}
    assert {r["is_active"] for rows in first.values() for r in rows} <= {"Y", "N"}

    email = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    stamp = re.compile(
        r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])"
        r" ([01]\d|2[0-3]):[0-5]\d:[0-5]\d$"
    )
    bad_spaces = re.compile(r"(^ )|( $)|(  )")
    for name, rows in first.items():
        for row in rows:
            for key, value in row.items():
                if key == "phone_extension":
                    continue
                assert value is not None, f"{name}.{key} is null"
                if isinstance(value, str):
                    assert not bad_spaces.search(value), f"{name}.{key}={value!r}"
                    if "timestamp" in key:
                        # Strict shape: catches month=18 style impossibilities
                        # that lexicographic range checks miss.
                        assert stamp.match(value), f"{name}.{key}={value!r}"
                        assert "2000-01-01" <= value <= "2027-12-31"
            if "email" in row:
                assert email.match(row["email"]), row["email"]
