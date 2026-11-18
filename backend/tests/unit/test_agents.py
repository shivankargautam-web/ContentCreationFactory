from pathlib import Path

from app.agents import PublisherAgent, ResearchAgent, ScriptAgent, SEOAgent, VideoAgent
from app.agents.state import ContentState
from app.services.integrations.offline_llm import OfflineLLMClient
from app.services.integrations.storage import LocalObjectStorage
from tests.conftest import FakeRenderer, FakeTTS

STATE: ContentState = {
    "content_item_id": "item-1",
    "campaign_id": "camp-1",
    "topic": "Kafka architecture",
    "subtopic": "How Kafka partitions work",
    "sequence_number": 1,
    "total_items": 10,
    "platforms": ["youtube"],
}


async def test_research_script_seo_chain() -> None:
    llm = OfflineLLMClient()
    state = dict(STATE)
    state.update(await ResearchAgent(llm)(state))
    assert len(state["research"]["facts"]) >= 3
    state.update(await ScriptAgent(llm)(state))
    assert state["script"]["hook"] and state["script"]["cta"]
    assert state["script"]["full_text"].startswith(state["script"]["hook"])
    update = await SEOAgent(llm)(state)
    assert update["trace"] == ["seo"]
    assert len(update["seo"]["title"]) <= 100
    assert all(tag.startswith("#") for tag in update["seo"]["hashtags"])


async def test_video_agent_renders_and_stores(tmp_path: Path) -> None:
    llm = OfflineLLMClient()
    state = dict(STATE)
    state.update(await ResearchAgent(llm)(state))
    state.update(await ScriptAgent(llm)(state))
    renderer = FakeRenderer()
    storage = LocalObjectStorage(str(tmp_path))
    update = await VideoAgent(llm, FakeTTS(), renderer, storage)(state)
    video = update["video"]
    assert video["video_key"] == "campaigns/camp-1/items/item-1/short.mp4"
    assert video["audio_key"].endswith("voiceover.mp3")
    assert (tmp_path / video["video_key"]).exists()
    # Scenes are stretched to the (fake) 30s voiceover length.
    assert abs(sum(s["duration_seconds"] for s in video["storyboard"]) - 30.0) < 0.05
    assert "-->" in video["captions_srt"]
    assert renderer.calls[0].audio_path is not None


async def test_publisher_agent_delegates_to_gateway() -> None:
    class Gateway:
        async def handoff(self, state: ContentState) -> list[dict]:
            return [{"platform": p, "status": "scheduled"} for p in state["platforms"]]

    update = await PublisherAgent(Gateway())(STATE)
    assert update["publish_results"] == [{"platform": "youtube", "status": "scheduled"}]
