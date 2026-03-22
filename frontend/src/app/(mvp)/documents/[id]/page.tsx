"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import DarkHeroWrapper from "@/components/DarkHeroWrapper";
import { realApiService } from "@/lib/real-api-client";
import type {
  DocumentDetailResponse,
  DocumentSummaryResponse,
  DocumentChunksResponse,
} from "@/lib/real-api-client";

// react-pdf must be loaded client-side only (PDF.js worker)
const Document = dynamic(
  () => import("react-pdf").then((mod) => mod.Document),
  { ssr: false }
);
const Page = dynamic(
  () => import("react-pdf").then((mod) => mod.Page),
  { ssr: false }
);

// Configure PDF.js worker — bundled locally to avoid CDN dependency during demo
import { pdfjs } from "react-pdf";
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

// Import react-pdf styles
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// ── Helpers ──────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileExtension(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  return ext;
}

type PreviewType = "pdf" | "image" | "text" | "data" | "doc";

function getPreviewType(mimeType: string | null, filename: string): PreviewType {
  const ext = getFileExtension(filename);
  if (mimeType?.startsWith("application/pdf") || ext === "pdf") return "pdf";
  if (
    mimeType?.startsWith("image/") ||
    ["png", "jpg", "jpeg", "bmp", "gif", "webp"].includes(ext)
  )
    return "image";
  if (["txt", "md", "json"].includes(ext)) return "text";
  if (["csv", "xlsx", "xls"].includes(ext)) return "data";
  return "doc"; // .doc, .docx, .ppt, .pptx — show extracted text
}

// ── SVG Icons ────────────────────────────────────────────────────────

function ChevronLeftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 12L6 8L10 4" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M8 2v8M4 8l4 4 4-4M2 14h12" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="6" cy="6" r="4.5" />
      <path d="M9.5 9.5L13 13" />
    </svg>
  );
}

// ── Main Page Component ──────────────────────────────────────────────

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const docId = params?.id as string;

  const [detail, setDetail] = useState<DocumentDetailResponse | null>(null);
  const [summary, setSummary] = useState<DocumentSummaryResponse | null>(null);
  const [chunks, setChunks] = useState<DocumentChunksResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);

  // PDF state
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);

  // Chunk search
  const [chunkSearch, setChunkSearch] = useState("");

  // Fetch all data — clear stale state on docId change, abort on unmount/navigation
  useEffect(() => {
    if (!docId) return;

    let cancelled = false;

    // Clear previous document's data to prevent stale display
    setDetail(null);
    setSummary(null);
    setChunks(null);
    setChunkSearch("");
    setImageError(false);
    setPageNumber(1);
    setNumPages(0);

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [detailRes, summaryRes, chunksRes] = await Promise.allSettled([
          realApiService.getDocumentDetail(docId),
          realApiService.getDocumentSummary(docId),
          realApiService.getDocumentChunks(docId, 0, 50),
        ]);

        if (cancelled) return;

        if (detailRes.status === "fulfilled") {
          setDetail(detailRes.value);
        } else {
          setError("Document not found");
          return;
        }

        if (summaryRes.status === "fulfilled") {
          setSummary(summaryRes.value);
        }
        if (chunksRes.status === "fulfilled") {
          setChunks(chunksRes.value);
        }
      } catch {
        if (!cancelled) setError("Failed to load document");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchData();
    return () => { cancelled = true; };
  }, [docId]);

  // Filtered chunks
  const filteredChunks = useMemo(() => {
    if (!chunks?.chunks) return [];
    if (!chunkSearch.trim()) return chunks.chunks;
    const q = chunkSearch.toLowerCase();
    return chunks.chunks.filter((c) => c.content.toLowerCase().includes(q));
  }, [chunks, chunkSearch]);

  // Highlight match in chunk text
  const highlightText = useCallback(
    (text: string) => {
      if (!chunkSearch.trim()) return text;
      const regex = new RegExp(
        `(${chunkSearch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
        "gi"
      );
      const parts = text.split(regex);
      const q = chunkSearch.trim().toLowerCase();
      return parts.map((part, i) =>
        part.toLowerCase() === q ? (
          <mark key={i} className="bg-amber-100 text-amber-900 rounded px-0.5">
            {part}
          </mark>
        ) : (
          part
        )
      );
    },
    [chunkSearch]
  );

  const previewType = detail
    ? getPreviewType(detail.mime_type, detail.filename)
    : "doc";

  const contentUrl = detail
    ? realApiService.getDocumentContentUrl(docId)
    : "";

  // ── Loading state ──
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <DarkHeroWrapper className="mb-6" data-testid="doc-detail-hero">
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-gray-600/30 rounded w-48" />
              <div className="h-7 bg-gray-600/30 rounded w-96" />
              <div className="flex gap-6">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-4 bg-gray-600/30 rounded w-20" />
                ))}
              </div>
            </div>
          </DarkHeroWrapper>
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
            <div className="bg-white rounded-xl border border-gray-200 h-[500px] animate-pulse" />
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl border border-gray-200 h-40 animate-pulse"
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Error state ──
  if (error || !detail) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-gray-500 text-lg">{error || "Document not found"}</p>
          <button
            onClick={() => router.push("/documents-integrated")}
            className="text-blue-600 hover:underline"
          >
            Back to Documents
          </button>
        </div>
      </div>
    );
  }

  const ext = getFileExtension(detail.filename).toUpperCase() || "FILE";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Dark Hero Header ── */}
      <div className="px-4 sm:px-8 pt-6">
        <DarkHeroWrapper data-testid="doc-detail-hero">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => router.push("/documents-integrated")}
              className="text-gray-500 hover:text-gray-200 text-sm flex items-center gap-1 transition-colors"
              data-testid="doc-back-btn"
            >
              <ChevronLeftIcon />
              Documents
            </button>
            <span className="text-gray-600 text-sm">›</span>
            <span className="text-gray-200 text-sm truncate max-w-[300px]">
              {detail.filename}
            </span>
          </div>

          {/* Title */}
          <h1
            className="text-gray-200 text-xl sm:text-2xl font-bold tracking-tight mb-3"
            data-testid="doc-title"
          >
            {detail.filename}
          </h1>

          {/* Meta row */}
          <div className="flex flex-wrap gap-4 sm:gap-6">
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500 text-xs uppercase tracking-wider font-semibold">
                Status
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  detail.status === "processed"
                    ? "bg-emerald-900/40 text-emerald-400"
                    : detail.status === "processing"
                    ? "bg-amber-900/40 text-amber-400"
                    : "bg-red-900/40 text-red-400"
                }`}
              >
                {detail.status === "processed"
                  ? "Processed"
                  : detail.status === "processing"
                  ? "Processing"
                  : "Error"}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500 text-xs uppercase tracking-wider font-semibold">
                Type
              </span>
              <span className="bg-slate-800 text-blue-400 border border-slate-700 px-2.5 py-0.5 rounded-full text-xs font-medium">
                {ext}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500 text-xs uppercase tracking-wider font-semibold">
                Size
              </span>
              <span className="text-gray-200 text-sm">
                {formatFileSize(detail.size)}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500 text-xs uppercase tracking-wider font-semibold">
                Chunks
              </span>
              <span className="text-gray-200 text-sm font-mono">
                {detail.chunk_count}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500 text-xs uppercase tracking-wider font-semibold">
                Uploaded
              </span>
              <span className="text-gray-200 text-sm">
                {detail.uploaded_at
                  ? new Date(detail.uploaded_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })
                  : "—"}
              </span>
            </div>
          </div>
        </DarkHeroWrapper>
      </div>

      {/* ── Main Content ── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
          {/* ── Left: Document Preview ── */}
          <div
            className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
            data-testid="doc-preview-panel"
          >
            {/* Toolbar */}
            {previewType === "pdf" && (
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
                    disabled={pageNumber <= 1}
                    className="px-3 py-1.5 text-sm border border-gray-200 rounded-md bg-white hover:bg-gray-50 disabled:opacity-40 transition-colors"
                    data-testid="pdf-prev-btn"
                  >
                    ‹ Prev
                  </button>
                  <button
                    onClick={() =>
                      setPageNumber((p) => Math.min(numPages, p + 1))
                    }
                    disabled={pageNumber >= numPages}
                    className="px-3 py-1.5 text-sm border border-gray-200 rounded-md bg-white hover:bg-gray-50 disabled:opacity-40 transition-colors"
                    data-testid="pdf-next-btn"
                  >
                    Next ›
                  </button>
                  <span
                    className="text-sm text-gray-500 font-mono"
                    data-testid="pdf-page-info"
                  >
                    Page {pageNumber} of {numPages}
                  </span>
                </div>
                <a
                  href={contentUrl}
                  download
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-gray-200 rounded-md bg-white hover:bg-gray-50 transition-colors"
                  data-testid="doc-download-toolbar-btn"
                >
                  <DownloadIcon />
                  Download
                </a>
              </div>
            )}

            {/* Preview body */}
            <div className="p-4 sm:p-8 min-h-[400px] bg-gray-100 flex items-start justify-center">
              {!detail.file_exists ? (
                <div
                  className="text-center py-20 text-gray-500"
                  data-testid="doc-file-unavailable"
                >
                  <p className="text-lg font-medium mb-2">
                    Original file unavailable
                  </p>
                  <p className="text-sm">
                    AI summary and chunks are still accessible.
                  </p>
                </div>
              ) : previewType === "pdf" ? (
                <div className="w-full flex justify-center">
                  <Document
                    file={contentUrl}
                    onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                    loading={
                      <div className="h-[500px] w-full max-w-[600px] bg-white rounded shadow animate-pulse" />
                    }
                    error={
                      <div className="text-center py-20 text-gray-500">
                        <p>Unable to render PDF</p>
                        <a
                          href={contentUrl}
                          download
                          className="text-blue-600 hover:underline text-sm mt-2 inline-block"
                        >
                          Download instead
                        </a>
                      </div>
                    }
                  >
                    <Page
                      pageNumber={pageNumber}
                      renderTextLayer={true}
                      renderAnnotationLayer={true}
                      width={580}
                    />
                  </Document>
                </div>
              ) : previewType === "image" && !imageError ? (
                <img
                  src={contentUrl}
                  alt={detail.filename}
                  className="max-w-full max-h-[600px] object-contain rounded shadow"
                  data-testid="doc-image-preview"
                  onError={() => setImageError(true)}
                />
              ) : previewType === "image" && imageError ? (
                <p className="text-gray-500 text-center py-20">
                  Image format not supported by browser
                </p>
              ) : (
                <div
                  className="w-full bg-white rounded-lg shadow p-6 font-mono text-sm text-gray-700 whitespace-pre-wrap max-h-[600px] overflow-y-auto"
                  data-testid="doc-text-preview"
                >
                  {detail.ai_summary ? (
                    <p className="text-gray-500 italic mb-4">
                      Showing extracted text content:
                    </p>
                  ) : null}
                  {chunks?.chunks
                    ?.slice(0, 10)
                    .map((c) => c.content)
                    .join("\n\n") ||
                    "No text content available for preview."}
                </div>
              )}
            </div>
          </div>

          {/* ── Right: AI Intelligence Panel ── */}
          <div className="space-y-4" data-testid="doc-ai-panel">
            {/* AI Summary Card */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 bg-blue-600 rounded flex items-center justify-center text-white text-[10px] font-bold">
                    AI
                  </div>
                  <span className="text-sm font-semibold text-gray-900">
                    Document Summary
                  </span>
                </div>
                {summary?.status === "ready" && (
                  <span className="bg-gray-100 text-gray-500 text-[11px] font-medium px-2 py-0.5 rounded-full">
                    Auto-generated
                  </span>
                )}
              </div>
              <div className="p-4" data-testid="doc-summary-content">
                {summary?.status === "ready" && summary.summary ? (
                  <>
                    <p className="text-sm text-gray-600 leading-relaxed mb-3">
                      {summary.summary}
                    </p>
                    {Array.isArray(summary.outline) &&
                      summary.outline.length > 0 && (
                        <div className="space-y-2">
                          {(
                            summary.outline as Array<{
                              title?: string;
                              detail?: string;
                            }>
                          ).map((item, i) => (
                            <div key={i} className="flex gap-2.5">
                              <div className="w-1.5 h-1.5 bg-blue-600 rounded-full mt-2 flex-shrink-0" />
                              <p className="text-[13px] text-gray-600">
                                {item.title && (
                                  <strong className="text-gray-900 font-semibold">
                                    {item.title}:{" "}
                                  </strong>
                                )}
                                {item.detail || String(item)}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                  </>
                ) : (
                  <div className="py-6 text-center">
                    <div className="animate-pulse space-y-2 max-w-[250px] mx-auto">
                      <div className="h-3 bg-gray-200 rounded w-full" />
                      <div className="h-3 bg-gray-200 rounded w-3/4" />
                      <div className="h-3 bg-gray-200 rounded w-1/2" />
                    </div>
                    <p className="text-sm text-gray-400 mt-3">
                      {summary?.message || "AI is reading this document..."}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Document Details Card */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200">
                <span className="text-sm font-semibold text-gray-900">
                  Document Details
                </span>
              </div>
              <div className="p-4" data-testid="doc-details-content">
                {[
                  { label: "Filename", value: detail.filename },
                  { label: "Type", value: ext },
                  {
                    label: "Size",
                    value: formatFileSize(detail.size),
                  },
                  {
                    label: "Status",
                    value: detail.status,
                  },
                  {
                    label: "Vectorized Chunks",
                    value: String(detail.chunk_count),
                    mono: true,
                  },
                  {
                    label: "Embedding Model",
                    value: "nomic-v1.5",
                    mono: true,
                  },
                ].map((row, i) => (
                  <div
                    key={i}
                    className="flex justify-between items-center py-2 border-b border-gray-50 last:border-0"
                  >
                    <span className="text-[13px] text-gray-500">
                      {row.label}
                    </span>
                    <span
                      className={`text-[13px] text-gray-900 font-medium ${
                        row.mono ? "font-mono text-xs" : ""
                      }`}
                    >
                      {row.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Vectorized Chunks Card */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                <span className="text-sm font-semibold text-gray-900">
                  Vectorized Chunks
                </span>
                <span className="text-xs text-gray-500">
                  {chunks?.total ?? 0} chunks
                </span>
              </div>
              <div className="p-4" data-testid="doc-chunks-content">
                {/* Search */}
                <div className="relative mb-3">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                    <SearchIcon />
                  </div>
                  <input
                    type="text"
                    value={chunkSearch}
                    onChange={(e) => setChunkSearch(e.target.value)}
                    placeholder="Search within document..."
                    className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 outline-none transition-colors"
                    data-testid="chunk-search-input"
                  />
                </div>

                {/* Chunk list */}
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {filteredChunks.length > 0 ? (
                    filteredChunks.slice(0, 10).map((chunk) => (
                      <div
                        key={chunk.chunk_id}
                        className="p-2.5 bg-gray-50 rounded-lg border-l-[3px] border-blue-600"
                        data-testid={`chunk-${chunk.chunk_id}`}
                      >
                        <p className="text-xs text-gray-600 leading-relaxed line-clamp-3">
                          {highlightText(chunk.content)}
                        </p>
                        <p className="text-[11px] text-gray-400 font-mono mt-1">
                          Chunk #{chunk.chunk_id} · {chunk.char_count} chars
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-400 text-center py-4">
                      {chunkSearch
                        ? `No matches for "${chunkSearch}"`
                        : "No chunks available"}
                    </p>
                  )}
                </div>
                {chunkSearch && filteredChunks.length > 0 && (
                  <p className="text-xs text-gray-400 text-center mt-2">
                    {filteredChunks.length} of {chunks?.total ?? 0} chunks match
                  </p>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <button
              onClick={() => {
                const query = `Tell me about the document "${detail.filename}"`;
                router.push(
                  `/workflow-chat?q=${encodeURIComponent(query)}`
                );
              }}
              className="w-full flex items-center justify-center gap-2 py-3 bg-amber-500 hover:bg-amber-600 text-white font-medium rounded-xl transition-colors"
              data-testid="doc-ask-ai-btn"
            >
              Ask AI About This Document
            </button>

            {detail.file_exists && (
              <a
                href={contentUrl}
                download
                className="w-full flex items-center justify-center gap-2 py-3 bg-white hover:bg-gray-50 text-gray-700 font-medium rounded-xl border border-gray-200 transition-colors"
                data-testid="doc-download-btn"
              >
                <DownloadIcon />
                Download Original File
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
