import { type ReactNode } from "react";

/**
 * Shared dark hero container — the #1a1a2e section used across all demo pages.
 * Only handles background, padding, border radius, and gradient overlay.
 * Content is passed via children.
 */
export default function DarkHeroWrapper({
  children,
  className = "",
  "data-testid": testId,
}: {
  children: ReactNode;
  className?: string;
  "data-testid"?: string;
}) {
  return (
    <div
      className={`bg-[#1a1a2e] rounded-2xl px-6 py-4 relative overflow-hidden ${className}`}
      data-testid={testId}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/5 to-transparent pointer-events-none" />
      <div className="relative">{children}</div>
    </div>
  );
}
