from datetime import UTC, date, datetime, timedelta

from app.core.logging import get_logger
from app.models.analytics import AnalyticsSnapshot
from app.models.enums import JobStatus, Platform
from app.models.user import User
from app.repository.analytics_repository import METRICS
from app.repository.unit_of_work import UnitOfWork
from app.schemas.analytics import (
    AnalyticsSummary,
    CampaignAnalytics,
    MetricTotals,
    PlatformBreakdown,
    TimeseriesPoint,
    TopContent,
)
from app.services.campaign_service import CampaignService, scope_owner
from app.services.integrations.instagram import InstagramClient
from app.services.integrations.youtube import YouTubeClient
from app.services.platform_account_service import PlatformAccountService

logger = get_logger(__name__)


def _totals(snapshots: list[AnalyticsSnapshot]) -> MetricTotals:
    return MetricTotals(**{m: sum(getattr(s, m) for s in snapshots) for m in METRICS})


class AnalyticsService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def summary(self, user: User) -> AnalyticsSummary:
        owner = scope_owner(user)
        latest = await self._uow.analytics.latest_by_job(owner_id=owner)
        counts = await self._uow.publishing_jobs.count_by_status(owner)
        by_platform = []
        for platform in Platform:
            snaps = [s for s in latest if s.platform == platform]
            by_platform.append(
                PlatformBreakdown(
                    platform=platform,
                    published_count=len({s.publishing_job_id for s in snaps}),
                    **_totals(snaps).model_dump(),
                )
            )
        return AnalyticsSummary(
            totals=_totals(latest),
            published_count=counts.get(JobStatus.PUBLISHED, 0),
            scheduled_count=counts.get(JobStatus.SCHEDULED, 0) + counts.get(JobStatus.IN_PROGRESS, 0),
            failed_count=counts.get(JobStatus.FAILED, 0),
            campaign_count=await self._uow.campaigns.count_for_owner(owner),
            by_platform=by_platform,
        )

    async def timeseries(self, user: User, days: int = 30) -> list[TimeseriesPoint]:
        start = datetime.now(UTC).date() - timedelta(days=days)
        rows = await self._uow.analytics.daily_series(scope_owner(user), None, start)
        return [self._point(r) for r in rows]

    async def campaign(
        self, user: User, campaign_service: CampaignService, campaign_id, days: int = 30
    ) -> CampaignAnalytics:
        campaign = await campaign_service.get(user, campaign_id)
        latest = await self._uow.analytics.latest_by_job(campaign_id=campaign.id)
        start = datetime.now(UTC).date() - timedelta(days=days)
        rows = await self._uow.analytics.daily_series(None, campaign.id, start)
        top: list[TopContent] = []
        for snap in sorted(latest, key=lambda s: s.views, reverse=True)[:10]:
            job = await self._uow.publishing_jobs.get(snap.publishing_job_id)
            item = await self._uow.content_items.get(job.content_item_id) if job else None
            if job is None or item is None:
                continue
            top.append(
                TopContent(
                    content_item_id=item.id,
                    title=(item.seo or {}).get("title") or item.subtopic or f"Short #{item.sequence_number}",
                    platform=snap.platform,
                    external_url=job.external_url,
                    **{m: getattr(snap, m) for m in METRICS},
                )
            )
        return CampaignAnalytics(
            campaign_id=campaign.id,
            totals=_totals(latest),
            timeseries=[self._point(r) for r in rows],
            top_content=top,
        )

    @staticmethod
    def _point(row: dict) -> TimeseriesPoint:
        day = row["day"]
        if isinstance(day, str):
            day = date.fromisoformat(day[:10])
        elif isinstance(day, datetime):
            day = day.date()
        return TimeseriesPoint(day=day, **{m: int(row[m] or 0) for m in METRICS})


class AnalyticsCollector:
    """Pulls engagement metrics from YouTube/Instagram for published jobs and stores snapshots."""

    def __init__(
        self,
        uow: UnitOfWork,
        accounts: PlatformAccountService,
        youtube: YouTubeClient,
        instagram: InstagramClient,
    ) -> None:
        self._uow = uow
        self._accounts = accounts
        self._youtube = youtube
        self._instagram = instagram

    async def collect(self) -> int:
        jobs = await self._uow.publishing_jobs.list_published()
        stored = 0
        for job in jobs:
            external_id = job.external_id
            if job.platform_account is None or not external_id or external_id.startswith("dryrun-"):
                continue
            try:
                creds = await self._accounts.credentials_for(job.platform_account)
                if job.platform == Platform.YOUTUBE:
                    metrics = (await self._youtube.get_statistics(creds.access_token, [external_id])).get(
                        external_id, {}
                    )
                else:
                    metrics = await self._instagram.get_insights(creds.access_token, external_id)
            except Exception as exc:
                logger.warning("analytics.collect_failed", job_id=str(job.id), error=str(exc))
                continue
            if not metrics:
                continue
            await self._uow.analytics.add(
                AnalyticsSnapshot(
                    publishing_job_id=job.id,
                    platform=job.platform,
                    views=metrics.get("views", 0),
                    likes=metrics.get("likes", 0),
                    comments=metrics.get("comments", 0),
                    shares=metrics.get("shares", 0),
                    watch_time_seconds=metrics.get("watch_time_seconds", 0),
                    raw=metrics,
                )
            )
            stored += 1
        await self._uow.commit()
        logger.info("analytics.collected", snapshots=stored)
        return stored
