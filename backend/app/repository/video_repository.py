import uuid

from sqlalchemy import select

from app.models.video import Video
from app.repository.base import SQLAlchemyRepository


class VideoRepository(SQLAlchemyRepository[Video]):
    model = Video

    async def get_by_content_item(self, content_item_id: uuid.UUID) -> Video | None:
        return await self.session.scalar(select(Video).where(Video.content_item_id == content_item_id))
