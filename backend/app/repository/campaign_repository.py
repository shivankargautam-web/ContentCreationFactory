import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign
from app.models.content_item import ContentItem
from app.models.enums import CampaignStatus
from app.repository.base import SQLAlchemyRepository


class CampaignRepository(SQLAlchemyRepository[Campaign]):
    model = Campaign

    async def get_with_items(self, campaign_id: uuid.UUID) -> Campaign | None:
        stmt = (
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .options(selectinload(Campaign.content_items))
            .execution_options(populate_existing=True)
        )
        return await self.session.scalar(stmt)

    async def list_for_owner(
        self,
        owner_id: uuid.UUID | None,
        status: CampaignStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Campaign], int]:
        stmt = select(Campaign).order_by(Campaign.created_at.desc())
        if owner_id is not None:
            stmt = stmt.where(Campaign.owner_id == owner_id)
        if status is not None:
            stmt = stmt.where(Campaign.status == status)
        return await self._paginate(stmt, limit, offset)

    async def count_for_owner(self, owner_id: uuid.UUID | None) -> int:
        stmt = select(func.count(Campaign.id))
        if owner_id is not None:
            stmt = stmt.where(Campaign.owner_id == owner_id)
        return int(await self.session.scalar(stmt) or 0)

    async def refresh_status(self, campaign: Campaign) -> Campaign:
        """Derive aggregate campaign status from its content items."""
        from app.models.enums import ContentStatus

        await self.session.flush()
        rows = await self.session.execute(
            select(ContentItem.status, func.count())
            .where(ContentItem.campaign_id == campaign.id)
            .group_by(ContentItem.status)
        )
        counts = {status: n for status, n in rows.all()}
        total = sum(counts.values())
        if campaign.status == CampaignStatus.PAUSED or total == 0:
            return campaign
        if counts.get(ContentStatus.PUBLISHED, 0) == total:
            campaign.status = CampaignStatus.COMPLETED
        elif counts.get(ContentStatus.FAILED, 0) == total:
            campaign.status = CampaignStatus.FAILED
        elif counts.get(ContentStatus.PENDING, 0) + counts.get(ContentStatus.GENERATING, 0) > 0:
            campaign.status = CampaignStatus.GENERATING
        else:
            campaign.status = CampaignStatus.SCHEDULED
        await self.session.flush()
        return campaign
