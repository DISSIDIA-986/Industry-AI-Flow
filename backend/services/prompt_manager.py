"""
Prompt管理服务 - 集中式Prompt管理、版本控制、性能评估
支持动态Prompt选择、A/B测试、智能优化等功能
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

import asyncpg
import jinja2
from jinja2 import Environment, Template, meta
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)


class PromptStatus(Enum):
    """Prompt状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ExperimentStatus(Enum):
    """实验状态枚举"""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class PromptVariable:
    """Prompt变量定义"""

    name: str
    type: str = "string"  # string, number, boolean, json
    required: bool = True
    default_value: Any = None
    description: str = ""
    validation_regex: str = None
    options: List[Any] = None


@dataclass
class PromptInfo:
    """Prompt信息数据类"""

    id: uuid.UUID
    name: str
    category: str
    subcategory: Optional[str]
    version: str
    content: str
    variables: List[PromptVariable]
    metadata: Dict[str, Any]
    is_active: bool
    is_latest: bool
    priority: int
    performance_score: float
    usage_count: int
    success_count: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    tags: List[str] = None

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["variables"] = (
            [asdict(var) for var in self.variables] if self.variables else []
        )
        data["success_rate"] = self.success_rate
        return data


@dataclass
class UsageLog:
    """使用记录数据类"""

    prompt_id: uuid.UUID
    session_id: Optional[str]
    context: Dict[str, Any]
    variables_used: Dict[str, Any]
    execution_time_ms: int
    success: bool
    error_message: Optional[str]
    user_feedback: Optional[int]
    llm_response: Optional[Dict[str, Any]]
    tokens_used: int
    model_name: Optional[str]
    temperature: Optional[float]


class PromptManager:
    """Prompt管理器 - 核心服务类"""

    def __init__(self, db_pool: asyncpg.Pool, cache_ttl: int = 300):
        """
        初始化Prompt管理器

        Args:
            db_pool: 数据库连接池
            cache_ttl: 缓存过期时间（秒）
        """
        self.db_pool = db_pool
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[PromptInfo, datetime]] = {}
        self._jinja_env = Environment(autoescape=True)

        # 预编译正则表达式
        self._variable_pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")

        logger.info("Prompt管理器初始化完成")

    async def get_prompt(
        self,
        name: str,
        category: str,
        context: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None,
        enable_experiments: bool = True,
    ) -> Tuple[PromptInfo, str]:
        """
        获取最优Prompt并渲染模板

        Args:
            name: Prompt名称
            category: Prompt分类
            context: 使用上下文，用于智能选择
            variables: 变量值字典
            enable_experiments: 是否启用A/B测试

        Returns:
            Tuple[PromptInfo, str]: (Prompt信息, 渲染后的内容)
        """
        cache_key = f"{category}:{name}"

        # 检查缓存
        if cache_key in self._cache:
            prompt_info, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=self.cache_ttl):
                logger.debug(f"从缓存获取Prompt: {cache_key}")
                rendered_content = self._render_template(prompt_info.content, variables)
                return prompt_info, rendered_content

        # 获取最优Prompt
        if enable_experiments:
            prompt_info = await self._get_prompt_with_experiment(
                name, category, context
            )
        else:
            prompt_info = await self._get_best_prompt(name, category, context)

        if not prompt_info:
            raise ValueError(f"未找到Prompt: {category}/{name}")

        # 更新缓存
        self._cache[cache_key] = (prompt_info, datetime.now())

        # 渲染模板
        rendered_content = self._render_template(prompt_info.content, variables)

        # 记录使用（异步，不阻塞返回）
        asyncio.create_task(
            self._record_usage_start(prompt_info.id, context, variables)
        )

        logger.info(f"获取Prompt成功: {category}/{name} v{prompt_info.version}")
        return prompt_info, rendered_content

    async def _get_best_prompt(
        self, name: str, category: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[PromptInfo]:
        """
        获取最佳Prompt版本

        Args:
            name: Prompt名称
            category: Prompt分类
            context: 使用上下文

        Returns:
            PromptInfo: 最佳Prompt信息
        """
        async with self.db_pool.acquire() as conn:
            # 查询活跃版本，按性能评分和优先级排序
            query = """
                SELECT p.*,
                       COALESCE(
                           array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL),
                           ARRAY[]::VARCHAR[]
                       ) as tags
                FROM prompts p
                LEFT JOIN prompt_tag_relations ptr ON p.id = ptr.prompt_id
                LEFT JOIN prompt_tags t ON ptr.tag_id = t.id
                WHERE p.name = $1 AND p.category = $2 AND p.is_active = true
                GROUP BY p.id
                ORDER BY p.priority DESC, p.performance_score DESC, p.version DESC
                LIMIT 1
            """

            row = await conn.fetchrow(query, name, category)

            if not row:
                return None

            return self._row_to_prompt_info(row)

    async def _get_prompt_with_experiment(
        self, name: str, category: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[PromptInfo]:
        """
        获取包含A/B测试的Prompt

        Args:
            name: Prompt名称
            category: Prompt分类
            context: 使用上下文

        Returns:
            PromptInfo: 实验选择的Prompt信息
        """
        async with self.db_pool.acquire() as conn:
            # 查询是否有活跃的A/B测试
            experiment_query = """
                SELECT pe.*, pa.id as a_id, pb.id as b_id,
                       pa.performance_score as a_score, pb.performance_score as b_score
                FROM prompt_experiments pe
                JOIN prompts pa ON pe.prompt_a_id = pa.id
                JOIN prompts pb ON pe.prompt_b_id = pb.id
                WHERE pe.status = 'active'
                  AND ((pa.name = $1 AND pa.category = $2) OR (pb.name = $1 AND pb.category = $2))
                LIMIT 1
            """

            experiment_row = await conn.fetchrow(experiment_query, name, category)

            if not experiment_row:
                # 没有活跃实验，获取最佳Prompt
                return await self._get_best_prompt(name, category, context)

            # A/B测试逻辑：根据流量分配选择版本
            import random

            use_a = random.random() < float(experiment_row["traffic_split"])

            selected_id = experiment_row["a_id"] if use_a else experiment_row["b_id"]

            # 记录实验使用
            await self._record_experiment_usage(
                experiment_row["id"], selected_id, context
            )

            # 获取选中的Prompt
            prompt_query = """
                SELECT p.*,
                       COALESCE(
                           array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL),
                           ARRAY[]::VARCHAR[]
                       ) as tags
                FROM prompts p
                LEFT JOIN prompt_tag_relations ptr ON p.id = ptr.prompt_id
                LEFT JOIN prompt_tags t ON ptr.tag_id = t.id
                WHERE p.id = $1
                GROUP BY p.id
            """

            prompt_row = await conn.fetchrow(prompt_query, selected_id)

            if prompt_row:
                return self._row_to_prompt_info(prompt_row)

            # 备选方案：获取最佳Prompt
            return await self._get_best_prompt(name, category, context)

    def _render_template(
        self, template_content: str, variables: Optional[Dict[str, Any]]
    ) -> str:
        """
        渲染Prompt模板

        Args:
            template_content: 模板内容
            variables: 变量字典

        Returns:
            str: 渲染后的内容
        """
        if not variables:
            variables = {}

        try:
            # 使用Jinja2渲染
            template = self._jinja_env.from_string(template_content)
            rendered = template.render(**variables)

            # 清理多余的空行
            rendered = re.sub(r"\n\s*\n\s*\n", "\n\n", rendered)
            rendered = rendered.strip()

            return rendered

        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            # 降级到简单变量替换
            return self._simple_variable_replace(template_content, variables)

    def _simple_variable_replace(self, content: str, variables: Dict[str, Any]) -> str:
        """
        简单变量替换（降级方案）

        Args:
            content: 原始内容
            variables: 变量字典

        Returns:
            str: 替换后的内容
        """

        def replace_match(match):
            var_name = match.group(1)
            return str(variables.get(var_name, match.group(0)))

        return self._variable_pattern.sub(replace_match, content)

    def extract_variables(self, content: str) -> List[str]:
        """
        从模板内容中提取变量名

        Args:
            content: 模板内容

        Returns:
            List[str]: 变量名列表
        """
        try:
            # 使用Jinja2解析
            ast = self._jinja_env.parse(content)
            variables = list(meta.find_undeclared_variables(ast))
            return sorted(set(variables))
        except Exception:
            # 降级到正则表达式提取
            matches = self._variable_pattern.findall(content)
            return sorted(set(matches))

    async def create_prompt(
        self,
        name: str,
        category: str,
        content: str,
        subcategory: Optional[str] = None,
        version: str = "1.0.0",
        variables: Optional[List[PromptVariable]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> PromptInfo:
        """
        创建新Prompt

        Args:
            name: Prompt名称
            category: Prompt分类
            content: Prompt内容
            subcategory: 子分类
            version: 版本号
            variables: 变量定义
            metadata: 元数据
            priority: 优先级
            tags: 标签列表
            created_by: 创建者

        Returns:
            PromptInfo: 创建的Prompt信息
        """
        # 自动提取变量
        if variables is None:
            extracted_vars = self.extract_variables(content)
            variables = [PromptVariable(name=var) for var in extracted_vars]

        # 验证版本唯一性
        existing = await self._get_prompt_by_version(name, category, version)
        if existing:
            raise ValueError(f"版本已存在: {category}/{name} v{version}")

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 创建Prompt记录
                prompt_id = uuid.uuid4()

                insert_query = """
                    INSERT INTO prompts (
                        id, name, category, subcategory, version, content,
                        variables, metadata, priority, created_by
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING *
                """

                row = await conn.fetchrow(
                    insert_query,
                    prompt_id,
                    name,
                    category,
                    subcategory,
                    version,
                    content,
                    json.dumps([asdict(var) for var in variables])
                    if variables
                    else "{}",
                    json.dumps(metadata or {}),
                    priority,
                    created_by,
                )

                # 处理标签
                if tags:
                    await self._add_tags_to_prompt(conn, prompt_id, tags)

                # 标记为最新版本
                await self._mark_as_latest_version(conn, name, category, prompt_id)

                # 清除缓存
                cache_key = f"{category}:{name}"
                self._cache.pop(cache_key, None)

                prompt_info = self._row_to_prompt_info_with_tags(row, tags)

                logger.info(f"创建Prompt成功: {category}/{name} v{version}")
                return prompt_info

    async def update_prompt(
        self,
        prompt_id: uuid.UUID,
        content: Optional[str] = None,
        variables: Optional[List[PromptVariable]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: Optional[int] = None,
        tags: Optional[List[str]] = None,
        change_description: Optional[str] = None,
        updated_by: Optional[str] = None,
        create_new_version: bool = True,
    ) -> PromptInfo:
        """
        更新Prompt

        Args:
            prompt_id: Prompt ID
            content: 新内容
            variables: 变量定义
            metadata: 元数据
            priority: 优先级
            tags: 标签列表
            change_description: 变更描述
            updated_by: 更新者
            create_new_version: 是否创建新版本

        Returns:
            PromptInfo: 更新后的Prompt信息
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 获取当前Prompt
                current = await self._get_prompt_by_id(prompt_id)
                if not current:
                    raise ValueError(f"Prompt不存在: {prompt_id}")

                if create_new_version:
                    # 创建新版本
                    new_version = self._increment_version(current.version)

                    # 保存当前版本到历史
                    await self._save_version_to_history(
                        conn, current, change_description
                    )

                    # 创建新版本记录
                    new_variables = variables or current.variables
                    if content:
                        new_variables = [
                            PromptVariable(name=var)
                            for var in self.extract_variables(content)
                        ]

                    insert_query = """
                        INSERT INTO prompts (
                            id, name, category, subcategory, version, content,
                            variables, metadata, priority, is_latest, created_by
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        RETURNING *
                    """

                    new_prompt_id = uuid.uuid4()
                    row = await conn.fetchrow(
                        insert_query,
                        new_prompt_id,
                        current.name,
                        current.category,
                        current.subcategory,
                        new_version,
                        content or current.content,
                        json.dumps([asdict(var) for var in new_variables])
                        if new_variables
                        else "{}",
                        json.dumps(metadata or current.metadata),
                        priority if priority is not None else current.priority,
                        True,
                        updated_by,
                    )

                    # 更新旧版本标记
                    await self._mark_as_latest_version(
                        conn, current.name, current.category, new_prompt_id
                    )

                    # 处理标签
                    if tags is not None:
                        await self._update_prompt_tags(conn, new_prompt_id, tags)

                    prompt_info = self._row_to_prompt_info_with_tags(row, tags)

                else:
                    # 直接更新当前版本
                    update_fields = []
                    update_values = []
                    param_count = 1

                    if content is not None:
                        update_fields.append(f"content = ${param_count}")
                        update_values.append(content)
                        param_count += 1

                    if variables is not None:
                        update_fields.append(f"variables = ${param_count}")
                        update_values.append(
                            json.dumps([asdict(var) for var in variables])
                        )
                        param_count += 1

                    if metadata is not None:
                        update_fields.append(f"metadata = ${param_count}")
                        update_values.append(json.dumps(metadata))
                        param_count += 1

                    if priority is not None:
                        update_fields.append(f"priority = ${param_count}")
                        update_values.append(priority)
                        param_count += 1

                    update_fields.append(f"updated_by = ${param_count}")
                    update_values.append(updated_by)
                    param_count += 1

                    update_fields.append(f"updated_at = NOW()")

                    update_query = f"""
                        UPDATE prompts
                        SET {', '.join(update_fields)}
                        WHERE id = ${param_count}
                        RETURNING *
                    """
                    update_values.append(prompt_id)

                    row = await conn.fetchrow(update_query, *update_values)

                    # 处理标签
                    if tags is not None:
                        await self._update_prompt_tags(conn, prompt_id, tags)

                    prompt_info = self._row_to_prompt_info_with_tags(row, tags)

                # 清除缓存
                cache_key = f"{prompt_info.category}:{prompt_info.name}"
                self._cache.pop(cache_key, None)

                logger.info(f"更新Prompt成功: {prompt_info.category}/{prompt_info.name}")
                return prompt_info

    async def record_usage_log(self, log: UsageLog) -> None:
        """
        记录Prompt使用日志

        Args:
            log: 使用记录
        """
        async with self.db_pool.acquire() as conn:
            insert_query = """
                INSERT INTO prompt_usage_logs (
                    prompt_id, session_id, context, variables_used,
                    execution_time_ms, success, error_message,
                    user_feedback, llm_response, tokens_used,
                    model_name, temperature
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """

            await conn.execute(
                insert_query,
                log.prompt_id,
                log.session_id,
                json.dumps(log.context),
                json.dumps(log.variables_used),
                log.execution_time_ms,
                log.success,
                log.error_message,
                log.user_feedback,
                json.dumps(log.llm_response) if log.llm_response else None,
                log.tokens_used,
                log.model_name,
                log.temperature,
            )

    async def get_prompt_performance(self, prompt_id: uuid.UUID) -> Dict[str, Any]:
        """
        获取Prompt性能统计

        Args:
            prompt_id: Prompt ID

        Returns:
            Dict[str, Any]: 性能统计数据
        """
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT
                    p.usage_count,
                    p.success_count,
                    p.performance_score,
                    COUNT(pul.id) as total_logs,
                    AVG(pul.execution_time_ms) as avg_execution_time,
                    MIN(pul.execution_time_ms) as min_execution_time,
                    MAX(pul.execution_time_ms) as max_execution_time,
                    AVG(pul.user_feedback) as avg_user_feedback,
                    SUM(pul.tokens_used) as total_tokens,
                    COUNT(CASE WHEN pul.success = true THEN 1 END) as recent_success_count,
                    COUNT(CASE WHEN pul.created_at > NOW() - INTERVAL '7 days' THEN 1 END) as recent_usage_count
                FROM prompts p
                LEFT JOIN prompt_usage_logs pul ON p.id = pul.prompt_id
                WHERE p.id = $1
                GROUP BY p.id, p.usage_count, p.success_count, p.performance_score
            """

            row = await conn.fetchrow(query, prompt_id)

            if not row:
                return {}

            stats = {
                "usage_count": row["usage_count"],
                "success_count": row["success_count"],
                "performance_score": float(row["performance_score"]),
                "total_logs": row["total_logs"],
                "avg_execution_time_ms": float(row["avg_execution_time"] or 0),
                "min_execution_time_ms": row["min_execution_time_ms"],
                "max_execution_time_ms": row["max_execution_time_ms"],
                "avg_user_feedback": float(row["avg_user_feedback"] or 0),
                "total_tokens": row["total_tokens"],
                "recent_success_count": row["recent_success_count"],
                "recent_usage_count": row["recent_usage_count"],
                "success_rate": row["success_count"] / max(row["usage_count"], 1),
                "recent_success_rate": (
                    row["recent_success_count"] / max(row["recent_usage_count"], 1)
                    if row["recent_usage_count"] > 0
                    else 0
                ),
            }

            return stats

    # 私有方法实现...
    async def _get_prompt_by_version(
        self, name: str, category: str, version: str
    ) -> Optional[PromptInfo]:
        """根据版本获取Prompt"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT p.*,
                       COALESCE(
                           array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL),
                           ARRAY[]::VARCHAR[]
                       ) as tags
                FROM prompts p
                LEFT JOIN prompt_tag_relations ptr ON p.id = ptr.prompt_id
                LEFT JOIN prompt_tags t ON ptr.tag_id = t.id
                WHERE p.name = $1 AND p.category = $2 AND p.version = $3
                GROUP BY p.id
                LIMIT 1
            """

            row = await conn.fetchrow(query, name, category, version)
            return self._row_to_prompt_info_with_tags(row, []) if row else None

    async def _get_prompt_by_id(self, prompt_id: uuid.UUID) -> Optional[PromptInfo]:
        """根据ID获取Prompt"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT p.*,
                       COALESCE(
                           array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL),
                           ARRAY[]::VARCHAR[]
                       ) as tags
                FROM prompts p
                LEFT JOIN prompt_tag_relations ptr ON p.id = ptr.prompt_id
                LEFT JOIN prompt_tags t ON ptr.tag_id = t.id
                WHERE p.id = $1
                GROUP BY p.id
                LIMIT 1
            """

            row = await conn.fetchrow(query, prompt_id)
            return self._row_to_prompt_info_with_tags(row, []) if row else None

    async def _mark_as_latest_version(
        self, conn, name: str, category: str, prompt_id: uuid.UUID
    ) -> None:
        """标记为最新版本"""
        # 取消同name-category的其他版本的latest标记
        await conn.execute(
            """
            UPDATE prompts
            SET is_latest = false
            WHERE name = $1 AND category = $2 AND id != $3
            """,
            name,
            category,
            prompt_id,
        )

        # 设置当前版本为latest
        await conn.execute(
            "UPDATE prompts SET is_latest = true WHERE id = $1", prompt_id
        )

    async def _save_version_to_history(
        self, conn, prompt_info: PromptInfo, description: Optional[str]
    ) -> None:
        """保存版本到历史表"""
        await conn.execute(
            """
            INSERT INTO prompt_versions (
                prompt_id, version, content, variables,
                change_description, performance_metrics, usage_stats, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            prompt_info.id,
            prompt_info.version,
            prompt_info.content,
            json.dumps([asdict(var) for var in prompt_info.variables])
            if prompt_info.variables
            else "{}",
            description,
            json.dumps(
                {
                    "performance_score": prompt_info.performance_score,
                    "usage_count": prompt_info.usage_count,
                    "success_count": prompt_info.success_count,
                }
            ),
            json.dumps({"created_at": prompt_info.created_at.isoformat()}),
            prompt_info.created_by,
        )

    def _increment_version(self, current_version: str) -> str:
        """版本号递增"""
        try:
            parts = current_version.split(".")
            if len(parts) == 3:
                major, minor, patch = parts
                patch = str(int(patch) + 1)
                return f"{major}.{minor}.{patch}"
        except:
            pass
        return f"{current_version}.1"

    async def _add_tags_to_prompt(
        self, conn, prompt_id: uuid.UUID, tags: List[str]
    ) -> None:
        """为Prompt添加标签"""
        for tag_name in tags:
            # 确保标签存在
            await conn.execute(
                """
                INSERT INTO prompt_tags (name) VALUES ($1)
                ON CONFLICT (name) DO NOTHING
                """,
                tag_name,
            )

            # 关联标签
            await conn.execute(
                """
                INSERT INTO prompt_tag_relations (prompt_id, tag_id)
                SELECT $1, id FROM prompt_tags WHERE name = $2
                ON CONFLICT DO NOTHING
                """,
                prompt_id,
                tag_name,
            )

    async def _update_prompt_tags(
        self, conn, prompt_id: uuid.UUID, tags: List[str]
    ) -> None:
        """更新Prompt标签"""
        # 删除现有标签
        await conn.execute(
            "DELETE FROM prompt_tag_relations WHERE prompt_id = $1", prompt_id
        )

        # 添加新标签
        if tags:
            await self._add_tags_to_prompt(conn, prompt_id, tags)

    def _row_to_prompt_info(self, row) -> PromptInfo:
        """数据库行转PromptInfo"""
        variables_data = json.loads(row["variables"]) if row["variables"] else []
        variables = [PromptVariable(**var_data) for var_data in variables_data]

        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        return PromptInfo(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            subcategory=row["subcategory"],
            version=row["version"],
            content=row["content"],
            variables=variables,
            metadata=metadata,
            is_active=row["is_active"],
            is_latest=row["is_latest"],
            priority=row["priority"],
            performance_score=float(row["performance_score"]),
            usage_count=row["usage_count"],
            success_count=row["success_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
            tags=[],
        )

    def _row_to_prompt_info_with_tags(self, row, tags: List[str] = None) -> PromptInfo:
        """数据库行转PromptInfo（带标签）"""
        prompt_info = self._row_to_prompt_info(row)

        if tags:
            prompt_info.tags = tags
        elif row.get("tags"):
            prompt_info.tags = [tag for tag in row["tags"] if tag]

        return prompt_info

    async def _record_usage_start(
        self, prompt_id: uuid.UUID, context: Optional[Dict], variables: Optional[Dict]
    ) -> None:
        """记录使用开始（异步）"""
        # 这里可以扩展为更复杂的记录逻辑
        pass

    async def _record_experiment_usage(
        self,
        experiment_id: uuid.UUID,
        selected_prompt_id: uuid.UUID,
        context: Optional[Dict],
    ) -> None:
        """记录实验使用"""
        # 这里可以实现更详细的实验跟踪逻辑
        pass

    async def clear_cache(
        self, category: Optional[str] = None, name: Optional[str] = None
    ):
        """清除缓存"""
        if category and name:
            cache_key = f"{category}:{name}"
            self._cache.pop(cache_key, None)
        else:
            self._cache.clear()

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self._cache),
            "cache_ttl": self.cache_ttl,
            "cache_keys": list(self._cache.keys()),
        }

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return {
                    "status": "healthy",
                    "database": "connected",
                    "cache_size": len(self._cache),
                }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "database": "disconnected"}
