import uuid

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.core.security import JWTService, PasswordHasher
from app.models.enums import UserRole
from app.models.user import User
from app.repository.unit_of_work import UnitOfWork
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair

logger = get_logger(__name__)


class AuthService:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher, jwt_service: JWTService) -> None:
        self._uow = uow
        self._hasher = hasher
        self._jwt = jwt_service

    async def register(self, payload: RegisterRequest) -> User:
        if await self._uow.users.get_by_email(payload.email):
            raise ConflictError("Email is already registered", code="email_taken")
        # Bootstrap: the very first account becomes the administrator.
        role = UserRole.ADMIN if await self._uow.users.count() == 0 else UserRole.EDITOR
        user = await self._uow.users.add(
            User(
                email=payload.email.lower(),
                hashed_password=self._hasher.hash(payload.password),
                full_name=payload.full_name,
                role=role,
            )
        )
        await self._uow.commit()
        logger.info("auth.registered", user_id=str(user.id), role=role.value)
        return user

    async def login(self, payload: LoginRequest) -> TokenPair:
        user = await self._uow.users.get_by_email(payload.email)
        if user is None or not self._hasher.verify(payload.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password", code="invalid_credentials")
        if not user.is_active:
            raise AuthenticationError("Account is disabled", code="account_disabled")
        logger.info("auth.login", user_id=str(user.id))
        return self._issue(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        claims = self._jwt.decode(refresh_token, "refresh")
        user = await self._uow.users.get(uuid.UUID(claims["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationError("User no longer active", code="invalid_token")
        return self._issue(user)

    async def resolve_user(self, access_token: str) -> User:
        claims = self._jwt.decode(access_token, "access")
        user = await self._uow.users.get(uuid.UUID(claims["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or inactive", code="invalid_token")
        return user

    def _issue(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=self._jwt.create_token(str(user.id), user.role.value, "access"),
            refresh_token=self._jwt.create_token(str(user.id), user.role.value, "refresh"),
            expires_in=self._jwt.access_ttl_seconds,
        )
