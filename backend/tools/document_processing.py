"""
LangChain 1.0 文档处理工具

支持文档OCR、内容提取和预处理
"""

from pathlib import Path
from typing import Annotated, Optional

from langchain_core.tools import tool

from backend.services.document_processing import ocr_processor, process_document


@tool
def extract_document_text(
    file_path: Annotated[str, "Document file path"],
    use_ocr: Annotated[bool, "Whether to use OCR, default True"] = True,
) -> dict:
    """
    从文档中提取文本内容

    支持的文档格式:
    - PDF (.pdf)
    - Word (.docx, .doc)
    - Excel (.xlsx, .xls)
    - 文本 (.txt, .md)
    - 图像 (.png, .jpg, .jpeg, .bmp, .tiff)

    处理流程:
    1. 自动检测文档类型
    2. 使用适当的方法提取内容
    3. 对于图像和无法提取文本的PDF,使用OCR
    4. 返回提取的文本和元数据

    Args:
        file_path: 文档文件的绝对路径
        use_ocr: Whether to use OCR处理图像和扫描PDF

    Returns:
        提取结果字典,包含:
        - success: 是否成功
        - text: 提取的文本内容
        - file_type: 文档类型
        - method: 使用的提取方法
        - metadata: 文档元数据
        - error: 错误信息(如果失败)

    Examples:
        >>> # 提取PDF文本
        >>> result = extract_document_text("/path/to/document.pdf")
        >>> print(result['text'])

        >>> # 提取图像中的文字
        >>> result = extract_document_text("/path/to/image.png", use_ocr=True)
        >>> print(f"识别到文字: {result['text']}")
    """
    try:
        # 检查文件存在
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "text": "",
                "file_type": "unknown",
                "method": "none",
                "metadata": {},
            }

        # 提取内容
        content = process_document(file_path, use_ocr=use_ocr)

        return {
            "success": True,
            "text": content.text,
            "file_type": content.file_type,
            "method": content.method,
            "metadata": content.metadata,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "file_type": "unknown",
            "method": "failed",
            "metadata": {},
        }


@tool
def ocr_image(
    image_path: Annotated[str, "Image file path"],
    language: Annotated[str, "Language code, default 'en' (English)"] = "ch",
) -> dict:
    """
    对图像进行OCR文字识别

    支持语言:
    - 'ch': 中文
    - 'en': 英文
    - 'chinese_cht': 繁体中文

    处理方式:
    - 优先使用本地PaddleOCR(支持MPS/CUDA加速)
    - 失败时降级到百度OCR API

    Args:
        image_path: Image file path
        language: 识别语言

    Returns:
        OCR结果字典,包含:
        - success: 是否成功
        - text: 识别的文本
        - confidence: 平均置信度(0-1)
        - method: 使用的方法(local/api)
        - language: 语言
        - error: 错误信息(如果失败)

    Examples:
        >>> # 识别中文图像
        >>> result = ocr_image("/path/to/chinese_doc.png", language="ch")
        >>> print(f"识别文字: {result['text']}")
        >>> print(f"置信度: {result['confidence']:.2%}")

        >>> # 识别英文图像
        >>> result = ocr_image("/path/to/english_doc.png", language="en")
    """
    if ocr_processor is None:
        return {
            "success": False,
            "error": "OCR processor unavailable, please check PaddleOCR installation",
            "text": "",
            "confidence": 0.0,
            "method": "none",
            "language": language,
        }

    try:
        # 检查文件存在
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            return {
                "success": False,
                "error": f"Image file not found: {image_path}",
                "text": "",
                "confidence": 0.0,
                "method": "none",
                "language": language,
            }

        # 执行OCR
        # 需要重新初始化以支持不同语言
        from backend.services.document_processing.ocr_processor import OCRProcessor

        processor = OCRProcessor(lang=language)
        result = processor.process(image_path)

        return {
            "success": True,
            "text": result.text,
            "confidence": result.confidence,
            "method": result.method,
            "language": result.language,
            "num_boxes": len(result.boxes),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "confidence": 0.0,
            "method": "failed",
            "language": language,
        }


@tool
def batch_extract_documents(
    file_paths: Annotated[list[str], "List of document file paths"],
    use_ocr: Annotated[bool, "Whether to use OCR"] = True,
) -> dict:
    """
    批量提取多个文档的文本内容

    Args:
        file_paths: List of document file paths
        use_ocr: Whether to use OCR

    Returns:
        批量提取结果字典,包含:
        - success: 是否全部成功
        - results: 每个文件的提取结果列表
        - total: 总文件数
        - succeeded: 成功数
        - failed: 失败数

    Examples:
        >>> files = ["/path/to/doc1.pdf", "/path/to/doc2.docx"]
        >>> result = batch_extract_documents(files)
        >>> print(f"成功: {result['succeeded']}/{result['total']}")
    """
    results = []
    succeeded = 0
    failed = 0

    for file_path in file_paths:
        result = extract_document_text.invoke(
            {"file_path": file_path, "use_ocr": use_ocr}
        )

        results.append(
            {
                "file_path": file_path,
                **result,
            }
        )

        if result["success"]:
            succeeded += 1
        else:
            failed += 1

    return {
        "success": failed == 0,
        "results": results,
        "total": len(file_paths),
        "succeeded": succeeded,
        "failed": failed,
    }
