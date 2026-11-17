"""Meta Instagram Graph API client for Reels publishing and insights."""

import asyncio
from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.core.telemetry import get_tracer

tracer = get_tracer(__name__)


@dataclass(frozen=True)
class PublishedReel:
    media_id: str
    permalink: str | None


class InstagramClient:
    def __init__(
        self,
        settings: Settings,
        http: httpx.AsyncClient | None = None,
        poll_interval_seconds: float = 5.0,
        max_polls: int = 60,
    ) -> None:
        self._base = f"https://graph.facebook.com/{settings.meta_graph_api_version}"
        self._http = http or httpx.AsyncClient(timeout=60)
        self._poll_interval = poll_interval_seconds
        self._max_polls = max_polls

    async def publish_reel(
        self, access_token: str, ig_user_id: str, video_url: str, caption: str
    ) -> PublishedReel:
        """Create a REELS container from a publicly reachable URL, wait for processing, then publish."""
        with tracer.start_as_current_span("instagram.publish_reel"):
            container = await self._http.post(
                f"{self._base}/{ig_user_id}/media",
                data={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption[:2200],
                    "share_to_feed": "true",
                    "access_token": access_token,
                },
            )
            self._raise(container, "create container")
            creation_id = container.json()["id"]

            for _ in range(self._max_polls):
                status = await self._http.get(
                    f"{self._base}/{creation_id}",
                    params={"fields": "status_code,status", "access_token": access_token},
                )
                self._raise(status, "container status")
                code = status.json().get("status_code")
                if code == "FINISHED":
                    break
                if code in {"ERROR", "EXPIRED"}:
                    raise ExternalServiceError(f"Instagram container processing failed: {status.json()}")
                await asyncio.sleep(self._poll_interval)
            else:
                raise ExternalServiceError("Timed out waiting for Instagram to process the reel")

            published = await self._http.post(
                f"{self._base}/{ig_user_id}/media_publish",
                data={"creation_id": creation_id, "access_token": access_token},
            )
            self._raise(published, "media_publish")
            media_id = published.json()["id"]

            permalink_resp = await self._http.get(
                f"{self._base}/{media_id}", params={"fields": "permalink", "access_token": access_token}
            )
            permalink = permalink_resp.json().get("permalink") if permalink_resp.status_code < 400 else None
            return PublishedReel(media_id=media_id, permalink=permalink)

    async def get_insights(self, access_token: str, media_id: str) -> dict[str, int]:
        response = await self._http.get(
            f"{self._base}/{media_id}/insights",
            params={"metric": "views,likes,comments,shares,saved", "access_token": access_token},
        )
        self._raise(response, "insights")
        values: dict[str, int] = {}
        for metric in response.json().get("data", []):
            series = metric.get("values") or [{}]
            values[metric["name"]] = int(
                series[0].get("value", 0) or metric.get("total_value", {}).get("value", 0)
            )
        return {
            "views": values.get("views", 0),
            "likes": values.get("likes", 0),
            "comments": values.get("comments", 0),
            "shares": values.get("shares", 0),
        }

    @staticmethod
    def _raise(response: httpx.Response, action: str) -> None:
        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Instagram {action} failed ({response.status_code}): {response.text[:300]}"
            )
