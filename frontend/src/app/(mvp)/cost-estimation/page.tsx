"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import DarkHeroWrapper from "@/components/DarkHeroWrapper";
import {
  getCostHealth,
  predictCost,
  predictCostBatch,
  predictWhatIf,
  findSimilarProjects,
  getCostTransparency,
  type CostPrediction,
  type CostProjectFeatures,
  type DataTransparencyResponse,
  type SimilarProject,
  type WhatIfOverride,
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
  };

  return { project, errors };
}

function exportCsv(entries: BatchEntry[], results: CostPrediction[]) {
  const headers = [
    "project_type", "location", ...GROUP_1_FIELDS, ...GROUP_2_FIELDS, ...GROUP_3_FIELDS,
    "predicted_actual_cost_cad", "predicted_cost_overrun_pct",
    "interval_lower", "interval_upper",
    "model_type", "shap_top1_feature", "shap_top1_pct", "shap_top2_feature", "shap_top2_pct", "shap_top3_feature", "shap_top3_pct",
  ];
  const rows = results.map((r, i) => {
    const p = entries[i]?.project;
    /* eslint-disable @typescript-eslint/no-explicit-any */
    const shap = (r as any).shap_contributions as Array<{ feature: string; contribution_pct: number }> | undefined;
    const modelType = (r as any).model_info?.type ?? "";
    return [
      p?.project_type ?? "", p?.location ?? "",
      ...GROUP_1_FIELDS.map((f) => String(p?.[f] ?? "")),
      ...GROUP_2_FIELDS.map((f) => String(p?.[f] ?? "")),
      ...GROUP_3_FIELDS.map((f) => String(p?.[f] ?? "")),
      String(r.predicted_actual_cost_cad),
      String(r.predicted_cost_overrun_pct),
      String(r.prediction_interval_cad.lower),
      String(r.prediction_interval_cad.upper),
      modelType,
      shap?.[0]?.feature ?? "", shap?.[0]?.contribution_pct ?? "",
      shap?.[1]?.feature ?? "", shap?.[1]?.contribution_pct ?? "",
      shap?.[2]?.feature ?? "", shap?.[2]?.contribution_pct ?? "",
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

  /* Similar projects */
  const [similarProjects, setSimilarProjects] = useState<SimilarProject[]>([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);

  /* What-if */
  const [whatIfOverrides, setWhatIfOverrides] = useState<Record<string, number>>({});
  const [whatIfResult, setWhatIfResult] = useState<CostPrediction | null>(null);
  const [loadingWhatIf, setLoadingWhatIf] = useState(false);
  const whatIfTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastParsedProject = useRef<CostProjectFeatures | null>(null);

  /* Data transparency */
  const [transparency, setTransparency] = useState<DataTransparencyResponse | null>(null);

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

    getCostTransparency(config)
      .then(setTransparency)
      .catch(() => { /* silent */ });
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
      lastParsedProject.current = project;
      setWhatIfOverrides({});
      setWhatIfResult(null);

      // Load similar projects in background
      setLoadingSimilar(true);
      findSimilarProjects(config, project, 5)
        .then((res) => setSimilarProjects(res.projects || []))
        .catch(() => setSimilarProjects([]))
        .finally(() => setLoadingSimilar(false));
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoadingSingle(false);
      if (skeletonTimer.current) clearTimeout(skeletonTimer.current);
      setShowSkeleton(false);
    }
  }, [config, fields, confidence]);

  const handleWhatIfChange = useCallback((feature: string, value: number) => {
    setWhatIfOverrides((prev) => {
      const next = { ...prev, [feature]: value };

      // Debounced API call — build overrides from the fresh `next` state
      if (whatIfTimer.current) clearTimeout(whatIfTimer.current);
      whatIfTimer.current = setTimeout(async () => {
        if (!lastParsedProject.current) return;
        const overrides: WhatIfOverride[] = Object.entries(next)
          .filter(([, v]) => v !== undefined)
          .map(([f, v]) => ({ feature: f, value: v }));
        if (overrides.length === 0) return;

        setLoadingWhatIf(true);
        try {
          const res = await predictWhatIf(config, lastParsedProject.current, overrides, confidence);
          setWhatIfResult(res.modified_prediction);
        } catch {
          // Silent fail — what-if is non-critical
        } finally {
          setLoadingWhatIf(false);
        }
      }, 300);

      return next;
    });
  }, [config, confidence]);

  const resetWhatIf = useCallback(() => {
    setWhatIfOverrides({});
    setWhatIfResult(null);
  }, []);

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
      {/* Dark Hero */}
      <DarkHeroWrapper data-testid="cost-estimation-hero" className="mb-0">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">
              Construction Cost Intelligence
            </p>
            <h1 className="text-xl font-bold text-gray-200 mt-1">
              Predict and explain cost overruns
            </h1>
            <p className="text-sm text-gray-400 mt-0.5">
              CatBoost ML · SHAP Explainability · 10,000 Projects
            </p>
            {isDefaultData && (
              <span className="inline-block mt-1.5 px-2 py-0.5 text-xs font-medium rounded-full bg-amber-500/20 text-amber-400">
                Sample Data
              </span>
            )}
          </div>
          <div className="hidden sm:flex items-center gap-4 text-xs text-gray-500">
            {modelHealth && modelHealth.mape !== null && (
              <>
                <span>MAPE {(modelHealth.mape * 100).toFixed(1)}%</span>
                <span className="text-gray-600">·</span>
                <span>R² {modelHealth.r2?.toFixed(3)}</span>
              </>
            )}
          </div>
        </div>
      </DarkHeroWrapper>

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

            {/* Model metrics badge moved to below SHAP waterfall for honest dual display */}
          </div>
        )}

        {/* SHAP Waterfall — "Why This Overrun?" */}
        {singleResult && (singleResult as any).shap_contributions && (
          <div data-testid="shap-waterfall" style={{ marginTop: "1.25rem", padding: "1rem", background: "#f9fafb", borderRadius: "12px", border: "1px solid #e5e7eb" }}>
            <h4 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.75rem" }}>
              Why This Overrun?
            </h4>
            {(singleResult as any).shap_base_rate_pct !== undefined && (
              <p style={{ fontSize: "0.78rem", color: "#6b7280", marginBottom: "0.5rem" }}>
                Base rate: {((singleResult as any).shap_base_rate_pct as number).toFixed(1)}% →
                {" "}Predicted: {singleResult.predicted_cost_overrun_pct.toFixed(1)}%
              </p>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              {((singleResult as any).shap_contributions as Array<{feature: string; label: string; value: any; contribution_pct: number; direction: string}>).map((c) => {
                const maxBar = Math.max(...((singleResult as any).shap_contributions as Array<{contribution_pct: number}>).map((x) => Math.abs(x.contribution_pct)));
                const barWidth = maxBar > 0 ? (Math.abs(c.contribution_pct) / maxBar) * 100 : 0;
                const isIncrease = c.direction === "increase";
                return (
                  <div key={c.feature} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem" }}>
                    <span style={{ width: "130px", textAlign: "right", color: "#374151", flexShrink: 0 }}>{c.label}</span>
                    <div style={{ flex: 1, position: "relative", height: "20px", background: "#f3f4f6", borderRadius: "4px", overflow: "hidden" }}>
                      <div
                        aria-label={`${c.label}: ${isIncrease ? "increases" : "decreases"} overrun by ${Math.abs(c.contribution_pct).toFixed(1)}%`}
                        style={{
                          width: `${Math.min(barWidth, 100)}%`,
                          height: "100%",
                          background: isIncrease ? "#dc2626" : "#16a34a",
                          borderRadius: "4px",
                          transition: "width 0.3s ease",
                        }}
                      />
                    </div>
                    <span style={{ width: "65px", fontFamily: "var(--font-mono, monospace)", color: isIncrease ? "#dc2626" : "#16a34a", fontWeight: 600, flexShrink: 0 }}>
                      {c.contribution_pct > 0 ? "+" : ""}{c.contribution_pct.toFixed(1)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* SHAP empty state — before first prediction */}
        {!singleResult && !loadingSingle && (
          <div data-testid="shap-empty" style={{ marginTop: "1rem", padding: "1rem", background: "#f9fafb", borderRadius: "12px", border: "1px solid #e5e7eb", textAlign: "center" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", opacity: 0.4, marginBottom: "0.5rem" }}>
              {[80, 60, 45, 30, 50].map((w, i) => (
                <div key={i} style={{ height: "12px", width: `${w}%`, background: "#d1d5db", borderRadius: "4px", marginLeft: "auto", marginRight: "auto" }} />
              ))}
            </div>
            <p style={{ fontSize: "0.85rem", color: "#6b7280" }}>Click <strong>Predict Cost</strong> to see cost drivers</p>
          </div>
        )}

        {/* Model metrics — honest dual display */}
        {singleResult && (singleResult as any).model_info && (
          <div data-testid="model-info" style={{ marginTop: "0.6rem", fontSize: "0.78rem", color: "#6b7280" }}>
            <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: "#16a34a", marginRight: 5, verticalAlign: "middle" }} />
            {(singleResult as any).model_info.type === "catboost" ? "CatBoost" : "Ridge"} ·{" "}
            Overrun R² {((singleResult as any).model_info.metrics?.overrun_pct?.r2 ?? 0).toFixed(3)} ·{" "}
            Cost R² {((singleResult as any).model_info.metrics?.actual_cost?.r2 ?? 0).toFixed(3)} ·{" "}
            {((singleResult as any).model_info.training_rows ?? 0).toLocaleString()} projects ·{" "}
            <span style={{ fontStyle: "italic" }}>{(singleResult as any).model_info.data_source}</span>
          </div>
        )}

        {error && <p className="error-text" style={{ marginTop: "0.5rem" }}>{error}</p>}
      </article>

      {/* What-If Scenario Analysis */}
      {singleResult && (singleResult as any).shap_contributions && (
        <article className="panel-card" data-testid="what-if-section">
          <details open>
            <summary style={{ cursor: "pointer", fontWeight: 600, fontSize: "1.05rem" }}>
              What-If Scenario Analysis
              {loadingWhatIf && <span className="spinner" style={{ marginLeft: "0.5rem", width: 14, height: 14 }} />}
            </summary>
            <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: "0.3rem", marginBottom: "0.75rem" }}>
              Adjust parameters to see how changes affect the predicted overrun.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {[
                { key: "contractor_rating", label: "Contractor Rating", min: 2, max: 5, step: 0.1, decimals: 1 },
                { key: "num_change_orders", label: "Change Orders", min: 0, max: 30, step: 1, decimals: 0 },
                { key: "weather_risk_factor", label: "Weather Risk", min: 0, max: 1, step: 0.05, decimals: 2 },
                { key: "material_volatility", label: "Material Volatility", min: 0, max: 1, step: 0.05, decimals: 2 },
                { key: "budget_pressure", label: "Budget Pressure", min: 0, max: 1, step: 0.05, decimals: 2 },
              ].map((s) => {
                const originalVal = Number(fields[s.key] || 0);
                const currentVal = whatIfOverrides[s.key] ?? originalVal;
                const changed = whatIfOverrides[s.key] !== undefined && whatIfOverrides[s.key] !== originalVal;
                return (
                  <div key={s.key} style={{ display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "0.85rem" }}>
                    <span style={{ width: "140px", textAlign: "right", color: "#374151", flexShrink: 0 }}>{s.label}</span>
                    <span style={{ width: "50px", fontFamily: "var(--font-mono, monospace)", color: changed ? "#2563eb" : "#6b7280", textAlign: "right", flexShrink: 0, fontWeight: changed ? 600 : 400 }}>
                      {currentVal.toFixed(s.decimals)}
                    </span>
                    <input
                      type="range"
                      min={s.min}
                      max={s.max}
                      step={s.step}
                      value={currentVal}
                      onChange={(e) => handleWhatIfChange(s.key, Number(e.target.value))}
                      style={{ flex: 1, accentColor: "#2563eb", height: "6px" }}
                      aria-label={s.label}
                      aria-valuetext={`${currentVal.toFixed(s.decimals)}`}
                      data-testid={`whatif-slider-${s.key}`}
                    />
                  </div>
                );
              })}
            </div>

            {/* What-if delta display */}
            {whatIfResult && singleResult && (
              <div data-testid="whatif-delta" style={{ marginTop: "0.75rem", padding: "0.75rem", background: "#f9fafb", borderRadius: "8px", border: "1px solid #e5e7eb", display: "flex", gap: "1.5rem", flexWrap: "wrap", fontSize: "0.9rem" }}>
                <div>
                  <span style={{ color: "#6b7280" }}>Original: </span>
                  <span style={{ fontWeight: 600, color: overrunColor(singleResult.predicted_cost_overrun_pct) }}>
                    {singleResult.predicted_cost_overrun_pct.toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span style={{ color: "#6b7280" }}>Scenario: </span>
                  <span style={{ fontWeight: 600, color: overrunColor(whatIfResult.predicted_cost_overrun_pct) }}>
                    {whatIfResult.predicted_cost_overrun_pct.toFixed(1)}%
                  </span>
                </div>
                <div>
                  {(() => {
                    const delta = whatIfResult.predicted_cost_overrun_pct - singleResult.predicted_cost_overrun_pct;
                    return (
                      <>
                        <span style={{ color: "#6b7280" }}>Delta: </span>
                        <span style={{ fontWeight: 700, color: delta < 0 ? "#16a34a" : delta > 0 ? "#dc2626" : "#6b7280" }}>
                          {delta > 0 ? "+" : ""}{delta.toFixed(1)}%
                        </span>
                      </>
                    );
                  })()}
                </div>
                <button
                  type="button"
                  onClick={resetWhatIf}
                  style={{ marginLeft: "auto", fontSize: "0.78rem", color: "#2563eb", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
                >
                  Reset
                </button>
              </div>
            )}
          </details>
        </article>
      )}

      {/* Similar Projects */}
      {singleResult && (
        <article className="panel-card" data-testid="similar-projects">
          <h3 style={{ fontWeight: 600, fontSize: "1.05rem", marginBottom: "0.75rem" }}>
            Similar Projects in Dataset
            {loadingSimilar && <span className="spinner" style={{ marginLeft: "0.5rem", width: 14, height: 14 }} />}
          </h3>
          <p style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: "0.5rem" }}>
            Comparable projects from the training dataset — not validated against real outcomes.
          </p>
          <div style={{ display: "flex", gap: "0.75rem", overflowX: "auto", paddingBottom: "0.5rem" }}>
            {similarProjects.length > 0 ? similarProjects.map((sp, i) => (
              <div key={i} style={{ minWidth: "200px", maxWidth: "240px", padding: "0.75rem", background: "#f9fafb", borderRadius: "12px", border: "1px solid #e5e7eb", fontSize: "0.85rem", flexShrink: 0 }}>
                <p style={{ fontWeight: 600, color: "#111827", marginBottom: "0.25rem" }}>
                  {sp.project_type.replace(/_/g, " ")}
                </p>
                <p style={{ color: "#6b7280", fontSize: "0.78rem" }}>
                  {sp.location} · {sp.sqft.toLocaleString()} sqft
                </p>
                <p style={{ marginTop: "0.4rem", fontWeight: 700, fontSize: "1rem", color: overrunColor(sp.actual_overrun_pct) }}>
                  {sp.actual_overrun_pct > 0 ? "+" : ""}{sp.actual_overrun_pct.toFixed(1)}% overrun
                </p>
                {sp.key_diff && (
                  <p style={{ marginTop: "0.25rem", fontSize: "0.75rem", color: "#9ca3af", fontStyle: "italic" }}>
                    {sp.key_diff}
                  </p>
                )}
              </div>
            )) : !loadingSimilar && (
              <div style={{ minWidth: "200px", padding: "0.75rem", background: "#f9fafb", borderRadius: "12px", border: "1px solid #e5e7eb", fontSize: "0.85rem" }}>
                <p style={{ color: "#6b7280" }}>No similar projects found for this project type</p>
              </div>
            )}
          </div>
        </article>
      )}

      {/* Data Transparency */}
      {singleResult && (
        <article className="panel-card" data-testid="data-transparency">
          <details>
            <summary style={{ cursor: "pointer", fontWeight: 600, fontSize: "1.05rem" }}>
              Data Transparency
              <span style={{ fontFamily: "var(--font-mono, monospace)", fontSize: "0.78rem", color: "#6b7280", marginLeft: "0.5rem" }}>
                {transparency?.dataset
                  ? `${transparency.dataset.rows.toLocaleString()} ${transparency.dataset.source.replace(/_/g, " ")} projects`
                  : "10,000 Synthetic Projects · Remediated · BCPI-Adjusted"}
              </span>
            </summary>
            <div style={{ marginTop: "0.75rem", fontSize: "0.85rem", color: "#374151" }}>
              {/* Model performance comparison */}
              {transparency?.model_performance && (
                <div style={{ marginBottom: "0.75rem", padding: "0.6rem", background: "#f3f4f6", borderRadius: "8px" }}>
                  <h4 style={{ fontWeight: 600, marginBottom: "0.4rem", fontSize: "0.85rem" }}>Model Performance</h4>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.4rem", fontFamily: "var(--font-mono, monospace)", fontSize: "0.78rem" }}>
                    <div>Overrun R²: <strong>{transparency.model_performance.overrun_r2?.toFixed(3) ?? "—"}</strong></div>
                    <div>Cost R²: <strong>{transparency.model_performance.actual_cost_r2?.toFixed(3) ?? "—"}</strong></div>
                    <div>Overrun MAPE: <strong>{transparency.model_performance.overrun_mape ? `${(transparency.model_performance.overrun_mape * 100).toFixed(1)}%` : "—"}</strong></div>
                    <div>Cost MAPE: <strong>{transparency.model_performance.actual_cost_mape ? `${(transparency.model_performance.actual_cost_mape * 100).toFixed(1)}%` : "—"}</strong></div>
                  </div>
                  <p style={{ fontSize: "0.72rem", color: "#9ca3af", marginTop: "0.3rem", fontStyle: "italic" }}>
                    Not directly comparable to published results on real datasets (e.g., RSMeans R²=0.883)
                  </p>
                </div>
              )}

              <h4 style={{ fontWeight: 600, marginBottom: "0.4rem" }}>Known Limitations</h4>
              <ul style={{ paddingLeft: "1.25rem", lineHeight: 1.7, color: "#6b7280" }}>
                {(transparency?.limitations ?? [
                  "Training data is synthetic (generated, not collected from real projects)",
                  "Location cost adjustments based on Statistics Canada BCPI estimates",
                  "Duration values were capped at 520 weeks during data remediation",
                  "Model has not been validated against real construction project outcomes",
                  "Not directly comparable to published results on real datasets (e.g., RSMeans)",
                ]).map((lim, i) => (
                  <li key={i}>{lim}</li>
                ))}
              </ul>
            </div>
          </details>
        </article>
      )}

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
