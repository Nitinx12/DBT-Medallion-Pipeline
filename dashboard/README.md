# Sales Dashboard — Professional

Interactive **Streamlit + Plotly** dashboard reading directly from the `gold` star schema.
Designed as a portfolio-grade, enterprise dashboard: card-based layout, period-over-period KPIs,
tabbed navigation, CSV exports, and a cohesive Walmart-inspired design system.

![Dashboard](https://img.shields.io/badge/Streamlit-1.62-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-7.0-3F4F75?logo=plotly&logoColor=white)

## Run it

```powershell
uv sync
uv run streamlit run dashboard/home.py
# → http://localhost:8501
```

Requires the same `.env` as the rest of the project (`POSTGRES_HOST`, `POSTGRES_PORT`,
`POSTGRES_DATABASE`, `POSTGRES_USERNAME`, `POSTGRES_PASSWORD`, `POSTGRES_SCHEMA_GOLD`) —
it reuses `src/utils/engine.py` + `src/utils/connection.py`, so nothing new to configure.

Deployed demo: Streamlit Community Cloud reads secrets from `st.secrets` (no `.env` needed).

## What changed in the professional pass

- **Design system (`helpers/theme.py`)** — single source of truth for palette, typography (Inter),
  card/KPI/tab/table/button styling, and a unified `style(fig)` for every Plotly figure.
- **Components (`helpers/components.py`)** — reusable `kpi_cards`, `filter_chips`, `dataframe_with_download`,
  `empty_state`, `footer` so pages stay focused on layout/data flow.
- **Header & meta** — `get_gold_meta()` shows live fact-row count + last order timestamp;
  `↻ Refresh` clears `st.cache_data` and reloads from Postgres.
- **Sidebar** — brand lockup, date presets (7D/30D/90D/YTD/All), per-field Clear/All, grouped sections,
  and a collapsible “About this data” drawer.
- **KPIs** — custom HTML cards with accent bars, value, pill-shaped delta badge (▲/▼/—) and footnotes.
- **Tabs** — `Overview` (trend + store/category + period comparison), `Trends & Mix` (payment/status + daily detail),
  `Breakdown` (top brands + treemap + tables), `Data` (top products/customers + searchable recent orders).
- **UX polish** — active filter chips under the header, empty states, loading spinners,
  hover templates with currency formatting, per-chart CSV downloads, footer.
- **Config (`.streamlit/config.toml`)** — `F8FAFC` app background, blur header, minimal toolbar, no usage stats.

## Layout

| File | Responsibility |
|---|---|
| `home.py` | Landing page — KPIs + gold meta, entry point (`streamlit run dashboard/home.py`) |
| `pages/1_Sales.py` | Revenue trend + store/payment mix |
| `pages/2_Products.py` | Top products, brands, category→brand treemap |
| `pages/3_Customers.py` | Top customers + searchable recent orders |
| `pages/4_Categories.py` | Category donut + order-status breakdown |
| `helpers/queries.py` | All SQL — parameterized via `text()` + `bindparam(expanding=True)`, aggregated in Postgres |
| `helpers/theme.py` | Palette (`PALETTE`, `SEMANTIC`), `style(fig)`, `inject_css()` |
| `helpers/components.py` | KPI grid, chips, card helpers, dataframe+download, empty/footer |
| `lib/db.py` | Secrets→env + shared Postgres engine |
| `lib/filters.py` | Shared sidebar (presets + multiselects → `Filters`) |
| `lib/charts.py` | Shared Plotly builders (`revenue_trend_chart`, `bar_by`, `donut`) |
| `lib/queries.py` | Stable re-export layer for pages |
| `.streamlit/config.toml` | Streamlit chrome theme |

## Design choices worth knowing

- **Aggregation happens in SQL, not pandas.** Every chart does its own `GROUP BY` in Postgres
  and returns only summarized rows — the app never pulls the full `fact_order_items` table.
- **`is_active = true` on every query** (`fact_order_items` + `dim_orders`), matching the gold soft-delete convention.
- **KPIs show period-over-period deltas** — current window vs. equal-length prior window — with pill badges.
- **`Filters` is a frozen dataclass** so `@st.cache_data` can hash it directly.
- **Recent orders** are a bounded 200-row sample with client-side search + CSV export; full history lives in `gold.fact_order_items`.

## Extending it

- Add a breakdown dimension: one line in `_DIMENSION_COLUMNS` in `helpers/queries.py` (whitelist-guarded, no raw SQL).
- Add a `dim_date` table (fiscal periods, holiday flags) to enrich `get_revenue_trend` beyond `date_trunc`.
- Swap `PALETTE`/`SEMANTIC` in `helpers/theme.py` to rebrand without touching pages.
