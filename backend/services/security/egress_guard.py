"""Outbound policy checks for cloud LLM requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .redaction_service import RedactionResult, RedactionService


@dataclass
class EgressDecision:
    allowed: bool
    policy_decision: str
    reason: Optional[str] = None


class EgressGuard:
    """Ensures outbound text is redacted before cloud dispatch."""

    def __init__(self, redactor: Optional[RedactionService] = None) -> None:
        self.redactor = redactor or RedactionService()

    def evaluate(
        self,
        original_text: str,
        redacted_text: str,
        redaction_result: Optional[RedactionResult] = None,
    ) -> EgressDecision:
        if not redacted_text:
            return EgressDecision(
                allowed=False, policy_decision="block", reason="empty_payload"
            )

        if (
            original_text == redacted_text
            and redaction_result
            and redaction_result.hit_count > 0
        ):
            # Defensive check: redaction statistics says there were hits, but payload is unchanged.
            return EgressDecision(
                allowed=False,
                policy_decision="block",
                reason="redaction_inconsistent",
            )

        # Re-scan outbound payload. Any remaining sensitive token gets blocked.
        residual = self.redactor.redact(redacted_text)
        if residual.hit_count > 0:
            return EgressDecision(
                allowed=False,
                policy_decision="block",
                reason="residual_sensitive_data",
            )

        return EgressDecision(allowed=True, policy_decision="allow")
