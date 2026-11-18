"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "./AuthProvider";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "▦" },
  { href: "/campaign", label: "Campaigns", icon: "✦" },
  { href: "/analytics", label: "Analytics", icon: "↗" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

/** Authenticated layout: redirects anonymous users to /login and renders the sidebar. */
export function AppShell({ title, actions, children }: { title: string; actions?: React.ReactNode; children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, router, pathname]);

  if (loading || !user) {
    return (
      <div className="center-screen">
        <div className="spinner" aria-label="Loading" />
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link href="/dashboard" className="brand">
          <span className="brand-mark">◆</span> AI Content Factory
        </Link>
        <nav>
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className={`nav-link ${pathname.startsWith(item.href) ? "active" : ""}`}>
              <span className="nav-icon" aria-hidden>
                {item.icon}
              </span>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <div className="avatar">{(user.full_name || user.email).charAt(0).toUpperCase()}</div>
            <div className="user-meta">
              <div className="user-name">{user.full_name || user.email}</div>
              <div className="user-role">{user.role}</div>
            </div>
          </div>
          <button className="btn btn-ghost btn-block" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="page-header">
          <h1>{title}</h1>
          <div className="page-actions">{actions}</div>
        </header>
        {children}
      </main>
    </div>
  );
}
