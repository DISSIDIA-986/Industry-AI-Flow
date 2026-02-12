"use client";

import { useState } from "react";

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
            <pre>{uploadResult ? JSON.stringify(uploadResult, null, 2) : "No upload yet"}</pre>
          </div>
          <div>
            <p className="result-label">Document Statistics</p>
            <pre>{stats ? JSON.stringify(stats, null, 2) : "No stats loaded"}</pre>
          </div>
          <div>
            <p className="result-label">Operations Log</p>
            <pre>{operations ? JSON.stringify(operations, null, 2) : "No log loaded"}</pre>
          </div>
        </div>
      </article>
    </section>
  );
}
