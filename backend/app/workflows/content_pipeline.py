"""LangGraph workflow: START -> Research -> Script -> SEO -> Video -> Publisher -> END."""

from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.base import BaseAgent
from app.agents.state import ContentState

PIPELINE_ORDER = ("research", "script", "seo", "video", "publisher")


@dataclass(frozen=True)
class PipelineAgents:
    research: BaseAgent
    script: BaseAgent
    seo: BaseAgent
    video: BaseAgent
    publisher: BaseAgent


def build_content_graph(agents: PipelineAgents) -> Any:
    graph = StateGraph(ContentState)
    for name in PIPELINE_ORDER:
        graph.add_node(name, getattr(agents, name))
    graph.add_edge(START, PIPELINE_ORDER[0])
    for current, nxt in zip(PIPELINE_ORDER, PIPELINE_ORDER[1:], strict=False):
        graph.add_edge(current, nxt)
    graph.add_edge(PIPELINE_ORDER[-1], END)
    return graph.compile()


class ContentPipeline:
    def __init__(self, agents: PipelineAgents) -> None:
        self._graph = build_content_graph(agents)

    @property
    def graph(self) -> Any:
        return self._graph

    async def run(self, state: ContentState) -> ContentState:
        return await self._graph.ainvoke({**state, "trace": []})
