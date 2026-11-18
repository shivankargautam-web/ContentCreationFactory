"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatCadence, formatDateTime } from "@/lib/format";
import type { CampaignDetail, ContentItemDetail } from "@/lib/types";
import { AppShell } from "./AppShell";
import { useAuth } from "./AuthProvider";
import { ErrorBanner, PlatformTag, StatusBadge } from "./ui";

const ACTIVE = new Set(["pending", "generating", "publishing"]);

export function CampaignDetailView({ id }: { id: string }) {
  const router = useRouter();
  const { can } = useAuth();
  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const editable = can("admin", "editor");

  const load = useCallback(() => api.getCampaign(id).then(setCampaign).catch(setError), [id]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll while agents are still working on any item.
  const busy = campaign?.content_items.some((i) => ACTIVE.has(i.status)) ?? false;
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [busy, load]);

  async function act(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      await load();
    } catch (err) {
      setError(err);
    }
  }

  async function remove() {
    if (!confirm("Delete this campaign and all its content? This cannot be undone.")) return;
    try {
      await api.deleteCampaign(id);
      router.push("/campaign");
    } catch (err) {
      setError(err);
    }
  }

  if (!campaign) {
    return (
      <AppShell title="Campaign">
        <ErrorBanner error={error} />
        {!error && <div className="spinner" />}
      </AppShell>
    );
  }

  const done = campaign.content_items.filter((i) => i.status === "published").length;
  const ready = campaign.content_items.filter((i) => ["ready", "publishing", "published"].includes(i.status)).length;

  return (
    <AppShell
      title={campaign.name}
      actions={
        <>
          <Link href="/campaign" className="btn btn-ghost">
            ← Campaigns
          </Link>
          <Link href={`/analytics?campaign=${campaign.id}`} className="btn btn-ghost">
            Analytics
          </Link>
          {editable && campaign.status !== "paused" && campaign.status !== "completed" && (
            <button className="btn btn-ghost" onClick={() => act(() => api.setCampaignStatus(id, "paused"))}>
              Pause
            </button>
          )}
          {editable && campaign.status === "paused" && (
            <button className="btn btn-ghost" onClick={() => act(() => api.setCampaignStatus(id, "scheduled"))}>
              Resume
            </button>
          )}
          {editable && campaign.content_items.some((i) => i.status === "failed" || i.status === "pending") && (
            <button className="btn btn-primary" onClick={() => act(() => api.generateCampaign(id))}>
              Generate pending
            </button>
          )}
          {editable && (
            <button className="btn btn-danger" onClick={remove}>
              Delete
            </button>
          )}
        </>
      }
    >
      <ErrorBanner error={error} />
      <div className="card">
        <div className="detail-grid">
          <div>
            <div className="stat-label">Instruction</div>
            <p className="quote">“{campaign.instruction}”</p>
          </div>
          <dl className="facts">
            <dt>Status</dt>
            <dd>
              <StatusBadge status={campaign.status} />
            </dd>
            <dt>Topic</dt>
            <dd>{campaign.topic}</dd>
            <dt>Schedule</dt>
            <dd>
              {campaign.total_items} × {formatCadence(campaign.interval_hours).toLowerCase()} at {campaign.publish_time.slice(0, 5)} (
              {campaign.timezone}) from {campaign.start_date}
            </dd>
            <dt>Platforms</dt>
            <dd className="row gap-sm">
              {campaign.platforms.map((p) => (
                <PlatformTag key={p} platform={p} />
              ))}
            </dd>
            <dt>Progress</dt>
            <dd>
              <div className="progress" aria-label="Generation progress">
                <div className="progress-ready" style={{ width: `${(ready / campaign.total_items) * 100}%` }} />
                <div className="progress-done" style={{ width: `${(done / campaign.total_items) * 100}%` }} />
              </div>
              <span className="muted small">
                {ready}/{campaign.total_items} generated · {done} published
              </span>
            </dd>
          </dl>
        </div>
      </div>

      <div className="split">
        <div className="card">
          <div className="card-header">
            <h2>Content queue</h2>
            {busy && <span className="muted small">Agents working… auto-refreshing</span>}
          </div>
          <ul className="list">
            {campaign.content_items.map((item) => (
              <li key={item.id}>
                <button className={`list-row ${selected === item.id ? "selected" : ""}`} onClick={() => setSelected(item.id)}>
                  <div className="seq">#{item.sequence_number}</div>
                  <div className="grow">
                    <div className="list-title">{item.seo?.title ?? item.subtopic ?? "Untitled"}</div>
                    <div className="muted small">{formatDateTime(item.scheduled_at, campaign.timezone)}</div>
                  </div>
                  <StatusBadge status={item.status} />
                </button>
              </li>
            ))}
          </ul>
        </div>
        {selected ? (
          <ContentItemPanel key={selected} id={selected} timezone={campaign.timezone} editable={editable} onChange={load} />
        ) : (
          <div className="card empty">
            <div className="empty-title">Select a short</div>
            See its research, script, SEO metadata, storyboard, rendered video, and publishing status.
          </div>
        )}
      </div>
    </AppShell>
  );
}

function ContentItemPanel({ id, timezone, editable, onChange }: { id: string; timezone: string; editable: boolean; onChange: () => void }) {
  const [item, setItem] = useState<ContentItemDetail | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [tab, setTab] = useState<"script" | "seo" | "research" | "storyboard">("script");
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => api.getContentItem(id).then(setItem).catch(setError), [id]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (!item || !ACTIVE.has(item.status)) return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [item, load]);
  useEffect(() => {
    if (item?.video?.video_key) api.videoUrl(id).then((r) => setVideoUrl(r.url)).catch(() => setVideoUrl(null));
  }, [id, item?.video?.video_key]);

  if (!item) return <div className="card">{error ? <ErrorBanner error={error} /> : <div className="spinner" />}</div>;

  return (
    <div className="card">
      <div className="card-header">
        <h2>
          #{item.sequence_number} {item.seo?.title ?? item.subtopic}
        </h2>
        {editable && (item.status === "failed" || item.status === "ready") && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={() =>
              api
                .regenerateContentItem(id)
                .then(() => {
                  load();
                  onChange();
                })
                .catch(setError)
            }
          >
            Regenerate
          </button>
        )}
      </div>
      <ErrorBanner error={error} />
      {item.error && <div className="alert alert-error">{item.error}</div>}
      <div className="item-layout">
        <div className="phone">
          {videoUrl ? (
            <video src={videoUrl} controls playsInline className="phone-video" />
          ) : (
            <div className="phone-placeholder">
              {ACTIVE.has(item.status) ? "Rendering…" : item.video?.status === "failed" ? "Render failed" : "No video yet"}
            </div>
          )}
        </div>
        <div className="grow">
          <div className="tabs" role="tablist">
            {(["script", "seo", "research", "storyboard"] as const).map((t) => (
              <button key={t} role="tab" aria-selected={tab === t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
                {t === "seo" ? "SEO" : t[0]!.toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
          <div className="tab-body">
            {tab === "script" &&
              (item.script ? (
                <div className="script">
                  <p>
                    <span className="label">Hook</span> {item.script.hook}
                  </p>
                  {item.script.body.map((b, i) => (
                    <p key={i}>{b}</p>
                  ))}
                  <p>
                    <span className="label">CTA</span> {item.script.cta}
                  </p>
                </div>
              ) : (
                <p className="muted">Script not generated yet.</p>
              ))}
            {tab === "seo" &&
              (item.seo ? (
                <div>
                  <h3>{item.seo.title}</h3>
                  <p className="pre">{item.seo.description}</p>
                  <div className="chips">
                    {item.seo.hashtags.map((h) => (
                      <span key={h} className="chip static">
                        {h}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="muted">SEO metadata not generated yet.</p>
              ))}
            {tab === "research" &&
              (item.research ? (
                <div>
                  <p>{item.research.summary}</p>
                  <h4>Facts</h4>
                  <ul>
                    {item.research.facts.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                  <h4>Outline</h4>
                  <ol>
                    {item.research.outline.map((o, i) => (
                      <li key={i}>{o}</li>
                    ))}
                  </ol>
                </div>
              ) : (
                <p className="muted">Research not generated yet.</p>
              ))}
            {tab === "storyboard" &&
              (item.video?.storyboard?.length ? (
                <ol className="storyboard">
                  {item.video.storyboard.map((s) => (
                    <li key={s.index}>
                      <div className="swatch" style={{ background: s.background_color ?? "#1e293b" }}>
                        {s.on_screen_text}
                      </div>
                      <div>
                        <div className="small muted">
                          Scene {s.index + 1} · {s.duration_seconds.toFixed(1)}s
                        </div>
                        <div>{s.narration}</div>
                        <div className="small muted">Visual: {s.visual_prompt}</div>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="muted">Storyboard not generated yet.</p>
              ))}
          </div>
        </div>
      </div>
      <h3>Publishing</h3>
      {item.publishing_jobs.length === 0 ? (
        <p className="muted small">Jobs are created once the video is ready.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Platform</th>
              <th>Scheduled</th>
              <th>Status</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody>
            {item.publishing_jobs.map((j) => (
              <tr key={j.id}>
                <td>
                  <PlatformTag platform={j.platform} />
                </td>
                <td>{formatDateTime(j.scheduled_at, timezone)}</td>
                <td>
                  <StatusBadge status={j.status} />
                  {j.last_error && <div className="small text-danger">{j.last_error}</div>}
                </td>
                <td>
                  {j.external_url ? (
                    <a href={j.external_url} target="_blank" rel="noreferrer">
                      Open ↗
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
