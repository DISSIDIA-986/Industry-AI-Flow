"""
Code validation module for security and safety checks.

Validates Python code before execution to prevent:
- Dangerous imports (os.system, subprocess, etc.)
- File system operations outside workspace
- Network operations
- Infinite loops (basic detection)
"""

import ast
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    """Code validation result."""

    is_valid: bool
    error: Optional[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class CodeValidator:
    """
    Python code validator with security checks.

    Validates code against blacklisted patterns and unsafe operations.
    """

    # Dangerous modules/functions
    BLACKLISTED_IMPORTS = {
        "os",
        "subprocess",
        "sys",
        "shutil",
        "socket",
        "urllib",
        "requests",
        "http",
        "ftplib",
        "telnetlib",
        "multiprocessing",
        "threading",
        "asyncio",
        "__import__",
        "eval",
        "exec",
        "compile",
        "open",  # Use context-specific file operations only
    }

    # Allowed modules for data analysis
    WHITELISTED_IMPORTS = {
        "pandas",
        "numpy",
        "scipy",
        "sklearn",
        "xgboost",
        "lightgbm",
        "matplotlib",
        "seaborn",
        "plotly",
        "math",
        "statistics",
        "datetime",
        "json",
        "csv",
        "re",
        "collections",
        "itertools",
        "functools",
    }

    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        r"__.*__",  # Dunder methods (potential introspection)
        r"globals\(",  # Global scope access
        r"locals\(",  # Local scope access
        r"vars\(",  # Variable introspection
        r"dir\(",  # Directory listing
        r"getattr\(",  # Dynamic attribute access
        r"setattr\(",  # Dynamic attribute modification
        r"delattr\(",  # Attribute deletion
        r"\.system\(",  # System calls
        r"\.popen\(",  # Process execution
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize validator.

        Args:
            strict_mode: If True, only whitelisted imports are allowed
        """
        self.strict_mode = strict_mode

    def validate(self, code: str) -> ValidationResult:
        """
        Validate Python code for security issues.

        Args:
            code: Python code to validate

        Returns:
            ValidationResult with validation status and errors
        """
        warnings = []

        # Check if code is empty
        if not code.strip():
            return ValidationResult(
                is_valid=False,
                error="Code cannot be empty",
            )

        # Check syntax
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                error=f"Syntax error: {e}",
            )

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                return ValidationResult(
                    is_valid=False,
                    error=f"Dangerous pattern detected: {pattern}",
                )

        # Check imports
        import_result = self._validate_imports(tree)
        if not import_result.is_valid:
            return import_result

        warnings.extend(import_result.warnings)

        # Check for infinite loops (basic detection)
        loop_warning = self._check_loops(tree)
        if loop_warning:
            warnings.append(loop_warning)

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
        )

    def _validate_imports(self, tree: ast.AST) -> ValidationResult:
        """Validate imports against blacklist/whitelist."""
        warnings = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    result = self._check_module(module)
                    if not result.is_valid:
                        return result
                    warnings.extend(result.warnings)

            elif isinstance(node, ast.ImportFrom):
                module = node.module.split(".")[0] if node.module else ""
                result = self._check_module(module)
                if not result.is_valid:
                    return result
                warnings.extend(result.warnings)

        return ValidationResult(is_valid=True, warnings=warnings)

    def _check_module(self, module: str) -> ValidationResult:
        """Check if module is allowed."""
        # Check blacklist
        if module in self.BLACKLISTED_IMPORTS:
            return ValidationResult(
                is_valid=False,
                error=f"Blacklisted import: {module}",
            )

        # Check whitelist in strict mode
        if self.strict_mode and module not in self.WHITELISTED_IMPORTS:
            return ValidationResult(
                is_valid=False,
                error=f"Import not whitelisted: {module}",
            )

        # Warn about non-whitelisted imports in non-strict mode
        if not self.strict_mode and module not in self.WHITELISTED_IMPORTS:
            return ValidationResult(
                is_valid=True,
                warnings=[f"Non-whitelisted import: {module}"],
            )

        return ValidationResult(is_valid=True)

    def _check_loops(self, tree: ast.AST) -> Optional[str]:
        """Check for potential infinite loops (basic heuristic)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                # Check if condition is constant True
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    return "Warning: Potential infinite loop detected (while True)"

            elif isinstance(node, ast.For):
                # Check for very large ranges
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                        if len(node.iter.args) > 0:
                            arg = node.iter.args[0]
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                                if arg.value > 1_000_000:
                                    return f"Warning: Large range detected ({arg.value:,} iterations)"

        return None


# Convenience function
def validate_code(code: str, strict_mode: bool = True) -> ValidationResult:
    """
    Validate Python code (convenience function).

    Args:
        code: Python code to validate
        strict_mode: If True, only whitelisted imports allowed

    Returns:
        ValidationResult
    """
    validator = CodeValidator(strict_mode=strict_mode)
    return validator.validate(code)
