"""EN Agent - EN LangChain 1.0 EN"""

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
from backend.services.code_executor import code_executor
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
    """EN"""

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
    """EN"""

    original_request: str
    current_code: str
    attempts: List[ExecutionAttempt]
    context_blocks: Dict[str, Any]
    execution_history: List[Dict[str, Any]]
    max_attempts: int
    current_attempt: int
    is_completed: bool


class IterativeExecutionCallback(BaseCallbackHandler):
    """EN"""

    def __init__(self):
        self.execution_log = []
        self.error_patterns = {}
        self.fix_strategies = {}

    def on_agent_action(self, action, **kwargs):
        """Agent EN"""
        self.execution_log.append(
            {
                "type": "agent_action",
                "action": str(action),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def on_tool_start(self, serialized, input_str, **kwargs):
        """EN"""
        self.execution_log.append(
            {
                "type": "tool_start",
                "tool": serialized.get("name", "unknown"),
                "input": input_str,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def on_tool_end(self, output, **kwargs):
        """EN"""
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
        """EN"""
        self.execution_log.append(
            {
                "type": "tool_error",
                "error": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        )

        # EN
        self._analyze_error_pattern(error)

    def _analyze_error_pattern(self, error):
        """EN"""
        error_str = str(error).lower()

        # EN
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
    """EN"""

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
                # EN
                ("print", "print(", ")"),
                ("return", "return ", ""),
                ("def ", "def ", "(self):"),
                ("if ", "if ", ":"),
                ("for ", "for ", " in range"),
                ("while ", "while ", ":"),
            ],
            "define_variable": {
                # EN
                "df": "df = pd.DataFrame()",
                "data": "data = []",
                "result": "result = None",
                "fig": "fig, ax = plt.subplots()",
            },
            "fix_indexing": {
                # EN
                "out_of_bounds": "EN len(df) - 1 EN",
                "negative_index": "EN",
                "iloc_loc": "EN df.iloc EN",
            },
            "fix_type_conversion": {
                # EN
                "str_to_int": "int()",
                "str_to_float": "float()",
                "list_to_series": "pd.Series()",
                "series_to_list": ".tolist()",
            },
            "fix_file_path": {
                # EN
                "workspace": "/workspace/data/",
                "relative": "./data/",
                "absolute": "/tmp/luncheon_data/",
            },
        }

    def fix_code(
        self, code: str, error_message: str, fix_strategy: str
    ) -> tuple[str, List[str]]:
        """
        EN

        Args:
            code: EN
            error_message: EN
            fix_strategy: EN

        Returns:
            EN
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
            logger.warning(f"EN: {e}")
            return code, fixes_applied

    def _fix_missing_imports(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """EN"""
        error_lower = error_message.lower()
        fixed_code = code

        # EN
        for module, import_statement in self.fix_templates[
            "add_import_statement"
        ].items():
            if module in error_lower and module not in code.lower():
                # EN
                fixed_code = f"{import_statement}\n\n{fixed_code}"
                fixes_applied.append(f"EN: {import_statement}")

        return fixed_code, fixes_applied

    def _fix_syntax_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """EN"""
        fixed_code = code

        # EN
        for pattern, prefix, suffix in self.fix_templates["fix_syntax"]:
            if pattern in error_message.lower():
                # EN
                fixes_applied.append(f"EN: {pattern}")

        return fixed_code, fixes_applied

    def _fix_undefined_variables(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """EN"""
        fixed_code = code
        error_lower = error_message.lower()

        # EN
        for var_name, var_definition in self.fix_templates["define_variable"].items():
            if f"'{var_name}'" in error_lower and var_name not in code:
                # EN
                lines = code.split("\n")
                insert_index = 0

                # EN(EN)
                for i, line in enumerate(lines):
                    if line.strip().startswith(("import", "from")) or not line.strip():
                        continue
                    insert_index = i
                    break

                lines.insert(insert_index, f"# EN {var_name}\n{var_definition}\n")
                fixed_code = "\n".join(lines)
                fixes_applied.append(f"EN: {var_name}")

        return fixed_code, fixes_applied

    def _fix_index_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """EN"""
        fixed_code = code
        fixes_applied.append("EN")

        # EN
        # EN,ENilocEN

        return fixed_code, fixes_applied

    def _fix_type_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """EN"""
        fixed_code = code
        fixes_applied.append("EN")

        # EN

        return fixed_code, fixes_applied

    def _fix_file_paths(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """EN"""
        fixed_code = code
        fixes_applied.append("EN")

        # EN
        path_mappings = {
            "./data/": "/workspace/data/",
            "../data/": "/workspace/data/",
            "data/": "/workspace/data/",
            "~/": "/tmp/",
        }

        for wrong_path, correct_path in path_mappings.items():
            if wrong_path in fixed_code:
                fixed_code = fixed_code.replace(wrong_path, correct_path)
                fixes_applied.append(f"EN: {wrong_path} -> {correct_path}")

        return fixed_code, fixes_applied


class IterativeCodeExecutionAgent:
    """EN Agent"""

    def __init__(self, max_attempts: int = 5):
        """
        EN Agent

        Args:
            max_attempts: EN
        """
        self.max_attempts = max_attempts
        self.callback_handler = IterativeExecutionCallback()
        self.code_fixer = CodeFixer()
        self.llm = self._get_llm()
        self.logger = logging.getLogger(__name__)

    def _get_llm(self):
        """EN LLM EN"""
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
        EN,EN

        Args:
            original_request: EN
            initial_code: EN(EN)
            data_file: EN(EN)
            context: EN(EN)

        Returns:
            EN,EN:
            - success: EN
            - final_code: EN
            - attempts: EN
            - execution_result: EN
            - summary: EN
        """
        # EN
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

        # EN,EN
        if not state["current_code"]:
            state["current_code"] = await self._generate_initial_code(
                original_request, data_file, context
            )

        # EN
        while (
            state["current_attempt"] < state["max_attempts"]
            and not state["is_completed"]
        ):
            state["current_attempt"] += 1

            self.logger.info(
                f"EN {state['current_attempt']}/{state['max_attempts']}"
            )

            # EN
            attempt_result = await self._execute_code_attempt(state, data_file)
            state["attempts"].append(attempt_result)

            if attempt_result.success:
                state["is_completed"] = True
                self.logger.info("EN!")
            else:
                # EN
                fixed_code = await self._analyze_and_fix_code(state, attempt_result)
                state["current_code"] = fixed_code

        # EN
        return self._generate_final_result(state)

    async def _generate_initial_code(
        self,
        request: str,
        data_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """EN"""
        prompt = f"""
EN,EN Python EN:

EN: {request}

EN: {data_file if data_file else 'EN'}

EN: {json.dumps(context, ensure_ascii=False) if context else 'EN'}

EN Python EN,EN:
1. EN
2. EN
3. EN
4. EN

EN:
- EN
- EN
- EN
- EN
"""

        messages = [("system", "EN,EN Python EN."), ("human", prompt)]

        response = await self.llm.ainvoke(messages)
        return response.content

    async def _execute_code_attempt(
        self, state: CodeExecutionState, data_file: Optional[str] = None
    ) -> ExecutionAttempt:
        """EN"""
        attempt_id = f"attempt_{state['current_attempt']}"

        # EN
        data_files = [data_file] if data_file else None

        try:
            # EN
            result = code_executor.execute_code(
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
        """EN"""
        self.logger.info(f"EN: {failed_attempt.error_message}")

        # EN LLM EN
        analysis_result = await self._analyze_error_with_llm(
            failed_attempt.code, failed_attempt.error_message, failed_attempt.stderr
        )

        # EN
        fixed_code = await self._apply_automatic_fixes(
            failed_attempt.code, failed_attempt.error_message, analysis_result
        )

        return fixed_code

    async def _analyze_error_with_llm(
        self, code: str, error_message: str, stderr: str
    ) -> Dict[str, Any]:
        """EN LLM EN"""
        prompt = f"""
EN Python EN:

EN:
```python
{code}
```

EN:
{error_message}

EN:
{stderr}

EN:
1. EN
2. EN
3. EN
4. EN

EN JSON EN:
{{
    "error_type": "EN",
    "root_cause": "EN",
    "fix_suggestions": ["EN1", "EN2"],
    "missing_imports": ["import1", "import2"],
    "code_changes": [
        {{
            "line": EN,
            "original": "EN",
            "fixed": "EN"
        }}
    ]
}}
"""

        messages = [("system", "EN Python EN,EN."), ("human", prompt)]

        try:
            response = await self.llm.ainvoke(messages)
            # EN JSON EN
            return json.loads(response.content)
        except:
            # EN,EN
            return {
                "error_type": "unknown",
                "root_cause": "EN",
                "fix_suggestions": ["EN"],
                "missing_imports": [],
                "code_changes": [],
            }

    async def _apply_automatic_fixes(
        self, code: str, error_message: str, analysis_result: Dict[str, Any]
    ) -> str:
        """EN"""
        fixed_code = code
        fixes_applied = []

        # EN LLM EN
        fix_suggestions = analysis_result.get("fix_suggestions", [])
        missing_imports = analysis_result.get("missing_imports", [])

        # EN
        for import_stmt in missing_imports:
            if import_stmt not in fixed_code:
                fixed_code = f"{import_stmt}\n{fixed_code}"
                fixes_applied.append(f"EN: {import_stmt}")

        # EN
        code_changes = analysis_result.get("code_changes", [])
        for change in code_changes:
            line_num = change.get("line", 0)
            original = change.get("original", "")
            fixed = change.get("fixed", "")

            lines = fixed_code.split("\n")
            if 0 <= line_num < len(lines):
                if original in lines[line_num]:
                    lines[line_num] = lines[line_num].replace(original, fixed)
                    fixes_applied.append(f"EN{line_num}EN: {original} -> {fixed}")

            fixed_code = "\n".join(lines)

        # EN
        if fixes_applied:  # EN LLM EN,EN
            error_type = analysis_result.get("error_type", "").lower()
            fix_strategy = self.callback_handler.fix_strategies.get(error_type, "")

            if fix_strategy:
                fixed_code, auto_fixes = self.code_fixer.fix_code(
                    fixed_code, error_message, fix_strategy
                )
                fixes_applied.extend(auto_fixes)

        self.logger.info(f"EN {len(fixes_applied)} EN")
        return fixed_code

    def _generate_final_result(self, state: CodeExecutionState) -> Dict[str, Any]:
        """EN"""
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
        """EN"""
        total_fixes = 0
        for attempt in attempts[1:]:  # EN
            total_fixes += len(attempt.fixes_applied or [])
        return total_fixes


# EN
iterative_code_agent = IterativeCodeExecutionAgent()
