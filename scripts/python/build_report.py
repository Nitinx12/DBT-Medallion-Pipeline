"""Build reports/report.pdf from report.tex content using reportlab.

Fallback PDF builder when no LaTeX engine (pdflatex/xelatex) is installed.
Mirrors the structure of reports/report.tex with styled Platypus flowables.
"""
from __future__ import annotations

import pathlib

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = PROJECT_ROOT / "reports" / "report.pdf"

WALMART_BLUE = colors.HexColor("#0071CE")
WALMART_BLUE_DARK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")
BRONZE = colors.HexColor("#8B5A2B")
SILVER = colors.HexColor("#6B7280")
GOLD = colors.HexColor("#92400E")
CODE_BG = colors.HexColor("#F8FAFC")

styles = getSampleStyleSheet()

sTitle = ParagraphStyle("Title2", parent=styles["Title"], fontSize=26, leading=30, textColor=WALMART_BLUE_DARK, alignment=TA_CENTER, spaceAfter=6)
sSubtitle = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=11, leading=15, textColor=MUTED, alignment=TA_CENTER, spaceAfter=4)
sH1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, leading=19, textColor=WALMART_BLUE_DARK, spaceBefore=14, spaceAfter=6, keepWithNext=True, borderPadding=(0, 0, 4))
sH2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, leading=16, textColor=WALMART_BLUE_DARK, spaceBefore=10, spaceAfter=4, keepWithNext=True)
sH3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=10.5, leading=14, textColor=WALMART_BLUE_DARK, spaceBefore=8, spaceAfter=3)
sBody = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.2, leading=13.2, textColor=colors.HexColor("#1E293B"), alignment=TA_JUSTIFY, spaceAfter=4)
sBodyLeft = ParagraphStyle("BodyLeft", parent=sBody, alignment=TA_LEFT)
sBullet = ParagraphStyle("Bullet", parent=sBody, leftIndent=14, bulletIndent=4, spaceAfter=2)
sCaption = ParagraphStyle("Caption", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=MUTED, alignment=TA_CENTER, spaceAfter=6)
sCell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=7.2, leading=9.5, textColor=colors.HexColor("#1E293B"))
sCellH = ParagraphStyle("CellH", parent=sCell, textColor=colors.white, fontName="Helvetica-Bold")
sCode = ParagraphStyle("Code", parent=styles["Code"], fontSize=7.2, leading=9.2, textColor=colors.HexColor("#0F172A"), fontName="Courier", backColor=CODE_BG, borderPadding=(4, 4, 6))
sToc = ParagraphStyle("Toc", parent=styles["Normal"], fontSize=9, leading=13, textColor=WALMART_BLUE_DARK)
sKpi = ParagraphStyle("Kpi", parent=styles["Normal"], fontSize=8, leading=10, textColor=WALMART_BLUE_DARK, alignment=TA_CENTER)


def hr():
    return HRFlowable(width="100%", thickness=0.6, color=WALMART_BLUE, spaceAfter=6, spaceBefore=2)


def hr_light():
    return HRFlowable(width="100%", thickness=0.4, color=LINE, spaceAfter=6, spaceBefore=4)


def styled_table(headers, rows, col_widths=None, header_color=WALMART_BLUE):
    data = [[Paragraph(f"<b>{h}</b>", sCellH) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), sCell) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style))
    return t


def p(txt, style=sBody):
    return Paragraph(txt, style)


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(18 * mm, 282 * mm, 192 * mm, 282 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 286 * mm, "WALMART  MEDALLION  PIPELINE")
    canvas.drawRightString(192 * mm, 286 * mm, "Technical Report  —  2026")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(105 * mm, 10 * mm, f"{doc.page}")
    canvas.restoreState()


def build():
    doc = BaseDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=16 * mm,
        title="Walmart Medallion Pipeline — Technical Report",
        author="Nitin",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=header_footer)])

    story = []

    # Title page
    story.append(Spacer(1, 18 * mm))
    story.append(p("Walmart Medallion Data Pipeline", sTitle))
    story.append(Spacer(1, 3 * mm))
    story.append(p("MongoDB &rarr; PostgreSQL &rarr; dbt &nbsp; (Bronze &rarr; Silver &rarr; Gold)", ParagraphStyle("sub2", parent=sSubtitle, fontSize=10.5, textColor=WALMART_BLUE)))
    story.append(p("Incremental PySpark Extraction &nbsp;|&nbsp; 17 dbt Models &nbsp;|&nbsp; 3 Runners &nbsp;|&nbsp; 8 Quality Gates", sSubtitle))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="28%", thickness=1.2, color=WALMART_BLUE, spaceAfter=6, spaceBefore=0, hAlign="CENTER"))
    story.append(p("Nitin &nbsp;—&nbsp; Walmart_DBT &nbsp;&nbsp;|&nbsp;&nbsp; September 2026 &nbsp;&nbsp;|&nbsp;&nbsp; v0.1.0 &nbsp;&nbsp;|&nbsp;&nbsp; github.com/Nitinx12/Walmart_DBT", sSubtitle))
    story.append(Spacer(1, 8 * mm))
    # KPI badges
    kpi_data = [
        [p("Python<br/>3.13 / 3.12 / 3.11", sKpi), p("PostgreSQL<br/>16", sKpi), p("PySpark<br/>3.5.5", sKpi), p("dbt<br/>1.12 / 1.11", sKpi)],
        [p("Airflow<br/>3.3 Celery", sKpi), p("GX<br/>1.21.0", sKpi), p("Docker<br/>Compose", sKpi), p("uv<br/>lock", sKpi)],
    ]
    kt = Table(kpi_data, colWidths=[38 * mm, 38 * mm, 38 * mm, 38 * mm])
    kt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(kt)
    story.append(Spacer(1, 8 * mm))
    # runners box
    box = Table([[p("One pipeline, three runners — <b>PowerShell</b>, <b>Airflow DAG</b>, <b>Docker image</b><br/>One warehouse — <b>walmart_db</b> with schemas <b>bronze / silver / gold</b>", ParagraphStyle("box", parent=sBody, alignment=TA_CENTER, fontSize=8.5))]], colWidths=[150 * mm])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")), ("BOX", (0, 0), (-1, -1), 0.6, WALMART_BLUE), ("ROUNDEDCORNERS", [6, 6, 6, 6]), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(box)
    story.append(Spacer(1, 10 * mm))
    story.append(p("This report documents the production-style medallion ETL that mirrors MongoDB operational data into a PostgreSQL warehouse and curates it through <b>bronze</b> (raw, 1:1), <b>silver</b> (deduped, typed, SCD2) and <b>gold</b> (dimensional star/snowflake) layers. The pipeline is implemented once and executed identically by three runners over eight strict stages gated by two independent test systems plus Great Expectations. It covers 9 silver and 8 gold dbt models, watermark-based incremental extraction with true upserts, containerisation with two images, CI with a live Postgres integration job, and a Streamlit+Plotly gold dashboard. All commands use <b>uv</b> and <b>uv.lock</b> is the source of truth.", sBody))
    story.append(Spacer(1, 3 * mm))
    story.append(p("<i>Keywords — Medallion architecture, PySpark, MongoDB Spark Connector, PostgreSQL 16, dbt Core, Airflow 3.3, Great Expectations, Docker Compose, Streamlit</i>", ParagraphStyle("kw", parent=sBody, fontSize=7.8, textColor=MUTED, alignment=TA_CENTER)))
    story.append(Spacer(1, 6 * mm))
    story.append(p("Abstract — 1 &nbsp;&nbsp;|&nbsp;&nbsp; Architecture at a Glance — 2 &nbsp;&nbsp;|&nbsp;&nbsp; 18 sections &nbsp;&nbsp;|&nbsp;&nbsp; Appendix: Quick Reference", ParagraphStyle("meta", parent=sCaption, fontSize=7)))
    # TOC page
    story.append(PageBreak())
    story.append(p("Contents", sH1))
    story.append(hr())
    toc = [
        "1 &nbsp; Introduction &amp; Objectives — 3",
        "2 &nbsp; Architecture at a Glance — 3",
        "3 &nbsp; Technology Stack — 4",
        "4 &nbsp; Repository Layout — 4",
        "5 &nbsp; Pipeline — Eight Strict Stages — 5",
        "6 &nbsp; Bronze Ingestion: Watermark Extraction — 6",
        "7 &nbsp; Silver Layer: Clean, Typed, Historical — 7",
        "8 &nbsp; Gold Layer: Dimensional Star / Snowflake — 8",
        "9 &nbsp; Data Quality: Three Independent Systems — 9",
        "10 &nbsp; Orchestration: One Pipeline, Three Runners — 9",
        "11 &nbsp; Containerisation — 10",
        "12 &nbsp; CI / CD — 10",
        "13 &nbsp; BI Layer: SQL Reports &amp; Dashboard — 11",
        "14 &nbsp; Shared Utilities — 12",
        "15 &nbsp; Running the Pipeline — 12",
        "16 &nbsp; Observability, Security &amp; Conventions — 13",
        "17 &nbsp; Limitations &amp; Roadmap — 13",
        "18 &nbsp; Conclusion &amp; References — 14",
        "Appendix A &nbsp; Quick Reference — 14 &nbsp;&nbsp;|&nbsp;&nbsp; Appendix B &nbsp; Environment Variables — 14",
    ]
    for t in toc:
        story.append(p(t, ParagraphStyle("tocline", parent=sToc, leftIndent=6, spaceAfter=2)))
    story.append(Spacer(1, 4 * mm))
    story.append(p("Conventions — <font color=\"#64748B\">All file paths are relative to the repository root. Code listings show the authoritative line numbers. Stage numbers 0–7 (eight stages) match <b>pipeline/run_pipeline.ps1</b>, <b>main.py</b> and <b>airflow/dags/walmart_pipeline_dag.py</b>.</font>", ParagraphStyle("tocnote", parent=sBody, fontSize=7.5, textColor=MUTED)))

    # 1
    story.append(p("1 &nbsp; Introduction &amp; Objectives", sH1))
    story.append(hr())
    story.append(p("1.1 &nbsp; Why medallion", sH2))
    story.append(p("Operational MongoDB must stay write-optimised; analytics needs a typed, historical, dimensional warehouse. The medallion pattern isolates those concerns: <b>bronze</b> preserves source fidelity, <b>silver</b> enforces types and slowly-changing history, <b>gold</b> publishes a star schema for BI. Every hand-off between layers is a quality gate — downstream layers only build if the upstream gate passes.", sBody))
    story.append(p("1.2 &nbsp; Project goals", sH2))
    for b in [
        "Replicate <b>every</b> user collection from MongoDB to Postgres automatically (no hard-coded list) and keep it incrementally fresh without re-copying unchanged data.",
        "Cure source issues once (typing, deduplication, SCD2) so gold consumers never re-implement cleaning.",
        "Publish a dimensional star (<b>fact_order_items</b> + 7 dims) that powers both SQL reports (<b>sql/*.sql</b>) and an interactive dashboard.",
        "Gate quality twice at each hand-off: dbt built-ins (<b>schema.yml</b>) <i>and</i> a standalone SQL suite (<b>tests/bronze|silver|gold</b>), plus a final cross-layer Great Expectations checkpoint.",
        "Run the <b>same</b> logic three ways — local Windows, Airflow schedule, standalone container — without forking code.",
        "Ship like a team would: <b>uv</b> lockfile, Ruff + SQLFluff + pre-commit, GitHub Actions CI with a live Postgres integration job, Docker images published to GHCR.",
    ]:
        story.append(p(f"• &nbsp; {b}", sBullet))
    story.append(p("1.3 &nbsp; Non-goals", sH2))
    story.append(p("Real-time streaming (batch incremental), cross-warehouse federation, and PII masking are out of scope for the current milestone.", sBody))

    # 2
    story.append(p("2 &nbsp; Architecture at a Glance", sH1))
    story.append(hr())
    flow = Table(
        [
            [p("<b>MongoDB</b><br/><font size=7 color=\"#64748B\">operational source</font>", ParagraphStyle("f", parent=sKpi, fontSize=8)), p("<b>bronze</b><br/><font size=7 color=\"#64748B\">raw, 1:1, _id PK</font>", sKpi), p("<b>silver</b><br/><font size=7 color=\"#64748B\">typed, deduped, SCD2</font>", sKpi), p("<b>gold</b><br/><font size=7 color=\"#64748B\">star / snowflake</font>", sKpi), p("<b>BI</b><br/><font size=7 color=\"#64748B\">reports + Streamlit</font>", sKpi)],
        ],
        colWidths=[30 * mm, 30 * mm, 32 * mm, 32 * mm, 32 * mm],
    )
    flow.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, WALMART_BLUE), ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FEF3C7")), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FEF3C7")), ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#F1F5F9")), ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#FEF9C3")), ("BACKGROUND", (4, 0), (4, 0), colors.HexColor("#EFF6FF")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(flow)
    story.append(Spacer(1, 2 * mm))
    story.append(p("Fig. 1 — Medallion flow: MongoDB &rarr; bronze (PySpark watermark) &rarr; silver &rarr; gold (dbt) &rarr; BI. Postgres database is <b>walmart_db</b>; schemas default to <b>bronze / silver / gold</b> via POSTGRES_SCHEMA_* in .env (.env.example is the template). Control tables etl_watermarks and etl_logs live alongside bronze.", sCaption))
    story.append(p("All runners set <b>PYTHONPATH</b> to the project root so <b>utils.*</b> resolves identically. The “localhost problem” is handled by rewriting localhost &rarr; host.docker.internal only in consuming layers (DAG _PREAMBLE, docker run), never by editing .env.", sBody))

    # 3
    story.append(p("3 &nbsp; Technology Stack", sH1))
    story.append(hr())
    story.append(styled_table(["Layer", "Technology", "Version / Notes"], [
        ["Language", "Python", "3.13 local, 3.12-slim Docker, 3.11 CI"],
        ["Package mgr", "uv", "uv.lock is source of truth; never hand-edit pyproject.toml without uv lock"],
        ["Compute", "PySpark", "3.5.5 pinned — required by mongo-spark-connector_2.12:10.4.0; 4.x is binary-incompatible"],
        ["Source", "MongoDB", "Operational DB, auto-discovered collections"],
        ["Warehouse", "PostgreSQL", "16 — walmart_db, JDBC via jars/postgresql.jar"],
        ["Transform", "dbt Core + dbt-postgres", "1.12.0 / 1.11.0 — 17 models, 100+ tests"],
        ["Orchestration", "Apache Airflow", "3.3.x, CeleryExecutor (scheduler, worker, triggerer, Redis, Postgres meta)"],
        ["Quality", "Great Expectations", "1.21.0 — suites per layer in pipeline/data_quality/suites/"],
        ["BI", "Streamlit 1.62 + Plotly 7.0", "Live gold dashboard at dashboard/app.py"],
        ["Lint / Format", "Ruff 0.16 + SQLFluff 4.2 + pre-commit", "ruff check/format, sqlfluff lint --dialect postgres"],
        ["Containers", "Docker / Compose", "docker/Dockerfile (standalone) + docker/Dockerfile.airflow"],
        ["CI", "GitHub Actions", "lint → dashboard-smoke → unit → DAG → Docker → integration (live Postgres)"],
    ], col_widths=[28 * mm, 38 * mm, 90 * mm]))
    story.append(Spacer(1, 2 * mm))
    story.append(p("JDK is 17 (docker/Dockerfile and dev container) — PySpark 3.5’s Mongo connector is untested on JDK 21, so the pin is intentional.", sBody))

    # 4
    story.append(p("4 &nbsp; Repository Layout", sH1))
    story.append(hr())
    story.append(p("airflow/dags/walmart_pipeline_dag.py &nbsp;|&nbsp; docker/Dockerfile, Dockerfile.airflow, compose.yml &nbsp;|&nbsp; docs/*.md &nbsp;|&nbsp; jars/*.jar &nbsp;|&nbsp; pipeline/run_pipeline.ps1 + data_quality/ &nbsp;|&nbsp; scripts/python/ (extract.py, sql_test.py, ci_seed_bronze.py, …) &nbsp;|&nbsp; sql/ (21 files) &nbsp;|&nbsp; tests/bronze (3), silver (9), gold (7) &nbsp;|&nbsp; utils/ (engine.py, connection.py, logger.py) &nbsp;|&nbsp; dbt/models/{silver,gold} &nbsp;|&nbsp; dashboard/ (app.py, queries.py, theme.py) &nbsp;|&nbsp; reports/ &nbsp;|&nbsp; main.py", ParagraphStyle("mono", parent=sCode, fontSize=7, leading=10, alignment=TA_LEFT)))
    story.append(p("Conventions: <b>snake_case</b>, type hints on every signature, one function = one responsibility (see scripts/python/extract.py stage split), short “why not what” comments, <b>uv run ruff format/check</b> before commit.", sBody))

    # 5
    story.append(p("5 &nbsp; Pipeline — Eight Strict Stages", sH1))
    story.append(hr())
    story.append(p("Fixed order. If stage order or the definition of “success” changes, <b>pipeline/run_pipeline.ps1</b> <i>and</i> <b>airflow/dags/walmart_pipeline_dag.py</b> must change together (convention, AGENTS.md: Pipeline Stage Rule).", sBody))
    story.append(styled_table(["#", "Stage", "Runner command", "Gate"], [
        ["0", "Preflight", 'uv run python -c "import pyspark" + prefix check 3.5.x', "Mismatch → fail fast; container refuses to self-heal"],
        ["1", "Extract", "uv run python scripts/python/extract.py", "Per-collection VALIDATION FAILED → non-zero exit"],
        ["2", "Bronze SQL tests", "uv run python scripts/python/sql_test.py tests/bronze", "3 checks; violating rows → FAIL"],
        ["3", "dbt silver", "cd dbt && dbt run --select silver; dbt test --select silver", "schema.yml tests; failure stops stage"],
        ["4", "Silver SQL tests", "…/sql_test.py tests/silver", "9 checks"],
        ["5", "dbt gold", "dbt run --select gold + test", "8 models (7 dims + 1 fact)"],
        ["6", "Gold SQL tests", "…/sql_test.py tests/gold", "7 checks"],
        ["7", "Great Expectations", "python -m pipeline.data_quality.run --layer all", "Bronze/Silver/Gold suites; exit 1=data fail, 2=build error"],
    ], col_widths=[10 * mm, 28 * mm, 62 * mm, 56 * mm]))
    story.append(Spacer(1, 2 * mm))
    story.append(p("Stop-on-first-failure: <b>run_pipeline.ps1:99</b> (Stop-Pipeline) and <b>main.py:244</b> (raise) halt immediately; Airflow’s default <b>all_success</b> trigger does the same — downstream tasks go to <b>upstream_failed</b>. Logs go to <b>logs/pipeline_YYYY-MM-DD.log</b> (utils/logger.py) plus <b>{schema}.etl_logs</b> audit rows. Header “STEP n / 7” plus stage 0 = 8 stages stays honest via <b>main.py:37 TOTAL_STEPS = 7</b> assert.", sBody))

    # 6
    story.append(p("6 &nbsp; Bronze Ingestion: Watermark Extraction", sH1))
    story.append(hr())
    story.append(p("File: <b>scripts/python/extract.py</b> (~1230 lines) — the only place that touches MongoDB.", ParagraphStyle("note", parent=sBody, textColor=MUTED, fontSize=8)))
    story.append(p("6.1 &nbsp; Auto-discovery", sH2))
    story.append(p("<b>discover_collections()</b> lists <b>mongo_db.list_collection_names()</b> and drops names starting with <b>system.</b> (extract.py:127). No collection list is hard-coded; <b>--tables</b> is an optional filter for ad-hoc runs.", sBody))
    story.append(p("6.2 &nbsp; Watermark column priority", sH2))
    story.append(p("Per collection, a single document sample is inspected; first present candidate wins: <b>updated_timestamp &gt; updated_at &gt; created_timestamp &gt; created_at</b> (extract.py:151). <b>updated_*</b> is preferred because documents mutated after insert (e.g. order status → Cancelled) must be re-synced.", sBody))
    story.append(p("6.3 &nbsp; Incremental pushdown", sH2))
    story.append(p('When a watermark column and prior <b>last_watermark_value</b> exist, the Spark read is filtered server-side: <b>watermark_str = since.strftime("%Y-%m-%d %H:%M:%S")</b> then <b>json.dumps([{"$match": {col: {"$gt": watermark_str}}}])</b> via <b>reader.option("aggregation.pipeline", …)</b> (extract.py:656). Comparison is string-to-string because the source stores timestamps as "YYYY-MM-DD HH:MM:SS" strings, not BSON dates — MongoDB never matches across BSON types in $gt.', sBody))
    story.append(p("6.4 &nbsp; Upsert, not append", sH2))
    story.append(p("<b>_id</b> (cast to string, sanitize_for_postgres:672) is the merge key. Existing tables get a scratch staging table <b>_stg_{collection}</b> written with <b>mode(\"overwrite\")</b>, then a single <b>INSERT … ON CONFLICT (_id) DO UPDATE</b> with <b>(xmax = 0) AS inserted</b> to split counts (extract.py:721). A unique index on <b>_id</b> is ensured first (ensure_unique_id_index:409); creation failure (duplicate _id from a prior append-only run) falls back to plain append with a warning.", sBody))
    story.append(p("6.5 &nbsp; Nested fields", sH2))
    story.append(p("<b>StructType / ArrayType / MapType</b> columns are serialised to JSON strings via <b>to_json()</b> (extract.py:680) — the only lossy step, required because plain JDBC has no native struct type. Flattened field names are reported in the Rich final panel.", sBody))
    story.append(p("6.6 &nbsp; Control tables", sH2))
    for b in [
        "<b>{bronze}.etl_watermarks</b> — one row per collection: incremental_column, last_watermark_value, last_run_mode, rows_inserted/updated, updated_at. Upserted via ON CONFLICT (table_name) (extract.py:528).",
        "<b>{bronze}.etl_logs</b> — one audit row per collection per run: mode, counts before/after, validation status, error_full traceback, duration. Best-effort, never fails the run.",
        "<b>ensure_control_tables:448</b> is idempotent and forward-migrates columns added in later versions.",
    ]:
        story.append(p(f"• &nbsp; {b}", sBullet))
    story.append(p("6.7 &nbsp; Validation &amp; reporting", sH2))
    story.append(p("After each merge, <b>validate_collection:619</b> recounts the target and expects <b>before + inserted</b>. A Rich report prints per-collection rows, watermark state, flattened fields, and failures (render_report:916); same data lands in the daily log file and etl_logs. CLI: <b>--tables, --full-refresh, --dry-run, --watermark-column</b> (extract.py:1117).", sBody))

    # 7
    story.append(p("7 &nbsp; Silver Layer: Clean, Typed, Historical", sH1))
    story.append(hr())
    story.append(p("<b>dbt/dbt_project.yml:35</b> materialises all silver models as <b>table</b> in schema <b>silver</b>. Nine models mirror bronze 1:1 but add typing, dedup, and canonicalisation.", sBody))
    story.append(styled_table(["Model", "Key cleaning", "Notable logic"], [
        ["silver.brands", "dedup on _id, trim/case", "Coalesce brand name variants"],
        ["silver.categories", "dedup, null handling", "Canonical category list"],
        ["silver.customers", "dedup, email/phone", "is_active flag"],
        ["silver.employees", "dedup, date parsing", "Joins to stores"],
        ["silver.orders", "timestamp parsing, status", "order_timestamp typed"],
        ["silver.order_items", "line_amount = qty*price", "FK to orders + products"],
        ["silver.payment_methods", "dedup, type norm", "Lookup for gold dim"],
        ["silver.products", "dedup, price typing", "Links brands + categories"],
        ["silver.stores", "dedup, geo", "Store master"],
    ], col_widths=[32 * mm, 42 * mm, 82 * mm], header_color=SILVER))
    story.append(Spacer(1, 2 * mm))
    story.append(p("Each model has a <b>schema.yml</b> with <b>not_null, unique, relationships, accepted_values</b> tests. Grain is one row per source document — no aggregation yet. <b>tests/silver/</b> adds 9 PL/pgSQL checks (row counts, orphan FKs, distinctness) via <b>scripts/python/sql_test.py</b>.", sBody))

    # 8
    story.append(p("8 &nbsp; Gold Layer: Dimensional Star / Snowflake", sH1))
    story.append(hr())
    story.append(p("<b>dbt/dbt_project.yml:39</b> materialises gold as <b>table</b> in schema <b>gold</b>. Eight models:", sBody))
    story.append(styled_table(["Model", "Type", "Grain"], [
        ["gold.dim_stores", "Dimension", "One row per store"],
        ["gold.dim_customers", "Dimension", "One row per customer"],
        ["gold.dim_products", "Dimension (snowflake)", "One row per product"],
        ["gold.dim_brands", "Sub-dimension", "One row per brand"],
        ["gold.dim_categories", "Sub-dimension", "One row per category"],
        ["gold.dim_orders", "Dimension", "One row per order header"],
        ["gold.dim_payment_methods", "Dimension", "One row per payment method"],
        ["gold.fact_order_items", "Fact (incremental merge)", "One row per order line; FKs to dim_orders, dim_products"],
    ], col_widths=[38 * mm, 36 * mm, 82 * mm], header_color=GOLD))
    story.append(Spacer(1, 2 * mm))
    for b in [
        "<b>fact_order_items.sql:1</b> is the only incremental gold model — <b>unique_key=order_item_id</b>, <b>incremental_strategy='merge'</b>, 3-day lookback (<b>updated_timestamp &gt;= MAX(updated_timestamp) - 3 days</b>) to catch late-arriving updates.",
        "Dimensions are full-refresh tables rebuilt from silver each run — cheap at this scale and avoids SCD bookkeeping where not needed.",
        "<b>gold_loaded_at = CURRENT_TIMESTAMP</b> stamps lineage.",
        "The star is snowflaked only at products → brands/categories — intentional, because brand/category reports aggregate directly on those sub-dims.",
    ]:
        story.append(p(f"• &nbsp; {b}", sBullet))
    story.append(p("Gold is gated by <b>dbt test --select gold</b> plus 7 standalone checks under <b>tests/gold/</b>.", sBody))

    # 9
    story.append(p("9 &nbsp; Data Quality: Three Independent Systems", sH1))
    story.append(hr())
    story.append(styled_table(["System", "Location", "Runner", "Semantics"], [
        ["dbt tests", "dbt/models/*/schema.yml", "dbt test --select silver|gold", "Column/table contracts (null, unique, FK, accepted values)"],
        ["SQL suite", "tests/{bronze,silver,gold}/*.sql", "sql_test.py tests/<layer>", "SELECT returning violating rows = FAIL; DO $$ RAISE EXCEPTION = FAIL; one conn/layer, rollback on fail"],
        ["Great Expectations", "pipeline/data_quality/suites/", "python -m pipeline.data_quality.run --layer all", "One checkpoint per layer ({layer}_checkpoint), Fluent API 1.x; exit 1=data fail, 2=build error"],
    ], col_widths=[26 * mm, 38 * mm, 42 * mm, 50 * mm]))
    story.append(Spacer(1, 2 * mm))
    story.append(p("The SQL suite auto-detects mode per file via <b>psycopg2 ResourceClosedError</b> (tests/unit/test_sql_test.py:89). GX suites are built <b>add_or_update</b> so re-runs reconcile instead of duplicating, and all requested layers run even if an earlier one fails unless <b>--fail-fast</b> is passed (pipeline/data_quality/run.py:150). Together: bronze 3 checks, silver 9, gold 7, plus ~23 GX suites and 100+ dbt tests.", sBody))

    # 10
    story.append(p("10 &nbsp; Orchestration: One Pipeline, Three Runners", sH1))
    story.append(hr())
    story.append(styled_table(["Runner", "Entry point", "How it loads env & runs"], [
        ["Windows host", "pipeline/run_pipeline.ps1\n+ run_pipeline.bat", "Import-DotEnv overwrites process env; Assert-Prerequisites checks 7 paths; Invoke-PipelineCommand shells out via uv"],
        ["Standalone container", "main.py\n(docker/Dockerfile ENTRYPOINT)", "load_dotenv via setdefault (container env wins); in_container() refuses to self-heal PySpark inside image"],
        ["Airflow DAG", "airflow/dags/walmart_pipeline_dag.py\ndag_id=walmart_medallion_pipeline", "Every @task.bash prefixes _PREAMBLE: source .env, rewrite localhost→host.docker.internal, force PYSPARK_PYTHON=/app/.venv/bin/python, set DBT_PROFILES_DIR=/app/docker/dbt"],
    ], col_widths=[28 * mm, 44 * mm, 84 * mm]))
    story.append(Spacer(1, 2 * mm))
    story.append(p("DAG tasks form a linear chain <b>preflight → extract → bronze_tests → silver_run → silver_test → silver_sql → gold_run → gold_test → gold_sql → gx</b> with default <b>retries=0, max_active_runs=1</b>. Fail-fast is free from Airflow’s <b>all_success</b>. <b>_PREAMBLE</b> handles the “localhost problem” (docs/architecture.md:29): .env keeps localhost for local uv run; only consuming layers rewrite.", sBody))

    # 11
    story.append(p("11 &nbsp; Containerisation", sH1))
    story.append(hr())
    story.append(p("<b>Two images, two jobs</b> (docs/docker.md):", sH2))
    for b in [
        "<b>docker/Dockerfile</b> — standalone runner: <b>python:3.12-slim + JDK 17 + uv</b>, copies <b>jars/</b>, installs from <b>uv.lock</b>, sets <b>RUNNING_IN_DOCKER=1</b>, <b>ENTRYPOINT [\"python\",\"main.py\"]</b>.",
        "<b>docker/Dockerfile.airflow</b> — CeleryExecutor base: <b>apache/airflow:3.3.0 + JDK 17 + uv</b>, same <b>jars/</b> layer, used by <b>docker/compose.yml</b> for 6 services (apiserver, scheduler, dag-processor, worker, triggerer, postgres+redis).",
        "<b>docker/compose.yml</b> mounts the project root to <b>/app</b> and shadows <b>/app/.venv</b> with an anonymous volume so the container’s Linux venv never clobbers the host’s Windows venv. <b>airflow-worker</b> gets <b>extra_hosts: host.docker.internal:host-gateway</b>.",
        "Dev container (<b>.devcontainer/devcontainer.json</b>) mirrors the standalone Dockerfile (JDK 17, uv preinstalled) so PySpark works without local Java.",
    ]:
        story.append(p(f"• &nbsp; {b}", sBullet))

    # 12
    story.append(p("12 &nbsp; CI / CD", sH1))
    story.append(hr())
    story.append(p("<b>.github/workflows/ci.yml</b> — 6 jobs, PYTHON_VERSION 3.11, AIRFLOW_VERSION 3.3.0:", sBody))
    for i, b in enumerate([
        "<b>lint</b> — <b>ruff check</b>, <b>ruff format --check</b>, <b>sqlfluff lint dbt/models sql/ tests/ --dialect postgres</b>",
        "<b>dashboard-smoke</b> — installs <i>only</i> <b>dashboard/requirements.txt</b> (no databricks-sql-connector), asserts databricks not importable, then imports <b>dashboard.queries</b> with dummy env — catches the unconditional-databricks regression that broke Streamlit Cloud.",
        "<b>unit-tests</b> — <b>pytest tests/unit -v --cov=utils --cov=scripts</b> (28 tests, mocked, no live DB)",
        "<b>dag-integrity</b> — installs Airflow via constraints file and asserts <b>DagBag</b> loads <b>walmart_medallion_pipeline</b> with no import errors or cycles.",
        "<b>docker-build</b> — builds both <b>docker/Dockerfile</b> and <b>docker/Dockerfile.airflow</b> with Buildx cache, <b>lfs: true</b> so <b>jars/*.jar</b> are real files.",
        "<b>integration</b> — live Postgres 16 service; <b>ci_seed_bronze.py</b> seeds bronze from fixtures, then the exact gate sequence: bronze SQL → <b>dbt run/test silver</b> → silver SQL → <b>dbt run/test gold</b> → gold SQL → GX <b>--layer all</b>. Uses absolute <b>DBT_PROFILES_DIR</b> and <b>PYTHONPATH</b> fixes documented inline.",
    ], 1):
        story.append(p(f"<b>{i}.</b> &nbsp; {b}", sBullet))
    story.append(p("Images are published to GHCR on merge/tag; releases are cut via <b>CHANGELOG.md</b>.", sBody))

    # 13
    story.append(p("13 &nbsp; BI Layer: SQL Reports &amp; Dashboard", sH1))
    story.append(hr())
    story.append(p("13.1 &nbsp; Hand-written SQL (sql/, 21 files)", sH2))
    story.append(p("<b>00_init_schema.sql</b> creates schemas and extensions; <b>01_brands.sql .. 03_payment_methods.sql</b> and <b>08_order_status_analysis.sql .. 20_no_sales_date_analysis.sql</b> are analytical queries (brand/category revenue share, payment mix, ranking, Pareto, market basket, ABC, cohort) and two PL/pgSQL functions (<b>05_fn_product_report.sql</b>, <b>06_fn_sales_trend.sql</b>) plus a trigger (<b>07_trg_loaded.sql</b>). They query gold directly and are the ancestors of <b>reports/brand_report.md</b> and <b>category_report.md</b>.", sBody))
    story.append(p("13.2 &nbsp; Gold dashboard (dashboard/)", sH2))
    story.append(p("<b>dashboard/app.py</b> (766 lines) is a Streamlit app with Plotly charts. All SQL lives in <b>queries.py</b> (parameterised, aggregated in Postgres, cached via <b>st.cache_data</b>); styling in <b>theme.py</b>; cards/chips in <b>components.py</b>. Filters (date presets 7D/30D/90D/YTD/All, stores, categories, order statuses, granularity Day/Week/Month) build an immutable <b>Filters</b> key; KPIs show period-over-period deltas; tabs are Overview / Trends &amp; Mix / Breakdown / Data. Graceful empty states when gold is unpopulated. Runs with <b>uv run streamlit run dashboard/app.py</b> or on Streamlit Cloud with <b>st.secrets</b> fallback (app.py:34).", sBody))
    story.append(p("13.3 &nbsp; Existing reports (reports/)", sH2))
    story.append(p("<b>reports/brand_report.md</b> (7 brands, $18.9M total, Apple 15.75% leader) and <b>reports/category_report.md</b> (Electronics 17.76% leader, Home 14.34% outlier) are the reference BI outputs — both derived from gold CTEs that <b>LEFT JOIN dim_* → fact_order_items</b> so zero-sales entities remain visible.", sBody))

    # 14
    story.append(p("14 &nbsp; Shared Utilities", sH1))
    story.append(hr())
    for title, desc in [
        ("utils/engine.py", "Loads <b>.env</b> at import, validates required vars (<b>POSTGRES_*, MONGO_*</b>) with <b>OSError</b> on missing, warns on optional <b>POSTGRES_SCHEMA_*</b> and Databricks vars, casts <b>POSTGRES_PORT</b> to int. Hard-fails fast so every script gets a clear error."),
        ("utils/connection.py", "Cached factories: <b>get_postgres_engine()</b> (SQLAlchemy, SSL params), <b>get_mongo_db()</b> (pymongo with ping), <b>get_databricks_connection()</b> (lazy databricks_sql_connector, <b>ModuleNotFoundError</b> if extra not installed — dashboard-safe)."),
        ("utils/logger.py", "<b>get_logger(name)</b> returns a logger with console + daily file handlers (<b>logs/pipeline_YYYY-MM-DD.log</b>), <b>propagate=False</b>, configurable levels. Used by extract, dashboard, and GX runner."),
    ]:
        story.append(p(f"<b>{title}</b> — {desc}", sBullet))
    story.append(p("Patching for tests is via <b>tests/unit/test_*.py</b> with <b>unittest.mock</b> and small fixtures — never real DB data.", sBody))

    # 15
    story.append(p("15 &nbsp; Running the Pipeline", sH1))
    story.append(hr())
    story.append(p("Local (Windows) — mirrors README “Run it”:", sH3))
    story.append(p("uv venv<br/> .venv\\Scripts\\activate &nbsp; <font color=\"#64748B\"># Windows; source .venv/bin/activate on Linux/Mac</font><br/> uv sync &nbsp; <font color=\"#64748B\"># from uv.lock</font><br/> cp .env.example .env &nbsp; <font color=\"#64748B\"># fill POSTGRES_*, MONGO_*, optional DATABRICKS_*</font><br/><br/> ./pipeline/run_pipeline.ps1 &nbsp; <font color=\"#64748B\"># 8 stages</font><br/> # or: uv run python main.py<br/> # or: uv run python scripts/python/extract.py --dry-run --tables orders,customers<br/><br/> uv run python scripts/python/sql_test.py tests/bronze<br/> uv run dbt run --select silver --project-dir dbt &amp;&amp; uv run dbt test --select silver --project-dir dbt<br/> uv run python -m pipeline.data_quality.run --layer all<br/><br/> uv run streamlit run dashboard/app.py<br/><br/> uv run ruff format . &amp;&amp; uv run ruff check . &amp;&amp; uv run sqlfluff lint dbt/models --dialect postgres<br/> uv run pre-commit run --all-files<br/> uv run pytest tests/unit -v --cov=utils --cov=scripts", sCode))
    story.append(p("Docker &amp; Airflow:", sH3))
    story.append(p("docker build -f docker/Dockerfile -t walmart-pipeline .<br/> docker run --env-file .env walmart-pipeline<br/><br/> docker compose -f docker/compose.yml up<br/> # UI at http://localhost:8080 (airflow/airflow), DAG: walmart_medallion_pipeline", sCode))
    story.append(p("Health and security scripts: <b>uv run python scripts/python/health_check.py</b> and <b>security_check.py</b> (see <b>docs/health.md</b>).", sBody))

    # 16
    story.append(p("16 &nbsp; Observability, Security &amp; Conventions", sH1))
    story.append(hr())
    for b in [
        "Git workflow: one file/logical change per commit, <b>git add &lt;file&gt;</b> + prefix <b>extract: / dbt: / airflow: / docker: / tests: / utils: / docs:</b> (AGENTS.md, docs/git-workflow.md), rebase before push, no <b>.venv / __pycache__ / .env / data/raw|processed</b> committed.",
        "Secrets: <b>.env</b> is git-ignored; <b>.env.example</b> is the template; <b>detect-private-key</b> pre-commit hook; Databricks token never baked into images.",
        "Logging: Rich console + structured file logs + <b>etl_logs</b> table — three places to diagnose a failed collection without re-running.",
        "Idempotency: control tables and watermark upserts are <b>CREATE IF NOT EXISTS / ON CONFLICT</b> — re-running never duplicates state.",
        "Offline Spark: <b>jars/postgresql.jar</b> is vendored; the 5 Mongo connector jars are vendored when present in <b>jars/</b> — otherwise resolved once via Maven and a tip is printed (extract.py:304).",
    ]:
        story.append(p(f"• &nbsp; {b}", sBullet))

    # 17
    story.append(p("17 &nbsp; Limitations &amp; Roadmap", sH1))
    story.append(hr())
    story.append(styled_table(["Area", "Next step"], [
        ["Watermark type", "Source timestamps are strings; migrating Mongo to BSON dates would allow native date pushdown and remove the string-format coupling."],
        ["SCD2", "Silver history is dedup-only today; true SCD2 snapshots (dbt snapshots on dim_customers / dim_stores) are sketched in docs/dbt.md but not yet materialised."],
        ["Gold incremental", "Only fact_order_items is incremental; dimensions are full refresh — fine at current scale, revisit if counts grow 10x."],
        ["Streaming", "Batch-only; CDC via Debezium or Mongo change streams would enable near-real-time bronze."],
        ["PII / masking", "No column-level masking in silver; add views or dbt post-hooks before exposing gold externally."],
        ["Data Docs", "GX checkpoints have no UpdateDataDocsAction yet — add once gx/uncommitted is published."],
        ["Tests", "Bronze schema.yml tests are lighter than silver/gold — expand with dbt_expectations for cross-column rules."],
    ], col_widths=[28 * mm, 128 * mm]))

    # 18
    story.append(p("18 &nbsp; Conclusion", sH1))
    story.append(hr())
    story.append(p("The Walmart medallion pipeline delivers a clean separation between operational and analytical concerns without duplicating logic across execution environments. Auto-discovery plus watermark upserts keep bronze fresh and auditable; dbt turns that bronze into a typed silver and a dimensional gold that is directly queryable for reports and a live dashboard; two independent test systems plus Great Expectations gate every hand-off; and a single stage definition runs identically on a developer laptop, in Docker, and on a schedule in Airflow. The codebase is small enough to read in an afternoon (<b>extract.py</b> + 17 models + <b>sql_test.py</b> + <b>run.py</b>) yet strict enough to catch schema drift, load errors, and data regressions before they reach gold.", sBody))
    story.append(p("References", sH2))
    for ref in [
        "Project repository — <link href=\"https://github.com/Nitinx12/Walmart_DBT\">github.com/Nitinx12/Walmart_DBT</link>",
        "Live dashboard — <link href=\"https://walmartdbt-b3fdfqwyky3ghzr5syyxtu.streamlit.app/\">Streamlit Cloud</link>",
        "dbt documentation — <link href=\"https://docs.getdbt.com\">docs.getdbt.com</link>",
        "Great Expectations 1.x Fluent API — <link href=\"https://docs.greatexpectations.io\">docs.greatexpectations.io</link>",
        "MongoDB Spark Connector — <link href=\"https://www.mongodb.com/docs/spark-connector/\">mongodb.com/docs/spark-connector</link>",
        "Apache Airflow 3.3 — <link href=\"https://airflow.apache.org/docs/apache-airflow/3.3.0/\">airflow.apache.org</link>",
    ]:
        story.append(p(f"• &nbsp; {ref}", sBullet))

    # Appendix
    story.append(p("Appendix A &nbsp; Quick Reference", sH1))
    story.append(hr())
    story.append(styled_table(["Task", "Command"], [
        ["Create env", "uv venv"],
        ["Install deps", "uv sync"],
        ["Add dep", "uv add <pkg>"],
        ["Run extract", "uv run python scripts/python/extract.py"],
        ["Run dbt tests", "uv run dbt test --select silver"],
        ["Run SQL suite", "uv run python scripts/python/sql_test.py tests/<layer>"],
        ["Run GX", "uv run python -m pipeline.data_quality.run --layer all"],
        ["Format", "uv run ruff format ."],
        ["Lint", "uv run ruff check ."],
        ["Stage one file", "git add <file>"],
        ["Commit", 'git commit -m "<area>: <summary>"'],
    ], col_widths=[32 * mm, 124 * mm]))
    story.append(p("Appendix B &nbsp; Environment Variables (.env.example)", sH2))
    story.append(p("POSTGRES_HOST=localhost<br/> POSTGRES_PORT=5432<br/> POSTGRES_DATABASE=walmart_db<br/> POSTGRES_USERNAME=postgres<br/> POSTGRES_PASSWORD=changeme<br/> POSTGRES_SCHEMA_BRONZE=bronze<br/> POSTGRES_SCHEMA_SILVER=silver<br/> POSTGRES_SCHEMA_GOLD=gold<br/> MONGO_URI=mongodb://localhost:27017<br/> MONGO_DB=walmart<br/> PYSPARK_PYTHON=python<br/> PYSPARK_DRIVER_PYTHON=python<br/> DATABRICKS_HOST=<br/> DATABRICKS_HTTP_PATH=<br/> DATABRICKS_TOKEN=", sCode))
    story.append(Spacer(1, 6 * mm))
    story.append(p("Generated from repository state at <b>main@aa3d139</b> — September 2026. For the full system design see <b>docs/architecture.md</b> and <b>README.md</b>. LaTeX source is <b>reports/report.tex</b>; this PDF was built via <b>scripts/python/build_report.py</b> (reportlab) so it renders even without a local TeX engine.", ParagraphStyle("foot", parent=sCaption, fontSize=7)))

    doc.build(story)
    print(f"Built {OUT} ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    build()
