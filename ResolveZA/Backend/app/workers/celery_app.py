from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Create the Celery app
# ---------------------------------------------------------------------------
celery_app = Celery(
    "resolveza",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.sla_worker",
        "app.workers.notification_worker",
    ],
)

# ---------------------------------------------------------------------------
# Celery configuration
# ---------------------------------------------------------------------------
celery_app.conf.update(
    # Serialise tasks as JSON (not pickle — pickle is a security risk)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="Africa/Johannesburg",
    enable_utc=True,

    # Retry failed tasks up to 3 times with exponential backoff
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result expiry — don't keep task results forever
    result_expires=3600,  # 1 hour
)

# ---------------------------------------------------------------------------
# Periodic task schedule (Celery Beat)
# ---------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "check-sla-breaches": {
        "task": "app.workers.sla_worker.check_sla_breaches",
        "schedule": 300.0,  # every 5 minutes (300 seconds)
    },
}