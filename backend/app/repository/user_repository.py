from sqlalchemy import func, select

from app.models.user import User
from app.repository.base import SQLAlchemyRepository


class UserRepository(SQLAlchemyRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))

    async def list_users(self, limit: int = 50, offset: int = 0) -> tuple[list[User], int]:
        return await self._paginate(select(User).order_by(User.created_at.desc()), limit, offset)

    async def count(self) -> int:
        return int(await self.session.scalar(select(func.count(User.id))) or 0)
