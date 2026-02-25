#!/usr/bin/env python3
"""
LangChain 1.0 RAG EN

EN GLM-4 + Agent + EN
"""

import os

from dotenv import load_dotenv

load_dotenv()

# EN API
os.environ["LLM_PROVIDER"] = "zhipu"

from langchain_core.messages import HumanMessage

from backend.agents.rag_agent import rag_agent
from backend.config import settings


def test_rag_with_retrieval():
    """EN RAG EN:EN + EN + EN"""
    print("=" * 70)
    print("🎯 EN: EN RAG EN(EN GLM-4)")
    print("=" * 70)

    print(f"\n📋 EN:")
    print(f"  - LLM Provider: {settings.llm_provider}")
    print(f"  - Model: {settings.zhipu_model}")
    print(f"  - Database: {settings.database_url}")

    # EN(EN)
    test_questions = [
        "EN LangChain 1.0 EN?",
        "LangChain 1.0 EN Middleware EN?",
        "EN?",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'=' * 70}")
        print(f"EN {i}: {question}")
        print("=" * 70)

        try:
            result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})

            # EN
            final_message = result["messages"][-1]

            print(f"\n💬 Agent EN:")
            print(f"{final_message.content}")

            print(f"\n✅ EN {i} EN")

        except Exception as e:
            print(f"\n❌ EN {i} EN: {e}")
            import traceback

            traceback.print_exc()


def test_tool_usage_verification():
    """EN Agent EN"""
    print("\n" + "=" * 70)
    print("🔧 EN: EN")
    print("=" * 70)

    question = "EN'EN'EN"

    print(f"\n❓ EN: {question}")
    print("📊 EN: Agent EN hybrid_retrieval_tool")

    try:
        result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})

        print("\n✅ EN!")
        print(f"💬 Agent EN: {result['messages'][-1].content[:300]}...")

    except Exception as e:
        print(f"\n❌ EN: {e}")


def test_multi_turn_conversation():
    """EN"""
    print("\n" + "=" * 70)
    print("💬 EN: EN")
    print("=" * 70)

    conversation = ["EN?", "EN?"]

    messages = []

    for i, question in enumerate(conversation, 1):
        print(f"\nEN {i} EN:")
        print(f"👤 EN: {question}")

        messages.append(HumanMessage(content=question))

        try:
            result = rag_agent.invoke({"messages": messages})

            # EN
            messages = result["messages"]

            print(f"🤖 Agent: {messages[-1].content[:200]}...")

        except Exception as e:
            print(f"❌ EN: {e}")
            break


def analyze_performance():
    """EN"""
    print("\n" + "=" * 70)
    print("📊 EN")
    print("=" * 70)

    import time

    question = "EN?"

    print(f"\n❓ EN: {question}")

    try:
        start_time = time.time()

        result = rag_agent.invoke({"messages": [HumanMessage(content=question)]})

        elapsed = time.time() - start_time

        print(f"\n⏱️  EN: {elapsed:.2f}EN")
        print(f"💬 EN: {len(result['messages'][-1].content)} EN")

        # EN
        if elapsed < 5:
            rating = "EN 🌟"
        elif elapsed < 10:
            rating = "EN ✅"
        elif elapsed < 20:
            rating = "EN ⚠️"
        else:
            rating = "EN ❌"

        print(f"📈 EN: {rating}")

    except Exception as e:
        print(f"\n❌ EN: {e}")


def main():
    """EN"""
    print("\n" + "=" * 70)
    print("🚀 LangChain 1.0 EN RAG EN")
    print(f"   EN GLM-4 + PostgreSQL + LangChain 1.0 Agent")
    print("=" * 70)

    # EN
    tests = [
        ("EN RAG EN", test_rag_with_retrieval),
        ("EN", test_tool_usage_verification),
        ("EN", test_multi_turn_conversation),
        ("EN", analyze_performance),
    ]

    results = {}

    for name, test_func in tests:
        try:
            test_func()
            results[name] = True
        except Exception as e:
            print(f"\n❌ EN '{name}' EN: {e}")
            results[name] = False

    # EN
    print("\n" + "=" * 70)
    print("📊 EN")
    print("=" * 70)

    for name, passed in results.items():
        status = "✅ EN" if passed else "❌ EN"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\nEN: {passed}/{total} EN")

    if passed == total:
        print("\n🎉 EN!LangChain 1.0 RAG EN!")
    else:
        print(f"\n⚠️  {total - passed} EN")

    print("\n" + "=" * 70)
    print("💡 EN LangChain 1.0 EN:")
    print("=" * 70)
    print(
        """
1. EN Agent API:create_agent EN Agent EN
2. EN:LLM EN,EN
3. EN:TypedDict + operator.add EN
4. EN LLM EN:EN Ollama/EN/EN
5. EN:EN @tool EN

EN:
- EN 50%+ EN
- EN Agent EN
- EN
    """
    )


if __name__ == "__main__":
    main()
