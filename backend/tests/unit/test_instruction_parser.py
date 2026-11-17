from datetime import date, time

import pytest

from app.services.instruction_parser import InstructionParser, RuleBasedInstructionParser
from app.services.integrations.offline_llm import OfflineLLMClient

TODAY = date(2026, 11, 17)  # Tuesday


def parse(text: str) -> dict:
    return RuleBasedInstructionParser().parse(text, TODAY, "UTC")


def test_canonical_example() -> None:
    result = parse("Generate 10 shorts about Kafka architecture. Publish one per day at 9AM EST.")
    assert result["total_items"] == 10
    assert result["topic"] == "Kafka architecture"
    assert result["interval_hours"] == 24
    assert result["publish_time"] == time(9, 0)
    assert result["timezone"] == "America/New_York"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Create five reels on Docker networking, weekly at 6:30 pm PST",
            {
                "total_items": 5,
                "interval_hours": 168,
                "publish_time": time(18, 30),
                "timezone": "America/Los_Angeles",
                "topic": "Docker networking",
            },
        ),
        (
            "Make 3 short videos about Rust ownership every 2 days at 12am UTC",
            {"total_items": 3, "interval_hours": 48, "publish_time": time(0, 0), "timezone": "UTC"},
        ),
        (
            "Generate 4 clips covering Kubernetes operators every 6 hours starting tomorrow",
            {"interval_hours": 6, "start_date": date(2026, 11, 18), "topic": "Kubernetes operators"},
        ),
        (
            "8 shorts about Postgres indexing, two per day, starting monday at 08:15",
            {"interval_hours": 12, "start_date": date(2026, 11, 23), "publish_time": time(8, 15)},
        ),
        (
            "12 shorts about CQRS starting 2026-12-01 at 9am Europe/Paris",
            {"start_date": date(2026, 12, 1), "timezone": "Europe/Paris"},
        ),
    ],
)
def test_variants(text: str, expected: dict) -> None:
    result = parse(text)
    for key, value in expected.items():
        assert result[key] == value, key


async def test_parser_merges_and_validates() -> None:
    parser = InstructionParser(llm=None)
    plan = await parser.parse(
        "Generate 10 shorts about Kafka architecture. Publish one per day at 9AM EST.", TODAY, "UTC"
    )
    assert plan.total_items == 10 and plan.timezone == "America/New_York"


async def test_series_plan_has_distinct_episodes() -> None:
    parser = InstructionParser(llm=OfflineLLMClient())
    episodes = await parser.plan_series("Kafka", 12, None, None)
    assert len(episodes) == 12
    assert len(set(episodes)) == 12
