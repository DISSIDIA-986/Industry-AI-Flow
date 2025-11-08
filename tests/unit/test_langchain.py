#!/usr/bin/env python3
"""Test LangChain integration"""

from langchain_ollama import ChatOllama


def test_ollama_client():
    llm = ChatOllama(model="llama3.2")
    response = llm.invoke("Hello")
    print(response)
