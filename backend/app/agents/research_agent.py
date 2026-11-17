from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import ContentState
from app.schemas.agent_outputs import ResearchResult
from app.services.integrations.llm import LLMClient

SYSTEM = (
    "You are a meticulous technical researcher preparing material for a 30-60 second educational short. "
    "Collect accurate, specific, verifiable facts (numbers, mechanisms, trade-offs). Avoid fluff and "
    "speculation. Produce a tight outline that a scriptwriter can turn into spoken beats."
)


class ResearchAgent(BaseAgent):
    name = "research"

    def __init__(self, llm: LLMClient) -> None:
        super().__init__()
        self._llm = llm

    async def run(self, state: ContentState) -> dict[str, Any]:
        prompt = (
            f"Series topic: {state['topic']}\n"
            f"This episode ({state.get('sequence_number', 1)} of {state.get('total_items', 1)}): "
            f"{state.get('subtopic') or state['topic']}\n"
            f"Audience: {state.get('target_audience') or 'software engineers'}\n"
            "Return a summary, 4-8 key facts, a 3-6 step outline, and SEO keywords."
        )
        result = await self._llm.complete_json(
            system=SYSTEM, prompt=prompt, schema=ResearchResult, context=self.context(state)
        )
        return {"research": result.model_dump()}
