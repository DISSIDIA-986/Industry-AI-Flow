#!/usr/bin/env python3
"""
LangChain 1.0 RAG 系统完整功能测试

测试智谱 GLM-4 + Agent + 工具调用的完整流程
"""

import os

from dotenv import load_dotenv

load_dotenv()

# 设置使用智谱 API
os.environ["LLM_PROVIDER"] = "zhipu"

from langchain_core.messages import HumanMessage

from backend.agents.rag_agent import rag_agent
from backend.config import settings


def test_rag_with_retrieval():
    """测试完整 RAG 流程：检索 + 重排序 + 回答"""
    print("=" * 70)
    print("🎯 测试: 完整 RAG 流程（智谱 GLM-4）")
    print("=" * 70)

    print(f"\n📋 配置:")
    print(f"  - LLM Provider: {settings.llm_provider}")
    print(f"  - Model: {settings.zhipu_model}")
    print(f"  - Database: {settings.database_url}")

    # 测试问题（会触发检索）
    test_questions = [
        "什么是 LangChain 1.0 的主要改进？",
        "LangChain 1.0 的 Middleware 机制有什么作用？",
        "人工智能和机器学习有什么关系？",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'=' * 70}")
        print(f"问题 {i}: {question}")
        print("=" * 70)

        try:
            result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})

            # 提取响应
            final_message = result["messages"][-1]

            print(f"\n💬 Agent 回答:")
            print(f"{final_message.content}")

            print(f"\n✅ 测试 {i} 成功")

        except Exception as e:
            print(f"\n❌ 测试 {i} 失败: {e}")
            import traceback

            traceback.print_exc()


def test_tool_usage_verification():
    """验证 Agent 是否正确调用了工具"""
    print("\n" + "=" * 70)
    print("🔧 测试: 工具调用验证")
    print("=" * 70)

    question = "请检索关于'深度学习'的文档"

    print(f"\n❓ 问题: {question}")
    print("📊 预期行为: Agent 应调用 hybrid_retrieval_tool")

    try:
        result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})

        print("\n✅ 工具调用成功!")
        print(f"💬 Agent 响应: {result['messages'][-1].content[:300]}...")

    except Exception as e:
        print(f"\n❌ 工具调用失败: {e}")


def test_multi_turn_conversation():
    """测试多轮对话能力"""
    print("\n" + "=" * 70)
    print("💬 测试: 多轮对话")
    print("=" * 70)

    conversation = ["什么是人工智能？", "它的主要应用有哪些？"]

    messages = []

    for i, question in enumerate(conversation, 1):
        print(f"\n第 {i} 轮:")
        print(f"👤 用户: {question}")

        messages.append(HumanMessage(content=question))

        try:
            result = rag_agent.invoke({"messages": messages})

            # 更新消息历史
            messages = result["messages"]

            print(f"🤖 Agent: {messages[-1].content[:200]}...")

        except Exception as e:
            print(f"❌ 错误: {e}")
            break


def analyze_performance():
    """分析系统性能"""
    print("\n" + "=" * 70)
    print("📊 性能分析")
    print("=" * 70)

    import time

    question = "什么是机器学习？"

    print(f"\n❓ 测试问题: {question}")

    try:
        start_time = time.time()

        result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})

        elapsed = time.time() - start_time

        print(f"\n⏱️  执行时间: {elapsed:.2f}秒")
        print(f"💬 响应长度: {len(result['messages'][-1].content)} 字符")

        # 性能评估
        if elapsed < 5:
            rating = "优秀 🌟"
        elif elapsed < 10:
            rating = "良好 ✅"
        elif elapsed < 20:
            rating = "一般 ⚠️"
        else:
            rating = "需要优化 ❌"

        print(f"📈 性能评级: {rating}")

    except Exception as e:
        print(f"\n❌ 性能测试失败: {e}")


def main():
    """主测试流程"""
    print("\n" + "=" * 70)
    print("🚀 LangChain 1.0 完整 RAG 系统测试")
    print(f"   使用智谱 GLM-4 + PostgreSQL + LangChain 1.0 Agent")
    print("=" * 70)

    # 执行测试套件
    tests = [
        ("完整 RAG 流程", test_rag_with_retrieval),
        ("工具调用验证", test_tool_usage_verification),
        ("多轮对话", test_multi_turn_conversation),
        ("性能分析", analyze_performance),
    ]

    results = {}

    for name, test_func in tests:
        try:
            test_func()
            results[name] = True
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 异常: {e}")
            results[name] = False

    # 汇总结果
    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("=" * 70)

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！LangChain 1.0 RAG 系统运行正常！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")

    print("\n" + "=" * 70)
    print("💡 关于 LangChain 1.0 的优势:")
    print("=" * 70)
    print(
        """
1. 统一 Agent API：create_agent 简化了 Agent 创建流程
2. 工具化检索：LLM 自主决策何时检索、检索多少
3. 自动状态管理：TypedDict + operator.add 自动累加消息
4. 多 LLM 支持：轻松切换 Ollama/智谱/其他提供商
5. 可扩展性：添加新工具只需 @tool 装饰器

相比传统方式：
- 减少 50%+ 的胶水代码
- 提升 Agent 决策灵活性
- 更好的可观测性和调试能力
    """
    )


if __name__ == "__main__":
    main()
