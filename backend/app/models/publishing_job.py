import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import JobStatus, Platform

if TYPE_CHECKING:
    from app.models.analytics import AnalyticsSnapshot
    from app.models.content_item import ContentItem
    from app.models.platform_account import PlatformAccount


class PublishingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "publishing_jobs"
    __table_args__ = (
        UniqueConstraint("content_item_id", "platform", name="uq_publishing_jobs_item_platform"),
    )

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    platform_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_accounts.id", ondelete="SET NULL"), index=True
    )
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform", values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=lambda e: [m.value for m in e]),
        default=JobStatus.SCHEDULED,
        index=True,
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    external_url: Mapped[str | None] = mapped_column(String(1024))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)

    content_item: Mapped["ContentItem"] = relationship(back_populates="publishing_jobs")
    platform_account: Mapped["PlatformAccount | None"] = relationship()
    analytics: Mapped[list["AnalyticsSnapshot"]] = relationship(
        back_populates="publishing_job", cascade="all, delete-orphan"
    )
