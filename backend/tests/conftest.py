import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text

from app.container import Container
from app.core.config import Settings
from app.db.base import Base
from app.repository.unit_of_work import UnitOfWork
from app.services.dispatcher import InMemoryTaskDispatcher
from app.services.integrations.llm import LLMClient
from app.services.integrations.offline_llm import OfflineLLMClient
from app.services.media.renderer import RenderInput, RenderOutput


class FakeRenderer:
    def __init__(self) -> None:
        self.calls: list[RenderInput] = []

    async def probe_duration(self, media_path: Path) -> float:
        return 30.0

    async def render(self, data: RenderInput) -> RenderOutput:
        self.calls.append(data)
        data.workdir.mkdir(parents=True, exist_ok=True)
        out = data.workdir / "short.mp4"
        out.write_bytes(b"\x00\x00\x00\x18ftypmp42fake-video")
        return RenderOutput(video_path=out, duration_seconds=sum(s.duration_seconds for s in data.scenes))


class FakeTTS:
    async def synthesize(self, text: str) -> bytes | None:
        return b"ID3fake-mp3"


class TestContainer(Container):
    """Container with external side-effects replaced by in-process fakes."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.__dict__["dispatcher"] = InMemoryTaskDispatcher()
        self.__dict__["renderer"] = FakeRenderer()
        self.__dict__["tts"] = FakeTTS()
        self.__dict__["llm"] = OfflineLLMClient()

    def override_llm(self, llm: LLMClient) -> None:
        self.__dict__["llm"] = llm


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    db_url = os.getenv("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    return Settings(
        environment="test",
        database_url=db_url,
        jwt_secret_key=SecretStr("test-secret-key-that-is-long-enough-123"),
        local_storage_path=str(tmp_path / "media"),
        publishing_dry_run=True,
        log_json=False,
        log_level="WARNING",
        openai_api_key=None,
        elevenlabs_api_key=None,
    )


@pytest.fixture
async def container(settings: Settings) -> AsyncIterator[TestContainer]:
    c = TestContainer(settings)
    async with c.database.engine.begin() as conn:
        if c.database.engine.dialect.name == "postgresql":
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    yield c
    await c.database.dispose()


@pytest.fixture
async def uow(container: TestContainer) -> AsyncIterator[UnitOfWork]:
    async with container.database.session_factory() as session:
        yield UnitOfWork(session)


@pytest.fixture
async def client(container: TestContainer) -> AsyncIterator[AsyncClient]:
    from app.main import create_app

    app = create_app(container)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def register_and_login(
    client: AsyncClient, email: str, password: str = "Password123"
) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password, "full_name": "T"}
    )
    assert resp.status_code == 201, resp.text
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def admin_headers(client: AsyncClient) -> dict[str, str]:
    return await register_and_login(client, "admin@example.com")


@pytest.fixture
async def editor_headers(client: AsyncClient, admin_headers: dict[str, str]) -> dict[str, str]:
    return await register_and_login(client, "editor@example.com")
