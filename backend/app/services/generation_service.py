"""Runs the multi-agent pipeline for one content item and persists its artifacts."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.agents.publisher_agent import PublishingGateway
from app.agents.state import ContentState
from app.core.logging import get_logger
from app.models.enums import CampaignStatus, ContentStatus, JobStatus, VideoStatus
from app.models.video import Video
from app.repository.unit_of_work import UnitOfWork
from app.services.publishing_service import PublishingService
from app.workflows.content_pipeline import ContentPipeline

logger = get_logger(__name__)
PipelineFactory = Callable[[PublishingGateway], ContentPipeline]


class ContentGenerationService:
    def __init__(
        self, uow: UnitOfWork, pipeline_factory: PipelineFactory, publishing: PublishingService
    ) -> None:
        self._uow = uow
        self._pipeline_factory = pipeline_factory
        self._publishing = publishing

    async def generate(self, content_item_id: uuid.UUID) -> ContentState | None:
        item = await self._uow.content_items.get_detail(content_item_id)
        if item is None:
            logger.warning("generation.item_missing", content_item_id=str(content_item_id))
            return None
        if item.status not in {ContentStatus.PENDING, ContentStatus.FAILED}:
            logger.info("generation.skipped", content_item_id=str(item.id), status=item.status.value)
            return None
        campaign = item.campaign
        item.status = ContentStatus.GENERATING
        item.error = None
        if campaign.status in {CampaignStatus.DRAFT, CampaignStatus.FAILED}:
            campaign.status = CampaignStatus.GENERATING
        await self._uow.commit()

        state: ContentState = {
            "content_item_id": str(item.id),
            "campaign_id": str(campaign.id),
            "topic": campaign.topic,
            "subtopic": item.subtopic or campaign.topic,
            "sequence_number": item.sequence_number,
            "total_items": campaign.total_items,
            "tone": campaign.tone,
            "target_audience": campaign.target_audience,
            "platforms": list(campaign.platforms),
            "scheduled_at": item.scheduled_at.isoformat(),
        }
        log = logger.bind(content_item_id=str(item.id), campaign_id=str(campaign.id))
        try:
            result = await self._pipeline_factory(_Gateway(self._uow, self._publishing)).run(state)
        except Exception as exc:
            log.exception("generation.failed")
            await self._uow.rollback()
            item = await self._uow.content_items.get_detail(content_item_id)
            if item is not None:
                item.status = ContentStatus.FAILED
                item.error = f"{type(exc).__name__}: {exc}"[:2000]
                await self._uow.campaigns.refresh_status(item.campaign)
                await self._uow.commit()
            raise
        log.info("generation.completed", trace=result.get("trace"))
        return result


class _Gateway:
    """PublishingGateway adapter: persists agent output then schedules or immediately publishes."""

    def __init__(self, uow: UnitOfWork, publishing: PublishingService) -> None:
        self._uow = uow
        self._publishing = publishing

    async def handoff(self, state: ContentState) -> list[dict[str, Any]]:
        item = await self._uow.content_items.get_detail(uuid.UUID(state["content_item_id"]))
        if item is None:
            raise RuntimeError("Content item disappeared during generation")
        item.research = state.get("research")
        item.script = state.get("script")
        item.seo = state.get("seo")

        video_data = state.get("video") or {}
        video = item.video or await self._uow.videos.get_by_content_item(item.id)
        if video is None:
            video = Video(content_item_id=item.id)
            item.video = video
        video.status = VideoStatus.READY if video_data.get("video_key") else VideoStatus.FAILED
        video.storyboard = video_data.get("storyboard", [])
        video.captions_srt = video_data.get("captions_srt")
        video.audio_key = video_data.get("audio_key")
        video.video_key = video_data.get("video_key")
        video.duration_seconds = video_data.get("duration_seconds")

        item.status = ContentStatus.READY
        jobs = await self._publishing.schedule_jobs(item, item.campaign.owner_id, state.get("platforms", []))
        await self._uow.campaigns.refresh_status(item.campaign)
        await self._uow.commit()

        now = datetime.now(UTC)
        results: list[dict[str, Any]] = []
        for job in jobs:
            scheduled = job.scheduled_at if job.scheduled_at.tzinfo else job.scheduled_at.replace(tzinfo=UTC)
            if job.status == JobStatus.SCHEDULED and scheduled <= now:
                job = await self._publishing.publish(job.id) or job
            results.append(
                {
                    "job_id": str(job.id),
                    "platform": job.platform.value,
                    "status": job.status.value,
                    "scheduled_at": job.scheduled_at.isoformat(),
                    "external_url": job.external_url,
                }
            )
        return results
