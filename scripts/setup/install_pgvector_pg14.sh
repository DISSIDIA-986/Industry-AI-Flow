#!/bin/bash
# 为 PostgreSQL 14 编译安装 pgvector 扩展

set -e  # 遇到错误立即退出

echo "========================================"
echo "📦 PostgreSQL 14 pgvector 扩展安装脚本"
echo "========================================"

# 检查 PostgreSQL 14 是否安装
if ! command -v pg_config &> /dev/null; then
    echo "❌ 错误: 未找到 pg_config 命令"
    echo "   请确保 PostgreSQL 14 已通过 Homebrew 安装"
    echo "   安装命令: brew install postgresql@14"
    exit 1
fi

PG_VERSION=$(pg_config --version | grep -oE '[0-9]+' | head -1)
echo "✅ 检测到 PostgreSQL 版本: $PG_VERSION"

if [ "$PG_VERSION" != "14" ]; then
    echo "⚠️  警告: 当前 PostgreSQL 版本不是 14"
    echo "   pgvector 可能需要针对版本 $PG_VERSION 重新编译"
fi

# 创建临时目录
TMP_DIR="/tmp/pgvector_build"
rm -rf $TMP_DIR
mkdir -p $TMP_DIR
cd $TMP_DIR

echo ""
echo "🔧 步骤 1: 下载 pgvector 源码"
echo "========================================"
git clone https://github.com/pgvector/pgvector.git
cd pgvector

# 切换到稳定版本
echo ""
echo "🔧 步骤 2: 切换到稳定版本 (v0.5.1)"
echo "========================================"
git checkout v0.5.1

# 编译
echo ""
echo "🔧 步骤 3: 编译 pgvector"
echo "========================================"
make clean
make

# 安装
echo ""
echo "🔧 步骤 4: 安装 pgvector"
echo "========================================"
sudo make install

# 验证安装
echo ""
echo "🔍 步骤 5: 验证安装"
echo "========================================"

EXTENSION_DIR=$(pg_config --sharedir)/extension
if [ -f "$EXTENSION_DIR/vector.control" ]; then
    echo "✅ vector.control 文件已安装"
    echo "   路径: $EXTENSION_DIR/vector.control"
else
    echo "❌ 错误: vector.control 文件未找到"
    exit 1
fi

LIB_DIR=$(pg_config --pkglibdir)
if [ -f "$LIB_DIR/vector.so" ]; then
    echo "✅ vector.so 库文件已安装"
    echo "   路径: $LIB_DIR/vector.so"
else
    echo "❌ 错误: vector.so 库文件未找到"
    exit 1
fi

# 清理临时文件
cd /
rm -rf $TMP_DIR

echo ""
echo "========================================"
echo "✅ pgvector 安装完成！"
echo "========================================"
echo ""
echo "📝 下一步:"
echo "  1. 重启 PostgreSQL 服务:"
echo "     brew services restart postgresql@14"
echo ""
echo "  2. 在数据库中启用扩展:"
echo "     psql -U \$(whoami) ai_workflow -c 'CREATE EXTENSION vector;'"
echo ""
echo "  3. 运行数据库迁移脚本:"
echo "     bash scripts/migrate_to_pgvector.sh"
echo ""
