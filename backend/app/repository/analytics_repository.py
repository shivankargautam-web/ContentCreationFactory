import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, and_, func, select

from app.models.analytics import AnalyticsSnapshot
from app.models.campaign import Campaign
from app.models.content_item import ContentItem
from app.models.publishing_job import PublishingJob
from app.repository.base import SQLAlchemyRepository

METRICS = ("views", "likes", "comments", "shares", "watch_time_seconds")


class AnalyticsRepository(SQLAlchemyRepository[AnalyticsSnapshot]):
    """Snapshots hold cumulative counters, so aggregates use the latest snapshot per job."""

    model = AnalyticsSnapshot

    def _latest_snapshot_ids(
        self, owner_id: uuid.UUID | None, campaign_id: uuid.UUID | None, until: datetime | None = None
    ) -> Select[Any]:
        latest = (
            select(AnalyticsSnapshot.publishing_job_id, func.max(AnalyticsSnapshot.collected_at).label("ts"))
            .join(PublishingJob)
            .join(ContentItem)
            .join(Campaign)
            .group_by(AnalyticsSnapshot.publishing_job_id)
        )
        if owner_id is not None:
            latest = latest.where(Campaign.owner_id == owner_id)
        if campaign_id is not None:
            latest = latest.where(Campaign.id == campaign_id)
        if until is not None:
            latest = latest.where(AnalyticsSnapshot.collected_at <= until)
        return latest

    async def latest_by_job(
        self, owner_id: uuid.UUID | None = None, campaign_id: uuid.UUID | None = None
    ) -> list[AnalyticsSnapshot]:
        latest = self._latest_snapshot_ids(owner_id, campaign_id).subquery()
        stmt = select(AnalyticsSnapshot).join(
            latest,
            and_(
                AnalyticsSnapshot.publishing_job_id == latest.c.publishing_job_id,
                AnalyticsSnapshot.collected_at == latest.c.ts,
            ),
        )
        return list((await self.session.scalars(stmt)).all())

    async def daily_series(
        self, owner_id: uuid.UUID | None, campaign_id: uuid.UUID | None, start: date
    ) -> list[dict[str, Any]]:
        """Per-day totals using each job's last snapshot of that day."""
        day = func.date(AnalyticsSnapshot.collected_at)
        per_day = (
            select(
                AnalyticsSnapshot.publishing_job_id.label("job_id"),
                day.label("day"),
                func.max(AnalyticsSnapshot.collected_at).label("ts"),
            )
            .join(PublishingJob)
            .join(ContentItem)
            .join(Campaign)
            .where(AnalyticsSnapshot.collected_at >= start)
            .group_by(AnalyticsSnapshot.publishing_job_id, day)
        )
        if owner_id is not None:
            per_day = per_day.where(Campaign.owner_id == owner_id)
        if campaign_id is not None:
            per_day = per_day.where(Campaign.id == campaign_id)
        sub = per_day.subquery()
        stmt = (
            select(sub.c.day, *[func.sum(getattr(AnalyticsSnapshot, m)).label(m) for m in METRICS])
            .join(
                sub,
                and_(
                    AnalyticsSnapshot.publishing_job_id == sub.c.job_id,
                    AnalyticsSnapshot.collected_at == sub.c.ts,
                ),
            )
            .group_by(sub.c.day)
            .order_by(sub.c.day)
        )
        rows = (await self.session.execute(stmt)).mappings().all()
        return [dict(r) for r in rows]
