from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import ContentState
from app.workflows.content_pipeline import PIPELINE_ORDER, ContentPipeline, PipelineAgents


class Recorder(BaseAgent):
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        super().__init__()
        self._calls = calls

    async def run(self, state: ContentState) -> dict[str, Any]:
        self._calls.append(self.name)
        return {self.name: {"done": True}} if self.name != "publisher" else {"publish_results": []}


async def test_pipeline_runs_agents_in_order() -> None:
    calls: list[str] = []
    agents = PipelineAgents(**{n: Recorder(n, calls) for n in PIPELINE_ORDER})
    result = await ContentPipeline(agents).run({"content_item_id": "x", "topic": "t"})
    assert calls == ["research", "script", "seo", "video", "publisher"]
    assert result["trace"] == list(PIPELINE_ORDER)
    assert result["research"] == {"done": True} and result["publish_results"] == []


def test_graph_topology() -> None:
    calls: list[str] = []
    pipeline = ContentPipeline(PipelineAgents(**{n: Recorder(n, calls) for n in PIPELINE_ORDER}))
    edges = {(e.source, e.target) for e in pipeline.graph.get_graph().edges}
    assert ("__start__", "research") in edges
    assert ("video", "publisher") in edges
    assert ("publisher", "__end__") in edges
