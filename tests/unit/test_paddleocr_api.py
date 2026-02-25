#!/usr/bin/env python3
"""
ENPaddleOCR APIEN
"""

import os
import sys


def test_paddleocr_api():
    """ENPaddleOCRENAPIEN"""
    print("🔍 PaddleOCR APIEN")
    print("=" * 50)

    try:
        import paddleocr
        from paddleocr import PaddleOCR

        print("✅ PaddleOCREN")
        print(f"📦 PaddleOCREN: {paddleocr.__version__}")

        # EN
        image_path = "test_resources/images/architectural_floor_plan.png"
        if not os.path.exists(image_path):
            print(f"❌ EN: {image_path}")
            return False

        print(f"📷 EN: {image_path}")

        # EN
        print("\n🧪 EN1: EN")
        try:
            ocr = PaddleOCR(lang="en")
            print("✅ EN")
        except Exception as e:
            print(f"❌ EN: {e}")
            return False

        # ENOCREN
        print("\n🧪 EN2: OCREN")
        try:
            result = ocr.predict(image_path)
            print("✅ OCREN")
            print(f"📊 EN: {type(result)}")
            print(f"📊 EN: {len(result) if result else 0}")
            if result and len(result) > 0:
                print(f"📊 EN: {result[0]}")
                if isinstance(result[0], dict):
                    print("📋 EN:")
                    for key, value in result[0].items():
                        print(f"   - {key}: {type(value)}")
        except Exception as e:
            print(f"❌ OCREN: {e}")

        # ENAPIEN
        print("\n🧪 EN3: ENAPIEN")
        try:
            result_old = ocr.ocr(image_path)
            print("✅ ENAPIEN")
            print(f"📊 ENAPIEN: {type(result_old)}")
            if result_old:
                print(f"📊 ENAPIEN: {len(result_old)}")
        except Exception as e:
            print(f"⚠️ ENAPIEN(EN): {e}")

        return True

    except ImportError as e:
        print(f"❌ PaddleOCREN: {e}")
        return False
    except Exception as e:
        print(f"❌ EN: {e}")
        return False


if __name__ == "__main__":
    success = test_paddleocr_api()
    sys.exit(0 if success else 1)
