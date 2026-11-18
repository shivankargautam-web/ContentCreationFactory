"""Pure scheduling logic: turns a campaign cadence into concrete UTC publish datetimes (DST-safe)."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def first_slot(
    publish_time: time, tz_name: str, now: datetime, start_date: date | None, lead: timedelta
) -> datetime:
    """First local publish slot on/after start_date that is at least `lead` in the future."""
    tz = ZoneInfo(tz_name)
    local_now = now.astimezone(tz)
    day = start_date or local_now.date()
    candidate = datetime.combine(day, publish_time, tzinfo=tz)
    while candidate < local_now + lead:
        candidate = datetime.combine(candidate.date() + timedelta(days=1), publish_time, tzinfo=tz)
    return candidate


def compute_schedule(
    *,
    count: int,
    publish_time: time,
    tz_name: str,
    interval_hours: int,
    now: datetime | None = None,
    start_date: date | None = None,
    lead: timedelta = timedelta(minutes=30),
) -> list[datetime]:
    """Return `count` publish times in UTC.

    Whole-day intervals keep the same local wall-clock time across DST changes
    ("9AM EST" stays 9AM local); sub-day intervals are applied in absolute time.
    """
    if count < 1:
        return []
    now = now or datetime.now(UTC)
    tz = ZoneInfo(tz_name)
    start = first_slot(publish_time, tz_name, now, start_date, lead)
    slots: list[datetime] = []
    for i in range(count):
        if interval_hours % 24 == 0:
            local_day = start.date() + timedelta(days=i * interval_hours // 24)
            local = datetime.combine(local_day, publish_time, tzinfo=tz)
        else:
            local = (start.astimezone(UTC) + timedelta(hours=i * interval_hours)).astimezone(tz)
        slots.append(local.astimezone(UTC))
    return slots
