"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { CampaignDetail, Platform } from "@/lib/types";
import { ErrorBanner } from "./ui";

const EXAMPLES = [
  "Generate 10 shorts about Kafka architecture. Publish one per day at 9AM EST.",
  "Create 5 reels on Kubernetes networking, every 2 days at 6pm PST starting Monday",
  "Make 7 videos about Python async programming, publish daily at 12:30 UTC",
];

export function CreateCampaignForm({ compact = false, onCreated }: { compact?: boolean; onCreated?: (c: CampaignDetail) => void }) {
  const router = useRouter();
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

  return (
    <form onSubmit={onSubmit} className="form">
      <ErrorBanner error={error} />
      <label>
        What should we make?
        <textarea
          required
          minLength={10}
          rows={compact ? 3 : 4}
          placeholder={EXAMPLES[0]}
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
        />
      </label>
      <div className="chips">
        {EXAMPLES.map((ex) => (
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
        {busy ? "Planning campaign…" : "Create campaign"}
      </button>
    </form>
  );
}
