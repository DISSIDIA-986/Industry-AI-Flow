"use client";

import {
  MouseEvent as ReactMouseEvent,
  KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";

export interface LightboxChart {
  url: string;
  type: string;
  summary?: string | null;
}

interface ChartLightboxProps {
  charts: LightboxChart[];
  open: boolean;
  startIndex: number;
  onClose: () => void;
}

/**
 * Fullscreen chart viewer built on the native <dialog> element so focus trap,
 * ESC dismiss, top-layer stacking, and inert background all come for free.
 * Demo-critical: presenters click a chart, the image fills ~95vw/95vh on the
 * projector, ←/→ navigate the EDA grid, ESC or backdrop click closes.
 */
export default function ChartLightbox({
  charts,
  open,
  startIndex,
  onClose,
}: ChartLightboxProps) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const [index, setIndex] = useState(startIndex);
  const [imgLoaded, setImgLoaded] = useState(false);

  // Reset index to startIndex on each open transition (derive from props during
  // render, per React docs — avoids setState-in-effect cascading renders).
  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (open) setIndex(startIndex);
  }

  // Reset image-loaded flag whenever the displayed chart changes.
  const [lastIndex, setLastIndex] = useState(index);
  if (index !== lastIndex) {
    setLastIndex(index);
    setImgLoaded(false);
  }

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (open && !dlg.open) {
      try {
        dlg.showModal();
      } catch {
        // showModal throws if called twice; safe to ignore
      }
    } else if (!open && dlg.open) {
      dlg.close();
    }
  }, [open]);

  const total = charts.length;
  const current = charts[index];

  const goPrev = () => setIndex((i) => (i > 0 ? i - 1 : i));
  const goNext = () => setIndex((i) => (i < total - 1 ? i + 1 : i));

  const handleKeyDown = (e: ReactKeyboardEvent<HTMLDialogElement>) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      goPrev();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      goNext();
    }
  };

  const handleBackdropClick = (e: ReactMouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) onClose();
  };

  if (!current) return null;

  const canPrev = index > 0;
  const canNext = index < total - 1;
  const counter = total > 1 ? `Chart ${index + 1} of ${total}` : current.type;

  return (
    <dialog
      ref={dialogRef}
      data-testid="chart-lightbox"
      aria-label={`Chart viewer — ${current.type}`}
      onClose={onClose}
      onCancel={onClose}
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
      className="m-0 p-0 bg-transparent outline-none max-w-none max-h-none w-screen h-screen backdrop:bg-black/80"
    >
      <div className="flex flex-col w-full h-full p-4 md:p-6 box-border">
        {/* Top bar: counter + close */}
        <div className="flex items-center justify-between text-white mb-3 flex-shrink-0">
          <div
            className="text-sm md:text-base font-medium tracking-wide"
            aria-live="polite"
            data-testid="chart-lightbox-counter"
          >
            {counter}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close chart viewer"
            data-testid="chart-lightbox-close"
            className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white transition"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Image stage */}
        <div className="relative flex-1 flex items-center justify-center min-h-0">
          {!imgLoaded && (
            <div
              className="absolute inset-0 flex items-center justify-center text-white/60 text-sm"
              data-testid="chart-lightbox-loading"
            >
              Loading chart...
            </div>
          )}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            key={current.url}
            src={current.url}
            alt={`${current.type} chart, enlarged view`}
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgLoaded(true)}
            className="max-w-full max-h-full object-contain rounded-md shadow-2xl"
            data-testid="chart-lightbox-image"
          />

          {total > 1 && (
            <>
              <button
                type="button"
                onClick={goPrev}
                disabled={!canPrev}
                aria-label="Previous chart"
                data-testid="chart-lightbox-prev"
                className="absolute left-2 md:left-4 top-1/2 -translate-y-1/2 inline-flex items-center justify-center w-12 h-12 rounded-full bg-white/10 hover:bg-white/25 text-white transition disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                type="button"
                onClick={goNext}
                disabled={!canNext}
                aria-label="Next chart"
                data-testid="chart-lightbox-next"
                className="absolute right-2 md:right-4 top-1/2 -translate-y-1/2 inline-flex items-center justify-center w-12 h-12 rounded-full bg-white/10 hover:bg-white/25 text-white transition disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </>
          )}
        </div>

        {/* Caption */}
        {current.summary && (
          <p className="mt-3 text-sm text-white/80 text-center flex-shrink-0 max-w-3xl mx-auto">
            {current.summary}
          </p>
        )}
      </div>
    </dialog>
  );
}
