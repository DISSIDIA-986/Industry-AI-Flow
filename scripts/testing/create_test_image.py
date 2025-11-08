"""
创建OCR测试图片
生成包含中英文文本的测试图片
"""

import os

from PIL import Image, ImageDraw, ImageFont


def create_test_image():
    """创建测试图片"""
    # 创建白色背景图片
    width, height = 800, 400
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # 测试文本（中英文混合）
    texts = [
        "Hello World",
        "你好世界",
        "PaddleOCR 3.3.1 Test",
        "Industry AI Flow",
        "图文识别测试 OCR Recognition",
    ]

    # 使用系统默认字体绘制文本
    y_offset = 50
    for text in texts:
        try:
            # 使用较大字号
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 40)
        except:
            # 如果找不到字体，使用默认字体
            font = ImageFont.load_default()

        # 绘制文本
        draw.text((50, y_offset), text, fill="black", font=font)
        y_offset += 70

    # 保存图片
    output_path = "test_resources/images/test_ocr.png"
    os.makedirs("test_resources/images", exist_ok=True)
    image.save(output_path)
    print(f"✅ 测试图片已创建: {output_path}")

    return output_path


if __name__ == "__main__":
    create_test_image()
