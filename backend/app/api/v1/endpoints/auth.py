from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, auth: AuthServiceDep) -> UserRead:
    return UserRead.model_validate(await auth.register(payload))


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, auth: AuthServiceDep) -> TokenPair:
    return await auth.login(payload)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, auth: AuthServiceDep) -> TokenPair:
    return await auth.refresh(payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
