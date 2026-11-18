"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { CampaignDetailView } from "@/components/CampaignDetailView";
import { CreateCampaignForm } from "@/components/CreateCampaignForm";
import { Empty, ErrorBanner, PlatformTag, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { formatCadence } from "@/lib/format";
import type { Campaign, CampaignStatus } from "@/lib/types";

const PAGE_SIZE = 20;
const STATUSES: Array<CampaignStatus | ""> = ["", "generating", "scheduled", "completed", "paused", "failed"];

function CampaignList() {
  const { can } = useAuth();
  const [items, setItems] = useState<Campaign[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState<CampaignStatus | "">("");
  const [error, setError] = useState<unknown>(null);
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    api
      .listCampaigns({ status: status || undefined, limit: PAGE_SIZE, offset })
      .then((page) => {
        setItems(page.items);
        setTotal(page.total);
      })
      .catch(setError);
  }, [status, offset]);

  return (
    <AppShell
      title="Campaigns"
      actions={
        can("admin", "editor") && (
          <button className="btn btn-primary" onClick={() => setShowCreate((s) => !s)}>
            {showCreate ? "Close" : "New campaign"}
          </button>
        )
      }
    >
      {showCreate && (
        <div className="card">
          <div className="card-header">
            <h2>New campaign</h2>
          </div>
          <CreateCampaignForm />
        </div>
      )}
      <ErrorBanner error={error} />
      <div className="card">
        <div className="card-header">
          <h2>{total} campaign{total === 1 ? "" : "s"}</h2>
          <select
            aria-label="Filter by status"
            value={status}
            onChange={(e) => {
              setOffset(0);
              setStatus(e.target.value as CampaignStatus | "");
            }}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s ? s[0]!.toUpperCase() + s.slice(1) : "All statuses"}
              </option>
            ))}
          </select>
        </div>
        {items.length === 0 ? (
          <Empty title="No campaigns found" />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Campaign</th>
                <th>Shorts</th>
                <th>Cadence</th>
                <th>Platforms</th>
                <th>Starts</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link href={`/campaign?id=${c.id}`} className="list-title">
                      {c.name}
                    </Link>
                    <div className="muted small truncate">{c.instruction}</div>
                  </td>
                  <td>{c.total_items}</td>
                  <td>
                    {formatCadence(c.interval_hours)} · {c.publish_time.slice(0, 5)}
                    <div className="muted small">{c.timezone}</div>
                  </td>
                  <td>
                    <div className="row gap-sm">
                      {c.platforms.map((p) => (
                        <PlatformTag key={p} platform={p} />
                      ))}
                    </div>
                  </td>
                  <td>{c.start_date}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {total > PAGE_SIZE && (
          <div className="pager">
            <button className="btn btn-ghost btn-sm" disabled={offset === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>
              Previous
            </button>
            <span className="muted small">
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
            </span>
            <button className="btn btn-ghost btn-sm" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
              Next
            </button>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function CampaignRoute() {
  const id = useSearchParams().get("id");
  return id ? <CampaignDetailView id={id} /> : <CampaignList />;
}

export default function CampaignPage() {
  return (
    <Suspense>
      <CampaignRoute />
    </Suspense>
  );
}
