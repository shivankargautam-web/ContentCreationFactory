from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import ContentState
from app.schemas.agent_outputs import ScriptResult
from app.services.integrations.llm import LLMClient

SYSTEM = (
    "You are a viral short-form scriptwriter (YouTube Shorts / Instagram Reels). Write a spoken script: "
    "a scroll-stopping hook (max 12 words), 3-6 punchy body beats (max 20 words each, one idea per beat), "
    "and a clear call-to-action. Conversational, concrete, no filler. Total under 55 seconds when spoken."
)


class ScriptAgent(BaseAgent):
    name = "script"

    def __init__(self, llm: LLMClient) -> None:
        super().__init__()
        self._llm = llm

    async def run(self, state: ContentState) -> dict[str, Any]:
        research = state.get("research") or {}
        prompt = (
            f"Episode: {state.get('subtopic') or state['topic']}\n"
            f"Tone: {state.get('tone') or 'energetic and educational'}\n"
            f"Facts: {research.get('facts')}\nOutline: {research.get('outline')}\n"
            f"This is part {state.get('sequence_number', 1)} of {state.get('total_items', 1)} — "
            "the CTA should invite viewers to follow for the next part."
        )
        result = await self._llm.complete_json(
            system=SYSTEM, prompt=prompt, schema=ScriptResult, context=self.context(state)
        )
        return {"script": {**result.model_dump(), "full_text": result.full_text}}
