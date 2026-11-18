"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { SchedulingCalendar } from "@/components/Calendar";
import { CreateCampaignForm } from "@/components/CreateCampaignForm";
import { Empty, ErrorBanner, PlatformTag, StatCard, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { formatCadence, formatNumber } from "@/lib/format";
import type { AnalyticsSummary, Campaign } from "@/lib/types";

export default function DashboardPage() {
  const { can } = useAuth();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    Promise.all([api.analyticsSummary(), api.listCampaigns({ limit: 5 })])
      .then(([s, c]) => {
        setSummary(s);
        setCampaigns(c.items);
      })
      .catch(setError);
  }, [reload]);

  return (
    <AppShell
      title="Dashboard"
      actions={
        <Link href="/campaign" className="btn btn-ghost">
          All campaigns
        </Link>
      }
    >
      <ErrorBanner error={error} />
      <section className="grid grid-4">
        <StatCard label="Campaigns" value={summary?.campaign_count ?? "—"} />
        <StatCard label="Scheduled posts" value={summary?.scheduled_count ?? "—"} />
        <StatCard label="Published" value={summary?.published_count ?? "—"} hint={summary?.failed_count ? `${summary.failed_count} failed` : undefined} />
        <StatCard label="Total views" value={summary ? formatNumber(summary.totals.views) : "—"} />
      </section>

      <section className="grid grid-2">
        {can("admin", "editor") && (
          <div className="card">
            <div className="card-header">
              <h2>Create campaign</h2>
            </div>
            <CreateCampaignForm compact onCreated={() => setReload((n) => n + 1)} />
          </div>
        )}
        <div className="card">
          <div className="card-header">
            <h2>Recent campaigns</h2>
            <Link href="/campaign" className="small">
              View all →
            </Link>
          </div>
          {campaigns.length === 0 ? (
            <Empty title="No campaigns yet">Describe what you want and the agents will do the rest.</Empty>
          ) : (
            <ul className="list">
              {campaigns.map((c) => (
                <li key={c.id}>
                  <Link href={`/campaign?id=${c.id}`} className="list-row">
                    <div>
                      <div className="list-title">{c.name}</div>
                      <div className="muted small">
                        {c.total_items} shorts · {formatCadence(c.interval_hours)} at {c.publish_time.slice(0, 5)} ({c.timezone})
                      </div>
                    </div>
                    <div className="row gap-sm">
                      {c.platforms.map((p) => (
                        <PlatformTag key={p} platform={p} />
                      ))}
                      <StatusBadge status={c.status} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <SchedulingCalendar key={reload} />
    </AppShell>
  );
}
