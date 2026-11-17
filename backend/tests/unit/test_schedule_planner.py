from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.scheduler.schedule_planner import compute_schedule

NY = ZoneInfo("America/New_York")


def test_ten_daily_at_9am_est() -> None:
    now = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)  # 7AM New York
    slots = compute_schedule(
        count=10, publish_time=time(9), tz_name="America/New_York", interval_hours=24, now=now
    )
    assert len(slots) == 10
    assert slots[0] == datetime(2026, 1, 10, 14, 0, tzinfo=UTC)  # same day 9AM EST
    assert all(b - a == timedelta(days=1) for a, b in zip(slots, slots[1:], strict=False))
    assert all(s.astimezone(NY).hour == 9 for s in slots)


def test_rolls_to_next_day_when_time_passed() -> None:
    now = datetime(2026, 1, 10, 15, 0, tzinfo=UTC)  # 10AM New York
    slots = compute_schedule(
        count=1, publish_time=time(9), tz_name="America/New_York", interval_hours=24, now=now
    )
    assert slots[0].astimezone(NY).date() == date(2026, 1, 11)


def test_dst_transition_keeps_local_wall_clock() -> None:
    now = datetime(2026, 10, 29, 0, 0, tzinfo=UTC)
    slots = compute_schedule(
        count=6,
        publish_time=time(9),
        tz_name="America/New_York",
        interval_hours=24,
        now=now,
        start_date=date(2026, 10, 29),
    )
    assert [s.astimezone(NY).hour for s in slots] == [9] * 6
    assert slots[0].hour == 13 and slots[-1].hour == 14  # EDT -> EST


def test_hourly_and_weekly_intervals() -> None:
    now = datetime(2026, 3, 2, 0, 0, tzinfo=UTC)
    hourly = compute_schedule(count=3, publish_time=time(10), tz_name="UTC", interval_hours=6, now=now)
    assert [s.hour for s in hourly] == [10, 16, 22]
    weekly = compute_schedule(count=3, publish_time=time(10), tz_name="UTC", interval_hours=168, now=now)
    assert (weekly[2] - weekly[0]).days == 14


def test_zero_count() -> None:
    assert compute_schedule(count=0, publish_time=time(9), tz_name="UTC", interval_hours=24) == []
