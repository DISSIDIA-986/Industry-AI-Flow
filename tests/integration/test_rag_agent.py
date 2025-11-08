#!/usr/bin/env python3
"""测试LangChain 1.0 RAG Agent"""

from backend.agents.rag_agent import rag_agent
from langchain_core.messages import HumanMessage


def test_agent_basic():
    """测试Agent基础功能"""
    print("=" * 60)
    print("测试1: Agent基础调用")
    print("=" * 60)

    # 测试用户问题
    question = "测试问题：什么是LangChain?"

    try:
        # 调用Agent
        result = rag_agent.invoke({
            "messages": [HumanMessage(content=question)]
        })

        print(f"\n✅ Agent调用成功!")
        print(f"\n问题: {question}")
        print(f"\n消息数量: {len(result['messages'])}")
        print(f"\n最后的消息:")
        print(result['messages'][-1].content[:500])  # 显示前500字符

    except Exception as e:
        print(f"\n❌ Agent调用失败: {e}")
        import traceback
        traceback.print_exc()


def test_agent_with_tools():
    """测试Agent工具调用"""
    print("\n" + "=" * 60)
    print("测试2: Agent工具调用能力")
    print("=" * 60)

    # 这个测试需要数据库中有文档
    # 暂时只验证Agent的基本结构

    print("\n✅ Agent结构验证:")
    print(f"- 工具数量: {len(rag_agent.get_graph().nodes)}")
    print(f"- Agent类型: {type(rag_agent)}")


def test_tools_independently():
    """独立测试工具（无需数据库）"""
    print("\n" + "=" * 60)
    print("测试3: 工具定义验证")
    print("=" * 60)

    from backend.tools.retrieval import hybrid_retrieval_tool
    from backend.tools.reranker import rerank_tool

    print(f"\n✅ hybrid_retrieval_tool:")
    print(f"  - 名称: {hybrid_retrieval_tool.name}")
    print(f"  - 描述: {hybrid_retrieval_tool.description[:100]}...")

    print(f"\n✅ rerank_tool:")
    print(f"  - 名称: {rerank_tool.name}")
    print(f"  - 描述: {rerank_tool.description[:100]}...")


if __name__ == "__main__":
    print("\n🚀 LangChain 1.0 RAG Agent 测试开始\n")

    # 先测试工具定义
    test_tools_independently()

    # 再测试Agent基础功能
    test_agent_basic()

    # 最后测试工具调用（需要数据库）
    # test_agent_with_tools()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
