"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorBanner, PlatformTag } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Platform, PlatformAccount, Role, User } from "@/lib/types";

export default function SettingsPage() {
  const { user, can } = useAuth();
  return (
    <AppShell title="Settings">
      <div className="grid grid-2">
        <ProfileCard />
        {can("admin", "editor") && <PlatformAccountsCard />}
      </div>
      {user && can("admin") && <UsersCard currentUserId={user.id} />}
    </AppShell>
  );
}

function ProfileCard() {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.full_name ?? "");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.updateProfile(name || null);
      await refreshUser();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Profile</h2>
      </div>
      <ErrorBanner error={error} />
      <form className="form" onSubmit={save}>
        <label>
          Email
          <input value={user?.email ?? ""} disabled />
        </label>
        <label>
          Full name
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={255} />
        </label>
        <label>
          Role
          <input value={user?.role ?? ""} disabled />
        </label>
        <button className="btn btn-primary">{saved ? "Saved ✓" : "Save profile"}</button>
      </form>
    </div>
  );
}

const EMPTY_ACCOUNT = { platform: "youtube" as Platform, account_name: "", external_account_id: "", access_token: "", refresh_token: "" };

function PlatformAccountsCard() {
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [form, setForm] = useState(EMPTY_ACCOUNT);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.listAccounts().then(setAccounts).catch(setError), []);
  useEffect(() => {
    load();
  }, [load]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function connect(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.connectAccount({
        platform: form.platform,
        account_name: form.account_name,
        external_account_id: form.external_account_id,
        access_token: form.access_token,
        refresh_token: form.refresh_token || undefined,
        scopes:
          form.platform === "youtube"
            ? ["https://www.googleapis.com/auth/youtube.upload"]
            : ["instagram_basic", "instagram_content_publish"],
      });
      setForm(EMPTY_ACCOUNT);
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Connected accounts</h2>
      </div>
      <ErrorBanner error={error} />
      {accounts.length === 0 ? (
        <Empty title="No accounts connected">Without an account, publishing runs in dry-run mode when enabled.</Empty>
      ) : (
        <ul className="list">
          {accounts.map((a) => (
            <li key={a.id} className="list-row static">
              <div className="row gap-sm">
                <PlatformTag platform={a.platform} />
                <div>
                  <div className="list-title">{a.account_name}</div>
                  <div className="muted small">
                    {a.external_account_id}
                    {a.token_expires_at && ` · token expires ${formatDateTime(a.token_expires_at)}`}
                  </div>
                </div>
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => api.disconnectAccount(a.id).then(load).catch(setError)}
              >
                Disconnect
              </button>
            </li>
          ))}
        </ul>
      )}
      <form className="form" onSubmit={connect}>
        <h3>Connect an account</h3>
        <div className="grid grid-2 gap-md">
          <label>
            Platform
            <select value={form.platform} onChange={set("platform")}>
              <option value="youtube">YouTube</option>
              <option value="instagram">Instagram</option>
            </select>
          </label>
          <label>
            Display name
            <input required value={form.account_name} onChange={set("account_name")} />
          </label>
        </div>
        <label>
          {form.platform === "youtube" ? "Channel ID" : "Instagram business account ID"}
          <input required value={form.external_account_id} onChange={set("external_account_id")} />
        </label>
        <label>
          Access token
          <input required type="password" autoComplete="off" value={form.access_token} onChange={set("access_token")} />
        </label>
        {form.platform === "youtube" && (
          <label>
            Refresh token <span className="hint">(recommended — enables automatic renewal)</span>
            <input type="password" autoComplete="off" value={form.refresh_token} onChange={set("refresh_token")} />
          </label>
        )}
        <p className="hint">Tokens are encrypted at rest and never returned by the API.</p>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Connecting…" : "Connect account"}
        </button>
      </form>
    </div>
  );
}

function UsersCard({ currentUserId }: { currentUserId: string }) {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<unknown>(null);
  const load = useCallback(() => api.listUsers().then((p) => setUsers(p.items)).catch(setError), []);
  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="card">
      <div className="card-header">
        <h2>Team & roles</h2>
      </div>
      <ErrorBanner error={error} />
      <table className="table">
        <thead>
          <tr>
            <th>User</th>
            <th>Joined</th>
            <th>Role</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>
                <div className="list-title">{u.full_name || u.email}</div>
                <div className="muted small">{u.email}</div>
              </td>
              <td>{new Date(u.created_at).toLocaleDateString()}</td>
              <td>
                <select
                  aria-label={`Role for ${u.email}`}
                  value={u.role}
                  disabled={u.id === currentUserId}
                  onChange={(e) => api.setRole(u.id, e.target.value as Role).then(load).catch(setError)}
                >
                  <option value="admin">Admin</option>
                  <option value="editor">Editor</option>
                  <option value="viewer">Viewer</option>
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
