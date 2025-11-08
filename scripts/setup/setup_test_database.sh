#!/bin/bash
# 设置测试数据库 - 适配 macOS + Homebrew PostgreSQL

set -e  # 遇到错误立即退出

echo "========================================="
echo "📦 PostgreSQL 测试数据库设置脚本"
echo "========================================="

# 检查 PostgreSQL 是否运行
if ! pg_isready -q; then
    echo "❌ PostgreSQL 未运行，正在启动..."
    brew services start postgresql@14 || brew services start postgresql
    sleep 3

    if ! pg_isready -q; then
        echo "❌ PostgreSQL 启动失败，请手动启动："
        echo "   brew services start postgresql@14"
        exit 1
    fi
fi

echo "✅ PostgreSQL 运行中"

# 数据库配置
DB_NAME="ai_workflow"
DB_USER=$(whoami)  # Homebrew PostgreSQL 默认使用当前用户

echo ""
echo "📋 配置信息:"
echo "  - 数据库: $DB_NAME"
echo "  - 用户: $DB_USER"
echo "  - 主机: localhost:5432"

# 删除旧数据库（如果存在）
echo ""
echo "🗑️  清理旧数据库..."
psql -U $DB_USER postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true

# 创建新数据库
echo "🆕 创建数据库 '$DB_NAME'..."
psql -U $DB_USER postgres -c "CREATE DATABASE $DB_NAME;"

# 启用 pgvector 扩展
echo "🔌 启用 pgvector 扩展..."

# 尝试创建扩展，如果失败则跳过（表可能不使用向量）
if psql -U $DB_USER $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
    echo "✅ pgvector 扩展已启用"
else
    echo "⚠️  pgvector 扩展未安装，跳过向量功能"
    echo "    如需使用向量搜索，请安装: brew install pgvector"
    SKIP_VECTOR=true
fi

# 创建表结构
echo "📊 创建表结构..."

psql -U $DB_USER $DB_NAME <<EOF
-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    chunk_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文档块表（包含向量）
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(36) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding TEXT,  -- 向量存储为TEXT（pgvector不可用时）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doc_id, chunk_id)
);

-- 创建向量索引（加速检索）- 仅在 pgvector 可用时创建
-- CREATE INDEX IF NOT EXISTS idx_embedding ON document_chunks
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- 创建文档ID索引
CREATE INDEX IF NOT EXISTS idx_doc_id ON document_chunks(doc_id);
EOF

echo "✅ 表结构创建成功"

# 插入测试数据
echo ""
echo "📝 插入测试数据..."

psql -U $DB_USER $DB_NAME <<EOF
-- 插入测试文档
INSERT INTO documents (id, filename, filepath, chunk_count) VALUES
('test-doc-1', 'langchain_intro.txt', '/test/langchain_intro.txt', 3),
('test-doc-2', 'ai_basics.txt', '/test/ai_basics.txt', 2);

-- 插入测试文档块（暂不包含向量，需要 Python 脚本生成）
INSERT INTO document_chunks (doc_id, chunk_id, content) VALUES
('test-doc-1', 0, 'LangChain 1.0 是一个重大升级，引入了统一的 create_agent API，简化了 Agent 的创建流程。新版本采用瘦身架构，使得代码更加清晰易维护。'),
('test-doc-1', 1, 'LangChain 1.0 新增了 Middleware 机制，允许开发者在 Agent 运行过程中进行干预，提升了可观测性和可定制性。'),
('test-doc-1', 2, 'LangChain 1.0 增强了结构化输出控制，支持更好的 JSON、Schema 等结构化输出，便于工具集成和下游解析。'),
('test-doc-2', 0, '人工智能（AI）是计算机科学的一个分支，旨在创建能够模拟人类智能行为的系统。机器学习是AI的核心技术之一。'),
('test-doc-2', 1, '深度学习是机器学习的一个子集，使用多层神经网络来学习数据的表示。它在图像识别、自然语言处理等领域取得了突破性进展。');
EOF

echo "✅ 测试数据插入成功"

# 验证数据
echo ""
echo "🔍 验证数据..."
psql -U $DB_USER $DB_NAME -c "SELECT COUNT(*) as document_count FROM documents;"
psql -U $DB_USER $DB_NAME -c "SELECT COUNT(*) as chunk_count FROM document_chunks;"

echo ""
echo "========================================="
echo "✅ 数据库设置完成！"
echo "========================================="
echo ""
echo "📝 下一步:"
echo "  1. 运行: python scripts/generate_test_embeddings.py"
echo "  2. 运行: python test_zhipu_integration.py"
echo ""
