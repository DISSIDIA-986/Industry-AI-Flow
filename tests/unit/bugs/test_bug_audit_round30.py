"""TDI Round 30 regression tests.

Focus: code validator callable-reference bypasses.
"""

from backend.services.code_executor.validator import validate_code


class TestR30_ValidatorCallableReferenceBypass:
    """Blocked callables must not pass through as higher-order arguments."""

    def test_map_eval_reference_is_blocked(self):
        code = "list(map(eval, ['1+1']))"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "map(eval, ...) should be blocked. Passing a blocked callable as "
            "an argument bypasses direct-call checks."
        )

    def test_sorted_key_eval_reference_is_blocked(self):
        code = "sorted([1, 2, 3], key=eval)"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "sorted(..., key=eval) should be blocked. Keyword callable "
            "arguments must be validated."
        )

    def test_lambda_receiving_eval_reference_is_blocked(self):
        code = "(lambda fn: fn('1+1'))(eval)"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "Passing eval into a lambda should be blocked. Higher-order "
            "callable references are executable code paths."
        )
