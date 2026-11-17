import uuid
from datetime import datetime
from typing import Any

from app.models.enums import ContentStatus, JobStatus, Platform, VideoStatus
from app.schemas.common import ORMModel


class VideoRead(ORMModel):
    id: uuid.UUID
    status: VideoStatus
    storyboard: list[dict[str, Any]]
    captions_srt: str | None
    video_key: str | None
    audio_key: str | None
    duration_seconds: float | None
    error: str | None


class PublishingJobRead(ORMModel):
    id: uuid.UUID
    content_item_id: uuid.UUID
    platform: Platform
    status: JobStatus
    scheduled_at: datetime
    published_at: datetime | None
    external_id: str | None
    external_url: str | None
    attempts: int
    last_error: str | None


class ContentItemRead(ORMModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    sequence_number: int
    subtopic: str | None
    status: ContentStatus
    scheduled_at: datetime
    research: dict[str, Any] | None
    script: dict[str, Any] | None
    seo: dict[str, Any] | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class ContentItemDetail(ContentItemRead):
    video: VideoRead | None = None
    publishing_jobs: list[PublishingJobRead] = []
