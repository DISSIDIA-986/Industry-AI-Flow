"""
EN

EN:
1. OCREN
2. EN
3. LangChainEN
"""

import sys
from pathlib import Path

# EN
project_root = Path(__file__).parent

from backend.services.document_processing import ocr_processor, process_document
from backend.tools.document_processing import (
    batch_extract_documents,
    extract_document_text,
    ocr_image,
)


def test_ocr_availability():
    """ENOCREN"""
    print("=" * 60)
    print("EN 1: OCREN")
    print("=" * 60)

    if ocr_processor is None:
        print("⚠️  OCREN")
        print("   EN:")
        print("   - PaddleOCREN: pip install paddlepaddle paddleocr")
        print("   - EN")
        return False

    print(f"✅ OCREN")
    print(f"   - EN: {ocr_processor.use_local}")
    print(f"   - APIEN: {ocr_processor.use_api_fallback}")
    print(f"   - EN: {ocr_processor.lang}")

    return True


def test_document_extractor():
    """EN"""
    print("\n" + "=" * 60)
    print("EN 2: EN")
    print("=" * 60)

    try:
        from backend.services.document_processing.document_extractor import (
            DocumentExtractor,
        )

        extractor = DocumentExtractor(use_ocr=True)

        supported_types = DocumentExtractor.SUPPORTED_EXTENSIONS
        print(f"✅ EN")
        print(f"   EN: {len(supported_types)} EN")
        for ext, file_type in list(supported_types.items())[:5]:
            print(f"   - {ext}: {file_type}")
        print("   ...")

        return True

    except Exception as e:
        print(f"❌ EN: {e}")
        return False


def test_text_extraction():
    """EN"""
    print("\n" + "=" * 60)
    print("EN 3: EN")
    print("=" * 60)

    # EN
    test_file = project_root / "test_sample.txt"

    try:
        # EN
        test_content = """EN.
EN.
EN.

This is a test document.
With multiple lines.
For testing document extraction."""

        test_file.write_text(test_content, encoding="utf-8")

        # EN
        result = process_document(test_file, use_ocr=False)

        if result.text.strip() == test_content.strip():
            print(f"✅ EN")
            print(f"   EN: {result.method}")
            print(f"   EN: {result.metadata.get('num_chars', 0)}")
            print(f"   EN: {result.metadata.get('num_lines', 0)}")
            return True
        else:
            print(f"❌ EN")
            return False

    except Exception as e:
        print(f"❌ EN: {e}")
        return False

    finally:
        # EN
        if test_file.exists():
            test_file.unlink()


def test_langchain_tools():
    """ENLangChainEN"""
    print("\n" + "=" * 60)
    print("EN 4: LangChainEN")
    print("=" * 60)

    # EN
    test_file = project_root / "test_doc.txt"

    try:
        # EN
        test_content = "LangChain 1.0 Document Processing Test"
        test_file.write_text(test_content, encoding="utf-8")

        # EN
        print("\n4.1 EN:")
        result = extract_document_text.invoke(
            {
                "file_path": str(test_file),
                "use_ocr": False,
            }
        )

        if result["success"]:
            print(f"   ✅ EN")
            print(f"   EN: {result['file_type']}")
            print(f"   EN: {result['method']}")
            print(f"   EN: {len(result['text'])} EN")
            return True
        else:
            print(f"   ❌ EN: {result.get('error', 'Unknown')}")
            return False

    except Exception as e:
        print(f"❌ EN: {e}")
        return False

    finally:
        # EN
        if test_file.exists():
            test_file.unlink()


def test_batch_processing():
    """EN"""
    print("\n" + "=" * 60)
    print("EN 5: EN")
    print("=" * 60)

    # EN
    test_files = []
    created_files = []

    try:
        for i in range(3):
            test_file = project_root / f"test_batch_{i}.txt"
            test_file.write_text(f"Test document {i+1}", encoding="utf-8")
            test_files.append(str(test_file))
            created_files.append(test_file)

        # EN
        result = batch_extract_documents.invoke(
            {
                "file_paths": test_files,
                "use_ocr": False,
            }
        )

        print(f"   EN: {result['total']}")
        print(f"   EN: {result['succeeded']}")
        print(f"   EN: {result['failed']}")

        if result["success"]:
            print(f"✅ EN")
            return True
        else:
            print(f"⚠️  EN")
            return False

    except Exception as e:
        print(f"❌ EN: {e}")
        return False

    finally:
        # EN
        for test_file in created_files:
            if test_file.exists():
                test_file.unlink()


def test_ocr_integration():
    """ENOCREN(EN)"""
    print("\n" + "=" * 60)
    print("EN 6: OCREN (EN)")
    print("=" * 60)

    if ocr_processor is None or ocr_processor.local_ocr is None:
        print("⚠️  OCREN,EN")
        print("   ENPaddleOCR: pip install paddlepaddle paddleocr")
        return None

    print("✅ OCREN,EN")
    print("   EN: ENOCREN")
    print("   EN:")
    print("   >>> from backend.tools.document_processing import ocr_image")
    print("   >>> result = ocr_image('/path/to/image.png', language='ch')")

    return True


def main():
    """EN"""
    print("\n" + "=" * 60)
    print("EN")
    print("=" * 60)

    results = {
        "OCREN": test_ocr_availability(),
        "EN": test_document_extractor(),
        "EN": test_text_extraction(),
        "LangChainEN": test_langchain_tools(),
        "EN": test_batch_processing(),
        "OCREN": test_ocr_integration(),
    }

    # EN
    print("\n" + "=" * 60)
    print("EN")
    print("=" * 60)

    # ENNone(EN)
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
        print(f"\nEN: {passed}/{total} EN ({passed/total*100:.1f}%)")

        if passed == total:
            print("\n🎉 EN!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} EN")
            return 1
    else:
        print("\n⚠️  EN")
        return 0


if __name__ == "__main__":
    sys.exit(main())
