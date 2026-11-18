"""Structured outputs produced by the LLM-backed agents (validated with Pydantic v2)."""

from pydantic import BaseModel, Field, field_validator


class SeriesOutline(BaseModel):
    episodes: list[str] = Field(min_length=1, description="One distinct angle/sub-topic per short")


class ResearchResult(BaseModel):
    summary: str
    facts: list[str] = Field(min_length=3, max_length=12)
    outline: list[str] = Field(min_length=3, max_length=8)
    keywords: list[str] = Field(default_factory=list)


class ScriptResult(BaseModel):
    hook: str = Field(description="First 3 seconds, pattern-interrupt line")
    body: list[str] = Field(min_length=2, description="Short spoken beats")
    cta: str
    estimated_duration_seconds: int = Field(default=45, ge=10, le=90)

    @property
    def full_text(self) -> str:
        return " ".join([self.hook, *self.body, self.cta])


class SEOResult(BaseModel):
    title: str = Field(max_length=100)
    description: str = Field(max_length=5000)
    hashtags: list[str] = Field(min_length=3, max_length=15)
    tags: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("hashtags")
    @classmethod
    def _normalize_hashtags(cls, value: list[str]) -> list[str]:
        out: list[str] = []
        for tag in value:
            clean = "#" + "".join(ch for ch in tag.lstrip("#") if ch.isalnum() or ch == "_")
            if len(clean) > 1 and clean.lower() not in {t.lower() for t in out}:
                out.append(clean)
        return out

    @property
    def caption(self) -> str:
        return f"{self.title}\n\n{self.description}\n\n{' '.join(self.hashtags)}".strip()


class StoryboardScene(BaseModel):
    index: int = Field(ge=0)
    narration: str
    on_screen_text: str = Field(max_length=120)
    visual_prompt: str
    duration_seconds: float = Field(gt=0, le=20)
    background_color: str = Field(default="#1E293B", pattern=r"^#[0-9A-Fa-f]{6}$")


class Storyboard(BaseModel):
    scenes: list[StoryboardScene] = Field(min_length=2, max_length=12)

    @property
    def total_duration(self) -> float:
        return round(sum(s.duration_seconds for s in self.scenes), 2)
