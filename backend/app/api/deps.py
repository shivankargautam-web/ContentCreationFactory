"""FastAPI dependency providers (request-scoped DI)."""

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import Container
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.enums import UserRole
from app.models.user import User
from app.repository.unit_of_work import UnitOfWork
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.campaign_service import CampaignService
from app.services.content_service import ContentService
from app.services.oauth_service import OAuthService
from app.services.platform_account_service import PlatformAccountService
from app.services.user_service import UserService

bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


async def get_session(container: ContainerDep) -> AsyncIterator[AsyncSession]:
    async with container.database.session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> UnitOfWork:
    return UnitOfWork(session)


UoWDep = Annotated[UnitOfWork, Depends(get_uow)]


def get_auth_service(uow: UoWDep, container: ContainerDep) -> AuthService:
    return AuthService(uow, container.password_hasher, container.jwt_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    auth: AuthServiceDep, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Missing bearer token", code="not_authenticated")
    return await auth.resolve_user(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], Coroutine[Any, Any, User]]:
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AuthorizationError(f"Requires role: {', '.join(r.value for r in roles)}")
        return user

    return checker


EditorUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def get_campaign_service(uow: UoWDep, container: ContainerDep) -> CampaignService:
    return CampaignService(
        uow, container.instruction_parser(), container.dispatcher, container.settings.default_timezone
    )


def get_content_service(uow: UoWDep, container: ContainerDep) -> ContentService:
    return ContentService(uow, container.dispatcher, container.storage)


def get_platform_account_service(uow: UoWDep, container: ContainerDep) -> PlatformAccountService:
    return container.platform_account_service(uow)


def get_oauth_service(uow: UoWDep, container: ContainerDep) -> OAuthService:
    return container.oauth_service(uow)


def get_analytics_service(uow: UoWDep) -> AnalyticsService:
    return AnalyticsService(uow)


def get_user_service(uow: UoWDep) -> UserService:
    return UserService(uow)


CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]
ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]
PlatformAccountServiceDep = Annotated[PlatformAccountService, Depends(get_platform_account_service)]
OAuthServiceDep = Annotated[OAuthService, Depends(get_oauth_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
