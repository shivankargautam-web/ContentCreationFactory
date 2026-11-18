from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login

pytestmark = pytest.mark.integration
INSTRUCTION = "Generate 10 shorts about Kafka architecture. Publish one per day at 9AM EST."


async def test_create_campaign_from_instruction(client: AsyncClient, editor_headers: dict, container) -> None:
    resp = await client.post(
        "/api/v1/campaigns",
        json={"instruction": INSTRUCTION, "platforms": ["youtube", "instagram"]},
        headers=editor_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["topic"] == "Kafka architecture"
    assert body["total_items"] == 10 and body["interval_hours"] == 24
    assert body["timezone"] == "America/New_York" and body["publish_time"] == "09:00:00"
    assert body["status"] == "generating"
    items = body["content_items"]
    assert [i["sequence_number"] for i in items] == list(range(1, 11))
    local = [
        datetime.fromisoformat(i["scheduled_at"]).astimezone(ZoneInfo("America/New_York")) for i in items
    ]
    assert all(dt.hour == 9 and dt.minute == 0 for dt in local)
    assert len({dt.date() for dt in local}) == 10
    assert len(set(i["subtopic"] for i in items)) == 10
    assert len(container.dispatcher.generation) == 10  # one generation task queued per short


async def test_list_get_calendar_status_delete(client: AsyncClient, editor_headers: dict) -> None:
    created = (
        await client.post("/api/v1/campaigns", json={"instruction": INSTRUCTION}, headers=editor_headers)
    ).json()
    cid = created["id"]

    listing = (await client.get("/api/v1/campaigns", headers=editor_headers)).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == cid
    assert (await client.get(f"/api/v1/campaigns/{cid}", headers=editor_headers)).status_code == 200

    start = datetime.now(UTC)
    params = {"start": start.isoformat(), "end": (start + timedelta(days=31)).isoformat()}
    events = (await client.get("/api/v1/campaigns/calendar", params=params, headers=editor_headers)).json()
    assert len(events) == 10 and events[0]["campaign_name"] == created["name"]

    paused = await client.patch(
        f"/api/v1/campaigns/{cid}/status", json={"status": "paused"}, headers=editor_headers
    )
    assert paused.json()["status"] == "paused"
    resumed = await client.patch(
        f"/api/v1/campaigns/{cid}/status", json={"status": "scheduled"}, headers=editor_headers
    )
    assert resumed.json()["status"] == "generating"
    bad = await client.patch(
        f"/api/v1/campaigns/{cid}/status", json={"status": "completed"}, headers=editor_headers
    )
    assert bad.status_code == 422

    assert (await client.delete(f"/api/v1/campaigns/{cid}", headers=editor_headers)).status_code == 204
    assert (await client.get(f"/api/v1/campaigns/{cid}", headers=editor_headers)).status_code == 404


async def test_rbac_and_ownership(client: AsyncClient, admin_headers: dict, editor_headers: dict) -> None:
    created = (
        await client.post("/api/v1/campaigns", json={"instruction": INSTRUCTION}, headers=editor_headers)
    ).json()
    other = await register_and_login(client, "other@example.com")
    assert (await client.get(f"/api/v1/campaigns/{created['id']}", headers=other)).status_code == 403
    assert (await client.get("/api/v1/campaigns", headers=other)).json()["total"] == 0
    assert (await client.get(f"/api/v1/campaigns/{created['id']}", headers=admin_headers)).status_code == 200

    users = (await client.get("/api/v1/users", headers=admin_headers)).json()["items"]
    other_id = next(u["id"] for u in users if u["email"] == "other@example.com")
    await client.patch(f"/api/v1/users/{other_id}/role", json={"role": "viewer"}, headers=admin_headers)
    resp = await client.post("/api/v1/campaigns", json={"instruction": INSTRUCTION}, headers=other)
    assert resp.status_code == 403


async def test_validation(client: AsyncClient, editor_headers: dict) -> None:
    resp = await client.post("/api/v1/campaigns", json={"instruction": "short"}, headers=editor_headers)
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "validation_error"
