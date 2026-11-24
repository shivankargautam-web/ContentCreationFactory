import uuid
from datetime import date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CampaignStatus, Platform
from app.schemas.common import ORMModel
from app.schemas.content import ContentItemRead


def _validate_tz(value: str | None) -> str | None:
    if value is None:
        return value
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {value}") from exc
    return value


class CampaignPlan(BaseModel):
    """Structured interpretation of a natural-language campaign instruction."""

    topic: str = Field(min_length=2, max_length=500)
    total_items: int = Field(ge=1, le=100)
    interval_hours: int = Field(default=24, ge=1, le=24 * 30)
    publish_time: time = time(9, 0)
    timezone: str = "America/New_York"
    start_date: date | None = None
    tone: str | None = None
    target_audience: str | None = None

    _tz = field_validator("timezone")(_validate_tz)


CampaignMode = Literal["scheduled", "now"]


class CampaignCreate(BaseModel):
    instruction: str = Field(min_length=10, max_length=4000)
    mode: CampaignMode = Field(
        default="scheduled",
        description="'scheduled' plans a series from the instruction; "
        "'now' makes one reel and posts it right away",
    )
    name: str | None = Field(default=None, max_length=255)
    platforms: list[Platform] = Field(
        default_factory=lambda: [Platform.YOUTUBE, Platform.INSTAGRAM], min_length=1
    )
    start_date: date | None = None
    timezone: str | None = None
    tone: str | None = Field(default=None, max_length=100)
    target_audience: str | None = Field(default=None, max_length=255)
    auto_generate: bool = True

    _tz = field_validator("timezone")(_validate_tz)


class CampaignStatusUpdate(BaseModel):
    status: CampaignStatus


class CampaignRead(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    instruction: str
    topic: str
    total_items: int
    interval_hours: int
    publish_time: time
    timezone: str
    start_date: date
    platforms: list[Platform]
    tone: str | None
    target_audience: str | None
    status: CampaignStatus
    mode: CampaignMode = "scheduled"
    created_at: datetime
    updated_at: datetime


class CampaignDetail(CampaignRead):
    content_items: list[ContentItemRead] = Field(default_factory=list)


class CalendarEvent(BaseModel):
    content_item_id: uuid.UUID
    campaign_id: uuid.UUID
    campaign_name: str
    title: str
    scheduled_at: datetime
    status: str
    platforms: list[Platform]
