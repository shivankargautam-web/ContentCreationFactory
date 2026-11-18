from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.platform_account import PlatformAccount


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.EDITOR,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    platform_accounts: Mapped[list["PlatformAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
