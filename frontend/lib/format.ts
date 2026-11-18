export function formatNumber(n: number): string {
  return new Intl.NumberFormat("en-US", { notation: n >= 10_000 ? "compact" : "standard" }).format(n);
}

export function formatDateTime(iso: string, timeZone?: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone,
    timeZoneName: timeZone ? "short" : undefined,
  }).format(new Date(iso));
}

export function formatCadence(intervalHours: number): string {
  if (intervalHours === 24) return "Daily";
  if (intervalHours === 168) return "Weekly";
  if (intervalHours % 24 === 0) return `Every ${intervalHours / 24} days`;
  return intervalHours === 1 ? "Hourly" : `Every ${intervalHours} hours`;
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h ? `${h}h ${m}m` : `${m}m`;
}

/** Returns the 6x7 grid of dates (Sunday-first) covering the month containing `anchor`. */
export function monthGrid(anchor: Date): Date[] {
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const start = new Date(first);
  start.setDate(first.getDate() - first.getDay());
  return Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
}

export function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
