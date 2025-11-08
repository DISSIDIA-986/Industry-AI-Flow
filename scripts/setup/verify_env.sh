#!/bin/bash

echo "🔍 验证环境..."

# 检查PostgreSQL服务
if brew services list | grep "postgresql" | grep -q "started"; then
    echo "✅ PostgreSQL服务 - 运行中（brew services）"
else
    echo "❌ PostgreSQL服务 - 未运行"
    echo "   运行: brew services start postgresql"
    exit 1
fi

# 检查PostgreSQL连接
if psql ai_workflow -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ PostgreSQL连接 - 成功"
else
    echo "❌ PostgreSQL连接 - 失败"
    exit 1
fi

# 检查pgvector
if psql ai_workflow -c "SELECT * FROM pg_extension WHERE extname='vector';" 2>/dev/null | grep -q "vector"; then
    echo "✅ pgvector扩展 - 已启用"
else
    echo "❌ pgvector扩展 - 未启用"
    echo "   运行: psql ai_workflow -c 'CREATE EXTENSION vector;'"
    exit 1
fi

# 检查Redis服务
if brew services list | grep "redis" | grep -q "started"; then
    echo "✅ Redis服务 - 运行中（brew services）"
else
    echo "❌ Redis服务 - 未运行"
    echo "   运行: brew services start redis"
    exit 1
fi

# 检查Redis连接
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "✅ Redis连接 - 成功"
else
    echo "❌ Redis连接 - 失败"
    exit 1
fi

# 检查Ollama
if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
    echo "✅ Ollama - 模型qwen2.5:7b已下载"
else
    echo "❌ Ollama - 模型未下载"
    echo "   运行: ollama pull qwen2.5:7b"
    exit 1
fi

# 检查Python包
if python -c "import fastapi, sentence_transformers, psycopg2, pgvector" 2>/dev/null; then
    echo "✅ Python依赖 - 已安装"
else
    echo "❌ Python依赖 - 未安装"
    echo "   运行: pip install -r backend/requirements.txt"
    exit 1
fi

echo ""
echo "✅ 所有验收通过!"
echo ""
echo "资源使用情况:"
echo "  本地服务模式: 比Docker节省约2-3GB内存"
