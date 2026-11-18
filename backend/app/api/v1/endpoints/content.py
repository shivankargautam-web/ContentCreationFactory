import uuid

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.deps import ContentServiceDep, CurrentUser, EditorUser
from app.schemas.content import ContentItemDetail

router = APIRouter()


class VideoUrl(BaseModel):
    url: str


@router.get("/{item_id}", response_model=ContentItemDetail)
async def get_content_item(
    item_id: uuid.UUID, user: CurrentUser, service: ContentServiceDep
) -> ContentItemDetail:
    return ContentItemDetail.model_validate(await service.get(user, item_id))


@router.post("/{item_id}/regenerate", response_model=ContentItemDetail, status_code=status.HTTP_202_ACCEPTED)
async def regenerate(item_id: uuid.UUID, user: EditorUser, service: ContentServiceDep) -> ContentItemDetail:
    return ContentItemDetail.model_validate(await service.regenerate(user, item_id))


@router.get("/{item_id}/video-url", response_model=VideoUrl)
async def video_url(item_id: uuid.UUID, user: CurrentUser, service: ContentServiceDep) -> VideoUrl:
    return VideoUrl(url=await service.video_url(user, item_id))
