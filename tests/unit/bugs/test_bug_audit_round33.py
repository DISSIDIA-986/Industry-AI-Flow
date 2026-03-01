"""TDI Round 33 regression tests.

Focus: builtins access via callable.__self__ in code validator.
"""

from backend.services.code_executor.validator import validate_code


class TestR33_ValidatorSelfBoundBuiltinsBypass:
    """Blocked callables must not be reachable via builtin function __self__."""

    def test_print_self_open_is_blocked(self):
        code = "print.__self__.open('/etc/passwd').read()"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "print.__self__.open(...) should be blocked; it bypasses direct "
            "open()/import restrictions by pivoting through builtins."
        )

    def test_abs_self_exec_is_blocked(self):
        code = "abs.__self__.exec('a=1')"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "abs.__self__.exec(...) should be blocked; builtins __self__ "
            "access re-exposes blocked exec."
        )
