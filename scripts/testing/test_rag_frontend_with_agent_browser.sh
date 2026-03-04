#!/bin/bash
# 使用 agent-browser 测试 RAG 前端页面功能
#
# 前置条件:
# 1. 启动前端服务: cd frontend && npm run dev (端口 3000)
# 2. 启动后端服务: make run (端口 8000)
# 3. 确保 Ollama 运行: ollama serve

set -e

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

echo "=================================="
echo "RAG 前端页面自动化测试"
echo "=================================="
echo "前端 URL: $FRONTEND_URL"
echo "后端 URL: $BACKEND_URL"
echo ""

# 检查服务是否运行
echo "1. 检查服务状态..."
if ! curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
    echo "❌ 前端服务未运行 ($FRONTEND_URL)"
    echo "请先启动: cd frontend && npm run dev"
    exit 1
fi
echo "✅ 前端服务运行中"

if ! curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo "⚠️  后端服务未运行 ($BACKEND_URL)"
    echo "建议启动: make run"
fi

# 测试查询列表
TEST_QUERIES=(
    "建筑项目中常见的成本超支原因有哪些？"
    "什么是风险管理中的风险评分？"
)

echo ""
echo "2. 打开前端页面..."
agent-browser open "$FRONTEND_URL"
agent-browser wait --load networkidle
agent-browser screenshot /tmp/rag_frontend_initial.png
echo "✅ 页面已打开，截图保存到: /tmp/rag_frontend_initial.png"

echo ""
echo "3. 获取页面快照..."
agent-browser snapshot -i --json > /tmp/rag_page_snapshot.json
echo "✅ 页面快照已保存到: /tmp/rag_page_snapshot.json"

echo ""
echo "4. 测试查询功能..."
for i in "${!TEST_QUERIES[@]}"; do
    query="${TEST_QUERIES[$i]}"
    echo ""
    echo "[$((i+1))/${#TEST_QUERIES[@]}] 测试查询: $query"

    # 注意：这里需要根据实际页面元素进行调整
    # 以下是通用测试流程

    # 获取页面快照，找到输入框和按钮
    SNAPSHOT=$(agent-browser snapshot -i --json)

    # 查找输入框（通常会有特定的 class 或 id）
    # 这里需要根据实际页面结构调整选择器

    # 示例：假设页面有输入框 id="query-input" 和提交按钮 id="submit-button"
    # agent-browser fill @QueryInput "$query"
    # agent-browser click @SubmitButton
    # agent-browser wait --load networkidle

    echo "  ⚠️  需要根据实际页面结构调整交互代码"
    echo "  当前快照已保存，请查看 /tmp/rag_page_snapshot.json"
done

echo ""
echo "5. 生成测试报告..."
cat > /tmp/rag_test_summary.md <<EOF
# RAG 前端测试摘要

## 测试环境
- 前端 URL: $FRONTEND_URL
- 后端 URL: $BACKEND_URL
- 测试时间: $(date)

## 测试结果
- ✅ 前端页面加载成功
- ✅ 页面快照已获取
- ⚠️  查询功能需要根据实际页面结构调整

## 生成文件
- 初始截图: /tmp/rag_frontend_initial.png
- 页面快照: /tmp/rag_page_snapshot.json

## 下一步
1. 查看页面快照，确定输入框和按钮的元素引用
2. 更新测试脚本，使用正确的元素引用
3. 运行实际的查询测试
EOF

echo "✅ 测试摘要已保存到: /tmp/rag_test_summary.md"

echo ""
echo "=================================="
echo "测试完成！"
echo "=================================="
echo ""
echo "查看结果:"
echo "  - 截图: open /tmp/rag_frontend_initial.png"
echo "  - 快照: cat /tmp/rag_page_snapshot.json"
echo "  - 摘要: cat /tmp/rag_test_summary.md"
