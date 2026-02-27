"""
PromptEN - ENPromptEN,EN,EN
ENPromptEN,A/BEN,EN
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
from jinja2 import Template, meta
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)


class PromptStatus(Enum):
    """PromptEN"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ExperimentStatus(Enum):
    """EN"""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class PromptVariable:
    """PromptEN"""

    name: str
    type: str = "string"  # string, number, boolean, json
    required: bool = True
    default_value: Any = None
    description: str = ""
    validation_regex: str = None
    options: List[Any] = None


@dataclass
class PromptInfo:
    """PromptEN"""

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
        """EN"""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    def to_dict(self) -> Dict[str, Any]:
        """EN"""
        data = asdict(self)
        data["variables"] = (
            [asdict(var) for var in self.variables] if self.variables else []
        )
        data["success_rate"] = self.success_rate
        return data


@dataclass
class UsageLog:
    """EN"""

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
    """PromptEN - EN"""

    def __init__(self, db_pool: asyncpg.Pool, cache_ttl: int = 300):
        """
        ENPromptEN

        Args:
            db_pool: EN
            cache_ttl: EN(EN)
        """
        self.db_pool = db_pool
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[PromptInfo, datetime]] = {}
        self._jinja_env = SandboxedEnvironment(
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._jinja_env.policies['ext.require_sandboxed'] = True

        # EN
        self._variable_pattern = re.compile(r"\{\{\s*(\w+)\s*\}\}")

        logger.info("PromptEN")

    async def get_prompt(
        self,
        name: str,
        category: str,
        context: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None,
        enable_experiments: bool = True,
    ) -> Tuple[PromptInfo, str]:
        """
        ENPromptEN

        Args:
            name: PromptEN
            category: PromptEN
            context: EN,EN
            variables: EN
            enable_experiments: ENA/BEN

        Returns:
            Tuple[PromptInfo, str]: (PromptEN, EN)
        """
        cache_key = f"{category}:{name}"

        # EN
        if cache_key in self._cache:
            prompt_info, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=self.cache_ttl):
                logger.debug(f"ENPrompt: {cache_key}")
                rendered_content = self._render_template(prompt_info.content, variables)
                return prompt_info, rendered_content

        # ENPrompt
        if enable_experiments:
            prompt_info = await self._get_prompt_with_experiment(
                name, category, context
            )
        else:
            prompt_info = await self._get_best_prompt(name, category, context)

        if not prompt_info:
            raise ValueError(f"ENPrompt: {category}/{name}")

        # EN
        self._cache[cache_key] = (prompt_info, datetime.now())

        # EN
        rendered_content = self._render_template(prompt_info.content, variables)

        # EN(EN,EN)
        asyncio.create_task(
            self._record_usage_start(prompt_info.id, context, variables)
        )

        logger.info(f"ENPromptEN: {category}/{name} v{prompt_info.version}")
        return prompt_info, rendered_content

    async def _get_best_prompt(
        self, name: str, category: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[PromptInfo]:
        """
        ENPromptEN

        Args:
            name: PromptEN
            category: PromptEN
            context: EN

        Returns:
            PromptInfo: ENPromptEN
        """
        async with self.db_pool.acquire() as conn:
            # EN,EN
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
        ENA/BENPrompt

        Args:
            name: PromptEN
            category: PromptEN
            context: EN

        Returns:
            PromptInfo: ENPromptEN
        """
        async with self.db_pool.acquire() as conn:
            # ENA/BEN
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
                # EN,ENPrompt
                return await self._get_best_prompt(name, category, context)

            # A/BEN:EN,EN.
            use_a = (
                self._allocate_experiment_bucket(
                    name=name,
                    category=category,
                    context=context,
                    traffic_split=float(experiment_row["traffic_split"]),
                )
                == "A"
            )

            selected_id = experiment_row["a_id"] if use_a else experiment_row["b_id"]

            # EN
            await self._record_experiment_usage(
                experiment_row["id"], selected_id, context
            )

            # ENPrompt
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

            # EN:ENPrompt
            return await self._get_best_prompt(name, category, context)

    def _render_template(
        self, template_content: str, variables: Optional[Dict[str, Any]]
    ) -> str:
        """
        ENPromptEN

        Args:
            template_content: EN
            variables: EN

        Returns:
            str: EN
        """
        if not variables:
            variables = {}

        try:
            # ENJinja2EN
            template = self._jinja_env.from_string(template_content)
            rendered = template.render(**variables)

            # EN
            rendered = re.sub(r"\n\s*\n\s*\n", "\n\n", rendered)
            rendered = rendered.strip()

            return rendered

        except Exception as e:
            logger.error(f"EN: {e}")
            # EN
            return self._simple_variable_replace(template_content, variables)

    def _simple_variable_replace(self, content: str, variables: Dict[str, Any]) -> str:
        """
        EN(EN)

        Args:
            content: EN
            variables: EN

        Returns:
            str: EN
        """

        def replace_match(match):
            var_name = match.group(1)
            return str(variables.get(var_name, match.group(0)))

        return self._variable_pattern.sub(replace_match, content)

    def extract_variables(self, content: str) -> List[str]:
        """
        EN

        Args:
            content: EN

        Returns:
            List[str]: EN
        """
        try:
            # ENJinja2EN
            ast = self._jinja_env.parse(content)
            variables = list(meta.find_undeclared_variables(ast))
            return sorted(set(variables))
        except Exception:
            # EN
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
        ENPrompt

        Args:
            name: PromptEN
            category: PromptEN
            content: PromptEN
            subcategory: EN
            version: EN
            variables: EN
            metadata: EN
            priority: EN
            tags: EN
            created_by: EN

        Returns:
            PromptInfo: ENPromptEN
        """
        # EN
        if variables is None:
            extracted_vars = self.extract_variables(content)
            variables = [PromptVariable(name=var) for var in extracted_vars]

        # EN
        existing = await self._get_prompt_by_version(name, category, version)
        if existing:
            raise ValueError(f"EN: {category}/{name} v{version}")

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # ENPromptEN
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

                # EN
                if tags:
                    await self._add_tags_to_prompt(conn, prompt_id, tags)

                # EN
                await self._mark_as_latest_version(conn, name, category, prompt_id)

                # EN
                cache_key = f"{category}:{name}"
                self._cache.pop(cache_key, None)

                prompt_info = self._row_to_prompt_info_with_tags(row, tags)

                logger.info(f"ENPromptEN: {category}/{name} v{version}")
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
        ENPrompt

        Args:
            prompt_id: Prompt ID
            content: EN
            variables: EN
            metadata: EN
            priority: EN
            tags: EN
            change_description: EN
            updated_by: EN
            create_new_version: EN

        Returns:
            PromptInfo: ENPromptEN
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # ENPrompt
                current = await self._get_prompt_by_id(prompt_id)
                if not current:
                    raise ValueError(f"PromptEN: {prompt_id}")

                if create_new_version:
                    # EN
                    new_version = self._increment_version(current.version)

                    # EN
                    await self._save_version_to_history(
                        conn, current, change_description
                    )

                    # EN
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

                    # EN
                    await self._mark_as_latest_version(
                        conn, current.name, current.category, new_prompt_id
                    )

                    # EN
                    if tags is not None:
                        await self._update_prompt_tags(conn, new_prompt_id, tags)

                    prompt_info = self._row_to_prompt_info_with_tags(row, tags)

                else:
                    # EN
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

                    # EN
                    if tags is not None:
                        await self._update_prompt_tags(conn, prompt_id, tags)

                    prompt_info = self._row_to_prompt_info_with_tags(row, tags)

                # EN
                cache_key = f"{prompt_info.category}:{prompt_info.name}"
                self._cache.pop(cache_key, None)

                logger.info(f"ENPromptEN: {prompt_info.category}/{prompt_info.name}")
                return prompt_info

    async def record_usage_log(self, log: UsageLog) -> None:
        """
        ENPromptEN

        Args:
            log: EN
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
        ENPromptEN

        Args:
            prompt_id: Prompt ID

        Returns:
            Dict[str, Any]: EN
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
                "min_execution_time_ms": row["min_execution_time"],
                "max_execution_time_ms": row["max_execution_time"],
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

    async def get_usage_summary(
        self,
        *,
        days: int = 7,
        category: Optional[str] = None,
        top_limit: int = 10,
    ) -> Dict[str, Any]:
        """
        ENPromptEN(EN).

        Args:
            days: EN
            category: EN
            top_limit: ENPromptEN
        """
        days = max(1, int(days))
        top_limit = max(1, int(top_limit))

        async with self.db_pool.acquire() as conn:
            base_params: List[Any] = [days]
            category_clause = ""
            if category:
                base_params.append(category)
                category_clause = f" AND p.category = ${len(base_params)}"

            totals_query = f"""
                SELECT
                    COUNT(DISTINCT p.id) AS prompt_count,
                    COUNT(pul.id) AS usage_logs,
                    COUNT(CASE WHEN pul.success = true THEN 1 END) AS success_logs,
                    AVG(pul.execution_time_ms) AS avg_execution_time_ms,
                    SUM(pul.tokens_used) AS total_tokens,
                    AVG(pul.user_feedback) AS avg_feedback
                FROM prompts p
                LEFT JOIN prompt_usage_logs pul
                  ON p.id = pul.prompt_id
                 AND pul.created_at >= NOW() - INTERVAL '1 day' * $1
                WHERE p.is_active = true
                {category_clause}
            """
            totals_row = await conn.fetchrow(totals_query, *base_params)

            top_query = f"""
                SELECT
                    p.id,
                    p.name,
                    p.category,
                    COUNT(pul.id) AS usage_count,
                    COUNT(CASE WHEN pul.success = true THEN 1 END) AS success_count,
                    AVG(pul.execution_time_ms) AS avg_execution_time_ms,
                    SUM(pul.tokens_used) AS total_tokens
                FROM prompts p
                LEFT JOIN prompt_usage_logs pul
                  ON p.id = pul.prompt_id
                 AND pul.created_at >= NOW() - INTERVAL '1 day' * $1
                WHERE p.is_active = true
                {category_clause}
                GROUP BY p.id, p.name, p.category
                ORDER BY usage_count DESC, p.name ASC
                LIMIT ${len(base_params) + 1}
            """
            top_rows = await conn.fetch(top_query, *(base_params + [top_limit]))

            daily_query = f"""
                SELECT
                    DATE(pul.created_at) AS date,
                    COUNT(*) AS usage_count,
                    COUNT(CASE WHEN pul.success = true THEN 1 END) AS success_count,
                    AVG(pul.execution_time_ms) AS avg_execution_time_ms,
                    SUM(pul.tokens_used) AS total_tokens
                FROM prompt_usage_logs pul
                JOIN prompts p ON p.id = pul.prompt_id
                WHERE pul.created_at >= NOW() - INTERVAL '1 day' * $1
                  AND p.is_active = true
                  {category_clause}
                GROUP BY DATE(pul.created_at)
                ORDER BY date DESC
            """
            daily_rows = await conn.fetch(daily_query, *base_params)

        totals_data = dict(totals_row) if totals_row else {}
        prompt_count = int(totals_data.get("prompt_count") or 0)
        usage_logs = int(totals_data.get("usage_logs") or 0)
        success_logs = int(totals_data.get("success_logs") or 0)
        avg_execution_time_ms = float(totals_data.get("avg_execution_time_ms") or 0.0)
        total_tokens = int(totals_data.get("total_tokens") or 0)
        avg_feedback = float(totals_data.get("avg_feedback") or 0.0)

        top_prompts = []
        for row in top_rows:
            usage_count = int(row["usage_count"] or 0)
            success_count = int(row["success_count"] or 0)
            top_prompts.append(
                {
                    "prompt_id": str(row["id"]),
                    "name": row["name"],
                    "category": row["category"],
                    "usage_count": usage_count,
                    "success_count": success_count,
                    "success_rate": (
                        float(success_count / usage_count) if usage_count > 0 else 0.0
                    ),
                    "avg_execution_time_ms": float(
                        row["avg_execution_time_ms"] or 0.0
                    ),
                    "total_tokens": int(row["total_tokens"] or 0),
                }
            )

        daily = []
        for row in daily_rows:
            usage_count = int(row["usage_count"] or 0)
            success_count = int(row["success_count"] or 0)
            day_value = row["date"]
            daily.append(
                {
                    "date": (
                        day_value.isoformat()
                        if hasattr(day_value, "isoformat")
                        else str(day_value)
                    ),
                    "usage_count": usage_count,
                    "success_count": success_count,
                    "success_rate": (
                        float(success_count / usage_count) if usage_count > 0 else 0.0
                    ),
                    "avg_execution_time_ms": float(
                        row["avg_execution_time_ms"] or 0.0
                    ),
                    "total_tokens": int(row["total_tokens"] or 0),
                }
            )

        return {
            "window_days": days,
            "category": category,
            "totals": {
                "prompt_count": prompt_count,
                "usage_logs": usage_logs,
                "success_logs": success_logs,
                "success_rate": (
                    float(success_logs / usage_logs) if usage_logs > 0 else 0.0
                ),
                "avg_execution_time_ms": avg_execution_time_ms,
                "total_tokens": total_tokens,
                "avg_feedback": avg_feedback,
            },
            "top_prompts": top_prompts,
            "daily": daily,
        }

    async def create_experiment(
        self,
        *,
        name: str,
        prompt_a_id: uuid.UUID,
        prompt_b_id: uuid.UUID,
        traffic_split: float = 0.5,
        description: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ENPrompt A/BEN."""
        if prompt_a_id == prompt_b_id:
            raise ValueError("prompt_a_id and prompt_b_id must be different")
        if traffic_split <= 0 or traffic_split >= 1:
            raise ValueError("traffic_split must be between 0 and 1")

        async with self.db_pool.acquire() as conn:
            prompt_check_query = """
                SELECT id, name, category
                FROM prompts
                WHERE id = $1 AND is_active = true
            """
            prompt_a = await conn.fetchrow(prompt_check_query, prompt_a_id)
            prompt_b = await conn.fetchrow(prompt_check_query, prompt_b_id)
            if not prompt_a or not prompt_b:
                raise ValueError("Prompt not found or inactive")

            if (
                prompt_a["name"] != prompt_b["name"]
                or prompt_a["category"] != prompt_b["category"]
            ):
                raise ValueError(
                    "Experiment prompts must share same name and category"
                )

            insert_query = """
                INSERT INTO prompt_experiments (
                    name, description, prompt_a_id, prompt_b_id, traffic_split, metrics, created_by
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, name, description, prompt_a_id, prompt_b_id,
                          traffic_split, status, metrics, created_at, created_by, updated_at
            """
            try:
                row = await conn.fetchrow(
                    insert_query,
                    name,
                    description,
                    prompt_a_id,
                    prompt_b_id,
                    traffic_split,
                    json.dumps(metrics or {}),
                    created_by,
                )
            except asyncpg.UniqueViolationError as exc:
                raise ValueError(f"Experiment already exists: {name}") from exc

        return self._experiment_row_to_dict(row)

    async def list_experiments(
        self,
        *,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """EN."""
        limit = max(1, int(limit))
        offset = max(0, int(offset))

        where_parts: List[str] = []
        params: List[Any] = []

        if status:
            status_value = status.lower()
            self._validate_experiment_status(status_value)
            params.append(status_value)
            where_parts.append(f"pe.status = ${len(params)}")
        if category:
            params.append(category)
            where_parts.append(f"pa.category = ${len(params)}")

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        async with self.db_pool.acquire() as conn:
            list_query = f"""
                SELECT
                    pe.id, pe.name, pe.description, pe.prompt_a_id, pe.prompt_b_id,
                    pe.traffic_split, pe.status, pe.metrics, pe.created_at, pe.created_by, pe.updated_at,
                    pa.name AS prompt_name, pa.category AS prompt_category,
                    pa.version AS prompt_a_version, pb.version AS prompt_b_version
                FROM prompt_experiments pe
                JOIN prompts pa ON pe.prompt_a_id = pa.id
                JOIN prompts pb ON pe.prompt_b_id = pb.id
                {where_clause}
                ORDER BY pe.created_at DESC
                LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """
            rows = await conn.fetch(list_query, *(params + [limit, offset]))

            count_query = f"""
                SELECT COUNT(*)
                FROM prompt_experiments pe
                JOIN prompts pa ON pe.prompt_a_id = pa.id
                {where_clause}
            """
            total = int(await conn.fetchval(count_query, *params) or 0)

        return [self._experiment_row_to_dict(row) for row in rows], total

    async def get_experiment(self, experiment_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """EN."""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT
                    pe.id, pe.name, pe.description, pe.prompt_a_id, pe.prompt_b_id,
                    pe.traffic_split, pe.status, pe.metrics, pe.created_at, pe.created_by, pe.updated_at,
                    pa.name AS prompt_name, pa.category AS prompt_category,
                    pa.version AS prompt_a_version, pb.version AS prompt_b_version
                FROM prompt_experiments pe
                JOIN prompts pa ON pe.prompt_a_id = pa.id
                JOIN prompts pb ON pe.prompt_b_id = pb.id
                WHERE pe.id = $1
                LIMIT 1
            """
            row = await conn.fetchrow(query, experiment_id)

        return self._experiment_row_to_dict(row) if row else None

    async def update_experiment_traffic(
        self, experiment_id: uuid.UUID, traffic_split: float
    ) -> Optional[Dict[str, Any]]:
        """EN."""
        if traffic_split <= 0 or traffic_split >= 1:
            raise ValueError("traffic_split must be between 0 and 1")

        async with self.db_pool.acquire() as conn:
            query = """
                UPDATE prompt_experiments
                SET traffic_split = $2
                WHERE id = $1
                RETURNING id, name, description, prompt_a_id, prompt_b_id,
                          traffic_split, status, metrics, created_at, created_by, updated_at
            """
            row = await conn.fetchrow(query, experiment_id, traffic_split)

        return self._experiment_row_to_dict(row) if row else None

    async def update_experiment_status(
        self, experiment_id: uuid.UUID, status: str
    ) -> Optional[Dict[str, Any]]:
        """EN."""
        normalized = status.lower().strip()
        self._validate_experiment_status(normalized)

        async with self.db_pool.acquire() as conn:
            query = """
                UPDATE prompt_experiments
                SET status = $2
                WHERE id = $1
                RETURNING id, name, description, prompt_a_id, prompt_b_id,
                          traffic_split, status, metrics, created_at, created_by, updated_at
            """
            row = await conn.fetchrow(query, experiment_id, normalized)

        return self._experiment_row_to_dict(row) if row else None

    # EN...
    async def _get_prompt_by_version(
        self, name: str, category: str, version: str
    ) -> Optional[PromptInfo]:
        """ENPrompt"""
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
        """ENIDENPrompt"""
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
        """EN"""
        # ENname-categoryENlatestEN
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

        # ENlatest
        await conn.execute(
            "UPDATE prompts SET is_latest = true WHERE id = $1", prompt_id
        )

    async def _save_version_to_history(
        self, conn, prompt_info: PromptInfo, description: Optional[str]
    ) -> None:
        """EN"""
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
        """EN"""
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
        """ENPromptEN"""
        for tag_name in tags:
            # EN
            await conn.execute(
                """
                INSERT INTO prompt_tags (name) VALUES ($1)
                ON CONFLICT (name) DO NOTHING
                """,
                tag_name,
            )

            # EN
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
        """ENPromptEN"""
        # EN
        await conn.execute(
            "DELETE FROM prompt_tag_relations WHERE prompt_id = $1", prompt_id
        )

        # EN
        if tags:
            await self._add_tags_to_prompt(conn, prompt_id, tags)

    def _row_to_prompt_info(self, row) -> PromptInfo:
        """ENPromptInfo"""
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
        """ENPromptInfo(EN)"""
        prompt_info = self._row_to_prompt_info(row)

        if tags:
            prompt_info.tags = tags
        elif row.get("tags"):
            prompt_info.tags = [tag for tag in row["tags"] if tag]

        return prompt_info

    async def _record_usage_start(
        self, prompt_id: uuid.UUID, context: Optional[Dict], variables: Optional[Dict]
    ) -> None:
        """EN(EN)"""
        # EN
        pass

    async def _record_experiment_usage(
        self,
        experiment_id: uuid.UUID,
        selected_prompt_id: uuid.UUID,
        context: Optional[Dict],
    ) -> None:
        """EN"""
        # EN
        pass

    async def clear_cache(
        self, category: Optional[str] = None, name: Optional[str] = None
    ):
        """EN"""
        if category and name:
            cache_key = f"{category}:{name}"
            self._cache.pop(cache_key, None)
        else:
            self._cache.clear()

    async def get_cache_stats(self) -> Dict[str, Any]:
        """EN"""
        return {
            "cache_size": len(self._cache),
            "cache_ttl": self.cache_ttl,
            "cache_keys": list(self._cache.keys()),
        }

    async def health_check(self) -> Dict[str, Any]:
        """EN"""
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

    def _allocate_experiment_bucket(
        self,
        *,
        name: str,
        category: str,
        context: Optional[Dict[str, Any]],
        traffic_split: float,
    ) -> str:
        """Deterministic experiment bucket allocation."""
        from backend.services.workflows.prompting.ab_allocator import ABAllocator

        allocator = ABAllocator()
        allocation_key = self._build_experiment_allocation_key(
            name=name,
            category=category,
            context=context,
        )
        return allocator.allocate(allocation_key, split=traffic_split)

    def _build_experiment_allocation_key(
        self,
        *,
        name: str,
        category: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build stable key for A/B allocation."""
        context = context or {}
        identity = (
            context.get("session_id")
            or context.get("tenant_id")
            or context.get("user_id")
            or context.get("trace_id")
            or "anonymous"
        )
        return f"{category}:{name}:{identity}"

    def _experiment_row_to_dict(self, row: Any) -> Dict[str, Any]:
        """EN."""
        if not row:
            return {}
        metrics = row["metrics"] if "metrics" in row else {}
        if isinstance(metrics, str):
            metrics = json.loads(metrics) if metrics else {}

        data = {
            "id": str(row["id"]),
            "name": row["name"],
            "description": row["description"],
            "prompt_a_id": str(row["prompt_a_id"]),
            "prompt_b_id": str(row["prompt_b_id"]),
            "traffic_split": float(row["traffic_split"]),
            "status": row["status"],
            "metrics": metrics or {},
            "created_at": row["created_at"].isoformat()
            if hasattr(row["created_at"], "isoformat")
            else row["created_at"],
            "created_by": row["created_by"],
            "updated_at": row["updated_at"].isoformat()
            if hasattr(row["updated_at"], "isoformat")
            else row["updated_at"],
        }
        if "prompt_name" in row:
            data["prompt_name"] = row["prompt_name"]
        if "prompt_category" in row:
            data["prompt_category"] = row["prompt_category"]
        if "prompt_a_version" in row:
            data["prompt_a_version"] = row["prompt_a_version"]
        if "prompt_b_version" in row:
            data["prompt_b_version"] = row["prompt_b_version"]
        return data

    def _validate_experiment_status(self, status: str) -> None:
        valid = {
            ExperimentStatus.ACTIVE.value,
            ExperimentStatus.PAUSED.value,
            ExperimentStatus.COMPLETED.value,
            ExperimentStatus.CANCELLED.value,
        }
        if status not in valid:
            raise ValueError(
                f"Invalid experiment status: {status}. Allowed: {', '.join(sorted(valid))}"
            )
