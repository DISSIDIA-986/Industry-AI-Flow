import fitz  # PyMuPDF


def load_pdf(file_path: str) -> str:
    """提取PDF文本（使用PyMuPDF）"""
    doc = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def load_txt(file_path: str) -> str:
    """加载纯文本文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def load_document(file_path: str) -> str:
    """根据文件扩展名加载文档"""
    if file_path.endswith(".pdf"):
        return load_pdf(file_path)
    elif file_path.endswith(".txt"):
        return load_txt(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")
