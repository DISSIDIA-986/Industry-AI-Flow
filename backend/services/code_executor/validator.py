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
        "importlib",
        "ctypes",
        "code",
        "pty",
        "signal",
        "pathlib",
        "pickle",
        "shelve",
        "webbrowser",
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
        "warnings",
    }

    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        r"\.(__class__|__subclasses__|__globals__|__builtins__|__import__|__loader__|__spec__)\b",  # Dangerous dunder attribute access
        r"globals\s*\(",  # Global scope access
        r"locals\s*\(",  # Local scope access
        r"vars\s*\(",  # Variable introspection
        r"dir\s*\(",  # Directory listing
        r"getattr\s*\(",  # Dynamic attribute access
        r"setattr\s*\(",  # Dynamic attribute modification
        r"delattr\s*\(",  # Attribute deletion
        r"\.system\s*\(",  # System calls
        r"\.popen\s*\(",  # Process execution
        r"\bbreakpoint\s*\(",  # Debugger invocation
    ]

    BLOCKED_CALL_NAMES = {
        "open",
        "eval",
        "exec",
        "compile",
        "__import__",
        "input",
        "raw_input",
        "breakpoint",
    }
    BLOCKED_ATTRIBUTE_CALLS = {
        ("builtins", "open"),
        ("os", "system"),
        ("os", "popen"),
        ("subprocess", "popen"),
        ("subprocess", "run"),
        ("subprocess", "call"),
    }

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

        # Check blocked calls (including aliased calls).
        call_result = self._validate_blocked_calls(tree)
        if not call_result.is_valid:
            return call_result

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

    def _validate_blocked_calls(self, tree: ast.AST) -> ValidationResult:
        """Validate dangerous function calls, including simple aliases and container indirection."""
        blocked_attr_calls = {
            (base.lower(), attr.lower()) for base, attr in self.BLOCKED_ATTRIBUTE_CALLS
        }
        blocked_names = {name.lower() for name in self.BLOCKED_CALL_NAMES}
        alias_names: set[str] = set()

        # Block references to blocked names inside containers (lists, dicts, tuples, sets).
        # Patterns like [exec][0](...) or {"e": exec}["e"](...) hide blocked
        # functions inside data structures to bypass direct-call detection.
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id.lower() in blocked_names:
                # Allow import-target names (handled by _validate_imports)
                # but block references inside containers or subscripts
                # We check all Name nodes — any bare reference to a blocked
                # builtin (exec, eval, compile, etc.) is suspicious
                # except when it appears as a direct call (handled below)
                pass  # Direct call checks below handle ast.Call cases

            # Detect blocked names inside List, Dict, Tuple, Set literals
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                for elt in node.elts:
                    if isinstance(elt, ast.Name) and elt.id.lower() in blocked_names:
                        return ValidationResult(
                            is_valid=False,
                            error=f"Blocked function reference in container: {elt.id}",
                        )
            if isinstance(node, ast.Dict):
                for val in node.values:
                    if isinstance(val, ast.Name) and val.id.lower() in blocked_names:
                        return ValidationResult(
                            is_valid=False,
                            error=f"Blocked function reference in dict: {val.id}",
                        )

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue

            if isinstance(node.value, ast.Name):
                if node.value.id.lower() in blocked_names:
                    alias_names.add(target.id.lower())
                continue

            if isinstance(node.value, ast.Attribute) and isinstance(
                node.value.value, ast.Name
            ):
                base = node.value.value.id.lower()
                attr = node.value.attr.lower()
                if (base, attr) in blocked_attr_calls:
                    alias_names.add(target.id.lower())

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if isinstance(node.func, ast.Name):
                func_name = node.func.id.lower()
                if func_name in blocked_names or func_name in alias_names:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Blocked function call: {node.func.id}",
                    )
                # Block type() used as metaclass constructor (3-arg form)
                if func_name == "type" and len(node.args) >= 3:
                    return ValidationResult(
                        is_valid=False,
                        error="Blocked function call: type() metaclass creation",
                    )
                continue

            if isinstance(node.func, ast.Attribute) and isinstance(
                node.func.value, ast.Name
            ):
                base = node.func.value.id.lower()
                attr = node.func.attr.lower()
                if (base, attr) in blocked_attr_calls:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Blocked function call: {node.func.value.id}.{node.func.attr}",
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
                    if (
                        isinstance(node.iter.func, ast.Name)
                        and node.iter.func.id == "range"
                    ):
                        if len(node.iter.args) > 0:
                            arg = node.iter.args[0]
                            if isinstance(arg, ast.Constant) and isinstance(
                                arg.value, int
                            ):
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
