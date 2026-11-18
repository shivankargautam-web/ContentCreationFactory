import operator
from typing import Annotated, Any, TypedDict


class ContentState(TypedDict, total=False):
    """Shared state flowing through the LangGraph content pipeline."""

    content_item_id: str
    campaign_id: str
    topic: str
    subtopic: str
    sequence_number: int
    total_items: int
    tone: str | None
    target_audience: str | None
    platforms: list[str]
    scheduled_at: str

    research: dict[str, Any]
    script: dict[str, Any]
    seo: dict[str, Any]
    video: dict[str, Any]
    publish_results: list[dict[str, Any]]
    trace: Annotated[list[str], operator.add]
