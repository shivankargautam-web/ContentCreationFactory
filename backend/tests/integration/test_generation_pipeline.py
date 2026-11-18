"""End-to-end: campaign -> LangGraph agents -> persisted video -> scheduled/published jobs -> analytics."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.analytics import AnalyticsSnapshot
from app.models.enums import JobStatus, Platform
from app.repository.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration


async def _generate(container, item_id: str):
    async with container.database.session_factory() as session:
        return await container.generation_service(UnitOfWork(session)).generate(uuid.UUID(item_id))


async def _publish_due(container, now: datetime) -> list[uuid.UUID]:
    async with container.database.session_factory() as session:
        svc = container.publishing_service(UnitOfWork(session))
        ids = await svc.claim_due(now)
        for job_id in ids:
            await svc.publish(job_id)
        return ids


async def test_full_pipeline_schedules_then_publishes(
    client: AsyncClient, editor_headers: dict, container
) -> None:
    created = (
        await client.post(
            "/api/v1/campaigns",
            json={
                "instruction": "Generate 2 shorts about Kafka architecture. Publish one per day at 9AM EST."
            },
            headers=editor_headers,
        )
    ).json()
    first = created["content_items"][0]

    state = await _generate(container, first["id"])
    assert state["trace"] == ["research", "script", "seo", "video", "publisher"]
    assert {r["status"] for r in state["publish_results"]} == {"scheduled"}

    detail = (await client.get(f"/api/v1/content-items/{first['id']}", headers=editor_headers)).json()
    assert detail["status"] == "ready"
    assert detail["seo"]["title"] and detail["script"]["hook"] and detail["research"]["facts"]
    assert detail["video"]["status"] == "ready" and detail["video"]["video_key"].endswith("short.mp4")
    assert {j["platform"] for j in detail["publishing_jobs"]} == {"youtube", "instagram"}
    url = (await client.get(f"/api/v1/content-items/{first['id']}/video-url", headers=editor_headers)).json()[
        "url"
    ]
    assert url.endswith("short.mp4")

    # Nothing is due yet; then jump past the scheduled time.
    assert await _publish_due(container, datetime.now(UTC)) == []
    published = await _publish_due(container, datetime.now(UTC) + timedelta(days=3))
    assert len(published) == 2

    detail = (await client.get(f"/api/v1/content-items/{first['id']}", headers=editor_headers)).json()
    assert detail["status"] == "published"
    assert all(j["status"] == "published" and j["external_url"] for j in detail["publishing_jobs"])

    async with container.database.session_factory() as session:
        uow = UnitOfWork(session)
        jobs = await uow.publishing_jobs.list_for_item(uuid.UUID(first["id"]))
        for job, views in zip(jobs, (100, 250), strict=True):
            await uow.analytics.add(
                AnalyticsSnapshot(
                    publishing_job_id=job.id,
                    platform=job.platform,
                    views=views // 2,
                    collected_at=datetime.now(UTC) - timedelta(hours=2),
                )
            )
            await uow.analytics.add(
                AnalyticsSnapshot(
                    publishing_job_id=job.id,
                    platform=job.platform,
                    views=views,
                    likes=10,
                    collected_at=datetime.now(UTC),
                )
            )
        await uow.commit()

    summary = (await client.get("/api/v1/analytics/summary", headers=editor_headers)).json()
    assert summary["totals"]["views"] == 350 and summary["totals"]["likes"] == 20
    assert summary["published_count"] == 2 and summary["campaign_count"] == 1
    assert {p["platform"] for p in summary["by_platform"]} == {p.value for p in Platform}

    series = (await client.get("/api/v1/analytics/timeseries", headers=editor_headers)).json()
    assert sum(p["views"] for p in series) >= 350
    camp = (await client.get(f"/api/v1/analytics/campaigns/{created['id']}", headers=editor_headers)).json()
    assert camp["totals"]["views"] == 350 and camp["top_content"][0]["views"] == 250


async def test_due_item_publishes_immediately(client: AsyncClient, editor_headers: dict, container) -> None:
    created = (
        await client.post(
            "/api/v1/campaigns",
            json={"instruction": "Make 1 short about Redis streams", "platforms": ["youtube"]},
            headers=editor_headers,
        )
    ).json()
    item_id = created["content_items"][0]["id"]
    async with container.database.session_factory() as session:
        uow = UnitOfWork(session)
        item = await uow.content_items.get(uuid.UUID(item_id))
        item.scheduled_at = datetime.now(UTC) - timedelta(minutes=1)
        await uow.commit()
    state = await _generate(container, item_id)
    assert state["publish_results"][0]["status"] == JobStatus.PUBLISHED.value
    campaign = (await client.get(f"/api/v1/campaigns/{created['id']}", headers=editor_headers)).json()
    assert campaign["status"] == "completed"


async def test_failed_generation_marks_item_failed(
    client: AsyncClient, editor_headers: dict, container
) -> None:
    class BrokenLLM:
        async def complete_json(self, **_):
            raise RuntimeError("LLM down")

        async def generate_image(self, prompt: str):
            return None

    created = (
        await client.post(
            "/api/v1/campaigns",
            json={"instruction": "Make 1 short about Redis streams"},
            headers=editor_headers,
        )
    ).json()
    item_id = created["content_items"][0]["id"]
    container.override_llm(BrokenLLM())
    with pytest.raises(RuntimeError):
        await _generate(container, item_id)
    detail = (await client.get(f"/api/v1/content-items/{item_id}", headers=editor_headers)).json()
    assert detail["status"] == "failed" and "LLM down" in detail["error"]

    regen = await client.post(f"/api/v1/content-items/{item_id}/regenerate", headers=editor_headers)
    assert regen.status_code == 202 and regen.json()["status"] == "pending"
