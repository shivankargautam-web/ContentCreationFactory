"""Abstraction over the async task queue so services don't depend on Celery directly."""

import uuid
from typing import Protocol


class TaskDispatcher(Protocol):
    def enqueue_generation(self, content_item_id: uuid.UUID) -> None: ...
    def enqueue_publish(self, publishing_job_id: uuid.UUID) -> None: ...


class CeleryTaskDispatcher:
    def enqueue_generation(self, content_item_id: uuid.UUID) -> None:
        from app.scheduler.celery_app import celery_app

        celery_app.send_task("acf.generate_content", args=[str(content_item_id)], queue="generation")

    def enqueue_publish(self, publishing_job_id: uuid.UUID) -> None:
        from app.scheduler.celery_app import celery_app

        celery_app.send_task("acf.publish_job", args=[str(publishing_job_id)], queue="publishing")


class InMemoryTaskDispatcher:
    """Records dispatched tasks (tests / dry runs)."""

    def __init__(self) -> None:
        self.generation: list[uuid.UUID] = []
        self.publish: list[uuid.UUID] = []

    def enqueue_generation(self, content_item_id: uuid.UUID) -> None:
        self.generation.append(content_item_id)

    def enqueue_publish(self, publishing_job_id: uuid.UUID) -> None:
        self.publish.append(publishing_job_id)
