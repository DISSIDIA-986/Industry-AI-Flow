#!/usr/bin/env python3
"""
Streamlit RAG 系统测试页面

功能:
1. 实时问答测试
2. 文档检索可视化
3. 性能监控
4. 设备信息展示
"""

import os
import sys
import time
from typing import Optional

import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import AIMessage, HumanMessage

from backend.agents.rag_agent import rag_agent
from backend.services.retrieval.hybrid_search import HybridRetriever
from backend.services.vectorstore import VectorStore
from backend.utils.device_manager import device_manager

# 页面配置
st.set_page_config(
    page_title="LangChain 1.0 RAG 测试系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .device-info {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 0.5rem;
    }
    .doc-card {
        background-color: #f9f9f9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# 初始化 session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "retriever" not in st.session_state:
    vectorstore = VectorStore()
    st.session_state.retriever = HybridRetriever(vectorstore)


# 侧边栏 - 系统信息
with st.sidebar:
    st.markdown("### 🖥️ 系统信息")

    # 设备信息
    with st.expander("设备配置", expanded=True):
        st.markdown(
            f"""
        **当前设备**: {device_manager.device_name}
        **设备类型**: `{device_manager.device_type.value}`
        **PyTorch**: v{__import__('torch').__version__}
        """
        )

        # 设备详情
        if device_manager.device_type.value == "mps":
            st.success("✅ 使用 Apple MPS 加速")
        elif device_manager.device_type.value == "cuda":
            st.success("✅ 使用 NVIDIA CUDA 加速")
        else:
            st.warning("⚠️ 使用 CPU (性能较慢)")

    # LLM 配置
    with st.expander("LLM 配置"):
        llm_provider = os.getenv("LLM_PROVIDER", "ollama")
        st.markdown(
            f"""
        **提供商**: {llm_provider}
        **模型**: {os.getenv('ZHIPU_MODEL' if llm_provider == 'zhipu' else 'OLLAMA_MODEL')}
        """
        )

    # 嵌入模型配置
    with st.expander("嵌入模型配置"):
        st.markdown(
            f"""
        **模型**: {os.getenv('EMBEDDING_MODEL', 'nomic-ai/nomic-embed-text-v1.5')}
        **维度**: {os.getenv('EMBEDDING_DIM', '768')}
        """
        )

    # 检索配置
    with st.expander("检索配置"):
        vector_weight = st.slider("向量检索权重", 0.0, 1.0, 0.7, 0.1)
        bm25_weight = 1.0 - vector_weight
        top_k = st.slider("返回文档数量", 1, 20, 5, 1)

        st.markdown(
            f"""
        **BM25 权重**: {bm25_weight:.1f}
        **检索策略**: 混合检索 + 重排序
        """
        )

    # 清空对话
    if st.button("🗑️ 清空对话历史", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# 主页面
st.markdown(
    '<div class="main-header">🤖 LangChain 1.0 RAG 测试系统</div>', unsafe_allow_html=True
)

# 统计信息
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("对话轮次", len(st.session_state.messages) // 2)

with col2:
    vectorstore = VectorStore()
    doc_count = vectorstore.get_document_count()
    st.metric("文档总数", doc_count)

with col3:
    chunk_count = vectorstore.get_chunk_count()
    st.metric("文档块总数", chunk_count)

with col4:
    avg_time = st.session_state.get("avg_response_time", 0)
    st.metric("平均响应 (秒)", f"{avg_time:.2f}")

st.markdown("---")

# 标签页
tab1, tab2, tab3 = st.tabs(["💬 问答测试", "🔍 检索测试", "📊 性能分析"])


# 标签页 1: 问答测试
with tab1:
    st.markdown("### 💬 智能问答")

    # 显示对话历史
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.markdown(msg.content)
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(msg.content)

    # 用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        # 添加用户消息
        st.session_state.messages.append(HumanMessage(content=prompt))

        with st.chat_message("user"):
            st.markdown(prompt)

        # Agent 回答
        with st.chat_message("assistant"):
            with st.spinner("🤔 思考中..."):
                start_time = time.time()

                try:
                    # 调用 RAG Agent
                    result = rag_agent.invoke({"messages": st.session_state.messages})

                    # 提取响应
                    assistant_message = result["messages"][-1]
                    response_time = time.time() - start_time

                    # 更新平均响应时间
                    if "response_times" not in st.session_state:
                        st.session_state.response_times = []
                    st.session_state.response_times.append(response_time)
                    st.session_state.avg_response_time = sum(
                        st.session_state.response_times
                    ) / len(st.session_state.response_times)

                    # 显示回答
                    st.markdown(assistant_message.content)

                    # 显示性能指标
                    st.caption(f"⏱️ 响应时间: {response_time:.2f}秒")

                    # 添加到消息历史
                    st.session_state.messages.append(assistant_message)

                except Exception as e:
                    st.error(f"❌ 错误: {str(e)}")
                    import traceback

                    with st.expander("查看详细错误"):
                        st.code(traceback.format_exc())


# 标签页 2: 检索测试
with tab2:
    st.markdown("### 🔍 文档检索测试")

    search_query = st.text_input("输入检索查询:", placeholder="例如: LangChain 1.0 的主要改进")

    if st.button("🔍 执行检索", use_container_width=True):
        if search_query:
            with st.spinner("检索中..."):
                start_time = time.time()

                try:
                    # 执行检索
                    results = st.session_state.retriever.search(
                        query=search_query,
                        top_k=top_k,
                        vector_weight=vector_weight,
                        bm25_weight=bm25_weight,
                    )

                    retrieval_time = time.time() - start_time

                    # 显示结果
                    st.success(
                        f"✅ 检索完成！用时 {retrieval_time:.2f}秒，找到 {len(results)} 个相关文档"
                    )

                    # 显示每个文档
                    for i, doc in enumerate(results, 1):
                        with st.container():
                            st.markdown(
                                f"""
                            <div class="doc-card">
                                <h4>📄 文档 {i}</h4>
                                <p><strong>来源:</strong> {doc.get('filename', 'Unknown')}</p>
                                <p><strong>融合得分:</strong> {doc.get('score', 0):.4f}</p>
                                <p><strong>内容:</strong></p>
                                <p style="color: #555;">{doc.get('content', '')}</p>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                except Exception as e:
                    st.error(f"❌ 检索失败: {str(e)}")
                    import traceback

                    with st.expander("查看详细错误"):
                        st.code(traceback.format_exc())
        else:
            st.warning("⚠️ 请输入检索查询")


# 标签页 3: 性能分析
with tab3:
    st.markdown("### 📊 性能分析")

    if "response_times" in st.session_state and st.session_state.response_times:
        import numpy as np
        import pandas as pd

        times = st.session_state.response_times

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 响应时间统计")
            st.metric("平均响应时间", f"{np.mean(times):.2f}秒")
            st.metric("最快响应", f"{np.min(times):.2f}秒")
            st.metric("最慢响应", f"{np.max(times):.2f}秒")
            st.metric("标准差", f"{np.std(times):.2f}秒")

        with col2:
            st.markdown("#### 响应时间分布")
            df = pd.DataFrame({"轮次": range(1, len(times) + 1), "响应时间(秒)": times})
            st.line_chart(df.set_index("轮次"))

        # 性能评级
        avg_time = np.mean(times)
        if avg_time < 5:
            rating = "优秀 🌟"
            color = "green"
        elif avg_time < 10:
            rating = "良好 ✅"
            color = "blue"
        elif avg_time < 20:
            rating = "一般 ⚠️"
            color = "orange"
        else:
            rating = "需要优化 ❌"
            color = "red"

        st.markdown(f"**性能评级**: :{color}[{rating}]")

    else:
        st.info("📊 暂无性能数据，请先进行问答测试")

    # 系统资源信息
    st.markdown("---")
    st.markdown("#### 🖥️ 系统资源")

    try:
        import psutil

        col1, col2, col3 = st.columns(3)

        with col1:
            cpu_percent = psutil.cpu_percent(interval=1)
            st.metric("CPU 使用率", f"{cpu_percent}%")

        with col2:
            memory = psutil.virtual_memory()
            st.metric("内存使用率", f"{memory.percent}%")

        with col3:
            disk = psutil.disk_usage("/")
            st.metric("磁盘使用率", f"{disk.percent}%")

    except ImportError:
        st.info("💡 安装 psutil 以查看系统资源: `pip install psutil`")


# 页脚
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #888; font-size: 0.9rem;">
    🤖 LangChain 1.0 RAG 系统 |
    使用 {device_name} 加速 |
    <a href="https://github.com/anthropics/claude-code" target="_blank">GitHub</a>
</div>
""".format(
        device_name=device_manager.device_name
    ),
    unsafe_allow_html=True,
)
