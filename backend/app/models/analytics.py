import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, UUIDPrimaryKeyMixin, utcnow
from app.models.enums import Platform

if TYPE_CHECKING:
    from app.models.publishing_job import PublishingJob


class AnalyticsSnapshot(UUIDPrimaryKeyMixin, Base):
    """Point-in-time engagement metrics for a published video."""

    __tablename__ = "analytics"
    __table_args__ = (Index("ix_analytics_job_collected", "publishing_job_id", "collected_at"),)

    publishing_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("publishing_jobs.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform", values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    watch_time_seconds: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    publishing_job: Mapped["PublishingJob"] = relationship(back_populates="analytics")
