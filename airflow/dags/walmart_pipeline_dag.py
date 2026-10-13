# Walmart medallion pipeline: MWF 11am, rest 11pm mail alerts
from __future__ import annotations

import os

import pendulum
from airflow.sdk import dag, task

try:
    from airflow.task.trigger_rule import TriggerRule
except ImportError:
    from airflow.utils.trigger_rule import TriggerRule
try:
    from airflow.providers.smtp.operators.smtp import EmailOperator
except ImportError:
    from airflow.operators.email import EmailOperator
try:
    from airflow.timetables.trigger import CronTriggerTimetable

    _MWF_SCHEDULE = CronTriggerTimetable("0 11 * * 1,3,5", timezone="Asia/Kolkata")
    _REST_SCHEDULE = CronTriggerTimetable("0 23 * * 0,2,4,6", timezone="Asia/Kolkata")
except Exception:
    _MWF_SCHEDULE = "0 11 * * 1,3,5"
    _REST_SCHEDULE = "0 23 * * 0,2,4,6"
PROJECT_ROOT = "/app"
DBT_PROJECT_DIR = f"{PROJECT_ROOT}/dbt"
REQUIRED_PYSPARK_PREFIX = "3.5"
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
EMAIL_RECIPIENTS = [
    addr.strip()
    for addr in _RAW_RECIPIENTS.split(",")
    if addr.strip() and addr.strip().lower() != "changeme"
] or ["Nitin85x@gmail.com"]
_PREAMBLE = (
    "set -euo pipefail; "
    f"cd {PROJECT_ROOT}; "
    'if [ -f "{0}/.env" ]; then set -a; '.format(PROJECT_ROOT)
    + 'while IFS= read -r line || [ -n "$line" ]; do '
    'case "$line" in ""|"#"*) continue;; *=*) export "$line" || true;; esac; '
    + f"done < <(tr -d '\\r' < \"{PROJECT_ROOT}/.env\"); set +a; fi; "
    + 'export POSTGRES_HOST="${POSTGRES_HOST/localhost/host.docker.internal}"; '
    'export MONGO_URI="${MONGO_URI//localhost/host.docker.internal}"; '
    f"export PYTHONPATH={PROJECT_ROOT}; "
    "export PYSPARK_PYTHON=/app/.venv/bin/python; "
    "export PYSPARK_DRIVER_PYTHON=/app/.venv/bin/python; "
    f"export DBT_PROFILES_DIR={PROJECT_ROOT}/dbt; "
)


def _register(dag_id, schedule):
    @dag(
        dag_id=dag_id,
        schedule=schedule,
        start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Kolkata"),
        catchup=False,
        max_active_runs=1,
        tags=["walmart", "medallion", "etl"],
        default_args={"retries": 1, "retry_delay": pendulum.duration(minutes=5)},
    )
    def _pipeline():
        @task.bash(task_id="preflight")
        def preflight() -> str:
            return _PREAMBLE + (
                "if [ ! -x /app/.venv/bin/python ]; then uv sync --frozen; fi; "
                'installed="$(/app/.venv/bin/python -c '
                "'import pyspark; print(pyspark.__version__)' 2>/dev/null || true)\"; "
                f'if [[ "$installed" != {REQUIRED_PYSPARK_PREFIX}* ]]; then '
                'echo "pyspark incompatible"; exit 1; '
                'else echo "pyspark $installed OK"; fi'
            )

        @task.bash(task_id="extract")
        def extract() -> str:
            return _PREAMBLE + "uv run python src/jobs/extract.py"

        @task.bash(task_id="bronze_sql_tests")
        def bronze_sql_tests() -> str:
            return (
                _PREAMBLE
                + "uv run python src/jobs/sql_test.py tests/data-quality/bronze"
            )

        @task.bash(task_id="dbt_silver_run")
        def dbt_silver_run() -> str:
            return _PREAMBLE + f"cd {DBT_PROJECT_DIR} && uv run dbt run --select silver"

        @task.bash(task_id="dbt_silver_test")
        def dbt_silver_test() -> str:
            return (
                _PREAMBLE + f"cd {DBT_PROJECT_DIR} && uv run dbt test --select silver"
            )

        @task.bash(task_id="silver_sql_tests")
        def silver_sql_tests() -> str:
            return (
                _PREAMBLE
                + "uv run python src/jobs/sql_test.py tests/data-quality/silver"
            )

        @task.bash(task_id="dbt_gold_run")
        def dbt_gold_run() -> str:
            return _PREAMBLE + f"cd {DBT_PROJECT_DIR} && uv run dbt run --select gold"

        @task.bash(task_id="dbt_gold_test")
        def dbt_gold_test() -> str:
            return _PREAMBLE + f"cd {DBT_PROJECT_DIR} && uv run dbt test --select gold"

        @task.bash(task_id="gold_sql_tests")
        def gold_sql_tests() -> str:
            return (
                _PREAMBLE + "uv run python src/jobs/sql_test.py tests/data-quality/gold"
            )

        @task.bash(task_id="great_expectations_tests")
        def great_expectations_tests() -> str:
            return _PREAMBLE + "uv run python -m gx.run --layer all"

        @task(task_id="collect_results", trigger_rule=TriggerRule.ALL_DONE)
        def collect_results(**context) -> dict:
            dag_run = context["dag_run"]
            run_id = dag_run.run_id
            logical_date = context.get("logical_date", None) or getattr(
                dag_run, "logical_date", None
            )
            execution_date = (
                logical_date.date().isoformat()
                if logical_date is not None
                else "unknown"
            )
            ti = context["ti"]
            stage_statuses: dict[str, str] = {}
            for stage_id in STAGE_TASK_IDS:
                try:
                    value = ti.xcom_pull(task_ids=stage_id)
                except Exception as exc:
                    print(f"collect_results: xcom_pull failed for {stage_id} ({exc})")
                    value = None
                stage_statuses[stage_id] = "success" if value is not None else "failed"
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
            ti = context["ti"]
            result = ti.xcom_pull(task_ids="collect_results") or {}
            if result.get("status") == "SUCCESS":
                return "email_success"
            return "email_failure"

        email_success = EmailOperator(
            task_id="email_success",
            to=EMAIL_RECIPIENTS,
            subject="Walmart Pipeline SUCCESS - {{ ds }}",
            html_content="""
<h2>Walmart Medallion Pipeline - SUCCESS</h2>
<p><strong>Date:</strong> {{ ds }}</p>
<p><strong>Run ID:</strong> {{ ti.xcom_pull(task_ids='collect_results')['run_id'] }}</p>
<h3>Stage Results</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
<tr style="background:#4CAF50;color:white;"><th>Stage</th><th>Status</th></tr>
{% for stage, status in ti.xcom_pull(task_ids='collect_results')['stages'].items() %}
<tr><td>{{ stage }}</td><td>{{ status | upper }}</td></tr>
{% endfor %}
</table>
<p><em>All stages completed. Data is ready in the gold layer.</em></p>
""",
            trigger_rule=TriggerRule.ALL_SUCCESS,
        )
        email_failure = EmailOperator(
            task_id="email_failure",
            to=EMAIL_RECIPIENTS,
            subject="Walmart Pipeline FAILED - {{ ds }}",
            html_content="""
<h2>Walmart Medallion Pipeline - FAILURE</h2>
<p><strong>Date:</strong> {{ ds }}</p>
<h3>Stage Results</h3>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
<tr style="background:#f44336;color:white;"><th>Stage</th><th>Status</th></tr>
{% set stages = ti.xcom_pull(task_ids='collect_results', default={'stages': {}})['stages'] %}
{% for stage, status in stages.items() %}
<tr><td>{{ stage }}</td><td>{{ status | upper }}</td></tr>
{% endfor %}
</table>
<p><em>Check Airflow logs for the failing task.</em></p>
""",
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
        results = collect_results()
        choice = choose_email()
        chain >> results >> choice >> [email_success, email_failure]

    return _pipeline()


walmart_mwf_morning = _register("walmart_mwf_morning", _MWF_SCHEDULE)
walmart_rest_night = _register("walmart_rest_night", _REST_SCHEDULE)
