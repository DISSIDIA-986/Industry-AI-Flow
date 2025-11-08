"""
简化版PaddleOCR测试 - 直接测试PaddleOCR SDK

不依赖LangChain,直接使用PaddleOCR库
"""

import sys
from pathlib import Path
import time


def check_dependencies():
    """检查依赖"""
    print("=" * 80)
    print("依赖检查")
    print("=" * 80)

    missing = []

    # 检查PaddlePaddle
    try:
        import paddle
        version = paddle.__version__
        print(f"✅ PaddlePaddle: {version}")

        # 检查MPS设备
        try:
            custom_devices = paddle.device.get_all_custom_device_type()
            if 'mps' in custom_devices:
                print(f"   ✅ MPS设备可用")
            else:
                print(f"   ⚠️  MPS设备未检测到")
        except:
            print(f"   ⚠️  无法检测MPS设备")

    except ImportError:
        print(f"❌ PaddlePaddle 未安装")
        missing.append("paddlepaddle>=2.6.0")

    # 检查PaddleOCR
    try:
        import paddleocr
        print(f"✅ PaddleOCR 已安装")
    except ImportError:
        print(f"❌ PaddleOCR 未安装")
        missing.append("paddleocr>=3.3.0")

    # 检查NumPy
    try:
        import numpy as np
        version = np.__version__
        major = int(version.split('.')[0])
        if major < 2:
            print(f"✅ NumPy: {version} (兼容)")
        else:
            print(f"⚠️  NumPy: {version} (建议<2.0)")
    except ImportError:
        print(f"❌ NumPy 未安装")
        missing.append("numpy>=1.26.4,<2.0")

    if missing:
        print(f"\n缺少依赖，请安装:")
        print(f"pip install {' '.join(missing)}")
        return False

    return True


def test_ocr_basic():
    """基础OCR测试"""
    print("\n" + "=" * 80)
    print("基础OCR测试")
    print("=" * 80)

    try:
        from paddleocr import PaddleOCR
        import paddle

        # 初始化OCR
        print("\n初始化PaddleOCR...")

        # 检测设备
        use_gpu = False
        try:
            custom_devices = paddle.device.get_all_custom_device_type()
            if 'mps' in custom_devices:
                use_gpu = True
                print("✅ 启用MPS加速")
            elif paddle.device.is_compiled_with_cuda():
                use_gpu = True
                print("✅ 启用CUDA加速")
            else:
                print("⚠️  使用CPU模式")
        except:
            print("⚠️  使用CPU模式")

        ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            use_gpu=use_gpu,
            show_log=False
        )

        print("✅ PaddleOCR初始化成功")
        return ocr

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_images(ocr):
    """测试中文可视化图片"""
    if ocr is None:
        print("OCR未初始化，跳过测试")
        return

    print("\n" + "=" * 80)
    print("中文可视化图片识别测试")
    print("=" * 80)

    # 图片目录
    viz_dir = Path(__file__).parent / "chinese_visualization_output"
    if not viz_dir.exists():
        print(f"❌ 目录不存在: {viz_dir}")
        return

    # 获取图片
    images = sorted(viz_dir.glob("*.png"))
    if not images:
        print("❌ 没有找到图片")
        return

    print(f"\n找到 {len(images)} 个图片")

    results = []
    for idx, img_path in enumerate(images, 1):
        print(f"\n[{idx}/{len(images)}] {img_path.name}")
        print("-" * 80)

        try:
            start_time = time.time()

            # OCR识别
            result = ocr.ocr(str(img_path), cls=True)

            elapsed = time.time() - start_time

            if result and result[0]:
                # 提取文本
                texts = []
                confidences = []

                for line in result[0]:
                    box, (text, confidence) = line
                    texts.append(text)
                    confidences.append(confidence)

                full_text = "\n".join(texts)
                avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

                print(f"✅ 识别成功")
                print(f"   耗时: {elapsed:.2f}秒")
                print(f"   文本框: {len(texts)}个")
                print(f"   置信度: {avg_conf:.2%}")
                print(f"   字符数: {len(full_text)}")

                # 显示文本预览
                print(f"\n📝 识别文本预览:")
                preview = full_text[:300]
                print(preview)
                if len(full_text) > 300:
                    print("...")

                results.append({
                    'name': img_path.name,
                    'success': True,
                    'time': elapsed,
                    'boxes': len(texts),
                    'confidence': avg_conf,
                    'chars': len(full_text),
                    'text': full_text
                })

            else:
                print(f"⚠️  未识别到文本")
                results.append({
                    'name': img_path.name,
                    'success': False,
                })

        except Exception as e:
            print(f"❌ 识别失败: {e}")
            results.append({
                'name': img_path.name,
                'success': False,
                'error': str(e)
            })

    # 总结
    print("\n" + "=" * 80)
    print("识别总结")
    print("=" * 80)

    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]

    print(f"\n总计: {len(results)} 个图片")
    print(f"成功: {len(successful)} 个")
    print(f"失败: {len(failed)} 个")

    if successful:
        avg_time = sum(r['time'] for r in successful) / len(successful)
        avg_conf = sum(r['confidence'] for r in successful) / len(successful)
        total_chars = sum(r['chars'] for r in successful)

        print(f"\n性能统计:")
        print(f"   平均耗时: {avg_time:.2f}秒/张")
        print(f"   平均置信度: {avg_conf:.2%}")
        print(f"   总识别字符: {total_chars}")
        print(f"   平均字符数: {total_chars/len(successful):.0f}字/张")

        # 保存所有识别文本
        output_file = Path(__file__).parent / "ocr_results.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            for r in successful:
                f.write(f"{'='*80}\n")
                f.write(f"图片: {r['name']}\n")
                f.write(f"置信度: {r['confidence']:.2%}\n")
                f.write(f"{'='*80}\n")
                f.write(r['text'])
                f.write("\n\n")

        print(f"\n✅ 识别结果已保存到: {output_file}")


def main():
    """主函数"""
    print("\nPaddleOCR 3.3.1 (PP-OCRv5) 简化测试")
    print("=" * 80)

    # 检查依赖
    if not check_dependencies():
        print("\n请先安装依赖:")
        print("pip install paddlepaddle>=2.6.0")
        print("pip install paddleocr>=3.3.0")
        print("pip install 'numpy>=1.26.4,<2.0'")
        return 1

    # 初始化OCR
    ocr = test_ocr_basic()

    # 测试图片
    test_images(ocr)

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
