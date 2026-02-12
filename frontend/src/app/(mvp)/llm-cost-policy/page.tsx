"use client";

import { useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import {
  getLlmBudget,
  getLlmUsage,
  updateLlmBudget,
  type BudgetPolicyRequest,
  type LlmBudgetResponse,
  type LlmUsageResponse,
} from "@/lib/api-client";
import { formatCurrency, normalizeError } from "@/lib/formatters";

export default function LlmCostPolicyPage() {
  const { config } = useAppConfig();
  const [tenantId, setTenantId] = useState(config.tenantId);
  const [usage, setUsage] = useState<LlmUsageResponse | null>(null);
  const [budget, setBudget] = useState<LlmBudgetResponse | null>(null);
  const [policy, setPolicy] = useState<BudgetPolicyRequest>({
    monthly_budget_usd: 80,
    soft_limit_ratio: 0.8,
    hard_limit_ratio: 1,
    policy_mode: "local_only",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadCostData() {
    setLoading(true);
    setError(null);
    try {
      const [usagePayload, budgetPayload] = await Promise.all([
        getLlmUsage(config),
        getLlmBudget(config, tenantId),
      ]);
      setUsage(usagePayload);
      setBudget(budgetPayload);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  async function savePolicy() {
    setLoading(true);
    setError(null);
    try {
      await updateLlmBudget(config, tenantId, policy);
      await loadCostData();
    } catch (err) {
      setError(normalizeError(err));
      setLoading(false);
    }
  }

  return (
    <section className="page-stack">
      <article className="hero-card">
        <p className="eyebrow">L7 Governance Layer</p>
        <h2>LLM usage and budget policy controls</h2>
        <p>
          Show your hybrid strategy is controlled by measurable cost policy, not guesswork.
        </p>
      </article>

      <article className="panel-card">
        <header>
          <h3>Budget Controls</h3>
        </header>
        <div className="form-grid two-col">
          <label className="field-group">
            Tenant ID
            <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
          </label>
          <label className="field-group">
            Monthly Budget (USD)
            <input
              type="number"
              value={policy.monthly_budget_usd}
              onChange={(event) =>
                setPolicy((prev) => ({ ...prev, monthly_budget_usd: Number(event.target.value) }))
              }
            />
          </label>
          <label className="field-group">
            Soft Limit Ratio
            <input
              type="number"
              step="0.05"
              value={policy.soft_limit_ratio}
              onChange={(event) =>
                setPolicy((prev) => ({ ...prev, soft_limit_ratio: Number(event.target.value) }))
              }
            />
          </label>
          <label className="field-group">
            Hard Limit Ratio
            <input
              type="number"
              step="0.05"
              value={policy.hard_limit_ratio}
              onChange={(event) =>
                setPolicy((prev) => ({ ...prev, hard_limit_ratio: Number(event.target.value) }))
              }
            />
          </label>
          <label className="field-group">
            Policy Mode
            <select
              value={policy.policy_mode}
              onChange={(event) =>
                setPolicy((prev) => ({
                  ...prev,
                  policy_mode: event.target.value as BudgetPolicyRequest["policy_mode"],
                }))
              }
            >
              <option value="local_only">local_only</option>
              <option value="block">block</option>
            </select>
          </label>
        </div>

        <div className="action-row">
          <button className="action-button" type="button" onClick={loadCostData}>
            {loading ? "Loading..." : "Load Usage + Budget"}
          </button>
          <button className="secondary-button" type="button" onClick={savePolicy}>
            Save Budget Policy
          </button>
        </div>

        {error ? <p className="error-text">{error}</p> : null}

        <div className="result-grid">
          <div>
            <p className="result-label">Usage Summary</p>
            <pre>{usage ? JSON.stringify(usage, null, 2) : "No usage data loaded"}</pre>
          </div>
          <div>
            <p className="result-label">Budget Policy</p>
            <pre>{budget ? JSON.stringify(budget, null, 2) : "No budget policy loaded"}</pre>
            {budget && typeof budget.current_month_spend_usd === "number" ? (
              <p className="muted-text">
                Current Month Spend: {formatCurrency(Number(budget.current_month_spend_usd))}
              </p>
            ) : null}
          </div>
        </div>
      </article>
    </section>
  );
}
