import uuid
from datetime import datetime

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CampaignServiceDep, CurrentUser, EditorUser
from app.models.enums import CampaignStatus
from app.schemas.campaign import (
    CalendarEvent,
    CampaignCreate,
    CampaignDetail,
    CampaignRead,
    CampaignStatusUpdate,
)
from app.schemas.common import Page

router = APIRouter()


@router.post("", response_model=CampaignDetail, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate, user: EditorUser, service: CampaignServiceDep
) -> CampaignDetail:
    """Create a campaign from a natural-language instruction and queue generation of every short."""
    return CampaignDetail.model_validate(await service.create(user, payload))


@router.get("", response_model=Page[CampaignRead])
async def list_campaigns(
    user: CurrentUser,
    service: CampaignServiceDep,
    status_filter: CampaignStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Page[CampaignRead]:
    items, total = await service.list_campaigns(user, status_filter, limit, offset)
    return Page(
        items=[CampaignRead.model_validate(c) for c in items], total=total, limit=limit, offset=offset
    )


@router.get("/calendar", response_model=list[CalendarEvent])
async def calendar(
    user: CurrentUser, service: CampaignServiceDep, start: datetime = Query(...), end: datetime = Query(...)
) -> list[CalendarEvent]:
    return await service.calendar(user, start, end)


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: uuid.UUID, user: CurrentUser, service: CampaignServiceDep
) -> CampaignDetail:
    return CampaignDetail.model_validate(await service.get(user, campaign_id))


@router.patch("/{campaign_id}/status", response_model=CampaignDetail)
async def update_status(
    campaign_id: uuid.UUID, payload: CampaignStatusUpdate, user: EditorUser, service: CampaignServiceDep
) -> CampaignDetail:
    return CampaignDetail.model_validate(await service.update_status(user, campaign_id, payload.status))


@router.post("/{campaign_id}/generate", response_model=CampaignDetail, status_code=status.HTTP_202_ACCEPTED)
async def generate(campaign_id: uuid.UUID, user: EditorUser, service: CampaignServiceDep) -> CampaignDetail:
    return CampaignDetail.model_validate(await service.generate(user, campaign_id))


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: uuid.UUID, user: EditorUser, service: CampaignServiceDep) -> Response:
    await service.delete(user, campaign_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
