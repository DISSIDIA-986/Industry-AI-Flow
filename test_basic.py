#!/usr/bin/env python3
"""基础功能测试（不需要 pgvector）"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("测试基础功能")
print("=" * 60)
print()

# 测试 1: 导入模块
print("1. 测试模块导入...")
try:
    from backend.config import settings
    print("   ✅ backend.config")

    from backend.services.document_loader import load_txt
    print("   ✅ backend.services.document_loader")

    from backend.services.chunker import chunk_text
    print("   ✅ backend.services.chunker")

    from backend.services.embedder import embed_single_text
    print("   ✅ backend.services.embedder")

    from backend.services.ollama_client import OllamaClient
    print("   ✅ backend.services.ollama_client")

    print("   ✅ 所有模块导入成功")
except Exception as e:
    print(f"   ❌ 模块导入失败: {e}")
    sys.exit(1)

print()

# 测试 2: 配置
print("2. 测试配置...")
print(f"   数据库: {settings.postgres_db}")
print(f"   Ollama模型: {settings.ollama_model}")
print(f"   嵌入模型: {settings.embedding_model}")
print(f"   分块大小: {settings.chunk_size}")
print("   ✅ 配置加载成功")

print()

# 测试 3: 文档处理
print("3. 测试文档处理...")
test_text = "这是一个测试文档。RAG系统可以检索增强生成答案。"
chunks = chunk_text(test_text, chunk_size=20, overlap=5)
print(f"   原文: {test_text}")
print(f"   分块: {len(chunks)} 块")
for i, chunk in enumerate(chunks):
    print(f"     [{i}] {chunk}")
print("   ✅ 文档分块成功")

print()

# 测试 4: 向量嵌入
print("4. 测试向量嵌入（需要下载模型，首次运行较慢）...")
try:
    embedding = embed_single_text("测试文本")
    print(f"   向量维度: {len(embedding)}")
    print(f"   前5个值: {embedding[:5]}")
    print("   ✅ 向量嵌入成功")
except Exception as e:
    print(f"   ❌ 向量嵌入失败: {e}")

print()

# 测试 5: Ollama 客户端
print("5. 测试 Ollama 连接...")
try:
    client = OllamaClient()
    print(f"   Ollama地址: {client.base_url}")
    print(f"   模型: {client.model}")

    # 简单测试
    answer = client.generate("1+1等于几？请只回答数字。")
    print(f"   测试问题: 1+1等于几？")
    print(f"   LLM回答: {answer[:100]}...")
    print("   ✅ Ollama连接成功")
except Exception as e:
    print(f"   ❌ Ollama连接失败: {e}")

print()
print("=" * 60)
print("基础功能测试完成")
print("=" * 60)
print()
print("⚠️  下一步: 安装 pgvector 扩展后，可以运行完整的 RAG 测试")
print("   参考: INSTALL_PGVECTOR.md")
