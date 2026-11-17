"""Creates publishing jobs and executes them against platform publishers."""

import uuid
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.models.content_item import ContentItem
from app.models.enums import CampaignStatus, ContentStatus, JobStatus, Platform
from app.models.publishing_job import PublishingJob
from app.repository.unit_of_work import UnitOfWork
from app.services.integrations.publishers import PlatformCredentials, PublisherRegistry, PublishRequest
from app.services.platform_account_service import PlatformAccountService

logger = get_logger(__name__)
MAX_ATTEMPTS = 3


class PublishingService:
    def __init__(
        self,
        uow: UnitOfWork,
        registry: PublisherRegistry,
        accounts: PlatformAccountService,
        dry_run: bool = False,
    ) -> None:
        self._uow = uow
        self._registry = registry
        self._accounts = accounts
        self._dry_run = dry_run

    async def schedule_jobs(
        self, item: ContentItem, owner_id: uuid.UUID, platforms: list[str]
    ) -> list[PublishingJob]:
        """Idempotently ensure one job per platform for a content item."""
        jobs: list[PublishingJob] = []
        for name in platforms:
            platform = Platform(name)
            job = await self._uow.publishing_jobs.get_for_item_platform(item.id, platform)
            account = await self._uow.platform_accounts.get_active_for_platform(owner_id, platform)
            if job is None:
                job = await self._uow.publishing_jobs.add(
                    PublishingJob(
                        content_item_id=item.id,
                        platform=platform,
                        platform_account_id=account.id if account else None,
                        scheduled_at=item.scheduled_at,
                        status=JobStatus.SCHEDULED,
                        attempts=0,
                    )
                )
            elif job.status in {JobStatus.FAILED, JobStatus.CANCELLED}:
                job.status = JobStatus.SCHEDULED
                job.platform_account_id = account.id if account else job.platform_account_id
                job.scheduled_at = item.scheduled_at
                job.last_error = None
            jobs.append(job)
        await self._uow.session.flush()
        return jobs

    async def claim_due(self, now: datetime | None = None, limit: int = 50) -> list[uuid.UUID]:
        jobs = await self._uow.publishing_jobs.claim_due(now or datetime.now(UTC), limit)
        await self._uow.commit()
        return [job.id for job in jobs]

    async def publish(self, job_id: uuid.UUID) -> PublishingJob | None:
        job = await self._uow.publishing_jobs.get(job_id)
        if job is None or job.status in {JobStatus.PUBLISHED, JobStatus.CANCELLED}:
            return job
        item = await self._uow.content_items.get_detail(job.content_item_id)
        if item is None:
            return None
        if item.campaign.status == CampaignStatus.PAUSED:
            job.status = JobStatus.SCHEDULED
            await self._uow.commit()
            return job

        job.status = JobStatus.IN_PROGRESS
        job.attempts += 1
        item.status = ContentStatus.PUBLISHING
        await self._uow.commit()
        log = logger.bind(job_id=str(job.id), platform=job.platform.value)

        try:
            if item.video is None or not item.video.video_key or not item.seo:
                raise RuntimeError("Content is not ready: missing rendered video or SEO metadata")
            credentials = await self._resolve_credentials(job, item.campaign.owner_id)
            seo = item.seo
            request = PublishRequest(
                video_key=item.video.video_key,
                title=seo["title"],
                description=seo["description"],
                caption=f"{seo['title']}\n\n{seo['description']}\n\n{' '.join(seo.get('hashtags', []))}",
                tags=list(seo.get("hashtags", [])) + list(seo.get("tags", [])),
            )
            publisher = self._registry.get(job.platform)
            result = await publisher.publish(credentials, request)
        except Exception as exc:
            job.last_error = str(exc)[:2000]
            job.status = JobStatus.SCHEDULED if job.attempts < MAX_ATTEMPTS else JobStatus.FAILED
            log.warning("publish.failed", attempt=job.attempts, error=str(exc))
        else:
            job.status = JobStatus.PUBLISHED
            job.external_id = result.external_id
            job.external_url = result.url
            job.published_at = datetime.now(UTC)
            job.last_error = None
            log.info("publish.succeeded", external_id=result.external_id)

        await self._sync_item_status(item)
        await self._uow.campaigns.refresh_status(item.campaign)
        await self._uow.commit()
        return job

    async def _resolve_credentials(self, job: PublishingJob, owner_id: uuid.UUID) -> PlatformCredentials:
        account = None
        if job.platform_account_id:
            account = await self._uow.platform_accounts.get(job.platform_account_id)
        if account is None:
            account = await self._uow.platform_accounts.get_active_for_platform(owner_id, job.platform)
            job.platform_account_id = account.id if account else None
        if account is None:
            if self._dry_run:
                return PlatformCredentials(access_token="dry-run", external_account_id="dry-run")
            raise RuntimeError(f"No connected {job.platform.value} account. Connect one in Settings.")
        return await self._accounts.credentials_for(account)

    async def _sync_item_status(self, item: ContentItem) -> None:
        jobs = await self._uow.publishing_jobs.list_for_item(item.id)
        statuses = {j.status for j in jobs}
        if statuses and statuses <= {JobStatus.PUBLISHED}:
            item.status = ContentStatus.PUBLISHED
        elif JobStatus.FAILED in statuses and not statuses & {JobStatus.SCHEDULED, JobStatus.IN_PROGRESS}:
            item.status = ContentStatus.PUBLISHED if JobStatus.PUBLISHED in statuses else ContentStatus.FAILED
            failed = [j for j in jobs if j.status == JobStatus.FAILED]
            item.error = "; ".join(f"{j.platform.value}: {j.last_error}" for j in failed)[:2000]
        else:
            item.status = ContentStatus.READY
