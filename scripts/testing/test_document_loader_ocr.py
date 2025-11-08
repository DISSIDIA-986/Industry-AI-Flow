"""
测试DocumentLoader的OCR集成
验证PaddleOCR 3.3.1与DocumentLoader的完整集成
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pathlib import Path
from backend.services.document_loader import EnhancedDocumentLoader


def test_ocr_image_loading():
    """测试图片OCR加载"""
    print("=" * 80)
    print("DocumentLoader OCR集成测试")
    print("=" * 80)
    print()

    # 1. 初始化DocumentLoader
    print("[1/3] 初始化DocumentLoader...")
    try:
        loader = EnhancedDocumentLoader(use_ocr=True, ocr_lang='ch')
        print("✅ DocumentLoader初始化成功")
        print()
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

    # 2. 测试图片加载
    print("[2/3] 测试图片OCR识别...")
    test_image = Path("samples/test_ocr.png")

    if not test_image.exists():
        print(f"⚠️  测试图片不存在: {test_image}")
        print("   请先运行: python scripts/testing/create_test_image.py")
        return False

    try:
        print(f"   加载图片: {test_image.name}")
        text = loader.load_document(test_image)

        if text:
            print("✅ OCR识别成功")
            print("\n   识别结果:")
            for idx, line in enumerate(text.split('\n'), 1):
                if line.strip():
                    print(f"   [{idx}] {line}")
        else:
            print("⚠️  未识别到文字")
            return False

        print()
        return True

    except Exception as e:
        print(f"❌ OCR识别失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_features_summary():
    """显示功能总结"""
    print("[3/3] DocumentLoader功能总结")
    print("-" * 80)
    print("支持的文件格式:")
    print("  ✅ TXT - 纯文本文件")
    print("  ✅ PDF - 文本PDF或扫描PDF(自动OCR)")
    print("  ✅ 图片 - JPG, PNG, BMP, TIFF (需要OCR)")
    print()
    print("OCR特性:")
    print("  ✅ PaddleOCR 3.3.1 集成")
    print("  ✅ PP-OCRv5 高精度识别")
    print("  ✅ 支持中英文混合")
    print("  ✅ 自动文本行方向检测")
    print("  ✅ 智能PDF扫描件检测")
    print()
    print("工作流程:")
    print("  1. PDF文档 → 尝试提取文本")
    print("  2. 如果文本<50字符 → 判断为扫描件 → 使用OCR")
    print("  3. 图片文件 → 直接使用OCR识别")
    print("  4. 返回完整文本内容 → RAG向量化存储")
    print()


def main():
    """主函数"""
    success = test_ocr_image_loading()

    test_features_summary()

    # 总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)

    if success:
        print("✅ DocumentLoader OCR集成测试通过!")
        print("\n下一步:")
        print("  • 可以开始上传图片/扫描PDF到RAG系统")
        print("  • 系统会自动使用OCR提取文本并向量化")
        print("  • 支持对OCR识别的内容进行智能问答")
    else:
        print("⚠️  部分测试未通过")
        print("\n建议:")
        print("  • 检查测试图片是否存在")
        print("  • 验证PaddleOCR安装是否正确")

    print()


if __name__ == "__main__":
    main()
