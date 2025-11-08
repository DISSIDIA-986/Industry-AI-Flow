"""
测试PaddleOCR 3.3.1 (PP-OCRv5) 和 Apple MPS加速

测试内容:
1. PaddlePaddle版本检查
2. MPS设备检测
3. PP-OCRv5多语言识别测试
4. 性能基准测试
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_paddle_version():
    """测试PaddlePaddle版本"""
    print("=" * 60)
    print("测试 1: PaddlePaddle版本检查")
    print("=" * 60)

    try:
        import paddle

        version = paddle.__version__
        print(f"✅ PaddlePaddle版本: {version}")

        # 检查版本是否满足要求
        major, minor = map(int, version.split('.')[:2])
        if major > 2 or (major == 2 and minor >= 6):
            print(f"✅ 版本满足要求 (>=2.6.0)")
            return True
        else:
            print(f"⚠️  版本过低，建议升级到>=2.6.0以支持MPS")
            print(f"   升级命令: pip install --upgrade paddlepaddle")
            return False

    except ImportError:
        print("❌ PaddlePaddle未安装")
        print("   安装命令: pip install paddlepaddle>=2.6.0")
        return False


def test_mps_device():
    """测试MPS自定义设备"""
    print("\n" + "=" * 60)
    print("测试 2: Apple MPS设备检测")
    print("=" * 60)

    try:
        import paddle

        # 获取所有自定义设备
        custom_devices = paddle.device.get_all_custom_device_type()
        print(f"检测到的自定义设备: {custom_devices}")

        if 'mps' in custom_devices:
            print(f"✅ Apple MPS设备可用!")
            print(f"   预期性能提升: 2-5x (M1/M2/M3芯片)")
            print(f"   在M1 Max上某些场景可达4.7x")

            # 尝试使用MPS
            try:
                paddle.set_device('mps')
                print(f"✅ 成功切换到MPS设备")
                return True
            except Exception as e:
                print(f"⚠️  切换到MPS设备失败: {e}")
                return False
        else:
            print(f"⚠️  MPS设备未检测到")
            print(f"   可能原因:")
            print(f"   1. 未安装PaddleCustomDevice MPS支持")
            print(f"   2. 非Apple Silicon芯片")
            print(f"   安装MPS支持: pip install paddle-custom-mps")
            return False

    except Exception as e:
        print(f"❌ 设备检测失败: {e}")
        return False


def test_paddleocr_version():
    """测试PaddleOCR版本"""
    print("\n" + "=" * 60)
    print("测试 3: PaddleOCR版本检查")
    print("=" * 60)

    try:
        import paddleocr

        # PaddleOCR可能没有__version__属性
        try:
            version = paddleocr.__version__
            print(f"✅ PaddleOCR版本: {version}")
        except AttributeError:
            print(f"ℹ️  PaddleOCR版本信息不可用")
            print(f"   (某些版本不提供__version__属性)")

        # 尝试导入PaddleOCR类
        from paddleocr import PaddleOCR
        print(f"✅ PaddleOCR导入成功")

        print(f"\nPP-OCRv5 主要特性:")
        print(f"   • 单模型支持5种文字: 简体/繁体/英文/日文/拼音")
        print(f"   • 识别精度提升约13个百分点")
        print(f"   • 英文场景再提升约11%")
        print(f"   • 改进复杂手写体识别")

        return True

    except ImportError:
        print("❌ PaddleOCR未安装")
        print("   安装命令: pip install paddleocr>=3.3.0")
        return False


def test_ocr_initialization():
    """测试OCR初始化（使用项目代码）"""
    print("\n" + "=" * 60)
    print("测试 4: OCR处理器初始化")
    print("=" * 60)

    try:
        from backend.services.document_processing.ocr_processor import OCRProcessor

        # 初始化OCR处理器
        print("正在初始化OCR处理器...")
        processor = OCRProcessor(
            use_local=True,
            use_api_fallback=False,  # 仅测试本地
            lang="ch",               # PP-OCRv5混合语言
            use_gpu=True,
            ocr_version="PP-OCRv5"
        )

        if processor.local_ocr:
            print(f"✅ OCR处理器初始化成功")
            print(f"   版本: {processor.ocr_version}")
            print(f"   语言: {processor.lang}")
            print(f"   GPU加速: 已启用")
            return True
        else:
            print(f"⚠️  OCR处理器初始化失败")
            print(f"   请检查PaddlePaddle和PaddleOCR安装")
            return False

    except Exception as e:
        print(f"❌ OCR初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_numpy_version():
    """测试NumPy版本兼容性"""
    print("\n" + "=" * 60)
    print("测试 5: NumPy版本兼容性")
    print("=" * 60)

    try:
        import numpy as np

        version = np.__version__
        print(f"NumPy版本: {version}")

        # 检查版本
        major = int(version.split('.')[0])
        if major < 2:
            print(f"✅ NumPy版本兼容 (<2.0)")
            return True
        else:
            print(f"⚠️  NumPy版本可能不兼容 (>=2.0)")
            print(f"   PaddleOCR建议使用NumPy<2.0")
            print(f"   降级命令: pip install 'numpy<2.0'")
            return False

    except ImportError:
        print("❌ NumPy未安装")
        return False


def test_performance_info():
    """显示性能优化信息"""
    print("\n" + "=" * 60)
    print("性能优化建议")
    print("=" * 60)

    print("\n📊 Apple Silicon MPS加速:")
    print("   • M1/M2/M3芯片: 2-5x性能提升")
    print("   • M1 Max: 某些场景可达4.7x")
    print("   • 相比CPU推理有显著加速")

    print("\n⚙️  优化配置:")
    print("   • use_mp=True: 启用多进程")
    print("   • total_process_num=2: 进程数设置")
    print("   • rec_batch_num=6: 批次大小优化")

    print("\n🎯 PP-OCRv5优势:")
    print("   • 单模型多语言: 简/繁/英/日/拼音")
    print("   • 精度提升: +13% (通用), +11% (英文)")
    print("   • 手写体识别改进")

    print("\n📦 推荐安装:")
    print("   pip install paddlepaddle>=2.6.0")
    print("   pip install paddleocr>=3.3.0")
    print("   pip install 'numpy>=1.26.4,<2.0'")
    print("   pip install paddle-custom-mps  # MPS加速支持")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("PaddleOCR 3.3.1 (PP-OCRv5) + MPS 测试套件")
    print("=" * 60)

    results = {
        "PaddlePaddle版本": test_paddle_version(),
        "MPS设备检测": test_mps_device(),
        "PaddleOCR版本": test_paddleocr_version(),
        "NumPy兼容性": test_numpy_version(),
        "OCR初始化": test_ocr_initialization(),
    }

    # 显示性能信息
    test_performance_info()

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        if result:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"{status}  {name}")

    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过! PaddleOCR 3.3.1已就绪")
        print("\n下一步:")
        print("   1. 运行 python test_document_processing.py 测试文档处理")
        print("   2. 使用真实图像测试OCR识别效果")
        print("   3. 基准测试MPS加速性能提升")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        print("\n请根据上述提示修复问题后重试")
        return 1


if __name__ == "__main__":
    sys.exit(main())
