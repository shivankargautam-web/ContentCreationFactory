import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_connect_list_disconnect(client: AsyncClient, editor_headers: dict) -> None:
    payload = {
        "platform": "instagram",
        "account_name": "@acf",
        "external_account_id": "17841400000000000",
        "access_token": "EAAG-super-secret",
        "scopes": ["instagram_content_publish"],
    }
    created = await client.post("/api/v1/platform-accounts", json=payload, headers=editor_headers)
    assert created.status_code == 201
    assert "access_token" not in created.text and "super-secret" not in created.text

    again = await client.post("/api/v1/platform-accounts", json=payload, headers=editor_headers)
    assert again.json()["id"] == created.json()["id"]  # upsert on identity

    listed = (await client.get("/api/v1/platform-accounts", headers=editor_headers)).json()
    assert len(listed) == 1
    resp = await client.delete(f"/api/v1/platform-accounts/{created.json()['id']}", headers=editor_headers)
    assert resp.status_code == 204
    assert (await client.get("/api/v1/platform-accounts", headers=editor_headers)).json() == []
