"use client";

import type { Platform } from "@/lib/types";

const STATUS_TONE: Record<string, string> = {
  draft: "neutral",
  pending: "neutral",
  generating: "info",
  rendering: "info",
  in_progress: "info",
  publishing: "info",
  scheduled: "accent",
  ready: "accent",
  published: "success",
  completed: "success",
  paused: "warning",
  cancelled: "warning",
  failed: "danger",
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${STATUS_TONE[status] ?? "neutral"}`}>{status.replace("_", " ")}</span>;
}

export function PlatformTag({ platform }: { platform: Platform }) {
  return <span className={`platform platform-${platform}`}>{platform === "youtube" ? "YouTube" : "Instagram"}</span>;
}

export function StatCard({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="card stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}

export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="alert alert-error" role="alert">
      {message}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="empty">
      <div className="empty-title">{title}</div>
      {children}
    </div>
  );
}
