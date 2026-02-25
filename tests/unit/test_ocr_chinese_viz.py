"""
ENPaddleOCR 3.3.1ENOCREN

EN:
- EN_EN.png
- EN_EN.png
- EN_EN.png
- EN_EN.png
- EN.png
"""

import sys
import time
from pathlib import Path

# EN
project_root = Path(__file__).parent


def test_ocr_on_visualization():
    """ENOCREN"""
    print("=" * 80)
    print("PaddleOCR 3.3.1 (PP-OCRv5) - EN")
    print("=" * 80)

    # ENPaddleOCREN
    try:
        from backend.services.document_processing import ocr_processor
        from backend.tools.document_processing import ocr_image

        if ocr_processor is None:
            print("\n❌ OCREN")
            print("ENPaddleOCR:")
            print("  pip install paddlepaddle>=2.6.0")
            print("  pip install paddleocr>=3.3.0")
            print("  pip install 'numpy>=1.26.4,<2.0'")
            print("  pip install paddle-custom-mps  # MPSEN")
            return False

        print(f"\n✅ OCREN")
        print(f"   EN: {ocr_processor.lang}")
        print(f"   ENOCR: {ocr_processor.local_ocr is not None}")
        print(f"   APIEN: {ocr_processor.use_api_fallback}")

    except Exception as e:
        print(f"\n❌ EN: {e}")
        return False

    # EN
    viz_dir = project_root / "test_resources" / "images"
    if not viz_dir.exists():
        print(f"\n❌ EN: {viz_dir}")
        return False

    # ENPNGEN
    image_files = sorted(viz_dir.glob("*.png"))
    if not image_files:
        print(f"\n❌ ENPNGEN")
        return False

    print(f"\nEN {len(image_files)} EN")
    print("-" * 80)

    # EN
    results = []
    for idx, image_path in enumerate(image_files, 1):
        print(f"\n[{idx}/{len(image_files)}] EN: {image_path.name}")
        print("-" * 80)

        try:
            # EN
            start_time = time.time()

            # ENLangChainENOCR
            result = ocr_image.invoke(
                {"image_path": str(image_path), "language": "ch"}  # PP-OCRv5EN
            )

            # EN
            elapsed_time = time.time() - start_time

            if result["success"]:
                print(f"✅ EN!")
                print(f"   EN: {result['method']}")
                print(f"   EN: {result['confidence']:.2%}")
                print(f"   EN: {elapsed_time:.2f}EN")
                print(f"   EN: {result.get('num_boxes', 0)}")

                # EN
                text = result["text"]
                if text:
                    print(f"\n📝 EN:")
                    # EN
                    if len(text) > 500:
                        print(f"{text[:500]}...")
                        print(f"\n   (EN,EN.EN: {len(text)} EN)")
                    else:
                        print(text)

                    # EN
                    lines = text.strip().split("\n")
                    print(f"\n📊 EN:")
                    print(f"   EN: {len(text)}")
                    print(f"   EN: {len(lines)}")
                    print(f"   EN: {len([l for l in lines if l.strip()])}")

                results.append(
                    {
                        "file": image_path.name,
                        "success": True,
                        "method": result["method"],
                        "confidence": result["confidence"],
                        "time": elapsed_time,
                        "text_length": len(text),
                        "num_boxes": result.get("num_boxes", 0),
                    }
                )
            else:
                print(f"❌ EN: {result.get('error', 'Unknown error')}")
                results.append(
                    {
                        "file": image_path.name,
                        "success": False,
                        "error": result.get("error", "Unknown"),
                    }
                )

        except Exception as e:
            print(f"❌ EN: {e}")
            import traceback

            traceback.print_exc()
            results.append(
                {
                    "file": image_path.name,
                    "success": False,
                    "error": str(e),
                }
            )

    # EN
    print("\n" + "=" * 80)
    print("EN")
    print("=" * 80)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\nEN: {len(image_files)} EN")
    print(f"EN: {len(successful)} EN")
    print(f"EN: {len(failed)} EN")
    print(f"EN: {len(successful)/len(results)*100:.1f}%")

    if successful:
        print(f"\n✅ EN:")
        for r in successful:
            print(f"   • {r['file']}")
            print(
                f"     - EN: {r['method']}, EN: {r['confidence']:.2%}, "
                f"EN: {r['time']:.2f}s, EN: {r['text_length']}"
            )

        # EN
        avg_time = sum(r["time"] for r in successful) / len(successful)
        avg_confidence = sum(r["confidence"] for r in successful) / len(successful)
        total_chars = sum(r["text_length"] for r in successful)

        print(f"\n📊 EN:")
        print(f"   EN: {avg_time:.2f}EN/EN")
        print(f"   EN: {avg_confidence:.2%}")
        print(f"   EN: {total_chars}")
        print(f"   EN/EN: {total_chars/len(successful):.0f}")

        # MPSEN
        if successful and successful[0]["method"] == "local":
            print(f"\n⚡ MPSEN:")
            print(f"   EN: ENPaddleOCR")
            print(f"   ENMPS,ENCPUEN2-5EN")
            print(f"   EN: python test_paddleocr_v5.py")

    if failed:
        print(f"\n❌ EN:")
        for r in failed:
            print(f"   • {r['file']}: {r.get('error', 'Unknown error')}")

    return len(failed) == 0


def test_batch_processing():
    """EN"""
    print("\n" + "=" * 80)
    print("EN")
    print("=" * 80)

    try:
        from backend.tools.document_processing import batch_extract_documents

        viz_dir = project_root / "test_resources" / "images"
        image_files = [str(f) for f in viz_dir.glob("*.png")]

        if not image_files:
            print("EN")
            return False

        print(f"\nEN {len(image_files)} EN...")

        start_time = time.time()
        result = batch_extract_documents.invoke(
            {"file_paths": image_files, "use_ocr": True}
        )
        elapsed_time = time.time() - start_time

        print(f"\nEN:")
        print(f"   EN: {result['total']}")
        print(f"   EN: {result['succeeded']}")
        print(f"   EN: {result['failed']}")
        print(f"   EN: {elapsed_time:.2f}EN")
        print(f"   EN: {elapsed_time/result['total']:.2f}EN/EN")

        return result["success"]

    except Exception as e:
        print(f"EN: {e}")
        return False


def test_integration_workflow():
    """EN: OCR → EN → EN"""
    print("\n" + "=" * 80)
    print("EN")
    print("=" * 80)

    try:
        from backend.services.document_processing import process_document

        # EN
        viz_dir = project_root / "test_resources" / "images"
        test_image = viz_dir / "EN.png"

        if not test_image.exists():
            # EN
            images = list(viz_dir.glob("*.png"))
            if not images:
                print("EN")
                return False
            test_image = images[0]

        print(f"\nEN: {test_image.name}")

        # EN
        content = process_document(test_image, use_ocr=True)

        print(f"\nEN:")
        print(f"   EN: {content.file_type}")
        print(f"   EN: {content.method}")
        print(f"   EN: {len(content.text)} EN")
        print(f"   EN: {content.metadata}")

        # EN
        output_file = project_root / "ocr_output.txt"
        output_file.write_text(content.text, encoding="utf-8")
        print(f"\n✅ EN: {output_file}")

        # EN200EN
        preview = content.text[:200]
        print(f"\nEN:")
        print(preview)
        if len(content.text) > 200:
            print("...")

        return True

    except Exception as e:
        print(f"EN: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """EN"""
    print("\n" + "=" * 80)
    print("PaddleOCR 3.3.1 (PP-OCRv5) EN")
    print("=" * 80)

    results = {
        "OCREN": test_ocr_on_visualization(),
        "EN": test_batch_processing(),
        "EN": test_integration_workflow(),
    }

    # EN
    print("\n" + "=" * 80)
    print("EN")
    print("=" * 80)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {name}")

    print(f"\nEN: {passed}/{total} EN ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 EN!")
        print("\nPP-OCRv5EN:")
        print("   ✅ EN (EN/EN/EN/EN/EN)")
        print("   ✅ EN +13%")
        print("   ✅ MPSEN (2-5xEN)")
        return 0
    else:
        print(f"\n⚠️  {total - passed} EN")
        return 1


if __name__ == "__main__":
    sys.exit(main())
