#!/usr/bin/env python3
"""批量导入文档脚本"""

import sys
import os
import time
from pathlib import Path

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.document_loader import load_document
from backend.services.chunker import chunk_text
from backend.services.embedder import embed_texts
from backend.services.vectorstore import VectorStore
from backend.config import settings


def import_documents(directory: str):
    """批量导入目录中的所有文档"""
    directory_path = Path(directory)
    if not directory_path.exists():
        print(f"❌ 目录不存在: {directory}")
        return

    # 获取所有支持的文档
    supported_formats = [".pdf", ".txt"]
    files = [
        f for f in directory_path.rglob("*")
        if f.is_file() and f.suffix in supported_formats
    ]

    if not files:
        print(f"❌ 目录中没有找到支持的文档 (pdf, txt)")
        return

    print(f"📁 找到 {len(files)} 个文档")
    print(f"📝 配置: chunk_size={settings.chunk_size}, overlap={settings.chunk_overlap}")
    print()

    vectorstore = VectorStore()
    start_time = time.time()
    success_count = 0
    total_chunks = 0

    for i, file_path in enumerate(files, 1):
        try:
            print(f"[{i}/{len(files)}] 处理: {file_path.name}")

            # 1. 加载文档
            text = load_document(str(file_path))
            print(f"  ✓ 提取文本: {len(text)} 字符")

            # 2. 分块
            chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
            print(f"  ✓ 分块完成: {len(chunks)} 块")

            # 3. 向量化
            embeddings = embed_texts(chunks)
            print(f"  ✓ 向量化完成: {len(embeddings)} 个向量")

            # 4. 存储到数据库
            doc_id = vectorstore.store_document_with_chunks(
                filename=file_path.name,
                filepath=str(file_path),
                chunks=chunks,
                embeddings=embeddings
            )
            print(f"  ✓ 存储成功: doc_id={doc_id}")

            success_count += 1
            total_chunks += len(chunks)

        except Exception as e:
            print(f"  ✗ 失败: {str(e)}")
            continue

        print()

    elapsed_time = time.time() - start_time

    print("=" * 60)
    print("📊 导入完成")
    print(f"成功: {success_count}/{len(files)} 文档")
    print(f"总块数: {total_chunks}")
    print(f"耗时: {elapsed_time:.2f} 秒 ({elapsed_time/60:.2f} 分钟)")
    print(f"速度: {len(files)/elapsed_time*60:.1f} 文档/分钟")
    print("=" * 60)

    # 验证数据库状态
    print()
    print("📊 数据库状态:")
    print(f"  文档总数: {vectorstore.get_document_count()}")
    print(f"  块总数: {vectorstore.get_chunk_count()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/import_docs.py <文档目录>")
        print("示例: python scripts/import_docs.py ./samples/")
        sys.exit(1)

    directory = sys.argv[1]
    import_documents(directory)
