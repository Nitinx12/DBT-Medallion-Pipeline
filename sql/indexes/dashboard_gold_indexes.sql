-- ============================================================================
-- Script:       dashboard_gold_indexes.sql
-- Purpose:      B-tree indexes for the Streamlit dashboard's hot paths:
--               every dashboard query filters dim_orders.order_timestamp
--               and joins fact_order_items to its dimensions, so these
--               five columns carry the whole interactive workload.
--
-- Run with psql or any SQL client as a privileged user:
--   psql -U postgres -d walmart_db -f sql/indexes/dashboard_gold_indexes.sql
--
-- All statements are IF NOT EXISTS, so re-running is always safe.
-- CONCURRENTLY avoids locking writes during the build, which also means
-- this file must NOT run inside a transaction block.
-- ============================================================================

-- Every dashboard WHERE clause: o.order_timestamp >= :start AND < :end.
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_dim_orders_order_timestamp
ON gold.dim_orders (order_timestamp);

-- Fact to dimension joins in the shared BASE_FROM graph.
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_fact_order_items_order_id
ON gold.fact_order_items (order_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_fact_order_items_product_id
ON gold.fact_order_items (product_id);

-- Dimension side of the store/customer joins (map, RFM, funnel).
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_dim_orders_store_id
ON gold.dim_orders (store_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_dim_orders_customer_id
ON gold.dim_orders (customer_id);
