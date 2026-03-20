"use client";

import { useMemo, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import CollapsibleCode from "@/components/CollapsibleCode";
import {
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
  const [uploadedPath, setUploadedPath] = useState("tips.csv");
  const [analysisType, setAnalysisType] = useState("eda");
  const [chartType, setChartType] = useState("line");
  const [instruction, setInstruction] = useState(
    "Run a concise analysis and summarize key findings."
  );
  const [includeViz, setIncludeViz] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [viz, setViz] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const METRICS_WHITELIST = ["success", "analysis_type", "code_gen_mode", "execution_time"];

  const analysisSummary = useMemo(() => {
    if (!result) {
      return [];
    }
    return METRICS_WHITELIST
      .filter((key) => key in result && result[key] !== undefined && result[key] !== null)
      .map((key) => [key, result[key]] as [string, string | number | boolean]);
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
      const filePath =
        (typeof payload.file_path === "string" && payload.file_path) ||
        (typeof payload.file_id === "string" ? payload.file_id : "");
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
        instruction,
        generate_visualization: includeViz,
        chart_type: includeViz ? chartType : undefined,
      });

      // Extract embedded visualization if present
      if (
        payload.visualization &&
        typeof payload.visualization === "object" &&
        !Array.isArray(payload.visualization)
      ) {
        setViz(payload.visualization as Record<string, unknown>);
        const { visualization: _v, ...analysisOnly } = payload;
        setResult(analysisOnly);
      } else {
        setResult(payload);
        if (!includeViz) {
          setViz(null);
        }
      }
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
        <p>Upload a file and run analysis. Toggle &quot;Include Visualization&quot; to generate a chart alongside.</p>
      </article>

      <article className="panel-card">
        <header>
          <h3>Data Workflow</h3>
        </header>

        <div className="form-grid two-col">
          <label className="field-group" style={{ gridColumn: "1 / -1" }}>
            Upload File
            <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          <label className="field-group">
            Analysis Type
            <select value={analysisType} onChange={(event) => setAnalysisType(event.target.value)}>
              <option value="eda">eda</option>
              <option value="summary">summary</option>
              <option value="regression">regression</option>
            </select>
          </label>
          {includeViz && (
            <label className="field-group">
              Chart Type
              <select value={chartType} onChange={(event) => setChartType(event.target.value)}>
                <option value="line">line</option>
                <option value="bar">bar</option>
                <option value="scatter">scatter</option>
                <option value="histogram">histogram</option>
                <option value="box">box</option>
                <option value="heatmap">heatmap</option>
                <option value="violin">violin</option>
                <option value="pie">pie</option>
              </select>
            </label>
          )}
          <label className="field-group">
            Analysis Instruction
            <input
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              placeholder="Describe what analysis or chart you want"
            />
          </label>
        </div>

        <div className="action-row">
          <button className="action-button" type="button" onClick={handleUploadData}>
            {loading ? "Processing..." : "1) Upload Data"}
          </button>
          <button className="secondary-button" type="button" onClick={handleRunAnalysis}>
            {loading ? "Processing..." : "2) Run Analysis"}
          </button>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem" }}>
            <input
              type="checkbox"
              checked={includeViz}
              onChange={(event) => setIncludeViz(event.target.checked)}
            />
            Include Visualization
          </label>
        </div>

        {error ? <p className="error-text">{error}</p> : null}

        {(result || viz) && (
          <div className="result-stack">
            {/* Status banner */}
            {result && (
              <div
                className={`status-banner ${
                  result.status === "error" || result.error ? "error" : "success"
                }`}
              >
                {result.status === "error" || result.error ? "Error" : "Analysis Complete"}
                {typeof result.analysis_type === "string" && ` — ${result.analysis_type}`}
                {typeof result.code_gen_mode === "string" && ` (${result.code_gen_mode})`}
              </div>
            )}

            {/* Answer / summary text */}
            {typeof result?.answer === "string" && result.answer && (
              <div className="artifact-card">
                <p className="result-label">Summary</p>
                <p style={{ marginTop: "0.35rem" }}>{result.answer as string}</p>
              </div>
            )}

            {/* Key metrics */}
            {analysisSummary.length > 0 && (
              <div>
                <p className="result-label">Key Metrics</p>
                <div className="kv-grid">
                  {analysisSummary.map(([key, value]) => (
                    <div key={key} className="kv-item">
                      <span>{key}</span>
                      <strong>
                        {key === "success" ? (
                          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                            <span
                              style={{
                                width: "8px",
                                height: "8px",
                                borderRadius: "50%",
                                background: value === true || value === "true" ? "#22c55e" : "#ef4444",
                                flexShrink: 0,
                              }}
                            />
                            {value === true || value === "true" ? "Yes" : "No"}
                          </span>
                        ) : (
                          String(value)
                        )}
                      </strong>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Visualization image */}
            {visualizationAsset && (
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
            )}

            {/* Generated code (collapsed) */}
            {(() => {
              const code = String(result?.generated_code ?? result?.generated_code_preview ?? "");
              return code ? <CollapsibleCode title="Generated Code" code={code} language="python" /> : null;
            })()}

            {/* Analysis output (collapsed) */}
            {(() => {
              const output = String(result?.output ?? result?.raw_output ?? "");
              return output ? <CollapsibleCode title="Analysis Output" code={output} language="text" /> : null;
            })()}

            {/* Full analysis response (collapsed) */}
            {result && (
              <CollapsibleCode
                title="Full Response (JSON)"
                code={JSON.stringify(result, null, 2)}
                language="json"
              />
            )}

            {/* Full visualization response (collapsed) */}
            {viz && (
              <CollapsibleCode
                title="Visualization Response (JSON)"
                code={JSON.stringify(viz, null, 2)}
                language="json"
              />
            )}
          </div>
        )}
      </article>
    </section>
  );
}
