"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { type RouteMode, useAppConfig } from "@/components/app-config-context";

const navItems = [
  { href: "/overview", label: "Overview", floor: "L1" },
  { href: "/workflow-chat", label: "AI Workflow Chat", floor: "L2" },
  { href: "/cost-estimation", label: "Cost Estimation", floor: "L3" },
  { href: "/documents", label: "Documents", floor: "L4" },
  { href: "/data-analysis", label: "Data Analysis", floor: "L5" },
  { href: "/prompt-admin", label: "Prompt Admin", floor: "L6" },
  { href: "/llm-cost-policy", label: "LLM Cost & Policy", floor: "L7" },
] as const;

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { config, setApiKey, setRouteMode, setTenantId, setUserId } = useAppConfig();

  const current = navItems.find((item) => pathname.startsWith(item.href));

  return (
    <div className="shell-root">
      <button
        className="mobile-toggle"
        type="button"
        onClick={() => setMobileOpen((prev) => !prev)}
      >
        Menu
      </button>

      <aside className={`shell-sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="shell-brand">
          <p>Industry AI Flow</p>
          <span>Capstone MVP</span>
        </div>

        <nav className="shell-nav">
          {navItems.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={active ? "shell-nav-link active" : "shell-nav-link"}
                onClick={() => setMobileOpen(false)}
              >
                <span className="floor-chip">{item.floor}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="shell-main">
        <header className="shell-header">
          <div>
            <p className="eyebrow">Current Floor</p>
            <h1>{current?.label ?? "Overview"}</h1>
          </div>

          <div className="config-grid">
            <label>
              Tenant
              <input
                value={config.tenantId}
                onChange={(event) => setTenantId(event.target.value)}
              />
            </label>
            <label>
              User
              <input
                value={config.userId}
                onChange={(event) => setUserId(event.target.value)}
              />
            </label>
            <label>
              Route
              <select
                value={config.routeMode}
                onChange={(event) => setRouteMode(event.target.value as RouteMode)}
              >
                <option value="local_only">local_only</option>
                <option value="hybrid_auto">hybrid_auto</option>
                <option value="cloud_only">cloud_only</option>
              </select>
            </label>
            <label>
              API Key
              <input
                type="password"
                placeholder="optional"
                value={config.apiKey}
                onChange={(event) => setApiKey(event.target.value)}
              />
            </label>
          </div>
        </header>

        <main className="shell-content">{children}</main>
      </div>
    </div>
  );
}
