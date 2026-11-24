import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import Platform
from app.schemas.common import ORMModel


class PlatformAccountCreate(BaseModel):
    platform: Platform
    account_name: str = Field(min_length=1, max_length=255)
    external_account_id: str = Field(
        min_length=1, max_length=255, description="YouTube channel id or Instagram business account id"
    )
    access_token: str = Field(min_length=1)
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list)


class PlatformAccountRead(ORMModel):
    id: uuid.UUID
    platform: Platform
    account_name: str
    external_account_id: str
    token_expires_at: datetime | None
    scopes: list[str]
    is_active: bool
    created_at: datetime


class OAuthProviders(BaseModel):
    youtube: bool
    instagram: bool


class OAuthAuthorization(BaseModel):
    authorization_url: str
