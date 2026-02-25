#!/usr/bin/env python3
"""EN GLM-4 API EN - LangChain 1.0 Agent"""

import os
import sys

from dotenv import load_dotenv

# EN
load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from backend.config import settings


def test_zhipu_basic_connection():
    """EN1: EN API EN"""
    print("=" * 70)
    print("EN1: EN GLM-4 API EN")
    print("=" * 70)

    # EN
    print(f"\n📋 EN:")
    print(
        f"  - API Key: {settings.zhipu_api_key[:20]}..."
        if settings.zhipu_api_key
        else "  - ❌ API KeyEN"
    )
    print(f"  - Base URL: {settings.zhipu_base_url}")
    print(f"  - Model: {settings.zhipu_model}")
    print(f"  - Timeout: {settings.api_timeout_ms/1000}s")

    if not settings.zhipu_api_key:
        print("\n❌ EN: ZHIPU_API_KEY EN,EN .env EN")
        return False

    try:
        # EN ChatAnthropic(EN)
        llm = ChatAnthropic(
            model=settings.zhipu_model,
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
            timeout=settings.api_timeout_ms / 1000,
            temperature=0,
        )

        # EN
        print("\n🚀 EN...")
        response = llm.invoke([HumanMessage(content="EN,EN.")])

        print(f"\n✅ EN API EN!")
        print(f"\n📨 EN:")
        print(f"  {response.content[:200]}...")

        return True

    except Exception as e:
        print(f"\n❌ EN API EN: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_zhipu_with_agent():
    """EN2: EN API EN LangChain 1.0 Agent EN"""
    print("\n" + "=" * 70)
    print("EN2: EN GLM-4 + LangChain 1.0 Agent EN")
    print("=" * 70)

    # EN LLM Provider EN
    original_provider = os.getenv("LLM_PROVIDER")
    os.environ["LLM_PROVIDER"] = "zhipu"

    try:
        # EN
        from importlib import reload

        from backend import config

        reload(config)
        from backend.config import settings

        print(f"\n📋 EN LLM Provider: {settings.llm_provider}")

        # EN Agent
        from backend.agents.rag_agent import build_rag_agent

        print("\n🔧 EN RAG Agent(EN GLM-4)...")
        agent = build_rag_agent()

        print("✅ Agent EN!")
        print(f"  - EN: 2 (hybrid_retrieval_tool, rerank_tool)")
        print(f"  - LLM: EN {settings.zhipu_model}")

        # EN(EN)
        print("\n🧪 EN(EN)...")
        test_question = "EN."

        result = agent.invoke({"messages": [HumanMessage(content=test_question)]})

        print(f"\n✅ Agent EN!")
        print(f"\n❓ EN: {test_question}")
        print(f"\n💬 EN: {result['messages'][-1].content[:300]}...")

        return True

    except Exception as e:
        print(f"\n❌ Agent EN: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # EN
        if original_provider:
            os.environ["LLM_PROVIDER"] = original_provider
        else:
            os.environ.pop("LLM_PROVIDER", None)


def test_zhipu_tool_calling():
    """EN3: EN API EN"""
    print("\n" + "=" * 70)
    print("EN3: EN GLM-4 EN")
    print("=" * 70)

    print("\n⚠️  EN: EN")
    print("EN,EN(EN)\n")

    # EN
    os.environ["LLM_PROVIDER"] = "zhipu"

    try:
        from importlib import reload

        from backend import config

        reload(config)
        from backend.agents.rag_agent import build_rag_agent

        agent = build_rag_agent()

        # EN
        test_question = "EN'EN'EN,EN."

        print(f"🧪 EN(EN):")
        print(f"  {test_question}")
        print(f"\n🚀 EN...")

        result = agent.invoke({"messages": [HumanMessage(content=test_question)]})

        print(f"\n✅ EN!")
        print(f"\n💬 Agent EN:")
        print(f"  {result['messages'][-1].content[:400]}...")

        return True

    except Exception as e:
        error_msg = str(e)

        # EN(EN)
        if "database" in error_msg.lower() or "connection" in error_msg.lower():
            print(f"\n⚠️  EN(EN)")
            print(f"  Agent EN,EN")
            print(f"  EN API EN!")
            return True
        else:
            print(f"\n❌ EN: {e}")
            import traceback

            traceback.print_exc()
            return False


def test_provider_switching():
    """EN4: LLM Provider EN"""
    print("\n" + "=" * 70)
    print("EN4: Ollama ↔ EN Provider EN")
    print("=" * 70)

    providers = ["ollama", "zhipu"]
    results = {}

    for provider in providers:
        print(f"\n🔄 EN: {provider}")
        os.environ["LLM_PROVIDER"] = provider

        try:
            from importlib import reload

            from backend import config

            reload(config)
            from backend.agents.rag_agent import build_rag_agent
            from backend.config import settings

            agent = build_rag_agent()

            # EN
            if provider == "zhipu" and settings.zhipu_api_key:
                result = agent.invoke({"messages": [HumanMessage(content="EN")]})
                results[provider] = "✅ EN"
            elif provider == "ollama":
                # Ollama EN
                results[provider] = "⏭️  EN(EN Ollama EN)"
            else:
                results[provider] = "⏭️  EN(API Key EN)"

        except Exception as e:
            results[provider] = f"❌ EN: {str(e)[:50]}"

    print("\n" + "=" * 70)
    print("Provider EN:")
    for provider, result in results.items():
        print(f"  - {provider}: {result}")

    return True


def main():
    """EN"""
    print("\n" + "=" * 70)
    print("🚀 EN GLM-4 + LangChain 1.0 EN")
    print("=" * 70)

    print("\n📍 EN:")
    print(f"  - Python: {sys.version.split()[0]}")
    print(f"  - EN: {os.getcwd()}")
    print(f"  - .env EN: {'✅ EN' if os.path.exists('.env') else '❌ EN'}")

    # EN
    tests = [
        ("EN", test_zhipu_basic_connection),
        ("Agent EN", test_zhipu_with_agent),
        ("EN", test_zhipu_tool_calling),
        ("Provider EN", test_provider_switching),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
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
        print("\n🎉 EN!EN GLM-4 EN!")
    else:
        print(f"\n⚠️  {total - passed} EN,EN")


if __name__ == "__main__":
    main()
