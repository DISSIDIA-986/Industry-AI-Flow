#!/bin/bash

# ==========================================
# Industry AI Flow - 一键部署脚本
# ==========================================
# 快速部署脚本，适用于演示和测试环境
# ==========================================

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Industry AI Flow - 一键部署${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 环境检查
echo -e "${BLUE}[1/6]${NC} 检查部署环境..."
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew未安装"
    exit 1
fi
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama未安装"
    exit 1
fi
echo "✅ 环境检查通过"

# 2. 安装依赖
echo -e "${BLUE}[2/6]${NC} 安装系统依赖..."
if ! command -v psql &> /dev/null; then
    brew install postgresql@15
    brew install pgvector
fi
brew services start postgresql@15 2>/dev/null || true
echo "✅ 依赖安装完成"

# 3. 配置数据库
echo -e "${BLUE}[3/6]${NC} 配置数据库..."
createdb ai_workflow 2>/dev/null || echo "数据库已存在"
psql -d ai_workflow -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null
echo "✅ 数据库配置完成"

# 4. 配置Ollama
echo -e "${BLUE}[4/6]${NC} 配置Ollama..."
ollama serve > /dev/null 2>&1 &
sleep 3
ollama pull qwen3.5:9b || echo "模型已存在"
echo "✅ Ollama配置完成"

# 5. 部署应用
echo -e "${BLUE}[5/6]${NC} 部署应用..."
if [ ! -d ".venv_capstone" ]; then
    python3.13 -m venv .venv_capstone || python3 -m venv .venv_capstone
fi
source .venv_capstone/bin/activate
pip install -q -r requirements/lock/py313-capstone.txt 2>/dev/null || pip install -q -r requirements/base.txt
if [ ! -f ".env" ]; then
    cp .env.example .env
fi
python backend/init_database.py 2>/dev/null || true
alembic upgrade head 2>/dev/null || true
echo "✅ 应用部署完成"

# 6. 启动服务
echo -e "${BLUE}[6/6]${NC} 启动服务..."
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs/application.log 2>&1 &
sleep 5
if curl -f http://localhost:8000/api/intent/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功"
else
    echo "❌ 服务启动失败"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📊 访问地址:"
echo "  - 主应用: http://localhost:8000"
echo "  - API文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/api/intent/health"
echo ""
echo "📝 常用命令:"
echo "  - 查看日志: tail -f logs/application.log"
echo "  - 停止服务: pkill -f 'uvicorn backend.main:app'"
echo "  - 运行测试: make test-demo-smoke-gate"
echo ""