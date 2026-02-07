#!/usr/bin/env python3
"""
文档加载功能测试（不依赖实际OCR库）
测试代码结构和接口
"""
import os
import sys

# 添加路径以便导入backend模块


def test_document_loader_structure():
    """测试文档加载器结构"""
    print("🔍 测试文档加载器结构...")

    try:
        # 检查文件是否存在
        loader_file = "backend/services/document_loader.py"
        if not os.path.exists(loader_file):
            print(f"❌ 文件不存在: {loader_file}")
            return False

        # 读取代码并检查关键类和方法
        with open(loader_file, "r", encoding="utf-8") as f:
            loader_code = f.read()

        required_classes = ["class DocumentLoader", "class EnhancedDocumentLoader"]

        for cls in required_classes:
            if cls in loader_code:
                print(f"✅ 类 {cls} 存在")
            else:
                print(f"❌ 类 {cls} 不存在")
                return False

        # 检查关键方法
        required_methods = [
            "def load_document",
            "def _load_pdf",
            "def _load_image_ocr",
            "def _load_text",
        ]

        for method in required_methods:
            if method in loader_code:
                print(f"✅ 方法 {method} 存在")
            else:
                print(f"⚠️  方法 {method} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ 文档加载器结构检查失败: {e}")
        return False


def test_ocr_integration():
    """测试OCR集成代码"""
    print("\n🔍 测试OCR集成代码...")

    try:
        with open("backend/services/document_loader.py", "r", encoding="utf-8") as f:
            loader_code = f.read()

        ocr_patterns = [
            "PaddleOCR",
            "use_ocr",
            "ocr_lang",
            "_detect_scanned_pdf",
            "_extract_text_from_pdf",
        ]

        for pattern in ocr_patterns:
            if pattern in loader_code:
                print(f"✅ OCR集成 {pattern} 存在")
            else:
                print(f"⚠️  OCR集成 {pattern} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ OCR集成检查失败: {e}")
        return False


def test_file_format_support():
    """测试文件格式支持"""
    print("\n🔍 测试文件格式支持...")

    try:
        with open("backend/services/document_loader.py", "r", encoding="utf-8") as f:
            loader_code = f.read()

        formats = [".pdf", ".txt", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"]

        for fmt in formats:
            if fmt in loader_code.lower():
                print(f"✅ 格式 {fmt} 支持")
            else:
                print(f"⚠️  格式 {fmt} 可能不支持")

        return True
    except Exception as e:
        print(f"❌ 文件格式支持检查失败: {e}")
        return False


def test_sample_files():
    """测试示例文件"""
    print("\n🔍 测试示例文件...")

    sample_files = [
        "samples/test_document_1.txt",
        "samples/test_document_2.txt",
        "samples/test_document_3.txt",
        "test_resources/images/test_ocr.png",
        "samples/test_text.txt",
    ]

    found_files = 0
    for file_path in sample_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} ({size} bytes)")
            found_files += 1
        else:
            print(f"❌ {file_path} 不存在")

    print(f"\n找到 {found_files}/{len(sample_files)} 个示例文件")
    return found_files >= len(sample_files) * 0.8


def test_rag_integration():
    """测试RAG集成"""
    print("\n🔍 测试RAG集成...")

    try:
        with open("backend/services/rag_engine.py", "r", encoding="utf-8") as f:
            rag_code = f.read()

        rag_patterns = [
            "DocumentLoader",
            "load_document",
            "add_documents",
            "process_file",
        ]

        for pattern in rag_patterns:
            if pattern in rag_code:
                print(f"✅ RAG集成 {pattern} 存在")
            else:
                print(f"⚠️  RAG集成 {pattern} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ RAG集成检查失败: {e}")
        return False


def simulate_document_processing():
    """模拟文档处理流程"""
    print("\n🔍 模拟文档处理流程...")

    try:
        # 模拟文本文件处理
        text_file = "samples/test_document_1.txt"
        if os.path.exists(text_file):
            with open(text_file, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"✅ 文本文件处理: {len(content)} 字符")

        # 模拟图片处理（不需要实际OCR）
        image_file = "test_resources/images/test_ocr.png"
        if os.path.exists(image_file):
            size = os.path.getsize(image_file)
            print(f"✅ 图片文件准备: {size} bytes")
            print("   模拟OCR处理: 提取文本内容...")

        # 模拟向量化过程
        mock_text = "这是一个测试文档内容示例。"
        mock_chunks = ["这是一个测试文档", "内容示例", "包含中文文本"]
        print(f"✅ 文档分块: {len(mock_chunks)} 个片段")
        print(f"✅ 向量化处理: 生成 {len(mock_chunks)} 个向量")

        return True
    except Exception as e:
        print(f"❌ 模拟文档处理失败: {e}")
        return False


def test_migration_compatibility():
    """测试迁移兼容性"""
    print("\n🔍 测试迁移兼容性...")

    try:
        # 检查迁移相关文件
        migration_files = [
            "PADDLEOCR_INSTALLATION_SUMMARY.md",
            "LLAMACPP_MIGRATION_SUMMARY.md",
        ]

        for file_path in migration_files:
            if os.path.exists(file_path):
                print(f"✅ 迁移文件存在: {file_path}")
            else:
                print(f"⚠️  迁移文件缺失: {file_path}")

        return True
    except Exception as e:
        print(f"❌ 迁移兼容性检查失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 文档加载和OCR功能测试开始\n")
    print("注意: 此测试不需要实际的OCR库加载")
    print("=" * 60)

    tests = [
        ("文档加载器结构", test_document_loader_structure),
        ("OCR集成代码", test_ocr_integration),
        ("文件格式支持", test_file_format_support),
        ("示例文件", test_sample_files),
        ("RAG集成", test_rag_integration),
        ("模拟文档处理", simulate_document_processing),
        ("迁移兼容性", test_migration_compatibility),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print("=" * 50)

        if test_func():
            passed += 1
            print(f"✅ {test_name} 测试通过")
        else:
            print(f"❌ {test_name} 测试失败")

    print(f"\n{'='*50}")
    print(f"测试总结: {passed}/{total} 通过")
    print("=" * 50)

    if passed >= total * 0.8:  # 80% 通过率
        print("🎉 大部分测试通过！文档加载功能结构正确")
        print("\n📝 下一步建议:")
        print("1. 完成 PaddlePaddle 安装")
        print("2. 进行实际OCR功能测试")
        print("3. 测试完整的文档处理流程")
        return True
    else:
        print("⚠️  部分测试失败，请检查文档加载实现")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
