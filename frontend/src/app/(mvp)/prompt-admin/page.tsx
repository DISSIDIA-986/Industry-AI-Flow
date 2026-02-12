"use client";

import { useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import { getPromptMetrics, listPrompts } from "@/lib/api-client";
import { normalizeError } from "@/lib/formatters";

export default function PromptAdminPage() {
  const { config } = useAppConfig();
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [prompts, setPrompts] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadPromptData() {
    setLoading(true);
    setError(null);
    try {
      const [metricsPayload, promptPayload] = await Promise.all([
        getPromptMetrics(config),
        listPrompts(config),
      ]);
      setMetrics(metricsPayload);
      setPrompts(promptPayload);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-stack">
      <article className="hero-card">
        <p className="eyebrow">L6 Prompt Layer</p>
        <h2>Prompt metrics and experiment visibility</h2>
        <p>
          MVP page reads key prompt data. Full editing remains available via Streamlit Prompt
          Admin.
        </p>
        <div className="chip-row">
          <span className="chip">Run locally: `make prompt-admin`</span>
        </div>
      </article>

      <article className="panel-card">
        <header>
          <h3>Prompt Snapshot</h3>
        </header>
        <button className="action-button" type="button" onClick={loadPromptData}>
          {loading ? "Loading..." : "Load Metrics + Top Prompts"}
        </button>
        {error ? <p className="error-text">{error}</p> : null}
        <div className="result-grid">
          <div>
            <p className="result-label">Metrics</p>
            <pre>{metrics ? JSON.stringify(metrics, null, 2) : "No metrics loaded"}</pre>
          </div>
          <div>
            <p className="result-label">Prompts</p>
            <pre>{prompts ? JSON.stringify(prompts, null, 2) : "No prompt data loaded"}</pre>
          </div>
        </div>
      </article>
    </section>
  );
}
