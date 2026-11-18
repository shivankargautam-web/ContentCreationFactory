"use client";

import type { TimeseriesPoint } from "@/lib/types";
import { formatNumber } from "@/lib/format";

type Metric = "views" | "likes" | "comments" | "shares";

/** Dependency-free responsive SVG line/area chart. */
export function LineChart({ data, metric = "views", height = 220 }: { data: TimeseriesPoint[]; metric?: Metric; height?: number }) {
  const width = 720;
  const pad = { top: 16, right: 16, bottom: 28, left: 48 };
  if (data.length === 0) return <div className="chart-empty">No data yet — metrics appear after videos are published.</div>;

  const values = data.map((d) => d[metric]);
  const max = Math.max(1, ...values);
  const x = (i: number) => pad.left + (data.length === 1 ? 0.5 : i / (data.length - 1)) * (width - pad.left - pad.right);
  const y = (v: number) => pad.top + (1 - v / max) * (height - pad.top - pad.bottom);
  const line = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(values.length - 1)},${y(0)} L${x(0)},${y(0)} Z`;
  const ticks = [0, 0.5, 1].map((t) => Math.round(max * t));
  const labelEvery = Math.max(1, Math.ceil(data.length / 6));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="chart" role="img" aria-label={`${metric} over time`}>
      <defs>
        <linearGradient id="area" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.left} x2={width - pad.right} y1={y(t)} y2={y(t)} className="chart-grid" />
          <text x={pad.left - 8} y={y(t) + 4} textAnchor="end" className="chart-label">
            {formatNumber(t)}
          </text>
        </g>
      ))}
      <path d={area} fill="url(#area)" />
      <path d={line} fill="none" stroke="var(--accent)" strokeWidth={2.5} strokeLinejoin="round" />
      {data.map((d, i) => (
        <g key={d.day}>
          <circle cx={x(i)} cy={y(d[metric])} r={3} fill="var(--accent)">
            <title>{`${d.day}: ${formatNumber(d[metric])} ${metric}`}</title>
          </circle>
          {i % labelEvery === 0 && (
            <text x={x(i)} y={height - 8} textAnchor="middle" className="chart-label">
              {new Date(`${d.day}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
