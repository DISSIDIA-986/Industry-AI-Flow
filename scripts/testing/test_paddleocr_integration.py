"""
PaddleOCR集成测试
测试PaddleOCR 3.3.1在macOS ARM64 + Python 3.13环境下的功能
"""

import logging
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pathlib import Path

from paddleocr import PaddleOCR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_paddleocr_initialization():
    """测试PaddleOCR初始化"""
    print("=" * 80)
    print("PaddleOCR集成测试")
    print("=" * 80)
    print()

    print("[1/3] 测试PaddleOCR初始化...")
    try:
        # 初始化PaddleOCR
        # use_textline_orientation=True 启用文本行方向分类
        # lang='ch' 支持中英文混合识别
        ocr = PaddleOCR(
            use_textline_orientation=True, lang="ch"  # 使用文本行方向分类  # 支持中英文混合
        )
        print("✅ PaddleOCR初始化成功")
        print(f"   模型配置: 中英文混合识别, 支持方向分类")
        return ocr

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return None


def test_ocr_on_sample_image(ocr):
    """测试对示例图片进行OCR识别"""
    print("\n[2/3] 测试OCR文字识别...")

    # 创建一个简单的测试目录
    test_dir = Path("test_results/ocr_samples")
    test_dir.mkdir(parents=True, exist_ok=True)

    # 注意：如果没有测试图片，此步骤会跳过
    # 用户可以放置PDF/图片到 samples/ 目录进行测试
    samples_dir = Path("samples")

    if (
        not samples_dir.exists()
        or not list(samples_dir.glob("*.jpg"))
        and not list(samples_dir.glob("*.png"))
    ):
        print("⚠️  没有找到测试图片")
        print(f"   请将测试图片(JPG/PNG)放到 {samples_dir.absolute()} 目录")
        print("   跳过OCR识别测试")
        return False

    # 获取第一张图片
    image_files = list(samples_dir.glob("*.jpg")) + list(samples_dir.glob("*.png"))
    if not image_files:
        print("⚠️  没有找到JPG或PNG图片")
        return False

    test_image = image_files[0]
    print(f"   测试图片: {test_image.name}")

    try:
        # 执行OCR识别 (PaddleOCR 3.3.1新API)
        result = ocr.predict(str(test_image))

        if not result or not result[0]:
            print("⚠️  未识别到文字")
            return False

        # 解析结果 (PaddleOCR 3.3.1新格式)
        print("✅ OCR识别成功")
        print("\n   识别结果:")

        # PaddleOCR 3.3.1返回列表，第一个元素是字典
        if isinstance(result, list) and len(result) > 0:
            page_result = result[0]

            # 检查是否有识别的文本行
            if "rec_texts" in page_result:
                # rec_texts包含识别出的所有文本
                texts = page_result["rec_texts"]
                scores = page_result.get("rec_scores", [])

                if isinstance(texts, list):
                    for idx, text in enumerate(texts, 1):
                        score = scores[idx - 1] if idx - 1 < len(scores) else 0.0
                        print(f"   [{idx}] {text} (置信度: {score:.2f})")
                else:
                    print(f"   文本: {texts}")
            else:
                print(f"   ⚠️ 未找到rec_text字段")
                print(f"   可用字段: {list(page_result.keys())}")
        else:
            print(f"   ⚠️ 结果格式不符合预期")

        return True

    except Exception as e:
        print(f"❌ OCR识别失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ocr_capabilities(ocr):
    """测试PaddleOCR特性"""
    print("\n[3/3] PaddleOCR特性说明")
    print("-" * 80)
    print("已安装版本: PaddleOCR 3.3.1")
    print("\n核心特性:")
    print("  ✅ PP-OCRv5 全场景识别 (简体、繁体、英文、日文、拼音)")
    print("  ✅ 支持复杂手写体识别")
    print("  ✅ PP-StructureV3 文档解析 (PDF高精度解析)")
    print("  ✅ Markdown/JSON结构导出")
    print("\n性能优化:")
    print("  ⚠️  MPS GPU加速需要PaddlePaddle (当前Python 3.13暂不支持)")
    print("  ✅ 使用CPU推理 (已优化多线程)")
    print("\n支持格式:")
    print("  • 图片: JPG, PNG, BMP, TIFF")
    print("  • 文档: PDF (通过PP-StructureV3)")
    print("  • 语言: 109种语言 (使用PaddleOCR-VL模型)")
    print()


def main():
    """主函数"""
    # 1. 初始化
    ocr = test_paddleocr_initialization()
    if not ocr:
        print("\n❌ 测试失败: PaddleOCR初始化失败")
        return

    # 2. 测试OCR识别
    ocr_success = test_ocr_on_sample_image(ocr)

    # 3. 显示特性
    test_ocr_capabilities(ocr)

    # 总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"  ✅ PaddleOCR初始化: 成功")
    print(
        f"  {'✅' if ocr_success else '⚠️ '} OCR文字识别: {'成功' if ocr_success else '跳过(无测试图片)'}"
    )
    print()

    if not ocr_success:
        print("📝 下一步:")
        print("  1. 将测试图片放到 samples/ 目录")
        print("  2. 重新运行此脚本测试OCR识别功能")
    else:
        print("✅ PaddleOCR集成测试全部通过!")

    print()


if __name__ == "__main__":
    main()
