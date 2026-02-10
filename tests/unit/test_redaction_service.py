"""Unit tests for redaction + egress policy checks."""

from __future__ import annotations

from backend.services.security.egress_guard import EgressGuard
from backend.services.security.redaction_service import RedactionService


def test_redaction_masks_sensitive_patterns():
    redactor = RedactionService()
    raw = "Email a@b.com or call +1 415-555-1212, server 10.2.3.4"
    result = redactor.redact(raw)

    assert result.hit_count >= 3
    assert "<REDACTED_EMAIL>" in result.text
    assert "<REDACTED_PHONE_US>" in result.text
    assert "<REDACTED_IPV4>" in result.text


def test_egress_guard_allows_sanitized_payload():
    redactor = RedactionService()
    guard = EgressGuard(redactor)
    raw = "Please contact foo@example.com for details."
    redacted = redactor.redact(raw)
    decision = guard.evaluate(raw, redacted.text, redacted)
    assert decision.allowed is True
    assert decision.policy_decision == "allow"
