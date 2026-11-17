from pathlib import Path

import httpx
import pytest
import respx

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.services.integrations.instagram import InstagramClient
from app.services.integrations.youtube import YouTubeClient

GRAPH = "https://graph.facebook.com/v21.0"


@respx.mock
async def test_youtube_resumable_upload(tmp_path: Path) -> None:
    video = tmp_path / "v.mp4"
    video.write_bytes(b"data")
    init = respx.post("https://www.googleapis.com/upload/youtube/v3/videos").mock(
        return_value=httpx.Response(200, headers={"Location": "https://upload.example/session"})
    )
    respx.put("https://upload.example/session").mock(return_value=httpx.Response(200, json={"id": "abc123"}))
    client = YouTubeClient(Settings(), http=httpx.AsyncClient())
    video_id = await client.upload_short("tok", video, "Title #shorts", "desc", ["kafka"])
    assert video_id == "abc123"
    assert init.calls[0].request.headers["X-Upload-Content-Length"] == "4"


@respx.mock
async def test_youtube_statistics_and_errors() -> None:
    respx.get("https://www.googleapis.com/youtube/v3/videos").mock(
        return_value=httpx.Response(
            200, json={"items": [{"id": "v1", "statistics": {"viewCount": "42", "likeCount": "7"}}]}
        )
    )
    client = YouTubeClient(Settings(), http=httpx.AsyncClient())
    stats = await client.get_statistics("tok", ["v1"])
    assert stats["v1"]["views"] == 42 and stats["v1"]["likes"] == 7

    with pytest.raises(ExternalServiceError):
        await client.refresh_access_token("refresh")  # no client credentials configured


@respx.mock
async def test_instagram_reel_publish_flow() -> None:
    respx.post(f"{GRAPH}/ig-1/media").mock(return_value=httpx.Response(200, json={"id": "container-1"}))
    respx.get(f"{GRAPH}/container-1").mock(
        side_effect=[
            httpx.Response(200, json={"status_code": "IN_PROGRESS"}),
            httpx.Response(200, json={"status_code": "FINISHED"}),
        ]
    )
    respx.post(f"{GRAPH}/ig-1/media_publish").mock(return_value=httpx.Response(200, json={"id": "media-9"}))
    respx.get(f"{GRAPH}/media-9").mock(return_value=httpx.Response(200, json={"permalink": "https://ig/p/9"}))
    client = InstagramClient(Settings(), http=httpx.AsyncClient(), poll_interval_seconds=0)
    reel = await client.publish_reel("tok", "ig-1", "https://cdn/video.mp4", "caption")
    assert reel.media_id == "media-9" and reel.permalink == "https://ig/p/9"


@respx.mock
async def test_instagram_container_error() -> None:
    respx.post(f"{GRAPH}/ig-1/media").mock(return_value=httpx.Response(200, json={"id": "c"}))
    respx.get(f"{GRAPH}/c").mock(return_value=httpx.Response(200, json={"status_code": "ERROR"}))
    client = InstagramClient(Settings(), http=httpx.AsyncClient(), poll_interval_seconds=0)
    with pytest.raises(ExternalServiceError):
        await client.publish_reel("tok", "ig-1", "https://cdn/video.mp4", "caption")
