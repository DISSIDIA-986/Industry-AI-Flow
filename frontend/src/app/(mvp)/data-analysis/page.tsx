"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import CollapsibleCode from "@/components/CollapsibleCode";
import DarkHeroWrapper from "@/components/DarkHeroWrapper";
import {
  dataAnalysisStreamUrl,
  runDataAnalysis,
  startDataAnalysisJob,
  uploadDataFile,
} from "@/lib/api-client";
import { normalizeError } from "@/lib/formatters";

/* ------------------------------------------------------------------ */
/*  Pipeline stage tracking for SSE streaming                         */
/* ------------------------------------------------------------------ */
interface StageEvent {
  stage: string;
  status: string;
  progress: number;
  detail: string;
  elapsed_ms: number;
}

const STAGE_LABELS: Record<string, string> = {
  file_resolution: "File Resolution",
  code_generation: "AI Code Generation",
  visualization: "Visualization",
  done: "Complete",
};

const STAGE_ORDER = ["file_resolution", "code_generation", "visualization", "done"];

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
  const [stages, setStages] = useState<Record<string, StageEvent>>({});
  const [streaming, setStreaming] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const METRICS_WHITELIST = ["success", "analysis_type", "execution_time"];

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

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const handleRunAnalysisStreaming = useCallback(async () => {
    if (!uploadedPath) {
      setError("Upload data file first.");
      return;
    }

    setLoading(true);
    setStreaming(true);
    setError(null);
    setResult(null);
    setViz(null);
    setStages({});
    eventSourceRef.current?.close();

    try {
      // Step 1: Start the job
      const { job_id } = await startDataAnalysisJob(config, {
        data_file: uploadedPath,
        analysis_type: analysisType,
        instruction,
        generate_visualization: includeViz,
        chart_type: includeViz ? chartType : undefined,
      });

      // Step 2: Subscribe to SSE stream
      const url = dataAnalysisStreamUrl(config, job_id);
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.addEventListener("stage", (ev) => {
        try {
          const data = JSON.parse(ev.data) as StageEvent;
          setStages((prev) => ({ ...prev, [data.stage]: data }));
        } catch { /* ignore parse errors */ }
      });

      es.addEventListener("result", (ev) => {
        try {
          const payload = JSON.parse(ev.data) as Record<string, unknown>;
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
            if (!includeViz) setViz(null);
          }
        } catch { /* ignore */ }
        es.close();
        setLoading(false);
        setStreaming(false);
      });

      es.addEventListener("error", (ev) => {
        // SSE errors — try to parse error data
        const me = ev as MessageEvent;
        if (me.data) {
          try {
            const d = JSON.parse(me.data);
            setError(d.error || "Analysis failed");
          } catch {
            setError("Connection to analysis pipeline lost");
          }
        }
        es.close();
        setLoading(false);
        setStreaming(false);
      });

      es.onerror = () => {
        // EventSource built-in error (connection lost)
        if (es.readyState === EventSource.CLOSED) {
          if (!result) {
            // Only show error if we didn't get a result
            setError("Connection to analysis pipeline lost. Results may still be processing.");
          }
          setLoading(false);
          setStreaming(false);
        }
      };
    } catch (err) {
      setError(normalizeError(err));
      setLoading(false);
      setStreaming(false);
    }
  }, [config, uploadedPath, analysisType, instruction, includeViz, chartType, result]);

  // Fallback: non-streaming analysis (in case SSE fails)
  async function handleRunAnalysisBatch() {
    if (!uploadedPath) {
      setError("Upload data file first.");
      return;
    }

    setLoading(true);
    setError(null);
    setStages({});
    try {
      const payload = await runDataAnalysis(config, {
        data_file: uploadedPath,
        analysis_type: analysisType,
        instruction,
        generate_visualization: includeViz,
        chart_type: includeViz ? chartType : undefined,
      });

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
      <DarkHeroWrapper data-testid="data-analysis-hero" className="mb-0">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">
              Dynamic Data Analysis
            </p>
            <h1 className="text-xl font-bold text-gray-200 mt-1">
              AI-powered data understanding
            </h1>
            <p className="text-sm text-gray-400 mt-0.5">
              Upload a dataset, run analysis, and generate visualizations — powered by cloud LLM + sandbox execution
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-4 text-xs text-gray-500">
            <span>Cloud LLM</span>
            <span className="text-gray-600">·</span>
            <span>Docker Sandbox</span>
            <span className="text-gray-600">·</span>
            <span>8 Chart Types</span>
          </div>
        </div>
      </DarkHeroWrapper>

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
          <button className="action-button" type="button" onClick={handleUploadData} disabled={loading}>
            {loading && !streaming ? "Processing..." : "1) Upload Data"}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={handleRunAnalysisStreaming}
            disabled={loading}
            data-testid="run-analysis-btn"
          >
            {streaming ? "Analyzing..." : "2) Run Analysis"}
          </button>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.875rem" }}>
            <input
              type="checkbox"
              checked={includeViz}
              onChange={(event) => setIncludeViz(event.target.checked)}
              data-testid="include-viz-toggle"
            />
            Include Visualization
          </label>
        </div>

        {/* Pipeline progress visualization */}
        {streaming && (
          <div
            className="mt-4 rounded-xl border border-gray-700 bg-[#1a1a2e] p-4"
            data-testid="analysis-pipeline-viz"
            role="status"
            aria-live="polite"
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">
              Analysis Pipeline
            </p>
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-0">
              {STAGE_ORDER.filter((s) => s !== "done" && (s !== "visualization" || includeViz)).map(
                (stageId, idx, arr) => {
                  const ev = stages[stageId];
                  const status = ev?.status ?? "pending";
                  const dotColor =
                    status === "completed" ? "bg-emerald-400" :
                    status === "running" ? "bg-amber-400 animate-pulse" :
                    status === "failed" ? "bg-red-400" :
                    status === "skipped" ? "bg-gray-600" :
                    "bg-gray-600";
                  return (
                    <div key={stageId} className="flex items-center gap-2 sm:flex-1">
                      <div className={`w-3 h-3 rounded-full flex-shrink-0 ${dotColor}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-200 truncate">
                          {STAGE_LABELS[stageId] ?? stageId}
                        </p>
                        {ev?.detail && (
                          <p className="text-xs text-gray-500 truncate">{ev.detail}</p>
                        )}
                      </div>
                      {idx < arr.length - 1 && (
                        <div className="hidden sm:block w-8 h-px bg-gray-700 flex-shrink-0" />
                      )}
                    </div>
                  );
                }
              )}
            </div>
            {/* Summary strip after stages done */}
            {stages.done?.status === "completed" && (
              <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
                <span className="font-mono">
                  {stages.code_generation?.detail || "Complete"}
                </span>
              </div>
            )}
          </div>
        )}

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
                {(() => {
                  const cg = result.code_generation;
                  const mode = typeof cg === "object" && cg !== null ? (cg as Record<string, unknown>).mode : null;
                  return typeof mode === "string" ? ` (${mode})` : null;
                })()}
              </div>
            )}

            {/* Answer / summary text */}
            {typeof result?.answer === "string" && result.answer && (
              <div className="artifact-card">
                <p className="result-label">Summary</p>
                <p style={{ marginTop: "0.35rem" }}>{result.answer as string}</p>
              </div>
            )}

            {/* Code generation mode badge */}
            {(() => {
              const cg = result?.code_generation;
              const mode = typeof cg === "object" && cg !== null ? (cg as Record<string, unknown>).mode : null;
              if (typeof mode !== "string") return null;
              const isLLM = mode === "llm" || mode === "llm_generated";
              const fallbackReason = typeof cg === "object" && cg !== null ? (cg as Record<string, unknown>).fallback_reason : null;
              return (
                <div className="flex items-center gap-2 text-sm" data-testid="code-gen-mode-badge">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      isLLM
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : "bg-amber-50 text-amber-700 border border-amber-200"
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${isLLM ? "bg-emerald-500" : "bg-amber-500"}`} />
                    {isLLM ? "LLM Generated" : "Template Fallback"}
                  </span>
                  {typeof fallbackReason === "string" && fallbackReason && (
                    <span className="text-xs text-gray-500">{fallbackReason}</span>
                  )}
                </div>
              );
            })()}

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
