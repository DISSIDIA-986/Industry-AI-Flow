"""Unified LLM dispatch service with privacy and cost governance."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from backend.config import settings
from backend.observability.llm_metrics import record_llm_fallback, record_llm_request
from backend.services.audit_logger import audit_logger
from backend.services.demo_mode_service import get_demo_mode_service
from backend.services.llm_integration.cost_tracker import CostTracker, cost_tracker
from backend.services.llm_integration.llm_client import LLMClientFactory
from backend.services.llm_integration.types import (
    CostStats,
    DispatchRequest,
    DispatchResponse,
    UsageStats,
)
from backend.services.security.egress_guard import EgressDecision, EgressGuard
from backend.services.security.redaction_service import RedactionService

logger = logging.getLogger(__name__)


class DispatchService:
    """Single control-plane for local/cloud dispatch and fallback."""

    def __init__(
        self,
        local_client=None,
        cloud_client=None,
        redactor: Optional[RedactionService] = None,
        egress_guard: Optional[EgressGuard] = None,
        tracker: Optional[CostTracker] = None,
    ) -> None:
        self._local_client = local_client
        self._cloud_client = cloud_client
        self.redactor = redactor or RedactionService()
        self.egress_guard = egress_guard or EgressGuard(self.redactor)
        self.cost_tracker = tracker or cost_tracker
        self._cloud_call_windows = defaultdict(deque)
        self._rate_limit_lock = threading.Lock()

    def _get_local_client(self):
        if self._local_client is None:
            backend = settings.resolved_local_backend
            self._local_client = LLMClientFactory.create_client(backend=backend)
        return self._local_client

    def _get_cloud_client(self):
        if self._cloud_client is None:
            provider = settings.resolved_cloud_provider
            self._cloud_client = LLMClientFactory.create_client(backend=provider)
        return self._cloud_client

    @staticmethod
    def _estimate_confidence(answer: str) -> float:
        if not answer:
            return 0.0
        text = answer.strip()
        if not text:
            return 0.0

        # Very short responses get low confidence
        if len(text) < 50:
            return 0.3

        lowered = text.lower()

        # Uncertainty markers that indicate low confidence
        uncertainty_phrases = [
            "i don't know",
            "i'm not sure",
            "i am not sure",
            "i cannot determine",
            "i cannot",
            "i'm unable to",
            "i am unable",
            "i do not have enough information",
            "insufficient information",
            "no information",
            "not enough context",
            "it depends",
            "generally speaking",
            "it is difficult to say",
            "further analysis would be needed",
            "i think",
            "might be",
            "could range",
        ]
        uncertainty_count = sum(1 for phrase in uncertainty_phrases if phrase in lowered)
        if uncertainty_count >= 3:
            return 0.45

        # Single strong uncertainty marker
        if any(
            phrase in lowered
            for phrase in ("i don't know", "i cannot determine", "i'm not sure")
        ):
            return 0.55

        # Check for repetition: split into sentences and look for duplicates
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if len(sentences) >= 3:
            unique_sentences = set(sentences)
            repetition_ratio = 1.0 - (len(unique_sentences) / len(sentences))
            if repetition_ratio > 0.5:
                return 0.4

        # Base confidence from content quality signals
        base = 0.55
        length_boost = min(len(text), 600) / 1500

        # Penalize hedging / vague language
        hedging_penalty = min(0.15, uncertainty_count * 0.05)

        # Penalize highly repetitive text (low unique-word ratio)
        words = lowered.split()
        if len(words) > 20:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.4:
                hedging_penalty += 0.10

        # Penalize lack of domain relevance — construction domain terms
        domain_terms = {
            "concrete", "steel", "foundation", "beam", "column", "rebar",
            "sqft", "cost", "load", "structural", "building", "code",
            "spec", "safety", "inspection", "permit", "excavation",
            "hvac", "plumbing", "electrical", "insulation",
        }
        domain_hit_count = sum(1 for t in domain_terms if t in lowered)
        if domain_hit_count == 0:
            hedging_penalty += 0.10  # No domain relevance signal

        confidence = base + length_boost - hedging_penalty
        return round(max(0.0, min(0.95, confidence)), 4)

    @staticmethod
    def _truncate_prompt(prompt: str, max_tokens: int, context_window: int = 4096) -> str:
        reserved_output = max_tokens or 512
        max_input_chars = max(1, (context_window - reserved_output) * 3)
        if len(prompt) > max_input_chars:
            return prompt[:max_input_chars]
        return prompt

    @staticmethod
    def _resolve_model_name(client, fallback: str) -> str:
        if client is None:
            return fallback
        if hasattr(client, "model"):
            return str(getattr(client, "model"))
        info = {}
        if hasattr(client, "get_model_info"):
            try:
                info = client.get_model_info() or {}
            except Exception:
                info = {}
        return str(info.get("model") or info.get("name") or fallback)

    def generate(self, req: DispatchRequest) -> DispatchResponse:
        demo_mode_service = get_demo_mode_service()
        replay = demo_mode_service.replay_response(req.prompt)
        if replay is not None:
            return DispatchResponse(
                success=True,
                text=str(replay["response"]),
                provider="scripted_replay",
                model="scripted-replay-v1",
                route_mode="local_only",
                trace_id=req.trace_id,
                latency_ms=0,
                confidence=1.0,
                usage=UsageStats(),
                cost=CostStats(),
                policy_decision="scripted_replay",
            )

        route_mode = demo_mode_service.resolve_route_mode(
            req.route_mode or settings.resolved_hybrid_mode
        )

        if route_mode == "local_only":
            return self._run_local(req, route_mode="local_only")

        if route_mode == "cloud_only":
            return self._run_cloud(req, route_mode="cloud_only")

        # hybrid_auto
        local_res = self._run_local(req, route_mode="hybrid_auto", soft_fail=True)
        threshold = req.local_conf_threshold or settings.local_confidence_threshold
        if local_res.success and local_res.confidence >= threshold:
            return local_res

        record_llm_fallback(reason="low_confidence_or_error")
        return self._run_cloud(
            req, route_mode="hybrid_auto", fallback_from_local=local_res
        )

    def _record_audit(
        self,
        *,
        req: DispatchRequest,
        status: str,
        provider: str,
        redaction_applied: bool,
        sensitive_hit_count: int,
        policy_decision: str,
        detail_extra: Optional[dict] = None,
    ) -> None:
        detail = {
            "provider": provider,
            "redaction_applied": redaction_applied,
            "sensitive_hit_count": sensitive_hit_count,
            "policy_decision": policy_decision,
            "trace_id": req.trace_id,
            "route_mode": req.route_mode,
        }
        if detail_extra:
            detail.update(detail_extra)
        audit_logger.log_event(
            action="llm.dispatch",
            tenant_id=req.tenant_id or settings.default_tenant_id,
            status=status,
            detail=detail,
        )

    def _run_local(
        self,
        req: DispatchRequest,
        *,
        route_mode: str,
        soft_fail: bool = False,
    ) -> DispatchResponse:
        started = time.time()
        provider = settings.resolved_local_backend
        try:
            client = self._get_local_client()
            prompt = self._truncate_prompt(req.prompt, req.max_tokens or 512, context_window=4096)
            text = client.generate(
                prompt,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                top_p=req.top_p,
            )
            latency_ms = int((time.time() - started) * 1000)
            usage = self.cost_tracker.estimate_usage(req.prompt, text)
            cost = self.cost_tracker.estimate_cost(
                provider=provider,
                model=self._resolve_model_name(client, provider),
                usage=usage,
            )
            self.cost_tracker.record_usage(
                tenant_id=req.tenant_id,
                provider=provider,
                model=self._resolve_model_name(client, provider),
                usage=usage,
                cost=cost,
                latency_ms=latency_ms,
                status="success",
                trace_id=req.trace_id,
                route_mode=route_mode,
            )
            self._record_audit(
                req=req,
                status="success",
                provider=provider,
                redaction_applied=False,
                sensitive_hit_count=0,
                policy_decision="allow",
                detail_extra={"latency_ms": latency_ms},
            )
            record_llm_request(
                provider=provider,
                route_mode=route_mode,
                status="success",
                latency_seconds=max(0.0, (time.time() - started)),
            )
            return DispatchResponse(
                success=True,
                text=text,
                provider=provider,
                model=self._resolve_model_name(client, provider),
                route_mode=route_mode,  # type: ignore[arg-type]
                trace_id=req.trace_id,
                latency_ms=latency_ms,
                confidence=self._estimate_confidence(text),
                usage=usage,
                cost=cost,
            )
        except Exception as exc:
            latency_ms = int((time.time() - started) * 1000)
            error_message = str(exc)
            logger.warning("Local LLM generation failed: %s", error_message)
            self._record_audit(
                req=req,
                status="error",
                provider=provider,
                redaction_applied=False,
                sensitive_hit_count=0,
                policy_decision="local_error",
                detail_extra={"error": error_message},
            )
            record_llm_request(
                provider=provider,
                route_mode=route_mode,
                status="error",
                latency_seconds=max(0.0, (time.time() - started)),
            )
            if soft_fail:
                return DispatchResponse(
                    success=False,
                    text="",
                    provider=provider,
                    model=provider,
                    route_mode=route_mode,  # type: ignore[arg-type]
                    trace_id=req.trace_id,
                    latency_ms=latency_ms,
                    confidence=0.0,
                    error=error_message,
                    policy_decision="local_error_soft_fail",
                )
            raise

    def _run_cloud(
        self,
        req: DispatchRequest,
        *,
        route_mode: str,
        fallback_from_local: Optional[DispatchResponse] = None,
    ) -> DispatchResponse:
        started = time.time()
        provider = settings.resolved_cloud_provider
        model = provider
        demo_mode_service = get_demo_mode_service()

        if not demo_mode_service.cloud_calls_allowed():
            latency_ms = int((time.time() - started) * 1000)
            if route_mode == "hybrid_auto" and fallback_from_local is not None:
                record_llm_fallback(reason="demo_mode_force_local")
                return fallback_from_local
            return DispatchResponse(
                success=False,
                text="Cloud provider is disabled by current demo mode.",
                provider=provider,
                model=model,
                route_mode=route_mode,  # type: ignore[arg-type]
                trace_id=req.trace_id,
                latency_ms=latency_ms,
                policy_decision="demo_mode_force_local",
                error="cloud_disabled_by_demo_mode",
            )

        rate_limit = max(1, settings.max_cloud_calls_per_minute)
        cloud_window = self._cloud_call_windows[req.tenant_id]
        with self._rate_limit_lock:
            now = time.time()
            while cloud_window and now - cloud_window[0] > 60:
                cloud_window.popleft()
            if len(cloud_window) >= rate_limit:
                latency_ms = int((time.time() - started) * 1000)
                if route_mode == "hybrid_auto" and fallback_from_local is not None:
                    record_llm_fallback(reason="cloud_rate_limit")
                    return fallback_from_local
                return DispatchResponse(
                    success=False,
                    text="Cloud provider rate limit reached for this tenant.",
                    provider=provider,
                    model=model,
                    route_mode=route_mode,  # type: ignore[arg-type]
                    trace_id=req.trace_id,
                    latency_ms=latency_ms,
                    policy_decision="rate_limit",
                    error="max_cloud_calls_per_minute exceeded",
                )

        estimated_cost = 0.0
        if hasattr(self.cost_tracker, "estimate_request_cost"):
            estimated_cost = self.cost_tracker.estimate_request_cost(req.max_tokens or 512)
        budget_eval = self.cost_tracker.evaluate_budget(req.tenant_id, additional_cost_usd=estimated_cost)
        if not budget_eval.get("allowed", True):
            latency_ms = int((time.time() - started) * 1000)
            policy_decision = str(budget_eval.get("decision") or "block_cloud")
            if route_mode == "hybrid_auto" and fallback_from_local is not None:
                # Return previously-computed local result when policy blocks cloud.
                record_llm_fallback(reason="budget_policy")
                return fallback_from_local
            return DispatchResponse(
                success=False,
                text="Cloud provider is blocked by budget policy.",
                provider=provider,
                model=model,
                route_mode=route_mode,  # type: ignore[arg-type]
                trace_id=req.trace_id,
                latency_ms=latency_ms,
                policy_decision=policy_decision,
                error=policy_decision,
            )

        redaction = self.redactor.redact(req.prompt)
        decision: EgressDecision = self.egress_guard.evaluate(
            original_text=req.prompt,
            redacted_text=redaction.text,
            redaction_result=redaction,
        )
        if not decision.allowed:
            latency_ms = int((time.time() - started) * 1000)
            self._record_audit(
                req=req,
                status="error",
                provider=provider,
                redaction_applied=True,
                sensitive_hit_count=redaction.hit_count,
                policy_decision=decision.policy_decision,
                detail_extra={"reason": decision.reason},
            )
            return DispatchResponse(
                success=False,
                text="Outbound payload was blocked by egress policy.",
                provider=provider,
                model=model,
                route_mode=route_mode,  # type: ignore[arg-type]
                trace_id=req.trace_id,
                latency_ms=latency_ms,
                redaction_applied=True,
                sensitive_hit_count=redaction.hit_count,
                redaction_categories=redaction.categories,
                policy_decision=decision.policy_decision,
                error=decision.reason,
            )

        try:
            client = self._get_cloud_client()
            model = self._resolve_model_name(client, provider)
            prompt_text = self._truncate_prompt(redaction.text, req.max_tokens or 512, context_window=128000)
            text = client.generate(
                prompt_text,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                top_p=req.top_p,
            )
            now = time.time()
            with self._rate_limit_lock:
                cloud_window.append(now)
            latency_ms = int((time.time() - started) * 1000)
            usage = self.cost_tracker.estimate_usage(prompt_text, text)
            cost = self.cost_tracker.estimate_cost(
                provider=provider, model=model, usage=usage
            )
            self.cost_tracker.record_usage(
                tenant_id=req.tenant_id,
                provider=provider,
                model=model,
                usage=usage,
                cost=cost,
                latency_ms=latency_ms,
                status="success",
                trace_id=req.trace_id,
                route_mode=route_mode,
            )
            self._record_audit(
                req=req,
                status="success",
                provider=provider,
                redaction_applied=redaction.hit_count > 0,
                sensitive_hit_count=redaction.hit_count,
                policy_decision=decision.policy_decision,
                detail_extra={
                    "latency_ms": latency_ms,
                    "fallback_from_local": bool(fallback_from_local),
                },
            )
            record_llm_request(
                provider=provider,
                route_mode=route_mode,
                status="success",
                latency_seconds=max(0.0, (time.time() - started)),
            )
            return DispatchResponse(
                success=True,
                text=text,
                provider=provider,
                model=model,
                route_mode=route_mode,  # type: ignore[arg-type]
                trace_id=req.trace_id,
                latency_ms=latency_ms,
                confidence=self._estimate_confidence(text),
                usage=usage,
                cost=cost,
                redaction_applied=redaction.hit_count > 0,
                sensitive_hit_count=redaction.hit_count,
                redaction_categories=redaction.categories,
                policy_decision=decision.policy_decision,
            )
        except Exception as exc:
            latency_ms = int((time.time() - started) * 1000)
            error_message = str(exc)
            logger.warning("Cloud LLM generation failed: %s", error_message)
            record_llm_request(
                provider=provider,
                route_mode=route_mode,
                status="error",
                latency_seconds=max(0.0, (time.time() - started)),
            )
            self._record_audit(
                req=req,
                status="error",
                provider=provider,
                redaction_applied=redaction.hit_count > 0,
                sensitive_hit_count=redaction.hit_count,
                policy_decision="cloud_error",
                detail_extra={"error": error_message},
            )

            if route_mode == "hybrid_auto" and settings.fallback_on_error:
                record_llm_fallback(reason="cloud_error")
                if fallback_from_local is not None:
                    return fallback_from_local

            return DispatchResponse(
                success=False,
                text="I'm sorry, I'm unable to generate a response at this time. Please try again later.",
                provider=provider,
                model=model,
                route_mode=route_mode,  # type: ignore[arg-type]
                trace_id=req.trace_id,
                latency_ms=latency_ms,
                confidence=0.0,
                usage=UsageStats(),
                cost=CostStats(),
                redaction_applied=redaction.hit_count > 0,
                sensitive_hit_count=redaction.hit_count,
                redaction_categories=redaction.categories,
                policy_decision="cloud_error",
                error=error_message,
            )


_dispatch_service: Optional[DispatchService] = None
_dispatch_service_lock = threading.Lock()


def get_dispatch_service() -> DispatchService:
    global _dispatch_service
    if _dispatch_service is None:
        with _dispatch_service_lock:
            if _dispatch_service is None:
                _dispatch_service = DispatchService()
    return _dispatch_service
