"""
智能意图分类器 - RAG系统的核心路由组件
基于LLM的智能问题分类和路由决策系统
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型枚举"""

    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"  # 知识检索类
    DATA_ANALYSIS = "data_analysis"  # 数据分析类
    COST_ESTIMATION = "cost_estimation"  # 成本估算类
    DOCUMENT_PROCESSING = "document_processing"  # 文档处理类
    CODE_EXECUTION = "code_execution"  # 代码执行类
    UNCLEAR_INTENT = "unclear_intent"  # 意图不明确


class SubIntentType(Enum):
    """子意图类型枚举"""

    # 知识检索子类
    FACT_QUERY = "fact_query"  # 事实查询
    CONCEPT_EXPLANATION = "concept_explanation"  # 概念解释
    COMPARISON_ANALYSIS = "comparison_analysis"  # 比较分析
    HOW_TO_GUIDE = "how_to_guide"  # 操作指南

    # 数据分析子类
    EXPLORATORY_ANALYSIS = "exploratory_analysis"  # 探索性分析
    STATISTICAL_ANALYSIS = "statistical_analysis"  # 统计分析
    MACHINE_LEARNING = "machine_learning"  # 机器学习
    VISUALIZATION = "visualization"  # 数据可视化

    # 文档处理子类
    OCR_PROCESSING = "ocr_processing"  # OCR处理
    TABLE_EXTRACTION = "table_extraction"  # 表格提取
    IMAGE_ANALYSIS = "image_analysis"  # 图像分析
    TEXT_EXTRACTION = "text_extraction"  # 文本提取

    # 代码执行子类
    SCRIPT_EXECUTION = "script_execution"  # 脚本执行
    COMPUTATION_TASK = "computation_task"  # 计算任务
    ALGORITHM_IMPLEMENTATION = "algorithm_implementation"  # 算法实现
    DEBUGGING = "debugging"  # 调试任务


@dataclass
class IntentResult:
    """意图分类结果"""

    intent: IntentType
    sub_intent: Optional[SubIntentType] = None
    confidence: float = 0.0
    reasoning: str = ""
    keywords: List[str] = None
    context_clues: List[str] = None
    suggested_action: str = ""
    uncertainty_factors: List[str] = None
    processing_time_ms: int = 0
    llm_response: Optional[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.context_clues is None:
            self.context_clues = []
        if self.uncertainty_factors is None:
            self.uncertainty_factors = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            **asdict(self),
            "intent": self.intent.value
            if isinstance(self.intent, IntentType)
            else self.intent,
            "sub_intent": self.sub_intent.value if self.sub_intent else None,
        }

    @property
    def is_high_confidence(self) -> bool:
        """判断是否为高置信度"""
        return self.confidence >= 0.7

    @property
    def is_very_high_confidence(self) -> bool:
        """判断是否为极高置信度"""
        return self.confidence >= 0.9

    @property
    def is_uncertain(self) -> bool:
        """判断是否意图不明确"""
        return self.confidence < 0.5


@dataclass
class QueryContext:
    """查询上下文信息"""

    session_id: str
    user_id: Optional[str] = None
    session_topic: str = ""
    recent_intents: List[str] = None
    uploaded_files: List[Dict[str, Any]] = None
    user_preferences: Dict[str, Any] = None
    interaction_history: List[Dict[str, Any]] = None
    time_of_day: str = ""
    query_count_in_session: int = 0

    def __post_init__(self):
        if self.recent_intents is None:
            self.recent_intents = []
        if self.uploaded_files is None:
            self.uploaded_files = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.interaction_history is None:
            self.interaction_history = []

    def add_intent(self, intent: str):
        """添加意图到历史记录"""
        self.recent_intents.append(intent)
        # 只保留最近5个意图
        if len(self.recent_intents) > 5:
            self.recent_intents = self.recent_intents[-5:]

    def add_uploaded_file(self, file_info: Dict[str, Any]):
        """添加上传文件记录"""
        self.uploaded_files.append(file_info)
        # 只保留最近3个文件
        if len(self.uploaded_files) > 3:
            self.uploaded_files = self.uploaded_files[-3:]


class IntentClassifier:
    """智能意图分类器"""

    def __init__(
        self,
        prompt_manager,
        llm_client,
        confidence_threshold: float = 0.7,
        enable_cache: bool = True,
        cache_ttl: int = 300,
    ):
        """
        初始化意图分类器

        Args:
            prompt_manager: Prompt管理器
            llm_client: LLM客户端
            confidence_threshold: 置信度阈值
            enable_cache: 是否启用缓存
            cache_ttl: 缓存过期时间（秒）
        """
        self.prompt_manager = prompt_manager
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl

        # 分类缓存
        self._classification_cache: Dict[str, Tuple[IntentResult, datetime]] = {}

        # 统计信息
        self.stats = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "clarification_count": 0,
            "cache_hits": 0,
            "avg_confidence": 0.0,
        }

        logger.info("意图分类器初始化完成")

    async def classify_intent(self, query: str, context: QueryContext) -> IntentResult:
        """
        分类用户意图

        Args:
            query: 用户查询
            context: 查询上下文

        Returns:
            IntentResult: 分类结果
        """
        start_time = datetime.now()

        try:
            # 1. 输入预处理
            processed_query = await self._preprocess_input(query)

            # 2. 检查缓存
            cache_key = self._generate_cache_key(processed_query, context)
            if self.enable_cache:
                cached_result = self._get_from_cache(cache_key)
                if cached_result:
                    self.stats["cache_hits"] += 1
                    logger.debug(f"从缓存获取分类结果: {cached_result.intent}")
                    return cached_result

            # 3. 构建分类请求
            classification_request = await self._build_classification_request(
                processed_query, context
            )

            # 4. 获取分类Prompt
            prompt_info, prompt_content = await self.prompt_manager.get_prompt(
                name="intent_classification",
                category="Intent",
                context={
                    "query_length": len(processed_query),
                    "has_uploaded_files": len(context.uploaded_files) > 0,
                    "session_depth": context.query_count_in_session,
                },
                variables={
                    "user_query": processed_query,
                    "session_topic": context.session_topic,
                    "recent_intents": ", ".join(context.recent_intents[-3:])
                    if context.recent_intents
                    else "",
                    "uploaded_files": ", ".join(
                        [f["name"] for f in context.uploaded_files]
                    )
                    if context.uploaded_files
                    else "无",
                    "user_preferences": json.dumps(
                        context.user_preferences, ensure_ascii=False
                    ),
                },
            )

            # 5. 调用LLM进行分类
            llm_response = await self._call_llm_for_classification(
                prompt_content + "\n\n" + classification_request
            )

            # 6. 解析分类结果
            intent_result = await self._parse_classification_result(llm_response)

            # 7. 后处理和验证
            intent_result = await self._post_process_result(
                intent_result, query, context
            )

            # 8. 更新缓存
            if self.enable_cache:
                self._save_to_cache(cache_key, intent_result)

            # 9. 更新统计
            self._update_stats(intent_result)

            # 10. 记录处理时间
            intent_result.processing_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            intent_result.llm_response = llm_response

            logger.info(
                f"意图分类完成: {intent_result.intent} (置信度: {intent_result.confidence:.2f})"
            )
            return intent_result

        except Exception as e:
            logger.error(f"意图分类失败: {e}")
            # 返回默认的模糊分类结果
            return IntentResult(
                intent=IntentType.UNCLEAR_INTENT,
                confidence=0.0,
                reasoning=f"分类过程中出现错误: {str(e)}",
                processing_time_ms=int(
                    (datetime.now() - start_time).total_seconds() * 1000
                ),
            )

    async def _preprocess_input(self, query: str) -> str:
        """
        输入预处理

        Args:
            query: 原始查询

        Returns:
            str: 处理后的查询
        """
        if not query:
            return ""

        # 移除多余空白字符
        processed = re.sub(r"\s+", " ", query.strip())

        # 处理特殊字符
        processed = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()[]{}"\'-]', "", processed)

        # 统一标点符号
        processed = re.sub(
            r"[，。！？；：]",
            lambda m: {"，": ",", "。": ".", "！": "!", "？": "?", "；": ";", "：": ":"}[
                m.group()
            ],
            processed,
        )

        # 处理英文大小写
        processed = (
            processed.lower() if self._is_english_heavy(processed) else processed
        )

        return processed.strip()

    def _is_english_heavy(self, text: str) -> bool:
        """判断是否以英文为主"""
        if not text:
            return False

        english_chars = len(re.findall(r"[a-zA-Z]", text))
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(re.findall(r"\w", text))

        return english_chars > chinese_chars and total_chars > 0

    async def _extract_context(self, session_id: str) -> QueryContext:
        """
        提取查询上下文

        Args:
            session_id: 会话ID

        Returns:
            QueryContext: 上下文信息
        """
        # 这里应该从数据库或缓存中获取实际的上下文信息
        # 暂时返回模拟上下文
        return QueryContext(
            session_id=session_id,
            session_topic="通用对话",
            recent_intents=[],
            uploaded_files=[],
            user_preferences={},
            interaction_history=[],
            time_of_day=datetime.now().strftime("%H:%M"),
            query_count_in_session=1,
        )

    async def _build_classification_request(
        self, query: str, context: QueryContext
    ) -> str:
        """
        构建分类请求

        Args:
            query: 处理后的查询
            context: 查询上下文

        Returns:
            str: 分类请求文本
        """
        request_parts = []

        # 基本查询信息
        request_parts.append(f"【用户问题】")
        request_parts.append(query)

        # 上下文信息
        if context.session_topic:
            request_parts.append(f"【会话主题】")
            request_parts.append(context.session_topic)

        if context.recent_intents:
            request_parts.append(f"【最近意图】")
            request_parts.append(", ".join(context.recent_intents[-3:]))

        if context.uploaded_files:
            file_names = [f["name"] for f in context.uploaded_files]
            request_parts.append(f"【上传文件】")
            request_parts.append(", ".join(file_names))

        if context.user_preferences:
            request_parts.append(f"【用户偏好】")
            request_parts.append(
                json.dumps(context.user_preferences, ensure_ascii=False)
            )

        return "\n\n".join(request_parts)

    async def _call_llm_for_classification(self, prompt: str) -> str:
        """
        调用LLM进行分类

        Args:
            prompt: 分类Prompt

        Returns:
            str: LLM响应
        """
        try:
            # 这里应该调用实际的LLM
            # 暂时返回模拟响应
            return await self._simulate_llm_response(prompt)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise

    async def _simulate_llm_response(self, prompt: str) -> str:
        """
        模拟LLM响应（用于演示）

        Args:
            prompt: 分类Prompt

        Returns:
            str: 模拟的LLM响应
        """
        # 简单的关键词匹配逻辑来模拟分类
        query_lower = prompt.lower()

        # 检查各种分类的关键词
        if any(keyword in query_lower for keyword in ["什么是", "如何", "告诉我", "解释", "定义"]):
            intent = "knowledge_retrieval"
            confidence = 0.85
            reasoning = "问题包含知识查询相关的关键词"
        elif any(
            keyword in query_lower
            for keyword in [
                "cost estimate",
                "cost estimation",
                "budget",
                "overrun",
                "construction cost",
                "成本",
                "预算",
                "估算",
                "超支",
            ]
        ):
            intent = "cost_estimation"
            confidence = 0.91
            reasoning = "问题涉及工程成本估算相关操作"
        elif any(
            keyword in query_lower for keyword in ["分析", "统计", "图表", "数据", "dataset"]
        ):
            intent = "data_analysis"
            confidence = 0.90
            reasoning = "问题涉及数据分析相关操作"
        elif any(
            keyword in query_lower for keyword in ["pdf", "图片", "ocr", "提取", "文档"]
        ):
            intent = "document_processing"
            confidence = 0.88
            reasoning = "问题提到文档处理或OCR相关"
        elif any(keyword in query_lower for keyword in ["运行", "执行", "代码", "计算", "程序"]):
            intent = "code_execution"
            confidence = 0.87
            reasoning = "问题涉及代码执行或计算任务"
        else:
            intent = "unclear_intent"
            confidence = 0.45
            reasoning = "无法明确识别用户意图"

        # 提取关键词
        keywords = []
        if "数据" in query_lower:
            keywords.append("数据")
        if "分析" in query_lower:
            keywords.append("分析")
        if "pdf" in query_lower:
            keywords.append("PDF")
        if "代码" in query_lower:
            keywords.append("代码")

        return json.dumps(
            {
                "intent": intent,
                "confidence": confidence,
                "reasoning": reasoning,
                "keywords": keywords,
                "context_clues": [],
                "suggested_action": f"路由到{intent}处理模块",
                "uncertainty_factors": [] if confidence > 0.7 else ["查询信息不够充分"],
            },
            ensure_ascii=False,
        )

    async def _parse_classification_result(self, llm_response: str) -> IntentResult:
        """
        解析LLM分类结果

        Args:
            llm_response: LLM响应

        Returns:
            IntentResult: 解析后的分类结果
        """
        try:
            # 尝试解析JSON响应
            if llm_response.strip().startswith("{"):
                data = json.loads(llm_response)
            else:
                # 如果不是JSON格式，尝试提取JSON部分
                json_match = re.search(r"\{.*\}", llm_response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("无法从响应中提取JSON数据")

            # 创建IntentResult
            intent_value = data.get("intent", "unclear_intent")
            intent = (
                IntentType(intent_value)
                if intent_value in [e.value for e in IntentType]
                else IntentType.UNCLEAR_INTENT
            )

            sub_intent_value = data.get("sub_intent")
            sub_intent = None
            if sub_intent_value and sub_intent_value in [
                e.value for e in SubIntentType
            ]:
                sub_intent = SubIntentType(sub_intent_value)

            return IntentResult(
                intent=intent,
                sub_intent=sub_intent,
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning", ""),
                keywords=data.get("keywords", []),
                context_clues=data.get("context_clues", []),
                suggested_action=data.get("suggested_action", ""),
                uncertainty_factors=data.get("uncertainty_factors", []),
            )

        except Exception as e:
            logger.error(f"解析分类结果失败: {e}")
            # 返回默认结果
            return IntentResult(
                intent=IntentType.UNCLEAR_INTENT,
                confidence=0.0,
                reasoning=f"解析失败: {str(e)}",
            )

    async def _post_process_result(
        self, result: IntentResult, original_query: str, context: QueryContext
    ) -> IntentResult:
        """
        后处理和验证分类结果

        Args:
            result: 原始分类结果
            original_query: 原始查询
            context: 查询上下文

        Returns:
            IntentResult: 后处理的分类结果
        """
        # 验证置信度范围
        result.confidence = max(0.0, min(1.0, result.confidence))

        # 基于上下文调整置信度
        if (
            context.recent_intents
            and result.intent.value in context.recent_intents[-2:]
        ):
            # 如果与最近的意图一致，增加置信度
            result.confidence = min(1.0, result.confidence + 0.1)
            result.reasoning += f" (与最近意图 '{result.intent.value}' 一致，置信度提升)"

        # 基于上传文件调整
        if context.uploaded_files:
            file_types = [f.get("type", "") for f in context.uploaded_files]
            if "data" in file_types and result.intent == IntentType.DATA_ANALYSIS:
                result.confidence = min(1.0, result.confidence + 0.15)
                result.reasoning += " (用户上传了数据文件，加强数据分析意图判断)"
            elif (
                any("pdf" in ft.lower() or "image" in ft.lower() for ft in file_types)
                and result.intent == IntentType.DOCUMENT_PROCESSING
            ):
                result.confidence = min(1.0, result.confidence + 0.15)
                result.reasoning += " (用户上传了文档/图片，加强文档处理意图判断)"

        # 添加关键词到推理
        if result.keywords:
            result.reasoning += f" (识别关键词: {', '.join(result.keywords)})"

        # 确定建议动作
        result.suggested_action = self._get_suggested_action(result.intent)

        return result

    def _get_suggested_action(self, intent: IntentType) -> str:
        """获取建议的处理动作"""
        actions = {
            IntentType.KNOWLEDGE_RETRIEVAL: "调用RAG检索系统进行知识查询",
            IntentType.DATA_ANALYSIS: "启动数据分析Agent处理数据任务",
            IntentType.COST_ESTIMATION: "启动成本估算模型进行预算与超支预测",
            IntentType.DOCUMENT_PROCESSING: "启动OCR Agent处理文档提取任务",
            IntentType.CODE_EXECUTION: "启动代码执行Agent运行计算任务",
            IntentType.UNCLEAR_INTENT: "启动澄清对话确认用户意图",
        }
        return actions.get(intent, "启动通用处理流程")

    def _generate_cache_key(self, query: str, context: QueryContext) -> str:
        """生成缓存键"""
        key_data = {
            "query": query,
            "recent_intents": context.recent_intents[-2:]
            if context.recent_intents
            else [],
            "has_files": len(context.uploaded_files) > 0,
        }
        return hash(json.dumps(key_data, sort_keys=True)).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[IntentResult]:
        """从缓存获取结果"""
        if cache_key in self._classification_cache:
            result, cached_at = self._classification_cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=self.cache_ttl):
                return result
            else:
                del self._classification_cache[cache_key]
        return None

    def _save_to_cache(self, cache_key: str, result: IntentResult):
        """保存到缓存"""
        self._classification_cache[cache_key] = (result, datetime.now())

        # 限制缓存大小
        if len(self._classification_cache) > 1000:
            # 删除最旧的缓存项
            oldest_key = min(
                self._classification_cache.keys(),
                key=lambda k: self._classification_cache[k][1],
            )
            del self._classification_cache[oldest_key]

    def _update_stats(self, result: IntentResult):
        """更新统计信息"""
        self.stats["total_classifications"] += 1
        if result.is_high_confidence:
            self.stats["high_confidence_count"] += 1
        if result.is_uncertain:
            self.stats["clarification_count"] += 1

        # 更新平均置信度
        total = self.stats["total_classifications"]
        current_avg = self.stats["avg_confidence"]
        self.stats["avg_confidence"] = (
            (current_avg * (total - 1)) + result.confidence
        ) / total

    async def get_clarification_prompt(self, query: str, result: IntentResult) -> str:
        """
        获取澄清对话Prompt

        Args:
            query: 用户查询
            result: 分类结果

        Returns:
            str: 澄清问句
        """
        try:
            prompt_info, prompt_content = await self.prompt_manager.get_prompt(
                name="intent_clarification",
                category="Intent",
                context={"confidence": result.confidence},
                variables={
                    "user_query": query,
                    "possible_intents": json.dumps(
                        [
                            {"type": "knowledge_retrieval", "desc": "知识查询和回答"},
                            {"type": "data_analysis", "desc": "数据分析和可视化"},
                            {"type": "cost_estimation", "desc": "工程成本估算与超支预测"},
                            {"type": "document_processing", "desc": "文档处理和OCR"},
                            {"type": "code_execution", "desc": "代码执行和计算"},
                        ],
                        ensure_ascii=False,
                    ),
                },
            )

            # 模拟LLM调用
            return await self._simulate_clarification_response(query, result)

        except Exception as e:
            logger.error(f"获取澄清Prompt失败: {e}")
            return f"抱歉，我没有完全理解您的问题。您是想：1. 查询知识信息 2. 分析数据 3. 处理文档 4. 执行代码 请选择一个选项。"

    async def _simulate_clarification_response(
        self, query: str, result: IntentResult
    ) -> str:
        """模拟澄清响应"""
        return f"""抱歉，我没有完全理解您的问题"{query}"。根据我的分析，您可能想要：

1. **知识查询** - 获取特定信息或答案
2. **数据分析** - 对数据进行分析或可视化
3. **文档处理** - 从PDF或图片中提取信息
4. **代码执行** - 运行特定的计算或程序

请告诉我您想要哪种类型的帮助，这样我可以为您提供更准确的服务。"""

    async def route_to_agent(
        self, result: IntentResult, context: QueryContext
    ) -> Dict[str, Any]:
        """
        路由到对应的Agent

        Args:
            result: 分类结果
            context: 查询上下文

        Returns:
            Dict[str, Any]: 路由信息
        """
        routing_info = {
            "success": True,
            "intent": result.intent.value,
            "sub_intent": result.sub_intent.value if result.sub_intent else None,
            "confidence": result.confidence,
            "agent_type": self._get_agent_type(result.intent),
            "routing_reason": result.reasoning,
            "requires_clarification": result.is_uncertain,
            "suggested_action": result.suggested_action,
        }

        # 添加特定的路由参数
        if result.intent == IntentType.DATA_ANALYSIS:
            routing_info.update(
                {
                    "requires_docker": True,
                    "supported_formats": ["csv", "excel", "json", "parquet"],
                    "default_visualization": True,
                }
            )
        elif result.intent == IntentType.COST_ESTIMATION:
            routing_info.update(
                {
                    "supported_formats": ["csv", "excel", "json"],
                    "model_inference": True,
                    "prediction_targets": ["cost_overrun_pct", "actual_cost_cad"],
                }
            )
        elif result.intent == IntentType.DOCUMENT_PROCESSING:
            routing_info.update(
                {
                    "supported_formats": ["pdf", "jpg", "png", "tiff"],
                    "ocr_engines": ["pytesseract", "deepscan"],
                    "output_format": "text",
                }
            )
        elif result.intent == IntentType.CODE_EXECUTION:
            routing_info.update(
                {
                    "supported_languages": ["python", "javascript", "sql"],
                    "execution_timeout": 30,
                    "safety_checks": True,
                }
            )

        return routing_info

    def _get_agent_type(self, intent: IntentType) -> str:
        """获取对应的Agent类型"""
        agent_mapping = {
            IntentType.KNOWLEDGE_RETRIEVAL: "RAGAgent",
            IntentType.DATA_ANALYSIS: "DataAnalysisAgent",
            IntentType.COST_ESTIMATION: "DataAnalysisAgent",
            IntentType.DOCUMENT_PROCESSING: "OCRAgent",
            IntentType.CODE_EXECUTION: "CodeExecutorAgent",
            IntentType.UNCLEAR_INTENT: "ClarificationAgent",
        }
        return agent_mapping.get(intent, "GeneralAgent")

    def get_stats(self) -> Dict[str, Any]:
        """获取分类器统计信息"""
        total = self.stats["total_classifications"]
        return {
            **self.stats,
            "high_confidence_rate": (
                self.stats["high_confidence_count"] / max(total, 1)
            ),
            "clarification_rate": (self.stats["clarification_count"] / max(total, 1)),
            "cache_hit_rate": (self.stats["cache_hits"] / max(total, 1)),
            "cache_size": len(self._classification_cache),
        }

    def clear_cache(self):
        """清空缓存"""
        self._classification_cache.clear()
        logger.info("分类缓存已清空")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试Prompt管理器连接
            test_prompt, _ = await self.prompt_manager.get_prompt(
                name="intent_classification", category="Intent"
            )

            return {
                "status": "healthy",
                "prompt_manager": "connected",
                "cache_size": len(self._classification_cache),
                "confidence_threshold": self.confidence_threshold,
                "stats": self.get_stats(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "prompt_manager": "disconnected",
            }
