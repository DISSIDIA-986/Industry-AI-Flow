"""BUG-3 (High): DANGEROUS_PATTERNS regex r"__.*__" blocks valid Python code.

The `CodeValidator.DANGEROUS_PATTERNS` list includes `r"__.*__"` which is
intended to block dunder method introspection.  However, this regex also
blocks perfectly valid Python constructs like:

- `if __name__ == "__main__":` (standard guard)
- String literals containing dunder references
- Documentation strings mentioning dunder methods

This test asserts that valid code using `__name__` is NOT rejected by the
validator.  It should FAIL until the regex is refined.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestBug3DunderRegexOverlyAggressive:

    def test_name_main_guard_should_pass_validation(self, sample_code_with_dunder):
        """Standard `if __name__ == '__main__':` guard should pass validation."""
        from backend.services.code_executor.validator import validate_code

        result = validate_code(sample_code_with_dunder, strict_mode=True)

        assert result.is_valid, (
            f"BUG-3: Valid code with `if __name__ == '__main__':` was rejected "
            f"by the validator due to overly aggressive dunder regex. "
            f"Error: {result.error}"
        )

    def test_dataframe_len_should_pass_validation(self):
        """Code using len(df) should pass — `__len__` is used internally but
        the user code doesn't explicitly reference dunders."""
        from backend.services.code_executor.validator import validate_code

        code = (
            "import pandas as pd\n"
            "df = pd.read_csv('data.csv')\n"
            "print(f'Rows: {len(df)}')\n"
        )

        result = validate_code(code, strict_mode=True)

        # This should pass — len() is a builtin, no dunder usage.
        # But the regex r"__.*__" may match string representations in
        # error messages or comments.
        assert result.is_valid, (
            f"BUG-3: Valid code using len(df) was rejected. Error: {result.error}"
        )

    def test_string_containing_dunder_in_print_should_pass(self):
        """A print statement mentioning __init__ in a string should not be blocked."""
        from backend.services.code_executor.validator import validate_code

        code = (
            "import pandas as pd\n"
            "print('The __init__ method is called on construction')\n"
        )

        result = validate_code(code, strict_mode=True)

        assert result.is_valid, (
            f"BUG-3: String literal containing '__init__' was falsely "
            f"flagged as dangerous. Error: {result.error}"
        )
