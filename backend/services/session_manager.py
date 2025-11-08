"""
会话管理模块 - 处理用户会话和反馈的持久化存储
"""

import uuid
import datetime
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from backend.services.core.vectorstore import VectorStore
from backend.config import settings

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class QueryPhase(Enum):
    """查询阶段"""
    INITIAL = "initial"
    REFINED = "refined"
    OPTIMIZED = "optimized"


@dataclass
class SessionMessage:
    """会话消息"""
    message_id: str
    session_id: str
    message_type: str  # "user_query", "assistant_response", "feedback"
    content: Dict[str, Any]
    timestamp: datetime.datetime
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'message_id': self.message_id,
            'session_id': self.session_id,
            'message_type': self.message_type,
            'content': json.dumps(self.content),
            'timestamp': self.timestamp,
            'metadata': json.dumps(self.metadata) if self.metadata else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionMessage':
        """从字典创建实例"""
        return cls(
            message_id=data['message_id'],
            session_id=data['session_id'],
            message_type=data['message_type'],
            content=json.loads(data['content']),
            timestamp=data['timestamp'],
            metadata=json.loads(data['metadata']) if data.get('metadata') else None
        )


@dataclass
class UserSession:
    """用户会话"""
    session_id: str
    user_id: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime.datetime = None
    last_activity: datetime.datetime = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.datetime.now()


class SessionManager:
    """会话管理器 - 处理会话和消息的持久化"""

    def __init__(self, vectorstore: VectorStore):
        self.vectorstore = vectorstore
        self._init_database()

    def _init_database(self):
        """初始化会话管理相关的数据库表"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # 创建用户会话表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255),
                    status VARCHAR(50) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB,
                    query_count INTEGER DEFAULT 0,
                    feedback_count INTEGER DEFAULT 0
                )
            """)

            # 创建会话消息表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS session_messages (
                    message_id VARCHAR(255) PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    message_type VARCHAR(50) NOT NULL,
                    content JSONB NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB,
                    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
                )
            """)

            # 创建RAG状态表 - 用于跟踪RAG系统状态和优化
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rag_system_state (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id VARCHAR(255),
                    query_id VARCHAR(255),
                    query_text TEXT NOT NULL,
                    retrieval_config JSONB,
                    llm_config JSONB,
                    performance_metrics JSONB,
                    optimization_history JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
                )
            """)

            # 创建反馈驱动的优化触发器表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback_optimization_triggers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    trigger_type VARCHAR(100) NOT NULL,
                    trigger_data JSONB NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    processing_result JSONB,
                    error_message TEXT
                )
            """)

            # 创建自适应配置表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS adaptive_configurations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    config_type VARCHAR(100) NOT NULL,
                    config_key VARCHAR(255) NOT NULL,
                    config_value JSONB NOT NULL,
                    performance_score FLOAT,
                    usage_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    UNIQUE (config_type, config_key)
                )
            """)

            # 创建索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_status ON user_sessions(status)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON user_sessions(last_activity)",
                "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON session_messages(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON session_messages(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_rag_state_session_id ON rag_system_state(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_rag_state_query_id ON rag_system_state(query_id)",
                "CREATE INDEX IF NOT EXISTS idx_opt_triggers_status ON feedback_optimization_triggers(status)",
                "CREATE INDEX IF NOT EXISTS idx_adaptive_config_type ON adaptive_configurations(config_type)"
            ]

            for index_sql in indexes:
                try:
                    cur.execute(index_sql)
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")

            # 创建更新时间的触发器
            cur.execute("""
                CREATE OR REPLACE FUNCTION update_rag_state_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)

            cur.execute("""
                DROP TRIGGER IF EXISTS update_rag_state_updated_at_trigger ON rag_system_state;
                CREATE TRIGGER update_rag_state_updated_at_trigger
                    BEFORE UPDATE ON rag_system_state
                    FOR EACH ROW
                    EXECUTE FUNCTION update_rag_state_updated_at();
            """)

            # 创建会话统计更新函数
            cur.execute("""
                CREATE OR REPLACE FUNCTION update_session_stats()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NEW.message_type = 'user_query' THEN
                        UPDATE user_sessions
                        SET query_count = query_count + 1,
                            last_activity = NEW.timestamp
                        WHERE session_id = NEW.session_id;
                    ELSIF NEW.message_type = 'feedback' THEN
                        UPDATE user_sessions
                        SET feedback_count = feedback_count + 1,
                            last_activity = NEW.timestamp
                        WHERE session_id = NEW.session_id;
                    ELSE
                        UPDATE user_sessions
                        SET last_activity = NEW.timestamp
                        WHERE session_id = NEW.session_id;
                    END IF;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)

            cur.execute("""
                DROP TRIGGER IF EXISTS update_session_stats_trigger ON session_messages;
                CREATE TRIGGER update_session_stats_trigger
                    AFTER INSERT ON session_messages
                    FOR EACH ROW
                    EXECUTE FUNCTION update_session_stats();
            """)

            conn.commit()
            logger.info("Session management database tables initialized successfully")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to initialize session management database: {e}")
            raise e
        finally:
            cur.close()
            conn.close()

    def create_session(self, user_id: str = None, metadata: Dict = None) -> str:
        """创建新会话"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            session_id = str(uuid.uuid4())

            cur.execute("""
                INSERT INTO user_sessions (session_id, user_id, metadata)
                VALUES (%s, %s, %s)
            """, (session_id, user_id, json.dumps(metadata) if metadata else None))

            conn.commit()
            logger.info(f"Created new session: {session_id}")
            return session_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create session: {e}")
            raise e
        finally:
            cur.close()
            conn.close()

    def add_message(self, session_id: str, message_type: str, content: Dict,
                   metadata: Dict = None) -> str:
        """添加会话消息"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            message_id = str(uuid.uuid4())

            cur.execute("""
                INSERT INTO session_messages (message_id, session_id, message_type, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (message_id, session_id, message_type, json.dumps(content),
                  json.dumps(metadata) if metadata else None))

            conn.commit()
            logger.debug(f"Added message {message_id} to session {session_id}")
            return message_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add message to session {session_id}: {e}")
            raise e
        finally:
            cur.close()
            conn.close()

    def record_rag_state(self, session_id: str, query_id: str, query_text: str,
                        retrieval_config: Dict, llm_config: Dict, performance_metrics: Dict = None):
        """记录RAG系统状态"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO rag_system_state
                (session_id, query_id, query_text, retrieval_config, llm_config, performance_metrics)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, query_id, query_text,
                  json.dumps(retrieval_config), json.dumps(llm_config),
                  json.dumps(performance_metrics) if performance_metrics else None))

            conn.commit()
            logger.debug(f"Recorded RAG state for query {query_id}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record RAG state: {e}")
        finally:
            cur.close()
            conn.close()

    def trigger_optimization(self, trigger_type: str, trigger_data: Dict) -> str:
        """触发优化任务"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            trigger_id = str(uuid.uuid4())

            cur.execute("""
                INSERT INTO feedback_optimization_triggers (trigger_type, trigger_data, status)
                VALUES (%s, %s, 'pending')
            """, (trigger_type, json.dumps(trigger_data)))

            conn.commit()
            logger.info(f"Triggered optimization: {trigger_type} - {trigger_id}")
            return trigger_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to trigger optimization: {e}")
            raise e
        finally:
            cur.close()
            conn.close()

    def get_pending_optimizations(self, limit: int = 10) -> List[Dict]:
        """获取待处理的优化任务"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT id, trigger_type, trigger_data, created_at
                FROM feedback_optimization_triggers
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT %s
            """, (limit,))

            optimizations = []
            for row in cur.fetchall():
                optimizations.append({
                    'id': row[0],
                    'trigger_type': row[1],
                    'trigger_data': json.loads(row[2]),
                    'created_at': row[3]
                })

            return optimizations

        except Exception as e:
            logger.error(f"Failed to get pending optimizations: {e}")
            return []
        finally:
            cur.close()
            conn.close()

    def update_optimization_status(self, trigger_id: str, status: str,
                                result: Dict = None, error_message: str = None):
        """更新优化任务状态"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE feedback_optimization_triggers
                SET status = %s,
                    processed_at = CURRENT_TIMESTAMP,
                    processing_result = %s,
                    error_message = %s
                WHERE id = %s
            """, (status, json.dumps(result) if result else None, error_message, trigger_id))

            conn.commit()
            logger.info(f"Updated optimization status: {trigger_id} -> {status}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update optimization status: {e}")
        finally:
            cur.close()
            conn.close()

    def save_adaptive_config(self, config_type: str, config_key: str,
                           config_value: Dict, performance_score: float = None):
        """保存自适应配置"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO adaptive_configurations
                (config_type, config_key, config_value, performance_score)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (config_type, config_key)
                DO UPDATE SET
                    config_value = EXCLUDED.config_value,
                    performance_score = EXCLUDED.performance_score,
                    usage_count = adaptive_configurations.usage_count + 1,
                    last_updated = CURRENT_TIMESTAMP
            """, (config_type, config_key, json.dumps(config_value), performance_score))

            conn.commit()
            logger.debug(f"Saved adaptive config: {config_type}.{config_key}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save adaptive config: {e}")
        finally:
            cur.close()
            conn.close()

    def get_adaptive_config(self, config_type: str, config_key: str) -> Optional[Dict]:
        """获取自适应配置"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT config_value, performance_score, usage_count
                FROM adaptive_configurations
                WHERE config_type = %s AND config_key = %s AND is_active = TRUE
            """, (config_type, config_key))

            result = cur.fetchone()
            if result:
                config_value, performance_score, usage_count = result
                return {
                    'config_value': json.loads(config_value),
                    'performance_score': performance_score,
                    'usage_count': usage_count
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get adaptive config: {e}")
            return None
        finally:
            cur.close()
            conn.close()

    def get_session_history(self, session_id: str, limit: int = 50) -> List[SessionMessage]:
        """获取会话历史"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT message_id, session_id, message_type, content, timestamp, metadata
                FROM session_messages
                WHERE session_id = %s
                ORDER BY timestamp ASC
                LIMIT %s
            """, (session_id, limit))

            messages = []
            for row in cur.fetchall():
                messages.append(SessionMessage(
                    message_id=row[0],
                    session_id=row[1],
                    message_type=row[2],
                    content=json.loads(row[3]),
                    timestamp=row[4],
                    metadata=json.loads(row[5]) if row[5] else None
                ))

            return messages

        except Exception as e:
            logger.error(f"Failed to get session history: {e}")
            return []
        finally:
            cur.close()
            conn.close()

    def get_rag_performance_analytics(self, session_id: str = None, days: int = 7) -> Dict:
        """获取RAG性能分析数据"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # 构建查询条件
            where_clause = "WHERE created_at > NOW() - INTERVAL '%s days'"
            params = [days]

            if session_id:
                where_clause += " AND session_id = %s"
                params.append(session_id)

            # 获取平均性能指标
            cur.execute(f"""
                SELECT
                    AVG((performance_metrics->>'response_time')::float) as avg_response_time,
                    AVG((performance_metrics->>'retrieval_score')::float) as avg_retrieval_score,
                    AVG((performance_metrics->>'reranking_score')::float) as avg_reranking_score,
                    COUNT(*) as total_queries
                FROM rag_system_state
                {where_clause}
            """, params)

            performance_data = cur.fetchone()
            avg_response_time, avg_retrieval_score, avg_reranking_score, total_queries = performance_data

            # 获取配置使用统计
            cur.execute(f"""
                SELECT
                    retrieval_config->>'vector_weight' as vector_weight,
                    retrieval_config->>'bm25_weight' as bm25_weight,
                    COUNT(*) as usage_count,
                    AVG((performance_metrics->>'response_time')::float) as avg_response_time
                FROM rag_system_state
                {where_clause}
                GROUP BY retrieval_config->>'vector_weight', retrieval_config->>'bm25_weight'
                ORDER BY usage_count DESC
            """, params)

            config_stats = []
            for row in cur.fetchall():
                config_stats.append({
                    'vector_weight': float(row[0]) if row[0] else None,
                    'bm25_weight': float(row[1]) if row[1] else None,
                    'usage_count': row[2],
                    'avg_response_time': float(row[3]) if row[3] else None
                })

            return {
                'performance_summary': {
                    'avg_response_time': float(avg_response_time) if avg_response_time else None,
                    'avg_retrieval_score': float(avg_retrieval_score) if avg_retrieval_score else None,
                    'avg_reranking_score': float(avg_reranking_score) if avg_reranking_score else None,
                    'total_queries': total_queries or 0
                },
                'configuration_usage': config_stats,
                'period_days': days,
                'session_id': session_id
            }

        except Exception as e:
            logger.error(f"Failed to get RAG performance analytics: {e}")
            return {}
        finally:
            cur.close()
            conn.close()

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """清理旧会话数据"""
        conn = self.vectorstore.get_connection()
        cur = conn.cursor()

        try:
            # 归档旧会话
            cur.execute("""
                UPDATE user_sessions
                SET status = 'archived'
                WHERE status = 'active'
                AND last_activity < NOW() - INTERVAL '%s days'
            """, (days,))

            archived_count = cur.rowcount

            # 获取要删除的消息的会话ID
            cur.execute("""
                SELECT session_id FROM user_sessions
                WHERE status = 'archived'
                AND last_activity < NOW() - INTERVAL '%s days'
            """, (days * 2,))  # 2倍时间后删除

            old_session_ids = [row[0] for row in cur.fetchall()]

            if old_session_ids:
                # 删除相关消息和RAG状态
                cur.execute("""
                    DELETE FROM session_messages
                    WHERE session_id = ANY(%s)
                """, (old_session_ids,))

                cur.execute("""
                    DELETE FROM rag_system_state
                    WHERE session_id = ANY(%s)
                """, (old_session_ids,))

                # 删除会话记录
                cur.execute("""
                    DELETE FROM user_sessions
                    WHERE session_id = ANY(%s)
                """, (old_session_ids,))

            conn.commit()
            logger.info(f"Cleaned up {archived_count} old sessions")
            return archived_count

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
        finally:
            cur.close()
            conn.close()