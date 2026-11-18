"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { monthGrid, sameDay } from "@/lib/format";
import type { CalendarEvent } from "@/lib/types";
import { ErrorBanner } from "./ui";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function SchedulingCalendar() {
  const [anchor, setAnchor] = useState(() => new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [error, setError] = useState<unknown>(null);
  const days = useMemo(() => monthGrid(anchor), [anchor]);

  useEffect(() => {
    const start = days[0]!;
    const end = new Date(days[days.length - 1]!);
    end.setDate(end.getDate() + 1);
    api
      .calendar(start, end)
      .then((e) => {
        setEvents(e);
        setError(null);
      })
      .catch(setError);
  }, [days]);

  const shift = (months: number) => setAnchor((a) => new Date(a.getFullYear(), a.getMonth() + months, 1));
  const today = new Date();

  return (
    <div className="card">
      <div className="card-header">
        <h2>Scheduling calendar</h2>
        <div className="row gap-sm">
          <button className="btn btn-ghost btn-sm" onClick={() => shift(-1)} aria-label="Previous month">
            ‹
          </button>
          <span className="calendar-title">{anchor.toLocaleString("en-US", { month: "long", year: "numeric" })}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => shift(1)} aria-label="Next month">
            ›
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setAnchor(new Date())}>
            Today
          </button>
        </div>
      </div>
      <ErrorBanner error={error} />
      <div className="calendar">
        {WEEKDAYS.map((d) => (
          <div key={d} className="calendar-weekday">
            {d}
          </div>
        ))}
        {days.map((day) => {
          const dayEvents = events.filter((e) => sameDay(new Date(e.scheduled_at), day));
          return (
            <div
              key={day.toISOString()}
              className={`calendar-day ${day.getMonth() !== anchor.getMonth() ? "muted" : ""} ${sameDay(day, today) ? "today" : ""}`}
            >
              <div className="calendar-date">{day.getDate()}</div>
              {dayEvents.slice(0, 3).map((e) => (
                <Link
                  key={e.content_item_id}
                  href={`/campaign?id=${e.campaign_id}`}
                  className={`calendar-event status-${e.status}`}
                  title={`${e.campaign_name}: ${e.title}`}
                >
                  <span className="calendar-time">
                    {new Date(e.scheduled_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
                  </span>{" "}
                  {e.title}
                </Link>
              ))}
              {dayEvents.length > 3 && <div className="calendar-more">+{dayEvents.length - 3} more</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
