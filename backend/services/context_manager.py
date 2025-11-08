"""
上下文管理服务
为意图分类器提供丰富的上下文信息，包括会话历史、文件信息、用户偏好等
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FileContext:
    """文件上下文信息"""

    file_id: str
    file_name: str
    file_type: str
    file_size: int
    upload_time: datetime
    file_path: str
    preview: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["upload_time"] = self.upload_time.isoformat()
        return data


@dataclass
class InteractionRecord:
    """交互记录"""

    record_id: str
    timestamp: datetime
    user_query: str
    classified_intent: str
    agent_response: str
    confidence: float
    processing_time_ms: int
    user_feedback: Optional[int] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class SessionContext:
    """会话上下文"""

    session_id: str
    user_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    query_count: int = 0
    session_topic: str = ""
    session_stage: str = "initial"  # initial, exploring, deep_dive, closing
    language_preference: str = "auto"
    uploaded_files: List[FileContext] = field(default_factory=list)
    interaction_history: List[InteractionRecord] = field(default_factory=list)
    detected_intents: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    context_keywords: List[str] = field(default_factory=list)
    completion_rate: float = 0.0
    satisfaction_score: Optional[float] = None

    def add_interaction(self, record: InteractionRecord):
        """添加交互记录"""
        self.interaction_history.append(record)
        self.last_activity = record.timestamp
        self.query_count += 1

        # 更新检测到的意图
        if record.classified_intent not in self.detected_intents:
            self.detected_intents.append(record.classified_intent)
            # 只保留最近10个意图
            if len(self.detected_intents) > 10:
                self.detected_intents = self.detected_intents[-10:]

        # 更新完成率
        successful_interactions = sum(1 for r in self.interaction_history if r.success)
        self.completion_rate = successful_interactions / max(
            len(self.interaction_history), 1
        )

    def add_uploaded_file(self, file_context: FileContext):
        """添加上传文件"""
        self.uploaded_files.append(file_context)
        # 只保留最近10个文件
        if len(self.uploaded_files) > 10:
            self.uploaded_files = self.uploaded_files[-10:]

    def get_recent_intents(self, limit: int = 5) -> List[str]:
        """获取最近的意图列表"""
        return self.detected_intents[-limit:] if self.detected_intents else []

    def get_session_duration(self) -> float:
        """获取会话持续时间（秒）"""
        return (self.last_activity - self.start_time).total_seconds()

    def update_session_stage(self):
        """更新会话阶段"""
        duration = self.get_session_duration()
        query_count = self.query_count

        if duration < 60:  # 1分钟内
            self.session_stage = "initial"
        elif query_count < 3:
            self.session_stage = "exploring"
        elif query_count < 10:
            self.session_stage = "deep_dive"
        else:
            self.session_stage = "closing"

    def get_context_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "session_id": self.session_id,
            "duration_minutes": round(self.get_session_duration() / 60, 1),
            "query_count": self.query_count,
            "stage": self.session_stage,
            "topic": self.session_topic,
            "language": self.language_preference,
            "uploaded_files_count": len(self.uploaded_files),
            "completion_rate": self.completion_rate,
            "detected_intents": self.get_recent_intents(),
        }


class ContextManager:
    """上下文管理器"""

    def __init__(self, storage_backend: str = "memory", cache_ttl: int = 3600):
        """
        初始化上下文管理器

        Args:
            storage_backend: 存储后端 ("memory", "database", "redis")
            cache_ttl: 缓存过期时间（秒）
        """
        self.storage_backend = storage_backend
        self.cache_ttl = cache_ttl

        # 内存缓存
        self._session_cache: Dict[str, SessionContext] = {}
        self._file_cache: Dict[str, FileContext] = {}

        # 统计信息
        self.stats = {
            "active_sessions": 0,
            "total_interactions": 0,
            "avg_session_duration": 0.0,
            "cache_hits": 0,
        }

        logger.info(f"上下文管理器初始化完成，后端: {storage_backend}")

    async def get_session_context(
        self, session_id: str, user_id: Optional[str] = None
    ) -> SessionContext:
        """
        获取会话上下文

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            SessionContext: 会话上下文
        """
        # 检查缓存
        if session_id in self._session_cache:
            session = self._session_cache[session_id]
            # 验证会话是否仍然有效（24小时内有活动）
            if (datetime.now() - session.last_activity).total_seconds() < 86400:
                self.stats["cache_hits"] += 1
                logger.debug(f"从缓存获取会话: {session_id}")
                return session
            else:
                # 会话过期，从缓存中移除
                del self._session_cache[session_id]

        # 创建新会话或从存储加载
        session = await self._load_session_from_storage(session_id, user_id)

        # 添加到缓存
        self._session_cache[session_id] = session
        self._update_active_sessions_count()

        logger.info(f"创建/加载会话上下文: {session_id}")
        return session

    async def update_session_context(
        self, session_id: str, updates: Dict[str, Any]
    ) -> SessionContext:
        """
        更新会话上下文

        Args:
            session_id: 会话ID
            updates: 更新字段

        Returns:
            SessionContext: 更新后的会话上下文
        """
        session = await self.get_session_context(session_id)

        # 应用更新
        for field, value in updates.items():
            if hasattr(session, field):
                setattr(session, field, value)

        session.last_activity = datetime.now()
        session.update_session_stage()

        # 保存到存储
        await self._save_session_to_storage(session)

        # 更新缓存
        self._session_cache[session_id] = session

        return session

    async def add_interaction_record(
        self,
        session_id: str,
        user_query: str,
        classified_intent: str,
        agent_response: str,
        confidence: float,
        processing_time_ms: int,
        user_feedback: Optional[int] = None,
        success: bool = True,
    ) -> None:
        """
        添加交互记录

        Args:
            session_id: 会话ID
            user_query: 用户查询
            classified_intent: 分类意图
            agent_response: Agent响应
            confidence: 置信度
            processing_time_ms: 处理时间
            user_feedback: 用户反馈
            success: 是否成功
        """
        session = await self.get_session_context(session_id)

        record = InteractionRecord(
            record_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            user_query=user_query,
            classified_intent=classified_intent,
            agent_response=agent_response,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            user_feedback=user_feedback,
            success=success,
        )

        session.add_interaction(record)
        session.detected_intents.append(classified_intent)

        # 更新满意度分数（基于用户反馈）
        if user_feedback is not None:
            if session.satisfaction_score is None:
                session.satisfaction_score = user_feedback
            else:
                # 计算移动平均
                session.satisfaction_score = (
                    session.satisfaction_score * 0.8 + user_feedback * 0.2
                )

        await self._save_session_to_storage(session)
        self._session_cache[session_id] = session

        self.stats["total_interactions"] += 1

    async def add_uploaded_file(
        self,
        session_id: str,
        file_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
        file_path: str,
        preview: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加上传文件记录

        Args:
            session_id: 会话ID
            file_id: 文件ID
            file_name: 文件名
            file_type: 文件类型
            file_size: 文件大小
            file_path: 文件路径
            preview: 文件预览
            metadata: 文件元数据
        """
        file_context = FileContext(
            file_id=file_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            file_path=file_path,
            preview=preview,
            metadata=metadata or {},
        )

        session = await self.get_session_context(session_id)
        session.add_uploaded_file(file_context)

        # 更新会话主题（如果这是第一个文件）
        if len(session.uploaded_files) == 1:
            session.session_topic = f"文件处理: {file_name}"

        await self._save_session_to_storage(session)
        self._session_cache[session_id] = session

    async def get_enhanced_context(
        self, session_id: str, max_history: int = 10, include_files: bool = True
    ) -> Dict[str, Any]:
        """
        获取增强的上下文信息

        Args:
            session_id: 会话ID
            max_history: 最大历史记录数
            include_files: 是否包含文件信息

        Returns:
            Dict[str, Any]: 增强的上下文信息
        """
        session = await self.get_session_context(session_id)

        # 基础上下文
        context = {
            "session_info": session.get_context_summary(),
            "recent_intents": session.get_recent_intents(),
            "interaction_count": session.query_count,
            "session_stage": session.session_stage,
        }

        # 历史交互
        if session.interaction_history:
            recent_history = session.interaction_history[-max_history:]
            context["interaction_history"] = [
                record.to_dict() for record in recent_history
            ]

        # 文件信息
        if include_files and session.uploaded_files:
            context["file_context"] = {
                "total_files": len(session.uploaded_files),
                "recent_files": [
                    file.to_dict() for file in session.uploaded_files[-3:]
                ],
                "file_types": list(
                    set(file.file_type for file in session.uploaded_files)
                ),
            }

        # 用户偏好
        if session.user_preferences:
            context["user_preferences"] = session.user_preferences

        # 上下文关键词
        context_keywords = []

        # 从交互历史中提取关键词
        for record in session.interaction_history[-5:]:
            context_keywords.extend(self._extract_keywords(record.user_query))
            context_keywords.extend(self._extract_keywords(record.agent_response))

        # 从文件名中提取关键词
        for file in session.uploaded_files[-3:]:
            context_keywords.append(file.file_name)

        # 去重并清理
        context["context_keywords"] = list(
            set(
                word
                for word in context_keywords
                if len(word) > 1
                and word.lower()
                not in [
                    "the",
                    "a",
                    "an",
                    "and",
                    "or",
                    "but",
                    "in",
                    "on",
                    "at",
                    "to",
                    "for",
                    "of",
                    "with",
                    "by",
                    "this",
                    "that",
                    "is",
                    "are",
                    "be",
                    "have",
                    "has",
                    "what",
                    "when",
                    "where",
                    "why",
                    "how",
                    "all",
                    "any",
                    "can",
                    "could",
                    "would",
                    "should",
                    "will",
                ]
            )
        )[
            :20
        ]  # 限制关键词数量

        return context

    async def analyze_session_patterns(self, session_id: str) -> Dict[str, Any]:
        """
        分析会话模式

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 会话模式分析结果
        """
        session = await self.get_session_context(session_id)

        if not session.interaction_history:
            return {"status": "no_data"}

        patterns = {
            "query_patterns": self._analyze_query_patterns(session),
            "intent_evolution": self._analyze_intent_evolution(session),
            "time_distribution": self._analyze_time_distribution(session),
            "success_patterns": self._analyze_success_patterns(session),
            "interaction_rhythm": self._analyze_interaction_rhythm(session),
        }

        return patterns

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        if not text:
            return []

        # 简单的关键词提取
        words = re.findall(r"\b[a-zA-Z\u4e00-\u9fff]{2,}\b", text.lower())
        return words

    def _analyze_query_patterns(self, session: SessionContext) -> Dict[str, Any]:
        """分析查询模式"""
        if not session.interaction_history:
            return {}

        queries = [record.user_query for record in session.interaction_history]

        # 查询长度分析
        lengths = [len(query) for query in queries]

        # 查询类型分析
        question_count = sum(1 for query in queries if "?" in query or "？" in query)
        statement_count = sum(
            1 for query in queries if query.endswith(".") or query.endswith("。")
        )

        return {
            "avg_query_length": sum(lengths) / max(len(lengths), 1),
            "max_query_length": max(lengths) if lengths else 0,
            "min_query_length": min(lengths) if lengths else 0,
            "question_ratio": question_count / max(len(queries), 1),
            "statement_ratio": statement_count / max(len(queries), 1),
        }

    def _analyze_intent_evolution(self, session: SessionContext) -> Dict[str, Any]:
        """分析意图演化"""
        if len(session.detected_intents) < 2:
            return {"status": "insufficient_data"}

        # 意图变化分析
        intent_changes = 0
        for i in range(1, len(session.detected_intents)):
            if session.detected_intents[i] != session.detected_intents[i - 1]:
                intent_changes += 1

        return {
            "total_intents": len(session.detected_intents),
            "unique_intents": len(set(session.detected_intents)),
            "intent_changes": intent_changes,
            "intent_diversity": intent_changes
            / max(len(session.detected_intents) - 1, 1),
            "current_intent": session.detected_intents[-1]
            if session.detected_intents
            else None,
        }

    def _analyze_time_distribution(self, session: SessionContext) -> Dict[str, Any]:
        """分析时间分布"""
        if len(session.interaction_history) < 2:
            return {"status": "insufficient_data"}

        timestamps = [record.timestamp for record in session.interaction_history]

        # 计算交互间隔
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds()
            intervals.append(interval)

        return {
            "total_session_duration": session.get_session_duration(),
            "avg_interaction_interval": sum(intervals) / max(len(intervals), 1),
            "min_interval": min(intervals) if intervals else 0,
            "max_interval": max(intervals) if intervals else 0,
        }

    def _analyze_success_patterns(self, session: SessionContext) -> Dict[str, Any]:
        """分析成功模式"""
        if not session.interaction_history:
            return {"status": "no_data"}

        successful = sum(1 for record in session.interaction_history if record.success)
        total = len(session.interaction_history)

        # 置信度分析
        confidences = [record.confidence for record in session.interaction_history]

        return {
            "success_rate": session.completion_rate,
            "total_interactions": total,
            "successful_interactions": successful,
            "avg_confidence": sum(confidences) / max(len(confidences), 1),
            "high_confidence_rate": sum(1 for c in confidences if c >= 0.8)
            / max(len(confidences), 1),
        }

    def _analyze_interaction_rhythm(self, session: SessionContext) -> Dict[str, Any]:
        """分析交互节奏"""
        if len(session.interaction_history) < 2:
            return {"status": "insufficient_data"}

        timestamps = [record.timestamp for record in session.interaction_history]
        processing_times = [
            record.processing_time_ms for record in session.interaction_history
        ]

        # 计算交互节奏
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds()
            intervals.append(interval)

        return {
            "avg_interaction_interval": sum(intervals) / max(len(intervals), 1),
            "interaction_frequency": len(session.interaction_history)
            / max(session.get_session_duration() / 60, 1),  # 每分钟
            "avg_processing_time": sum(processing_times)
            / max(len(processing_times), 1),
            "processing_time_trend": "stable",  # 简化版本，可以添加趋势分析
        }

    async def _load_session_from_storage(
        self, session_id: str, user_id: Optional[str] = None
    ) -> SessionContext:
        """从存储加载会话"""
        # 模拟从数据库加载
        return SessionContext(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.now() - timedelta(minutes=5),
            last_activity=datetime.now() - timedelta(minutes=1),
            query_count=2,
            session_topic="初始对话",
            detected_intents=["knowledge_retrieval"],
            user_preferences={"language": "zh-CN", "response_style": "professional"},
            context_keywords=["查询", "信息", "帮助"],
        )

    async def _save_session_to_storage(self, session: SessionContext) -> None:
        """保存会话到存储"""
        # 这里应该保存到实际的数据库
        # await database.save_session(session.to_dict())
        pass

    def _update_active_sessions_count(self):
        """更新活跃会话数"""
        current_time = datetime.now()
        active_count = 0

        for session in self._session_cache.values():
            if (current_time - session.last_activity).total_seconds() < 3600:  # 1小时内活跃
                active_count += 1

        self.stats["active_sessions"] = active_count

    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        return {
            **self.stats,
            "cache_size": len(self._session_cache),
            "file_cache_size": len(self._file_cache),
            "storage_backend": self.storage_backend,
        }

    def clear_cache(self):
        """清空缓存"""
        self._session_cache.clear()
        self._file_cache.clear()
        self.stats["cache_hits"] = 0
        logger.info("上下文缓存已清空")

    async def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session in list(self._session_cache.items()):
            age_hours = (current_time - session.last_activity).total_seconds() / 3600
            if age_hours > max_age_hours:
                expired_sessions.append(session_id)
                del self._session_cache[session_id]

        logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
        return len(expired_sessions)

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "storage_backend": self.storage_backend,
            "active_sessions": self.stats["active_sessions"],
            "cache_size": len(self._session_cache),
            "total_interactions": self.stats["total_interactions"],
        }
