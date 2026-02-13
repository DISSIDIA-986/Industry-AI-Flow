#!/bin/bash

# ==========================================
# Industry AI Flow - 监控脚本
# ==========================================
# 实时监控系统健康状态
# ==========================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 清屏并显示标题
clear
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Industry AI Flow - 系统监控${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ==========================================
# 函数定义
# ==========================================

# 检查服务状态
check_service() {
    if pgrep -f "$1" > /dev/null; then
        echo -e "${GREEN}✓${NC} $2 运行中"
        return 0
    else
        echo -e "${RED}✗${NC} $2 未运行"
        return 1
    fi
}

# 检查端口
check_port() {
    if lsof -i :$1 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} 端口 $1 已占用"
        return 0
    else
        echo -e "${RED}✗${NC} 端口 $1 未占用"
        return 1
    fi
}

# 检查HTTP端点
check_http() {
    if curl -f -s "$1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $2 响应正常"
        return 0
    else
        echo -e "${RED}✗${NC} $2 响应异常"
        return 1
    fi
}

# 显示内存使用
show_memory() {
    local free_mem=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
    local active_mem=$(vm_stat | grep "Pages active" | awk '{print $3}' | sed 's/\.//')
    local wired_mem=$(vm_stat | grep "Pages wired" | awk '{print $3}' | sed 's/\.//')
    local inactive_mem=$(vm_stat | grep "Pages inactive" | awk '{print $3}' | sed 's/\.//')
    
    local total_mem=$((free_mem + active_mem + wired_mem + inactive_mem))
    local used_mem=$((active_mem + wired_mem))
    
    local page_size=4096
    local total_gb=$((total_mem * page_size / 1024 / 1024 / 1024))
    local used_gb=$((used_mem * page_size / 1024 / 1024 / 1024))
    local free_gb=$((free_mem * page_size / 1024 / 1024 / 1024))
    
    echo "内存使用: ${used_gb}GB / ${total_gb}GB (可用: ${free_gb}GB)"
}

# 显示CPU使用
show_cpu() {
    local cpu_usage=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
    echo "CPU使用: ${cpu_usage}%"
}

# ==========================================
# 监控循环
# ==========================================

while true; do
    clear
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Industry AI Flow - 系统监控${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "📅 $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # 系统资源
    echo -e "${YELLOW}=== 系统资源 ===${NC}"
    show_memory
    show_cpu
    echo ""
    
    # 服务状态
    echo -e "${YELLOW}=== 服务状态 ===${NC}"
    check_service "uvicorn backend.main:app" "后端服务"
    check_port 8000
    echo ""
    
    # 数据库状态
    echo -e "${YELLOW}=== 数据库状态 ===${NC}"
    if pgrep postgres > /dev/null; then
        echo -e "${GREEN}✓${NC} PostgreSQL 运行中"
    else
        echo -e "${RED}✗${NC} PostgreSQL 未运行"
    fi
    check_port 5432
    echo ""
    
    # Ollama状态
    echo -e "${YELLOW}=== Ollama状态 ===${NC}"
    if pgrep ollama > /dev/null; then
        echo -e "${GREEN}✓${NC} Ollama 运行中"
    else
        echo -e "${RED}✗${NC} Ollama 未运行"
    fi
    check_http "http://localhost:11434/api/tags" "Ollama API"
    echo ""
    
    # 应用健康检查
    echo -e "${YELLOW}=== 应用健康检查 ===${NC}"
    check_http "http://localhost:8000/api/intent/health" "应用健康端点"
    check_http "http://localhost:8000/docs" "API文档"
    echo ""
    
    # 最近日志
    echo -e "${YELLOW}=== 最近日志 (最后5行) ===${NC}"
    if [ -f "logs/application.log" ]; then
        tail -5 logs/application.log
    else
        echo "日志文件不存在"
    fi
    echo ""
    
    echo -e "${BLUE}========================================${NC}"
    echo "按 Ctrl+C 退出监控"
    echo "刷新间隔: 5秒"
    
    sleep 5
done