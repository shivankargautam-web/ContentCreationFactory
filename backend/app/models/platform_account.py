import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Platform

if TYPE_CHECKING:
    from app.models.user import User


class PlatformAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "platform", "external_account_id", name="uq_platform_accounts_identity"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform", values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="platform_accounts")
