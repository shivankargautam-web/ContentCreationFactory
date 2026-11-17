import uuid
from datetime import date, time
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CampaignStatus

if TYPE_CHECKING:
    from app.models.content_item import ContentItem
    from app.models.user import User


class Campaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    publish_time: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    platforms: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    tone: Mapped[str | None] = mapped_column(String(100))
    target_audience: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status", values_callable=lambda e: [m.value for m in e]),
        default=CampaignStatus.DRAFT,
        index=True,
        nullable=False,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="campaigns")
    content_items: Mapped[list["ContentItem"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", order_by="ContentItem.sequence_number"
    )
