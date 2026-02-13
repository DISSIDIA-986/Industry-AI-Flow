#!/bin/bash

# ==========================================
# Industry AI Flow - 健康检查脚本
# ==========================================
# 检查系统各组件的健康状态
# ==========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 计数器
PASS_COUNT=0
FAIL_COUNT=0
WARNING_COUNT=0

# ==========================================
# 检查函数
# ==========================================

check_pass() {
    echo -e "${GREEN}✓ PASS${NC} $1"
    ((PASS_COUNT++))
}

check_fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    ((FAIL_COUNT++))
}

check_warning() {
    echo -e "${YELLOW}⚠ WARN${NC} $1"
    ((WARNING_COUNT++))
}

# ==========================================
# 系统检查
# ==========================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Industry AI Flow - 健康检查${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 硬件信息
echo -e "${BLUE}=== 硬件信息 ===${NC}"
echo "芯片型号: $(sysctl -n machdep.cpu.brand_string)"
echo "内存大小: $(sysctl -n hw.memsize | awk '{printf "%.2f GB", $1/1024/1024/1024}')"
echo "CPU核心数: $(sysctl -n hw.ncpu)"
echo ""

# 系统依赖
echo -e "${BLUE}=== 系统依赖 ===${NC}"
command -v brew &> /dev/null && check_pass "Homebrew已安装" || check_fail "Homebrew未安装"
command -v git &> /dev/null && check_pass "Git已安装" || check_fail "Git未安装"
command -v python3 &> /dev/null && check_pass "Python已安装" || check_fail "Python未安装"
command -v psql &> /dev/null && check_pass "PostgreSQL已安装" || check_warning "PostgreSQL未安装"
command -v ollama &> /dev/null && check_pass "Ollama已安装" || check_fail "Ollama未安装"
echo ""

# 服务状态
echo -e "${BLUE}=== 服务状态 ===${NC}"
pgrep postgres &> /dev/null && check_pass "PostgreSQL服务运行中" || check_fail "PostgreSQL服务未运行"
pgrep ollama &> /dev/null && check_pass "Ollama服务运行中" || check_fail "Ollama服务未运行"
pgrep -f "uvicorn backend.main:app" &> /dev/null && check_pass "后端服务运行中" || check_warning "后端服务未运行"
pgrep redis &> /dev/null && check_pass "Redis服务运行中" || check_warning "Redis服务未运行 (可选)"
echo ""

# 端口检查
echo -e "${BLUE}=== 端口检查 ===${NC}"
lsof -i :5432 &> /dev/null && check_pass "PostgreSQL端口5432开放" || check_fail "PostgreSQL端口5432未开放"
lsof -i :11434 &> /dev/null && check_pass "Ollama端口11434开放" || check_fail "Ollama端口11434未开放"
lsof -i :8000 &> /dev/null && check_pass "后端服务端口8000开放" || check_warning "后端服务端口8000未开放"
lsof -i :6379 &> /dev/null && check_pass "Redis端口6379开放" || check_warning "Redis端口6379未开放 (可选)"
echo ""

# HTTP端点检查
echo -e "${BLUE}=== HTTP端点检查 ===${NC}"
curl -f -s http://localhost:11434/api/tags &> /dev/null && check_pass "Ollama API响应正常" || check_fail "Ollama API响应异常"
curl -f -s http://localhost:8000/api/intent/health &> /dev/null && check_pass "应用健康端点响应正常" || check_warning "应用健康端点响应异常"
curl -f -s http://localhost:8000/docs &> /dev/null && check_pass "API文档可访问" || check_warning "API文档不可访问"
echo ""

# 数据库检查
echo -e "${BLUE}=== 数据库检查 ===${NC}"
if psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw ai_workflow; then
    check_pass "数据库ai_workflow存在"
    
    # 检查pgvector扩展
    if psql -d ai_workflow -c "SELECT * FROM pg_extension WHERE extname='vector';" -t | grep -q vector; then
        check_pass "pgvector扩展已安装"
    else
        check_fail "pgvector扩展未安装"
    fi
else
    check_fail "数据库ai_workflow不存在"
fi
echo ""

# Ollama模型检查
echo -e "${BLUE}=== Ollama模型检查 ===${NC}"
if ollama list &> /dev/null; then
    echo "已安装的模型:"
    ollama list | grep -q "qwen2.5:7b" && check_pass "qwen2.5:7b模型已安装" || check_warning "qwen2.5:7b模型未安装"
    ollama list | grep -q "llama2" && check_pass "llama2模型已安装" || check_warning "llama2模型未安装"
else
    check_fail "无法获取Ollama模型列表"
fi
echo ""

# 应用配置检查
echo -e "${BLUE}=== 应用配置检查 ===${NC}"
[ -f ".env" ] && check_pass "环境配置文件.env存在" || check_warning "环境配置文件.env不存在"
[ -f ".venv_capstone/bin/activate" ] && check_pass "虚拟环境存在" || check_warning "虚拟环境不存在"
[ -d "logs" ] && check_pass "日志目录存在" || check_warning "日志目录不存在"
echo ""

# ==========================================
# 总结
# ==========================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  检查总结${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ PASS: ${PASS_COUNT}${NC}"
echo -e "${YELLOW}⚠ WARN: ${WARNING_COUNT}${NC}"
echo -e "${RED}✗ FAIL: ${FAIL_COUNT}${NC}"
echo ""

TOTAL_CHECKS=$((PASS_COUNT + WARNING_COUNT + FAIL_COUNT))
TOTAL_SCORE=$((PASS_COUNT * 100 / TOTAL_CHECKS))

echo "总检查项: ${TOTAL_CHECKS}"
echo "健康评分: ${TOTAL_SCORE}%"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ 系统健康状态: 良好${NC}"
    exit 0
elif [ $FAIL_COUNT -le 2 ]; then
    echo -e "${YELLOW}⚠ 系统健康状态: 警告${NC}"
    exit 1
else
    echo -e "${RED}✗ 系统健康状态: 异常${NC}"
    exit 2
fi