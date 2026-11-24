"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { Empty, ErrorBanner, PlatformTag } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { OAuthProviders, Platform, PlatformAccount, Role, User } from "@/lib/types";

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

const PLATFORM_LABEL: Record<Platform, string> = { youtube: "YouTube", instagram: "Instagram" };
const SIGN_IN_LABEL: Record<Platform, string> = {
  youtube: "Connect YouTube (sign in with Google)",
  instagram: "Connect Instagram (sign in with Facebook)",
};

function readOAuthResult(): { connected?: string; error?: string } {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  const result = { connected: params.get("connected") ?? undefined, error: params.get("oauth_error") ?? undefined };
  if (result.connected || result.error) window.history.replaceState(null, "", window.location.pathname);
  return result;
}

function PlatformAccountsCard() {
  const [accounts, setAccounts] = useState<PlatformAccount[]>([]);
  const [providers, setProviders] = useState<OAuthProviders | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<Platform | null>(null);
  const load = useCallback(() => api.listAccounts().then(setAccounts).catch(setError), []);
  useEffect(() => {
    load();
    api.oauthProviders().then(setProviders).catch(setError);
    const result = readOAuthResult();
    if (result.connected) setNotice(`${PLATFORM_LABEL[result.connected as Platform] ?? result.connected} connected.`);
    if (result.error) setError(new Error(result.error));
  }, [load]);

  async function signIn(platform: Platform) {
    setBusy(platform);
    setError(null);
    try {
      const { authorization_url } = await api.oauthAuthorizeUrl(platform);
      window.location.assign(authorization_url);
    } catch (err) {
      setError(err);
      setBusy(null);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Connected accounts</h2>
      </div>
      {notice && <div className="alert alert-success">{notice}</div>}
      <ErrorBanner error={error} />
      {accounts.length === 0 ? (
        <Empty title="No accounts connected">Connect YouTube or Instagram so reels can be posted.</Empty>
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
                    {` · connected ${formatDateTime(a.created_at)}`}
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
      <div className="form">
        <h3>Connect an account</h3>
        <div className="connect-buttons">
          {(["youtube", "instagram"] as Platform[]).map((p) => (
            <button
              key={p}
              type="button"
              className="btn btn-primary"
              disabled={busy !== null || providers?.[p] === false}
              onClick={() => signIn(p)}
            >
              {busy === p ? "Redirecting…" : SIGN_IN_LABEL[p]}
            </button>
          ))}
        </div>
        {providers && (!providers.youtube || !providers.instagram) && (
          <p className="hint">
            {[!providers.youtube && "YouTube sign-in needs YOUTUBE_CLIENT_ID/SECRET", !providers.instagram && "Instagram sign-in needs META_APP_ID/SECRET"]
              .filter(Boolean)
              .join(" · ")}{" "}
            on the server.
          </p>
        )}
        <p className="hint">You approve access on Google or Facebook. Tokens are encrypted at rest and never shown in the app.</p>
      </div>
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
