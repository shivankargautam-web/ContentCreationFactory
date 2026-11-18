import uuid

from sqlalchemy import select

from app.models.enums import Platform
from app.models.platform_account import PlatformAccount
from app.repository.base import SQLAlchemyRepository


class PlatformAccountRepository(SQLAlchemyRepository[PlatformAccount]):
    model = PlatformAccount

    async def list_for_user(self, user_id: uuid.UUID) -> list[PlatformAccount]:
        stmt = (
            select(PlatformAccount)
            .where(PlatformAccount.user_id == user_id)
            .order_by(PlatformAccount.created_at)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_for_platform(self, user_id: uuid.UUID, platform: Platform) -> PlatformAccount | None:
        stmt = (
            select(PlatformAccount)
            .where(
                PlatformAccount.user_id == user_id,
                PlatformAccount.platform == platform,
                PlatformAccount.is_active.is_(True),
            )
            .order_by(PlatformAccount.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def get_by_identity(
        self, user_id: uuid.UUID, platform: Platform, external_account_id: str
    ) -> PlatformAccount | None:
        stmt = select(PlatformAccount).where(
            PlatformAccount.user_id == user_id,
            PlatformAccount.platform == platform,
            PlatformAccount.external_account_id == external_account_id,
        )
        return await self.session.scalar(stmt)
