#!/bin/bash
# 数据库迁移脚本: 将 TEXT 类型的 embedding 列迁移到 vector 类型

set -e  # 遇到错误立即退出

echo "========================================="
echo "🔄 数据库迁移: TEXT → vector 类型"
echo "========================================="

DB_NAME="ai_workflow"
DB_USER=$(whoami)

# 检查 PostgreSQL 是否运行
if ! pg_isready -q; then
    echo "❌ PostgreSQL 未运行，正在启动..."
    brew services start postgresql@14
    sleep 3

    if ! pg_isready -q; then
        echo "❌ PostgreSQL 启动失败"
        exit 1
    fi
fi

echo "✅ PostgreSQL 运行中"

# 检查 pgvector 扩展是否已安装
echo ""
echo "🔍 检查 pgvector 扩展..."
PGVECTOR_INSTALLED=$(psql -U $DB_USER $DB_NAME -tAc "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")

if [ "$PGVECTOR_INSTALLED" = "f" ]; then
    echo "📦 启用 pgvector 扩展..."
    psql -U $DB_USER $DB_NAME -c "CREATE EXTENSION vector;"
    echo "✅ pgvector 扩展已启用"
else
    echo "✅ pgvector 扩展已存在"
fi

# 检查当前 embedding 列类型
echo ""
echo "🔍 检查当前表结构..."
CURRENT_TYPE=$(psql -U $DB_USER $DB_NAME -tAc "SELECT data_type FROM information_schema.columns WHERE table_name='document_chunks' AND column_name='embedding';")

if [ "$CURRENT_TYPE" = "text" ]; then
    echo "⚠️  当前 embedding 列类型为 TEXT，需要迁移"

    # 备份数据
    echo ""
    echo "💾 步骤 1: 备份现有数据..."
    psql -U $DB_USER $DB_NAME <<EOF
-- 创建备份表
DROP TABLE IF EXISTS document_chunks_backup;
CREATE TABLE document_chunks_backup AS SELECT * FROM document_chunks;
EOF
    echo "✅ 数据已备份到 document_chunks_backup"

    # 创建新的向量列
    echo ""
    echo "🔧 步骤 2: 添加新的 vector 列..."
    psql -U $DB_USER $DB_NAME <<EOF
-- 添加新的 vector 列
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_vec vector(768);
EOF
    echo "✅ 新列 embedding_vec 已创建"

    # 迁移数据
    echo ""
    echo "🔄 步骤 3: 迁移数据 (TEXT → vector)..."
    psql -U $DB_USER $DB_NAME <<EOF
-- 更新数据: 将 TEXT 格式的向量转换为 vector 类型
-- PostgreSQL 数组格式: {1.0,2.0,3.0}
UPDATE document_chunks
SET embedding_vec = embedding::vector
WHERE embedding IS NOT NULL;
EOF
    echo "✅ 数据迁移完成"

    # 删除旧列，重命名新列
    echo ""
    echo "🔧 步骤 4: 替换旧列..."
    psql -U $DB_USER $DB_NAME <<EOF
-- 删除旧的 TEXT 列
ALTER TABLE document_chunks DROP COLUMN embedding;

-- 重命名新列
ALTER TABLE document_chunks RENAME COLUMN embedding_vec TO embedding;
EOF
    echo "✅ 列替换完成"

    # 创建向量索引
    echo ""
    echo "🚀 步骤 5: 创建向量索引 (IVFFlat)..."
    psql -U $DB_USER $DB_NAME <<EOF
-- 创建 IVFFlat 索引 (适用于中等规模数据)
-- lists 参数: sqrt(行数) 是一个好的起点
CREATE INDEX IF NOT EXISTS idx_embedding_cosine ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 10);

-- 分析表以更新统计信息
ANALYZE document_chunks;
EOF
    echo "✅ 向量索引已创建"

else
    echo "✅ embedding 列已经是 vector 类型，无需迁移"
fi

# 验证迁移结果
echo ""
echo "🔍 验证迁移结果..."
echo "========================================="

psql -U $DB_USER $DB_NAME <<EOF
-- 检查表结构
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'document_chunks'
    AND column_name IN ('id', 'doc_id', 'content', 'embedding')
ORDER BY ordinal_position;

-- 统计数据
SELECT
    COUNT(*) as total_chunks,
    COUNT(embedding) as chunks_with_embedding,
    ROUND(100.0 * COUNT(embedding) / NULLIF(COUNT(*), 0), 2) as embedding_coverage_percent
FROM document_chunks;

-- 检查索引
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'document_chunks'
    AND indexname LIKE '%embedding%';
EOF

echo ""
echo "========================================="
echo "✅ 迁移完成！"
echo "========================================="
echo ""
echo "📊 性能提升预期:"
echo "  - 向量检索速度: 10-100x 提升 (取决于数据规模)"
echo "  - 内存使用: 优化 50%+"
echo "  - 原生向量运算: ✅"
echo ""
echo "💡 提示:"
echo "  - 备份表: document_chunks_backup (可手动删除)"
echo "  - 向量索引: idx_embedding_cosine (余弦相似度)"
echo "  - 索引类型: IVFFlat (平衡性能和精度)"
echo ""
