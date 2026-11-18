import uuid
from datetime import date

from pydantic import BaseModel

from app.models.enums import Platform


class MetricTotals(BaseModel):
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_seconds: int = 0


class PlatformBreakdown(MetricTotals):
    platform: Platform
    published_count: int = 0


class AnalyticsSummary(BaseModel):
    totals: MetricTotals
    published_count: int
    scheduled_count: int
    failed_count: int
    campaign_count: int
    by_platform: list[PlatformBreakdown]


class TimeseriesPoint(MetricTotals):
    day: date


class TopContent(MetricTotals):
    content_item_id: uuid.UUID
    title: str
    platform: Platform
    external_url: str | None


class CampaignAnalytics(BaseModel):
    campaign_id: uuid.UUID
    totals: MetricTotals
    timeseries: list[TimeseriesPoint]
    top_content: list[TopContent]
