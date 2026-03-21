/** Shared intent display configuration — single source of truth for colors and labels. */

export const INTENT_STYLE: Record<
  string,
  { label: string; dot: string; bg: string; text: string; barColor: string }
> = {
  knowledge_retrieval: {
    label: 'Knowledge Retrieval',
    dot: 'bg-blue-500',
    bg: 'bg-blue-50 border-blue-200',
    text: 'text-blue-700',
    barColor: 'bg-blue-500',
  },
  cost_estimation: {
    label: 'Cost Estimation',
    dot: 'bg-green-500',
    bg: 'bg-green-50 border-green-200',
    text: 'text-green-700',
    barColor: 'bg-green-500',
  },
  data_analysis: {
    label: 'Data Analysis',
    dot: 'bg-purple-500',
    bg: 'bg-purple-50 border-purple-200',
    text: 'text-purple-700',
    barColor: 'bg-purple-500',
  },
  document_processing: {
    label: 'Document Processing',
    dot: 'bg-orange-500',
    bg: 'bg-orange-50 border-orange-200',
    text: 'text-orange-700',
    barColor: 'bg-orange-500',
  },
  code_execution: {
    label: 'Code Execution',
    dot: 'bg-red-500',
    bg: 'bg-red-50 border-red-200',
    text: 'text-red-700',
    barColor: 'bg-red-500',
  },
  unclear_intent: {
    label: 'Unclear',
    dot: 'bg-gray-400',
    bg: 'bg-gray-50 border-gray-200',
    text: 'text-gray-600',
    barColor: 'bg-gray-400',
  },
}

/** 11-node intent workflow definition for IntentFlowViz */
export const INTENT_WORKFLOW_NODES = [
  { id: 'input_preprocessing', label: 'Input\nPreprocess', isDecision: false },
  { id: 'context_enrichment', label: 'Context\nEnrichment', isDecision: false },
  { id: 'intent_classification', label: 'Intent\nClassification', isDecision: false },
  { id: 'confidence_evaluation', label: 'Confidence\nEvaluation', isDecision: true },
  { id: 'routing_decision', label: 'Routing\nDecision', isDecision: false },
  { id: 'prompt_preparation', label: 'Prompt\nPreparation', isDecision: false },
  { id: 'clarification_step', label: 'Clarification\nCheck', isDecision: true },
  { id: 'agent_dispatch', label: 'Agent\nDispatch', isDecision: false },
  { id: 'response_processing', label: 'Response\nProcessing', isDecision: false },
] as const

/** SVG icon paths for intent workflow nodes (heroicons outline, 24x24 viewBox) */
export const INTENT_NODE_ICONS: Record<string, string> = {
  input_preprocessing:
    'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z',
  context_enrichment:
    'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
  intent_classification:
    'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  confidence_evaluation:
    'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  routing_decision:
    'M13 17h8m0 0V9m0 8l-8-8-4 4-6-6',
  prompt_preparation:
    'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z',
  clarification_step:
    'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  agent_dispatch:
    'M13 10V3L4 14h7v7l9-11h-7z',
  response_processing:
    'M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z',
}
