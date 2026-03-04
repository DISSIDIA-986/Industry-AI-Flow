#!/bin/bash

# ==========================================
# Industry AI Flow - 自动化部署脚本
# ==========================================
# 适用于 Apple Mac Studio (M1 Max, 32GB RAM)
# 作者: DevOps Team
# 版本: 1.0.0
# ==========================================

set -e  # 遇到错误立即退出
set -u  # 使用未定义变量时报错

# ==========================================
# 颜色和格式定义
# ==========================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==========================================
# 日志函数
# ==========================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ==========================================
# 检查函数
# ==========================================
check_command() {
    if command -v $1 &> /dev/null; then
        log_success "$1 已安装"
        return 0
    else
        log_warning "$1 未安装"
        return 1
    fi
}

check_service() {
    if brew services list | grep -q "$1.*started"; then
        log_success "$1 服务正在运行"
        return 0
    else
        log_warning "$1 服务未运行"
        return 1
    fi
}

# ==========================================
# 环境检查
# ==========================================
check_environment() {
    log_info "检查部署环境..."
    
    echo ""
    log_info "=== 硬件信息 ==="
    log_info "芯片型号: $(sysctl -n machdep.cpu.brand_string)"
    log_info "内存大小: $(sysctl -n hw.memsize | awk '{printf "%.2f GB", $1/1024/1024/1024}')"
    log_info "CPU核心数: $(sysctl -n hw.ncpu)"
    
    echo ""
    log_info "=== 软件环境 ==="
    check_command "brew" || { log_error "Homebrew未安装，请先安装Homebrew"; exit 1; }
    check_command "git" || { log_error "Git未安装，请先安装Git"; exit 1; }
    check_command "python3.13" || log_warning "Python 3.13未安装，将使用默认Python版本"
    check_command "psql" || log_warning "PostgreSQL未安装"
    check_command "ollama" || log_error "Ollama未安装，请先安装Ollama"; exit 1
    
    echo ""
    log_info "=== 服务状态 ==="
    check_service "postgresql"
    check_service "redis" || log_warning "Redis未安装或未运行 (可选)"
    
    # 检查Ollama服务
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        log_success "Ollama服务正在运行"
        ollama list
    else
        log_warning "Ollama服务未运行"
    fi
}

# ==========================================
# 安装系统依赖
# ==========================================
install_dependencies() {
    log_info "安装系统依赖..."
    
    # 安装PostgreSQL
    if ! check_command "psql"; then
        log_info "安装PostgreSQL 15..."
        brew install postgresql@15
        brew install pgvector
        brew services start postgresql@15
        log_success "PostgreSQL安装完成"
    fi
    
    # 安装Redis (可选)
    if ! check_command "redis-cli"; then
        log_info "安装Redis..."
        brew install redis
        brew services start redis
        log_success "Redis安装完成"
    fi
    
    # 安装Python 3.13 (如果未安装)
    if ! check_command "python3.13"; then
        log_info "安装Python 3.13..."
        brew install python@3.13
        log_success "Python 3.13安装完成"
    fi
}

# ==========================================
# 配置数据库
# ==========================================
setup_database() {
    log_info "配置数据库..."
    
    # 启动PostgreSQL服务
    if ! check_service "postgresql"; then
        log_info "启动PostgreSQL服务..."
        brew services start postgresql@15
        sleep 3
    fi
    
    # 创建数据库
    if psql -lqt | cut -d \| -f 1 | grep -qw ai_workflow; then
        log_info "数据库 ai_workflow 已存在"
    else
        log_info "创建数据库 ai_workflow..."
        createdb ai_workflow
        log_success "数据库创建成功"
    fi
    
    # 安装pgvector扩展
    log_info "安装pgvector扩展..."
    psql -d ai_workflow -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1 || {
        log_error "pgvector扩展安装失败，请手动安装"
        exit 1
    }
    log_success "pgvector扩展安装成功"
}

# ==========================================
# 配置Ollama
# ==========================================
setup_ollama() {
    log_info "配置Ollama..."
    
    # 检查Ollama服务
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        log_info "启动Ollama服务..."
        ollama serve > /dev/null 2>&1 &
        sleep 5
    fi
    
    # 下载模型
    log_info "下载Ollama模型..."
    ollama pull qwen3.5:4b || log_warning "qwen3.5:4b下载失败"
    ollama pull llama2:7b || log_warning "llama2:7b下载失败"
    
    log_success "Ollama配置完成"
    ollama list
}

# ==========================================
# 部署应用
# ==========================================
deploy_application() {
    log_info "部署应用..."
    
    # 检查虚拟环境
    if [ -d ".venv_capstone" ]; then
        log_info "虚拟环境已存在，跳过创建"
    else
        log_info "创建虚拟环境..."
        python3.13 -m venv .venv_capstone || python3 -m venv .venv_capstone
        log_success "虚拟环境创建成功"
    fi
    
    # 激活虚拟环境
    source .venv_capstone/bin/activate
    
    # 安装依赖
    log_info "安装Python依赖..."
    if [ -f "requirements/lock/py313-capstone.txt" ]; then
        pip install -r requirements/lock/py313-capstone.txt || {
            log_error "依赖安装失败"
            exit 1
        }
        log_success "依赖安装成功"
    else
        log_warning "未找到依赖文件 requirements/lock/py313-capstone.txt"
        log_info "尝试安装基础依赖..."
        pip install -r requirements/base.txt || log_warning "基础依赖安装失败"
    fi
    
    # 配置环境变量
    if [ -f ".env" ]; then
        log_info "环境配置文件已存在"
    else
        log_info "创建环境配置文件..."
        cp .env.example .env
        log_warning "请编辑 .env 文件配置环境变量"
        read -p "是否立即编辑 .env 文件? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    fi
    
    # 初始化数据库
    log_info "初始化数据库..."
    python backend/init_database.py || log_warning "数据库初始化失败"
    
    # 运行数据库迁移
    log_info "运行数据库迁移..."
    alembic upgrade head || log_warning "数据库迁移失败"
    
    log_success "应用部署完成"
}

# ==========================================
# 启动服务
# ==========================================
start_services() {
    log_info "启动服务..."
    
    # 激活虚拟环境
    source .venv_capstone/bin/activate
    
    # 启动后端服务
    log_info "启动后端服务..."
    nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs/application.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > .backend.pid
    
    # 等待服务启动
    sleep 5
    
    # 健康检查
    if curl -f http://localhost:8000/api/intent/health > /dev/null 2>&1; then
        log_success "后端服务启动成功"
    else
        log_error "后端服务启动失败"
        cat logs/application.log
        exit 1
    fi
    
    log_info "后端服务PID: $BACKEND_PID"
    log_info "访问地址: http://localhost:8000"
    log_info "API文档: http://localhost:8000/docs"
}

# ==========================================
# 运行测试
# ==========================================
run_tests() {
    log_info "运行冒烟测试..."
    
    # 激活虚拟环境
    source .venv_capstone/bin/activate
    
    # 运行CI友好的冒烟测试
    python scripts/testing/run_demo_smoke.py \
        --pretty \
        --train-model-if-missing \
        --skip-postgres-check \
        --skip-ollama-check \
        --dataset-path datasets/unified_construction_projects_enhanced.csv \
        --model-path /tmp/industry_ai_flow_smoke_model.json || {
        log_error "冒烟测试失败"
        exit 1
    }
    
    log_success "冒烟测试通过"
}

# ==========================================
# 主菜单
# ==========================================
show_menu() {
    echo ""
    echo "========================================"
    echo "  Industry AI Flow - 部署菜单"
    echo "========================================"
    echo "1) 完整部署 (推荐)"
    echo "2) 仅检查环境"
    echo "3) 仅安装依赖"
    echo "4) 仅配置数据库"
    echo "5) 仅配置Ollama"
    echo "6) 仅部署应用"
    echo "7) 仅启动服务"
    echo "8) 仅运行测试"
    echo "9) 退出"
    echo "========================================"
}

# ==========================================
# 主流程
# ==========================================
main() {
    echo ""
    log_info "Industry AI Flow - 自动化部署脚本"
    log_info "适用于 Apple Mac Studio (M1 Max, 32GB RAM)"
    echo ""
    
    # 检查是否在项目根目录
    if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ] && [ ! -f "requirements.txt" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 创建日志目录
    mkdir -p logs
    
    # 显示菜单
    while true; do
        show_menu
        read -p "请选择操作 [1-9]: " choice
        
        case $choice in
            1)
                log_info "开始完整部署..."
                check_environment
                install_dependencies
                setup_database
                setup_ollama
                deploy_application
                start_services
                run_tests
                log_success "完整部署完成！"
                ;;
            2)
                check_environment
                ;;
            3)
                install_dependencies
                ;;
            4)
                setup_database
                ;;
            5)
                setup_ollama
                ;;
            6)
                deploy_application
                ;;
            7)
                start_services
                ;;
            8)
                run_tests
                ;;
            9)
                log_info "退出部署脚本"
                exit 0
                ;;
            *)
                log_error "无效选择，请重新输入"
                ;;
        esac
    done
}

# 运行主流程
main "$@"
