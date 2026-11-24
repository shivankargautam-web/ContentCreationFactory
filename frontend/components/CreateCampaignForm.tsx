"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { CampaignDetail, CampaignMode, Platform } from "@/lib/types";
import { ErrorBanner } from "./ui";

const EXAMPLES: Record<CampaignMode, string[]> = {
  now: [
    "Explain how Kafka consumer groups rebalance when a new consumer joins",
    "Three tips for writing faster SQL queries, aimed at junior developers",
    "Why Python's GIL matters for multithreading, with a simple analogy",
  ],
  scheduled: [
    "Generate 10 shorts about Kafka architecture. Publish one per day at 9AM EST.",
    "Create 5 reels on Kubernetes networking, every 2 days at 6pm PST starting Monday",
    "Make 7 videos about Python async programming, publish daily at 12:30 UTC",
  ],
};

const MODE_COPY: Record<CampaignMode, { label: string; prompt: string; hint: string; submit: string; busy: string }> = {
  now: {
    label: "Post now",
    prompt: "What should the reel be about?",
    hint: "Write a topic or a short explanation. We make one reel and post it as soon as it's ready.",
    submit: "Create & post reel",
    busy: "Starting…",
  },
  scheduled: {
    label: "Schedule a series",
    prompt: "Describe the series and its schedule",
    hint: "Say how many videos and when to post, e.g. “one per day at 9AM EST”.",
    submit: "Create campaign",
    busy: "Planning campaign…",
  },
};

export function CreateCampaignForm({ compact = false, onCreated }: { compact?: boolean; onCreated?: (c: CampaignDetail) => void }) {
  const router = useRouter();
  const [mode, setMode] = useState<CampaignMode>("now");
  const [instruction, setInstruction] = useState("");
  const [platforms, setPlatforms] = useState<Platform[]>(["youtube", "instagram"]);
  const [name, setName] = useState("");
  const [tone, setTone] = useState("");
  const [audience, setAudience] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const toggle = (p: Platform) => setPlatforms((cur) => (cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p]));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (platforms.length === 0) {
      setError(new Error("Select at least one platform"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const campaign = await api.createCampaign({
        instruction,
        mode,
        platforms,
        name: name || undefined,
        tone: tone || undefined,
        target_audience: audience || undefined,
      });
      setInstruction("");
      onCreated?.(campaign);
      router.push(`/campaign?id=${campaign.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const copy = MODE_COPY[mode];

  return (
    <form onSubmit={onSubmit} className="form">
      <ErrorBanner error={error} />
      <div className="segmented" role="radiogroup" aria-label="How to publish">
        {(["now", "scheduled"] as CampaignMode[]).map((m) => (
          <button
            type="button"
            key={m}
            role="radio"
            aria-checked={mode === m}
            className={mode === m ? "active" : ""}
            onClick={() => setMode(m)}
          >
            {MODE_COPY[m].label}
          </button>
        ))}
      </div>
      <label>
        {copy.prompt}
        <textarea
          required
          minLength={10}
          rows={compact ? 3 : 4}
          placeholder={EXAMPLES[mode][0]}
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
        />
        <span className="hint">{copy.hint}</span>
      </label>
      <div className="chips">
        {EXAMPLES[mode].map((ex) => (
          <button type="button" key={ex} className="chip" onClick={() => setInstruction(ex)}>
            {ex.length > 48 ? `${ex.slice(0, 48)}…` : ex}
          </button>
        ))}
      </div>
      <fieldset className="row gap-md">
        <legend>Platforms</legend>
        {(["youtube", "instagram"] as Platform[]).map((p) => (
          <label key={p} className="checkbox">
            <input type="checkbox" checked={platforms.includes(p)} onChange={() => toggle(p)} />
            {p === "youtube" ? "YouTube Shorts" : "Instagram Reels"}
          </label>
        ))}
      </fieldset>
      {!compact && (
        <div className="grid grid-3 gap-md">
          <label>
            Name <span className="hint">(optional)</span>
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={255} />
          </label>
          <label>
            Tone <span className="hint">(optional)</span>
            <input value={tone} onChange={(e) => setTone(e.target.value)} placeholder="energetic, expert" maxLength={100} />
          </label>
          <label>
            Audience <span className="hint">(optional)</span>
            <input value={audience} onChange={(e) => setAudience(e.target.value)} placeholder="backend engineers" maxLength={255} />
          </label>
        </div>
      )}
      <button className="btn btn-primary" disabled={busy}>
        {busy ? copy.busy : copy.submit}
      </button>
    </form>
  );
}
