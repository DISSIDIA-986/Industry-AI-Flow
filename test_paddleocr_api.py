#!/usr/bin/env python3
"""
测试PaddleOCR API的正确用法
"""

import os
import sys


def test_paddleocr_api():
    """测试PaddleOCR的各种API调用方式"""
    print("🔍 PaddleOCR API测试")
    print("=" * 50)

    try:
        import paddleocr
        from paddleocr import PaddleOCR

        print("✅ PaddleOCR导入成功")
        print(f"📦 PaddleOCR版本: {paddleocr.__version__}")

        # 测试图像路径
        image_path = "test_resources/images/architectural_floor_plan.png"
        if not os.path.exists(image_path):
            print(f"❌ 测试图像不存在: {image_path}")
            return False

        print(f"📷 使用测试图像: {image_path}")

        # 测试不同的初始化方式
        print("\n🧪 测试1: 基本初始化")
        try:
            ocr = PaddleOCR(lang="en")
            print("✅ 基本初始化成功")
        except Exception as e:
            print(f"❌ 基本初始化失败: {e}")
            return False

        # 测试OCR预测
        print("\n🧪 测试2: OCR预测")
        try:
            result = ocr.predict(image_path)
            print("✅ OCR预测成功")
            print(f"📊 结果类型: {type(result)}")
            print(f"📊 结果长度: {len(result) if result else 0}")
            if result and len(result) > 0:
                print(f"📊 第一个结果: {result[0]}")
                if isinstance(result[0], dict):
                    print("📋 结果是字典格式:")
                    for key, value in result[0].items():
                        print(f"   - {key}: {type(value)}")
        except Exception as e:
            print(f"❌ OCR预测失败: {e}")

        # 测试旧的API方式
        print("\n🧪 测试3: 旧API方式")
        try:
            result_old = ocr.ocr(image_path)
            print("✅ 旧API调用成功")
            print(f"📊 旧API结果类型: {type(result_old)}")
            if result_old:
                print(f"📊 旧API结果长度: {len(result_old)}")
        except Exception as e:
            print(f"⚠️ 旧API调用失败（预期）: {e}")

        return True

    except ImportError as e:
        print(f"❌ PaddleOCR导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    success = test_paddleocr_api()
    sys.exit(0 if success else 1)
