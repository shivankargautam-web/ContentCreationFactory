from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.analytics_repository import AnalyticsRepository
from app.repository.campaign_repository import CampaignRepository
from app.repository.content_item_repository import ContentItemRepository
from app.repository.platform_account_repository import PlatformAccountRepository
from app.repository.publishing_job_repository import PublishingJobRepository
from app.repository.user_repository import UserRepository
from app.repository.video_repository import VideoRepository


class UnitOfWork:
    """Groups repositories that share one transaction (session)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.campaigns = CampaignRepository(session)
        self.content_items = ContentItemRepository(session)
        self.videos = VideoRepository(session)
        self.platform_accounts = PlatformAccountRepository(session)
        self.publishing_jobs = PublishingJobRepository(session)
        self.analytics = AnalyticsRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
