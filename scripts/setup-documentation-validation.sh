#!/bin/bash
# 文档验证系统安装脚本

set -e

echo "🔧 设置文档验证系统..."

# 检查是否在git仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ 错误: 不在Git仓库中"
    exit 1
fi

# 创建.git/hooks目录（如果不存在）
mkdir -p .git/hooks

# 安装pre-commit钩子
echo "📦 安装pre-commit钩子..."
pip install pre-commit

# 创建钩子符号链接
HOOKS_DIR=".github/hooks"
GIT_HOOKS_DIR=".git/hooks"

for hook in pre-commit prevent-temp-docs.sh; do
    if [ -f "$HOOKS_DIR/$hook" ]; then
        echo "🔗 链接钩子: $hook"
        ln -sf "../../$HOOKS_DIR/$hook" "$GIT_HOOKS_DIR/"
        chmod +x "$GIT_HOOKS_DIR/$hook"
    else
        echo "⚠️ 警告: 钩子文件不存在: $HOOKS_DIR/$hook"
    fi
done

# 安装Python验证脚本
if [ -f ".github/hooks/validate-docs.py" ]; then
    echo "🐍 设置Python验证脚本..."
    chmod +x .github/hooks/validate-docs.py
else
    echo "⚠️ 警告: Python验证脚本不存在"
fi

# 安装pre-commit配置
echo "⚙️ 安装pre-commit配置..."
pre-commit install

# 运行初始验证
echo "🧪 运行初始验证..."
pre-commit run --all-files || {
    echo "⚠️ 一些验证失败，请检查并修复问题"
    echo "运行 'pre-commit run --all-files' 查看详细信息"
}

echo ""
echo "✅ 文档验证系统安装完成!"
echo ""
echo "📋 使用说明:"
echo "1. 提交前会自动运行文档验证"
echo "2. 手动运行所有检查: pre-commit run --all-files"
echo "3. 更新钩子: pre-commit install --overwrite"
echo "4. 查看配置: cat .pre-commit-config.yaml"
echo ""
echo "📚 文档规范: .github/DOCUMENTATION_STANDARDS.md"