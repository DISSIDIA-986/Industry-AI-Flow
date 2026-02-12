"use client";

import { useEffect, useMemo, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import {
  getCostHealth,
  getPlatformHealth,
  getWorkflowHealth,
  type HealthResponse,
} from "@/lib/api-client";
import { normalizeError } from "@/lib/formatters";

interface HealthCard {
  title: string;
  status: string;
  details: string;
}

export default function OverviewPage() {
  const { config } = useAppConfig();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [platform, setPlatform] = useState<HealthResponse | null>(null);
  const [workflow, setWorkflow] = useState<HealthResponse | null>(null);
  const [cost, setCost] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [platformHealth, workflowHealth, costHealth] = await Promise.all([
          getPlatformHealth(config),
          getWorkflowHealth(config),
          getCostHealth(config),
        ]);

        if (!active) {
          return;
        }
        setPlatform(platformHealth);
        setWorkflow(workflowHealth);
        setCost(costHealth);
      } catch (err) {
        if (active) {
          setError(normalizeError(err));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [config]);

  const cards = useMemo<HealthCard[]>(
    () => [
      {
        title: "Platform Core",
        status: platform?.status ?? "unknown",
        details: platform
          ? `memory ${platform.memory_usage_mb ?? "-"} MB · v${platform.version ?? "n/a"}`
          : "Waiting for backend",
      },
      {
        title: "Workflow Orchestrator",
        status: workflow?.status ?? "unknown",
        details: workflow?.component ?? "workflow",
      },
      {
        title: "Cost Estimation Engine",
        status: cost?.status ?? "unknown",
        details:
          typeof cost?.model === "object"
            ? JSON.stringify(cost.model)
            : "model metadata unavailable",
      },
    ],
    [cost, platform, workflow],
  );

  return (
    <section className="page-stack">
      <article className="hero-card">
        <p className="eyebrow">Demo Control Deck</p>
        <h2>One screen for the Capstone opening minute</h2>
        <p>
          This floor shows health, current route mode, and operational readiness before
          you start the live demo story.
        </p>
        <div className="chip-row">
          <span className="chip">Tenant: {config.tenantId}</span>
          <span className="chip">Route Mode: {config.routeMode}</span>
          <span className="chip">User: {config.userId}</span>
        </div>
      </article>

      <div className="floor-grid stagger-list">
        {cards.map((card) => (
          <article key={card.title} className="panel-card">
            <header>
              <h3>{card.title}</h3>
              <span className={`status-dot ${card.status === "ok" ? "ok" : "warn"}`}>
                {card.status}
              </span>
            </header>
            <p>{card.details}</p>
          </article>
        ))}
      </div>

      <article className="panel-card">
        <header>
          <h3>Quick Demo Flow</h3>
        </header>
        <ol className="ordered-flow">
          <li>Go to Workflow Chat and ask a natural-language project question.</li>
          <li>Jump to Cost Estimation and show prediction + interval output.</li>
          <li>Use Data Analysis to upload a file and trigger chart generation.</li>
        </ol>
        <button className="action-button" type="button" onClick={() => window.location.reload()}>
          {loading ? "Refreshing..." : "Refresh Health"}
        </button>
        {error ? <p className="error-text">{error}</p> : null}
      </article>
    </section>
  );
}
