#!/bin/bash

echo "=== 前端本地测试开始 ==="
echo "时间: $(date)"
echo ""

# 1. 检查开发服务器
echo "1. 检查开发服务器状态..."
if curl -s http://localhost:3000 > /dev/null; then
  echo "✅ 开发服务器运行正常"
else
  echo "❌ 开发服务器未运行"
  exit 1
fi

# 2. 检查后端API
echo "2. 检查后端API状态..."
if curl -s http://localhost:8001/api/v1/health > /dev/null; then
  echo "✅ 后端API运行正常"
  HEALTH_RESPONSE=$(curl -s http://localhost:8001/api/v1/health)
  echo "   状态: $(echo $HEALTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")"
  echo "   内存使用: $(echo $HEALTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['memory_usage_mb'])") MB"
  echo "   版本: $(echo $HEALTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])")"
else
  echo "⚠️  后端API未运行（使用模拟数据）"
fi

# 3. 测试核心页面
echo ""
echo "3. 测试核心页面可访问性..."
pages=("workflow-chat" "documents-integrated" "data-dashboard" "cost-estimation" "api-integration-test" "components-demo")

for page in "${pages[@]}"; do
  echo -n "   测试页面: /$page ... "
  if curl -s "http://localhost:3000/$page" | grep -q "<title>"; then
    TITLE=$(curl -s "http://localhost:3000/$page" | grep -o "<title>[^<]*</title>" | sed 's/<title>//' | sed 's/<\/title>//')
    echo "✅ 可访问 ($TITLE)"
  else
    echo "❌ 访问失败"
  fi
done

# 4. 测试API端点
echo ""
echo "4. 测试关键API端点..."
apis=("health" "workflow/health" "query/health" "cost-estimation/health")

for api in "${apis[@]}"; do
  echo -n "   测试API: /api/v1/$api ... "
  if curl -s "http://localhost:8001/api/v1/$api" --max-time 5 > /dev/null 2>&1; then
    echo "✅ 响应正常"
  else
    echo "⚠️  无响应或超时"
  fi
done

# 5. 检查组件库
echo ""
echo "5. 检查组件库状态..."
COMPONENTS_DIR="/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/src/components"
if [ -d "$COMPONENTS_DIR" ]; then
  COMPONENT_COUNT=$(find "$COMPONENTS_DIR" -name "*.tsx" -o -name "*.ts" | wc -l | tr -d ' ')
  echo "   ✅ 组件库存在，包含 $COMPONENT_COUNT 个组件文件"
  
  # 检查主要组件类别
  CATEGORIES=("forms" "tables" "cards" "modals" "feedback" "files" "charts")
  for category in "${CATEGORIES[@]}"; do
    if [ -f "$COMPONENTS_DIR/$category/index.tsx" ] || [ -d "$COMPONENTS_DIR/$category" ]; then
      echo "      • $category: ✅ 存在"
    else
      echo "      • $category: ⚠️  缺失"
    fi
  done
else
  echo "   ❌ 组件库目录不存在"
fi

# 6. 检查配置文件
echo ""
echo "6. 检查配置文件..."
CONFIG_FILES=("package.json" "tsconfig.json" "tailwind.config.js" "next.config.js")

for config in "${CONFIG_FILES[@]}"; do
  CONFIG_PATH="/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/$config"
  if [ -f "$CONFIG_PATH" ]; then
    echo "   ✅ $config: 存在"
  else
    echo "   ❌ $config: 缺失"
  fi
done

# 7. 检查环境变量
echo ""
echo "7. 检查环境变量配置..."
ENV_FILE="/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/.env.local"
if [ -f "$ENV_FILE" ]; then
  echo "   ✅ .env.local: 存在"
  # 检查关键环境变量
  if grep -q "NEXT_PUBLIC_API_URL" "$ENV_FILE"; then
    echo "      • NEXT_PUBLIC_API_URL: ✅ 已配置"
  else
    echo "      • NEXT_PUBLIC_API_URL: ⚠️  未配置（使用默认值）"
  fi
else
  echo "   ⚠️  .env.local: 不存在（使用默认配置）"
fi

# 8. 总结
echo ""
echo "=== 测试结果总结 ==="
echo ""

# 计算通过率
TOTAL_TESTS=0
PASSED_TESTS=0

# 开发服务器测试
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if curl -s http://localhost:3000 > /dev/null; then
  PASSED_TESTS=$((PASSED_TESTS + 1))
fi

# 后端API测试
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if curl -s http://localhost:8001/api/v1/health > /dev/null; then
  PASSED_TESTS=$((PASSED_TESTS + 1))
fi

# 页面测试（6个页面）
for page in "${pages[@]}"; do
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  if curl -s "http://localhost:3000/$page" | grep -q "<title>"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
  fi
done

# API端点测试（4个端点）
for api in "${apis[@]}"; do
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  if curl -s "http://localhost:8001/api/v1/$api" --max-time 5 > /dev/null 2>&1; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
  fi
done

# 组件库测试
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ -d "$COMPONENTS_DIR" ]; then
  PASSED_TESTS=$((PASSED_TESTS + 1))
fi

# 配置文件测试（4个文件）
for config in "${CONFIG_FILES[@]}"; do
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  CONFIG_PATH="/Users/openclaw/Documents/github.com/Industry-AI-Flow/frontend/$config"
  if [ -f "$CONFIG_PATH" ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
  fi
done

# 环境变量测试
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ -f "$ENV_FILE" ]; then
  PASSED_TESTS=$((PASSED_TESTS + 1))
fi

# 计算通过率
if [ $TOTAL_TESTS -gt 0 ]; then
  PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
else
  PASS_RATE=0
fi

echo "测试总数: $TOTAL_TESTS"
echo "通过测试: $PASSED_TESTS"
echo "失败测试: $((TOTAL_TESTS - PASSED_TESTS))"
echo "通过率: $PASS_RATE%"

echo ""
if [ $PASS_RATE -ge 90 ]; then
  echo "🎉 测试结果: 优秀 (通过率 ≥ 90%)"
  echo "   前端系统状态良好，可以进入下一阶段"
elif [ $PASS_RATE -ge 70 ]; then
  echo "✅ 测试结果: 良好 (通过率 ≥ 70%)"
  echo "   前端系统基本正常，建议修复部分问题"
elif [ $PASS_RATE -ge 50 ]; then
  echo "⚠️  测试结果: 一般 (通过率 ≥ 50%)"
  echo "   前端系统存在问题，需要修复"
else
  echo "❌ 测试结果: 较差 (通过率 < 50%)"
  echo "   前端系统存在严重问题，需要紧急修复"
fi

echo ""
echo "=== 前端本地测试完成 ==="
echo "完成时间: $(date)"