"use client";

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

interface CollapsibleCodeProps {
  title: string;
  code: string;
  language: string;
  defaultOpen?: boolean;
  maxHeight?: number;
}

export default function CollapsibleCode({
  title,
  code,
  language,
  defaultOpen = false,
  maxHeight = 400,
}: CollapsibleCodeProps) {
  return (
    <details className="collapsible-section" open={defaultOpen || undefined}>
      <summary>{title}</summary>
      <div className="code-scroll" style={{ maxHeight }}>
        <SyntaxHighlighter
          language={language}
          style={oneLight}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            background: "transparent",
            fontSize: "0.79rem",
          }}
          wrapLongLines
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </details>
  );
}
