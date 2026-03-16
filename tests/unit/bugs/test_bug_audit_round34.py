"""TDI Round 34 regression tests.

Focus: subscript/container callable indirection bypass in code validator.
"""

from backend.services.code_executor.validator import validate_code


class TestR34_ValidatorSubscriptIndirectionBypass:
    """Blocked callables must not be executable through subscript indirection."""

    def test_dict_subscript_eval_assignment_is_blocked(self):
        code = "d = {}\nd['x'] = eval\nd['x']('1+1')"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "Assigning eval into a dictionary slot and calling it via subscript "
            "should be blocked."
        )

    def test_alias_in_list_subscript_call_is_blocked(self):
        code = "f = eval\na = [f]\na[0]('1+1')"
        result = validate_code(code, strict_mode=True)
        assert (
            not result.is_valid
        ), "Calling aliased eval through list subscript should be blocked."

    def test_list_comprehension_subscript_call_is_blocked(self):
        code = "f = eval\n[g for g in [f]][0]('1+1')"
        result = validate_code(code, strict_mode=True)
        assert not result.is_valid, (
            "List-comprehension subscript indirection should not bypass blocked "
            "callable checks."
        )
