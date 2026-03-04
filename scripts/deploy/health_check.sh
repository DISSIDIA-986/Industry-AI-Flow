#!/bin/bash

# ==========================================
# Industry AI Flow - Health Check Script
# ==========================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASS_COUNT=0
FAIL_COUNT=0
WARNING_COUNT=0

# Check functions
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
# Header
# ==========================================
clear
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Industry AI Flow - Health Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ==========================================
# Hardware Info
# ==========================================
echo -e "${BLUE}=== Hardware Info ===${NC}"
if command -v sysctl &> /dev/null; then
    echo "Chip: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Unknown')"
    echo "Memory: $(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.2f GB", $1/1024/1024/1024}')"
    echo "CPU Cores: $(sysctl -n hw.ncpu 2>/dev/null || echo 'Unknown')"
else
    echo "Hardware info not available (non-macOS system)"
fi
echo ""

# ==========================================
# System Dependencies
# ==========================================
echo -e "${BLUE}=== System Dependencies ===${NC}"
command -v brew &> /dev/null && check_pass "Homebrew installed" || check_fail "Homebrew not installed"
command -v git &> /dev/null && check_pass "Git installed" || check_fail "Git not installed"
command -v python3 &> /dev/null && check_pass "Python installed" || check_fail "Python not installed"
command -v psql &> /dev/null && check_pass "PostgreSQL client installed" || check_warning "PostgreSQL client not installed"
command -v ollama &> /dev/null && check_pass "Ollama installed" || check_fail "Ollama not installed"
echo ""

# ==========================================
# Service Status
# ==========================================
echo -e "${BLUE}=== Service Status ===${NC}"
pgrep postgres &> /dev/null && check_pass "PostgreSQL running" || check_fail "PostgreSQL not running"
pgrep ollama &> /dev/null && check_pass "Ollama running" || check_fail "Ollama not running"
pgrep -f "uvicorn backend.main:app" &> /dev/null && check_pass "Backend service running" || check_warning "Backend service not running"
pgrep redis-server &> /dev/null && check_pass "Redis running" || check_warning "Redis not running (optional)"
echo ""

# ==========================================
# Port Checks
# ==========================================
echo -e "${BLUE}=== Port Checks ===${NC}"
lsof -i :5432 &> /dev/null && check_pass "PostgreSQL port 5432 open" || check_fail "PostgreSQL port 5432 not open"
lsof -i :11434 &> /dev/null && check_pass "Ollama port 11434 open" || check_fail "Ollama port 11434 not open"
lsof -i :8000 &> /dev/null && check_pass "Backend port 8000 open" || check_warning "Backend port 8000 not open"
lsof -i :6379 &> /dev/null && check_pass "Redis port 6379 open" || check_warning "Redis port 6379 not open (optional)"
echo ""

# ==========================================
# HTTP Endpoints
# ==========================================
echo -e "${BLUE}=== HTTP Endpoints ===${NC}"
curl -f -s http://localhost:11434/api/tags &> /dev/null && check_pass "Ollama API responding" || check_fail "Ollama API not responding"
curl -f -s http://localhost:8000/api/intent/health &> /dev/null && check_pass "App health endpoint responding" || check_warning "App health endpoint not responding"
curl -f -s http://localhost:8000/docs &> /dev/null && check_pass "API docs accessible" || check_warning "API docs not accessible"
echo ""

# ==========================================
# Database Checks
# ==========================================
echo -e "${BLUE}=== Database Checks ===${NC}"
if psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw ai_workflow; then
    check_pass "Database ai_workflow exists"
    
    if psql -d ai_workflow -c "SELECT * FROM pg_extension WHERE extname='vector';" -t 2>/dev/null | grep -q vector; then
        check_pass "pgvector extension installed"
    else
        check_fail "pgvector extension not installed"
    fi
else
    check_fail "Database ai_workflow does not exist"
fi
echo ""

# ==========================================
# Ollama Models
# ==========================================
echo -e "${BLUE}=== Ollama Models ===${NC}"
if ollama list &> /dev/null; then
    echo "Installed models:"
    ollama list
    ollama list 2>/dev/null | grep -q "qwen3.5:4b" && check_pass "qwen3.5:4b installed" || check_warning "qwen3.5:4b not installed"
else
    check_fail "Cannot get Ollama model list"
fi
echo ""

# ==========================================
# Application Config
# ==========================================
echo -e "${BLUE}=== Application Config ===${NC}"
[ -f ".env" ] && check_pass "Environment config .env exists" || check_warning "Environment config .env does not exist"
[ -f ".venv_capstone/bin/activate" ] && check_pass "Virtual environment exists" || check_warning "Virtual environment does not exist"
[ -d "logs" ] && check_pass "Logs directory exists" || check_warning "Logs directory does not exist"
echo ""

# ==========================================
# Summary
# ==========================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Health Check Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ PASS: ${PASS_COUNT}${NC}"
echo -e "${YELLOW}⚠ WARN: ${WARNING_COUNT}${NC}"
echo -e "${RED}✗ FAIL: ${FAIL_COUNT}${NC}"
echo ""

TOTAL_CHECKS=$((PASS_COUNT + WARNING_COUNT + FAIL_COUNT))
if [ $TOTAL_CHECKS -gt 0 ]; then
    TOTAL_SCORE=$((PASS_COUNT * 100 / TOTAL_CHECKS))
    echo "Total checks: ${TOTAL_CHECKS}"
    echo "Health score: ${TOTAL_SCORE}%"
    echo ""
fi

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ System health: GOOD${NC}"
    exit 0
elif [ $FAIL_COUNT -le 2 ]; then
    echo -e "${YELLOW}⚠ System health: WARNING${NC}"
    exit 1
else
    echo -e "${RED}✗ System health: CRITICAL${NC}"
    exit 2
fi
