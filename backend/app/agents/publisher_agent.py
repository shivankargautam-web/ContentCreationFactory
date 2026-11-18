from typing import Any, Protocol

from app.agents.base import BaseAgent
from app.agents.state import ContentState


class PublishingGateway(Protocol):
    """Port through which the agent persists artifacts and schedules/publishes to platforms."""

    async def handoff(self, state: ContentState) -> list[dict[str, Any]]: ...


class PublisherAgent(BaseAgent):
    """Uploads to YouTube Shorts / Instagram Reels now if due, otherwise schedules for the slot."""

    name = "publisher"

    def __init__(self, gateway: PublishingGateway) -> None:
        super().__init__()
        self._gateway = gateway

    async def run(self, state: ContentState) -> dict[str, Any]:
        return {"publish_results": await self._gateway.handoff(state)}
