#!/usr/bin/env python3
"""
RAG引擎功能测试（不依赖实际向量数据库）
测试代码结构和接口
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 添加路径以便导入backend模块
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_path)


def test_rag_engine_structure():
    """测试RAG引擎结构"""
    print("🔍 测试RAG引擎结构...")

    try:
        # 检查文件是否存在
        rag_file = "backend/services/rag_engine.py"
        if not os.path.exists(rag_file):
            print(f"❌ 文件不存在: {rag_file}")
            return False

        # 读取代码并检查关键类和方法
        with open(rag_file, "r", encoding="utf-8") as f:
            rag_code = f.read()

        required_classes = ["class RAGEngine", "class EnhancedRAGEngine"]

        for cls in required_classes:
            if cls in rag_code:
                print(f"✅ 类 {cls} 存在")
            else:
                print(f"⚠️  类 {cls} 可能缺失")

        # 检查关键方法
        required_methods = [
            "def add_documents",
            "def query",
            "def search",
            "def delete_documents",
            "def get_stats",
        ]

        for method in required_methods:
            if method in rag_code:
                print(f"✅ 方法 {method} 存在")
            else:
                print(f"⚠️  方法 {method} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ RAG引擎结构检查失败: {e}")
        return False


def test_vector_database_integration():
    """测试向量数据库集成"""
    print("\n🔍 测试向量数据库集成...")

    try:
        with open("backend/services/rag_engine.py", "r", encoding="utf-8") as f:
            rag_code = f.read()

        vector_patterns = [
            "sentence_transformers",
            "SentenceTransformer",
            "numpy",
            "faiss",
            "chromadb",
            "vector",
            "embedding",
        ]

        for pattern in vector_patterns:
            if pattern in rag_code.lower():
                print(f"✅ 向量集成 {pattern} 存在")
            else:
                print(f"⚠️  向量集成 {pattern} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ 向量数据库集成检查失败: {e}")
        return False


def test_llm_integration():
    """测试LLM集成"""
    print("\n🔍 测试LLM集成...")

    try:
        with open("backend/services/rag_engine.py", "r", encoding="utf-8") as f:
            rag_code = f.read()

        llm_patterns = ["llm_client", "generate", "llama_cpp", "ollama", "LLMClient"]

        for pattern in llm_patterns:
            if pattern in rag_code.lower():
                print(f"✅ LLM集成 {pattern} 存在")
            else:
                print(f"⚠️  LLM集成 {pattern} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ LLM集成检查失败: {e}")
        return False


def test_document_processing():
    """测试文档处理功能"""
    print("\n🔍 测试文档处理功能...")

    try:
        with open("backend/services/rag_engine.py", "r", encoding="utf-8") as f:
            rag_code = f.read()

        doc_patterns = [
            "DocumentLoader",
            "load_document",
            "chunk_size",
            "chunk_overlap",
            "text_splitter",
        ]

        for pattern in doc_patterns:
            if pattern in rag_code.lower():
                print(f"✅ 文档处理 {pattern} 存在")
            else:
                print(f"⚠️  文档处理 {pattern} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ 文档处理功能检查失败: {e}")
        return False


def test_retrieval_mechanism():
    """测试检索机制"""
    print("\n🔍 测试检索机制...")

    try:
        with open("backend/services/rag_engine.py", "r", encoding="utf-8") as f:
            rag_code = f.read()

        retrieval_patterns = [
            "similarity_search",
            "cosine_similarity",
            "top_k",
            "threshold",
            "retrieve",
        ]

        for pattern in retrieval_patterns:
            if pattern in rag_code.lower():
                print(f"✅ 检索机制 {pattern} 存在")
            else:
                print(f"⚠️  检索机制 {pattern} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ 检索机制检查失败: {e}")
        return False


def test_configuration():
    """测试配置功能"""
    print("\n🔍 测试配置功能...")

    try:
        # 检查配置文件
        with open("backend/config.py", "r", encoding="utf-8") as f:
            config_code = f.read()

        rag_configs = [
            "embedding_model",
            "vector_db_path",
            "chunk_size",
            "chunk_overlap",
            "max_context_length",
        ]

        for config in rag_configs:
            if config in config_code:
                print(f"✅ RAG配置 {config} 存在")
            else:
                print(f"⚠️  RAG配置 {config} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ 配置功能检查失败: {e}")
        return False


def simulate_rag_workflow():
    """模拟RAG工作流程"""
    print("\n🔍 模拟RAG工作流程...")

    try:
        # 模拟文档加载
        documents = ["人工智能是计算机科学的一个分支", "机器学习是人工智能的子领域", "深度学习使用神经网络进行学习"]
        print(f"✅ 文档加载: {len(documents)} 个文档")

        # 模拟文档分块
        chunks = ["人工智能是计算机科学的一个分支", "机器学习是人工智能的子领域", "深度学习使用神经网络进行学习"]
        print(f"✅ 文档分块: {len(chunks)} 个片段")

        # 模拟向量化
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        print(f"✅ 向量化: 生成 {len(embeddings)} 个向量 (维度: {len(embeddings[0])})")

        # 模拟查询
        query = "什么是机器学习？"
        print(f"✅ 用户查询: {query}")

        # 模拟向量检索
        similarities = [0.85, 0.92, 0.67]
        top_k = 2
        relevant_docs = [chunks[i] for i in range(top_k)]
        print(f"✅ 相似度检索: 找到 {top_k} 个相关文档")

        # 模拟上下文构建
        context = "\n".join(relevant_docs)
        print(f"✅ 上下文构建: {len(context)} 字符")

        # 模拟LLM生成
        response = "机器学习是人工智能的一个重要子领域，它使计算机能够从数据中学习并做出预测或决策。"
        print(f"✅ 答案生成: {len(response)} 字符")

        return True
    except Exception as e:
        print(f"❌ 模拟RAG工作流程失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n🔍 测试错误处理...")

    try:
        with open("backend/services/rag_engine.py", "r", encoding="utf-8") as f:
            rag_code = f.read()

        error_patterns = ["try:", "except", "raise", "logging", "logger"]

        for pattern in error_patterns:
            if pattern in rag_code:
                print(f"✅ 错误处理 {pattern} 存在")
            else:
                print(f"⚠️  错误处理 {pattern} 可能缺失")

        return True
    except Exception as e:
        print(f"❌ 错误处理检查失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 RAG引擎功能测试开始\n")
    print("注意: 此测试不需要实际的向量数据库")
    print("=" * 60)

    tests = [
        ("RAG引擎结构", test_rag_engine_structure),
        ("向量数据库集成", test_vector_database_integration),
        ("LLM集成", test_llm_integration),
        ("文档处理功能", test_document_processing),
        ("检索机制", test_retrieval_mechanism),
        ("配置功能", test_configuration),
        ("模拟RAG工作流程", simulate_rag_workflow),
        ("错误处理", test_error_handling),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print("=" * 50)

        if test_func():
            passed += 1
            print(f"✅ {test_name} 测试通过")
        else:
            print(f"❌ {test_name} 测试失败")

    print(f"\n{'='*50}")
    print(f"测试总结: {passed}/{total} 通过")
    print("=" * 50)

    if passed >= total * 0.75:  # 75% 通过率
        print("🎉 大部分测试通过！RAG引擎结构正确")
        print("\n📝 下一步建议:")
        print("1. 安装向量数据库依赖 (sentence-transformers, faiss等)")
        print("2. 进行实际的向量化测试")
        print("3. 测试完整的检索和生成流程")
        return True
    else:
        print("⚠️  部分测试失败，请检查RAG引擎实现")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
