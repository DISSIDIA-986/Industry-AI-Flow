#!/bin/bash
set -e

echo "🚀 开始设置本地环境..."

# 1. 检查系统
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠️  非macOS系统，性能可能不同"
fi

if [[ "$(uname -m)" != "arm64" ]]; then
    echo "⚠️  非Apple Silicon，性能可能不同"
fi

# 2. 检查内存
TOTAL_MEM_GB=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)}')
if [[ $TOTAL_MEM_GB -lt 16 ]]; then
    echo "❌ 内存不足: ${TOTAL_MEM_GB}GB < 16GB"
    exit 1
fi

# 3. 检查并安装依赖
echo "🔍 检查现有安装..."

# 检查PostgreSQL（灵活检测：brew或直接命令）
if command -v psql >/dev/null 2>&1; then
    echo "✅ PostgreSQL已安装 ($(psql --version | head -1))"
else
    echo "⚠️  PostgreSQL未安装，建议运行: brew install postgresql"
    exit 1
fi

# 检查Redis（灵活检测：brew或直接命令）
if command -v redis-cli >/dev/null 2>&1; then
    echo "✅ Redis已安装 ($(redis-cli --version))"
else
    echo "⚠️  Redis未安装，建议运行: brew install redis"
    exit 1
fi

# 检查Ollama
if command -v ollama >/dev/null 2>&1; then
    echo "✅ Ollama已安装"
else
    echo "❌ 未安装Ollama，建议运行: brew install ollama"
    exit 1
fi

# 4. 检查服务状态
echo "▶️  检查服务状态..."

# 检查PostgreSQL是否可连接
if psql -l >/dev/null 2>&1; then
    echo "✅ PostgreSQL服务 - 可连接"
else
    echo "⚠️  PostgreSQL服务未运行，尝试启动..."
    if command -v brew >/dev/null 2>&1; then
        brew services start postgresql 2>/dev/null || echo "   请手动启动PostgreSQL服务"
        sleep 2
    else
        echo "   请手动启动PostgreSQL服务"
    fi
fi

# 检查Redis是否可连接
if redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis服务 - 可连接"
else
    echo "⚠️  Redis服务未运行，尝试启动..."
    if command -v brew >/dev/null 2>&1; then
        brew services start redis 2>/dev/null || echo "   请手动启动Redis服务"
        sleep 2
    else
        echo "   请手动启动Redis服务"
    fi
fi

# 5. 初始化数据库
echo "🗄️  初始化数据库..."

# 检查数据库是否存在
if psql -lqt | cut -d \| -f 1 | grep -qw ai_workflow; then
    echo "✅ 数据库ai_workflow已存在"
else
    echo "创建数据库ai_workflow..."
    createdb ai_workflow
fi

# 启用pgvector扩展
echo "启用pgvector扩展..."
psql ai_workflow -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null

# 执行初始化SQL
if [ -f "infra/init.sql" ]; then
    echo "执行初始化SQL..."
    psql ai_workflow -f infra/init.sql
fi

# 6. 检查并下载模型
echo "📥 检查Ollama模型..."
if ollama list | grep -q "qwen2.5:7b"; then
    echo "✅ 模型qwen2.5:7b已下载"
else
    echo "下载Qwen2.5-7B（约5GB，需5-10分钟）..."
    ollama pull qwen2.5:7b
fi

# 7. 安装Python依赖
echo "🐍 安装Python依赖..."
pip install -q -r backend/requirements.txt

# 8. 创建.env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ 创建.env文件"
fi

echo ""
echo "✅ 环境搭建完成!"
echo ""
echo "验证命令:"
echo "  brew services list                 # 查看服务状态"
echo "  ollama list                        # 应显示qwen2.5:7b"
echo "  psql ai_workflow -c 'SELECT 1;'    # 应返回1"
echo "  redis-cli ping                     # 应返回PONG"
echo ""
echo "资源使用:"
echo "  本地服务模式: 节省约2-3GB内存（相比Docker）"
echo ""
echo "下一步:"
echo "  cd backend && python main.py       # 启动API服务"
