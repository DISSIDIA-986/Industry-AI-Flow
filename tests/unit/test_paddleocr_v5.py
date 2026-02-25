"""
ENPaddleOCR 3.3.1 (PP-OCRv5) EN Apple MPSEN

EN:
1. PaddlePaddleEN
2. MPSEN
3. PP-OCRv5EN
4. EN
"""

import sys
from pathlib import Path

# EN
project_root = Path(__file__).parent


def test_paddle_version():
    """ENPaddlePaddleEN"""
    print("=" * 60)
    print("EN 1: PaddlePaddleEN")
    print("=" * 60)

    try:
        import paddle

        version = paddle.__version__
        print(f"✅ PaddlePaddleEN: {version}")

        # EN
        major, minor = map(int, version.split(".")[:2])
        if major > 2 or (major == 2 and minor >= 6):
            print(f"✅ EN (>=2.6.0)")
            return True
        else:
            print(f"⚠️  EN,EN>=2.6.0ENMPS")
            print(f"   EN: pip install --upgrade paddlepaddle")
            return False

    except ImportError:
        print("❌ PaddlePaddleEN")
        print("   EN: pip install paddlepaddle>=2.6.0")
        return False


def test_mps_device():
    """ENMPSEN"""
    print("\n" + "=" * 60)
    print("EN 2: Apple MPSEN")
    print("=" * 60)

    try:
        import paddle

        # EN
        custom_devices = paddle.device.get_all_custom_device_type()
        print(f"EN: {custom_devices}")

        if "mps" in custom_devices:
            print(f"✅ Apple MPSEN!")
            print(f"   EN: 2-5x (M1/M2/M3EN)")
            print(f"   ENM1 MaxEN4.7x")

            # ENMPS
            try:
                paddle.set_device("mps")
                print(f"✅ ENMPSEN")
                return True
            except Exception as e:
                print(f"⚠️  ENMPSEN: {e}")
                return False
        else:
            print(f"⚠️  MPSEN")
            print(f"   EN:")
            print(f"   1. ENPaddleCustomDevice MPSEN")
            print(f"   2. ENApple SiliconEN")
            print(f"   ENMPSEN: pip install paddle-custom-mps")
            return False

    except Exception as e:
        print(f"❌ EN: {e}")
        return False


def test_paddleocr_version():
    """ENPaddleOCREN"""
    print("\n" + "=" * 60)
    print("EN 3: PaddleOCREN")
    print("=" * 60)

    try:
        import paddleocr

        # PaddleOCREN__version__EN
        try:
            version = paddleocr.__version__
            print(f"✅ PaddleOCREN: {version}")
        except AttributeError:
            print(f"ℹ️  PaddleOCREN")
            print(f"   (EN__version__EN)")

        # ENPaddleOCREN
        from paddleocr import PaddleOCR

        print(f"✅ PaddleOCREN")

        print(f"\nPP-OCRv5 EN:")
        print(f"   • EN5EN: EN/EN/EN/EN/EN")
        print(f"   • EN13EN")
        print(f"   • EN11%")
        print(f"   • EN")

        return True

    except ImportError:
        print("❌ PaddleOCREN")
        print("   EN: pip install paddleocr>=3.3.0")
        return False


def test_ocr_initialization():
    """ENOCREN(EN)"""
    print("\n" + "=" * 60)
    print("EN 4: OCREN")
    print("=" * 60)

    try:
        from backend.services.document_processing.ocr_processor import OCRProcessor

        # ENOCREN
        print("ENOCREN...")
        processor = OCRProcessor(
            use_local=True,
            use_api_fallback=False,  # EN
            lang="ch",  # PP-OCRv5EN
            use_gpu=True,
            ocr_version="PP-OCRv5",
        )

        if processor.local_ocr:
            print(f"✅ OCREN")
            print(f"   EN: {processor.ocr_version}")
            print(f"   EN: {processor.lang}")
            print(f"   GPUEN: EN")
            return True
        else:
            print(f"⚠️  OCREN")
            print(f"   ENPaddlePaddleENPaddleOCREN")
            return False

    except Exception as e:
        print(f"❌ OCREN: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_numpy_version():
    """ENNumPyEN"""
    print("\n" + "=" * 60)
    print("EN 5: NumPyEN")
    print("=" * 60)

    try:
        import numpy as np

        version = np.__version__
        print(f"NumPyEN: {version}")

        # EN
        major = int(version.split(".")[0])
        if major < 2:
            print(f"✅ NumPyEN (<2.0)")
            return True
        else:
            print(f"⚠️  NumPyEN (>=2.0)")
            print(f"   PaddleOCRENNumPy<2.0")
            print(f"   EN: pip install 'numpy<2.0'")
            return False

    except ImportError:
        print("❌ NumPyEN")
        return False


def test_performance_info():
    """EN"""
    print("\n" + "=" * 60)
    print("EN")
    print("=" * 60)

    print("\n📊 Apple Silicon MPSEN:")
    print("   • M1/M2/M3EN: 2-5xEN")
    print("   • M1 Max: EN4.7x")
    print("   • ENCPUEN")

    print("\n⚙️  EN:")
    print("   • use_mp=True: EN")
    print("   • total_process_num=2: EN")
    print("   • rec_batch_num=6: EN")

    print("\n🎯 PP-OCRv5EN:")
    print("   • EN: EN/EN/EN/EN/EN")
    print("   • EN: +13% (EN), +11% (EN)")
    print("   • EN")

    print("\n📦 EN:")
    print("   pip install paddlepaddle>=2.6.0")
    print("   pip install paddleocr>=3.3.0")
    print("   pip install 'numpy>=1.26.4,<2.0'")
    print("   pip install paddle-custom-mps  # MPSEN")


def main():
    """EN"""
    print("\n" + "=" * 60)
    print("PaddleOCR 3.3.1 (PP-OCRv5) + MPS EN")
    print("=" * 60)

    results = {
        "PaddlePaddleEN": test_paddle_version(),
        "MPSEN": test_mps_device(),
        "PaddleOCREN": test_paddleocr_version(),
        "NumPyEN": test_numpy_version(),
        "OCREN": test_ocr_initialization(),
    }

    # EN
    test_performance_info()

    # EN
    print("\n" + "=" * 60)
    print("EN")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        if result:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"{status}  {name}")

    print(f"\nEN: {passed}/{total} EN ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 EN! PaddleOCR 3.3.1EN")
        print("\nEN:")
        print("   1. EN python test_document_processing.py EN")
        print("   2. ENOCREN")
        print("   3. ENMPSEN")
        return 0
    else:
        print(f"\n⚠️  {total - passed} EN")
        print("\nEN")
        return 1


if __name__ == "__main__":
    sys.exit(main())
