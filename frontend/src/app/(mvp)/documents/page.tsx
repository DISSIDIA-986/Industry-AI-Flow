"use client";

import { useMemo, useState } from "react";

import { useAppConfig } from "@/components/app-config-context";
import {
  getDocumentOperationLog,
  getDocumentStats,
  uploadDocument,
} from "@/lib/api-client";
import { normalizeError } from "@/lib/formatters";

export default function DocumentsPage() {
  const { config } = useAppConfig();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<Record<string, unknown> | null>(null);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [operations, setOperations] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const statsSummary = useMemo(() => {
    if (!stats) {
      return [];
    }
    const keys = ["total_documents", "active_documents", "total_chunks"];
    return keys
      .filter((key) => typeof stats[key] === "number")
      .map((key) => [key, Number(stats[key])] as const);
  }, [stats]);

  const operationRows = useMemo(() => {
    if (!operations || !Array.isArray(operations.logs)) {
      return [];
    }
    return operations.logs
      .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
      .slice(0, 5);
  }, [operations]);

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = await uploadDocument(config, selectedFile);
      setUploadResult(payload);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadStatsAndLog() {
    setLoading(true);
    setError(null);
    try {
      const [statsPayload, operationsPayload] = await Promise.all([
        getDocumentStats(config),
        getDocumentOperationLog(config),
      ]);
      setStats(statsPayload);
      setOperations(operationsPayload);
    } catch (err) {
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-stack">
      <article className="hero-card">
        <p className="eyebrow">L4 Document Layer</p>
        <h2>Document ingestion and version operations</h2>
        <p>Use this floor to keep RAG source documents healthy and traceable.</p>
      </article>

      <article className="panel-card">
        <header>
          <h3>Upload Document</h3>
        </header>

        <div className="inline-row">
          <input
            type="file"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
          <button className="action-button" type="button" onClick={handleUpload}>
            {loading ? "Uploading..." : "Upload"}
          </button>
          <button className="secondary-button" type="button" onClick={loadStatsAndLog}>
            Refresh Stats + Operation Log
          </button>
        </div>

        {error ? <p className="error-text">{error}</p> : null}

        <div className="result-grid">
          <div>
            <p className="result-label">Upload Result</p>
            {uploadResult ? (
              <div className="kv-grid">
                {Object.entries(uploadResult)
                  .filter(([key, value]) =>
                    ["filename", "sanitized_filename", "size", "status"].includes(key) &&
                    ["string", "number"].includes(typeof value),
                  )
                  .map(([key, value]) => (
                    <div key={key} className="kv-item">
                      <span>{key}</span>
                      <strong>{String(value)}</strong>
                    </div>
                  ))}
              </div>
            ) : null}
            <pre>{uploadResult ? JSON.stringify(uploadResult, null, 2) : "No upload yet"}</pre>
          </div>
          <div>
            <p className="result-label">Document Statistics</p>
            {statsSummary.length ? (
              <div className="kv-grid">
                {statsSummary.map(([key, value]) => (
                  <div key={key} className="kv-item">
                    <span>{key}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
            ) : null}
            <pre>{stats ? JSON.stringify(stats, null, 2) : "No stats loaded"}</pre>
          </div>
          <div>
            <p className="result-label">Operations Log</p>
            {operationRows.length ? (
              <div className="log-list">
                {operationRows.map((row, index) => (
                  <div key={`${String(row.id ?? index)}`} className="log-item">
                    <strong>{String(row.operation ?? "operation")}</strong>
                    <span>
                      {String(row.status ?? "unknown")} · {String(row.filename ?? "-")}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
            <pre>{operations ? JSON.stringify(operations, null, 2) : "No log loaded"}</pre>
          </div>
        </div>
      </article>
    </section>
  );
}
