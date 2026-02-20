"""可迭代代码执行 Agent - 支持 LangChain 1.0 中间件和自我修复机制"""

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
    """执行尝试记录"""

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
    """代码执行状态"""

    original_request: str
    current_code: str
    attempts: List[ExecutionAttempt]
    context_blocks: Dict[str, Any]
    execution_history: List[Dict[str, Any]]
    max_attempts: int
    current_attempt: int
    is_completed: bool


class IterativeExecutionCallback(BaseCallbackHandler):
    """可迭代执行回调处理器"""

    def __init__(self):
        self.execution_log = []
        self.error_patterns = {}
        self.fix_strategies = {}

    def on_agent_action(self, action, **kwargs):
        """Agent 动作回调"""
        self.execution_log.append(
            {
                "type": "agent_action",
                "action": str(action),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def on_tool_start(self, serialized, input_str, **kwargs):
        """工具开始回调"""
        self.execution_log.append(
            {
                "type": "tool_start",
                "tool": serialized.get("name", "unknown"),
                "input": input_str,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def on_tool_end(self, output, **kwargs):
        """工具结束回调"""
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
        """工具错误回调"""
        self.execution_log.append(
            {
                "type": "tool_error",
                "error": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 分析错误模式
        self._analyze_error_pattern(error)

    def _analyze_error_pattern(self, error):
        """分析错误模式"""
        error_str = str(error).lower()

        # 常见错误模式识别
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
    """代码修复器"""

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
                # 修复常见语法错误
                ("print", "print(", ")"),
                ("return", "return ", ""),
                ("def ", "def ", "(self):"),
                ("if ", "if ", ":"),
                ("for ", "for ", " in range"),
                ("while ", "while ", ":"),
            ],
            "define_variable": {
                # 变量定义模板
                "df": "df = pd.DataFrame()",
                "data": "data = []",
                "result": "result = None",
                "fig": "fig, ax = plt.subplots()",
            },
            "fix_indexing": {
                # 索引修复策略
                "out_of_bounds": "使用 len(df) - 1 作为最大索引",
                "negative_index": "使用负数索引从末尾访问",
                "iloc_loc": "使用 df.iloc 而不是直接索引",
            },
            "fix_type_conversion": {
                # 类型转换修复
                "str_to_int": "int()",
                "str_to_float": "float()",
                "list_to_series": "pd.Series()",
                "series_to_list": ".tolist()",
            },
            "fix_file_path": {
                # 文件路径修复
                "workspace": "/workspace/data/",
                "relative": "./data/",
                "absolute": "/tmp/luncheon_data/",
            },
        }

    def fix_code(
        self, code: str, error_message: str, fix_strategy: str
    ) -> tuple[str, List[str]]:
        """
        修复代码

        Args:
            code: 原始代码
            error_message: 错误消息
            fix_strategy: 修复策略

        Returns:
            修复后的代码和应用修复列表
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
            logger.warning(f"代码修复失败: {e}")
            return code, fixes_applied

    def _fix_missing_imports(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """修复缺失的导入"""
        error_lower = error_message.lower()
        fixed_code = code

        # 检测缺失的模块
        for module, import_statement in self.fix_templates[
            "add_import_statement"
        ].items():
            if module in error_lower and module not in code.lower():
                # 在代码开头添加导入
                fixed_code = f"{import_statement}\n\n{fixed_code}"
                fixes_applied.append(f"添加导入: {import_statement}")

        return fixed_code, fixes_applied

    def _fix_syntax_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """修复语法错误"""
        fixed_code = code

        # 基础语法修复
        for pattern, prefix, suffix in self.fix_templates["fix_syntax"]:
            if pattern in error_message.lower():
                # 这里可以实现更复杂的语法修复逻辑
                fixes_applied.append(f"尝试修复语法错误: {pattern}")

        return fixed_code, fixes_applied

    def _fix_undefined_variables(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """修复未定义变量"""
        fixed_code = code
        error_lower = error_message.lower()

        # 检测未定义的变量
        for var_name, var_definition in self.fix_templates["define_variable"].items():
            if f"'{var_name}'" in error_lower and var_name not in code:
                # 在使用变量前添加定义
                lines = code.split("\n")
                insert_index = 0

                # 寻找合适的插入位置（在导入语句之后）
                for i, line in enumerate(lines):
                    if line.strip().startswith(("import", "from")) or not line.strip():
                        continue
                    insert_index = i
                    break

                lines.insert(insert_index, f"# 定义变量 {var_name}\n{var_definition}\n")
                fixed_code = "\n".join(lines)
                fixes_applied.append(f"定义变量: {var_name}")

        return fixed_code, fixes_applied

    def _fix_index_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """修复索引错误"""
        fixed_code = code
        fixes_applied.append("检查并修复索引访问")

        # 这里可以实现更复杂的索引修复逻辑
        # 例如添加边界检查、使用iloc等

        return fixed_code, fixes_applied

    def _fix_type_errors(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """修复类型错误"""
        fixed_code = code
        fixes_applied.append("添加类型转换")

        # 这里可以实现类型转换逻辑

        return fixed_code, fixes_applied

    def _fix_file_paths(
        self, code: str, error_message: str, fixes_applied: List[str]
    ) -> tuple[str, List[str]]:
        """修复文件路径错误"""
        fixed_code = code
        fixes_applied.append("修正文件路径")

        # 替换可能的错误路径
        path_mappings = {
            "./data/": "/workspace/data/",
            "../data/": "/workspace/data/",
            "data/": "/workspace/data/",
            "~/": "/tmp/",
        }

        for wrong_path, correct_path in path_mappings.items():
            if wrong_path in fixed_code:
                fixed_code = fixed_code.replace(wrong_path, correct_path)
                fixes_applied.append(f"路径修正: {wrong_path} -> {correct_path}")

        return fixed_code, fixes_applied


class IterativeCodeExecutionAgent:
    """可迭代代码执行 Agent"""

    def __init__(self, max_attempts: int = 5):
        """
        初始化可迭代代码执行 Agent

        Args:
            max_attempts: 最大尝试次数
        """
        self.max_attempts = max_attempts
        self.callback_handler = IterativeExecutionCallback()
        self.code_fixer = CodeFixer()
        self.llm = self._get_llm()
        self.logger = logging.getLogger(__name__)

    def _get_llm(self):
        """获取 LLM 实例"""
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
        迭代执行代码，直到成功或达到最大尝试次数

        Args:
            original_request: 原始请求
            initial_code: 初始代码（可选）
            data_file: 数据文件路径（可选）
            context: 上下文信息（可选）

        Returns:
            执行结果字典，包含：
            - success: 是否成功
            - final_code: 最终代码
            - attempts: 所有尝试记录
            - execution_result: 最终执行结果
            - summary: 执行摘要
        """
        # 初始化状态
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

        # 如果没有初始代码，生成初始代码
        if not state["current_code"]:
            state["current_code"] = await self._generate_initial_code(
                original_request, data_file, context
            )

        # 迭代执行
        while (
            state["current_attempt"] < state["max_attempts"]
            and not state["is_completed"]
        ):
            state["current_attempt"] += 1

            self.logger.info(
                f"代码执行尝试 {state['current_attempt']}/{state['max_attempts']}"
            )

            # 执行代码
            attempt_result = await self._execute_code_attempt(state, data_file)
            state["attempts"].append(attempt_result)

            if attempt_result.success:
                state["is_completed"] = True
                self.logger.info("代码执行成功！")
            else:
                # 分析错误并修复代码
                fixed_code = await self._analyze_and_fix_code(state, attempt_result)
                state["current_code"] = fixed_code

        # 生成最终结果
        return self._generate_final_result(state)

    async def _generate_initial_code(
        self,
        request: str,
        data_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成初始代码"""
        prompt = f"""
基于以下用户请求，生成 Python 数据分析代码：

用户请求: {request}

数据文件: {data_file if data_file else '无'}

上下文信息: {json.dumps(context, ensure_ascii=False) if context else '无'}

请生成完整的 Python 代码，包括：
1. 必要的导入语句
2. 数据读取和预处理
3. 分析和可视化代码
4. 结果输出

要求：
- 代码应该完整可执行
- 包含错误处理
- 生成可视化图表
- 输出分析结果
"""

        messages = [("system", "你是一个专业的数据分析师，擅长编写 Python 数据分析代码。"), ("human", prompt)]

        response = await self.llm.ainvoke(messages)
        return response.content

    async def _execute_code_attempt(
        self, state: CodeExecutionState, data_file: Optional[str] = None
    ) -> ExecutionAttempt:
        """执行单次代码尝试"""
        attempt_id = f"attempt_{state['current_attempt']}"

        # 准备数据文件
        data_files = [data_file] if data_file else None

        try:
            # 执行代码
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
        """分析错误并修复代码"""
        self.logger.info(f"分析执行错误: {failed_attempt.error_message}")

        # 使用 LLM 分析错误
        analysis_result = await self._analyze_error_with_llm(
            failed_attempt.code, failed_attempt.error_message, failed_attempt.stderr
        )

        # 应用自动修复
        fixed_code = await self._apply_automatic_fixes(
            failed_attempt.code, failed_attempt.error_message, analysis_result
        )

        return fixed_code

    async def _analyze_error_with_llm(
        self, code: str, error_message: str, stderr: str
    ) -> Dict[str, Any]:
        """使用 LLM 分析错误"""
        prompt = f"""
分析以下 Python 代码的错误并提供修复建议：

代码:
```python
{code}
```

错误信息:
{error_message}

标准错误输出:
{stderr}

请分析：
1. 错误的根本原因
2. 具体的修复建议
3. 需要添加的导入语句
4. 需要修改的代码行

以 JSON 格式返回分析结果：
{{
    "error_type": "错误类型",
    "root_cause": "根本原因",
    "fix_suggestions": ["修复建议1", "修复建议2"],
    "missing_imports": ["import1", "import2"],
    "code_changes": [
        {{
            "line": 行号,
            "original": "原始代码",
            "fixed": "修复后代码"
        }}
    ]
}}
"""

        messages = [("system", "你是一个专业的 Python 调试专家，擅长分析和修复代码错误。"), ("human", prompt)]

        try:
            response = await self.llm.ainvoke(messages)
            # 尝试解析 JSON 结果
            return json.loads(response.content)
        except:
            # 如果解析失败，返回基础分析
            return {
                "error_type": "unknown",
                "root_cause": "无法解析错误信息",
                "fix_suggestions": ["检查代码语法"],
                "missing_imports": [],
                "code_changes": [],
            }

    async def _apply_automatic_fixes(
        self, code: str, error_message: str, analysis_result: Dict[str, Any]
    ) -> str:
        """应用自动修复"""
        fixed_code = code
        fixes_applied = []

        # 基于 LLM 分析应用修复
        fix_suggestions = analysis_result.get("fix_suggestions", [])
        missing_imports = analysis_result.get("missing_imports", [])

        # 添加缺失的导入
        for import_stmt in missing_imports:
            if import_stmt not in fixed_code:
                fixed_code = f"{import_stmt}\n{fixed_code}"
                fixes_applied.append(f"添加导入: {import_stmt}")

        # 应用代码变更
        code_changes = analysis_result.get("code_changes", [])
        for change in code_changes:
            line_num = change.get("line", 0)
            original = change.get("original", "")
            fixed = change.get("fixed", "")

            lines = fixed_code.split("\n")
            if 0 <= line_num < len(lines):
                if original in lines[line_num]:
                    lines[line_num] = lines[line_num].replace(original, fixed)
                    fixes_applied.append(f"第{line_num}行: {original} -> {fixed}")

            fixed_code = "\n".join(lines)

        # 使用内置修复器
        if fixes_applied:  # 如果 LLM 修复失败，尝试内置修复
            error_type = analysis_result.get("error_type", "").lower()
            fix_strategy = self.callback_handler.fix_strategies.get(error_type, "")

            if fix_strategy:
                fixed_code, auto_fixes = self.code_fixer.fix_code(
                    fixed_code, error_message, fix_strategy
                )
                fixes_applied.extend(auto_fixes)

        self.logger.info(f"应用了 {len(fixes_applied)} 个修复")
        return fixed_code

    def _generate_final_result(self, state: CodeExecutionState) -> Dict[str, Any]:
        """生成最终结果"""
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
                "error_message": "达到最大尝试次数，代码执行失败",
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
        """统计应用的修复数量"""
        total_fixes = 0
        for attempt in attempts[1:]:  # 跳过第一次尝试
            total_fixes += len(attempt.fixes_applied or [])
        return total_fixes


# 全局实例
iterative_code_agent = IterativeCodeExecutionAgent()
