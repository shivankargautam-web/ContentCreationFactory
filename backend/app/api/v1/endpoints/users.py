import uuid

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, CurrentUser, UserServiceDep
from app.schemas.common import Page
from app.schemas.user import UserRead, UserRoleUpdate, UserUpdate

router = APIRouter()


@router.get("", response_model=Page[UserRead])
async def list_users(
    _: AdminUser,
    service: UserServiceDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[UserRead]:
    users, total = await service.list_users(limit, offset)
    return Page(items=[UserRead.model_validate(u) for u in users], total=total, limit=limit, offset=offset)


@router.patch("/me", response_model=UserRead)
async def update_me(payload: UserUpdate, user: CurrentUser, service: UserServiceDep) -> UserRead:
    return UserRead.model_validate(await service.update_profile(user, payload))


@router.patch("/{user_id}/role", response_model=UserRead)
async def change_role(
    user_id: uuid.UUID, payload: UserRoleUpdate, admin: AdminUser, service: UserServiceDep
) -> UserRead:
    return UserRead.model_validate(await service.change_role(admin, user_id, payload.role))
