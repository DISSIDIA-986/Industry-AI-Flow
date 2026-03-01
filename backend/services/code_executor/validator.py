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
        "codecs",
        "builtins",
        "types",
        "gc",
        "inspect",
        "atexit",
        "_thread",
        "_io",
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
        "warnings",
    }

    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        r"\.(__class__|__subclasses__|__globals__|__builtins__|__import__|__loader__|__spec__|__getattribute__|__mro__|__bases__|__init__|__dict__|__reduce__|__reduce_ex__|__del__|__getattr__|__setattr__|__delattr__|__init_subclass__|__set_name__|__prepare__|__self__)\b",  # Dangerous dunder attribute access
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
        "chr",
        "bytes",
        "bytearray",
    }
    BLOCKED_ATTRIBUTE_CALLS = {
        ("builtins", "open"),
        ("os", "system"),
        ("os", "popen"),
        ("subprocess", "popen"),
        ("subprocess", "run"),
        ("subprocess", "call"),
        # Whitelisted-library methods that can execute arbitrary code
        ("pd", "eval"),
        ("pandas", "eval"),
        ("np", "load"),
        ("numpy", "load"),
        ("pd", "read_pickle"),
        ("pandas", "read_pickle"),
    }

    # Attribute calls blocked on any object (e.g., df.query(), df.eval())
    BLOCKED_METHOD_NAMES = {
        "query",  # DataFrame.query() evaluates arbitrary expressions
        "eval",   # DataFrame.eval() evaluates arbitrary expressions
        "pipe",   # DataFrame.pipe() passes arbitrary callables
        "apply",  # DataFrame.apply() runs arbitrary functions per element
        "agg",    # DataFrame.agg() accepts arbitrary callables
        "transform",  # DataFrame.transform() accepts arbitrary callables
        "map",    # Series.map() accepts arbitrary callables
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

        # Check for dangerous dunder method definitions (metaclass/descriptor hooks
        # that execute at class definition time, not at call time).
        dangerous_dunder_defs = {
            "__init_subclass__",
            "__set_name__",
            "__prepare__",
            "__reduce__",
            "__reduce_ex__",
        }
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in dangerous_dunder_defs:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Dangerous metaclass/descriptor hook: {node.name}",
                    )

        # Check f-string expressions for dangerous calls (ast.JoinedStr / FormattedValue)
        fstring_result = self._validate_fstring_expressions(tree)
        if not fstring_result.is_valid:
            return fstring_result

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
        blocked_methods = {name.lower() for name in self.BLOCKED_METHOD_NAMES}
        alias_names: set[str] = set()
        alias_attribute_names: set[str] = set()

        def _find_blocked_callable_reference(expr: ast.AST) -> Optional[str]:
            """Detect blocked callables passed around as first-class values."""
            for child in ast.walk(expr):
                if isinstance(child, ast.Name):
                    candidate = child.id.lower()
                    if candidate in blocked_names or candidate in alias_names:
                        return child.id
                if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
                    base = child.value.id.lower()
                    attr = child.attr.lower()
                    if (base, attr) in blocked_attr_calls:
                        return f"{child.value.id}.{child.attr}"
            return None

        # Block references to blocked names inside containers (lists, dicts, tuples, sets).
        # Patterns like [exec][0](...) or {"e": exec}["e"](...) hide blocked
        # functions inside data structures to bypass direct-call detection.
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "__builtins__":
                return ValidationResult(
                    is_valid=False,
                    error="Blocked builtin namespace access: __builtins__",
                )

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

            if isinstance(node, ast.Lambda):
                for child in ast.walk(node.body):
                    if isinstance(child, ast.Name) and child.id.lower() in blocked_names:
                        return ValidationResult(
                            is_valid=False,
                            error=f"Blocked function reference in lambda: {child.id}",
                        )

        # Block blocked callables hidden in default arguments
        # (e.g., def run(fn=eval): ...).
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            defaults = list(node.args.defaults) + [
                kw for kw in node.args.kw_defaults if kw is not None
            ]
            for default_value in defaults:
                blocked_ref = _find_blocked_callable_reference(default_value)
                if blocked_ref:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Blocked callable in default argument: {blocked_ref}",
                    )

        # Track aliases created from blocked callable references, including
        # expression-based assignments (ifexp/boolop/etc.).
        def _record_alias_from_assignment(target: ast.AST, value: ast.AST) -> bool:
            blocked_ref = _find_blocked_callable_reference(value)
            if not blocked_ref:
                return False
            if isinstance(target, ast.Name):
                key = target.id.lower()
                if key not in alias_names:
                    alias_names.add(key)
                    return True
            if isinstance(target, ast.Attribute):
                key = target.attr.lower()
                if key not in alias_attribute_names:
                    alias_attribute_names.add(key)
                    return True
            return False

        changed = True
        while changed:
            changed = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    if len(node.targets) != 1:
                        continue
                    if _record_alias_from_assignment(node.targets[0], node.value):
                        changed = True
                elif isinstance(node, ast.AnnAssign):
                    if node.value is None:
                        continue
                    if _record_alias_from_assignment(node.target, node.value):
                        changed = True

        for node in ast.walk(tree):
            # Track walrus operator aliases: (fn := exec) creates a NamedExpr
            if isinstance(node, ast.NamedExpr):
                blocked_ref = _find_blocked_callable_reference(node.value)
                if blocked_ref:
                    target_name = (
                        node.target.id
                        if isinstance(node.target, ast.Name)
                        else getattr(node.target, "attr", "<expr>")
                    )
                    return ValidationResult(
                        is_valid=False,
                        error=(
                            "Blocked function alias via walrus operator: "
                            f"{target_name} := {blocked_ref}"
                        ),
                    )

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

            # Block blocked callables passed as arguments/kwargs to higher-order
            # functions (e.g., map(eval, ...), sorted(..., key=eval)).
            argument_nodes = list(node.args) + [
                kw.value for kw in node.keywords if kw.value is not None
            ]
            for arg_node in argument_nodes:
                blocked_ref = _find_blocked_callable_reference(arg_node)
                if blocked_ref:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Blocked callable reference passed as argument: {blocked_ref}",
                    )

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

            if isinstance(node.func, ast.Attribute):
                attr = node.func.attr.lower()
                if attr in blocked_names:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Blocked function call via attribute: .{node.func.attr}",
                    )
                if attr in alias_names or attr in alias_attribute_names:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Blocked function call via attribute alias: .{node.func.attr}",
                    )
                # Block dangerous method calls on any object (e.g., df.query(), df.eval())
                if attr in blocked_methods:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Blocked method call: .{node.func.attr}()",
                    )
                if isinstance(node.func.value, ast.Name):
                    base = node.func.value.id.lower()
                    if (base, attr) in blocked_attr_calls:
                        return ValidationResult(
                            is_valid=False,
                            error=f"Blocked function call: {node.func.value.id}.{node.func.attr}",
                        )

        return ValidationResult(is_valid=True)

    def _validate_fstring_expressions(self, tree: ast.AST) -> ValidationResult:
        """Validate that f-string expressions don't contain dangerous calls."""
        blocked_names = {name.lower() for name in self.BLOCKED_CALL_NAMES}
        for node in ast.walk(tree):
            if not isinstance(node, ast.JoinedStr):
                continue
            # Walk all sub-expressions inside the f-string
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if isinstance(func, ast.Name) and func.id.lower() in blocked_names:
                        return ValidationResult(
                            is_valid=False,
                            error=f"Blocked call inside f-string: {func.id}",
                        )
                    if isinstance(func, ast.Attribute):
                        attr = func.attr.lower()
                        if attr in {m.lower() for m in self.BLOCKED_METHOD_NAMES}:
                            return ValidationResult(
                                is_valid=False,
                                error=f"Blocked method call inside f-string: .{func.attr}()",
                            )
                        if isinstance(func.value, ast.Name):
                            base = func.value.id.lower()
                            if (base, attr) in {
                                (b.lower(), a.lower()) for b, a in self.BLOCKED_ATTRIBUTE_CALLS
                            }:
                                return ValidationResult(
                                    is_valid=False,
                                    error=f"Blocked call inside f-string: {func.value.id}.{func.attr}",
                                )
        return ValidationResult(is_valid=True)

    def _check_loops(self, tree: ast.AST) -> Optional[str]:
        """Check for potential infinite loops (basic heuristic)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                # Check if condition is a truthy constant (True, 1, non-zero int, etc.)
                if isinstance(node.test, ast.Constant) and node.test.value:
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
