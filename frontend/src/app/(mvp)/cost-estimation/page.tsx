"use client";

import { useMemo, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import {
  predictCost,
  predictCostBatch,
  type CostPrediction,
  type CostProjectFeatures,
} from "@/lib/api-client";
import { formatCurrency, formatNumber, normalizeError } from "@/lib/formatters";

const baseProject: CostProjectFeatures = {
  project_type: "commercial_office",
  location: "Toronto",
  sqft: 185000,
  floors: 18,
  num_units: 1,
  planned_duration_weeks: 78,
  estimated_cost_cad: 72000000,
  contractor_rating: 4.2,
  complexity_score: 7,
  team_experience_years: 11,
  num_change_orders: 5,
  weather_risk_factor: 0.32,
  material_volatility: 0.44,
  num_subcontractors: 16,
  budget_pressure: 0.58,
  risk_score: 6.8,
  risk_score_original: 6.3,
};

const NUM_FIELDS: Array<keyof CostProjectFeatures> = [
  "sqft",
  "floors",
  "num_units",
  "planned_duration_weeks",
  "estimated_cost_cad",
  "contractor_rating",
  "complexity_score",
  "team_experience_years",
  "num_change_orders",
  "weather_risk_factor",
  "material_volatility",
  "num_subcontractors",
  "budget_pressure",
  "risk_score",
  "risk_score_original",
];

export default function CostEstimationPage() {
  const { config } = useAppConfig();
  const [project, setProject] = useState<CostProjectFeatures>(baseProject);
  const [confidence, setConfidence] = useState(0.9);
  const [singleResult, setSingleResult] = useState<CostPrediction | null>(null);
  const [batchRows, setBatchRows] = useState<CostProjectFeatures[]>([]);
  const [batchResults, setBatchResults] = useState<CostPrediction[]>([]);
  const [loadingSingle, setLoadingSingle] = useState(false);
  const [loadingBatch, setLoadingBatch] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canRunBatch = batchRows.length > 0;
  const quantileLabel = useMemo(() => `${Math.round(confidence * 100)}%`, [confidence]);

  function updateNumericField(field: keyof CostProjectFeatures, raw: string) {
    setProject((prev) => ({
      ...prev,
      [field]: Number(raw),
    }));
  }

  async function runSinglePrediction() {
    setLoadingSingle(true);
    setError(null);
    try {
      const response = await predictCost(config, project, confidence);
      setSingleResult(response.prediction);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoadingSingle(false);
    }
  }

  async function runBatchPrediction() {
    if (!batchRows.length) {
      return;
    }

    setLoadingBatch(true);
    setError(null);
    try {
      const response = await predictCostBatch(config, batchRows, confidence);
      setBatchResults(response.predictions);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoadingBatch(false);
    }
  }

  function addCurrentProjectToBatch() {
    setBatchRows((prev) => [project, ...prev]);
    // Existing batch predictions no longer represent the new queue content.
    setBatchResults([]);
  }

  function clearBatchQueue() {
    setBatchRows([]);
    setBatchResults([]);
  }

  return (
    <section className="page-stack">
      <article className="hero-card">
        <p className="eyebrow">L3 Cost Layer</p>
        <h2>Structured regression prediction for construction costs</h2>
        <p>
          This page uses the dedicated cost-estimation model instead of free-form LLM guessing.
        </p>
      </article>

      <article className="panel-card">
        <header>
          <h3>Single Project Prediction</h3>
        </header>

        <div className="form-grid two-col">
          <label className="field-group">
            Project Type
            <input
              value={project.project_type}
              onChange={(event) =>
                setProject((prev) => ({ ...prev, project_type: event.target.value }))
              }
            />
          </label>
          <label className="field-group">
            Location
            <input
              value={project.location}
              onChange={(event) =>
                setProject((prev) => ({ ...prev, location: event.target.value }))
              }
            />
          </label>

          {NUM_FIELDS.map((field) => (
            <label className="field-group" key={field}>
              {field}
              <input
                type="number"
                step="any"
                value={project[field] as number}
                onChange={(event) => updateNumericField(field, event.target.value)}
              />
            </label>
          ))}
        </div>

        <label className="field-group">
          Confidence Quantile: {quantileLabel}
          <input
            type="range"
            min="0.5"
            max="0.99"
            step="0.01"
            value={confidence}
            onChange={(event) => setConfidence(Number(event.target.value))}
          />
        </label>

        <div className="action-row">
          <button className="action-button" type="button" onClick={runSinglePrediction}>
            {loadingSingle ? "Predicting..." : "Predict Cost"}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={addCurrentProjectToBatch}
          >
            Add Current Project To Batch
          </button>
        </div>

        {singleResult ? (
          <div className="result-grid">
            <div>
              <p className="result-label">Predicted Actual Cost</p>
              <p className="result-value">{formatCurrency(singleResult.predicted_actual_cost_cad)}</p>
            </div>
            <div>
              <p className="result-label">Predicted Overrun</p>
              <p className="result-value">{formatNumber(singleResult.predicted_cost_overrun_pct)}%</p>
            </div>
            <div>
              <p className="result-label">Prediction Interval</p>
              <p className="result-value">
                {formatCurrency(singleResult.prediction_interval_cad.lower)} -{" "}
                {formatCurrency(singleResult.prediction_interval_cad.upper)}
              </p>
            </div>
          </div>
        ) : null}
        {error ? <p className="error-text">{error}</p> : null}
      </article>

      <article className="panel-card">
        <header>
          <h3>Batch Prediction Queue ({batchRows.length})</h3>
        </header>

        <div className="action-row">
          <button
            className="action-button"
            type="button"
            disabled={!canRunBatch}
            onClick={runBatchPrediction}
          >
            {loadingBatch ? "Running Batch..." : "Run Batch"}
          </button>
          <button className="secondary-button" type="button" onClick={clearBatchQueue}>
            Clear Queue
          </button>
        </div>

        {batchResults.length ? (
          <div className="table-wrap">
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
                  <tr key={`${item.predicted_actual_cost_cad}-${index}`}>
                    <td>{index + 1}</td>
                    <td>{formatCurrency(item.predicted_actual_cost_cad)}</td>
                    <td>{formatNumber(item.predicted_cost_overrun_pct)}%</td>
                    <td>
                      {formatCurrency(item.prediction_interval_cad.lower)} -{" "}
                      {formatCurrency(item.prediction_interval_cad.upper)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted-text">Add projects from the form above to run batch mode.</p>
        )}
      </article>
    </section>
  );
}
