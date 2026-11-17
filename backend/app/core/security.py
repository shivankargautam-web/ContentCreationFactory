"""Password hashing, JWT issuing/verification and symmetric encryption of third-party tokens."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.core.exceptions import AuthenticationError

TokenType = Literal["access", "refresh"]


class PasswordHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False


class JWTService:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret_key.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._access_ttl = timedelta(minutes=settings.access_token_expire_minutes)
        self._refresh_ttl = timedelta(minutes=settings.refresh_token_expire_minutes)

    @property
    def access_ttl_seconds(self) -> int:
        return int(self._access_ttl.total_seconds())

    def create_token(self, subject: str, role: str, token_type: TokenType) -> str:
        now = datetime.now(UTC)
        ttl = self._access_ttl if token_type == "access" else self._refresh_ttl
        payload: dict[str, Any] = {
            "sub": subject,
            "role": role,
            "type": token_type,
            "iat": now,
            "nbf": now,
            "exp": now + ttl,
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str, expected_type: TokenType) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired", code="token_expired") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid token", code="invalid_token") from exc
        if payload.get("type") != expected_type:
            raise AuthenticationError("Invalid token type", code="invalid_token")
        return payload


class TokenCipher:
    """Encrypts OAuth tokens at rest. Falls back to a key derived from the JWT secret in dev."""

    def __init__(self, settings: Settings) -> None:
        key = settings.token_encryption_key.get_secret_value() if settings.token_encryption_key else None
        if not key:
            import base64
            import hashlib

            digest = hashlib.sha256(settings.jwt_secret_key.get_secret_value().encode()).digest()
            key = base64.urlsafe_b64encode(digest).decode()
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise AuthenticationError("Unable to decrypt stored credential") from exc
