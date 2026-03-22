"use client";

import { useState } from "react";
import {
  GOLDEN_QUESTIONS,
  TOTAL_DOCUMENTS,
  TOTAL_QUESTIONS,
  type DocumentCategory,
} from "@/lib/golden-questions";

interface GoldenQuestionsProps {
  onSelect: (questionText: string) => void;
  disabled?: boolean;
}

export default function GoldenQuestions({
  onSelect,
  disabled,
}: GoldenQuestionsProps) {
  const [expandedId, setExpandedId] = useState<string | null>(
    GOLDEN_QUESTIONS[0]?.id ?? null,
  );

  const toggle = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div data-testid="golden-questions">
      {/* Badge */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-gray-900 text-sm">Golden Questions</h3>
        <span
          className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 font-medium"
          data-testid="gq-badge"
        >
          {TOTAL_DOCUMENTS} Docs · {TOTAL_QUESTIONS} Qs
        </span>
      </div>

      {/* Accordion */}
      <div className="space-y-1" data-testid="gq-accordion">
        {GOLDEN_QUESTIONS.map((category) => (
          <CategoryAccordion
            key={category.id}
            category={category}
            expanded={expandedId === category.id}
            onToggle={() => toggle(category.id)}
            onSelect={onSelect}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  );
}

function CategoryAccordion({
  category,
  expanded,
  onToggle,
  onSelect,
  disabled,
}: {
  category: DocumentCategory;
  expanded: boolean;
  onToggle: () => void;
  onSelect: (text: string) => void;
  disabled?: boolean;
}) {
  return (
    <div data-testid={`gq-category-${category.id}`}>
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-gray-50 transition text-left"
        data-testid={`gq-toggle-${category.id}`}
      >
        {/* Color dot */}
        <span
          className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${category.dotColor}`}
        />
        {/* Label */}
        <span className="text-xs font-medium text-gray-700 flex-1 truncate">
          {category.shortLabel}
        </span>
        {/* Count */}
        <span className="text-[10px] text-gray-400">
          {category.questions.length}
        </span>
        {/* Chevron */}
        <svg
          className={`w-3 h-3 text-gray-400 transition-transform duration-150 ${
            expanded ? "rotate-90" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 5l7 7-7 7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="ml-4 mt-0.5 space-y-0.5">
          {category.questions.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => !disabled && onSelect(q.text)}
              disabled={disabled}
              className="w-full text-left px-2 py-1.5 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded transition disabled:opacity-50 disabled:cursor-not-allowed leading-relaxed"
              data-testid={`gq-question-${category.id}-${idx}`}
            >
              {q.text}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
