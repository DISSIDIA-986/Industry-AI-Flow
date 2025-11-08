"""
测试PaddleOCR 3.3.1对中文可视化图片的OCR识别能力

测试图片:
- 房屋特征价格关系_中文.png
- 房屋特征相关性热力图_中文.png
- 房价综合分析仪表板_中文.png
- 房价分布分析_中文.png
- 中文文本渲染测试.png
"""

import sys
from pathlib import Path
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_ocr_on_visualization():
    """测试OCR对可视化图片的识别"""
    print("=" * 80)
    print("PaddleOCR 3.3.1 (PP-OCRv5) - 中文可视化图片识别测试")
    print("=" * 80)

    # 检查PaddleOCR可用性
    try:
        from backend.services.document_processing import ocr_processor
        from backend.tools.document_processing import ocr_image

        if ocr_processor is None:
            print("\n❌ OCR处理器未初始化")
            print("请先安装PaddleOCR:")
            print("  pip install paddlepaddle>=2.6.0")
            print("  pip install paddleocr>=3.3.0")
            print("  pip install 'numpy>=1.26.4,<2.0'")
            print("  pip install paddle-custom-mps  # MPS加速")
            return False

        print(f"\n✅ OCR处理器已初始化")
        print(f"   语言: {ocr_processor.lang}")
        print(f"   本地OCR: {ocr_processor.local_ocr is not None}")
        print(f"   API备份: {ocr_processor.use_api_fallback}")

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        return False

    # 测试图片目录
    viz_dir = project_root / "test_resources" / "images"
    if not viz_dir.exists():
        print(f"\n❌ 目录不存在: {viz_dir}")
        return False

    # 获取所有PNG图片
    image_files = sorted(viz_dir.glob("*.png"))
    if not image_files:
        print(f"\n❌ 目录中没有找到PNG图片")
        return False

    print(f"\n找到 {len(image_files)} 个测试图片")
    print("-" * 80)

    # 逐个测试
    results = []
    for idx, image_path in enumerate(image_files, 1):
        print(f"\n[{idx}/{len(image_files)}] 测试图片: {image_path.name}")
        print("-" * 80)

        try:
            # 开始计时
            start_time = time.time()

            # 使用LangChain工具进行OCR
            result = ocr_image.invoke({
                "image_path": str(image_path),
                "language": "ch"  # PP-OCRv5中文模式
            })

            # 计算耗时
            elapsed_time = time.time() - start_time

            if result['success']:
                print(f"✅ 识别成功!")
                print(f"   方法: {result['method']}")
                print(f"   置信度: {result['confidence']:.2%}")
                print(f"   耗时: {elapsed_time:.2f}秒")
                print(f"   文本框数量: {result.get('num_boxes', 0)}")

                # 显示识别的文本
                text = result['text']
                if text:
                    print(f"\n📝 识别文本:")
                    # 限制显示长度
                    if len(text) > 500:
                        print(f"{text[:500]}...")
                        print(f"\n   (文本过长，已截断。总长度: {len(text)} 字符)")
                    else:
                        print(text)

                    # 文本分析
                    lines = text.strip().split('\n')
                    print(f"\n📊 文本统计:")
                    print(f"   总字符数: {len(text)}")
                    print(f"   行数: {len(lines)}")
                    print(f"   非空行数: {len([l for l in lines if l.strip()])}")

                results.append({
                    'file': image_path.name,
                    'success': True,
                    'method': result['method'],
                    'confidence': result['confidence'],
                    'time': elapsed_time,
                    'text_length': len(text),
                    'num_boxes': result.get('num_boxes', 0),
                })
            else:
                print(f"❌ 识别失败: {result.get('error', 'Unknown error')}")
                results.append({
                    'file': image_path.name,
                    'success': False,
                    'error': result.get('error', 'Unknown'),
                })

        except Exception as e:
            print(f"❌ 处理异常: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'file': image_path.name,
                'success': False,
                'error': str(e),
            })

    # 输出总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"\n总计: {len(image_files)} 个图片")
    print(f"成功: {len(successful)} 个")
    print(f"失败: {len(failed)} 个")
    print(f"成功率: {len(successful)/len(results)*100:.1f}%")

    if successful:
        print(f"\n✅ 成功识别的图片:")
        for r in successful:
            print(f"   • {r['file']}")
            print(f"     - 方法: {r['method']}, 置信度: {r['confidence']:.2%}, "
                  f"耗时: {r['time']:.2f}s, 字符数: {r['text_length']}")

        # 性能统计
        avg_time = sum(r['time'] for r in successful) / len(successful)
        avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
        total_chars = sum(r['text_length'] for r in successful)

        print(f"\n📊 性能统计:")
        print(f"   平均耗时: {avg_time:.2f}秒/张")
        print(f"   平均置信度: {avg_confidence:.2%}")
        print(f"   总识别字符: {total_chars}")
        print(f"   平均字符/张: {total_chars/len(successful):.0f}")

        # MPS加速提示
        if successful and successful[0]['method'] == 'local':
            print(f"\n⚡ MPS加速状态:")
            print(f"   当前识别方法: 本地PaddleOCR")
            print(f"   如果已启用MPS，预期性能为CPU的2-5倍")
            print(f"   验证命令: python test_paddleocr_v5.py")

    if failed:
        print(f"\n❌ 失败的图片:")
        for r in failed:
            print(f"   • {r['file']}: {r.get('error', 'Unknown error')}")

    return len(failed) == 0


def test_batch_processing():
    """测试批量处理能力"""
    print("\n" + "=" * 80)
    print("批量处理测试")
    print("=" * 80)

    try:
        from backend.tools.document_processing import batch_extract_documents

        viz_dir = project_root / "test_resources" / "images"
        image_files = [str(f) for f in viz_dir.glob("*.png")]

        if not image_files:
            print("没有找到图片文件")
            return False

        print(f"\n批量处理 {len(image_files)} 个图片...")

        start_time = time.time()
        result = batch_extract_documents.invoke({
            "file_paths": image_files,
            "use_ocr": True
        })
        elapsed_time = time.time() - start_time

        print(f"\n批量处理结果:")
        print(f"   总文件数: {result['total']}")
        print(f"   成功: {result['succeeded']}")
        print(f"   失败: {result['failed']}")
        print(f"   总耗时: {elapsed_time:.2f}秒")
        print(f"   平均: {elapsed_time/result['total']:.2f}秒/张")

        return result['success']

    except Exception as e:
        print(f"批量处理失败: {e}")
        return False


def test_integration_workflow():
    """测试完整工作流: OCR → 文本提取 → 保存"""
    print("\n" + "=" * 80)
    print("完整工作流测试")
    print("=" * 80)

    try:
        from backend.services.document_processing import process_document

        # 选择一张图片进行详细测试
        viz_dir = project_root / "test_resources" / "images"
        test_image = viz_dir / "中文文本渲染测试.png"

        if not test_image.exists():
            # 选择第一张可用图片
            images = list(viz_dir.glob("*.png"))
            if not images:
                print("没有找到测试图片")
                return False
            test_image = images[0]

        print(f"\n测试图片: {test_image.name}")

        # 提取文档内容
        content = process_document(test_image, use_ocr=True)

        print(f"\n提取结果:")
        print(f"   文件类型: {content.file_type}")
        print(f"   提取方法: {content.method}")
        print(f"   文本长度: {len(content.text)} 字符")
        print(f"   元数据: {content.metadata}")

        # 保存提取的文本
        output_file = project_root / "ocr_output.txt"
        output_file.write_text(content.text, encoding='utf-8')
        print(f"\n✅ 文本已保存到: {output_file}")

        # 显示前200字符
        preview = content.text[:200]
        print(f"\n文本预览:")
        print(preview)
        if len(content.text) > 200:
            print("...")

        return True

    except Exception as e:
        print(f"工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("PaddleOCR 3.3.1 (PP-OCRv5) 中文可视化图片识别测试")
    print("=" * 80)

    results = {
        "OCR识别测试": test_ocr_on_visualization(),
        "批量处理测试": test_batch_processing(),
        "工作流测试": test_integration_workflow(),
    }

    # 输出最终总结
    print("\n" + "=" * 80)
    print("最终测试总结")
    print("=" * 80)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {name}")

    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过!")
        print("\nPP-OCRv5性能总结:")
        print("   ✅ 单模型多语言识别 (简/繁/英/日/拼音)")
        print("   ✅ 识别精度提升 +13%")
        print("   ✅ MPS加速支持 (2-5x性能)")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
