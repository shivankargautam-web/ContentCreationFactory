"""Deterministic LLM stand-in used when no OpenAI key is configured (local dev, demos, tests)."""

from typing import Any, TypeVar

from pydantic import BaseModel

from app.schemas.agent_outputs import (
    ResearchResult,
    ScriptResult,
    SEOResult,
    SeriesOutline,
    Storyboard,
    StoryboardScene,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

_ANGLES = [
    "What is {t} and why it matters",
    "Core building blocks of {t}",
    "How {t} works under the hood",
    "Top 3 mistakes engineers make with {t}",
    "{t} best practices for production",
    "Scaling {t}: what changes at 10x",
    "{t} vs the alternatives",
    "Real-world use cases of {t}",
    "Debugging {t} like a pro",
    "The future of {t}",
]
_PALETTE = ["#0F172A", "#1E3A8A", "#7C2D12", "#14532D", "#581C87", "#164E63"]


class OfflineLLMClient:
    async def complete_json(
        self, *, system: str, prompt: str, schema: type[SchemaT], context: dict[str, Any] | None = None
    ) -> SchemaT:
        ctx = context or {}
        topic = str(ctx.get("topic", "this topic"))
        angle = str(ctx.get("subtopic") or topic)
        builders = {
            SeriesOutline: lambda: self._outline(topic, int(ctx.get("count", 5))),
            ResearchResult: lambda: self._research(topic, angle),
            ScriptResult: lambda: self._script(angle, ctx),
            SEOResult: lambda: self._seo(topic, angle),
            Storyboard: lambda: self._storyboard(ctx),
        }
        builder = builders.get(schema)
        if builder is None:
            raise NotImplementedError(f"OfflineLLMClient cannot produce {schema.__name__}")
        return schema.model_validate(builder().model_dump())

    async def generate_image(self, prompt: str) -> bytes | None:
        return None

    @staticmethod
    def _outline(topic: str, count: int) -> SeriesOutline:
        episodes = [_ANGLES[i % len(_ANGLES)].format(t=topic) for i in range(count)]
        episodes = [
            e if i < len(_ANGLES) else f"{e} (part {i // len(_ANGLES) + 1})" for i, e in enumerate(episodes)
        ]
        return SeriesOutline(episodes=episodes)

    @staticmethod
    def _research(topic: str, angle: str) -> ResearchResult:
        return ResearchResult(
            summary=f"{angle}: a concise primer on {topic} for busy engineers.",
            facts=[
                f"{topic} solves a specific class of problems that appear at scale.",
                f"Understanding the core abstractions of {topic} prevents most production incidents.",
                f"Teams adopting {topic} typically trade simplicity for throughput and resilience.",
                f"Observability is critical when operating {topic} in production.",
            ],
            outline=[f"Hook on {angle}", "Explain the core idea", "Show a concrete example", "Key takeaway"],
            keywords=[topic, "engineering", "architecture"],
        )

    @staticmethod
    def _script(angle: str, ctx: dict[str, Any]) -> ScriptResult:
        facts = (ctx.get("research") or {}).get("facts") or [f"{angle} is easier than you think."]
        return ScriptResult(
            hook=f"Stop scrolling: {angle} in under a minute.",
            body=[str(f) for f in facts[:3]] + ["Here is the one thing to remember."],
            cta="Follow for the next part of the series!",
            estimated_duration_seconds=40,
        )

    @staticmethod
    def _seo(topic: str, angle: str) -> SEOResult:
        slug = "".join(ch for ch in topic.title() if ch.isalnum())
        return SEOResult(
            title=f"{angle} #shorts"[:100],
            description=f"{angle}. A quick, practical breakdown of {topic} for developers and architects.",
            hashtags=[f"#{slug}", "#SoftwareEngineering", "#SystemDesign", "#Shorts", "#TechTok"],
            tags=[topic, "system design", "software architecture", "programming"],
        )

    @staticmethod
    def _storyboard(ctx: dict[str, Any]) -> Storyboard:
        script = ctx.get("script") or {}
        lines = (
            [script.get("hook", "Intro")]
            + list(script.get("body", ["Main point"]))
            + [script.get("cta", "Follow")]
        )
        scenes = [
            StoryboardScene(
                index=i,
                narration=line,
                on_screen_text=line[:110],
                visual_prompt=f"Minimal tech illustration, vertical 9:16, depicting: {line}",
                duration_seconds=max(2.5, min(8.0, len(line.split()) / 2.6)),
                background_color=_PALETTE[i % len(_PALETTE)],
            )
            for i, line in enumerate(lines)
        ]
        return Storyboard(scenes=scenes)
