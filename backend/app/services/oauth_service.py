"""OAuth sign-in flows that connect YouTube channels and Instagram professional accounts."""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.enums import Platform
from app.models.platform_account import PlatformAccount
from app.models.user import User
from app.repository.unit_of_work import UnitOfWork
from app.schemas.platform_account import PlatformAccountCreate
from app.services.platform_account_service import PlatformAccountService

logger = get_logger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
INSTAGRAM_SCOPES = [
    "instagram_basic",
    "instagram_content_publish",
    "instagram_manage_insights",
    "pages_show_list",
    "pages_read_engagement",
    "business_management",
]
STATE_TTL = timedelta(minutes=10)
STATE_AUDIENCE = "acf-oauth"


@dataclass(frozen=True)
class OAuthResult:
    platform: Platform
    accounts: list[PlatformAccount]


class OAuthService:
    def __init__(
        self,
        settings: Settings,
        uow: UnitOfWork,
        accounts: PlatformAccountService,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._accounts = accounts
        self._http = http or httpx.AsyncClient(timeout=30)
        self._graph = f"https://graph.facebook.com/{settings.meta_graph_api_version}"

    def providers(self) -> dict[str, bool]:
        s = self._settings
        return {
            Platform.YOUTUBE.value: bool(s.youtube_client_id and s.youtube_client_secret),
            Platform.INSTAGRAM.value: bool(s.meta_app_id and s.meta_app_secret),
        }

    def redirect_uri(self, platform: Platform) -> str:
        base = self._settings.public_app_url.rstrip("/")
        return f"{base}{self._settings.api_v1_prefix}/platform-accounts/oauth/{platform.value}/callback"

    def authorization_url(self, user: User, platform: Platform) -> str:
        self._require_configured(platform)
        state = self._encode_state(user.id, platform)
        if platform == Platform.YOUTUBE:
            params = {
                "client_id": self._settings.youtube_client_id,
                "redirect_uri": self.redirect_uri(platform),
                "response_type": "code",
                "scope": " ".join(YOUTUBE_SCOPES),
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
                "state": state,
            }
            return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        params = {
            "client_id": self._settings.meta_app_id,
            "redirect_uri": self.redirect_uri(platform),
            "response_type": "code",
            "scope": ",".join(INSTAGRAM_SCOPES),
            "state": state,
        }
        return f"https://www.facebook.com/{self._settings.meta_graph_api_version}/dialog/oauth?{urlencode(params)}"

    async def complete(self, platform: Platform, code: str, state: str) -> OAuthResult:
        self._require_configured(platform)
        user_id = self._decode_state(state, platform)
        user = await self._uow.users.get(user_id)
        if user is None or not user.is_active:
            raise NotFoundError("User not found")
        if platform == Platform.YOUTUBE:
            payloads = await self._youtube_accounts(code)
        else:
            payloads = await self._instagram_accounts(code)
        accounts = [await self._accounts.connect(user, p) for p in payloads]
        logger.info("oauth.connected", platform=platform.value, user_id=str(user.id), accounts=len(accounts))
        return OAuthResult(platform=platform, accounts=accounts)

    async def _youtube_accounts(self, code: str) -> list[PlatformAccountCreate]:
        secret = self._settings.youtube_client_secret
        token = await self._json(
            "POST",
            GOOGLE_TOKEN_URL,
            "Google token exchange",
            data={
                "code": code,
                "client_id": self._settings.youtube_client_id,
                "client_secret": secret.get_secret_value() if secret else "",
                "redirect_uri": self.redirect_uri(Platform.YOUTUBE),
                "grant_type": "authorization_code",
            },
        )
        access_token = token["access_token"]
        channels = await self._json(
            "GET",
            YOUTUBE_CHANNELS_URL,
            "YouTube channel lookup",
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        items = channels.get("items") or []
        if not items:
            raise ValidationError("This Google account has no YouTube channel")
        expires_at = datetime.now(UTC) + timedelta(seconds=int(token.get("expires_in", 3600)) - 60)
        scopes = str(token.get("scope", "")).split()
        return [
            PlatformAccountCreate(
                platform=Platform.YOUTUBE,
                account_name=item.get("snippet", {}).get("title") or item["id"],
                external_account_id=item["id"],
                access_token=access_token,
                refresh_token=token.get("refresh_token"),
                token_expires_at=expires_at,
                scopes=scopes,
            )
            for item in items
        ]

    async def _instagram_accounts(self, code: str) -> list[PlatformAccountCreate]:
        secret = self._settings.meta_app_secret
        app = {
            "client_id": self._settings.meta_app_id,
            "client_secret": secret.get_secret_value() if secret else "",
        }
        short = await self._json(
            "GET",
            f"{self._graph}/oauth/access_token",
            "Facebook token exchange",
            params={**app, "redirect_uri": self.redirect_uri(Platform.INSTAGRAM), "code": code},
        )
        long_lived = await self._json(
            "GET",
            f"{self._graph}/oauth/access_token",
            "Facebook long-lived token exchange",
            params={**app, "grant_type": "fb_exchange_token", "fb_exchange_token": short["access_token"]},
        )
        pages = await self._json(
            "GET",
            f"{self._graph}/me/accounts",
            "Facebook Page lookup",
            params={
                "fields": "name,access_token,instagram_business_account{id,username}",
                "access_token": long_lived["access_token"],
            },
        )
        # Page tokens obtained from a long-lived user token do not expire, so publishing keeps working.
        payloads = [
            PlatformAccountCreate(
                platform=Platform.INSTAGRAM,
                account_name=f"@{ig['username']}" if ig.get("username") else page.get("name", ig["id"]),
                external_account_id=ig["id"],
                access_token=page["access_token"],
                scopes=INSTAGRAM_SCOPES,
            )
            for page in pages.get("data") or []
            if (ig := page.get("instagram_business_account")) and page.get("access_token")
        ]
        if not payloads:
            raise ValidationError(
                "No Instagram Business or Creator account is linked to the Facebook Pages you shared"
            )
        return payloads

    async def _json(self, method: str, url: str, what: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"{what} failed: {exc}") from exc
        if response.status_code >= 400:
            logger.warning(
                "oauth.provider_error", step=what, status=response.status_code, body=response.text[:500]
            )
            raise ExternalServiceError(f"{what} failed ({response.status_code})")
        body: dict[str, Any] = response.json()
        return body

    def _require_configured(self, platform: Platform) -> None:
        if not self.providers()[platform.value]:
            env = "YOUTUBE_CLIENT_ID/SECRET" if platform == Platform.YOUTUBE else "META_APP_ID/SECRET"
            raise ValidationError(f"{platform.value.title()} sign-in is not configured. Set {env}.")

    def _encode_state(self, user_id: uuid.UUID, platform: Platform) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "platform": platform.value,
            "aud": STATE_AUDIENCE,
            "nonce": secrets.token_urlsafe(16),
            "iat": now,
            "exp": now + STATE_TTL,
        }
        return jwt.encode(
            payload, self._settings.jwt_secret_key.get_secret_value(), algorithm=self._settings.jwt_algorithm
        )

    def _decode_state(self, state: str, platform: Platform) -> uuid.UUID:
        try:
            payload = jwt.decode(
                state,
                self._settings.jwt_secret_key.get_secret_value(),
                algorithms=[self._settings.jwt_algorithm],
                audience=STATE_AUDIENCE,
            )
        except jwt.PyJWTError as exc:
            raise ValidationError("Sign-in link expired or invalid. Please try again.") from exc
        if payload.get("platform") != platform.value:
            raise ValidationError("Sign-in state does not match the platform")
        return uuid.UUID(payload["sub"])
