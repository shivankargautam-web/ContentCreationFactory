"""YouTube Data API v3 client (OAuth token refresh, resumable upload, statistics)."""

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.core.telemetry import get_tracer

tracer = get_tracer(__name__)


@dataclass(frozen=True)
class RefreshedToken:
    access_token: str
    expires_at: datetime


class YouTubeClient:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    API_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None) -> None:
        self._client_id = settings.youtube_client_id
        self._client_secret = (
            settings.youtube_client_secret.get_secret_value() if settings.youtube_client_secret else None
        )
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(60, read=600))

    async def refresh_access_token(self, refresh_token: str) -> RefreshedToken:
        if not (self._client_id and self._client_secret):
            raise ExternalServiceError("YouTube OAuth client credentials are not configured")
        response = await self._http.post(
            self.TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        self._raise_for_status(response, "token refresh")
        body = response.json()
        return RefreshedToken(
            access_token=body["access_token"],
            expires_at=datetime.now(UTC) + timedelta(seconds=int(body.get("expires_in", 3600)) - 60),
        )

    async def upload_short(
        self,
        access_token: str,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        privacy_status: str = "public",
    ) -> str:
        """Resumable upload; returns the YouTube video id. Shorts = vertical video <= 60s with #shorts."""
        metadata: dict[str, Any] = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:30],
                "categoryId": "28",  # Science & Technology
            },
            "status": {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False},
        }
        size = (await asyncio.to_thread(video_path.stat)).st_size
        with tracer.start_as_current_span("youtube.upload") as span:
            span.set_attribute("video.bytes", size)
            init = await self._http.post(
                self.UPLOAD_URL,
                params={"uploadType": "resumable", "part": "snippet,status"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "video/mp4",
                    "X-Upload-Content-Length": str(size),
                },
                content=json.dumps(metadata),
            )
            self._raise_for_status(init, "upload init")
            session_url = init.headers.get("Location")
            if not session_url:
                raise ExternalServiceError("YouTube did not return a resumable session URL")
            upload = await self._http.put(
                session_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(size),
                },
                content=_iter_file(video_path),
            )
            self._raise_for_status(upload, "upload")
            video_id = upload.json()["id"]
            span.set_attribute("youtube.video_id", video_id)
            return video_id

    async def get_statistics(self, access_token: str, video_ids: list[str]) -> dict[str, dict[str, int]]:
        if not video_ids:
            return {}
        response = await self._http.get(
            f"{self.API_URL}/videos",
            params={"part": "statistics", "id": ",".join(video_ids[:50])},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self._raise_for_status(response, "statistics")
        result: dict[str, dict[str, int]] = {}
        for item in response.json().get("items", []):
            stats = item.get("statistics", {})
            result[item["id"]] = {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "shares": 0,
            }
        return result

    @staticmethod
    def _raise_for_status(response: httpx.Response, action: str) -> None:
        if response.status_code >= 400:
            raise ExternalServiceError(
                f"YouTube {action} failed ({response.status_code}): {response.text[:300]}"
            )


async def _iter_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> AsyncIterator[bytes]:
    """Stream a file without blocking the event loop or loading it fully into memory."""
    handle = await asyncio.to_thread(path.open, "rb")
    try:
        while chunk := await asyncio.to_thread(handle.read, chunk_size):
            yield chunk
    finally:
        await asyncio.to_thread(handle.close)
