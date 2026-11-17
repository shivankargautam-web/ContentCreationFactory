import uuid

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.content_item import ContentItem
from app.models.enums import ContentStatus, UserRole
from app.models.user import User
from app.repository.unit_of_work import UnitOfWork
from app.services.dispatcher import TaskDispatcher
from app.services.integrations.storage import ObjectStorage


class ContentService:
    def __init__(self, uow: UnitOfWork, dispatcher: TaskDispatcher, storage: ObjectStorage) -> None:
        self._uow = uow
        self._dispatcher = dispatcher
        self._storage = storage

    async def get(self, user: User, item_id: uuid.UUID) -> ContentItem:
        item = await self._uow.content_items.get_detail(item_id)
        if item is None:
            raise NotFoundError("Content item not found")
        if user.role != UserRole.ADMIN and item.campaign.owner_id != user.id:
            raise AuthorizationError("You do not have access to this content item")
        return item

    async def regenerate(self, user: User, item_id: uuid.UUID) -> ContentItem:
        item = await self.get(user, item_id)
        if item.status in {ContentStatus.PUBLISHED, ContentStatus.PUBLISHING, ContentStatus.GENERATING}:
            raise ValidationError(f"Cannot regenerate an item that is {item.status.value}")
        item.status = ContentStatus.PENDING
        item.error = None
        await self._uow.commit()
        self._dispatcher.enqueue_generation(item.id)
        return await self.get(user, item_id)

    async def video_url(self, user: User, item_id: uuid.UUID) -> str:
        item = await self.get(user, item_id)
        if item.video is None or not item.video.video_key:
            raise NotFoundError("Video has not been rendered yet")
        return await self._storage.url_for(item.video.video_key)
