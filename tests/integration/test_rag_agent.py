#!/usr/bin/env python3
"""ENLangChain 1.0 RAG Agent"""

from langchain_core.messages import HumanMessage

from backend.agents.rag_agent import rag_agent


def test_agent_basic():
    """ENAgentEN"""
    print("=" * 60)
    print("EN1: AgentEN")
    print("=" * 60)

    # EN
    question = "EN:ENLangChain?"

    try:
        # ENAgent
        result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})

        print(f"\n✅ AgentEN!")
        print(f"\nEN: {question}")
        print(f"\nEN: {len(result['messages'])}")
        print(f"\nEN:")
        print(result["messages"][-1].content[:500])  # EN500EN

    except Exception as e:
        print(f"\n❌ AgentEN: {e}")
        import traceback

        traceback.print_exc()


def test_agent_with_tools():
    """ENAgentEN"""
    print("\n" + "=" * 60)
    print("EN2: AgentEN")
    print("=" * 60)

    # EN
    # ENAgentEN

    print("\n✅ AgentEN:")
    print(f"- EN: {len(rag_agent.get_graph().nodes)}")
    print(f"- AgentEN: {type(rag_agent)}")


def test_tools_independently():
    """EN(EN)"""
    print("\n" + "=" * 60)
    print("EN3: EN")
    print("=" * 60)

    from backend.tools.reranker import rerank_tool
    from backend.tools.retrieval import hybrid_retrieval_tool

    print(f"\n✅ hybrid_retrieval_tool:")
    print(f"  - EN: {hybrid_retrieval_tool.name}")
    print(f"  - EN: {hybrid_retrieval_tool.description[:100]}...")

    print(f"\n✅ rerank_tool:")
    print(f"  - EN: {rerank_tool.name}")
    print(f"  - EN: {rerank_tool.description[:100]}...")


if __name__ == "__main__":
    print("\n🚀 LangChain 1.0 RAG Agent EN\n")

    # EN
    test_tools_independently()

    # ENAgentEN
    test_agent_basic()

    # EN(EN)
    # test_agent_with_tools()

    print("\n" + "=" * 60)
    print("✅ EN!")
    print("=" * 60)
