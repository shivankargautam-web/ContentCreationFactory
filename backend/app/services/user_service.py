import uuid

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import UserRole
from app.models.user import User
from app.repository.unit_of_work import UnitOfWork
from app.schemas.user import UserUpdate


class UserService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def list_users(self, limit: int, offset: int) -> tuple[list[User], int]:
        return await self._uow.users.list_users(limit=limit, offset=offset)

    async def update_profile(self, user: User, payload: UserUpdate) -> User:
        await self._uow.users.update(user, **payload.model_dump(exclude_unset=True))
        await self._uow.commit()
        return user

    async def change_role(self, actor: User, user_id: uuid.UUID, role: UserRole) -> User:
        target = await self._uow.users.get(user_id)
        if target is None:
            raise NotFoundError("User not found")
        if target.id == actor.id and role != UserRole.ADMIN:
            raise ValidationError("Administrators cannot demote themselves")
        await self._uow.users.update(target, role=role)
        await self._uow.commit()
        return target
