from typing import Any

from app.agents.base import BaseAgent
from app.agents.state import ContentState
from app.schemas.agent_outputs import SEOResult
from app.services.integrations.llm import LLMClient

SYSTEM = (
    "You are a YouTube Shorts and Instagram Reels SEO strategist. Write a curiosity-driven title "
    "(max 70 characters, front-load the keyword), a 2-3 sentence description with keywords, 5-10 relevant "
    "hashtags (mix of broad and niche, always include #shorts), and 8-15 search tags."
)


class SEOAgent(BaseAgent):
    name = "seo"

    def __init__(self, llm: LLMClient) -> None:
        super().__init__()
        self._llm = llm

    async def run(self, state: ContentState) -> dict[str, Any]:
        script = state.get("script") or {}
        research = state.get("research") or {}
        prompt = (
            f"Topic: {state['topic']}\nEpisode: {state.get('subtopic')}\n"
            f"Hook: {script.get('hook')}\nScript: {script.get('full_text')}\n"
            f"Keywords: {research.get('keywords')}"
        )
        result = await self._llm.complete_json(
            system=SYSTEM, prompt=prompt, schema=SEOResult, context=self.context(state)
        )
        return {"seo": {**result.model_dump(), "caption": result.caption}}
