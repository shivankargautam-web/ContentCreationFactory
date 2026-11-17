import uuid
from datetime import UTC, datetime, timedelta

from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.security import TokenCipher
from app.models.enums import Platform
from app.models.platform_account import PlatformAccount
from app.models.user import User
from app.repository.unit_of_work import UnitOfWork
from app.schemas.platform_account import PlatformAccountCreate
from app.services.integrations.publishers import PlatformCredentials
from app.services.integrations.youtube import YouTubeClient


class PlatformAccountService:
    def __init__(self, uow: UnitOfWork, cipher: TokenCipher, youtube: YouTubeClient | None = None) -> None:
        self._uow = uow
        self._cipher = cipher
        self._youtube = youtube

    async def connect(self, user: User, payload: PlatformAccountCreate) -> PlatformAccount:
        values = {
            "account_name": payload.account_name,
            "access_token_encrypted": self._cipher.encrypt(payload.access_token),
            "refresh_token_encrypted": self._cipher.encrypt(payload.refresh_token)
            if payload.refresh_token
            else None,
            "token_expires_at": payload.token_expires_at,
            "scopes": payload.scopes,
            "is_active": True,
        }
        account = await self._uow.platform_accounts.get_by_identity(
            user.id, payload.platform, payload.external_account_id
        )
        if account is None:
            account = await self._uow.platform_accounts.add(
                PlatformAccount(
                    user_id=user.id,
                    platform=payload.platform,
                    external_account_id=payload.external_account_id,
                    **values,
                )
            )
        else:
            await self._uow.platform_accounts.update(account, **values)
        await self._uow.commit()
        return account

    async def list_accounts(self, user: User) -> list[PlatformAccount]:
        return await self._uow.platform_accounts.list_for_user(user.id)

    async def disconnect(self, user: User, account_id: uuid.UUID) -> None:
        account = await self._uow.platform_accounts.get(account_id)
        if account is None:
            raise NotFoundError("Platform account not found")
        if account.user_id != user.id:
            raise AuthorizationError("You do not own this platform account")
        await self._uow.platform_accounts.delete(account)
        await self._uow.commit()

    async def credentials_for(self, account: PlatformAccount) -> PlatformCredentials:
        """Decrypt tokens, refreshing expiring YouTube access tokens transparently."""
        access_token = self._cipher.decrypt(account.access_token_encrypted)
        expires_soon = account.token_expires_at is not None and account.token_expires_at <= datetime.now(
            UTC
        ) + timedelta(minutes=5)
        if (
            account.platform == Platform.YOUTUBE
            and expires_soon
            and account.refresh_token_encrypted
            and self._youtube
        ):
            refreshed = await self._youtube.refresh_access_token(
                self._cipher.decrypt(account.refresh_token_encrypted)
            )
            account.access_token_encrypted = self._cipher.encrypt(refreshed.access_token)
            account.token_expires_at = refreshed.expires_at
            await self._uow.session.flush()
            access_token = refreshed.access_token
        return PlatformCredentials(access_token=access_token, external_account_id=account.external_account_id)
