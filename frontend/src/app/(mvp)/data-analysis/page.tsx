"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import CollapsibleCode from "@/components/CollapsibleCode";
import DarkHeroWrapper from "@/components/DarkHeroWrapper";
import {
  dataAnalysisStreamUrl,
  previewDataFile,
  startDataAnalysisJob,
  uploadDataFile,
} from "@/lib/api-client";
import { normalizeError } from "@/lib/formatters";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface StageEvent {
  stage: string;
  status: string;
  progress: number;
  detail: string;
  elapsed_ms: number;
}

interface PreviewColumn {
  name: string;
  type: string;
  sample?: string;
}

interface AnalysisSummary {
  analysis_type?: string;
  key_findings?: string[];
  chart_type?: string;
}

/* ------------------------------------------------------------------ */
/*  Pipeline stage configuration (6-node)                              */
/* ------------------------------------------------------------------ */
const STAGE_ORDER = [
  "file_parse",
  "metadata_extract",
  "code_generation",
  "security_check",
  "sandbox_execution",
  "result_render",
];

const STAGE_LABELS: Record<string, string> = {
  file_parse: "File Parse",
  metadata_extract: "Metadata",
  code_generation: "AI Code Gen",
  security_check: "Security",
  sandbox_execution: "Sandbox Exec",
  result_render: "Result Render",
};

const STAGE_ICONS: Record<string, string> = {
  file_parse: "📄",
  metadata_extract: "📊",
  code_generation: "🤖",
  security_check: "🛡️",
  sandbox_execution: "⚙️",
  result_render: "📈",
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */
function firstArtifactPath(payload: Record<string, unknown> | null): string | null {
  if (!payload) return null;
  if (typeof payload.file_path === "string" && payload.file_path) return payload.file_path;
  const chartInfo = payload.chart_info;
  if (chartInfo && typeof chartInfo === "object" && typeof (chartInfo as Record<string, unknown>).output_file === "string") {
    return (chartInfo as Record<string, string>).output_file;
  }
  const visualizations = payload.visualizations;
  if (Array.isArray(visualizations)) {
    for (const item of visualizations) {
      if (item && typeof item === "object") {
        const row = item as Record<string, unknown>;
        if (typeof row.path === "string" && row.path) return row.path;
        if (typeof row.filename === "string" && row.filename) return row.filename;
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

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */
export default function DataAnalysisPage() {
  const { config } = useAppConfig();

  // Step 1: Upload & Preview
  const [file, setFile] = useState<File | null>(null);
  const [uploadedPath, setUploadedPath] = useState("tips.csv");
  const [previewColumns, setPreviewColumns] = useState<PreviewColumn[]>([]);
  const [, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [previewMeta, setPreviewMeta] = useState<Record<string, unknown> | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Step 2: Ask & Analyze
  const [instruction, setInstruction] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [prevResult, setPrevResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stages, setStages] = useState<Record<string, StageEvent>>({});
  const [streaming, setStreaming] = useState(false);
  const [pipelineCollapsed, setPipelineCollapsed] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const gotResultRef = useRef(false);

  // Load preview for default dataset on mount
  useEffect(() => {
    loadPreview("tips.csv");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => { eventSourceRef.current?.close(); };
  }, []);

  /* ---- Step 1: Upload & Preview ---- */
  async function handleUpload() {
    if (!file) return;
    setPreviewLoading(true);
    setError(null);
    try {
      const payload = await uploadDataFile(config, file);
      const filePath =
        (typeof payload.file_path === "string" && payload.file_path) ||
        (typeof payload.file_id === "string" ? payload.file_id : "");
      setUploadedPath(filePath);
      await loadPreview(filePath);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setPreviewLoading(false);
    }
  }

  async function loadPreview(dataFile: string) {
    setPreviewLoading(true);
    try {
      const data = await previewDataFile(config, dataFile);
      setPreviewColumns((data.preview_columns as PreviewColumn[]) || []);
      setPreviewRows((data.sample_rows as Record<string, unknown>[]) || []);
      setPreviewMeta((data.metadata as Record<string, unknown>) || null);
    } catch {
      // Preview is non-critical — just show empty
      setPreviewColumns([]);
      setPreviewRows([]);
      setPreviewMeta(null);
    } finally {
      setPreviewLoading(false);
    }
  }

  function handleUseSample() {
    setFile(null);
    setUploadedPath("tips.csv");
    loadPreview("tips.csv");
  }

  /* ---- Step 2: Run Analysis (SSE streaming) ---- */
  const handleRunAnalysis = useCallback(async () => {
    if (!uploadedPath) {
      setError("Upload a data file first.");
      return;
    }
    if (!instruction.trim()) {
      setError("Enter an analysis question.");
      return;
    }

    // Preserve previous result
    if (result) setPrevResult(result);

    setLoading(true);
    setStreaming(true);
    setError(null);
    setResult(null);
    setStages({});
    setPipelineCollapsed(false);
    gotResultRef.current = false;
    eventSourceRef.current?.close();

    try {
      const { job_id } = await startDataAnalysisJob(config, {
        data_file: uploadedPath,
        instruction,
        generate_visualization: true,
      });

      const url = dataAnalysisStreamUrl(config, job_id);
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.addEventListener("stage", (ev) => {
        try {
          const data = JSON.parse(ev.data) as StageEvent;
          setStages((prev) => ({ ...prev, [data.stage]: data }));
        } catch { /* ignore */ }
      });

      es.addEventListener("result", (ev) => {
        try {
          const payload = JSON.parse(ev.data) as Record<string, unknown>;
          setResult(payload);
        } catch { /* ignore */ }
        gotResultRef.current = true;
        es.close();
        setLoading(false);
        setStreaming(false);
      });

      es.addEventListener("error", (ev) => {
        const me = ev as MessageEvent;
        if (me.data) {
          try {
            const d = JSON.parse(me.data);
            setError(d.error || "Analysis could not complete. Try a shorter question.");
          } catch {
            setError("Connection to analysis pipeline lost.");
          }
        }
        es.close();
        setLoading(false);
        setStreaming(false);
      });

      es.onerror = () => {
        if (es.readyState === EventSource.CLOSED) {
          if (!gotResultRef.current) {
            setError("Connection lost. Results may still be processing.");
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
  }, [config, uploadedPath, instruction, result]);

  /* ---- Derived state ---- */
  const codeGenMode = useMemo(() => {
    const cg = result?.code_generation;
    if (typeof cg === "object" && cg !== null) {
      return (cg as Record<string, unknown>).mode as string | undefined;
    }
    return undefined;
  }, [result]);

  const analysisSummary = useMemo<AnalysisSummary | null>(() => {
    if (!result?.analysis_summary) return null;
    return result.analysis_summary as AnalysisSummary;
  }, [result]);

  const visualizationAsset = useMemo(() => {
    const raw = firstArtifactPath(result);
    if (!raw) return null;
    const filename = basename(raw);
    const extension = filename.split(".").pop()?.toLowerCase() ?? "";
    return {
      filename,
      url: `/api/backend/api/v1/files/visualizations/${encodeURIComponent(filename)}`,
      isImage: ["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(extension),
    };
  }, [result]);

  const pipelineComplete = stages.result_render?.status === "completed" ||
    stages.done?.status === "completed";

  const pipelineSummary = useMemo(() => {
    const completedCount = STAGE_ORDER.filter(s => stages[s]?.status === "completed").length;
    const totalMs = Object.values(stages).reduce((sum, ev) => sum + (ev.elapsed_ms || 0), 0);
    const modeLabel = codeGenMode === "llm" ? "LLM Generated" : codeGenMode === "template_fallback" ? "Template Fallback" : codeGenMode || "";
    return `${completedCount}/${STAGE_ORDER.length} stages · ${(totalMs / 1000).toFixed(1)}s${modeLabel ? ` · ${modeLabel}` : ""}`;
  }, [stages, codeGenMode]);

  /* ---- Render ---- */
  return (
    <section className="page-stack">
      {/* Dark Hero Header */}
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
              Upload a dataset, ask a question — AI analyzes and visualizes in one step
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-4 text-xs text-gray-500">
            <span>Cloud LLM</span>
            <span className="text-gray-600">·</span>
            <span>Docker Sandbox</span>
            <span className="text-gray-600">·</span>
            <span>AI Charts</span>
          </div>
        </div>
      </DarkHeroWrapper>

      <article className="panel-card">
        {/* ============ Step 1: Upload & Preview ============ */}
        <header>
          <h3>Step 1: Upload & Preview</h3>
        </header>

        <div className="form-grid two-col">
          <label className="field-group" style={{ gridColumn: "1 / -1" }} data-testid="file-upload-zone">
            Upload Data File (CSV / Excel)
            <div className="flex items-center gap-3">
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                }}
              />
              <button
                className="action-button"
                type="button"
                onClick={handleUpload}
                disabled={!file || previewLoading}
                data-testid="upload-btn"
              >
                {previewLoading ? "Uploading..." : "Upload"}
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={handleUseSample}
                data-testid="use-sample-btn"
              >
                Use Sample (tips.csv)
              </button>
            </div>
          </label>
        </div>

        {/* Data Preview */}
        {previewLoading && (
          <div className="mt-4 text-sm text-gray-500" data-testid="preview-skeleton">
            Loading preview...
          </div>
        )}

        {!previewLoading && previewColumns.length > 0 && (
          <div className="mt-4 rounded-lg border border-gray-200 overflow-hidden" data-testid="data-preview">
            <div className="bg-gray-50 px-4 py-2 flex items-center gap-3 text-sm text-gray-600">
              <span className="font-medium">{previewMeta ? `${previewMeta.columns} columns · ${previewMeta.rows} rows` : "Data Preview"}</span>
              {uploadedPath && (
                <span className="text-xs text-gray-400 font-mono">{basename(uploadedPath)}</span>
              )}
            </div>
            {/* Desktop: table */}
            <div className="hidden sm:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="text-left px-4 py-2 font-medium text-gray-700">Column</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-700">Type</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-700">Sample</th>
                  </tr>
                </thead>
                <tbody>
                  {previewColumns.map((col) => (
                    <tr key={col.name} className="border-b border-gray-100">
                      <td className="px-4 py-1.5 font-mono text-gray-900">{col.name}</td>
                      <td className="px-4 py-1.5 text-gray-500">{col.type}</td>
                      <td className="px-4 py-1.5 text-gray-600 truncate max-w-[200px]">{col.sample || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Mobile: card list */}
            <div className="sm:hidden divide-y divide-gray-100">
              {previewColumns.slice(0, 5).map((col) => (
                <div key={col.name} className="px-4 py-2">
                  <div className="font-mono text-sm text-gray-900">{col.name}</div>
                  <div className="text-xs text-gray-500">{col.type} · {col.sample || "—"}</div>
                </div>
              ))}
              {previewColumns.length > 5 && (
                <div className="px-4 py-2 text-xs text-gray-400">
                  + {previewColumns.length - 5} more columns
                </div>
              )}
            </div>
          </div>
        )}

        {/* ============ Step 2: Ask & Analyze ============ */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-base font-semibold text-gray-900 mb-3">Step 2: Ask & Analyze</h3>

          <label className="field-group" data-testid="instruction-input">
            Analysis Instruction
            <input
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="Ask anything about your data..."
              disabled={loading}
              className={loading ? "bg-gray-100" : ""}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleRunAnalysis();
                }
              }}
            />
          </label>

          <div className="action-row mt-3">
            <button
              className="action-button"
              type="button"
              onClick={handleRunAnalysis}
              disabled={loading || !uploadedPath}
              data-testid="run-analysis-btn"
              style={{
                backgroundColor: loading ? undefined : "#f59e0b",
                borderColor: loading ? undefined : "#f59e0b",
                color: loading ? undefined : "#1a1a2e",
              }}
            >
              {streaming ? "Analyzing..." : "Run Analysis"}
            </button>
          </div>
        </div>

        {/* 6-Node Pipeline Visualization */}
        {(streaming || Object.keys(stages).length > 0) && (
          <div
            className="mt-4 rounded-xl border border-gray-700 bg-[#1a1a2e] p-4"
            data-testid="analysis-pipeline-viz"
            role="status"
            aria-live="polite"
          >
            {pipelineComplete && pipelineCollapsed ? (
              /* Collapsed summary */
              <button
                className="w-full flex items-center gap-2 text-xs text-gray-400 hover:text-gray-300"
                onClick={() => setPipelineCollapsed(false)}
                data-testid="pipeline-summary"
              >
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
                <span className="font-mono">{pipelineSummary}</span>
                <span className="ml-auto text-gray-600">Click to expand</span>
              </button>
            ) : (
              <>
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">
                    Analysis Pipeline
                  </p>
                  {pipelineComplete && (
                    <button
                      className="text-xs text-gray-500 hover:text-gray-400"
                      onClick={() => setPipelineCollapsed(true)}
                    >
                      Collapse
                    </button>
                  )}
                </div>
                {/* Desktop: horizontal */}
                <div className="hidden sm:flex items-center gap-0">
                  {STAGE_ORDER.map((stageId, idx) => {
                    const ev = stages[stageId];
                    const status = ev?.status ?? "pending";
                    const dotColor =
                      status === "completed" ? "bg-emerald-400" :
                      status === "running" ? "bg-amber-400 animate-pulse" :
                      status === "failed" ? "bg-red-400" :
                      "bg-gray-600";
                    return (
                      <div key={stageId} className="flex items-center flex-1">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="text-base flex-shrink-0">{STAGE_ICONS[stageId]}</span>
                          <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${dotColor}`} />
                          <div className="min-w-0">
                            <p className="text-xs font-medium text-gray-300 truncate">
                              {STAGE_LABELS[stageId]}
                            </p>
                            {ev?.detail && (
                              <p className="text-[10px] text-gray-500 truncate">{ev.detail}</p>
                            )}
                          </div>
                        </div>
                        {idx < STAGE_ORDER.length - 1 && (
                          <div className="w-4 h-px bg-gray-700 flex-shrink-0 mx-1" />
                        )}
                      </div>
                    );
                  })}
                </div>
                {/* Mobile: vertical */}
                <div className="sm:hidden flex flex-col gap-2">
                  {STAGE_ORDER.map((stageId) => {
                    const ev = stages[stageId];
                    const status = ev?.status ?? "pending";
                    const dotColor =
                      status === "completed" ? "bg-emerald-400" :
                      status === "running" ? "bg-amber-400 animate-pulse" :
                      status === "failed" ? "bg-red-400" :
                      "bg-gray-600";
                    return (
                      <div key={stageId} className="flex items-center gap-2">
                        <span className="text-sm flex-shrink-0">{STAGE_ICONS[stageId]}</span>
                        <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${dotColor}`} />
                        <span className="text-xs text-gray-300">{STAGE_LABELS[stageId]}</span>
                        {ev?.detail && (
                          <span className="text-[10px] text-gray-500 truncate ml-auto">{ev.detail}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        )}

        {/* Error */}
        {error && <p className="error-text mt-3">{error}</p>}

        {/* ============ Results ============ */}
        {result && (
          <div className="result-stack mt-4" data-testid="analysis-results">
            {/* Status banner */}
            <div
              className={`status-banner ${
                result.success === false ? "error" : "success"
              }`}
            >
              {result.success === false ? "Analysis Error" : "Analysis Complete"}
              {analysisSummary?.chart_type && ` — ${analysisSummary.chart_type}`}
              {codeGenMode && ` (${codeGenMode === "llm" ? "LLM" : "Fallback"})`}
            </div>

            {/* Code generation mode badge */}
            {codeGenMode && (
              <div className="flex items-center gap-2 text-sm" data-testid="code-gen-mode-badge">
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                    codeGenMode === "llm"
                      ? "bg-emerald-900/20 text-emerald-400 border border-emerald-800"
                      : "bg-amber-900/20 text-amber-400 border border-amber-800"
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${codeGenMode === "llm" ? "bg-emerald-500" : "bg-amber-500"}`} />
                  {codeGenMode === "llm" ? "LLM Generated" : "Template Fallback"}
                </span>
                {(() => {
                  const cg = result.code_generation;
                  const reason = typeof cg === "object" && cg !== null ? (cg as Record<string, unknown>).fallback_reason : null;
                  return typeof reason === "string" && reason ? (
                    <span className="text-xs text-gray-500">{reason}</span>
                  ) : null;
                })()}
              </div>
            )}

            {/* Key Findings (from ANALYSIS_SUMMARY_JSON) */}
            {analysisSummary?.key_findings && analysisSummary.key_findings.length > 0 && (
              <div className="artifact-card">
                <p className="result-label">Key Findings</p>
                <ul className="mt-2 space-y-1">
                  {analysisSummary.key_findings.map((finding, i) => (
                    <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                      <span className="text-emerald-500 mt-0.5 flex-shrink-0">•</span>
                      {finding}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Fallback: raw answer text if no key findings */}
            {(!analysisSummary?.key_findings || analysisSummary.key_findings.length === 0) &&
              typeof result.answer === "string" && result.answer && (
              <div className="artifact-card">
                <p className="result-label">Summary</p>
                <p className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{result.answer as string}</p>
              </div>
            )}

            {/* Chart — PRIMARY visual, largest */}
            {visualizationAsset && visualizationAsset.isImage && (
              <div className="artifact-card" data-testid="analysis-chart">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  className="w-full rounded-lg border border-gray-200 shadow-sm"
                  src={visualizationAsset.url}
                  alt="Analysis chart"
                  style={{ maxWidth: "100%", aspectRatio: "10/6" }}
                />
              </div>
            )}

            {/* Chart generation failed but analysis OK */}
            {!visualizationAsset && result.success !== false && (
              <div className="artifact-card border-amber-200 bg-amber-50/50">
                <p className="text-sm text-amber-700">
                  Chart could not be generated, but analysis results are ready above.
                </p>
              </div>
            )}

            {/* Generated code (collapsed) */}
            {(() => {
              const code = String(result.code ?? result.generated_code_preview ?? "");
              return code ? <CollapsibleCode title="Generated Code (Python)" code={code} language="python" /> : null;
            })()}

            {/* Raw output (collapsed) */}
            {(() => {
              const output = String(result.stdout ?? result.output ?? result.raw_output ?? "");
              return output ? <CollapsibleCode title="Raw Output" code={output} language="text" /> : null;
            })()}

            {/* Full response JSON (collapsed) */}
            <CollapsibleCode
              title="Full Response (JSON)"
              code={JSON.stringify(result, null, 2)}
              language="json"
            />
          </div>
        )}

        {/* Previous Analysis (collapsed) */}
        {prevResult && result && (
          <details className="mt-4" data-testid="previous-analysis">
            <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
              Previous Analysis
            </summary>
            <div className="mt-2 rounded-lg border border-gray-200 p-3 bg-gray-50">
              <CollapsibleCode
                title="Previous Result (JSON)"
                code={JSON.stringify(prevResult, null, 2)}
                language="json"
              />
            </div>
          </details>
        )}
      </article>
    </section>
  );
}
