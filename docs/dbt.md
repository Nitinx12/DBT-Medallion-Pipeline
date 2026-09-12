# dbt

Medallion models in `walmart_dbt/`.

## Models

- **Silver (9)**: `brands, categories, customers, employees, order_items, orders, payment_methods, products, stores` — deduped, typed.
- **Gold (8)**: `dim_brands, dim_categories, dim_customers, dim_orders, dim_payment_methods, dim_products, dim_stores, fact_order_items` — snowflake (fact → dims → sub-dims).

## Tests

`models/*/schema.yml` per model (`not_null`, `unique`, `relationships`, `accepted_values`). Custom generics in `tests/generic/` (unused, `dbt_utils` used instead).

```bash
cd walmart_dbt
uv run dbt run --select silver && uv run dbt test --select silver
uv run dbt run --select gold && uv run dbt test --select gold
```

Add `schema.yml` tests for every new model.

See `tests.md`, `architecture.md` §4.
