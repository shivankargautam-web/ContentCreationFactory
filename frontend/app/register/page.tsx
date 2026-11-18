"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthCard } from "@/components/AuthCard";
import { ErrorBanner } from "@/components/ui";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.register(form.email, form.password, form.full_name || undefined);
      router.push("/login?registered=1");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard title="Create your account" subtitle="The first account becomes the workspace admin.">
      <ErrorBanner error={error} />
      <form onSubmit={onSubmit} className="form">
        <label>
          Full name
          <input value={form.full_name} onChange={set("full_name")} autoComplete="name" />
        </label>
        <label>
          Email
          <input type="email" required value={form.email} onChange={set("email")} autoComplete="email" />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={8}
            pattern="(?=.*[A-Za-z])(?=.*\d).{8,}"
            title="At least 8 characters with letters and digits"
            value={form.password}
            onChange={set("password")}
            autoComplete="new-password"
          />
          <span className="hint">At least 8 characters, including letters and digits.</span>
        </label>
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="muted small">
        Already registered? <Link href="/login">Sign in</Link>
      </p>
    </AuthCard>
  );
}
