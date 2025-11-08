#!/bin/bash
# 快速测试脚本 - 验证系统完整功能

set -e

echo "========================================"
echo "🚀 LangChain 1.0 RAG 系统快速测试"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  未检测到虚拟环境，正在激活...${NC}"
    source venv/bin/activate
fi

echo -e "${GREEN}✅ 虚拟环境: $VIRTUAL_ENV${NC}"
echo ""

# 步骤 1: 设备检测
echo "========================================"
echo "步骤 1/4: 设备检测"
echo "========================================"
python backend/utils/device_manager.py

echo ""
read -p "按 Enter 继续..."
echo ""

# 步骤 2: 数据库连接测试
echo "========================================"
echo "步骤 2/4: 数据库连接测试"
echo "========================================"

if pg_isready -q; then
    echo -e "${GREEN}✅ PostgreSQL 运行中${NC}"

    DOC_COUNT=$(psql -U $(whoami) ai_workflow -tAc "SELECT COUNT(*) FROM documents;")
    CHUNK_COUNT=$(psql -U $(whoami) ai_workflow -tAc "SELECT COUNT(*) FROM document_chunks;")

    echo "  - 文档总数: $DOC_COUNT"
    echo "  - 文档块总数: $CHUNK_COUNT"

    if [ "$CHUNK_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  数据库中没有文档块${NC}"
        echo "   运行: python scripts/generate_test_embeddings.py"
    fi
else
    echo -e "${RED}❌ PostgreSQL 未运行${NC}"
    echo "   启动: brew services start postgresql@14"
    exit 1
fi

echo ""
read -p "按 Enter 继续..."
echo ""

# 步骤 3: RAG 系统测试
echo "========================================"
echo "步骤 3/4: RAG 系统完整测试"
echo "========================================"
echo "这可能需要几分钟..."
echo ""

python test_complete_rag_system.py

echo ""
read -p "按 Enter 继续..."
echo ""

# 步骤 4: 性能报告
echo "========================================"
echo "步骤 4/4: 性能总结"
echo "========================================"

echo ""
echo "📊 系统配置:"
echo "  - Python: $(python --version 2>&1)"
echo "  - PyTorch: $(python -c 'import torch; print(torch.__version__)')"
echo "  - 设备: $(python -c 'from backend.utils.device_manager import device_manager; print(device_manager.device_name)')"
echo ""

# 检查 pgvector
PGVECTOR_INSTALLED=$(psql -U $(whoami) ai_workflow -tAc "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")

if [ "$PGVECTOR_INSTALLED" = "t" ]; then
    echo -e "${GREEN}✅ pgvector 扩展已启用 - 使用原生向量运算${NC}"
else
    echo -e "${YELLOW}⚠️  pgvector 扩展未启用 - 使用 Python 相似度计算${NC}"
    echo "   性能提升建议: bash scripts/install_pgvector_pg14.sh"
fi

echo ""
echo "========================================"
echo "🎉 测试完成！"
echo "========================================"
echo ""
echo "📝 下一步:"
echo "  1. 查看详细文档: cat SETUP_AND_TESTING_GUIDE.md"
echo "  2. 安装 pgvector (可选): bash scripts/install_pgvector_pg14.sh"
echo "  3. 启动 Web 界面 (需要 Python 3.12): streamlit run streamlit_app.py"
echo ""
