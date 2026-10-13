# Walmart hourly health check: postgres + mongo with failure mail
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

    _SCHEDULE = CronTriggerTimetable("0 * * * *", timezone="Asia/Kolkata")
except Exception:
    _SCHEDULE = "0 * * * *"
PROJECT_ROOT = "/app"
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
)


@dag(
    dag_id="walmart_hourly_health_check",
    schedule=_SCHEDULE,
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Kolkata"),
    catchup=False,
    max_active_runs=1,
    tags=["walmart", "health", "monitoring"],
    default_args={"retries": 1, "retry_delay": pendulum.duration(minutes=5)},
)
def walmart_hourly_health_check():
    @task.bash(task_id="postgres_check")
    def postgres_check() -> str:
        return _PREAMBLE + (
            "uv run python -c "
            '"from src.utils.connection import get_postgres_engine; '
            "from sqlalchemy import text; "
            "e=get_postgres_engine(); "
            "with e.connect() as c: c.execute(text('SELECT 1')); "
            "print('postgres OK')\""
        )

    @task.bash(task_id="mongo_check")
    def mongo_check() -> str:
        return _PREAMBLE + (
            "uv run python -c "
            '"from src.utils.connection import get_mongo_db; '
            "db=get_mongo_db(); "
            "db.command('ping'); "
            "print('mongo OK')\""
        )

    email_failure = EmailOperator(
        task_id="email_failure",
        to=EMAIL_RECIPIENTS,
        subject="Walmart Health Check FAILED - {{ ds }} {{ ti.hostname }}",
        html_content="""
<h2>Walmart Hourly Health Check - FAILURE</h2>
<p><strong>Date:</strong> {{ ds }} {{ data_interval_start }}</p>
<p><em>Postgres or Mongo ping failed. Check task logs.</em></p>
""",
        trigger_rule=TriggerRule.ONE_FAILED,
    )
    [postgres_check(), mongo_check()] >> email_failure


walmart_hourly_health_check()
