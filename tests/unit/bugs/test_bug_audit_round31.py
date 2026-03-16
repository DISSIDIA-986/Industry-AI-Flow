"""TDI Round 31 regression tests.

Focus: indirect callable-alias bypasses in code validator.
"""

from backend.services.code_executor.validator import validate_code


class TestR31_ValidatorIndirectAliasBypass:
    """Blocked callables must not be reachable via indirect alias expressions."""

    def test_ifexp_alias_to_eval_is_blocked(self):
        code = "fn = eval if True else print\nfn('1+1')"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "Alias built from conditional expression should be blocked when it "
            "references eval."
        )

    def test_default_argument_eval_is_blocked(self):
        code = "def run(fn=eval):\n    return fn('1+1')\nrun()"
        result = validate_code(code, strict_mode=True)
        assert (
            not result.is_valid
        ), "Function default arguments must not carry blocked callables like eval."

    def test_class_attribute_alias_eval_is_blocked(self):
        code = "class X:\n    fn = eval\nX.fn('1+1')"
        result = validate_code(code, strict_mode=True)
        assert (
            not result.is_valid
        ), "Class attribute aliases to blocked callables should be rejected."
