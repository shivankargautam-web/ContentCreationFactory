import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import VideoStatus

if TYPE_CHECKING:
    from app.models.content_item import ContentItem


class Video(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "videos"

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, name="video_status", values_callable=lambda e: [m.value for m in e]),
        default=VideoStatus.PENDING,
        nullable=False,
    )
    storyboard: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)
    captions_srt: Mapped[str | None] = mapped_column(Text)
    audio_key: Mapped[str | None] = mapped_column(String(1024))
    video_key: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_key: Mapped[str | None] = mapped_column(String(1024))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(Text)

    content_item: Mapped["ContentItem"] = relationship(back_populates="video")
