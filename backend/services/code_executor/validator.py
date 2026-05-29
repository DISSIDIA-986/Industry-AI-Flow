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
        "statsmodels",
        # NOTE: xgboost/lightgbm are intentionally NOT whitelisted. They are not
        # installed in the E2B sandbox (only `statsmodels` is bootstrapped), so
        # whitelisting them produced a runtime ModuleNotFoundError that the repair
        # round silently rewrote to sklearn — the user asked for XGBoost and got
        # sklearn with no disclosure. Fail-fast at validation instead; sklearn's
        # GradientBoosting* covers the gradient-boosting capability. Re-add only
        # if these are preinstalled in the sandbox image. See
        # docs/data_analysis_ml_adversarial_review.md §4 (2026-05-29).
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
        # `random` is required by the random_state=42 mandate in the agentic
        # user/repair prompts (PR #35). The prompt instructs LLM to seed
        # `np.random.seed(42); random.seed(42)`; without `random` in the
        # whitelist, every agentic round-1 with that header gets rejected
        # ("Import not whitelisted: random"). Pure stdlib, no IO.
        "random",
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

    # I/O-safety policy (enterprise hardening, 2026-05-29 adversarial review).
    # The sandbox is the real boundary, but allowed-library APIs must not silently
    # read local files, fetch URLs, or write outside the workspace.
    _WORKSPACE_ROOT = "/workspace"
    _URL_PREFIXES = (
        "http://", "https://", "ftp://", "ftps://",
        "s3://", "gs://", "gcs://", "file://", "//",
    )
    # Funcs whose path/URL argument (by positional index) must stay workspace-local.
    # Covers pandas readers, numpy/scipy/image I/O, and matplotlib savefig.
    _PATH_ARG_FUNCS = {
        "read_csv": 0, "read_table": 0, "read_fwf": 0, "read_excel": 0,
        "read_json": 0, "read_html": 0, "read_xml": 0, "read_parquet": 0,
        "read_feather": 0, "read_orc": 0, "read_sas": 0, "read_stata": 0,
        "read_spss": 0, "fromfile": 0, "genfromtxt": 0, "loadtxt": 0,
        "savetxt": 0, "savefig": 0, "imread": 0, "imsave": 0, "to_csv": 0,
    }
    # Funcs blocked outright regardless of args (network / deserialization / no
    # legitimate use in this metadata-only analysis pipeline).
    _BLOCKED_IO_FUNCS = {
        "fromfile",      # np.fromfile — raw local read (also path-checked above)
        "loadmat",       # scipy.io.loadmat — deserialization gadget
        "savemat",       # scipy.io.savemat
        "load",          # numpy.load (alias-resistant; see _validate_io_safety)
    }

    # Compute-budget policy (enterprise reliability, 2026-05-29 review). Heavy
    # hyperparameter search hangs the live demo (GridSearchCV with a large grid
    # blew past the 120s budget and returned nothing). Reject provably-oversized
    # search up front so it fails fast (instant) and the repair round can shrink
    # it, instead of a 2-minute wall. Non-literal grids fall through to the
    # runtime timeout + durable-result safety net.
    _MAX_MODEL_FITS = 200       # grid_size × cv ceiling
    _MAX_CV_FOLDS = 20
    _MAX_N_ESTIMATORS = 2000
    _SEARCH_FUNCS = {
        "gridsearchcv", "randomizedsearchcv",
        "halvinggridsearchcv", "halvingrandomsearchcv",
    }

    # Attribute calls blocked on any object (e.g., df.query(), df.eval())
    BLOCKED_METHOD_NAMES = {
        "query",  # DataFrame.query() evaluates arbitrary expressions
        "eval",  # DataFrame.eval() evaluates arbitrary expressions
        "pipe",  # DataFrame.pipe() passes arbitrary callables
        "apply",  # DataFrame.apply() runs arbitrary functions per element
        "agg",  # DataFrame.agg() accepts arbitrary callables
        "transform",  # DataFrame.transform() accepts arbitrary callables
        "map",  # Series.map() accepts arbitrary callables
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

        # Check I/O safety: workspace-local paths only, no URLs, no network
        # fetchers or deserialization gadgets (alias-resistant).
        io_result = self._validate_io_safety(tree)
        if not io_result.is_valid:
            return io_result

        # Check compute budget: reject provably-oversized hyperparameter search
        # so heavy jobs fail fast instead of hanging past the time budget.
        compute_result = self._validate_compute_budget(tree)
        if not compute_result.is_valid:
            return compute_result

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
        def _call_passes_callable_arg(node: ast.Call) -> bool:
            """True iff this Call passes a Lambda (or callable-typed
            expression) as a positional or keyword argument.

            This is the ACTUAL danger signal for `.transform()` — a
            pandas Series/DataFrame/GroupBy `.transform(lambda x: ...)`
            runs arbitrary Python, while `.transform("mean")` (string
            aggregator lookup) and `scaler.transform(X)` (sklearn data
            arg) are safe. The prior heuristic ("receiver chain has
            .groupby()") missed aliased groupby objects AND blocked
            nothing for direct Series/DataFrame.transform(lambda) —
            both confirmed bypasses per Codex adversarial review 2026-04-19.
            """
            for arg in node.args:
                if isinstance(arg, ast.Lambda):
                    return True
            for kw in node.keywords:
                if isinstance(kw.value, ast.Lambda):
                    return True
            return False


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
                if isinstance(child, ast.Attribute) and isinstance(
                    child.value, ast.Name
                ):
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
                    if (
                        isinstance(child, ast.Name)
                        and child.id.lower() in blocked_names
                    ):
                        return ValidationResult(
                            is_valid=False,
                            error=f"Blocked function reference in lambda: {child.id}",
                        )

        # Block blocked callables hidden in default arguments
        # (e.g., def run(fn=eval): ...).
        for node in ast.walk(tree):
            if not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
            ):
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
                    # Block assigning blocked callables into container slots
                    # (e.g., d['x'] = eval) because later subscript calls can
                    # execute them while bypassing Name/Attribute call checks.
                    if any(isinstance(t, ast.Subscript) for t in node.targets):
                        blocked_ref = _find_blocked_callable_reference(node.value)
                        if blocked_ref:
                            return ValidationResult(
                                is_valid=False,
                                error=(
                                    "Blocked callable assigned via subscript target: "
                                    f"{blocked_ref}"
                                ),
                            )
                    if len(node.targets) != 1:
                        continue
                    if _record_alias_from_assignment(node.targets[0], node.value):
                        changed = True
                elif isinstance(node, ast.AnnAssign):
                    if node.value is None:
                        continue
                    if isinstance(node.target, ast.Subscript):
                        blocked_ref = _find_blocked_callable_reference(node.value)
                        if blocked_ref:
                            return ValidationResult(
                                is_valid=False,
                                error=(
                                    "Blocked callable assigned via subscript target: "
                                    f"{blocked_ref}"
                                ),
                            )
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

            if isinstance(node.func, ast.Subscript):
                blocked_ref = _find_blocked_callable_reference(node.func)
                if blocked_ref:
                    return ValidationResult(
                        is_valid=False,
                        error=(
                            "Blocked function call via subscript expression: "
                            f"{blocked_ref}"
                        ),
                    )

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
                    # Narrow exception: `.transform()` is overloaded across
                    # pandas (dangerous when given a lambda) and sklearn
                    # (always data-arg based — StandardScaler, LabelEncoder,
                    # Pipeline, ColumnTransformer). The ACTUAL danger
                    # signal is a callable (Lambda) argument, not the
                    # receiver chain. The prior groupby-chain heuristic
                    # missed aliased groupby AND direct Series.transform
                    # (Codex adversarial review 2026-04-19).
                    if attr == "transform" and not _call_passes_callable_arg(node):
                        continue
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

    @staticmethod
    def _dotted_base(node: ast.AST) -> Optional[str]:
        """Return the dotted module path for an attribute/name chain, else None.

        e.g. ``scipy.io`` for ``scipy.io.loadmat`` (the func node's `.value`),
        ``np`` for ``np.fromfile``.
        """
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return None

    def _path_violation(self, path: str) -> Optional[str]:
        """Return a reason string if a literal path/URL escapes the workspace."""
        s = path.strip()
        low = s.lower()
        if any(low.startswith(pre) for pre in self._URL_PREFIXES):
            return "URL / network location"
        if ".." in s.replace("\\", "/").split("/"):
            return "parent-directory escape"
        if s.startswith("/") or (len(s) > 1 and s[1] == ":"):  # POSIX abs or Windows drive
            if not (s == self._WORKSPACE_ROOT or s.startswith(self._WORKSPACE_ROOT + "/")):
                return "absolute path outside /workspace"
        return None

    def _validate_io_safety(self, tree: ast.AST) -> ValidationResult:
        """Constrain file/URL I/O in allowed libraries.

        - Reject network fetchers (``sklearn.datasets.fetch_*``), deserialization
          gadgets (``scipy.io.loadmat``, ``numpy.load`` including aliased imports),
          and ``np.fromfile``.
        - Reject ``matplotlib.use(...)`` backend switching.
        - Require path/URL arguments to pandas readers, ``savefig``, etc. to be
          workspace-local (``/workspace/...`` or relative) — never a URL or an
          absolute path elsewhere. Only string-literal args are inspected;
          dynamic paths fall through to the sandbox boundary.
        """
        # Build import-alias maps so blocks are alias-resistant.
        from_alias: dict[str, tuple[str, str]] = {}  # local -> (module, orig_name)
        mod_alias: dict[str, str] = {}  # local -> dotted module
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    mod_alias[(a.asname or a.name).split(".")[0]] = a.name
                    if a.asname:
                        mod_alias[a.asname] = a.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for a in node.names:
                    from_alias[a.asname or a.name] = (node.module, a.name)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            funcname: Optional[str] = None
            module: Optional[str] = None
            if isinstance(func, ast.Name):
                if func.id in from_alias:
                    module, funcname = from_alias[func.id]
                else:
                    funcname = func.id
            elif isinstance(func, ast.Attribute):
                funcname = func.attr
                base = self._dotted_base(func.value)
                if base is not None:
                    head = base.split(".")[0]
                    module = mod_alias.get(head, base)
                    if head in from_alias:  # e.g. `from sklearn import datasets`
                        module = from_alias[head][0]
            if not funcname:
                continue
            fn = funcname.lower()
            mod = (module or "").lower()

            # 1. sklearn network fetchers
            if fn.startswith("fetch_") and ("sklearn" in mod or fn in {
                "fetch_openml", "fetch_california_housing", "fetch_20newsgroups",
                "fetch_lfw_people", "fetch_olivetti_faces", "fetch_covtype",
                "fetch_kddcup99", "fetch_rcv1", "fetch_species_distributions",
            }):
                return ValidationResult(
                    is_valid=False,
                    error=f"Blocked network data fetcher: {funcname}",
                )
            # 2. deserialization / raw-read gadgets (alias-resistant)
            if fn in self._BLOCKED_IO_FUNCS:
                # `load` is only dangerous as numpy.load; allow model.load_* etc.
                if fn == "load" and "numpy" not in mod and "np" not in mod:
                    pass
                else:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Blocked I/O gadget: {funcname}",
                    )
            # 4. path/URL argument must be workspace-local
            if fn in self._PATH_ARG_FUNCS:
                idx = self._PATH_ARG_FUNCS[fn]
                if len(node.args) > idx and isinstance(node.args[idx], ast.Constant):
                    val = node.args[idx].value
                    if isinstance(val, str):
                        why = self._path_violation(val)
                        if why:
                            return ValidationResult(
                                is_valid=False,
                                error=f"Blocked I/O path ({why}): {funcname}({val!r})",
                            )
        return ValidationResult(is_valid=True)

    @staticmethod
    def _literal_int(node: Optional[ast.AST]) -> Optional[int]:
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(
            node.value, bool
        ):
            return node.value
        return None

    @staticmethod
    def _grid_product(node: Optional[ast.AST]) -> Optional[int]:
        """Estimate the number of param combinations in a literal param_grid dict.

        Returns None when the grid (or any value list) is not a literal we can
        size statically — caller then leaves it to the runtime timeout.
        """
        if not isinstance(node, ast.Dict):
            return None
        total = 1
        for value in node.values:
            if isinstance(value, (ast.List, ast.Tuple)):
                total *= max(1, len(value.elts))
            else:
                return None
        return total

    def _validate_compute_budget(self, tree: ast.AST) -> ValidationResult:
        """Reject provably-oversized hyperparameter search / model sizing."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute):
                fname = node.func.attr.lower()
            elif isinstance(node.func, ast.Name):
                fname = node.func.id.lower()
            else:
                continue
            kw = {k.arg: k.value for k in node.keywords if k.arg}

            cv_n = self._literal_int(kw.get("cv"))
            if cv_n is not None and cv_n > self._MAX_CV_FOLDS:
                return ValidationResult(
                    is_valid=False,
                    error=(
                        f"compute budget: cv={cv_n} exceeds the {self._MAX_CV_FOLDS}-fold "
                        "limit for live analysis — use a smaller cv"
                    ),
                )
            n_est = self._literal_int(kw.get("n_estimators"))
            if n_est is not None and n_est > self._MAX_N_ESTIMATORS:
                return ValidationResult(
                    is_valid=False,
                    error=(
                        f"compute budget: n_estimators={n_est} exceeds the "
                        f"{self._MAX_N_ESTIMATORS} limit — use fewer estimators"
                    ),
                )

            if fname in self._SEARCH_FUNCS:
                cv = cv_n if cv_n is not None else 5
                if "random" in fname:
                    n_iter = self._literal_int(kw.get("n_iter"))
                    grid = n_iter if n_iter is not None else 10
                else:
                    pg = kw.get("param_grid") or kw.get("param_distributions")
                    if pg is None and len(node.args) >= 2:
                        pg = node.args[1]
                    grid = self._grid_product(pg) if pg is not None else None
                if grid is not None and grid * cv > self._MAX_MODEL_FITS:
                    fits = grid * cv
                    return ValidationResult(
                        is_valid=False,
                        error=(
                            f"compute budget: hyperparameter search would train ~{fits} "
                            f"models ({grid} param combinations x {cv} folds), exceeding "
                            f"the {self._MAX_MODEL_FITS}-fit limit for live analysis. "
                            "Shrink the grid, lower cv, or use RandomizedSearchCV with a "
                            "small n_iter."
                        ),
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
                                (b.lower(), a.lower())
                                for b, a in self.BLOCKED_ATTRIBUTE_CALLS
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
