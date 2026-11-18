from celery import Celery
from celery.signals import worker_process_init
from kombu import Queue

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.telemetry import instrument_celery

settings = get_settings()
configure_logging(settings.log_level, settings.log_json)

celery_app = Celery(
    "acf", broker=settings.broker_url, backend=settings.result_backend, include=["app.scheduler.tasks"]
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.celery_task_always_eager,
    task_default_queue="default",
    task_queues=(Queue("default"), Queue("generation"), Queue("publishing"), Queue("analytics")),
    task_routes={
        "acf.generate_content": {"queue": "generation"},
        "acf.publish_job": {"queue": "publishing"},
        "acf.dispatch_due_jobs": {"queue": "publishing"},
        "acf.collect_analytics": {"queue": "analytics"},
    },
    beat_schedule={
        "dispatch-due-publishing-jobs": {
            "task": "acf.dispatch_due_jobs",
            "schedule": float(settings.publish_dispatch_interval_seconds),
        },
        "collect-analytics": {
            "task": "acf.collect_analytics",
            "schedule": float(settings.analytics_sync_interval_seconds),
        },
    },
    result_expires=60 * 60 * 24,
)


@worker_process_init.connect
def _init_worker(**_: object) -> None:
    instrument_celery(settings)
