"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import {
  getCostHealth,
  predictCost,
  predictCostBatch,
  type CostPrediction,
  type CostProjectFeatures,
} from "@/lib/api-client";
import { formatCurrency, formatNumber, normalizeError } from "@/lib/formatters";

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const PROJECT_TYPES = [
  "commercial_office",
  "commercial_retail",
  "education_school",
  "healthcare_hospital",
  "industrial_warehouse",
  "infrastructure_bridge",
  "mixed_use",
  "renewable_energy",
  "renovation_commercial",
  "residential_multi_family",
  "residential_single_family",
  "transit_station",
] as const;

const LOCATIONS = [
  "Brampton",
  "Calgary",
  "Edmonton",
  "Halifax",
  "Markham",
  "Mississauga",
  "Montreal",
  "Ottawa",
  "Quebec City",
  "Saskatoon",
  "Surrey",
  "Toronto",
  "Vancouver",
  "Victoria",
  "Winnipeg",
] as const;

/* Field grouping: 3 logical groups */
const GROUP_1_FIELDS = [
  "estimated_cost_cad",
  "sqft",
  "floors",
] as const;

const GROUP_2_FIELDS = [
  "planned_duration_weeks",
  "num_units",
  "contractor_rating",
  "team_experience_years",
  "num_subcontractors",
  "num_change_orders",
] as const;

const GROUP_3_FIELDS = [
  "complexity_score",
  "weather_risk_factor",
  "material_volatility",
  "budget_pressure",
  "risk_score",
  "risk_score_original",
] as const;

const FIELD_LABELS: Record<string, string> = {
  sqft: "Square Footage (sq ft)",
  floors: "Number of Floors",
  num_units: "Number of Units",
  planned_duration_weeks: "Planned Duration (weeks)",
  estimated_cost_cad: "Estimated Cost (CAD)",
  contractor_rating: "Contractor Rating (0–5)",
  complexity_score: "Complexity Score (1–10)",
  team_experience_years: "Team Experience (years)",
  num_change_orders: "Number of Change Orders",
  weather_risk_factor: "Weather Risk Factor",
  material_volatility: "Material Volatility",
  num_subcontractors: "Number of Subcontractors",
  budget_pressure: "Budget Pressure",
  risk_score: "Risk Score",
  risk_score_original: "Original Risk Score",
};

const CONFIDENCE_PRESETS = [
  { label: "80%", value: 0.8 },
  { label: "90%", value: 0.9 },
  { label: "95%", value: 0.95 },
] as const;

/* String-backed defaults to avoid NaN on keystroke */
const DEFAULT_STRINGS: Record<string, string> = {
  project_type: "commercial_office",
  location: "Toronto",
  sqft: "29155",
  floors: "5",
  num_units: "1",
  planned_duration_weeks: "78",
  estimated_cost_cad: "72000000",
  contractor_rating: "4.2",
  complexity_score: "7",
  team_experience_years: "11",
  num_change_orders: "5",
  weather_risk_factor: "0.32",
  material_volatility: "0.44",
  num_subcontractors: "16",
  budget_pressure: "0.58",
  risk_score: "24.2",
  risk_score_original: "34.3",
};

interface ModelHealth {
  mape: number | null;
  r2: number | null;
  training_rows: number | null;
}

interface BatchEntry {
  id: string;
  project: CostProjectFeatures;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function overrunColor(pct: number): string {
  if (pct < 5) return "var(--ok)";
  if (pct < 15) return "var(--amber, #f59e0b)";
  return "var(--warn)";
}

function parseFields(
  strings: Record<string, string>,
): { project: CostProjectFeatures; errors: Record<string, string> } {
  const errors: Record<string, string> = {};
  function num(key: string, opts?: { gt?: number; ge?: number; le?: number }): number {
    const raw = strings[key] ?? "";
    const val = Number(raw);
    if (raw.trim() === "" || isNaN(val)) {
      errors[key] = "Required";
      return 0;
    }
    if (opts?.gt !== undefined && val <= opts.gt) {
      errors[key] = `Must be greater than ${opts.gt}`;
      return val;
    }
    if (opts?.ge !== undefined && val < opts.ge) {
      errors[key] = `Must be at least ${opts.ge}`;
      return val;
    }
    if (opts?.le !== undefined && val > opts.le) {
      errors[key] = `Must be at most ${opts.le}`;
      return val;
    }
    return val;
  }

  const project: CostProjectFeatures = {
    project_type: strings.project_type || "commercial_office",
    location: strings.location || "Toronto",
    sqft: num("sqft", { gt: 0 }),
    floors: num("floors", { ge: 0 }),
    num_units: num("num_units", { ge: 0 }),
    planned_duration_weeks: num("planned_duration_weeks", { gt: 0 }),
    estimated_cost_cad: num("estimated_cost_cad", { gt: 0 }),
    contractor_rating: num("contractor_rating", { ge: 0, le: 5 }),
    complexity_score: num("complexity_score", { ge: 1, le: 10 }),
    team_experience_years: num("team_experience_years", { ge: 0 }),
    num_change_orders: num("num_change_orders", { ge: 0 }),
    weather_risk_factor: num("weather_risk_factor", { ge: 0 }),
    material_volatility: num("material_volatility", { ge: 0 }),
    num_subcontractors: num("num_subcontractors", { ge: 0 }),
    budget_pressure: num("budget_pressure", { ge: 0 }),
    risk_score: num("risk_score", { ge: 0 }),
    risk_score_original: num("risk_score_original", { ge: 0 }),
  };

  return { project, errors };
}

function exportCsv(entries: BatchEntry[], results: CostPrediction[]) {
  const headers = [
    "project_type", "location", ...GROUP_1_FIELDS, ...GROUP_2_FIELDS, ...GROUP_3_FIELDS,
    "predicted_actual_cost_cad", "predicted_cost_overrun_pct",
    "interval_lower", "interval_upper",
  ];
  const rows = results.map((r, i) => {
    const p = entries[i]?.project;
    return [
      p?.project_type ?? "", p?.location ?? "",
      ...GROUP_1_FIELDS.map((f) => String(p?.[f] ?? "")),
      ...GROUP_2_FIELDS.map((f) => String(p?.[f] ?? "")),
      ...GROUP_3_FIELDS.map((f) => String(p?.[f] ?? "")),
      String(r.predicted_actual_cost_cad),
      String(r.predicted_cost_overrun_pct),
      String(r.prediction_interval_cad.lower),
      String(r.prediction_interval_cad.upper),
    ].join(",");
  });
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "cost_estimation_batch.csv";
  a.click();
  URL.revokeObjectURL(url);
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function CostEstimationPage() {
  const { config } = useAppConfig();

  /* String-backed form state */
  const [fields, setFields] = useState<Record<string, string>>(DEFAULT_STRINGS);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [confidence, setConfidence] = useState(0.9);

  /* Results */
  const [singleResult, setSingleResult] = useState<CostPrediction | null>(null);
  const [batchEntries, setBatchEntries] = useState<BatchEntry[]>([]);
  const [batchResults, setBatchResults] = useState<CostPrediction[]>([]);
  const [loadingSingle, setLoadingSingle] = useState(false);
  const [loadingBatch, setLoadingBatch] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const skeletonTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Model health */
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);

  const isDefaultData = useMemo(
    () => Object.entries(DEFAULT_STRINGS).every(([k, v]) => fields[k] === v),
    [fields],
  );

  /* Fetch model health on mount via authenticated API client */
  useEffect(() => {
    getCostHealth(config)
      .then((data) => {
        /* eslint-disable @typescript-eslint/no-explicit-any */
        const model = (data as any)?.model;
        const cv = model?.metrics?.cross_validation?.actual_cost;
        setModelHealth({
          mape: cv?.mape ?? null,
          r2: cv?.r2 ?? null,
          training_rows: model?.training_rows ?? null,
        });
      })
      .catch(() => { /* hide badge silently */ });
  }, [config]);

  function updateField(key: string, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
    if (fieldErrors[key]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  }

  const runSinglePrediction = useCallback(async () => {
    const { project, errors } = parseFields(fields);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setFieldErrors({});
    setLoadingSingle(true);
    setSingleResult(null);
    setError(null);

    /* Delayed skeleton */
    skeletonTimer.current = setTimeout(() => setShowSkeleton(true), 300);

    try {
      const response = await predictCost(config, project, confidence);
      setSingleResult(response.prediction);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoadingSingle(false);
      if (skeletonTimer.current) clearTimeout(skeletonTimer.current);
      setShowSkeleton(false);
    }
  }, [config, fields, confidence]);

  const addToBatch = useCallback(() => {
    const { project, errors } = parseFields(fields);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setFieldErrors({});
    setBatchEntries((prev) => [{ id: crypto.randomUUID(), project }, ...prev]);
    setBatchResults([]);
  }, [fields]);

  /* Snapshot entries at submit time to prevent data corruption if queue
     is mutated while the request is in flight. */
  const batchSnapshotRef = useRef<BatchEntry[]>([]);

  const runBatchPrediction = useCallback(async () => {
    if (!batchEntries.length) return;
    const snapshot = [...batchEntries];
    batchSnapshotRef.current = snapshot;
    setLoadingBatch(true);
    setError(null);
    try {
      const response = await predictCostBatch(
        config,
        snapshot.map((e) => e.project),
        confidence,
      );
      /* Use the snapshot for CSV export — not the possibly-mutated queue */
      setBatchEntries(snapshot);
      setBatchResults(response.predictions);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoadingBatch(false);
      batchSnapshotRef.current = [];
    }
  }, [config, batchEntries, confidence]);

  function clearBatch() {
    setBatchEntries([]);
    setBatchResults([]);
  }

  /* Render helpers */
  function renderNumericField(field: string) {
    const hasError = !!fieldErrors[field];
    return (
      <label className="field-group" key={field} htmlFor={`ce-${field}`}>
        {FIELD_LABELS[field] ?? field}
        <input
          id={`ce-${field}`}
          type="text"
          inputMode="decimal"
          value={fields[field] ?? ""}
          onChange={(e) => updateField(field, e.target.value)}
          style={hasError ? { borderColor: "var(--warn)" } : undefined}
        />
        {hasError && <span className="field-error">{fieldErrors[field]}</span>}
      </label>
    );
  }

  return (
    <section className="page-stack">
      {/* Hero */}
      <article className="hero-card">
        <p className="eyebrow">Cost Prediction</p>
        <h2 style={{ fontWeight: 700, letterSpacing: "-0.02em" }}>
          Predict construction cost overruns
        </h2>
        <p>
          Enter project parameters below. The model analyzes 10,000 historical
          projects to predict whether your project will go over budget.
        </p>
        {isDefaultData && (
          <span className="chip" style={{ marginTop: "0.5rem", display: "inline-block" }}>
            Sample Data
          </span>
        )}
      </article>

      {/* Single Prediction */}
      <article className="panel-card">
        <header>
          <h3>Single Project Prediction</h3>
        </header>

        {/* Group 1: Project Overview — always visible */}
        <p className="eyebrow" style={{ marginBottom: "0.5rem" }}>Project Overview</p>
        <div className="form-grid two-col">
          <label className="field-group" htmlFor="ce-project_type">
            Project Type
            <select
              id="ce-project_type"
              value={fields.project_type}
              onChange={(e) => updateField("project_type", e.target.value)}
            >
              {PROJECT_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
          </label>
          <label className="field-group" htmlFor="ce-location">
            Location
            <select
              id="ce-location"
              value={fields.location}
              onChange={(e) => updateField("location", e.target.value)}
            >
              {LOCATIONS.map((loc) => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </label>
          {GROUP_1_FIELDS.map((f) => renderNumericField(f))}
        </div>

        {/* Group 2: Construction Parameters — collapsible */}
        <details className="collapsible-section" open style={{ marginTop: "1rem" }}>
          <summary>Construction Parameters ({GROUP_2_FIELDS.length} fields)</summary>
          <div className="form-grid two-col" style={{ padding: "0.75rem" }}>
            {GROUP_2_FIELDS.map((f) => renderNumericField(f))}
          </div>
        </details>

        {/* Group 3: Risk Factors — collapsed by default */}
        <details className="collapsible-section" style={{ marginTop: "0.75rem" }}>
          <summary>Risk Factors ({GROUP_3_FIELDS.length} fields)</summary>
          <div className="form-grid two-col" style={{ padding: "0.75rem" }}>
            {GROUP_3_FIELDS.map((f) => renderNumericField(f))}
          </div>
        </details>

        {/* Prediction Interval selector */}
        <div style={{ marginTop: "1rem" }}>
          <p className="eyebrow" style={{ marginBottom: "0.33rem" }}>Prediction Interval</p>
          <div className="chip-row">
            {CONFIDENCE_PRESETS.map((p) => (
              <button
                key={p.value}
                type="button"
                className="chip"
                style={
                  confidence === p.value
                    ? { background: "var(--steel)", color: "#fff", borderColor: "var(--steel)" }
                    : undefined
                }
                onClick={() => setConfidence(p.value)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="action-row" style={{ marginTop: "1rem" }}>
          <button
            className="action-button"
            type="button"
            onClick={runSinglePrediction}
            disabled={loadingSingle}
          >
            {loadingSingle ? (
              <>
                <span className="spinner" aria-hidden="true" /> Predicting...
              </>
            ) : (
              "Predict Cost"
            )}
          </button>
          <button className="secondary-button" type="button" onClick={addToBatch} disabled={loadingBatch}>
            Add to Batch
          </button>
        </div>

        {/* Skeleton loading */}
        {loadingSingle && showSkeleton && !singleResult && (
          <div className="result-grid" style={{ marginTop: "1rem" }}>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton-block" />
            ))}
          </div>
        )}

        {/* Results */}
        {singleResult && (
          <div style={{ animation: "rise 200ms ease" }}>
            <div className="result-grid" style={{ marginTop: "1rem" }}>
              <div>
                <p className="result-label">Predicted Actual Cost</p>
                <p className="result-value" style={{ fontSize: "1.5rem", fontWeight: 800 }}>
                  {formatCurrency(singleResult.predicted_actual_cost_cad)}
                </p>
              </div>
              <div>
                <p className="result-label">Predicted Overrun</p>
                <p
                  className="result-value"
                  style={{ color: overrunColor(singleResult.predicted_cost_overrun_pct) }}
                >
                  {formatNumber(singleResult.predicted_cost_overrun_pct)}%
                </p>
              </div>
              <div>
                <p className="result-label">
                  Prediction Interval{" "}
                  <span title={`${Math.round((singleResult.prediction_interval_cad.confidence_quantile ?? confidence) * 100)}% interval based on historical prediction error`} style={{ cursor: "help" }}>
                    ⓘ
                  </span>
                </p>
                <p className="result-value" style={{ fontSize: "0.9rem", color: "var(--muted)" }}>
                  {formatCurrency(singleResult.prediction_interval_cad.lower)} –{" "}
                  {formatCurrency(singleResult.prediction_interval_cad.upper)}
                </p>
              </div>
            </div>

            {/* Warning banner */}
            {singleResult.warning && (
              <div
                className="alert-box"
                style={{
                  marginTop: "0.75rem",
                  background: singleResult.confidence_degraded ? "var(--amber-soft, #fef3c7)" : "var(--copper-soft, #fef2f2)",
                  border: `1px solid ${singleResult.confidence_degraded ? "var(--amber, #f59e0b)" : "var(--warn)"}`,
                  borderRadius: "8px",
                  padding: "0.6rem 0.8rem",
                  fontSize: "0.85rem",
                }}
              >
                {singleResult.warning}
              </div>
            )}

            {/* Model metrics badge */}
            {modelHealth && modelHealth.mape !== null && (
              <p style={{ marginTop: "0.6rem", fontSize: "0.78rem", color: "var(--muted)" }}>
                <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: "var(--ok)", marginRight: 5, verticalAlign: "middle" }} />
                MAPE {(modelHealth.mape * 100).toFixed(1)}% · R² {modelHealth.r2?.toFixed(3)} · Trained on {modelHealth.training_rows?.toLocaleString()} projects
              </p>
            )}
          </div>
        )}

        {error && <p className="error-text" style={{ marginTop: "0.5rem" }}>{error}</p>}
      </article>

      {/* Batch Prediction */}
      <article className="panel-card">
        <header>
          <h3>Batch Prediction Queue ({batchEntries.length})</h3>
        </header>

        <div className="action-row">
          <button
            className="action-button"
            type="button"
            disabled={!batchEntries.length || loadingBatch}
            onClick={runBatchPrediction}
          >
            {loadingBatch ? (
              <>
                <span className="spinner" aria-hidden="true" /> Running Batch...
              </>
            ) : (
              "Run Batch"
            )}
          </button>
          <button className="secondary-button" type="button" onClick={clearBatch} disabled={loadingBatch}>
            Clear Queue
          </button>
          {batchResults.length > 0 && (
            <button
              className="secondary-button"
              type="button"
              onClick={() => exportCsv(batchEntries, batchResults)}
              aria-label="Export batch results as CSV"
            >
              Export CSV
            </button>
          )}
        </div>

        {batchResults.length ? (
          <div className="table-wrap" style={{ marginTop: "0.75rem" }}>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Predicted Actual Cost</th>
                  <th>Overrun %</th>
                  <th>Interval (CAD)</th>
                </tr>
              </thead>
              <tbody>
                {batchResults.map((item, index) => (
                  <tr key={batchEntries[index]?.id ?? index}>
                    <td>{index + 1}</td>
                    <td>{formatCurrency(item.predicted_actual_cost_cad)}</td>
                    <td style={{ color: overrunColor(item.predicted_cost_overrun_pct) }}>
                      {formatNumber(item.predicted_cost_overrun_pct)}%
                    </td>
                    <td>
                      {formatCurrency(item.prediction_interval_cad.lower)} –{" "}
                      {formatCurrency(item.prediction_interval_cad.upper)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted-text" style={{ marginTop: "0.5rem" }}>
            Batch Queue: {batchEntries.length} projects. Use &quot;Add to Batch&quot; above.
          </p>
        )}
      </article>
    </section>
  );
}
