"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { workflowApi, realApiService } from "@/lib/api-client";
import {
  websocketService,
  type QueryResponseData,
} from "@/lib/websocket-service";
import { getStaticFollowUps } from "@/lib/golden-questions";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import GoldenQuestions from "@/components/GoldenQuestions";
import CompactPipelineViz from "@/components/CompactPipelineViz";

interface Message {
  id: string;
  content: string;
  sender: "user" | "ai";
  timestamp: Date;
  intent?: {
    type: string;
    confidence: number;
    description: string;
  };
  sources?: Array<{
    document_id: string;
    document_name: string;
    relevance: number;
    content: string;
  }>;
  suggestedQuestions?: string[];
  metadata?: Record<string, unknown>;
}

function createWorkflowSessionId(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return `wf-${crypto.randomUUID()}`;
  }
  return `wf-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function extractSuggestedQuestions(metadata: unknown): string[] | undefined {
  if (!metadata || typeof metadata !== "object") {
    return undefined;
  }
  const payload = metadata as Record<string, unknown>;
  const agentExecution =
    payload.agent_execution && typeof payload.agent_execution === "object"
      ? (payload.agent_execution as Record<string, unknown>)
      : undefined;
  const raw =
    payload.suggested_questions ?? agentExecution?.suggested_questions;
  if (!Array.isArray(raw)) {
    return undefined;
  }
  const normalized = raw
    .map((item) => String(item || "").trim())
    .filter((item) => item.length > 0);
  return normalized.length > 0 ? normalized.slice(0, 8) : undefined;
}

function buildFallbackSuggestedQuestions(
  query: string,
  sourceName?: string,
): string[] {
  const normalizedQuery = query.trim().replace(/\s+/g, " ");
  const shortQuery =
    normalizedQuery.length > 72
      ? `${normalizedQuery.slice(0, 72)}...`
      : normalizedQuery;
  const sourceLabel =
    sourceName && sourceName.trim().length > 0
      ? sourceName.trim()
      : "the referenced documents";

  return [
    `Which section in ${sourceLabel} most directly supports this answer?`,
    `What assumptions should I validate next for "${shortQuery}"?`,
    `Can you provide a step-by-step checklist to execute this recommendation?`,
  ];
}

export default function WorkflowChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content:
        "Hello! I am the Industry AI Flow assistant. I can help you with construction regulations, cost estimates, risk analysis and data queries. Click a Golden Question to get started, or type your own.",
      sender: "ai",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState<
    "checking" | "connected" | "disconnected"
  >("checking");
  const [wsStatus, setWsStatus] = useState<
    "disconnected" | "connecting" | "connected"
  >("disconnected");
  const [useWebSocket, _setUseWebSocket] = useState(false);
  const [sessionId] = useState<string>(createWorkflowSessionId);
  const [mobileGQOpen, setMobileGQOpen] = useState(false);
  const pendingQueryRef = useRef<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();

  // Check API connection status
  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const health = await realApiService.checkHealth();
        setApiStatus(health.status === "ok" ? "connected" : "disconnected");
      } catch {
        setApiStatus("disconnected");
      }
    };
    checkApiHealth();
    const interval = setInterval(checkApiHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket connection management
  useEffect(() => {
    if (!useWebSocket) return;
    setWsStatus("connecting");

    const connectWebSocket = async () => {
      const connected = await websocketService.connect();
      setWsStatus(connected ? "connected" : "disconnected");
    };
    connectWebSocket();

    const unsubscribe = websocketService.onConnectionChange((connected) => {
      setWsStatus(connected ? "connected" : "disconnected");
    });

    const unsubscribeResponse = websocketService.onMessage(
      "query_response",
      (data: QueryResponseData) => {
        const suggestedQuestions =
          extractSuggestedQuestions(data.metadata) ??
          buildFallbackSuggestedQuestions(pendingQueryRef.current);
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.response,
          sender: "ai",
          timestamp: new Date(data.timestamp),
          suggestedQuestions,
          metadata: data.metadata,
        };
        setMessages((prev) => [...prev, aiMessage]);
        setLoading(false);
      },
    );

    const unsubscribeNotification = websocketService.onMessage(
      "notification",
      () => {},
    );

    return () => {
      unsubscribe();
      unsubscribeResponse();
      unsubscribeNotification();
      websocketService.disconnect();
    };
  }, [useWebSocket]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Use a ref to avoid React state-ordering bug: setLastClickedGQ + handleSend
  // in the same event would read stale state. Ref is synchronously updated.
  const lastClickedGQRef = useRef<string | null>(null);

  const handleSend = async (overrideText?: string) => {
    const queryText = (overrideText ?? input).trim();
    if (!queryText || loading) return;
    pendingQueryRef.current = queryText;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: queryText,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      if (useWebSocket && wsStatus === "connected") {
        const sent = websocketService.sendChatMessage(queryText);
        if (!sent) throw new Error("WebSocket send failed");
      } else {
        const response = await workflowApi.sendQuery(
          { query: queryText, session_id: sessionId, thread_id: sessionId },
          { userId: user?.id },
        );

        // Hybrid follow-up: static for first GQ response, backend for rest
        let suggestedQuestions: string[];
        const currentGQ = lastClickedGQRef.current;
        const staticFollowUps = currentGQ
          ? getStaticFollowUps(currentGQ)
          : undefined;

        if (staticFollowUps && staticFollowUps.length > 0) {
          // First response to a Golden Question — use static follow-ups
          suggestedQuestions = staticFollowUps;
          lastClickedGQRef.current = null; // Clear so subsequent rounds use backend
        } else if (
          response.suggested_questions &&
          response.suggested_questions.length > 0
        ) {
          suggestedQuestions = response.suggested_questions;
        } else {
          suggestedQuestions = buildFallbackSuggestedQuestions(
            queryText,
            response.sources && response.sources.length > 0
              ? response.sources[0].document_name
              : undefined,
          );
        }

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: response.response,
          sender: "ai",
          timestamp: new Date(),
          intent: response.intent,
          sources: response.sources,
          suggestedQuestions,
          metadata: response.metadata,
        };

        setMessages((prev) => [...prev, aiMessage]);
        setLoading(false);
      }
    } catch (error) {
      console.error("Query error:", error);
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        content:
          "Sorry, an error occurred while processing your query. Please try again later.",
        sender: "ai",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setLoading(false);
    }
  };

  const handleGoldenQuestionSelect = (questionText: string) => {
    lastClickedGQRef.current = questionText;
    setMobileGQOpen(false);
    handleSend(questionText);
  };

  const handleFollowUpClick = (question: string) => {
    lastClickedGQRef.current = null; // Follow-up clicks are not GQ first-round
    handleSend(question);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      lastClickedGQRef.current = null; // Manual typing clears GQ tracking
      handleSend();
    }
  };

  // Get latest AI message metadata for pipeline
  const latestMetadata =
    [...messages].reverse().find((m) => m.sender === "ai" && m.metadata)
      ?.metadata ?? null;

  const apiStatusDot =
    apiStatus === "connected"
      ? "bg-green-500"
      : apiStatus === "disconnected"
        ? "bg-red-500"
        : "bg-yellow-500";

  const apiStatusText =
    apiStatus === "connected"
      ? "Connected"
      : apiStatus === "disconnected"
        ? "Disconnected"
        : "Checking...";

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-6 h-full flex flex-col">
      {/* Dark Hero Header */}
      <div
        className="bg-[#1a1a2e] rounded-2xl px-6 py-4 mb-4 flex-shrink-0 relative overflow-hidden"
        data-testid="workflow-chat-hero"
      >
        <div className="absolute inset-0 bg-gradient-to-br from-blue-900/5 to-transparent pointer-events-none" />
        <div className="relative flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-200">Workflow Chat</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              AI-powered construction knowledge assistant
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${apiStatusDot}`} />
            <span className="text-xs text-gray-400">{apiStatusText}</span>
          </div>
        </div>
      </div>

      {/* WebSocket banner (rarely shown) */}
      {useWebSocket && wsStatus !== "disconnected" && (
        <div
          className={`mb-4 p-2 rounded-lg text-xs ${
            wsStatus === "connected"
              ? "bg-green-50 text-green-800"
              : "bg-yellow-50 text-yellow-800"
          }`}
        >
          WebSocket{" "}
          {wsStatus === "connected"
            ? "connected"
            : "connecting..."}
        </div>
      )}

      {/* Mobile Golden Questions toggle */}
      <div className="lg:hidden mb-3 flex-shrink-0">
        <button
          type="button"
          onClick={() => setMobileGQOpen(!mobileGQOpen)}
          className="w-full flex items-center justify-between px-4 py-2 bg-white rounded-lg border border-gray-200 text-sm text-gray-700"
          data-testid="mobile-gq-toggle"
        >
          <span>Golden Questions</span>
          <svg
            className={`w-4 h-4 transition-transform ${mobileGQOpen ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {mobileGQOpen && (
          <div className="mt-2 bg-white rounded-lg border border-gray-200 p-3 max-h-64 overflow-y-auto">
            <GoldenQuestions
              onSelect={handleGoldenQuestionSelect}
              disabled={loading}
            />
          </div>
        )}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-0">
        {/* Chat area — 3/4 width */}
        <div className="lg:col-span-3 flex flex-col min-h-0">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col flex-1 min-h-0">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 min-h-0">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`mb-5 ${message.sender === "user" ? "text-right" : "text-left"}`}
                >
                  <div
                    className={`inline-block max-w-[85%] rounded-2xl px-4 py-3 ${
                      message.sender === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-50 text-gray-800 border-l-2 border-blue-200"
                    }`}
                    data-testid={
                      message.sender === "user" ? "user-bubble" : "ai-bubble"
                    }
                  >
                    {message.sender === "ai" ? (
                      <MarkdownRenderer content={message.content} />
                    ) : (
                      <div className="whitespace-pre-wrap">
                        {message.content}
                      </div>
                    )}

                    {/* Compact source citations — always visible */}
                    {message.sender === "ai" &&
                      message.sources &&
                      message.sources.length > 0 && (
                        <div
                          className="mt-2 pt-2 border-t border-gray-200"
                          data-testid="source-citations"
                        >
                          <div className="text-xs font-medium text-gray-500 mb-1">
                            Sources
                          </div>
                          {message.sources.map((source, index) => (
                            <div
                              key={index}
                              className="flex items-center gap-2 text-[11px] py-0.5"
                            >
                              <span className="text-gray-700 font-medium truncate flex-1">
                                {source.document_name}
                              </span>
                              <span className="text-gray-400 flex-shrink-0">
                                {(source.relevance * 100).toFixed(0)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      )}

                    {/* Follow-up question pills */}
                    {message.sender === "ai" &&
                      message.suggestedQuestions &&
                      message.suggestedQuestions.length > 0 && (
                        <div
                          className="mt-2 pt-2 border-t border-gray-200"
                          data-testid="follow-up-pills"
                        >
                          <div className="text-xs font-medium text-gray-500 mb-1.5">
                            Follow-up
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {message.suggestedQuestions.map(
                              (question, index) => (
                                <button
                                  key={`${message.id}-suggestion-${index}`}
                                  type="button"
                                  onClick={() =>
                                    handleFollowUpClick(question)
                                  }
                                  className="text-[11px] px-2.5 py-1 rounded-full border border-blue-200 text-blue-600 hover:bg-blue-50 transition leading-tight"
                                  data-testid={`follow-up-${index}`}
                                >
                                  {question}
                                </button>
                              ),
                            )}
                          </div>
                        </div>
                      )}

                    <div
                      className={`text-[10px] mt-2 ${
                        message.sender === "user"
                          ? "text-blue-200"
                          : "text-gray-400"
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="text-left mb-4">
                  <div className="inline-block max-w-[80%] rounded-2xl px-4 py-3 bg-gray-50 border-l-2 border-blue-200">
                    <div className="flex items-center space-x-1.5">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse [animation-delay:150ms]" />
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="border-t border-gray-200 p-3">
              <div className="flex gap-2">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Enter your question or query..."
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none text-sm"
                  rows={2}
                  disabled={loading}
                  data-testid="chat-input"
                />
                <button
                  onClick={() => {
                    lastClickedGQRef.current = null;
                    handleSend();
                  }}
                  disabled={loading || !input.trim()}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed self-end"
                  data-testid="send-button"
                >
                  {loading ? "..." : "Send"}
                </button>
              </div>
              <div className="mt-1.5 text-[11px] text-gray-400">
                Enter to send · Shift+Enter for new line
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar — 1/4 width, desktop only */}
        <div className="hidden lg:flex flex-col min-h-0 gap-3">
          {/* Golden Questions — scrollable top section */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 flex-1 overflow-y-auto min-h-0">
            <GoldenQuestions
              onSelect={handleGoldenQuestionSelect}
              disabled={loading}
            />
          </div>

          {/* Compact Pipeline — sticky bottom */}
          <CompactPipelineViz metadata={latestMetadata} loading={loading} />
        </div>
      </div>
    </div>
  );
}
