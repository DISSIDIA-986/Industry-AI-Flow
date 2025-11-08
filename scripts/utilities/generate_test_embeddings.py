#!/usr/bin/env python3
"""为测试数据生成向量嵌入"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.embedder import embed_texts
from backend.services.vectorstore import VectorStore


def generate_embeddings():
    """为数据库中的测试数据生成向量嵌入"""
    print("=" * 70)
    print("📊 生成测试数据向量嵌入")
    print("=" * 70)

    vectorstore = VectorStore()
    conn = vectorstore.get_connection()
    cur = conn.cursor()

    try:
        # 获取所有未生成向量的文档块
        print("\n🔍 查找未生成向量的文档块...")
        cur.execute(
            """
            SELECT id, content
            FROM document_chunks
            WHERE embedding IS NULL
        """
        )

        chunks = cur.fetchall()
        print(f"找到 {len(chunks)} 个文档块需要生成向量")

        if not chunks:
            print("✅ 所有文档块已有向量嵌入")
            return

        # 批量生成向量
        print("\n🤖 生成向量嵌入（使用 sentence-transformers）...")
        chunk_ids = [chunk[0] for chunk in chunks]
        texts = [chunk[1] for chunk in chunks]

        embeddings = embed_texts(texts)
        print(f"✅ 成功生成 {len(embeddings)} 个向量")

        # 更新数据库
        print("\n💾 更新数据库...")
        for chunk_id, embedding in zip(chunk_ids, embeddings):
            cur.execute(
                """
                UPDATE document_chunks
                SET embedding = %s
                WHERE id = %s
            """,
                (embedding, chunk_id),
            )

        conn.commit()
        print("✅ 数据库更新完成")

        # 验证
        print("\n🔍 验证向量嵌入...")
        cur.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(embedding) as with_embedding
            FROM document_chunks
        """
        )

        total, with_embedding = cur.fetchone()
        print(f"  - 总文档块数: {total}")
        print(f"  - 已有向量: {with_embedding}")
        print(f"  - 覆盖率: {with_embedding/total*100:.1f}%")

        if with_embedding == total:
            print("\n🎉 所有测试数据向量嵌入生成完成！")
        else:
            print(f"\n⚠️  仍有 {total - with_embedding} 个文档块未生成向量")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    try:
        generate_embeddings()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
