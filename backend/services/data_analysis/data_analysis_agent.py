"""
数据分析Agent - 专门处理CSV/Excel等结构化数据的分析查询
基于CodeExecutor实现智能数据分析、统计计算和可视化
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.config import settings
from backend.services.code_executor import CodeExecutionError, code_executor
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class DataAnalysisAgent:
    """数据分析Agent - 智能处理结构化数据查询"""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        """
        初始化数据分析Agent

        Args:
            llm_client: LLM客户端，用于生成分析代码
        """
        self.llm_client = llm_client or OllamaClient()
        self.code_executor = code_executor

        if not self.code_executor:
            logger.warning("CodeExecutor不可用，数据分析功能受限")

    def analyze_query(
        self,
        question: str,
        data_file_path: str,
        dataset_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        分析用户查询并生成答案

        Args:
            question: 用户问题
            data_file_path: 数据文件路径
            dataset_metadata: 数据集元数据（列信息、统计摘要等）

        Returns:
            Dict包含answer、code、visualizations等
        """
        try:
            # 1. 加载并检查数据文件
            if not os.path.exists(data_file_path):
                return {
                    "success": False,
                    "error": f"数据文件不存在: {data_file_path}",
                    "answer": "抱歉，找不到相关的数据文件。",
                }

            # 2. 获取数据集信息
            if not dataset_metadata:
                dataset_metadata = self._extract_dataset_info(data_file_path)

            # 3. 生成分析代码
            analysis_code = self._generate_analysis_code(
                question, data_file_path, dataset_metadata
            )

            if not analysis_code:
                return {
                    "success": False,
                    "error": "无法生成分析代码",
                    "answer": "抱歉，我无法理解如何分析这个问题。",
                }

            # 4. 执行代码
            if not self.code_executor:
                return {
                    "success": False,
                    "error": "CodeExecutor不可用",
                    "answer": "抱歉，数据分析服务暂时不可用。",
                }

            execution_result = self.code_executor.execute_code(
                code=analysis_code, data_files=[data_file_path], timeout=30
            )

            # 5. 处理执行结果
            if execution_result["success"]:
                answer = self._parse_execution_output(
                    execution_result["stdout"], question, dataset_metadata
                )

                return {
                    "success": True,
                    "answer": answer,
                    "code": analysis_code,
                    "stdout": execution_result["stdout"],
                    "execution_time": execution_result["execution_time"],
                    "visualizations": execution_result.get("visualizations", []),
                    "dataset_info": dataset_metadata,
                }
            else:
                # 执行失败，尝试生成备选答案
                fallback_answer = self._generate_fallback_answer(
                    question, dataset_metadata, execution_result.get("stderr", "")
                )

                return {
                    "success": False,
                    "error": execution_result.get("error", "代码执行失败"),
                    "stderr": execution_result.get("stderr", ""),
                    "answer": fallback_answer,
                    "code": analysis_code,
                    "dataset_info": dataset_metadata,
                }

        except Exception as e:
            logger.error(f"数据分析失败: {e}")
            return {"success": False, "error": str(e), "answer": "抱歉，数据分析过程中出现错误。"}

    def _extract_dataset_info(self, file_path: str) -> Dict[str, Any]:
        """
        提取数据集基本信息

        Args:
            file_path: 数据文件路径

        Returns:
            数据集元数据
        """
        try:
            # 读取数据
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            elif file_path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(file_path)
            else:
                return {"error": "不支持的文件格式"}

            # 提取列信息
            columns_info = []
            for col in df.columns:
                col_type = str(df[col].dtype)
                col_info = {
                    "name": col,
                    "type": col_type,
                    "non_null_count": int(df[col].count()),
                    "null_count": int(df[col].isnull().sum()),
                }

                # 数值列添加统计信息
                if df[col].dtype in ["int64", "float64"]:
                    col_info.update(
                        {
                            "mean": float(df[col].mean()) if not df[col].empty else 0,
                            "min": float(df[col].min()) if not df[col].empty else 0,
                            "max": float(df[col].max()) if not df[col].empty else 0,
                            "std": float(df[col].std()) if not df[col].empty else 0,
                        }
                    )

                # 分类列添加唯一值信息
                elif df[col].dtype == "object":
                    unique_count = df[col].nunique()
                    if unique_count <= 20:  # 只显示少量唯一值的分布
                        value_counts = df[col].value_counts().to_dict()
                        col_info.update(
                            {
                                "unique_values": unique_count,
                                "top_values": dict(list(value_counts.items())[:5]),
                            }
                        )
                    else:
                        col_info["unique_values"] = unique_count

                columns_info.append(col_info)

            return {
                "filename": os.path.basename(file_path),
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "columns_info": columns_info,
                "memory_usage": int(df.memory_usage(deep=True).sum()),
                "has_index": df.index.name is not None,
            }

        except Exception as e:
            logger.error(f"提取数据集信息失败: {e}")
            return {"error": str(e)}

    def _generate_analysis_code(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        使用LLM生成数据分析代码

        Args:
            question: 用户问题
            data_file_path: 数据文件路径
            dataset_metadata: 数据集元数据

        Returns:
            生成的Python代码
        """
        # 构建Prompt
        prompt = self._build_code_generation_prompt(
            question, data_file_path, dataset_metadata
        )

        try:
            # 调用LLM生成代码
            llm_response = self.llm_client.generate(
                prompt, temperature=0.1, max_tokens=1000  # 低温度保证代码准确性
            )

            # 提取代码块
            code = self._extract_code_from_response(llm_response)

            return code

        except Exception as e:
            logger.error(f"生成分析代码失败: {e}")
            # 降级：使用模板生成简单分析代码
            return self._generate_template_code(
                question, data_file_path, dataset_metadata
            )

    def _build_code_generation_prompt(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """构建代码生成Prompt"""
        columns_desc = "\n".join(
            [
                f"  - {col['name']} ({col['type']})"
                for col in dataset_metadata.get("columns_info", [])
            ]
        )

        return f"""你是一个专业的数据分析助手。请根据用户问题生成Python数据分析代码。

**数据集信息**:
- 文件: {os.path.basename(data_file_path)}
- 行数: {dataset_metadata.get('rows', 'unknown')}
- 列数: {dataset_metadata.get('columns', 'unknown')}
- 列信息:
{columns_desc}

**用户问题**: {question}

**代码要求**:
1. 使用pandas读取数据: pd.read_csv() 或 pd.read_excel()
2. 数据文件路径已自动映射到 /workspace/data/{os.path.basename(data_file_path)}
3. 只输出最终答案，使用 print() 函数
4. 答案简洁明了，直接回答问题
5. 如果需要可视化，保存图片到 /workspace/ 目录
6. 不要使用任何网络请求或系统命令
7. 代码必须在30秒内完成

**代码示例**:
```python
import pandas as pd
import numpy as np

# 读取数据
df = pd.read_csv('/workspace/data/{os.path.basename(data_file_path)}')

# 执行分析
# ... your analysis code ...

# 输出答案
print("答案: ...")
```

请只返回Python代码，不要包含任何解释。将代码放在```python 和 ```之间。"""

    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """从LLM响应中提取代码"""
        # 尝试提取代码块
        code_pattern = r"```python\n(.*?)```"
        matches = re.findall(code_pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # 如果没有代码块标记，尝试直接返回
        if "import" in response and "print" in response:
            return response.strip()

        return None

    def _generate_template_code(
        self, question: str, data_file_path: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """使用模板生成简单分析代码"""
        filename = os.path.basename(data_file_path)

        # 检测问题类型并生成相应代码
        question_lower = question.lower()

        # 统计类问题
        if any(keyword in question_lower for keyword in ["average", "平均", "mean"]):
            return self._template_average(filename, dataset_metadata)

        elif any(
            keyword in question_lower for keyword in ["max", "最高", "最大", "highest"]
        ):
            return self._template_max(filename, dataset_metadata)

        elif any(
            keyword in question_lower for keyword in ["min", "最低", "最小", "lowest"]
        ):
            return self._template_min(filename, dataset_metadata)

        elif any(
            keyword in question_lower for keyword in ["count", "数量", "个数", "how many"]
        ):
            return self._template_count(filename, dataset_metadata)

        elif any(
            keyword in question_lower for keyword in ["percentage", "百分比", "比例", "%"]
        ):
            return self._template_percentage(filename, dataset_metadata)

        else:
            # 默认：显示基本信息
            return self._template_describe(filename, dataset_metadata)

    def _template_describe(self, filename: str, metadata: Dict) -> str:
        """描述统计模板"""
        return f"""import pandas as pd

df = pd.read_csv('/workspace/data/{filename}')
print("数据集概览:")
print(f"总行数: {{len(df)}}")
print(f"总列数: {{len(df.columns)}}")
print("\\n列信息:")
print(df.dtypes)
print("\\n数值列统计:")
print(df.describe())
"""

    def _template_average(self, filename: str, metadata: Dict) -> str:
        """平均值计算模板"""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "mean" in col
        ]

        if numeric_cols:
            target_col = numeric_cols[0]  # 使用第一个数值列
            return f"""import pandas as pd

df = pd.read_csv('/workspace/data/{filename}')
avg_value = df['{target_col}'].mean()
print(f"'{target_col}'的平均值: {{avg_value:.2f}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _template_max(self, filename: str, metadata: Dict) -> str:
        """最大值查询模板"""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "max" in col
        ]

        if numeric_cols:
            target_col = numeric_cols[0]
            return f"""import pandas as pd

df = pd.read_csv('/workspace/data/{filename}')
max_value = df['{target_col}'].max()
max_row = df[df['{target_col}'] == max_value].iloc[0]
print(f"最大'{target_col}': {{max_value}}")
print(f"对应记录: {{max_row.to_dict()}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _template_min(self, filename: str, metadata: Dict) -> str:
        """最小值查询模板"""
        numeric_cols = [
            col["name"] for col in metadata.get("columns_info", []) if "min" in col
        ]

        if numeric_cols:
            target_col = numeric_cols[0]
            return f"""import pandas as pd

df = pd.read_csv('/workspace/data/{filename}')
min_value = df['{target_col}'].min()
min_row = df[df['{target_col}'] == min_value].iloc[0]
print(f"最小'{target_col}': {{min_value}}")
print(f"对应记录: {{min_row.to_dict()}}")
"""
        else:
            return self._template_describe(filename, metadata)

    def _template_count(self, filename: str, metadata: Dict) -> str:
        """计数模板"""
        categorical_cols = [
            col["name"]
            for col in metadata.get("columns_info", [])
            if col.get("unique_values", 0) > 0 and col.get("unique_values", 0) < 100
        ]

        if categorical_cols:
            target_col = categorical_cols[0]
            return f"""import pandas as pd

df = pd.read_csv('/workspace/data/{filename}')
value_counts = df['{target_col}'].value_counts()
print(f"'{target_col}'各类别数量:")
print(value_counts)
"""
        else:
            return f"""import pandas as pd

df = pd.read_csv('/workspace/data/{filename}')
print(f"总记录数: {{len(df)}}")
"""

    def _template_percentage(self, filename: str, metadata: Dict) -> str:
        """百分比计算模板"""
        categorical_cols = [
            col["name"]
            for col in metadata.get("columns_info", [])
            if col.get("unique_values", 0) > 0 and col.get("unique_values", 0) < 50
        ]

        if categorical_cols:
            target_col = categorical_cols[0]
            return f"""import pandas as pd

df = pd.read_csv('/workspace/data/{filename}')
value_counts = df['{target_col}'].value_counts()
percentages = (value_counts / len(df) * 100).round(2)
print(f"'{target_col}'各类别百分比:")
for val, pct in percentages.items():
    print(f"  {{val}}: {{pct}}%")
"""
        else:
            return self._template_describe(filename, metadata)

    def _parse_execution_output(
        self, stdout: str, question: str, dataset_metadata: Dict[str, Any]
    ) -> str:
        """
        解析代码执行输出并生成自然语言答案

        Args:
            stdout: 标准输出
            question: 原始问题
            dataset_metadata: 数据集元数据

        Returns:
            自然语言答案
        """
        if not stdout.strip():
            return "代码执行成功，但没有输出结果。"

        # 清理输出
        cleaned_output = stdout.strip()

        # 如果输出已经是完整句子，直接返回
        if cleaned_output.endswith((".", "。", "!", "！")):
            return cleaned_output

        # 否则，添加上下文
        return f"根据数据分析结果：\n{cleaned_output}"

    def _generate_fallback_answer(
        self, question: str, dataset_metadata: Dict[str, Any], error_message: str
    ) -> str:
        """
        生成备选答案（当代码执行失败时）

        Args:
            question: 用户问题
            dataset_metadata: 数据集元数据
            error_message: 错误信息

        Returns:
            备选答案
        """
        # 基于元数据尝试回答简单问题
        question_lower = question.lower()

        # 列名查询
        if (
            "feature" in question_lower
            or "column" in question_lower
            or "特征" in question_lower
            or "列" in question_lower
        ):
            columns = dataset_metadata.get("column_names", [])
            if columns:
                return f"数据集包含以下列: {', '.join(columns)}"

        # 行数查询
        if (
            "how many" in question_lower
            or "多少" in question_lower
            or "row" in question_lower
            or "行" in question_lower
        ):
            rows = dataset_metadata.get("rows")
            if rows:
                return f"数据集包含 {rows} 条记录。"

        # 默认回答
        return f"抱歉，我无法直接回答这个问题。数据集包含 {dataset_metadata.get('rows', 'unknown')} 行数据和 {dataset_metadata.get('columns', 'unknown')} 个字段。"


# 全局实例
data_analysis_agent = DataAnalysisAgent()
