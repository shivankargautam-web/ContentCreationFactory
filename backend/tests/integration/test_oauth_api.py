from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from app.core.config import Settings

pytestmark = pytest.mark.integration


@pytest.fixture
def settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "youtube_client_id": "yt-client.apps.googleusercontent.com",
            "youtube_client_secret": SecretStr("yt-secret"),
            "meta_app_id": "123456",
            "meta_app_secret": SecretStr("meta-secret"),
            "public_app_url": "https://acf.example.com",
        }
    )


def _provider_mock(calls: list[httpx.Request]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        url = str(request.url)
        if url.startswith("https://oauth2.googleapis.com/token"):
            return httpx.Response(
                200,
                json={
                    "access_token": "ya29.access",
                    "refresh_token": "1//refresh",
                    "expires_in": 3599,
                    "scope": "https://www.googleapis.com/auth/youtube.upload",
                },
            )
        if url.startswith("https://www.googleapis.com/youtube/v3/channels"):
            assert request.headers["Authorization"] == "Bearer ya29.access"
            return httpx.Response(200, json={"items": [{"id": "UC123", "snippet": {"title": "Kafka Daily"}}]})
        if "/oauth/access_token" in url:
            long_lived = "fb_exchange_token" in url
            return httpx.Response(200, json={"access_token": "EAA-long" if long_lived else "EAA-short"})
        if "/me/accounts" in url:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "name": "ACF Page",
                            "access_token": "EAA-page",
                            "instagram_business_account": {"id": "17841400000000000", "username": "acf"},
                        },
                        {"name": "Page without IG", "access_token": "EAA-other"},
                    ]
                },
            )
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _authorize(client: AsyncClient, headers: dict, platform: str) -> dict[str, list[str]]:
    resp = await client.get(f"/api/v1/platform-accounts/oauth/{platform}/authorize", headers=headers)
    assert resp.status_code == 200, resp.text
    return parse_qs(urlparse(resp.json()["authorization_url"]).query)


async def test_providers_reports_configuration(client: AsyncClient, editor_headers: dict) -> None:
    resp = await client.get("/api/v1/platform-accounts/oauth/providers", headers=editor_headers)
    assert resp.json() == {"youtube": True, "instagram": True}


async def test_youtube_sign_in_connects_channel(client: AsyncClient, editor_headers: dict, container) -> None:
    calls: list[httpx.Request] = []
    container.__dict__["oauth_http"] = _provider_mock(calls)
    query = await _authorize(client, editor_headers, "youtube")
    assert query["redirect_uri"] == [
        "https://acf.example.com/api/v1/platform-accounts/oauth/youtube/callback"
    ]
    assert query["access_type"] == ["offline"] and "youtube.upload" in query["scope"][0]

    resp = await client.get(
        "/api/v1/platform-accounts/oauth/youtube/callback",
        params={"code": "auth-code", "state": query["state"][0]},
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://acf.example.com/settings?connected=youtube&accounts=1"
    assert b"code=auth-code" in calls[0].content

    accounts = (await client.get("/api/v1/platform-accounts", headers=editor_headers)).json()
    assert [(a["platform"], a["account_name"], a["external_account_id"]) for a in accounts] == [
        ("youtube", "Kafka Daily", "UC123")
    ]
    assert "ya29" not in str(accounts)


async def test_instagram_sign_in_uses_page_token(
    client: AsyncClient, editor_headers: dict, container
) -> None:
    calls: list[httpx.Request] = []
    container.__dict__["oauth_http"] = _provider_mock(calls)
    query = await _authorize(client, editor_headers, "instagram")
    assert "instagram_content_publish" in query["scope"][0]

    resp = await client.get(
        "/api/v1/platform-accounts/oauth/instagram/callback",
        params={"code": "fb-code", "state": query["state"][0]},
    )
    assert resp.headers["location"].endswith("/settings?connected=instagram&accounts=1")
    accounts = (await client.get("/api/v1/platform-accounts", headers=editor_headers)).json()
    assert [(a["account_name"], a["external_account_id"]) for a in accounts] == [
        ("@acf", "17841400000000000")
    ]
    assert accounts[0]["token_expires_at"] is None


async def test_callback_rejects_bad_state_and_cancel(client: AsyncClient, editor_headers: dict) -> None:
    youtube_state = (await _authorize(client, editor_headers, "youtube"))["state"][0]
    resp = await client.get(
        "/api/v1/platform-accounts/oauth/instagram/callback", params={"code": "x", "state": youtube_state}
    )
    assert "oauth_error=" in resp.headers["location"]
    resp = await client.get(
        "/api/v1/platform-accounts/oauth/youtube/callback", params={"code": "x", "state": "forged"}
    )
    assert "oauth_error=Sign-in+link+expired" in resp.headers["location"]
    resp = await client.get(
        "/api/v1/platform-accounts/oauth/youtube/callback", params={"error": "access_denied"}
    )
    assert resp.headers["location"].endswith("oauth_error=access_denied")
    assert (await client.get("/api/v1/platform-accounts", headers=editor_headers)).json() == []
