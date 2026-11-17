"""Platform publishers (strategy pattern) behind a common interface."""

import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.models.enums import Platform
from app.services.integrations.instagram import InstagramClient
from app.services.integrations.storage import ObjectStorage
from app.services.integrations.youtube import YouTubeClient


@dataclass(frozen=True)
class PlatformCredentials:
    access_token: str
    external_account_id: str


@dataclass(frozen=True)
class PublishRequest:
    video_key: str
    title: str
    description: str
    caption: str
    tags: list[str]


@dataclass(frozen=True)
class PublishResult:
    external_id: str
    url: str | None


class Publisher(Protocol):
    platform: Platform

    async def publish(self, credentials: PlatformCredentials, request: PublishRequest) -> PublishResult: ...


class YouTubePublisher:
    platform = Platform.YOUTUBE

    def __init__(self, client: YouTubeClient, storage: ObjectStorage) -> None:
        self._client = client
        self._storage = storage

    async def publish(self, credentials: PlatformCredentials, request: PublishRequest) -> PublishResult:
        with tempfile.TemporaryDirectory() as tmp:
            local = await self._storage.download_to(request.video_key, Path(tmp) / "video.mp4")
            description = f"{request.description}\n\n{' '.join(t for t in request.tags if t.startswith('#'))}"
            title = request.title if "#shorts" in request.title.lower() else f"{request.title[:91]} #shorts"
            video_id = await self._client.upload_short(
                credentials.access_token,
                local,
                title=title,
                description=description.strip(),
                tags=[t.lstrip("#") for t in request.tags],
            )
        return PublishResult(external_id=video_id, url=f"https://www.youtube.com/shorts/{video_id}")


class InstagramPublisher:
    platform = Platform.INSTAGRAM

    def __init__(self, client: InstagramClient, storage: ObjectStorage) -> None:
        self._client = client
        self._storage = storage

    async def publish(self, credentials: PlatformCredentials, request: PublishRequest) -> PublishResult:
        video_url = await self._storage.url_for(request.video_key)
        reel = await self._client.publish_reel(
            credentials.access_token, credentials.external_account_id, video_url, request.caption
        )
        return PublishResult(external_id=reel.media_id, url=reel.permalink)


class DryRunPublisher:
    """Simulates publishing (local/staging) without calling external platforms."""

    def __init__(self, platform: Platform) -> None:
        self.platform = platform

    async def publish(self, credentials: PlatformCredentials, request: PublishRequest) -> PublishResult:
        fake_id = f"dryrun-{uuid.uuid4().hex[:12]}"
        return PublishResult(external_id=fake_id, url=f"https://example.com/{self.platform.value}/{fake_id}")


class PublisherRegistry:
    def __init__(self, publishers: list[Publisher]) -> None:
        self._publishers = {p.platform: p for p in publishers}

    def get(self, platform: Platform) -> Publisher:
        try:
            return self._publishers[platform]
        except KeyError as exc:
            raise ValueError(f"No publisher registered for {platform}") from exc
