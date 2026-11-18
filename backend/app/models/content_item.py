import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ContentStatus

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.publishing_job import PublishingJob
    from app.models.video import Video


class ContentItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint("campaign_id", "sequence_number", name="uq_content_items_campaign_seq"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    subtopic: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status", values_callable=lambda e: [m.value for m in e]),
        default=ContentStatus.PENDING,
        index=True,
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    research: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    script: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    seo: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    error: Mapped[str | None] = mapped_column(Text)

    campaign: Mapped["Campaign"] = relationship(back_populates="content_items")
    video: Mapped["Video | None"] = relationship(
        back_populates="content_item", cascade="all, delete-orphan", uselist=False
    )
    publishing_jobs: Mapped[list["PublishingJob"]] = relationship(
        back_populates="content_item", cascade="all, delete-orphan"
    )
