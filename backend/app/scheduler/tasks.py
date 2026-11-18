"""Celery tasks. Each task runs its async body on a per-process event loop with a fresh transaction."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.container import get_container
from app.core.logging import get_logger
from app.repository.unit_of_work import UnitOfWork
from app.scheduler.celery_app import celery_app

logger = get_logger(__name__)
T = TypeVar("T")
_loop: asyncio.AbstractEventLoop | None = None


def run_async(coro: Awaitable[T]) -> T:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop.run_until_complete(coro)


async def _with_uow(fn: Callable[[UnitOfWork], Awaitable[T]]) -> T:
    container = get_container()
    async with container.database.session_factory() as session:
        return await fn(UnitOfWork(session))


@celery_app.task(name="acf.generate_content", bind=True, max_retries=2, default_retry_delay=60)
def generate_content(self: Any, content_item_id: str) -> dict[str, Any]:
    container = get_container()
    try:
        state = run_async(
            _with_uow(lambda uow: container.generation_service(uow).generate(uuid.UUID(content_item_id)))
        )
    except Exception as exc:
        logger.warning("task.generate_content.failed", content_item_id=content_item_id, error=str(exc))
        raise self.retry(exc=exc) from exc
    return {"content_item_id": content_item_id, "trace": (state or {}).get("trace", [])}


@celery_app.task(name="acf.publish_job", bind=True, max_retries=0)
def publish_job(self: Any, publishing_job_id: str) -> dict[str, Any]:
    container = get_container()
    job = run_async(
        _with_uow(lambda uow: container.publishing_service(uow).publish(uuid.UUID(publishing_job_id)))
    )
    return {"publishing_job_id": publishing_job_id, "status": job.status.value if job else None}


@celery_app.task(name="acf.dispatch_due_jobs")
def dispatch_due_jobs() -> int:
    container = get_container()
    job_ids = run_async(_with_uow(lambda uow: container.publishing_service(uow).claim_due()))
    for job_id in job_ids:
        container.dispatcher.enqueue_publish(job_id)
    if job_ids:
        logger.info("task.dispatch_due_jobs", count=len(job_ids))
    return len(job_ids)


@celery_app.task(name="acf.collect_analytics")
def collect_analytics() -> int:
    container = get_container()
    return run_async(_with_uow(lambda uow: container.analytics_collector(uow).collect()))
