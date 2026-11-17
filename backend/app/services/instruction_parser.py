"""Turns natural-language instructions into a structured CampaignPlan.

A deterministic rule-based parser extracts explicit values (count, cadence, time, timezone);
an optional LLM pass fills in the remaining semantics (clean topic, tone, audience).
Explicit values from the rules always win, so "9AM EST" is never hallucinated away.
"""

import re
from datetime import date, time, timedelta

from app.core.logging import get_logger
from app.schemas.agent_outputs import SeriesOutline
from app.schemas.campaign import CampaignPlan
from app.services.integrations.llm import LLMClient

logger = get_logger(__name__)

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "a dozen": 12,
    "dozen": 12,
}
_TZ_ALIASES = {
    "est": "America/New_York",
    "edt": "America/New_York",
    "et": "America/New_York",
    "eastern": "America/New_York",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "ct": "America/Chicago",
    "central": "America/Chicago",
    "mst": "America/Denver",
    "mdt": "America/Denver",
    "mt": "America/Denver",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "pt": "America/Los_Angeles",
    "pacific": "America/Los_Angeles",
    "utc": "UTC",
    "gmt": "Europe/London",
    "bst": "Europe/London",
    "cet": "Europe/Berlin",
    "cest": "Europe/Berlin",
    "ist": "Asia/Kolkata",
    "jst": "Asia/Tokyo",
    "aest": "Australia/Sydney",
}
_CONTENT_NOUNS = r"(?:shorts?|videos?|reels?|clips?|posts?|episodes?)"
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class RuleBasedInstructionParser:
    def parse(self, instruction: str, today: date, default_tz: str) -> dict:
        text = " ".join(instruction.strip().split())
        lower = text.lower()
        result: dict = {}

        count_match = re.search(
            rf"\b(\d{{1,3}}|{'|'.join(_NUMBER_WORDS)})\s+(?:[\w-]+\s+){{0,3}}{_CONTENT_NOUNS}\b", lower
        )
        if count_match:
            raw = count_match.group(1)
            result["total_items"] = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw]

        topic_match = re.search(
            r"\b(?:about|on|covering|explaining|for)\s+(.+?)(?=(?:\.|,|;|\bpublish|\bpost|\bupload|\bone\s+per|\bevery|\bdaily|\bweekly|\bstarting|\bat\s+\d|$))",
            text,
            flags=re.IGNORECASE,
        )
        if topic_match:
            result["topic"] = topic_match.group(1).strip(" .,'\"")

        if re.search(r"\b(?:one|1|a)\s+(?:\w+\s+)?(?:per|a|each)\s+day\b|\bdaily\b|\bevery\s*day\b", lower):
            result["interval_hours"] = 24
        elif m := re.search(r"\bevery\s+(\d+)\s+days?\b", lower):
            result["interval_hours"] = int(m.group(1)) * 24
        elif re.search(r"\b(?:per|a|each|every)\s+week\b|\bweekly\b", lower):
            result["interval_hours"] = 24 * 7
        elif m := re.search(r"\bevery\s+(\d+)\s+hours?\b", lower):
            result["interval_hours"] = int(m.group(1))
        elif re.search(r"\b(?:every|per|each|an?)\s+hour\b|\bhourly\b", lower):
            result["interval_hours"] = 1
        elif m := re.search(r"\b(\d+|two|three|four)\s+(?:per|a)\s+day\b", lower):
            raw = m.group(1)
            per_day = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw]
            result["interval_hours"] = max(1, 24 // per_day)

        time_match = re.search(
            r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", lower
        ) or re.search(r"\bat\s+(\d{1,2}):(\d{2})\b()", lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            meridiem = (time_match.group(3) or "").replace(".", "")
            if meridiem == "pm" and hour < 12:
                hour += 12
            if meridiem == "am" and hour == 12:
                hour = 0
            if 0 <= hour < 24 and 0 <= minute < 60:
                result["publish_time"] = time(hour, minute)

        for alias, tz in _TZ_ALIASES.items():
            if re.search(rf"\b{alias}\b", lower):
                result["timezone"] = tz
                break
        if "timezone" not in result and (m := re.search(r"\b([A-Z][a-z]+/[A-Z][A-Za-z_]+)\b", text)):
            result["timezone"] = m.group(1)

        if m := re.search(r"\bstarting\s+(?:on\s+)?(\d{4}-\d{2}-\d{2})\b", lower):
            result["start_date"] = date.fromisoformat(m.group(1))
        elif "starting tomorrow" in lower or "from tomorrow" in lower:
            result["start_date"] = today + timedelta(days=1)
        elif "starting today" in lower:
            result["start_date"] = today
        elif m := re.search(rf"\bstarting\s+(?:on\s+|this\s+|next\s+)?({'|'.join(_WEEKDAYS)})\b", lower):
            delta = (_WEEKDAYS.index(m.group(1)) - today.weekday()) % 7 or 7
            result["start_date"] = today + timedelta(days=delta)

        result.setdefault("timezone", default_tz)
        return result


class InstructionParser:
    def __init__(self, llm: LLMClient | None, rules: RuleBasedInstructionParser | None = None) -> None:
        self._llm = llm
        self._rules = rules or RuleBasedInstructionParser()

    async def parse(self, instruction: str, today: date, default_tz: str) -> CampaignPlan:
        explicit = self._rules.parse(instruction, today, default_tz)
        inferred: dict = {}
        if self._llm is not None:
            try:
                plan = await self._llm.complete_json(
                    system=(
                        "You convert content-campaign instructions into a structured plan. "
                        f"Today is {today.isoformat()}. Default timezone is {default_tz}. "
                        "interval_hours is hours between consecutive posts. publish_time is HH:MM:SS 24h."
                    ),
                    prompt=instruction,
                    schema=CampaignPlan,
                    context={
                        "topic": explicit.get("topic", instruction),
                        "count": explicit.get("total_items", 5),
                    },
                )
                inferred = plan.model_dump(exclude_none=True)
            except NotImplementedError:
                pass
            except Exception as exc:  # LLM is an enhancement; rules remain authoritative
                logger.warning("instruction_parser.llm_failed", error=str(exc))
        merged = {**inferred, **explicit}
        merged.setdefault("topic", instruction[:200])
        merged.setdefault("total_items", 1)
        return CampaignPlan.model_validate(merged)

    async def plan_series(self, topic: str, count: int, tone: str | None, audience: str | None) -> list[str]:
        if self._llm is None:
            return [f"{topic} — part {i + 1}" for i in range(count)]
        outline = await self._llm.complete_json(
            system=(
                "You are a short-form video series planner. Produce distinct, non-overlapping episode angles "
                "that build on each other. Each must be specific enough for a 30-60s vertical video."
            ),
            prompt=(
                f"Topic: {topic}\nNumber of episodes: {count}\nTone: {tone or 'energetic, educational'}\n"
                f"Audience: {audience or 'software engineers'}"
            ),
            schema=SeriesOutline,
            context={"topic": topic, "count": count},
        )
        episodes = outline.episodes[:count]
        while len(episodes) < count:
            episodes.append(f"{topic} — part {len(episodes) + 1}")
        return episodes
