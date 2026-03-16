"""TDI Round 32 regression tests.

Focus: __builtins__ namespace access bypass in code validator.
"""

from backend.services.code_executor.validator import validate_code


class TestR32_ValidatorBuiltinsNamespaceBypass:
    """Blocked callables must not be reachable via __builtins__ lookups."""

    def test_builtins_subscript_eval_is_blocked(self):
        code = "__builtins__['eval']('1+1')"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "__builtins__ subscript lookup should be blocked because it can "
            "recover blocked callables like eval/exec."
        )

    def test_builtins_subscript_exec_is_blocked(self):
        code = "__builtins__['exec']('a=1')"
        result = validate_code(code, strict_mode=True)
        assert (
            not result.is_valid
        ), "__builtins__ subscript lookup should block exec recovery paths."

    def test_builtins_getitem_eval_is_blocked(self):
        code = "__builtins__.__getitem__('eval')('1+1')"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, "__builtins__.__getitem__ access should be blocked."
