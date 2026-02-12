#!/bin/bash
# 带兼容性检查的自动安装脚本
# 解决Python版本不兼容导致的安装失败问题

set -e

echo "🔍 开始环境兼容性检查和自动安装..."
LOCK_FILE="requirements/lock/py313-capstone.txt"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Python版本
check_python_version() {
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    log_info "检测到Python版本: $PYTHON_VERSION"

    # 版本兼容性检查
    if [ "$PYTHON_MAJOR" -lt "3" ] || ([ "$PYTHON_MAJOR" -eq "3" ] && [ "$PYTHON_MINOR" -lt "8" ]); then
        log_error "Python版本过低: $PYTHON_VERSION < 3.8"
        log_info "建议升级到Python 3.8-3.12版本"
        exit 1
    fi

    if [ "$PYTHON_MAJOR" -gt "3" ] || ([ "$PYTHON_MAJOR" -eq "3" ] && [ "$PYTHON_MINOR" -gt "13" ]); then
        log_error "Python版本过高: $PYTHON_VERSION > 3.13"
        log_info "建议使用Python 3.8-3.12版本"
        exit 1
    fi

    log_success "Python版本兼容: $PYTHON_VERSION"
    return 0
}

# 检查并创建虚拟环境
setup_virtual_environment() {
    if [ -d "venv" ]; then
        log_info "虚拟环境已存在，激活中..."
        source venv/bin/activate
        log_success "虚拟环境已激活"
    else
        log_info "创建Python虚拟环境..."
        python3 -m venv venv
        source venv/bin/activate
        log_success "虚拟环境创建并激活成功"
    fi
}

# 升级pip
upgrade_pip() {
    log_info "升级pip到最新版本..."
    pip install --upgrade pip setuptools wheel
    log_success "pip升级完成"
}

# 安装核心依赖
install_core_dependencies() {
    log_info "安装核心依赖..."

    # 基础依赖
    pip install pandas==1.5.3 numpy==1.24.3 scikit-learn==1.3.0

    # 测试依赖
    pip install pytest==7.4.0 pytest-asyncio==0.21.0

    log_success "核心依赖安装完成"
}

# 根据Python版本安装特定依赖
install_version_specific_dependencies() {
    local py_version=$1
    local py_major=$(echo $py_version | cut -d. -f1)
    local py_minor=$(echo $py_version | cut -d. -f2)

    log_info "根据Python $py_version 安装特定依赖..."

    if [ "$py_major" -eq "3" ] && [ "$py_minor" -eq "13" ]; then
        log_warning "Python 3.13 特殊处理模式"
        log_info "安装兼容Python 3.13的版本..."

        # Python 3.13 兼容版本
        log_info "安装PaddlePaddle和PaddleOCR..."
        pip install paddlepaddle==2.6.1 paddleocr==2.7.0 || {
            log_warning "PaddleOCR安装失败，尝试其他版本..."
            pip install paddlepaddle==2.5.2 paddleocr==2.7.0
        }

        log_info "Python 3.13环境下，跳过部分不兼容的AI库..."
        log_warning "langchain和sentence-transformers在Python 3.13下可能不兼容"

        # 尝试安装兼容版本
        pip install torch==2.1.0 || log_warning "PyTorch安装失败，某些功能可能受限"

    elif [ "$py_major" -eq "3" ] && [ "$py_minor" -eq "12" ]; then
        log_info "Python 3.12 稳定模式"

        # Python 3.12 兼容版本
        pip install "paddlepaddle==2.4.2" "paddleocr==2.6.1"
        pip install "torch==2.0.1" "torchvision==0.15.2"
        pip install "langchain==0.1.0" "langchain-core==0.1.0" "langchain-community==0.0.1"
        pip install "sentence-transformers==2.2.2"
        pip install "transformers==4.21.0"

    elif [ "$py_major" -eq "3" ] && ([ "$py_minor" -ge "8" ] && [ "$py_minor" -le "11" ]); then
        log_info "Python $py_version 推荐兼容模式"

        # Python 3.8-3.11 推荐版本
        pip install "paddlepaddle==2.4.2" "paddleocr==2.6.1"
        pip install "torch==2.0.1" "torchvision==0.15.2"
        pip install "langchain==0.1.0" "langchain-core==0.1.0" "langchain-community==0.0.1"
        pip install "sentence-transformers==2.2.2"
        pip install "transformers==4.21.0"
        pip install "einops==0.7.0"

    else
        log_error "不支持的Python版本: $py_version"
        exit 1
    fi

    # 安装通用依赖
    pip install "pillow==10.0.1" "requests==2.31.0" "opencv-python==4.8.0.76"

    log_success "版本特定依赖安装完成"
}

# 验证安装
verify_installation() {
    log_info "验证关键包安装状态..."

    # 创建验证脚本
    cat > verify_installation.py << 'EOF'
#!/usr/bin/env python3
import sys

def check_import(package_name, import_name=None):
    try:
        if import_name is None:
            import_name = package_name.replace('-', '_')
        __import__(import_name)
        print(f"✅ {package_name}: 已安装")
        return True
    except ImportError as e:
        print(f"❌ {package_name}: 未安装 - {e}")
        return False

# 检查关键包
packages = [
    ('pandas', 'pandas'),
    ('numpy', 'numpy'),
    ('scikit-learn', 'sklearn'),
    ('paddleocr', 'paddleocr'),
    ('langchain', 'langchain'),
    ('sentence-transformers', 'sentence_transformers'),
    ('torch', 'torch'),
    ('pillow', 'PIL'),
    ('opencv-python', 'cv2')
]

success_count = 0
total_count = len(packages)

print("🔍 包安装验证:")
for package, import_name in packages:
    if check_import(package, import_name):
        success_count += 1

print(f"\n📊 安装成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

if success_count >= total_count * 0.8:  # 80%成功率
    print("🎉 安装验证通过！")
    sys.exit(0)
else:
    print("⚠️ 部分包安装失败，可能影响某些功能")
    sys.exit(1)
EOF

    python verify_installation.py
    rm verify_installation.py
}

# 创建requirements.locked文件
create_locked_requirements() {
    log_info "创建锁定的依赖文件..."

    mkdir -p "$(dirname "$LOCK_FILE")"
    pip freeze > "$LOCK_FILE"
    cp "$LOCK_FILE" requirements.locked.txt
    log_success "已创建 $LOCK_FILE（并同步兼容副本 requirements.locked.txt）"
}

# 生成环境信息
generate_environment_info() {
    log_info "生成环境信息文件..."

    cat > environment_info.json << EOF
{
    "python_version": "$(python3 --version)",
    "pip_version": "$(pip --version)",
    "virtual_environment": "$VIRTUAL_ENV",
    "installation_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "platform": "$(uname -s)",
    "architecture": "$(uname -m)"
}
EOF

    log_success "已创建 environment_info.json"
}

# 主安装流程
main() {
    echo "🚀 开始智能环境设置和依赖安装"
    echo "=" * 60

    # 检查Python版本
    check_python_version

    # 设置虚拟环境
    setup_virtual_environment

    # 升级pip
    upgrade_pip

    # 安装核心依赖
    install_core_dependencies

    # 根据Python版本安装特定依赖
    install_version_specific_dependencies $PYTHON_VERSION

    # 验证安装
    verify_installation

    # 创建锁定文件
    create_locked_requirements

    # 生成环境信息
    generate_environment_info

    echo "=" * 60
    log_success "环境设置完成！"
    echo ""
    echo "📋 后续步骤:"
    echo "1. 激活虚拟环境: source venv/bin/activate"
    echo "2. 运行版本检查: python version_manager.py"
    echo "3. 运行测试: python -m pytest tests/"
    echo ""
    echo "📁 生成的文件:"
    echo "- $LOCK_FILE (锁定的依赖列表)"
    echo "- requirements.locked.txt (兼容副本)"
    echo "- environment_info.json (环境信息)"
    echo ""
    log_success "现在可以运行测试了！"
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查上面的错误信息"; exit 1' ERR

# 运行主流程
main "$@"
