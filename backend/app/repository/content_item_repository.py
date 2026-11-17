import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign
from app.models.content_item import ContentItem
from app.repository.base import SQLAlchemyRepository


class ContentItemRepository(SQLAlchemyRepository[ContentItem]):
    model = ContentItem

    async def get_detail(self, item_id: uuid.UUID) -> ContentItem | None:
        stmt = (
            select(ContentItem)
            .where(ContentItem.id == item_id)
            .options(
                selectinload(ContentItem.video),
                selectinload(ContentItem.publishing_jobs),
                selectinload(ContentItem.campaign),
            )
            .execution_options(populate_existing=True)
        )
        return await self.session.scalar(stmt)

    async def list_by_campaign(self, campaign_id: uuid.UUID) -> list[ContentItem]:
        stmt = (
            select(ContentItem)
            .where(ContentItem.campaign_id == campaign_id)
            .order_by(ContentItem.sequence_number)
        )
        return list((await self.session.scalars(stmt)).all())

    async def list_in_window(
        self, owner_id: uuid.UUID | None, start: datetime, end: datetime
    ) -> list[ContentItem]:
        stmt = (
            select(ContentItem)
            .join(Campaign)
            .where(ContentItem.scheduled_at >= start, ContentItem.scheduled_at < end)
            .options(selectinload(ContentItem.campaign))
            .order_by(ContentItem.scheduled_at)
        )
        if owner_id is not None:
            stmt = stmt.where(Campaign.owner_id == owner_id)
        return list((await self.session.scalars(stmt)).all())
