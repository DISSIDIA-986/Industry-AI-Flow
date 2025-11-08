"""
测试文档处理系统

测试内容:
1. OCR处理器测试
2. 文档提取器测试
3. LangChain工具集成
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.document_processing import ocr_processor, process_document
from backend.tools.document_processing import (
    batch_extract_documents,
    extract_document_text,
    ocr_image,
)


def test_ocr_availability():
    """测试OCR可用性"""
    print("=" * 60)
    print("测试 1: OCR可用性检测")
    print("=" * 60)

    if ocr_processor is None:
        print("⚠️  OCR处理器未初始化")
        print("   可能原因:")
        print("   - PaddleOCR未安装: pip install paddlepaddle paddleocr")
        print("   - 依赖库缺失")
        return False

    print(f"✅ OCR处理器可用")
    print(f"   - 使用本地: {ocr_processor.use_local}")
    print(f"   - API备份: {ocr_processor.use_api_fallback}")
    print(f"   - 语言: {ocr_processor.lang}")

    return True


def test_document_extractor():
    """测试文档提取器"""
    print("\n" + "=" * 60)
    print("测试 2: 文档提取器")
    print("=" * 60)

    try:
        from backend.services.document_processing.document_extractor import (
            DocumentExtractor,
        )

        extractor = DocumentExtractor(use_ocr=True)

        supported_types = DocumentExtractor.SUPPORTED_EXTENSIONS
        print(f"✅ 文档提取器初始化成功")
        print(f"   支持的文件类型: {len(supported_types)} 种")
        for ext, file_type in list(supported_types.items())[:5]:
            print(f"   - {ext}: {file_type}")
        print("   ...")

        return True

    except Exception as e:
        print(f"❌ 文档提取器初始化失败: {e}")
        return False


def test_text_extraction():
    """测试文本文件提取"""
    print("\n" + "=" * 60)
    print("测试 3: 文本文件提取")
    print("=" * 60)

    # 创建临时测试文件
    test_file = project_root / "test_sample.txt"

    try:
        # 写入测试内容
        test_content = """这是一个测试文档。
包含多行文本。
用于验证文档提取功能。

This is a test document.
With multiple lines.
For testing document extraction."""

        test_file.write_text(test_content, encoding="utf-8")

        # 提取内容
        result = process_document(test_file, use_ocr=False)

        if result.text.strip() == test_content.strip():
            print(f"✅ 文本提取成功")
            print(f"   方法: {result.method}")
            print(f"   字符数: {result.metadata.get('num_chars', 0)}")
            print(f"   行数: {result.metadata.get('num_lines', 0)}")
            return True
        else:
            print(f"❌ 提取内容不匹配")
            return False

    except Exception as e:
        print(f"❌ 文本提取失败: {e}")
        return False

    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()


def test_langchain_tools():
    """测试LangChain工具"""
    print("\n" + "=" * 60)
    print("测试 4: LangChain工具集成")
    print("=" * 60)

    # 创建临时测试文件
    test_file = project_root / "test_doc.txt"

    try:
        # 写入测试内容
        test_content = "LangChain 1.0 Document Processing Test"
        test_file.write_text(test_content, encoding="utf-8")

        # 测试提取工具
        print("\n4.1 文档提取工具:")
        result = extract_document_text.invoke(
            {
                "file_path": str(test_file),
                "use_ocr": False,
            }
        )

        if result["success"]:
            print(f"   ✅ 提取成功")
            print(f"   文件类型: {result['file_type']}")
            print(f"   方法: {result['method']}")
            print(f"   文本长度: {len(result['text'])} 字符")
            return True
        else:
            print(f"   ❌ 提取失败: {result.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print(f"❌ 工具测试失败: {e}")
        return False

    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()


def test_batch_processing():
    """测试批量处理"""
    print("\n" + "=" * 60)
    print("测试 5: 批量文档处理")
    print("=" * 60)

    # 创建多个测试文件
    test_files = []
    created_files = []

    try:
        for i in range(3):
            test_file = project_root / f"test_batch_{i}.txt"
            test_file.write_text(f"Test document {i+1}", encoding="utf-8")
            test_files.append(str(test_file))
            created_files.append(test_file)

        # 批量处理
        result = batch_extract_documents.invoke(
            {
                "file_paths": test_files,
                "use_ocr": False,
            }
        )

        print(f"   总文件数: {result['total']}")
        print(f"   成功: {result['succeeded']}")
        print(f"   失败: {result['failed']}")

        if result["success"]:
            print(f"✅ 批量处理成功")
            return True
        else:
            print(f"⚠️  部分文件处理失败")
            return False

    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        return False

    finally:
        # 清理测试文件
        for test_file in created_files:
            if test_file.exists():
                test_file.unlink()


def test_ocr_integration():
    """测试OCR集成（可选）"""
    print("\n" + "=" * 60)
    print("测试 6: OCR集成 (可选)")
    print("=" * 60)

    if ocr_processor is None or ocr_processor.local_ocr is None:
        print("⚠️  OCR未启用，跳过测试")
        print("   安装PaddleOCR: pip install paddlepaddle paddleocr")
        return None

    print("✅ OCR已启用，可以处理图像文档")
    print("   注: 需要真实图像文件才能测试OCR功能")
    print("   使用方法:")
    print("   >>> from backend.tools.document_processing import ocr_image")
    print("   >>> result = ocr_image('/path/to/image.png', language='ch')")

    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("文档处理系统测试套件")
    print("=" * 60)

    results = {
        "OCR可用性": test_ocr_availability(),
        "文档提取器": test_document_extractor(),
        "文本提取": test_text_extraction(),
        "LangChain工具": test_langchain_tools(),
        "批量处理": test_batch_processing(),
        "OCR集成": test_ocr_integration(),
    }

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    # 过滤掉None（跳过的测试）
    non_skipped = {k: v for k, v in results.items() if v is not None}
    passed = sum(non_skipped.values())
    total = len(non_skipped)

    for name, result in results.items():
        if result is None:
            status = "⏭️  SKIP"
        elif result:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"{status}  {name}")

    if total > 0:
        print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

        if passed == total:
            print("\n🎉 所有测试通过!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} 个测试失败")
            return 1
    else:
        print("\n⚠️  所有测试被跳过")
        return 0


if __name__ == "__main__":
    sys.exit(main())
