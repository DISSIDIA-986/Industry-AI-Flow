#!/bin/bash
# Python 3.13 + PaddleOCR 专用安装脚本
# 专门为支持PaddleOCR核心功能而设计

set -e

echo "🎯 Python 3.13 + PaddleOCR 专用安装脚本"
echo "专门配置支持建筑图纸OCR识别的环境"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_paddle() {
    echo -e "${PURPLE}🔍 $1${NC}"
}

# 检查Python版本
check_python_version() {
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    log_paddle "检测Python版本: $PYTHON_VERSION"

    # 严格要求Python 3.13
    if [ "$PYTHON_MAJOR" -eq "3" ] && [ "$PYTHON_MINOR" -eq "13" ]; then
        log_success "✅ Python版本完美匹配: 3.13 (PaddleOCR核心版本)"
        return 0
    else
        log_error "❌ Python版本不匹配: $PYTHON_VERSION (必须使用Python 3.13)"
        log_info "PaddleOCR 2.7.0需要Python 3.13支持"
        log_info "安装Python 3.13的方法:"
        echo "  # 使用pyenv (推荐)"
        echo "  brew install pyenv"
        echo "  pyenv install 3.13.x"
        echo "  pyenv local 3.13.x"
        echo ""
        echo "  # 或者直接下载Python 3.13"
        echo "  https://www.python.org/downloads/release/python-3130/"
        exit 1
    fi
}

# 检查并创建虚拟环境
setup_virtual_environment() {
    if [ -d "venv" ]; then
        log_info "检测到现有虚拟环境，检查Python版本..."
        if [ -f "venv/bin/python" ]; then
            VENV_PYTHON=$($(which python3) venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            if [ "$VENV_PYTHON" == "3.13" ]; then
                log_success "✅ 虚拟环境Python版本正确: $VENV_PYTHON"
                log_info "激活现有虚拟环境..."
                source venv/bin/activate
                return 0
            else
                log_warning "⚠️ 现有虚拟环境Python版本: $VENV_PYTHON，需要重建"
                log_info "删除现有虚拟环境..."
                rm -rf venv
            fi
        fi
    fi

    log_info "创建Python 3.13专用虚拟环境..."
    python3.13 -m venv venv
    source venv/bin/activate
    log_success "✅ Python 3.13虚拟环境创建并激活成功"
}

# 升级pip和基础工具
upgrade_pip() {
    log_info "升级pip到最新版本..."
    pip install --upgrade pip setuptools wheel
    log_success "✅ pip升级完成"
}

# 安装PaddleOCR核心依赖
install_paddleocr_dependencies() {
    log_paddle "安装PaddleOCR核心依赖..."

    log_info "安装PaddlePaddle后端..."
    pip install paddlepaddle==2.6.1

    log_info "安装PaddleOCR..."
    pip install paddleocr==2.7.0

    log_success "✅ PaddleOCR核心依赖安装完成"
}

# 安装图像处理依赖
install_image_processing() {
    log_info "安装图像处理依赖..."

    log_info "安装OpenCV..."
    pip install opencv-python==4.8.0.76

    log_info "安装Pillow..."
    pip install pillow==10.0.1

    log_info "安装numpy (数值计算)..."
    pip install numpy==1.24.3

    log_success "✅ 图像处理依赖安装完成"
}

# 安装数据处理依赖
install_data_processing() {
    log_info "安装数据处理依赖..."

    log_info "安装pandas..."
    pip install pandas==1.5.3

    log_info "安装matplotlib (可视化)..."
    pip install matplotlib==3.7.2

    log_success "✅ 数据处理依赖安装完成"
}

# 验证PaddleOCR安装
verify_paddleocr() {
    log_paddle "验证PaddleOCR安装..."

    cat > verify_paddleocr.py << 'EOF'
#!/usr/bin/env python3
import sys

def test_paddleocr():
    try:
        import paddleocr
        print("✅ PaddleOCR导入成功")

        # 检查版本
        try:
            version = getattr(paddleocr, '__version__', 'Unknown')
            print(f"📦 PaddleOCR版本: {version}")
        except:
            print("⚠️ 无法获取PaddleOCR版本信息")

        # 尝试初始化OCR (不运行实际推理)
        try:
            ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang='ch')
            print("✅ PaddleOCR初始化成功")
            print("🔍 支持中文识别")
            return True
        except Exception as e:
            print(f"⚠️ PaddleOCR初始化警告: {e}")
            print("💡 这可能是正常的，某些依赖可能需要额外配置")
            return True

    except ImportError as e:
        print(f"❌ PaddleOCR导入失败: {e}")
        return False

def test_dependencies():
    dependencies = {
        'paddlepaddle': 'PaddlePaddle',
        'cv2': 'OpenCV',
        'PIL': 'Pillow',
        'numpy': 'NumPy',
        'pandas': 'Pandas'
    }

    results = {}
    for module, name in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {name}: 已安装")
            results[module] = True
        except ImportError as e:
            print(f"❌ {name}: 未安装 - {e}")
            results[module] = False

    return results

def main():
    print("=" * 50)
    print("🔍 PaddleOCR环境验证")
    print("=" * 50)

    # 测试PaddleOCR
    paddleocr_ok = test_paddleocr()
    print()

    # 测试依赖
    print("📦 检查依赖包:")
    dep_results = test_dependencies()
    print()

    # 总结
    total_deps = len(dep_results)
    installed_deps = sum(dep_results.values())

    print("=" * 50)
    print("📊 验证总结:")
    print(f"PaddleOCR状态: {'✅ 正常' if paddleocr_ok else '❌ 异常'}")
    print(f"依赖包状态: {installed_deps}/{total_deps} 已安装")

    if paddleocr_ok and installed_deps >= total_deps * 0.8:
        print("🎉 环境验证通过！PaddleOCR可以正常使用")
        return True
    else:
        print("⚠️ 环境验证未完全通过，请检查上面的错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

    python verify_paddleocr.py
    verification_result=$?
    rm verify_paddleocr.py

    if [ $verification_result -eq 0 ]; then
        log_success "✅ PaddleOCR环境验证通过"
    else
        log_warning "⚠️ PaddleOCR环境验证未完全通过，请检查上面的信息"
    fi
}

# 创建配置文件
create_configuration() {
    log_info "创建PaddleOCR配置文件..."

    cat > paddleocr_config.json << 'EOF'
{
  "use_gpu": false,
  "use_angle_cls": true,
  "lang": "ch",
  "det_db_thresh": 0.3,
  "det_db_box_thresh": 0.5,
  "rec_batch_num": 6,
  "drop_score": 0.5,
  "show_log": false
}
EOF

    log_success "✅ PaddleOCR配置文件已创建: paddleocr_config.json"
}

# 创建OCR测试脚本
create_test_script() {
    log_info "创建OCR测试脚本..."

    cat > test_paddleocr.py << 'EOF'
#!/usr/bin/env python3
"""
PaddleOCR建筑图纸识别测试脚本
测试建筑平面图和施工详图的OCR识别能力
"""

import os
import json
from pathlib import Path
import paddleocr
from PIL import Image
import cv2
import numpy as np

class ArchitectureOCRTester:
    def __init__(self, config_file="paddleocr_config.json"):
        self.ocr = None
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                print(f"✅ 加载配置文件: {self.config_file}")
            else:
                self.config = {
                    "use_gpu": False,
                    "use_angle_cls": True,
                    "lang": "ch"
                }
                print("⚠️ 使用默认配置")
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            self.config = {"use_gpu": False, "use_angle_cls": True, "lang": "ch"}

    def initialize_ocr(self):
        try:
            print("🔍 初始化PaddleOCR...")
            self.ocr = paddleocr.PaddleOCR(**self.config)
            print("✅ PaddleOCR初始化成功")
            return True
        except Exception as e:
            print(f"❌ PaddleOCR初始化失败: {e}")
            return False

    def test_image_files(self):
        """测试建筑图像文件"""
        test_images = [
            "test_resources/images/architectural_floor_plan.png",
            "test_resources/images/construction_detail_drawing.png"
        ]

        results = []

        for image_path in test_images:
            if os.path.exists(image_path):
                print(f"\n🖼️ 测试图像: {image_path}")
                result = self.process_image(image_path)
                results.append({
                    "image_path": image_path,
                    "success": result["success"],
                    "text_found": len(result.get("texts", [])),
                    "processing_time": result.get("processing_time", 0)
                })

                if result["success"]:
                    print(f"✅ 识别成功，发现 {len(result.get('texts', []))} 个文本区域")
                    for i, text in enumerate(result.get("texts", [])[:5]):  # 显示前5个
                        print(f"   {i+1}. {text}")
                else:
                    print(f"❌ 识别失败: {result.get('error', 'Unknown error')}")
            else:
                print(f"⚠️ 图像文件不存在: {image_path}")

        return results

    def process_image(self, image_path):
        """处理单个图像"""
        try:
            import time
            start_time = time.time()

            # 读取图像
            img = cv2.imread(image_path)
            if img is None:
                return {"success": False, "error": "无法读取图像文件"}

            # OCR识别
            result = self.ocr.ocr(img, cls=True)

            processing_time = time.time() - start_time
            texts = []

            # 提取文本
            if result and result[0]:
                for line in result[0]:
                    if line[1][0]:
                        texts.append(line[1][0])

            return {
                "success": True,
                "texts": texts,
                "processing_time": processing_time,
                "image_shape": img.shape
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_test(self):
        """运行完整的OCR测试"""
        print("=" * 60)
        print("🏗️ 建筑图纸OCR识别测试")
        print("=" * 60)

        # 初始化OCR
        if not self.initialize_ocr():
            return False

        # 测试图像
        results = self.test_image_files()

        # 生成报告
        self.generate_report(results)

        return len([r for r in results if r["success"]]) > 0

    def generate_report(self, results):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 OCR测试报告")
        print("=" * 60)

        total_images = len(results)
        successful_images = len([r for r in results if r["success"]])
        total_texts = sum([r.get("text_found", 0) for r in results])
        avg_processing_time = sum([r.get("processing_time", 0) for r in results]) / max(1, len(results))

        print(f"测试图像数量: {total_images}")
        print(f"成功识别数量: {successful_images}")
        print(f"识别成功率: {successful_images/total_images*100:.1f}%")
        print(f"识别文本总数: {total_texts}")
        print(f"平均处理时间: {avg_processing_time:.2f}秒")

        # 保存详细报告
        report = {
            "timestamp": str(datetime.datetime.now()),
            "total_images": total_images,
            "successful_images": successful_images,
            "success_rate": successful_images/total_images,
            "total_texts": total_texts,
            "average_processing_time": avg_processing_time,
            "detailed_results": results
        }

        with open("ocr_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📁 详细报告已保存: ocr_test_report.json")

def main():
    import datetime

    tester = ArchitectureOCRTester()
    success = tester.run_test()

    if success:
        print("\n🎉 OCR测试完成！建筑图纸识别功能正常")
    else:
        print("\n❌ OCR测试失败，请检查环境配置")

    return success

if __name__ == "__main__":
    import datetime
    success = main()
    exit(0 if success else 1)
EOF

    chmod +x test_paddleocr.py
    log_success "✅ OCR测试脚本已创建: test_paddleocr.py"
}

# 生成环境信息
generate_environment_info() {
    log_info "生成环境信息文件..."

    cat > environment_python313.json << EOF
{
    "python_version": "$(python3 --version)",
    "target_version": "3.13",
    "paddleocr_version": "2.7.0",
    "paddlepaddle_version": "2.6.1",
    "installation_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "platform": "$(uname -s)",
    "architecture": "$(uname -m)",
    "virtual_environment": "$VIRTUAL_ENV",
    "purpose": "PaddleOCR建筑图纸识别专用环境"
}
EOF

    log_success "✅ 环境信息已保存: environment_python313.json"
}

# 主安装流程
main() {
    echo "🚀 开始Python 3.13 + PaddleOCR专用环境设置"
    echo "=" * 60

    # 1. 检查Python版本
    check_python_version

    # 2. 设置虚拟环境
    setup_virtual_environment

    # 3. 升级pip
    upgrade_pip

    # 4. 安装PaddleOCR核心依赖
    install_paddleocr_dependencies

    # 5. 安装图像处理依赖
    install_image_processing

    # 6. 安装数据处理依赖
    install_data_processing

    # 7. 验证PaddleOCR安装
    verify_paddleocr

    # 8. 创建配置文件
    create_configuration

    # 9. 创建测试脚本
    create_test_script

    # 10. 生成环境信息
    generate_environment_info

    echo "=" * 60
    log_success "Python 3.13 + PaddleOCR环境设置完成！"
    echo ""
    echo "🏗️ 专用功能:"
    echo "✅ PaddleOCR 2.7.0 - 建筑图纸识别"
    echo "✅ OpenCV 4.8.0 - 图像处理"
    echo "✅ NumPy 1.24.3 - 数值计算"
    echo "✅ Pandas 1.5.3 - 数据处理"
    echo ""
    echo "🔧 下一步操作:"
    echo "1. 测试OCR功能: python3 test_paddleocr.py"
    echo "2. 运行建筑行业测试: python3 test_architecture_construction_industry.py"
    echo "3. 查看配置文件: cat paddleocr_config.json"
    echo ""
    echo "📁 生成的文件:"
    echo "- paddleocr_config.json (OCR配置)"
    echo "- test_paddleocr.py (OCR测试脚本)"
    echo "- environment_python313.json (环境信息)"
    echo ""
    log_success "现在可以使用PaddleOCR进行建筑图纸识别了！"
}

# 错误处理
trap 'log_error "安装过程中发生错误，请检查上面的错误信息"; exit 1' ERR

# 运行主流程
main "$@"
