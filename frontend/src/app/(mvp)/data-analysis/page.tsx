"use client";

import { useMemo, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import {
  generateVisualization,
  runDataAnalysis,
  uploadDataFile,
} from "@/lib/api-client";
import { normalizeError } from "@/lib/formatters";

function firstArtifactPath(payload: Record<string, unknown> | null): string | null {
  if (!payload) {
    return null;
  }

  if (typeof payload.file_path === "string" && payload.file_path) {
    return payload.file_path;
  }

  const chartInfo = payload.chart_info;
  if (
    chartInfo &&
    typeof chartInfo === "object" &&
    typeof (chartInfo as Record<string, unknown>).output_file === "string"
  ) {
    return (chartInfo as Record<string, string>).output_file;
  }

  const visualizations = payload.visualizations;
  if (Array.isArray(visualizations)) {
    for (const item of visualizations) {
      if (item && typeof item === "object") {
        const row = item as Record<string, unknown>;
        if (typeof row.path === "string" && row.path) {
          return row.path;
        }
        if (typeof row.filename === "string" && row.filename) {
          return row.filename;
        }
      }
    }
  }

  return null;
}

function basename(rawPath: string): string {
  const normalized = rawPath.replace(/\\/g, "/");
  const pieces = normalized.split("/");
  return pieces[pieces.length - 1] || rawPath;
}

export default function DataAnalysisPage() {
  const { config } = useAppConfig();
  const [file, setFile] = useState<File | null>(null);
  const [uploadedPath, setUploadedPath] = useState("");
  const [analysisType, setAnalysisType] = useState("eda");
  const [chartType, setChartType] = useState("line");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [viz, setViz] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analysisSummary = useMemo(() => {
    if (!result) {
      return [];
    }
    return Object.entries(result)
      .filter(([, value]) => ["string", "number", "boolean"].includes(typeof value))
      .slice(0, 6);
  }, [result]);

  const visualizationAsset = useMemo(() => {
    const raw = firstArtifactPath(viz);
    if (!raw) {
      return null;
    }
    const filename = basename(raw);
    const extension = filename.split(".").pop()?.toLowerCase() ?? "";
    return {
      filename,
      url: `/api/backend/api/v1/files/visualizations/${encodeURIComponent(filename)}`,
      isImage: ["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(extension),
    };
  }, [viz]);

  async function handleUploadData() {
    if (!file) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = await uploadDataFile(config, file);
      setResult(payload);
      const filePath = typeof payload.file_path === "string" ? payload.file_path : "";
      setUploadedPath(filePath);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleRunAnalysis() {
    if (!uploadedPath) {
      setError("Upload data file first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = await runDataAnalysis(config, {
        data_file: uploadedPath,
        analysis_type: analysisType,
      });
      setResult(payload);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateViz() {
    if (!uploadedPath) {
      setError("Upload data file first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = await generateVisualization(config, {
        data_file: uploadedPath,
        chart_type: chartType,
      });
      setViz(payload);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-stack">
      <article className="hero-card">
        <p className="eyebrow">L5 Analysis Layer</p>
        <h2>Dynamic data analysis and chart generation</h2>
        <p>Upload a file, run an analysis pass, then generate a chart artifact.</p>
      </article>

      <article className="panel-card">
        <header>
          <h3>Data Workflow</h3>
        </header>

        <div className="form-grid two-col">
          <label className="field-group">
            Upload File
            <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <label className="field-group">
            Uploaded Path
            <input value={uploadedPath} onChange={(event) => setUploadedPath(event.target.value)} />
          </label>
          <label className="field-group">
            Analysis Type
            <select value={analysisType} onChange={(event) => setAnalysisType(event.target.value)}>
              <option value="eda">eda</option>
              <option value="summary">summary</option>
              <option value="regression">regression</option>
            </select>
          </label>
          <label className="field-group">
            Chart Type
            <select value={chartType} onChange={(event) => setChartType(event.target.value)}>
              <option value="line">line</option>
              <option value="bar">bar</option>
              <option value="scatter">scatter</option>
              <option value="histogram">histogram</option>
            </select>
          </label>
        </div>

        <div className="action-row">
          <button className="action-button" type="button" onClick={handleUploadData}>
            {loading ? "Processing..." : "1) Upload Data"}
          </button>
          <button className="secondary-button" type="button" onClick={handleRunAnalysis}>
            2) Run Analysis
          </button>
          <button className="secondary-button" type="button" onClick={handleGenerateViz}>
            3) Generate Visualization
          </button>
        </div>

        {error ? <p className="error-text">{error}</p> : null}

        <div className="result-grid">
          <div>
            <p className="result-label">Analysis Result</p>
            {analysisSummary.length ? (
              <div className="kv-grid">
                {analysisSummary.map(([key, value]) => (
                  <div key={key} className="kv-item">
                    <span>{key}</span>
                    <strong>{String(value)}</strong>
                  </div>
                ))}
              </div>
            ) : null}
            <pre>{result ? JSON.stringify(result, null, 2) : "No analysis result yet"}</pre>
          </div>
          <div>
            <p className="result-label">Visualization Result</p>
            {visualizationAsset ? (
              <div className="artifact-card">
                <p className="muted-text">Artifact: {visualizationAsset.filename}</p>
                {visualizationAsset.isImage ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    className="artifact-image"
                    src={visualizationAsset.url}
                    alt={visualizationAsset.filename}
                  />
                ) : (
                  <a
                    className="secondary-button"
                    href={visualizationAsset.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Generated Artifact
                  </a>
                )}
              </div>
            ) : null}
            <pre>{viz ? JSON.stringify(viz, null, 2) : "No visualization result yet"}</pre>
          </div>
        </div>
      </article>
    </section>
  );
}
