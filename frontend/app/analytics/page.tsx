"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { LineChart } from "@/components/LineChart";
import { Empty, ErrorBanner, PlatformTag, StatCard } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDuration, formatNumber } from "@/lib/format";
import type { AnalyticsSummary, Campaign, CampaignAnalytics, TimeseriesPoint } from "@/lib/types";

type Metric = "views" | "likes" | "comments" | "shares";

function Analytics() {
  const params = useSearchParams();
  const [days, setDays] = useState(30);
  const [metric, setMetric] = useState<Metric>("views");
  const [campaignId, setCampaignId] = useState(params.get("campaign") ?? "");
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [series, setSeries] = useState<TimeseriesPoint[]>([]);
  const [campaignStats, setCampaignStats] = useState<CampaignAnalytics | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    Promise.all([api.analyticsSummary(), api.listCampaigns({ limit: 100 })])
      .then(([s, c]) => {
        setSummary(s);
        setCampaigns(c.items);
      })
      .catch(setError);
  }, []);

  useEffect(() => {
    if (campaignId) {
      api
        .campaignAnalytics(campaignId, days)
        .then((a) => {
          setCampaignStats(a);
          setSeries(a.timeseries);
        })
        .catch(setError);
    } else {
      setCampaignStats(null);
      api.timeseries(days).then(setSeries).catch(setError);
    }
  }, [campaignId, days]);

  const totals = campaignStats?.totals ?? summary?.totals;

  return (
    <AppShell
      title="Analytics"
      actions={
        <>
          <select aria-label="Campaign" value={campaignId} onChange={(e) => setCampaignId(e.target.value)}>
            <option value="">All campaigns</option>
            {campaigns.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select aria-label="Range" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[7, 30, 90, 365].map((d) => (
              <option key={d} value={d}>
                Last {d} days
              </option>
            ))}
          </select>
        </>
      }
    >
      <ErrorBanner error={error} />
      <section className="grid grid-4">
        <StatCard label="Views" value={totals ? formatNumber(totals.views) : "—"} />
        <StatCard label="Likes" value={totals ? formatNumber(totals.likes) : "—"} />
        <StatCard label="Comments" value={totals ? formatNumber(totals.comments) : "—"} />
        <StatCard label="Watch time" value={totals ? formatDuration(totals.watch_time_seconds) : "—"} />
      </section>

      <div className="card">
        <div className="card-header">
          <h2>Performance over time</h2>
          <div className="tabs">
            {(["views", "likes", "comments", "shares"] as Metric[]).map((m) => (
              <button key={m} className={`tab ${metric === m ? "active" : ""}`} onClick={() => setMetric(m)}>
                {m[0]!.toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <LineChart data={series} metric={metric} />
      </div>

      {campaignStats ? (
        <div className="card">
          <div className="card-header">
            <h2>Top content</h2>
          </div>
          {campaignStats.top_content.length === 0 ? (
            <Empty title="Nothing published yet" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Platform</th>
                  <th>Views</th>
                  <th>Likes</th>
                  <th>Comments</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {campaignStats.top_content.map((c) => (
                  <tr key={`${c.content_item_id}-${c.platform}`}>
                    <td>{c.title}</td>
                    <td>
                      <PlatformTag platform={c.platform} />
                    </td>
                    <td>{formatNumber(c.views)}</td>
                    <td>{formatNumber(c.likes)}</td>
                    <td>{formatNumber(c.comments)}</td>
                    <td>
                      {c.external_url && (
                        <a href={c.external_url} target="_blank" rel="noreferrer">
                          Open ↗
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : (
        summary && (
          <div className="card">
            <div className="card-header">
              <h2>By platform</h2>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>Published</th>
                  <th>Views</th>
                  <th>Likes</th>
                  <th>Comments</th>
                  <th>Shares</th>
                </tr>
              </thead>
              <tbody>
                {summary.by_platform.map((p) => (
                  <tr key={p.platform}>
                    <td>
                      <PlatformTag platform={p.platform} />
                    </td>
                    <td>{p.published_count}</td>
                    <td>{formatNumber(p.views)}</td>
                    <td>{formatNumber(p.likes)}</td>
                    <td>{formatNumber(p.comments)}</td>
                    <td>{formatNumber(p.shares)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </AppShell>
  );
}

export default function AnalyticsPage() {
  return (
    <Suspense>
      <Analytics />
    </Suspense>
  );
}
