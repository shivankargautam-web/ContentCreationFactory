import uuid

from fastapi import APIRouter, Query

from app.api.deps import AnalyticsServiceDep, CampaignServiceDep, CurrentUser
from app.schemas.analytics import AnalyticsSummary, CampaignAnalytics, TimeseriesPoint

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
async def summary(user: CurrentUser, service: AnalyticsServiceDep) -> AnalyticsSummary:
    return await service.summary(user)


@router.get("/timeseries", response_model=list[TimeseriesPoint])
async def timeseries(
    user: CurrentUser, service: AnalyticsServiceDep, days: int = Query(30, ge=1, le=365)
) -> list[TimeseriesPoint]:
    return await service.timeseries(user, days)


@router.get("/campaigns/{campaign_id}", response_model=CampaignAnalytics)
async def campaign_analytics(
    campaign_id: uuid.UUID,
    user: CurrentUser,
    service: AnalyticsServiceDep,
    campaigns: CampaignServiceDep,
    days: int = Query(30, ge=1, le=365),
) -> CampaignAnalytics:
    return await service.campaign(user, campaigns, campaign_id, days)
