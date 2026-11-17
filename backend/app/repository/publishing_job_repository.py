import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign
from app.models.content_item import ContentItem
from app.models.enums import CampaignStatus, JobStatus, Platform
from app.models.publishing_job import PublishingJob
from app.repository.base import SQLAlchemyRepository


class PublishingJobRepository(SQLAlchemyRepository[PublishingJob]):
    model = PublishingJob

    async def get_for_item_platform(
        self, content_item_id: uuid.UUID, platform: Platform
    ) -> PublishingJob | None:
        stmt = select(PublishingJob).where(
            PublishingJob.content_item_id == content_item_id, PublishingJob.platform == platform
        )
        return await self.session.scalar(stmt)

    async def list_for_item(self, content_item_id: uuid.UUID) -> list[PublishingJob]:
        stmt = select(PublishingJob).where(PublishingJob.content_item_id == content_item_id)
        return list((await self.session.scalars(stmt)).all())

    async def claim_due(self, now: datetime, limit: int = 50) -> list[PublishingJob]:
        """Lock due jobs (SKIP LOCKED on Postgres) so concurrent dispatchers never double-publish."""
        paused = select(Campaign.id).where(Campaign.status == CampaignStatus.PAUSED)
        stmt = (
            select(PublishingJob)
            .join(ContentItem)
            .where(
                PublishingJob.status == JobStatus.SCHEDULED,
                PublishingJob.scheduled_at <= now,
                ContentItem.campaign_id.not_in(paused),
            )
            .order_by(PublishingJob.scheduled_at)
            .limit(limit)
        )
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True, of=PublishingJob)
        jobs = list((await self.session.scalars(stmt)).all())
        for job in jobs:
            job.status = JobStatus.IN_PROGRESS
        await self.session.flush()
        return jobs

    async def list_published(
        self, owner_id: uuid.UUID | None = None, limit: int = 500
    ) -> list[PublishingJob]:
        stmt = (
            select(PublishingJob)
            .join(ContentItem)
            .join(Campaign)
            .where(PublishingJob.status == JobStatus.PUBLISHED, PublishingJob.external_id.is_not(None))
            .options(selectinload(PublishingJob.platform_account))
            .order_by(PublishingJob.published_at.desc())
            .limit(limit)
        )
        if owner_id is not None:
            stmt = stmt.where(Campaign.owner_id == owner_id)
        return list((await self.session.scalars(stmt)).all())

    async def count_by_status(self, owner_id: uuid.UUID | None) -> dict[JobStatus, int]:
        stmt = (
            select(PublishingJob.status, func.count(PublishingJob.id))
            .join(ContentItem)
            .join(Campaign)
            .group_by(PublishingJob.status)
        )
        if owner_id is not None:
            stmt = stmt.where(Campaign.owner_id == owner_id)
        return {status: int(n) for status, n in (await self.session.execute(stmt)).all()}
