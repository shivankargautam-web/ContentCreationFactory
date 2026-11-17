import time
from abc import ABC, abstractmethod
from typing import Any

from app.agents.state import ContentState
from app.core.logging import get_logger
from app.core.telemetry import get_tracer

tracer = get_tracer("app.agents")


class BaseAgent(ABC):
    """Template-method base: adds tracing, timing and structured logging around `run`."""

    name: str = "agent"

    def __init__(self) -> None:
        self._log = get_logger(f"agents.{self.name}")

    async def __call__(self, state: ContentState) -> dict[str, Any]:
        started = time.perf_counter()
        with tracer.start_as_current_span(f"agent.{self.name}") as span:
            span.set_attribute("content_item_id", state.get("content_item_id", ""))
            self._log.info("agent.started", content_item_id=state.get("content_item_id"))
            update = await self.run(state)
            elapsed = round((time.perf_counter() - started) * 1000)
            span.set_attribute("agent.duration_ms", elapsed)
        self._log.info("agent.completed", content_item_id=state.get("content_item_id"), duration_ms=elapsed)
        return {**update, "trace": [self.name]}

    @abstractmethod
    async def run(self, state: ContentState) -> dict[str, Any]: ...

    @staticmethod
    def context(state: ContentState) -> dict[str, Any]:
        return {
            "topic": state.get("topic"),
            "subtopic": state.get("subtopic"),
            "sequence_number": state.get("sequence_number"),
            "total_items": state.get("total_items"),
            "tone": state.get("tone"),
            "target_audience": state.get("target_audience"),
            "research": state.get("research"),
            "script": state.get("script"),
            "seo": state.get("seo"),
        }
