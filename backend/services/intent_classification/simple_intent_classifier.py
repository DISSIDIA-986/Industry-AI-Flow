"""
简化的意图分类器 - 无需数据库依赖的版本
用于测试和独立运行场景
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型枚举"""

    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"  # 知识检索类
    DATA_ANALYSIS = "data_analysis"  # 数据分析类
    DOCUMENT_PROCESSING = "document_processing"  # 文档处理类
    CODE_EXECUTION = "code_execution"  # 代码执行类
    UNCLEAR_INTENT = "unclear_intent"  # 意图不明确


@dataclass
class SimpleIntentResult:
    """简化的意图分类结果"""

    intent: IntentType
    confidence: float = 0.0
    reasoning: str = ""
    keywords: List[str] = None
    suggested_action: str = ""

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []

    @property
    def is_high_confidence(self) -> bool:
        """判断是否为高置信度"""
        return self.confidence >= 0.7

    @property
    def is_uncertain(self) -> bool:
        """判断是否意图不明确"""
        return self.confidence < 0.5


class SimpleIntentClassifier:
    """
    简化的意图分类器 - 基于规则的轻量级版本

    不依赖数据库和复杂的LLM调用，适用于:
    1. 测试环境
    2. 快速原型开发
    3. 资源受限场景
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """
        初始化简化意图分类器

        Args:
            confidence_threshold: 置信度阈值
        """
        self.confidence_threshold = confidence_threshold

        # 关键词规则库
        self._keyword_rules = self._build_keyword_rules()

        # 统计信息
        self.stats = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "intent_distribution": {},
        }

        logger.info("简化意图分类器初始化完成")

    def _build_keyword_rules(self) -> Dict[IntentType, Dict[str, Any]]:
        """构建关键词规则库"""
        return {
            IntentType.KNOWLEDGE_RETRIEVAL: {
                "keywords": [
                    # 英文
                    "what is",
                    "how does",
                    "explain",
                    "define",
                    "tell me",
                    "describe",
                    "show me",
                    "information about",
                    "details of",
                    "concept",
                    "principle",
                    "mechanism",
                    "theory",
                    # 中文
                    "什么是",
                    "如何",
                    "怎么",
                    "解释",
                    "说明",
                    "告诉我",
                    "定义",
                    "原理",
                    "机制",
                    "概念",
                    "介绍",
                ],
                "patterns": [
                    r"what\s+(is|are|does)",
                    r"how\s+(does|do|to)",
                    r"(explain|describe|tell)\s+me",
                    r"什么是",
                    r"如何.*工作",
                ],
                "priority": 1,
            },
            IntentType.DATA_ANALYSIS: {
                "keywords": [
                    # 英文 - 分析类
                    "analyze",
                    "analysis",
                    "statistics",
                    "stat",
                    "calculate",
                    "compute",
                    "summarize",
                    "aggregate",
                    "trend",
                    "pattern",
                    # 英文 - 数据类
                    "data",
                    "dataset",
                    "csv",
                    "excel",
                    "table",
                    "column",
                    "row",
                    "record",
                    "field",
                    "value",
                    "distribution",
                    # 英文 - 查询类
                    "average",
                    "mean",
                    "median",
                    "max",
                    "min",
                    "sum",
                    "count",
                    "highest",
                    "lowest",
                    "most",
                    "least",
                    "percentage",
                    "ratio",
                    "correlation",
                    "variance",
                    "standard deviation",
                    # 英文 - 比较类
                    "compare",
                    "comparison",
                    "versus",
                    "vs",
                    "difference",
                    "between",
                    "among",
                    "relation",
                    "relationship",
                    # 英文 - 可视化类
                    "chart",
                    "graph",
                    "plot",
                    "visualization",
                    "visualize",
                    "histogram",
                    "scatter",
                    "bar chart",
                    "line plot",
                    # 中文 - 分析类
                    "分析",
                    "统计",
                    "计算",
                    "汇总",
                    "趋势",
                    "模式",
                    # 中文 - 数据类
                    "数据",
                    "数据集",
                    "表格",
                    "列",
                    "行",
                    "记录",
                    "字段",
                    "值",
                    "分布",
                    # 中文 - 查询类
                    "平均",
                    "均值",
                    "中位数",
                    "最大",
                    "最小",
                    "总和",
                    "数量",
                    "最高",
                    "最低",
                    "百分比",
                    "比例",
                    "相关",
                    # 中文 - 比较类
                    "对比",
                    "比较",
                    "差异",
                    "之间",
                    "关系",
                    # 中文 - 可视化类
                    "图表",
                    "可视化",
                    "柱状图",
                    "折线图",
                    "散点图",
                ],
                "patterns": [
                    r"(analyze|analysis|calculate)\s+",
                    r"(average|mean|median|max|min|sum|count)\s+",
                    r"(highest|lowest|most|least)\s+",
                    r"(compare|comparison|versus|vs)\s+",
                    r"what\s+(is|are)\s+the\s+(average|max|min|total)",
                    r"how\s+many",
                    r"(percentage|ratio)\s+of",
                    r"分析.*数据",
                    r"(平均|最大|最小|总和|数量)",
                    r"(对比|比较).*数据",
                    r"多少.*百分比",
                ],
                "priority": 2,  # 高优先级，因为数据分析更具体
            },
            IntentType.DOCUMENT_PROCESSING: {
                "keywords": [
                    # 英文
                    "pdf",
                    "document",
                    "file",
                    "image",
                    "picture",
                    "photo",
                    "scan",
                    "ocr",
                    "extract",
                    "extract text",
                    "read document",
                    "parse",
                    "convert",
                    "jpg",
                    "png",
                    "tiff",
                    "jpeg",
                    # 中文
                    "pdf",
                    "文档",
                    "文件",
                    "图片",
                    "照片",
                    "扫描",
                    "识别",
                    "提取",
                    "解析",
                    "转换",
                    "读取文档",
                ],
                "patterns": [
                    r"(extract|read|parse)\s+(text|content)\s+from",
                    r"ocr\s+",
                    r"(pdf|document|image|file)\s+",
                    r"提取.*文本",
                    r"识别.*文档",
                ],
                "priority": 1,
            },
            IntentType.CODE_EXECUTION: {
                "keywords": [
                    # 英文
                    "run",
                    "execute",
                    "code",
                    "script",
                    "program",
                    "compute",
                    "calculation",
                    "algorithm",
                    "function",
                    "implement",
                    "process",
                    "batch",
                    "automation",
                    # 中文
                    "运行",
                    "执行",
                    "代码",
                    "脚本",
                    "程序",
                    "计算",
                    "算法",
                    "函数",
                    "实现",
                    "处理",
                    "批处理",
                    "自动化",
                ],
                "patterns": [
                    r"(run|execute)\s+(code|script|program)",
                    r"implement\s+",
                    r"运行.*代码",
                    r"执行.*脚本",
                ],
                "priority": 1,
            },
        }

    def classify_intent(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> SimpleIntentResult:
        """
        分类用户意图

        Args:
            query: 用户查询
            context: 可选的上下文信息（如上传的文件信息）

        Returns:
            SimpleIntentResult: 分类结果
        """
        try:
            # 预处理查询
            processed_query = self._preprocess_query(query)

            # 计算每个意图的得分
            intent_scores = {}

            for intent_type, rules in self._keyword_rules.items():
                score, matched_keywords = self._calculate_intent_score(
                    processed_query, rules
                )

                if score > 0:
                    intent_scores[intent_type] = {
                        "score": score,
                        "keywords": matched_keywords,
                    }

            # 基于上下文调整得分
            if context:
                intent_scores = self._adjust_scores_with_context(intent_scores, context)

            # 选择最高得分的意图
            if not intent_scores:
                # 没有匹配任何规则
                result = SimpleIntentResult(
                    intent=IntentType.UNCLEAR_INTENT,
                    confidence=0.3,
                    reasoning="未能识别明确的意图模式",
                    suggested_action="启动澄清对话确认用户意图",
                )
            else:
                # 选择得分最高的意图
                best_intent = max(intent_scores.items(), key=lambda x: x[1]["score"])
                intent_type, intent_data = best_intent

                # 计算置信度（归一化得分）
                max_possible_score = 100.0  # 假设的最大得分
                confidence = min(intent_data["score"] / max_possible_score, 1.0)

                # 构建推理说明
                reasoning = f"识别到{len(intent_data['keywords'])}个相关关键词: {', '.join(intent_data['keywords'][:3])}"

                result = SimpleIntentResult(
                    intent=intent_type,
                    confidence=confidence,
                    reasoning=reasoning,
                    keywords=intent_data["keywords"],
                    suggested_action=self._get_suggested_action(intent_type),
                )

            # 更新统计
            self._update_stats(result)

            logger.info(f"意图分类: {result.intent.value} (置信度: {result.confidence:.2f})")
            return result

        except Exception as e:
            logger.error(f"意图分类失败: {e}")
            return SimpleIntentResult(
                intent=IntentType.UNCLEAR_INTENT,
                confidence=0.0,
                reasoning=f"分类过程出错: {str(e)}",
                suggested_action="启动澄清对话确认用户意图",
            )

    def _preprocess_query(self, query: str) -> str:
        """预处理查询文本"""
        # 转小写
        processed = query.lower()

        # 移除多余空白
        processed = re.sub(r"\s+", " ", processed).strip()

        return processed

    def _calculate_intent_score(self, query: str, rules: Dict[str, Any]) -> tuple:
        """
        计算意图得分

        Args:
            query: 处理后的查询
            rules: 意图规则

        Returns:
            tuple: (得分, 匹配的关键词列表)
        """
        score = 0.0
        matched_keywords = []

        # 关键词匹配
        keywords = rules.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in query:
                # 基础得分
                base_score = 10.0

                # 位置加权：出现在开头得分更高
                if query.startswith(keyword.lower()):
                    base_score *= 1.5

                # 长度加权：更长的关键词得分更高
                if len(keyword.split()) > 1:
                    base_score *= 1.2

                score += base_score
                matched_keywords.append(keyword)

        # 正则模式匹配
        patterns = rules.get("patterns", [])
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += 15.0  # 模式匹配得分更高

        # 优先级加权
        priority = rules.get("priority", 1)
        score *= priority

        return score, matched_keywords

    def _adjust_scores_with_context(
        self, intent_scores: Dict[IntentType, Dict], context: Dict[str, Any]
    ) -> Dict[IntentType, Dict]:
        """基于上下文调整得分"""
        # 检查是否有上传的文件
        uploaded_files = context.get("uploaded_files", [])

        if uploaded_files:
            for file_info in uploaded_files:
                file_type = file_info.get("type", "").lower()
                file_ext = file_info.get("extension", "").lower()

                # CSV/Excel文件增强数据分析意图
                if file_ext in [".csv", ".xlsx", ".xls"] or "spreadsheet" in file_type:
                    if IntentType.DATA_ANALYSIS in intent_scores:
                        intent_scores[IntentType.DATA_ANALYSIS]["score"] *= 1.5
                        intent_scores[IntentType.DATA_ANALYSIS]["keywords"].append(
                            "detected_csv_file"
                        )

                # PDF/图片文件增强文档处理意图
                elif (
                    file_ext in [".pdf", ".jpg", ".png", ".jpeg", ".tiff"]
                    or "image" in file_type
                    or "pdf" in file_type
                ):
                    if IntentType.DOCUMENT_PROCESSING in intent_scores:
                        intent_scores[IntentType.DOCUMENT_PROCESSING]["score"] *= 1.5
                        intent_scores[IntentType.DOCUMENT_PROCESSING][
                            "keywords"
                        ].append("detected_document_file")

        return intent_scores

    def _get_suggested_action(self, intent: IntentType) -> str:
        """获取建议的处理动作"""
        actions = {
            IntentType.KNOWLEDGE_RETRIEVAL: "调用RAG检索系统进行知识查询",
            IntentType.DATA_ANALYSIS: "启动数据分析Agent处理数据任务",
            IntentType.DOCUMENT_PROCESSING: "启动OCR Agent处理文档提取任务",
            IntentType.CODE_EXECUTION: "启动代码执行Agent运行计算任务",
            IntentType.UNCLEAR_INTENT: "启动澄清对话确认用户意图",
        }
        return actions.get(intent, "启动通用处理流程")

    def _update_stats(self, result: SimpleIntentResult):
        """更新统计信息"""
        self.stats["total_classifications"] += 1

        if result.is_high_confidence:
            self.stats["high_confidence_count"] += 1

        intent_value = result.intent.value
        if intent_value not in self.stats["intent_distribution"]:
            self.stats["intent_distribution"][intent_value] = 0
        self.stats["intent_distribution"][intent_value] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取分类器统计信息"""
        total = self.stats["total_classifications"]
        return {
            **self.stats,
            "high_confidence_rate": (
                self.stats["high_confidence_count"] / max(total, 1)
            ),
        }


# 全局实例
simple_intent_classifier = SimpleIntentClassifier()
