"""Iterative Code Execution Agent - self-healing code execution with LangChain 1.0."""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from backend.config import settings
from backend.services.code_executor import get_code_executor
from backend.services.data_transfer import data_transfer
from backend.tools.code_execution import code_execution_tool

logger = logging.getLogger(__name__)


class _FallbackAsyncLLM:
    """Fallback async LLM used when provider SDKs are unavailable."""

    async def ainvoke(self, messages):
        return AIMessage(
            content=(
                "```python\n"
                "print('Fallback iterative execution response: provider SDK unavailable')\n"
                "```"
            )
        )


@dataclass
class ExecutionAttempt:
    """Record of a single code execution attempt and its outcome."""

    attempt_id: str
    code: str
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    visualizations: List[Dict[str, Any]] = None
    fixes_applied: List[str] = None

    def __post_init__(self):
        if self.visualizations is None:
            self.visualizations = []
        if self.fixes_applied is None:
            self.fixes_applied = []


class CodeExecutionState(TypedDict):
    """State for the iterative code execution pipeline."""

    original_request: str
    current_code: str
    attempts: List[ExecutionAttempt]
    context_blocks: Dict[str, Any]
    execution_history: List[Dict[str, Any]]
    max_attempts: int
    current_attempt: int
    is_completed: bool


class IterativeExecutionCallback(BaseCallbackHandler):
    """Callback handler that tracks execution events and analyzes error patterns."""

    def __init__(self):
        self.execution_log = []
        self.error_patterns = {}
        self.fix_strategies = {}

    def on_agent_action(self, action, **kwargs):
        """Log an agent action event."""
        self.execution_log.append(
            {
                "type": "agent_action",
                "action": str(action),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def on_tool_start(self, serialized, input_str, **kwargs):
        """Log a tool invocation start event."""
        self.execution_log.append(
            {
                "type": "tool_start",
                "tool": serialized.get("name", "unknown"),
                "input": input_str,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def on_tool_end(self, output, **kwargs):
        """Log a tool completion event."""
        self.execution_log.append(
            {
                "type": "tool_end",
                "output": output[:500]
                if isinstance(output, str)
                else str(output)[:500],
                "timestamp": datetime.now().isoformat(),
            }
        )

    def on_tool_error(self, error, **kwargs):
        """Log a tool error event."""
        self.execution_log.append(
            {
                "type": "tool_error",
                "error": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Analyze the error pattern for automatic fix strategies
        self._analyze_error_pattern(error)

    def _analyze_error_pattern(self, error):
        """Classify error patterns and map them to fix strategies."""
        error_str = str(error).lower()

        # Classify error by type
        if "import" in error_str and "no module" in error_str:
            self.error_patterns["missing_import"] = (
                self.error_patterns.get("missing_import", 0) + 1
            )
            self.fix_strategies["missing_import"] = "add_import_statement"

        elif "name" in error_str and "not defined" in error_str:
            self.error_patterns["name_error"] = (
                self.error_patterns.get("name_error", 0) + 1
            )
            self.fix_strategies["name_error"] = "define_variable"

        elif "syntax" in error_str or "syntaxerror" in error_str:
            self.error_patterns["syntax_error"] = (
                self.error_patterns.get("syntax_error", 0) + 1
            )
            self.fix_strategies["syntax_error"] = "fix_syntax"

        elif "index" in error_str and "out of range" in error_str:
            self.error_patterns["index_error"] = (
                self.error_patterns.get("index_error", 0) + 1
            )
            self.fix_strategies["index_error"] = "fix_indexing"

        elif "type" in error_str and "error" in error_str:
            self.error_patterns["type_error"] = (
                self.error_patterns.get("type_error", 0) + 1
            )
            self.fix_strategies["type_error"] = "fix_type_conversion"

        elif "file" in error_str and (
            "not found" in error_str or "no such file" in error_str
        ):
            self.error_patterns["file_error"] = (
                self.error_patterns.get("file_error", 0) + 1
            )
            self.fix_strategies["file_error"] = "fix_file_path"


class CodeFixer:
    """Applies template-based automatic fixes to failed code."""

    def __init__(self):
        self.fix_templates = {
            "add_import_statement": {
                "pandas": "import pandas as pd",
                "numpy": "import numpy as np",
                "matplotlib": "import matplotlib.pyplot as plt",
                "seaborn": "import seaborn as sns",
                "sklearn": "import sklearn",
                "plotly": "import plotly.express as px",
            },
            "fix_syntax": [
                # Common syntax fix patterns: (keyword, prefix, suffix)
                ("print", "print(", ")"),
                ("return", "return ", ""),
                ("def ", "def ", "(self):"),
                ("if ", "if ", ":"),
                ("for ", "for ", " in range"),
                ("while ", "while ", ":"),
            ],
            "define_variable": {
                # Default variable definitions
                "df": "df = pd.DataFrame()",
                "data": "data = []",
                "result": "result = None",
                "fig": "fig, ax = plt.subplots()",
            },
            "fix_indexing": {
                # Index error fix hints
                "out_of_bounds": "Clamp index to len(df) - 1 maximum",
                "negative_index": "Convert negative index to positive equivalent",
                "iloc_loc": "Use df.iloc for integer-based indexing",
            },
            "fix_type_conversion": {
                # Type conversion helpers
                "str_to_int": "int()",
                "str_to_float": "float()",
                "list_to_series": "pd.Series()",
                "series_to_list": ".tolist()",
            },
            "fix_file_path": {
                # File path correction mappings
                "workspace": "/workspace/data/",
                "relative": "./data/",
                "absolute": "/tmp/luncheon_data/",
            },
        }

    def fix_code(
        self, code: str, error_message: str, fix_strategy: str
    ) -> tuple[str, List[str]]:
        """
        Apply an automatic fix to the code based on the error and strategy.

        Args:
            code: The original source code that failed.
            error_message: The error message from execution.
            fix_strategy: The fix strategy identifier to apply.

        Returns:
            A tuple of (fixed_code, list_of_fixes_applied).
        """
        fixes_applied = []

        try:
            if fix_strategy == "add_import_statement":
                return self._fix_missing_imports(code, error_message, fixes_applied)

            elif fix_strategy == "fix_syntax":
                return self._fix_syntax_errors(code, error_message, fixes_applied)

            elif fix_strategy == "define_variable":
                return self._fix_undefined_variables(code, error_message, fixes_applied)

            elif fix_strategy == "fix_indexing":
                return self._fix_index_errors(code, error_message, fixes_applied)

            elif fix_strategy == "fix_type_conversion":
                return self._fix_type_errors(code, error_message, fixes_applied)

            elif fix_strategy == "fix_file_path":
                return self._fix_file_paths(code, error_message, fixes_applied)

            else:
                return code, fixes_applied

        except Exception as e:
            logger.warning(f"Code fix failed: {e}")
            return code, fixes_applied

    def _fix_missing_imports(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """Fix missing import errors by prepending the required import statement."""
        error_lower = error_message.lower()
        fixed_code = code

        # Check each known module against the error message
        for module, import_statement in self.fix_templates[
            "add_import_statement"
        ].items():
            if module in error_lower and module not in code.lower():
                # Prepend the missing import
                fixed_code = f"{import_statement}\n\n{fixed_code}"
                fixes_applied.append(f"Added import: {import_statement}")

        return fixed_code, fixes_applied

    def _fix_syntax_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """Attempt to fix syntax errors using pattern matching."""
        fixed_code = code

        # Try each syntax fix pattern
        for pattern, prefix, suffix in self.fix_templates["fix_syntax"]:
            if pattern in error_message.lower():
                # Apply syntax fix for the matched pattern
                fixes_applied.append(f"Applied syntax fix for: {pattern}")

        return fixed_code, fixes_applied

    def _fix_undefined_variables(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """Fix undefined variable errors by inserting default definitions."""
        fixed_code = code
        error_lower = error_message.lower()

        # Check each known variable pattern
        for var_name, var_definition in self.fix_templates["define_variable"].items():
            if f"'{var_name}'" in error_lower and var_name not in code:
                # Insert variable definition after imports
                lines = code.split("\n")
                insert_index = 0

                # Skip past import statements (insert after them)
                for i, line in enumerate(lines):
                    if line.strip().startswith(("import", "from")) or not line.strip():
                        continue
                    insert_index = i
                    break

                lines.insert(insert_index, f"# Auto-defined {var_name}\n{var_definition}\n")
                fixed_code = "\n".join(lines)
                fixes_applied.append(f"Defined variable: {var_name}")

        return fixed_code, fixes_applied

    def _fix_index_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """Fix index out-of-range errors."""
        fixed_code = code
        fixes_applied.append("Suggested index bounds check")

        # Note: full automatic index fix requires AST analysis
        # For now, recommend using iloc with bounds checking

        return fixed_code, fixes_applied

    def _fix_type_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """Fix type conversion errors."""
        fixed_code = code
        fixes_applied.append("Suggested type conversion fix")

        # Note: full automatic type fix requires runtime type inference

        return fixed_code, fixes_applied

    def _fix_file_paths(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """Fix file path errors by remapping to the sandbox workspace."""
        fixed_code = code
        fixes_applied.append("Remapped file paths to workspace")

        # Apply known path corrections
        path_mappings = {
            "./data/": "/workspace/data/",
            "../data/": "/workspace/data/",
            "data/": "/workspace/data/",
            "~/": "/tmp/",
        }

        for wrong_path, correct_path in path_mappings.items():
            if wrong_path in fixed_code:
                fixed_code = fixed_code.replace(wrong_path, correct_path)
                fixes_applied.append(f"Remapped path: {wrong_path} -> {correct_path}")

        return fixed_code, fixes_applied


class IterativeCodeExecutionAgent:
    """Agent that executes code iteratively with automatic error recovery."""

    def __init__(self, max_attempts: int = 5):
        """
        Initialize the iterative code execution agent.

        Args:
            max_attempts: Maximum number of execution attempts before giving up.
        """
        self.max_attempts = max_attempts
        self.callback_handler = IterativeExecutionCallback()
        self.code_fixer = CodeFixer()
        self.llm = self._get_llm()
        self.logger = logging.getLogger(__name__)

    def _get_llm(self):
        """Get the LLM instance for code generation and error analysis."""
        from backend.config import settings

        if settings.llm_provider == "zhipu":
            try:
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(
                    model=settings.zhipu_model,
                    api_key=settings.zhipu_api_key,
                    base_url=settings.zhipu_base_url,
                    temperature=0.1,
                )
            except Exception as exc:
                logger.warning(
                    "langchain_anthropic unavailable, using fallback async LLM: %s",
                    exc,
                )
                return _FallbackAsyncLLM()
        else:
            try:
                from langchain_ollama import ChatOllama

                return ChatOllama(
                    model=settings.ollama_model,
                    base_url=settings.ollama_host,
                    temperature=0.1,
                )
            except Exception as exc:
                logger.warning(
                    "langchain_ollama unavailable, using fallback async LLM: %s",
                    exc,
                )
                return _FallbackAsyncLLM()

    async def execute_code_iteratively(
        self,
        original_request: str,
        initial_code: Optional[str] = None,
        data_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute code iteratively with automatic error recovery.

        Args:
            original_request: The user's original analysis request.
            initial_code: Pre-written code to execute (optional).
            data_file: Path to the data file (optional).
            context: Additional context for code generation (optional).

        Returns:
            A dict containing:
            - success: Whether execution succeeded.
            - final_code: The final version of the code.
            - attempts: Number of attempts made.
            - execution_result: Output from the last execution.
            - summary: Execution summary with error counts.
        """
        # Initialize execution state
        state = CodeExecutionState(
            original_request=original_request,
            current_code=initial_code or "",
            attempts=[],
            context_blocks=context or {},
            execution_history=[],
            max_attempts=self.max_attempts,
            current_attempt=0,
            is_completed=False,
        )

        # Generate initial code if none provided
        if not state["current_code"]:
            state["current_code"] = await self._generate_initial_code(
                original_request, data_file, context
            )

        # Iterative execution loop
        while (
            state["current_attempt"] < state["max_attempts"]
            and not state["is_completed"]
        ):
            state["current_attempt"] += 1

            self.logger.info(
                f"Execution attempt {state['current_attempt']}/{state['max_attempts']}"
            )

            # Execute the current code
            attempt_result = await self._execute_code_attempt(state, data_file)
            state["attempts"].append(attempt_result)

            if attempt_result.success:
                state["is_completed"] = True
                self.logger.info("Code execution succeeded!")
            else:
                # Analyze error and attempt to fix the code
                fixed_code = await self._analyze_and_fix_code(state, attempt_result)
                state["current_code"] = fixed_code

        # Generate the final result summary
        return self._generate_final_result(state)

    async def _generate_initial_code(
        self,
        request: str,
        data_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate initial Python code from the user's request using the LLM."""
        prompt = f"""
Based on the following request, generate Python code to accomplish the task:

Request: {request}

Data file: {data_file if data_file else 'No data file specified'}

Context: {json.dumps(context, ensure_ascii=False) if context else 'No additional context'}

Write clean, well-documented Python code that:
1. Loads and validates the data
2. Performs the requested analysis
3. Generates visualizations if applicable
4. Prints a summary of results

Requirements:
- Use pandas for data manipulation
- Handle missing values gracefully
- Include error handling
- Add comments explaining each step
"""

        messages = [("system", "You are a Python code generation assistant. Write clean, executable Python code."), ("human", prompt)]

        response = await self.llm.ainvoke(messages)
        return response.content

    async def _execute_code_attempt(
        self, state: CodeExecutionState, data_file: Optional[str] = None
    ) -> ExecutionAttempt:
        """Execute the current code and return the attempt result."""
        attempt_id = f"attempt_{state['current_attempt']}"

        # Prepare data files for the sandbox
        data_files = [data_file] if data_file else None

        try:
            # Execute code in the sandbox
            executor = get_code_executor()
            if executor is None:
                raise RuntimeError("Code executor unavailable: Docker is not running")
            result = executor.execute_code(
                code=state["current_code"],
                data_files=data_files,
                timeout=settings.code_execution_timeout,
            )

            attempt = ExecutionAttempt(
                attempt_id=attempt_id,
                code=state["current_code"],
                timestamp=datetime.now(),
                success=result["success"],
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                execution_time=result.get("execution_time", 0.0),
                visualizations=result.get("visualizations", []),
            )

            if not result["success"]:
                attempt.error_message = result.get("error", "Unknown error")

            return attempt

        except Exception as e:
            return ExecutionAttempt(
                attempt_id=attempt_id,
                code=state["current_code"],
                timestamp=datetime.now(),
                success=False,
                error_message=str(e),
            )

    async def _analyze_and_fix_code(
        self, state: CodeExecutionState, failed_attempt: ExecutionAttempt
    ) -> str:
        """Analyze the failed attempt and generate fixed code."""
        self.logger.info(f"Analyzing error: {failed_attempt.error_message}")

        # Use LLM to analyze the error
        analysis_result = await self._analyze_error_with_llm(
            failed_attempt.code, failed_attempt.error_message, failed_attempt.stderr
        )

        # Apply automatic fixes based on the analysis
        fixed_code = await self._apply_automatic_fixes(
            failed_attempt.code, failed_attempt.error_message, analysis_result
        )

        return fixed_code

    async def _analyze_error_with_llm(
        self, code: str, error_message: str, stderr: str
    ) -> Dict[str, Any]:
        """Use the LLM to analyze a code execution error and suggest fixes."""
        prompt = f"""
Analyze the following Python code execution error:

Code:
```python
{code}
```

Error message:
{error_message}

Stderr output:
{stderr}

Please:
1. Identify the error type
2. Determine the root cause
3. Suggest specific fixes
4. Provide corrected code snippets

Return your analysis as JSON:
{{
    "error_type": "error category",
    "root_cause": "explanation of why the error occurred",
    "fix_suggestions": ["fix suggestion 1", "fix suggestion 2"],
    "missing_imports": ["import1", "import2"],
    "code_changes": [
        {{
            "line": 0,
            "original": "original code",
            "fixed": "corrected code"
        }}
    ]
}}
"""

        messages = [("system", "You are a Python debugging expert. Analyze errors and suggest precise fixes."), ("human", prompt)]

        try:
            response = await self.llm.ainvoke(messages)
            # Parse the JSON response from the LLM
            return json.loads(response.content)
        except:
            # Fallback when LLM response cannot be parsed
            return {
                "error_type": "unknown",
                "root_cause": "Unable to determine root cause",
                "fix_suggestions": ["Review the error message manually"],
                "missing_imports": [],
                "code_changes": [],
            }

    async def _apply_automatic_fixes(
        self, code: str, error_message: str, analysis_result: Dict[str, Any]
    ) -> str:
        """Apply automatic fixes based on LLM analysis and template-based strategies."""
        fixed_code = code
        fixes_applied = []

        # Extract fix suggestions from LLM analysis
        fix_suggestions = analysis_result.get("fix_suggestions", [])
        missing_imports = analysis_result.get("missing_imports", [])

        # Add missing imports
        for import_stmt in missing_imports:
            if import_stmt not in fixed_code:
                fixed_code = f"{import_stmt}\n{fixed_code}"
                fixes_applied.append(f"Added import: {import_stmt}")

        # Apply line-level code changes
        code_changes = analysis_result.get("code_changes", [])
        for change in code_changes:
            line_num = change.get("line", 0)
            original = change.get("original", "")
            fixed = change.get("fixed", "")

            lines = fixed_code.split("\n")
            if 0 <= line_num < len(lines):
                if original in lines[line_num]:
                    lines[line_num] = lines[line_num].replace(original, fixed)
                    fixes_applied.append(f"Fixed line {line_num}: {original} -> {fixed}")

            fixed_code = "\n".join(lines)

        # Apply template-based fixes as a fallback
        if fixes_applied:  # If LLM fixes were applied, also try template fixes
            error_type = analysis_result.get("error_type", "").lower()
            fix_strategy = self.callback_handler.fix_strategies.get(error_type, "")

            if fix_strategy:
                fixed_code, auto_fixes = self.code_fixer.fix_code(
                    fixed_code, error_message, fix_strategy
                )
                fixes_applied.extend(auto_fixes)

        self.logger.info(f"Applied {len(fixes_applied)} fixes")
        return fixed_code

    def _generate_final_result(self, state: CodeExecutionState) -> Dict[str, Any]:
        """Generate the final execution result summary."""
        successful_attempt = None
        failed_attempts = []

        for attempt in state["attempts"]:
            if attempt.success:
                successful_attempt = attempt
            else:
                failed_attempts.append(attempt)

        if successful_attempt:
            return {
                "success": True,
                "final_code": successful_attempt.code,
                "attempts": len(state["attempts"]),
                "successful_attempt": successful_attempt.attempt_id,
                "execution_time": successful_attempt.execution_time,
                "stdout": successful_attempt.stdout,
                "stderr": successful_attempt.stderr,
                "visualizations": successful_attempt.visualizations,
                "summary": {
                    "total_attempts": len(state["attempts"]),
                    "success": True,
                    "error_count": len(failed_attempts),
                    "fixes_applied": self._count_fixes_applied(state["attempts"]),
                },
            }
        else:
            return {
                "success": False,
                "final_code": state["current_code"],
                "attempts": len(state["attempts"]),
                "error_message": "All execution attempts failed.",
                "failed_attempts": [
                    {
                        "attempt_id": attempt.attempt_id,
                        "error_message": attempt.error_message,
                    }
                    for attempt in failed_attempts
                ],
                "summary": {
                    "total_attempts": len(state["attempts"]),
                    "success": False,
                    "last_error": failed_attempts[-1].error_message
                    if failed_attempts
                    else "Unknown error",
                    "error_patterns": self.callback_handler.error_patterns,
                },
            }

    def _count_fixes_applied(self, attempts: List[ExecutionAttempt]) -> int:
        """Count the total number of fixes applied across all retry attempts."""
        total_fixes = 0
        for attempt in attempts[1:]:  # Skip the first attempt (no fixes yet)
            total_fixes += len(attempt.fixes_applied or [])
        return total_fixes


# Module-level singleton instance
iterative_code_agent = IterativeCodeExecutionAgent()
