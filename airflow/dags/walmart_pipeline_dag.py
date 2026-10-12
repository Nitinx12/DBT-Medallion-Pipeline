"""
walmart_pipeline_dag.py
Target location in your repo: airflow/dags/walmart_pipeline_dag.py

Mirrors pipeline/run_pipeline.ps1 stage-for-stage and in the same order:
    0. Preflight        (pyspark <-> mongo-spark-connector version check)
    1. Extract          (scripts/python/extract.py)
    2. Bronze SQL tests (tests/bronze/*.sql)
    3. dbt silver build + test (dbt, models/silver)
    4. Silver SQL tests (tests/silver/*.sql)
    5. dbt gold build + test (dbt, models/gold)
    6. Gold SQL tests (tests/gold/*.sql)
    7. Great Expectations tests (Bronze, Silver, Gold)

Stop-on-first-failure is native to this: Airflow's default trigger rule
(all_success) means the moment one task fails, everything downstream goes
to upstream_failed and never runs -- no extra guard logic needed to match
ps1's Stop-Pipeline behavior.

Schedule: Monday, Tuesday, Wednesday at 11:00 AM (Asia/Kolkata).
Email: detailed HTML summary sent on success or failure via SMTP (configured
in .env — AIRFLOW__SMTP__* variables).
"""

from __future__ import annotations

import os

import pendulum
from airflow.sdk import dag, task

try:  # Airflow 3.x canonical path (airflow.utils.trigger_rule is deprecated)
    from airflow.task.trigger_rule import TriggerRule
except ImportError:  # pragma: no cover - legacy Airflow 2.x layout
    from airflow.utils.trigger_rule import TriggerRule

try:  # Airflow 3.x canonical path; falls back to the legacy alias
    from airflow.providers.smtp.operators.smtp import EmailOperator
except ImportError:  # pragma: no cover - legacy Airflow 2.x layout
    from airflow.operators.email import EmailOperator

try:  # run at 11:00 Asia/Kolkata, not 11:00 UTC
    from airflow.timetables.trigger import CronTriggerTimetable

    _SCHEDULE = CronTriggerTimetable("0 11 * * 1,2,3", timezone="Asia/Kolkata")
except Exception:  # noqa: BLE001 - timetable import must never break DAG parsing
    # pragma: no cover - very old Airflow without trigger timetables
    _SCHEDULE = "0 11 * * 1,2,3"

PROJECT_ROOT = "/app"
DBT_PROJECT_DIR = f"{PROJECT_ROOT}/dbt"

REQUIRED_PYSPARK_PREFIX = "3.5"

# Single source of truth for the stages collect_results reports on. Must stay
# in sync with the chain wired at the bottom of this file.
STAGE_TASK_IDS = [
    "preflight",
    "extract",
    "bronze_sql_tests",
    "dbt_silver_run",
    "dbt_silver_test",
    "silver_sql_tests",
    "dbt_gold_run",
    "dbt_gold_test",
    "gold_sql_tests",
    "great_expectations_tests",
]

_RAW_RECIPIENTS = os.environ.get("AIRFLOW__SMTP__SMTP_MAIL_FROM", "Nitin85x@gmail.com")
# Supports a comma-separated recipient list; ignores the "changeme" placeholder
# from .env.example so a misconfigured env fails loudly at send time, not here.
EMAIL_RECIPIENTS = [
    addr.strip()
    for addr in _RAW_RECIPIENTS.split(",")
    if addr.strip() and addr.strip().lower() != "changeme"
] or ["Nitin85x@gmail.com"]

_PREAMBLE = (
    "set -euo pipefail; "
    f"cd {PROJECT_ROOT}; "
    # NOTE: do NOT `source /app/.env` here. The host .env contains values
    # with spaces (e.g. the Gmail app password `cngi cvjg llrv numr`) that
    # `source` word-splits into bogus commands (exit 127). Exporting each
    # KEY=VALUE line as a single word assigns values literally instead.
    # NOTE: .format() is deliberate here — f-strings would need every bash
    # ${...} doubled to {{...}}. (noqa: UP030/UP032)
    'if [ -f "{0}/.env" ]; then set -a; '.format(PROJECT_ROOT)
    + 'while IFS= read -r line || [ -n "$line" ]; do '
    'case "$line" in ""|"#"*) continue;; *=*) export "$line" || true;; esac; '
    + "done < <(tr -d '\\r' < \"{0}/.env\"); set +a; fi; ".format(  # noqa: UP030,UP032
        PROJECT_ROOT
    )
    + 'export POSTGRES_HOST="${POSTGRES_HOST/localhost/host.docker.internal}"; '
    'export MONGO_URI="${MONGO_URI//localhost/host.docker.internal}"; '
    f"export PYTHONPATH={PROJECT_ROOT}; "
    "export PYSPARK_PYTHON=/app/.venv/bin/python; "
    "export PYSPARK_DRIVER_PYTHON=/app/.venv/bin/python; "
    f"export DBT_PROFILES_DIR={PROJECT_ROOT}/docker/dbt; "
)


@dag(
    dag_id="walmart_medallion_pipeline",
    schedule=_SCHEDULE,
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Kolkata"),
    catchup=False,
    max_active_runs=1,
    tags=["walmart", "medallion", "etl", "production"],
    default_args={
        "retries": 1,
        "retry_delay": pendulum.duration(minutes=5),
        # No per-task email_on_failure: failure notification is the summary
        # email (email_success/email_failure via choose_email). The notifier
        # path would spam one mail per failed task attempt.
    },
)
def walmart_medallion_pipeline():
    @task.bash(task_id="preflight")
    def preflight() -> str:
        # Uses the venv python directly: `uv run` would re-verify (and on a
        # cold volume, fully rebuild) the environment on every invocation.
        # The image bakes /app/.venv, so this is a seconds-fast import check;
        # the explicit `uv sync` below only fires as a self-heal fallback.
        return _PREAMBLE + (
            "if [ ! -x /app/.venv/bin/python ]; then "
            'echo "venv missing, running uv sync..."; uv sync --frozen; fi; '
            'installed="$(/app/.venv/bin/python -c '
            "'import pyspark; print(pyspark.__version__)' 2>/dev/null || true)\"; "
            f'if [[ "$installed" != {REQUIRED_PYSPARK_PREFIX}* ]]; then '
            f'echo "pyspark $installed is incompatible; run uv sync to restore '
            f'{REQUIRED_PYSPARK_PREFIX}.x"; exit 1; '
            f'else echo "pyspark $installed OK"; fi'
        )

    @task.bash(task_id="extract")
    def extract() -> str:
        return _PREAMBLE + "uv run python scripts/python/extract.py"

    @task.bash(task_id="bronze_sql_tests")
    def bronze_sql_tests() -> str:
        return _PREAMBLE + "uv run python scripts/python/sql_test.py tests/bronze"

    @task.bash(task_id="dbt_silver_run")
    def dbt_silver_run() -> str:
        return _PREAMBLE + f"cd {DBT_PROJECT_DIR} && uv run dbt run --select silver"

    @task.bash(task_id="dbt_silver_test")
    def dbt_silver_test() -> str:
        return _PREAMBLE + f"cd {DBT_PROJECT_DIR} && uv run dbt test --select silver"

    @task.bash(task_id="silver_sql_tests")
    def silver_sql_tests() -> str:
        return _PREAMBLE + "uv run python scripts/python/sql_test.py tests/silver"

    @task.bash(task_id="dbt_gold_run")
    def dbt_gold_run() -> str:
        return _PREAMBLE + f"cd {DBT_PROJECT_DIR} && uv run dbt run --select gold"

    @task.bash(task_id="dbt_gold_test")
    def dbt_gold_test() -> str:
        return _PREAMBLE + f"cd {DBT_PROJECT_DIR} && uv run dbt test --select gold"

    @task.bash(task_id="gold_sql_tests")
    def gold_sql_tests() -> str:
        return _PREAMBLE + "uv run python scripts/python/sql_test.py tests/gold"

    @task.bash(task_id="great_expectations_tests")
    def great_expectations_tests() -> str:
        return _PREAMBLE + "uv run python -m pipeline.data_quality.run --layer all"

    @task(task_id="collect_results", trigger_rule=TriggerRule.ALL_DONE)
    def collect_results(**context) -> dict:
        # NOTE: the `dag_run` object in the task context is a Pydantic DTO in
        # Airflow 3.x -- it has no get_task_instances() (that was the ORM
        # model in 2.x). Do NOT query the metadata DB directly either: task
        # processes run via the Execution API and never see
        # AIRFLOW__DATABASE__SQL_ALCHEMY_CONN (empty env + empty conf caused
        # "no usable metadata DB URL found"). Instead derive each stage's
        # status from its XCom -- bash tasks push return_value only on
        # success, so a missing XCom means failed/skipped/upstream_failed.
        # ti.xcom_pull goes through the Execution API, which IS available.
        dag_run = context["dag_run"]
        run_id = dag_run.run_id
        # NOTE: there is no `ds` key in the Airflow 3.x task context
        # (KeyError). Derive the YYYY-MM-DD date from the logical date.
        logical_date = context.get("logical_date", None) or getattr(
            dag_run, "logical_date", None
        )
        execution_date = (
            logical_date.date().isoformat() if logical_date is not None else "unknown"
        )

        ti = context["ti"]
        stage_statuses: dict[str, str] = {}
        for stage_id in STAGE_TASK_IDS:
            try:
                value = ti.xcom_pull(task_ids=stage_id)
            except Exception as exc:  # noqa: BLE001 - never fail the reporter
                print(f"collect_results: xcom_pull failed for {stage_id} ({exc})")
                value = None
            stage_statuses[stage_id] = "success" if value is not None else "failed"
            print(f"collect_results: {stage_id} -> {stage_statuses[stage_id]}")

        overall_status = (
            "SUCCESS"
            if all(state == "success" for state in stage_statuses.values())
            else "FAILURE"
        )

        return {
            "status": overall_status,
            "run_id": run_id,
            "date": execution_date,
            "stages": stage_statuses,
        }

    @task.branch(task_id="choose_email")
    def choose_email(**context) -> str:
        # Routes to exactly one of email_success / email_failure so the
        # pipeline never sends both (or neither) for a single run.
        ti = context["ti"]
        result = ti.xcom_pull(task_ids="collect_results") or {}
        if result.get("status") == "SUCCESS":
            return "email_success"
        return "email_failure"

    email_success = EmailOperator(
        task_id="email_success",
        to=EMAIL_RECIPIENTS,
        subject="✅ Walmart Pipeline SUCCESS — {{ ds }}",
        html_content="""
<h2>Walmart Medallion Pipeline — SUCCESS</h2>
<p><strong>Date:</strong> {{ ds }}</p>
<p><strong>Run ID:</strong> {{ ti.xcom_pull(task_ids='collect_results')['run_id'] }}</p>

<h3>Stage Results</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
<tr style="background:#4CAF50;color:white;">
<th>Stage</th><th>Status</th>
</tr>
{% for stage, status in ti.xcom_pull(task_ids='collect_results')['stages'].items() %}
<tr>
<td>{{ stage }}</td>
<td style="color:{% if status == 'success' %}green{% else %}red{% endif %};font-weight:bold;">
{{ status | upper }}
</td>
</tr>
{% endfor %}
</table>

 <p><em>All 7 stages completed. Data is ready in the gold layer.</em></p>
""",
        # Runs only when choose_email routes here; skipped otherwise.
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    email_failure = EmailOperator(
        task_id="email_failure",
        to=EMAIL_RECIPIENTS,
        subject="❌ Walmart Pipeline FAILED — {{ ds }}",
        html_content="""
<h2>Walmart Medallion Pipeline — FAILURE</h2>
<p><strong>Date:</strong> {{ ds }}</p>

<h3>Stage Results</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
<tr style="background:#f44336;color:white;">
<th>Stage</th><th>Status</th>
</tr>
{% set stages = ti.xcom_pull(task_ids='collect_results', default={'stages': {}})['stages'] %}
{% for stage, status in stages.items() %}
<tr>
<td>{{ stage }}</td>
<td style="color:{% if status == 'success' %}green{% else %}red{% endif %};font-weight:bold;">
{{ status | upper }}
</td>
</tr>
{% endfor %}
</table>

 <p><em>Check Airflow logs for the failing task to diagnose the issue.</em></p>
""",
        # Runs only when choose_email routes here; skipped otherwise.
        # (ALL_DONE would fire on success too, sending both emails.)
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )

    chain = (
        preflight()
        >> extract()
        >> bronze_sql_tests()
        >> dbt_silver_run()
        >> dbt_silver_test()
        >> silver_sql_tests()
        >> dbt_gold_run()
        >> dbt_gold_test()
        >> gold_sql_tests()
        >> great_expectations_tests()
    )

    collect_results_task = collect_results()
    choose_email_task = choose_email()
    chain >> collect_results_task >> choose_email_task >> [email_success, email_failure]


walmart_medallion_pipeline()
