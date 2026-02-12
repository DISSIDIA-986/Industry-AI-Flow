"use client";

import { useMemo, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import {
  queryWorkflow,
  type WorkflowQueryResponse,
} from "@/lib/api-client";
import { normalizeError } from "@/lib/formatters";

interface ChatTurn {
  id: string;
  query: string;
  response: WorkflowQueryResponse;
}

const QUICK_PROMPTS = [
  "Estimate cost risk for a 20-floor office in Toronto with 200000 sqft and 18 months duration.",
  "What are the likely causes of cost overrun for a healthcare hospital project?",
  "Summarize how this platform routes between local and cloud models.",
];

export default function WorkflowChatPage() {
  const { config } = useAppConfig();
  const [query, setQuery] = useState(QUICK_PROMPTS[0]);
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const summary = useMemo(() => {
    if (!turns.length) {
      return "No interaction yet";
    }
    const last = turns[0].response;
    return `intent: ${last.intent ?? "unknown"} · provider: ${last.provider_used ?? "n/a"}`;
  }, [turns]);

  async function sendQuery() {
    const trimmed = query.trim();
    if (!trimmed || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = {
        query: trimmed,
        session_id: sessionId,
        user_id: config.userId,
        route_mode: config.routeMode,
      };
      const response = await queryWorkflow(config, payload);
      setTurns((prev) => [
        {
          id: response.trace_id,
          query: trimmed,
          response,
        },
        ...prev,
      ]);
      setQuery("");
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-stack">
      <article className="hero-card">
        <p className="eyebrow">L2 Workflow Layer</p>
        <h2>Natural-language entry for all AI capabilities</h2>
        <p>Ask normally; the workflow orchestrator handles intent routing and provider selection.</p>
        <div className="chip-row">
          <span className="chip">{summary}</span>
          <span className="chip">session: {sessionId.slice(0, 8)}</span>
        </div>
      </article>

      <article className="panel-card">
        <header>
          <h3>Query Console</h3>
        </header>
        <div className="inline-row">
          <label className="field-group">
            Session ID
            <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
          </label>
        </div>

        <textarea
          className="text-area"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask about cost, risk, documents, or analysis..."
        />

        <div className="quick-prompts">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              className="secondary-button"
              type="button"
              onClick={() => setQuery(prompt)}
            >
              Use Example
            </button>
          ))}
        </div>

        <button className="action-button" type="button" onClick={sendQuery}>
          {loading ? "Routing..." : "Send to Workflow"}
        </button>
        {error ? <p className="error-text">{error}</p> : null}
      </article>

      <section className="page-stack">
        {turns.map((turn) => (
          <article key={turn.id} className="panel-card chat-card">
            <p className="chat-query">Q: {turn.query}</p>
            <p className="chat-answer">A: {turn.response.response ?? turn.response.error ?? "No answer"}</p>
            <div className="chip-row">
              <span className="chip">intent: {turn.response.intent ?? "unknown"}</span>
              <span className="chip">provider: {turn.response.provider_used ?? "n/a"}</span>
              <span className="chip">mode: {turn.response.route_mode}</span>
              <span className="chip">trace: {turn.response.trace_id.slice(0, 8)}</span>
            </div>
            <details>
              <summary>Metadata</summary>
              <pre>{JSON.stringify(turn.response.metadata, null, 2)}</pre>
            </details>
          </article>
        ))}
      </section>
    </section>
  );
}
