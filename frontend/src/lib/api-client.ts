import type { AppConfigState } from "@/components/app-config-context";

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  config: AppConfigState;
  path: string;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>({ method = "GET", body, config, path }: RequestOptions): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Tenant-ID": config.tenantId,
  };

  if (config.apiKey) {
    headers["X-API-Key"] = config.apiKey;
  }

  const response = await fetch(`/api/backend/${path.replace(/^\/+/, "")}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : payload;
    throw new ApiError(
      `Request failed (${response.status})`,
      response.status,
      detail,
    );
  }

  return payload as T;
}

export interface WorkflowQueryRequest {
  query: string;
  session_id?: string;
  user_id?: string;
  route_mode?: "local_only" | "hybrid_auto" | "cloud_only";
}

export interface WorkflowQueryResponse {
  success: boolean;
  trace_id: string;
  session_id: string;
  intent?: string;
  route_mode: string;
  provider_used?: string;
  response?: string;
  metadata: Record<string, unknown>;
  error?: string;
}

export interface CostPrediction {
  predicted_cost_overrun_pct: number;
  predicted_actual_cost_cad: number;
  estimated_cost_cad: number;
  prediction_interval_cad: {
    confidence_quantile: number;
    lower: number;
    upper: number;
  };
  uncertainty: {
    ape_quantile: number;
  };
  unknown_categories: Record<string, string>;
}

export interface CostPredictResponse {
  success: boolean;
  prediction: CostPrediction;
}

export interface CostBatchPredictResponse {
  success: boolean;
  count: number;
  predictions: CostPrediction[];
}

export interface HealthResponse {
  status: string;
  component?: string;
  model?: Record<string, unknown>;
  memory_usage_mb?: number;
  version?: string;
}

export interface LlmUsageResponse {
  tenant_id?: string;
  total_cost_usd?: number;
  total_requests?: number;
  [key: string]: unknown;
}

export interface LlmBudgetResponse {
  tenant_id: string;
  policy: {
    monthly_budget_usd: number;
    soft_limit_ratio: number;
    hard_limit_ratio: number;
    policy_mode: string;
  } | null;
  current_month_spend_usd: number;
  budget_evaluation: Record<string, unknown>;
}

export interface BudgetPolicyRequest {
  monthly_budget_usd: number;
  soft_limit_ratio: number;
  hard_limit_ratio: number;
  policy_mode: "local_only" | "block";
}

export interface DemoModeState {
  success: boolean;
  mode: "live_hybrid" | "local_safe" | "scripted_replay";
  allow_cloud_override: boolean;
  profile: {
    label: string;
    description: string;
    default_route_mode: string;
    cloud_allowed: boolean;
    scripted_replay_enabled: boolean;
  };
  available_modes: Array<{
    mode: "live_hybrid" | "local_safe" | "scripted_replay";
    label: string;
    description: string;
  }>;
}

export async function getPlatformHealth(config: AppConfigState) {
  return request<HealthResponse>({ config, path: "api/v1/health" });
}

export async function getWorkflowHealth(config: AppConfigState) {
  return request<HealthResponse>({ config, path: "api/v1/workflow/health" });
}

export async function getCostHealth(config: AppConfigState) {
  return request<HealthResponse>({ config, path: "api/v1/cost-estimation/health" });
}

export async function queryWorkflow(config: AppConfigState, payload: WorkflowQueryRequest) {
  return request<WorkflowQueryResponse>({
    config,
    path: "api/v1/workflow/query",
    method: "POST",
    body: payload,
  });
}

export interface CostProjectFeatures {
  project_type: string;
  location: string;
  sqft: number;
  floors: number;
  num_units: number;
  planned_duration_weeks: number;
  estimated_cost_cad: number;
  contractor_rating: number;
  complexity_score: number;
  team_experience_years: number;
  num_change_orders: number;
  weather_risk_factor: number;
  material_volatility: number;
  num_subcontractors: number;
  budget_pressure: number;
  risk_score: number;
  risk_score_original: number;
}

export async function predictCost(
  config: AppConfigState,
  project: CostProjectFeatures,
  confidence_quantile = 0.9,
) {
  return request<CostPredictResponse>({
    config,
    path: "api/v1/cost-estimation/predict",
    method: "POST",
    body: { project, confidence_quantile },
  });
}

export async function predictCostBatch(
  config: AppConfigState,
  projects: CostProjectFeatures[],
  confidence_quantile = 0.9,
) {
  return request<CostBatchPredictResponse>({
    config,
    path: "api/v1/cost-estimation/predict/batch",
    method: "POST",
    body: { projects, confidence_quantile },
  });
}

export async function uploadDocument(config: AppConfigState, file: File) {
  const form = new FormData();
  form.append("file", file);

  const headers: Record<string, string> = {
    "X-Tenant-ID": config.tenantId,
  };
  if (config.apiKey) {
    headers["X-API-Key"] = config.apiKey;
  }

  const response = await fetch("/api/backend/api/v1/documents/upload", {
    method: "POST",
    headers,
    body: form,
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new ApiError("Upload failed", response.status, payload);
  }
  return payload as Record<string, unknown>;
}

export async function uploadDataFile(config: AppConfigState, file: File) {
  const form = new FormData();
  form.append("file", file);

  const headers: Record<string, string> = {
    "X-Tenant-ID": config.tenantId,
  };
  if (config.apiKey) {
    headers["X-API-Key"] = config.apiKey;
  }

  const response = await fetch("/api/backend/api/v1/data/upload", {
    method: "POST",
    headers,
    body: form,
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new ApiError("Data upload failed", response.status, payload);
  }
  return payload as Record<string, unknown>;
}

export async function getDocumentStats(config: AppConfigState) {
  return request<Record<string, unknown>>({
    config,
    path: "api/v1/documents/statistics",
  });
}

export async function getDocumentOperationLog(config: AppConfigState) {
  return request<Record<string, unknown>>({
    config,
    path: "api/v1/documents/operations/log",
  });
}

export async function runDataAnalysis(
  config: AppConfigState,
  payload: Record<string, unknown>,
) {
  return request<Record<string, unknown>>({
    config,
    path: "api/v1/data/analyze",
    method: "POST",
    body: payload,
  });
}

export async function generateVisualization(
  config: AppConfigState,
  payload: Record<string, unknown>,
) {
  return request<Record<string, unknown>>({
    config,
    path: "api/v1/visualization/generate",
    method: "POST",
    body: payload,
  });
}

export async function getPromptMetrics(config: AppConfigState) {
  return request<Record<string, unknown>>({
    config,
    path: "api/prompts/metrics/summary",
  });
}

export async function listPrompts(config: AppConfigState) {
  return request<Record<string, unknown>>({
    config,
    path: "api/prompts?page=1&size=5",
  });
}

export async function getLlmUsage(config: AppConfigState) {
  return request<LlmUsageResponse>({
    config,
    path: `llm/usage?days=30&tenant_id=${encodeURIComponent(config.tenantId)}`,
  });
}

export async function getLlmBudget(config: AppConfigState, tenantId: string) {
  return request<LlmBudgetResponse>({
    config,
    path: `llm/budget/${encodeURIComponent(tenantId)}`,
  });
}

export async function updateLlmBudget(
  config: AppConfigState,
  tenantId: string,
  policy: BudgetPolicyRequest,
) {
  return request<Record<string, unknown>>({
    config,
    path: `llm/budget/${encodeURIComponent(tenantId)}`,
    method: "POST",
    body: policy,
  });
}

export async function getDemoMode(config: AppConfigState) {
  return request<DemoModeState>({
    config,
    path: "api/v1/demo/mode",
  });
}

export async function updateDemoMode(
  config: AppConfigState,
  payload: {
    mode: "live_hybrid" | "local_safe" | "scripted_replay";
    allow_cloud_override?: boolean;
  },
) {
  return request<DemoModeState>({
    config,
    path: "api/v1/demo/mode",
    method: "POST",
    body: payload,
  });
}
