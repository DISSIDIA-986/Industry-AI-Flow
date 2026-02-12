"""
综合数据库初始化脚本
整合RAG系统和Prompt管理系统的完整数据库架构
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.database.driver_compat import (
    connect as connect_db,
    fetchall_dicts,
    fetchone_dict,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ComprehensiveDatabaseInitializer:
    """综合数据库初始化器"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        self.cursor = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.conn = connect_db(self.database_url)
            self.cursor = self.conn.cursor()
            logger.info("Database connection established successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    def disconnect(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

    def check_extension(self, extension_name: str) -> bool:
        """检查扩展是否可用"""
        try:
            self.cursor.execute(
                f"SELECT 1 FROM pg_extension WHERE extname = '{extension_name}'"
            )
            return self.cursor.fetchone() is not None
        except Exception as e:
            logger.warning(f"Error checking extension {extension_name}: {e}")
            return False

    def enable_extension(self, extension_name: str) -> bool:
        """启用PostgreSQL扩展"""
        try:
            self.cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {extension_name}")
            self.conn.commit()
            logger.info(f"Extension {extension_name} enabled successfully")
            return True
        except Exception as e:
            logger.warning(f"Failed to enable extension {extension_name}: {e}")
            self.conn.rollback()
            return False

    def execute_sql_file(self, file_path: str) -> bool:
        """执行SQL文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sql_content = f.read()

            # 分割SQL语句（简单实现）
            statements = []
            current_statement = ""

            for line in sql_content.split("\n"):
                line = line.strip()
                if line.startswith("--") or not line:
                    continue
                current_statement += line + "\n"
                if line.endswith(";"):
                    statements.append(current_statement.strip())
                    current_statement = ""

            # 执行SQL语句
            for statement in statements:
                if statement:
                    try:
                        self.cursor.execute(statement)
                        logger.debug(f"Executed: {statement[:100]}...")
                    except Exception as e:
                        logger.warning(
                            f"Failed to execute statement: {statement[:100]}... Error: {e}"
                        )
                        # 继续执行其他语句

            self.conn.commit()
            logger.info(f"SQL file {file_path} executed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to execute SQL file {file_path}: {e}")
            self.conn.rollback()
            return False

    def create_missing_tables(self) -> bool:
        """创建缺失的归档表"""
        archive_tables = [
            """
            CREATE TABLE IF NOT EXISTS query_feedback_archive (
                LIKE query_feedback INCLUDING ALL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS document_operations_log_archive (
                LIKE document_operations_log INCLUDING ALL
            )
            """,
        ]

        for table_sql in archive_tables:
            try:
                self.cursor.execute(table_sql)
                logger.info("Archive table created/verified")
            except Exception as e:
                logger.warning(f"Failed to create archive table: {e}")

        self.conn.commit()
        return True

    def initialize_prompt_data(self) -> bool:
        """初始化Prompt数据"""
        try:
            # 检查是否已有Prompt数据
            self.cursor.execute("SELECT COUNT(*) as count FROM prompts")
            row = fetchone_dict(self.cursor) or {}
            count = int(row.get("count") or 0)

            if count > 0:
                logger.info(f"Found {count} existing prompts, skipping initialization")
                return True

            # 插入默认Prompt
            default_prompts = [
                {
                    "name": "Intent Classification System",
                    "category": "INTENT_CLASSIFICATION",
                    "subcategory": "classification",
                    "version": "1.0.0",
                    "content": """Based on the user's query, classify their intent into one of the following categories:
1. RAG - Information retrieval and question answering
2. CODE_EXECUTION - Code analysis, review, or execution
3. DATA_ANALYSIS - Data processing, analysis, or visualization
4. EDA - Exploratory data analysis
5. OCR - Optical character recognition
6. ARCHITECTURE - Building and architectural analysis

Query: {query}

Response format: JSON with "intent" and "confidence" fields.""",
                    "variables": {"query": "user query text"},
                    "metadata": {
                        "description": "Intent classification for routing decisions",
                        "author": "system",
                    },
                    "priority": 100,
                    "is_active": True,
                    "is_latest": True,
                },
                {
                    "name": "RAG Response Generator",
                    "category": "RAG",
                    "subcategory": "response",
                    "version": "1.0.0",
                    "content": """Using the following retrieved context, provide a comprehensive and accurate answer to the user's question.

Context:
{context}

Question: {question}

Requirements:
1. Base your answer primarily on the provided context
2. If context doesn't contain sufficient information, clearly state this
3. Provide specific details and examples when possible
4. Structure your answer with clear headings and bullet points
5. Include relevant source citations if applicable""",
                    "variables": {
                        "context": "retrieved context",
                        "question": "user question",
                    },
                    "metadata": {
                        "description": "RAG response generation with retrieved context",
                        "author": "system",
                    },
                    "priority": 95,
                    "is_active": True,
                    "is_latest": True,
                },
                {
                    "name": "Code Analysis Assistant",
                    "category": "CODE_EXECUTION",
                    "subcategory": "analysis",
                    "version": "1.0.0",
                    "content": """Please analyze the following code and provide comprehensive feedback:

Code:
```python
{code}
```

Analysis areas:
1. Code Quality & Best Practices
2. Performance Optimization
3. Security Considerations
4. Bug Detection & Fixes
5. Documentation & Comments
6. Suggestions for Improvement

Provide your analysis in a structured format with specific code examples where applicable.""",
                    "variables": {"code": "Python code to analyze"},
                    "metadata": {
                        "description": "Comprehensive code analysis assistant",
                        "author": "system",
                    },
                    "priority": 90,
                    "is_active": True,
                    "is_latest": True,
                },
                {
                    "name": "Building Document OCR Processor",
                    "category": "OCR",
                    "subcategory": "architecture",
                    "version": "1.0.0",
                    "content": """Process the following OCR results from building documents and extract structured information:

OCR Results:
{ocr_results}

Extract and organize:
1. Document Type (floor plan, elevation, section, detail)
2. Building Dimensions and Measurements
3. Room Names and Areas
4. Construction Materials and Specifications
5. Structural Elements
6. Important Annotations and Labels
7. Scale Information
8. Date/Version Information

Format the output as structured JSON with clear categorization.""",
                    "variables": {"ocr_results": "OCR extraction results"},
                    "metadata": {
                        "description": "Building document OCR processing and structuring",
                        "author": "system",
                    },
                    "priority": 85,
                    "is_active": True,
                    "is_latest": True,
                },
            ]

            for prompt_data in default_prompts:
                self.cursor.execute(
                    """
                    INSERT INTO prompts
                    (name, category, subcategory, version, content, variables, metadata,
                     is_active, is_latest, priority, created_by, created_at)
                    VALUES (%(name)s, %(category)s, %(subcategory)s, %(version)s, %(content)s,
                           %(variables)s, %(metadata)s, %(is_active)s, %(is_latest)s, %(priority)s,
                           'system', CURRENT_TIMESTAMP)
                """,
                    prompt_data,
                )

            self.conn.commit()
            logger.info(f"Initialized {len(default_prompts)} default prompts")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize prompt data: {e}")
            self.conn.rollback()
            return False

    def setup_automated_maintenance(self) -> bool:
        """设置自动化维护任务"""
        try:
            # 创建归档表
            self.create_missing_tables()

            # 设置定期统计更新函数
            maintenance_functions = [
                """
                CREATE OR REPLACE FUNCTION daily_maintenance()
                RETURNS void AS $$
                BEGIN
                    -- 刷新统计
                    PERFORM refresh_prompt_stats();

                    -- 归档旧数据（每周执行一次，这里仅作为示例）
                    -- PERFORM archive_old_data();

                    -- 记录维护日志
                    INSERT INTO document_operations_log (operation, status, created_at)
                    VALUES ('daily_maintenance', 'completed', CURRENT_TIMESTAMP);

                    RAISE NOTICE 'Daily maintenance completed';
                END;
                $$ LANGUAGE plpgsql;
                """,
                """
                CREATE OR REPLACE FUNCTION monthly_archive()
                RETURNS void AS $$
                BEGIN
                    -- 归档旧数据
                    PERFORM archive_old_data();

                    -- 记录归档日志
                    INSERT INTO document_operations_log (operation, status, created_at)
                    VALUES ('monthly_archive', 'completed', CURRENT_TIMESTAMP);

                    RAISE NOTICE 'Monthly archive completed';
                END;
                $$ LANGUAGE plpgsql;
                """,
            ]

            for func_sql in maintenance_functions:
                try:
                    self.cursor.execute(func_sql)
                    logger.info("Maintenance function created/updated")
                except Exception as e:
                    logger.warning(f"Failed to create maintenance function: {e}")

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to setup automated maintenance: {e}")
            self.conn.rollback()
            return False

    def verify_schema(self) -> Dict[str, Any]:
        """验证数据库架构"""
        try:
            verification_result = {
                "tables": {},
                "indexes": {},
                "extensions": {},
                "views": {},
                "functions": {},
                "total_status": "success",
            }

            # 检查表
            expected_tables = [
                "documents",
                "document_chunks",
                "query_feedback",
                "document_quality_scores",
                "query_optimization_log",
                "document_versions",
                "document_operations_log",
                "prompts",
                "prompt_versions",
                "prompt_usage_logs",
                "prompt_experiments",
                "prompt_tags",
                "prompt_tag_relations",
                "prompt_daily_stats",
                "prompt_weekly_stats",
                "prompt_monthly_stats",
            ]

            self.cursor.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
            """
            )
            existing_tables = {
                str(row.get("table_name"))
                for row in fetchall_dicts(self.cursor)
                if row.get("table_name")
            }

            for table in expected_tables:
                verification_result["tables"][table] = table in existing_tables

            # 检查扩展
            expected_extensions = ["uuid-ossp", "pgcrypto", "vector"]
            for ext in expected_extensions:
                verification_result["extensions"][ext] = self.check_extension(ext)

            # 检查视图
            self.cursor.execute(
                """
                SELECT table_name FROM information_schema.views
                WHERE table_schema = 'public'
            """
            )
            existing_views = {
                str(row.get("table_name"))
                for row in fetchall_dicts(self.cursor)
                if row.get("table_name")
            }
            verification_result["views"]["prompt_summary"] = (
                "prompt_summary" in existing_views
            )

            # 统计结果
            total_items = len(expected_tables) + len(expected_extensions) + 1
            passed_items = (
                sum(verification_result["tables"][table] for table in expected_tables)
                + sum(
                    verification_result["extensions"][ext]
                    for ext in expected_extensions
                )
                + verification_result["views"]["prompt_summary"]
            )

            success_rate = (passed_items / total_items) * 100 if total_items > 0 else 0

            verification_result["success_rate"] = success_rate
            verification_result["total_items"] = total_items
            verification_result["passed_items"] = passed_items

            if success_rate >= 90:
                verification_result["total_status"] = "excellent"
            elif success_rate >= 70:
                verification_result["total_status"] = "good"
            elif success_rate >= 50:
                verification_result["total_status"] = "fair"
            else:
                verification_result["total_status"] = "needs_improvement"

            return verification_result

        except Exception as e:
            logger.error(f"Failed to verify schema: {e}")
            return {"error": str(e), "total_status": "failed"}

    def initialize_database(self) -> bool:
        """执行完整的数据库初始化"""
        try:
            logger.info("Starting comprehensive database initialization...")

            # 连接数据库
            if not self.connect():
                return False

            # 执行SQL架构文件
            schema_file = (
                Path(__file__).parent
                / "migrations"
                / "001_create_comprehensive_schema.sql"
            )
            if schema_file.exists():
                logger.info("Executing comprehensive schema from SQL file...")
                if not self.execute_sql_file(str(schema_file)):
                    return False
            else:
                logger.warning(
                    "SQL schema file not found, using manual initialization..."
                )
                # 这里可以添加手动初始化逻辑

            # 初始化Prompt数据
            if not self.initialize_prompt_data():
                return False

            # 设置自动化维护
            if not self.setup_automated_maintenance():
                return False

            # 验证架构
            verification_result = self.verify_schema()
            logger.info("Database verification completed")
            logger.info(f"Status: {verification_result['total_status']}")
            logger.info(
                f"Success rate: {verification_result.get('success_rate', 0):.1f}%"
            )

            logger.info("Comprehensive database initialization completed successfully!")
            return True

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
        finally:
            self.disconnect()


def main():
    """主函数"""
    # 从环境变量或配置文件获取数据库URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False

    initializer = ComprehensiveDatabaseInitializer(database_url)
    return initializer.initialize_database()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
