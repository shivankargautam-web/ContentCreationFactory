import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import ORMModel


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdate(ORMModel):
    full_name: str | None = Field(default=None, max_length=255)


class UserRoleUpdate(ORMModel):
    role: UserRole
