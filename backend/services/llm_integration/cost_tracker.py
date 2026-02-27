"""Usage/cost tracking and tenant budget governance for LLM dispatch."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.config import settings
from backend.observability.llm_metrics import record_llm_cost, record_llm_tokens
from backend.services.database.driver_compat import (
    connect as connect_db,
    fetchall_dicts,
    fetchone_dict,
)
from backend.services.llm_integration.types import CostStats, UsageStats

logger = logging.getLogger(__name__)


@dataclass
class BudgetPolicy:
    tenant_id: str
    monthly_budget_usd: float
    soft_limit_ratio: float = 0.8
    hard_limit_ratio: float = 1.0
    policy_mode: str = "local_only"  # local_only | block


class CostTracker:
    # USD per 1M tokens (input, output). Local backends are zero-cost.
    DEFAULT_RATE_TABLE: Dict[str, Dict[str, tuple]] = {
        "llama_cpp": {"*": (0.0, 0.0)},
        "ollama": {"*": (0.0, 0.0)},
        "zhipu": {
            "glm-4-plus": (2.0, 8.0),
            "*": (2.0, 8.0),
        },
    }

    def __init__(self) -> None:
        self.database_url = settings.database_url
        self.rate_table = self.DEFAULT_RATE_TABLE

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        ascii_chars = sum(1 for ch in text if ord(ch) < 128)
        non_ascii_chars = max(0, len(text) - ascii_chars)
        # Rough heuristic: ~4 ASCII chars/token, ~1 CJK char/token.
        return max(1, int(ascii_chars / 4) + non_ascii_chars)

    def estimate_request_cost(self, max_tokens: int = 512) -> float:
        """Estimate the cost of a cloud request based on max output tokens."""
        # Use the most expensive cloud rate as a conservative estimate.
        rate = self.rate_table.get("zhipu", {}).get("*", (2.0, 8.0))
        output_rate_per_token = rate[1] / 1_000_000
        return max_tokens * output_rate_per_token

    def estimate_usage(self, prompt: str, completion: str) -> UsageStats:
        prompt_tokens = self._estimate_tokens(prompt)
        completion_tokens = self._estimate_tokens(completion)
        return UsageStats(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    def estimate_cost(self, provider: str, model: str, usage: UsageStats) -> CostStats:
        provider_key = (provider or "").strip().lower()
        model_key = (model or "").strip()
        provider_rates = self.rate_table.get(provider_key, {})
        input_per_million, output_per_million = provider_rates.get(
            model_key, provider_rates.get("*", (0.0, 0.0))
        )
        estimated = (
            usage.prompt_tokens * input_per_million
            + usage.completion_tokens * output_per_million
        ) / 1_000_000
        return CostStats(estimated_cost_usd=round(float(estimated), 6))

    def _connect(self):
        return connect_db(self.database_url)

    def record_usage(
        self,
        *,
        tenant_id: str,
        provider: str,
        model: str,
        usage: UsageStats,
        cost: CostStats,
        latency_ms: int,
        status: str,
        trace_id: Optional[str] = None,
        route_mode: Optional[str] = None,
    ) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO llm_usage_logs (
                            id, tenant_id, provider, model,
                            prompt_tokens, completion_tokens, total_tokens,
                            estimated_cost_usd, latency_ms, status, trace_id, route_mode
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            uuid.uuid4(),
                            tenant_id,
                            provider,
                            model,
                            usage.prompt_tokens,
                            usage.completion_tokens,
                            usage.total_tokens,
                            cost.estimated_cost_usd,
                            max(0, latency_ms),
                            status,
                            trace_id,
                            route_mode,
                        ),
                    )
        except Exception as exc:
            logger.warning("Failed to persist llm usage log: %s", exc)

        record_llm_tokens(
            provider=provider,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )
        record_llm_cost(provider=provider, estimated_cost_usd=cost.estimated_cost_usd)

    def get_usage_summary(
        self, *, tenant_id: str, days: int = 30, provider: Optional[str] = None
    ) -> Dict[str, object]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            params: List[object] = [tenant_id, max(1, days)]
            provider_filter = ""
            if provider:
                provider_filter = "AND provider = %s"
                params.append(provider)
            cur.execute(
                f"""
                SELECT
                    provider,
                    model,
                    COUNT(*) AS request_count,
                    SUM(prompt_tokens) AS prompt_tokens,
                    SUM(completion_tokens) AS completion_tokens,
                    SUM(total_tokens) AS total_tokens,
                    SUM(estimated_cost_usd) AS total_cost_usd
                FROM llm_usage_logs
                WHERE tenant_id = %s
                  AND created_at >= NOW() - (%s || ' days')::INTERVAL
                  {provider_filter}
                GROUP BY provider, model
                ORDER BY total_cost_usd DESC, request_count DESC
                """,
                tuple(params),
            )
            rows = fetchall_dicts(cur)
        except Exception as exc:
            logger.warning("Failed to query llm usage summary: %s", exc)
            rows = []
        finally:
            cur.close()
            conn.close()

        totals = {
            "request_count": sum(int(r.get("request_count") or 0) for r in rows),
            "prompt_tokens": sum(int(r.get("prompt_tokens") or 0) for r in rows),
            "completion_tokens": sum(
                int(r.get("completion_tokens") or 0) for r in rows
            ),
            "total_tokens": sum(int(r.get("total_tokens") or 0) for r in rows),
            "total_cost_usd": round(
                sum(float(r.get("total_cost_usd") or 0.0) for r in rows), 6
            ),
        }
        return {
            "tenant_id": tenant_id,
            "days": days,
            "provider_filter": provider,
            "summary": rows,
            "totals": totals,
        }

    def get_budget_policy(self, tenant_id: str) -> Optional[BudgetPolicy]:
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT tenant_id, monthly_budget_usd, soft_limit_ratio,
                       hard_limit_ratio, policy_mode
                FROM llm_budget_policies
                WHERE tenant_id = %s
                """,
                (tenant_id,),
            )
            row = fetchone_dict(cur)
            if not row:
                return None
            return BudgetPolicy(
                tenant_id=row["tenant_id"],
                monthly_budget_usd=float(row["monthly_budget_usd"]),
                soft_limit_ratio=float(row["soft_limit_ratio"]),
                hard_limit_ratio=float(row["hard_limit_ratio"]),
                policy_mode=row["policy_mode"],
            )
        except Exception as exc:
            logger.warning("Failed to load budget policy: %s", exc)
            return None
        finally:
            cur.close()
            conn.close()

    def upsert_budget_policy(self, policy: BudgetPolicy) -> BudgetPolicy:
        policy.soft_limit_ratio = max(0.0, min(policy.soft_limit_ratio, 1.0))
        policy.hard_limit_ratio = max(policy.soft_limit_ratio, policy.hard_limit_ratio)
        policy.policy_mode = (
            policy.policy_mode
            if policy.policy_mode in {"local_only", "block"}
            else "local_only"
        )

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO llm_budget_policies (
                    tenant_id, monthly_budget_usd, soft_limit_ratio,
                    hard_limit_ratio, policy_mode, updated_at
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (tenant_id) DO UPDATE SET
                    monthly_budget_usd = EXCLUDED.monthly_budget_usd,
                    soft_limit_ratio = EXCLUDED.soft_limit_ratio,
                    hard_limit_ratio = EXCLUDED.hard_limit_ratio,
                    policy_mode = EXCLUDED.policy_mode,
                    updated_at = NOW()
                """,
                (
                    policy.tenant_id,
                    max(0.0, float(policy.monthly_budget_usd)),
                    policy.soft_limit_ratio,
                    policy.hard_limit_ratio,
                    policy.policy_mode,
                ),
            )
            conn.commit()
        except Exception as exc:
            logger.warning("Failed to persist budget policy: %s", exc)
        finally:
            cur.close()
            conn.close()
        return policy

    def get_monthly_spend(
        self, tenant_id: str, when: Optional[datetime] = None
    ) -> float:
        when = when or datetime.now(timezone.utc)
        month_start = datetime(when.year, when.month, 1, tzinfo=timezone.utc)
        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT COALESCE(SUM(estimated_cost_usd), 0)
                FROM llm_usage_logs
                WHERE tenant_id = %s
                  AND created_at >= %s
                """,
                (tenant_id, month_start),
            )
            amount = float(cur.fetchone()[0] or 0.0)
            return amount
        except Exception as exc:
            logger.warning("Failed to query monthly spend: %s", exc)
            return 0.0
        finally:
            cur.close()
            conn.close()

    def evaluate_budget(
        self, tenant_id: str, additional_cost_usd: float = 0.0
    ) -> Dict[str, object]:
        policy = self.get_budget_policy(tenant_id)
        if not policy:
            return {
                "allowed": True,
                "decision": "allow",
                "policy_mode": "none",
                "monthly_spend_usd": 0.0,
                "monthly_budget_usd": None,
                "ratio": 0.0,
            }

        monthly_spend = self.get_monthly_spend(tenant_id) + max(
            0.0, additional_cost_usd
        )
        budget = max(0.0, policy.monthly_budget_usd)
        ratio = (monthly_spend / budget) if budget > 0 else 0.0

        if budget > 0 and ratio >= policy.hard_limit_ratio:
            decision = "block_cloud" if policy.policy_mode == "block" else "force_local"
            return {
                "allowed": False,
                "decision": decision,
                "policy_mode": policy.policy_mode,
                "monthly_spend_usd": round(monthly_spend, 6),
                "monthly_budget_usd": budget,
                "ratio": round(ratio, 4),
            }

        if budget > 0 and ratio >= policy.soft_limit_ratio:
            return {
                "allowed": True,
                "decision": "warn_soft_limit",
                "policy_mode": policy.policy_mode,
                "monthly_spend_usd": round(monthly_spend, 6),
                "monthly_budget_usd": budget,
                "ratio": round(ratio, 4),
            }

        return {
            "allowed": True,
            "decision": "allow",
            "policy_mode": policy.policy_mode,
            "monthly_spend_usd": round(monthly_spend, 6),
            "monthly_budget_usd": budget,
            "ratio": round(ratio, 4),
        }


cost_tracker = CostTracker()
