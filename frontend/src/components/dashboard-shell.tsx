"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { type RouteMode, useAppConfig } from "@/components/app-config-context";
import { getDemoMode, updateDemoMode } from "@/lib/api-client";

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
  const [demoMode, setDemoMode] = useState<
    "live_hybrid" | "local_safe" | "scripted_replay"
  >("live_hybrid");
  const [cloudOverride, setCloudOverride] = useState(false);
  const [demoStatus, setDemoStatus] = useState<string>("");

  const current = navItems.find((item) => pathname.startsWith(item.href));

  useEffect(() => {
    let active = true;
    getDemoMode(config)
      .then((payload) => {
        if (!active) {
          return;
        }
        setDemoMode(payload.mode);
        setCloudOverride(payload.allow_cloud_override);
      })
      .catch(() => {
        if (active) {
          setDemoStatus("demo mode api unavailable");
        }
      });
    return () => {
      active = false;
    };
  }, [config]);

  async function applyDemoMode() {
    try {
      const payload = await updateDemoMode(config, {
        mode: demoMode,
        allow_cloud_override: cloudOverride,
      });
      setDemoStatus(`demo mode: ${payload.mode}`);
    } catch {
      setDemoStatus("failed to update demo mode (admin role required)");
    }
  }

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
            <label>
              Demo Mode
              <select
                value={demoMode}
                onChange={(event) =>
                  setDemoMode(
                    event.target.value as
                      | "live_hybrid"
                      | "local_safe"
                      | "scripted_replay",
                  )
                }
              >
                <option value="live_hybrid">live_hybrid</option>
                <option value="local_safe">local_safe</option>
                <option value="scripted_replay">scripted_replay</option>
              </select>
            </label>
            <label>
              Cloud Override
              <select
                value={cloudOverride ? "true" : "false"}
                onChange={(event) => setCloudOverride(event.target.value === "true")}
              >
                <option value="false">false</option>
                <option value="true">true</option>
              </select>
            </label>
          </div>
          <div className="chip-row">
            <button className="secondary-button" type="button" onClick={applyDemoMode}>
              Apply Demo Mode
            </button>
            {demoStatus ? <span className="chip">{demoStatus}</span> : null}
          </div>
        </header>

        <main className="shell-content">{children}</main>
      </div>
    </div>
  );
}
