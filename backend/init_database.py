"""
数据库初始化脚本 - 创建所有必要的表和索引
"""

import logging

import psycopg2

from backend.config import settings

logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库表结构"""
    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()

    try:
        # 首先尝试启用pgvector扩展
        pgvector_available = False
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            conn.commit()
            logger.info("pgcrypto extension enabled")
        except Exception as e:
            logger.warning(f"Failed to enable pgcrypto extension: {e}")
            conn.rollback()

        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            logger.info("pgvector extension enabled")
            pgvector_available = True
        except Exception as e:
            logger.warning(f"Failed to enable pgvector extension: {e}")
            logger.info("Continuing without pgvector (vectors will be stored as TEXT)")
            conn.rollback()  # 回滚失败的事务
            pgvector_available = False

        # 创建文档表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id VARCHAR(255) PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                filepath TEXT,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 创建文档块表
        if pgvector_available:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    doc_id VARCHAR(255) NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(768),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE (doc_id, chunk_id)
                )
            """
            )
        else:
            # 如果pgvector不可用，将向量存储为TEXT
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    doc_id VARCHAR(255) NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE (doc_id, chunk_id)
                )
            """
            )

        # 文本搜索索引（无论是否有pgvector均可创建）
        try:
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chunks_content_fts
                ON document_chunks USING gin (to_tsvector('simple', content))
                """
            )
        except Exception as e:
            logger.warning(
                f"Failed to create GIN index on document_chunks.content: {e}"
            )

        # 创建反馈表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS query_feedback (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query_id VARCHAR(255) UNIQUE NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                feedback_type VARCHAR(50) NOT NULL,
                user_comment TEXT,
                retrieved_chunks JSONB,
                feedback_weight FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """
        )

        # 创建文档质量评分表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_quality_scores (
                doc_id VARCHAR(255) NOT NULL,
                chunk_id INTEGER NOT NULL,
                quality_score FLOAT DEFAULT 0.0,
                helpful_count INTEGER DEFAULT 0,
                not_helpful_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id, chunk_id) REFERENCES document_chunks(doc_id, chunk_id) ON DELETE CASCADE,
                PRIMARY KEY (doc_id, chunk_id)
            )
        """
        )

        # 创建查询优化记录表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS query_optimization_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query_id VARCHAR(255) NOT NULL,
                original_query TEXT NOT NULL,
                optimized_query TEXT,
                optimization_strategy VARCHAR(100),
                improvement_score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 创建文档版本表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_versions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                doc_id VARCHAR(255) NOT NULL,
                version INTEGER NOT NULL,
                filename VARCHAR(255) NOT NULL,
                filepath TEXT,
                chunk_count INTEGER NOT NULL,
                operation VARCHAR(50) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE (doc_id, version)
            )
        """
        )

        # 创建文档操作日志表
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_operations_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                doc_id VARCHAR(255),
                operation VARCHAR(50) NOT NULL,
                filename VARCHAR(255),
                old_filename VARCHAR(255),
                reason TEXT,
                status VARCHAR(50) NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # LLM使用日志与预算策略（Phase 1 corrected plan）
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_usage_logs (
                id UUID PRIMARY KEY,
                tenant_id VARCHAR(128) NOT NULL,
                provider VARCHAR(64) NOT NULL,
                model VARCHAR(128) NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                estimated_cost_usd NUMERIC(12, 6) DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                status VARCHAR(32) NOT NULL,
                trace_id VARCHAR(128),
                route_mode VARCHAR(32),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_budget_policies (
                tenant_id VARCHAR(128) PRIMARY KEY,
                monthly_budget_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
                soft_limit_ratio NUMERIC(5, 4) NOT NULL DEFAULT 0.8,
                hard_limit_ratio NUMERIC(5, 4) NOT NULL DEFAULT 1.0,
                policy_mode VARCHAR(32) NOT NULL DEFAULT 'local_only',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Prompt核心表（P0修复：统一schema到init_database.py）
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prompts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                subcategory VARCHAR(100),
                version VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                variables JSONB DEFAULT '{}'::jsonb,
                metadata JSONB DEFAULT '{}'::jsonb,
                is_active BOOLEAN DEFAULT true,
                is_latest BOOLEAN DEFAULT false,
                priority INTEGER DEFAULT 0,
                performance_score NUMERIC(5, 4) DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255),
                updated_by VARCHAR(255),
                UNIQUE (name, category, version)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
                version VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                variables JSONB DEFAULT '{}'::jsonb,
                metadata JSONB DEFAULT '{}'::jsonb,
                change_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255),
                UNIQUE (prompt_id, version)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_usage_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
                session_id VARCHAR(255),
                context JSONB DEFAULT '{}'::jsonb,
                variables_used JSONB DEFAULT '{}'::jsonb,
                execution_time_ms INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                user_feedback INTEGER CHECK (user_feedback >= 1 AND user_feedback <= 5),
                llm_response JSONB,
                tokens_used INTEGER DEFAULT 0,
                model_name VARCHAR(255),
                temperature NUMERIC(4, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_tags (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_tag_relations (
                prompt_id UUID NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
                tag_id UUID NOT NULL REFERENCES prompt_tags(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (prompt_id, tag_id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_experiments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                prompt_a_id UUID NOT NULL REFERENCES prompts(id),
                prompt_b_id UUID NOT NULL REFERENCES prompts(id),
                traffic_split NUMERIC(4, 3) NOT NULL DEFAULT 0.5,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                metrics JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (name)
            )
            """
        )

        cur.execute(
            """
            INSERT INTO schema_migrations (version, description)
            VALUES (%s, %s)
            ON CONFLICT (version) DO NOTHING
            """,
            ("2026_02_10_llm_dispatch_foundation", "Add llm usage/budget governance"),
        )

        # Prompt schema migration（P0修复：添加schema版本记录）
        cur.execute(
            """
            INSERT INTO schema_migrations (version, description)
            VALUES (%s, %s)
            ON CONFLICT (version) DO NOTHING
            """,
            ("2026_02_10_prompt_schema_unify_v1", "Unify prompt schema to init_database.py with core tables and indexes"),
        )

        # 长期记忆表（给对话记忆系统使用）
        # 会话记忆表（独立于 user_sessions，避免外键依赖）
        if pgvector_available:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255),
                    memory_type VARCHAR(50) NOT NULL,
                    content JSONB NOT NULL,
                    embedding vector(768),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255),
                    memory_type VARCHAR(50) NOT NULL,
                    content JSONB NOT NULL,
                    embedding JSONB,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename)",
            "CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(doc_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_quality_docid_score ON document_quality_scores(doc_id, quality_score)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_type ON query_feedback(feedback_type)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_created ON query_feedback(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_doc_quality ON document_quality_scores(quality_score)",
            "CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON document_versions(doc_id)",
            "CREATE INDEX IF NOT EXISTS idx_doc_versions_active ON document_versions(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_doc_operations_created ON document_operations_log(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_conversation_memories_session ON conversation_memories(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_conversation_memories_type ON conversation_memories(memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_llm_usage_tenant_created ON llm_usage_logs(tenant_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_llm_usage_provider ON llm_usage_logs(provider)",
            "CREATE INDEX IF NOT EXISTS idx_llm_usage_trace ON llm_usage_logs(trace_id)",
            # Prompt相关索引（P0修复）
            "CREATE INDEX IF NOT EXISTS idx_prompts_category_name ON prompts(category, name)",
            "CREATE INDEX IF NOT EXISTS idx_prompts_is_active_latest ON prompts(is_active, is_latest)",
            "CREATE INDEX IF NOT EXISTS idx_prompts_performance ON prompts(performance_score DESC)",
            "CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id ON prompt_versions(prompt_id)",
            "CREATE INDEX IF NOT EXISTS idx_prompt_usage_prompt_created ON prompt_usage_logs(prompt_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_prompt_usage_session ON prompt_usage_logs(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_prompt_experiments_status ON prompt_experiments(status)",
        ]

        # 只有pgvector可用时才创建向量索引
        if pgvector_available:
            indexes.append(
                "CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops)"
            )
            indexes.append(
                "CREATE INDEX IF NOT EXISTS idx_conversation_memories_embedding ON conversation_memories USING ivfflat (embedding vector_cosine_ops)"
            )

        for index_sql in indexes:
            try:
                cur.execute(index_sql)
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")

        # 创建更新时间的触发器
        cur.execute(
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """
        )

        cur.execute(
            """
            DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
            CREATE TRIGGER update_documents_updated_at
                BEFORE UPDATE ON documents
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """
        )

        # 创建文档版本触发器函数
        cur.execute(
            """
            CREATE OR REPLACE FUNCTION update_document_versions()
            RETURNS TRIGGER AS $$
            BEGIN
                UPDATE document_versions
                SET is_active = FALSE
                WHERE doc_id = NEW.doc_id AND is_active = TRUE AND version != NEW.version;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """
        )

        cur.execute(
            """
            DROP TRIGGER IF EXISTS trigger_update_document_versions ON document_versions;
            CREATE TRIGGER trigger_update_document_versions
                AFTER INSERT ON document_versions
                FOR EACH ROW
                EXECUTE FUNCTION update_document_versions();
        """
        )

        # Prompt表updated_at触发器（P0修复）
        cur.execute(
            """
            DROP TRIGGER IF EXISTS update_prompts_updated_at ON prompts;
            CREATE TRIGGER update_prompts_updated_at
                BEFORE UPDATE ON prompts
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """
        )

        cur.execute(
            """
            DROP TRIGGER IF EXISTS update_prompt_experiments_updated_at ON prompt_experiments;
            CREATE TRIGGER update_prompt_experiments_updated_at
                BEFORE UPDATE ON prompt_experiments
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """
        )

        conn.commit()
        logger.info("Database initialized successfully")

        # 打印表信息
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        )
        tables = [row[0] for row in cur.fetchall()]
        logger.info(f"Created tables: {', '.join(tables)}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize database: {e}")
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database()
