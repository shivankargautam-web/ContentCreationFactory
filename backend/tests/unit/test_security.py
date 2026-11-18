from datetime import timedelta

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.security import JWTService, PasswordHasher, TokenCipher


@pytest.fixture
def cfg() -> Settings:
    return Settings(jwt_secret_key=SecretStr("unit-test-secret-key-0123456789abcdef"))


def test_password_hash_roundtrip() -> None:
    hasher = PasswordHasher()
    hashed = hasher.hash("S3cretPass")
    assert hashed != "S3cretPass"
    assert hasher.verify("S3cretPass", hashed)
    assert not hasher.verify("wrong", hashed)
    assert not hasher.verify("x", "not-a-hash")


def test_jwt_roundtrip_and_type_enforcement(cfg: Settings) -> None:
    svc = JWTService(cfg)
    token = svc.create_token("user-1", "editor", "access")
    claims = svc.decode(token, "access")
    assert claims["sub"] == "user-1" and claims["role"] == "editor"
    with pytest.raises(AuthenticationError):
        svc.decode(token, "refresh")


def test_jwt_expired(cfg: Settings) -> None:
    svc = JWTService(cfg)
    svc._access_ttl = timedelta(seconds=-5)
    token = svc.create_token("u", "viewer", "access")
    with pytest.raises(AuthenticationError) as exc:
        svc.decode(token, "access")
    assert exc.value.code == "token_expired"


def test_jwt_tampered(cfg: Settings) -> None:
    svc = JWTService(cfg)
    token = svc.create_token("u", "viewer", "access")
    with pytest.raises(AuthenticationError):
        svc.decode(token[:-2] + "xx", "access")


def test_token_cipher(cfg: Settings) -> None:
    cipher = TokenCipher(cfg)
    enc = cipher.encrypt("ya29.secret-token")
    assert "secret" not in enc
    assert cipher.decrypt(enc) == "ya29.secret-token"
    with pytest.raises(AuthenticationError):
        cipher.decrypt("garbage")
