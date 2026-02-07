"""
Prompt管理可视化界面 - Streamlit应用
提供友好的Web界面用于Prompt的创建、编辑、测试和监控
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# 模拟导入（实际使用时需要正确导入）
# from backend.services.prompt_manager import PromptManager, PromptVariable
# from backend.config import get_database_pool

# 模拟数据（用于演示）
DEMO_PROMPTS = [
    {
        "id": str(uuid.uuid4()),
        "name": "rag_response",
        "category": "RAG",
        "subcategory": "response",
        "version": "1.2.0",
        "content": """基于以下检索到的文档，请回答用户问题：

检索到的文档：
{{context}}

用户问题：{{query}}

请提供准确、有用的回答。如果文档中没有相关信息，请明确说明。""",
        "variables": [
            {"name": "context", "type": "string", "required": True},
            {"name": "query", "type": "string", "required": True},
            {"name": "language", "type": "string", "required": False, "default": "zh-CN"}
        ],
        "performance_score": 0.85,
        "usage_count": 1250,
        "success_count": 1062,
        "tags": ["RAG", "Response"],
        "created_at": datetime.now() - timedelta(days=15),
        "updated_at": datetime.now() - timedelta(days=2)
    },
    {
        "id": str(uuid.uuid4()),
        "name": "data_analysis",
        "category": "Data-Analysis",
        "subcategory": "EDA",
        "version": "2.1.0",
        "content": """请对提供的数据进行探索性数据分析（EDA）：

数据集信息：
{{dataset_info}}

分析目标：
{{analysis_goals}}

请包含以下分析：
1. 数据概览和基本统计
2. 数据质量评估
3. 分布分析
4. 相关性分析
5. 异常值检测
6. 关键发现和洞察

使用{{language}}生成分析报告。""",
        "variables": [
            {"name": "dataset_info", "type": "string", "required": True},
            {"name": "analysis_goals", "type": "string", "required": True},
            {"name": "language", "type": "string", "required": False, "default": "中文"}
        ],
        "performance_score": 0.92,
        "usage_count": 856,
        "success_count": 788,
        "tags": ["Data-Analysis", "EDA"],
        "created_at": datetime.now() - timedelta(days=30),
        "updated_at": datetime.now() - timedelta(days=5)
    }
]

# 配置页面
st.set_page_config(
    page_title="Prompt管理平台",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 2rem 0;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 2rem;
}

.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid #667eea;
}

.prompt-card {
    background: white;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
    border-left: 4px solid #764ba2;
}

.variable-tag {
    display: inline-block;
    background: #f0f2f6;
    color: #2d3748;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    margin: 0.25rem;
    font-size: 0.875rem;
}

.category-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.875rem;
    font-weight: 600;
    color: white;
}
</style>
""", unsafe_allow_html=True)


class MockPromptManager:
    """模拟Prompt管理器"""

    def __init__(self):
        self.prompts = DEMO_PROMPTS.copy()

    async def list_prompts(self, category=None, is_active=True):
        """获取Prompt列表"""
        prompts = self.prompts
        if category:
            prompts = [p for p in prompts if p["category"] == category]
        return prompts

    async def get_prompt(self, prompt_id):
        """获取单个Prompt"""
        for prompt in self.prompts:
            if prompt["id"] == prompt_id:
                return prompt
        return None

    async def create_prompt(self, prompt_data):
        """创建Prompt"""
        new_prompt = {
            "id": str(uuid.uuid4()),
            "name": prompt_data["name"],
            "category": prompt_data["category"],
            "subcategory": prompt_data.get("subcategory"),
            "version": prompt_data.get("version", "1.0.0"),
            "content": prompt_data["content"],
            "variables": prompt_data.get("variables", []),
            "performance_score": 0.0,
            "usage_count": 0,
            "success_count": 0,
            "tags": prompt_data.get("tags", []),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        self.prompts.append(new_prompt)
        return new_prompt

    async def update_prompt(self, prompt_id, update_data):
        """更新Prompt"""
        for i, prompt in enumerate(self.prompts):
            if prompt["id"] == prompt_id:
                self.prompts[i].update(update_data)
                self.prompts[i]["updated_at"] = datetime.now()
                return self.prompts[i]
        return None

    async def delete_prompt(self, prompt_id):
        """删除Prompt"""
        self.prompts = [p for p in self.prompts if p["id"] != prompt_id]
        return True

    def render_template(self, content, variables):
        """渲染模板"""
        try:
            for key, value in variables.items():
                content = content.replace(f"{{{{{key}}}}}", str(value))
            return content
        except Exception:
            return content

    def get_categories(self):
        """获取所有分类"""
        return list(set(p["category"] for p in self.prompts))


# 初始化
@st.cache_resource
def init_prompt_manager():
    """初始化Prompt管理器"""
    return MockPromptManager()


def main():
    """主应用"""
    prompt_manager = init_prompt_manager()

    # 侧边栏导航
    st.sidebar.title("🧠 Prompt管理")

    page = st.sidebar.radio(
        "选择功能页面",
        ["📊 仪表板", "📝 Prompt列表", "➕ 创建Prompt", "✏️ 编辑Prompt", "🧪 测试Prompt", "📈 性能分析"]
    )

    # 主标题
    st.markdown("""
    <div class="main-header">
        <h1>🧠 AI Prompt管理平台</h1>
        <p>集中管理、版本控制、性能监控的Prompt管理系统</p>
    </div>
    """, unsafe_allow_html=True)

    if page == "📊 仪表板":
        show_dashboard(prompt_manager)
    elif page == "📝 Prompt列表":
        show_prompt_list(prompt_manager)
    elif page == "➕ 创建Prompt":
        show_create_prompt(prompt_manager)
    elif page == "✏️ 编辑Prompt":
        show_edit_prompt(prompt_manager)
    elif page == "🧪 测试Prompt":
        show_test_prompt(prompt_manager)
    elif page == "📈 性能分析":
        show_performance_analysis(prompt_manager)


def show_dashboard(prompt_manager):
    """显示仪表板"""
    st.header("📊 系统概览")

    # 获取统计数据
    prompts = asyncio.run(prompt_manager.list_prompts())

    # 关键指标
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_prompts = len(prompts)
        st.markdown(f"""
        <div class="metric-card">
            <h3>{total_prompts}</h3>
            <p>总Prompt数量</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        total_usage = sum(p["usage_count"] for p in prompts)
        st.markdown(f"""
        <div class="metric-card">
            <h3>{total_usage:,}</h3>
            <p>总使用次数</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        avg_performance = sum(p["performance_score"] for p in prompts) / len(prompts) if prompts else 0
        st.markdown(f"""
        <div class="metric-card">
            <h3>{avg_performance:.2%}</h3>
            <p>平均性能评分</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        categories = prompt_manager.get_categories()
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(categories)}</h3>
            <p>活跃分类数</p>
        </div>
        """, unsafe_allow_html=True)

    # 分类分布
    st.subheader("📈 Prompt分类分布")

    category_data = {}
    for prompt in prompts:
        cat = prompt["category"]
        category_data[cat] = category_data.get(cat, 0) + 1

    if category_data:
        fig = px.pie(
            values=list(category_data.values()),
            names=list(category_data.keys()),
            title="Prompt分类分布"
        )
        st.plotly_chart(fig, use_container_width=True)

    # 性能排行榜
    st.subheader("🏆 性能排行榜")

    sorted_prompts = sorted(prompts, key=lambda x: x["performance_score"], reverse=True)[:10]

    for i, prompt in enumerate(sorted_prompts, 1):
        col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

        with col1:
            st.write(f"**#{i}**")

        with col2:
            st.write(f"**{prompt['name']}**")
            st.caption(f"{prompt['category']} - v{prompt['version']}")

        with col3:
            # 性能评分进度条
            score = prompt["performance_score"]
            st.progress(score)
            st.write(f"{score:.2%}")

        with col4:
            st.write(f"📊 {prompt['usage_count']}次使用")

        st.divider()


def show_prompt_list(prompt_manager):
    """显示Prompt列表"""
    st.header("📝 Prompt管理")

    # 筛选器
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search_term = st.text_input("🔍 搜索Prompt", placeholder="输入关键词...")

    with col2:
        category_filter = st.selectbox(
            "分类筛选",
            ["全部"] + prompt_manager.get_categories()
        )

    with col3:
        sort_by = st.selectbox("排序方式", ["性能评分", "使用次数", "更新时间"])

    # 获取数据
    prompts = asyncio.run(prompt_manager.list_prompts())

    # 应用筛选
    if search_term:
        prompts = [
            p for p in prompts
            if search_term.lower() in p["name"].lower() or
               search_term.lower() in p["content"].lower()
        ]

    if category_filter != "全部":
        prompts = [p for p in prompts if p["category"] == category_filter]

    # 排序
    if sort_by == "性能评分":
        prompts.sort(key=lambda x: x["performance_score"], reverse=True)
    elif sort_by == "使用次数":
        prompts.sort(key=lambda x: x["usage_count"], reverse=True)
    elif sort_by == "更新时间":
        prompts.sort(key=lambda x: x["updated_at"], reverse=True)

    # 显示Prompt卡片
    for prompt in prompts:
        with st.container():
            st.markdown(f"""
            <div class="prompt-card">
                <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h3>{prompt['name']}</h3>
                        <p><span class="category-badge" style="background: {'#4CAF50' if prompt['category'] == 'RAG' else '#2196F3' if prompt['category'] == 'Data-Analysis' else '#FF9800'};">{prompt['category']}</span>
                        {prompt.get('subcategory', '')}</p>
                    </div>
                    <div style="text-align: right;">
                        <p><strong>版本:</strong> {prompt['version']}</p>
                        <p><strong>性能:</strong> {prompt['performance_score']:.1%}</p>
                    </div>
                </div>

                <p><strong>内容预览:</strong></p>
                <p style="background: #f8f9fa; padding: 1rem; border-radius: 5px; font-family: monospace; font-size: 0.9rem;">
                    {prompt['content'][:200]}{'...' if len(prompt['content']) > 200 else ''}
                </p>

                <div style="margin-top: 1rem;">
                    <strong>变量:</strong>
                    {' '.join([f'<span class="variable-tag">{{{{{{{var["name"]}}}}}}}</span>' for var in prompt.get('variables', [])[:5]])}
                    {'...' if len(prompt.get('variables', [])) > 5 else ''}
                </div>

                <div style="margin-top: 1rem; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <small>📊 使用 {prompt['usage_count']}次 | ✅ 成功率 {prompt['success_count']/max(prompt['usage_count'], 1):.1%}</small>
                    </div>
                    <div>
                        <small>📅 更新于 {prompt['updated_at'].strftime('%Y-%m-%d')}</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 操作按钮
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("📝 编辑", key=f"edit_{prompt['id']}"):
                    st.session_state['edit_prompt_id'] = prompt['id']
                    st.rerun()

            with col2:
                if st.button("🧪 测试", key=f"test_{prompt['id']}"):
                    st.session_state['test_prompt_id'] = prompt['id']
                    st.rerun()

            with col3:
                if st.button("📊 分析", key=f"analyze_{prompt['id']}"):
                    st.session_state['analyze_prompt_id'] = prompt['id']
                    st.rerun()

            with col4:
                if st.button("🗑️ 删除", key=f"delete_{prompt['id']}"):
                    asyncio.run(prompt_manager.delete_prompt(prompt['id']))
                    st.success("Prompt删除成功！")
                    st.rerun()

            st.divider()


def show_create_prompt(prompt_manager):
    """显示创建Prompt页面"""
    st.header("➕ 创建新Prompt")

    with st.form("create_prompt_form"):
        # 基本信息
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Prompt名称*", placeholder="例如: rag_response")
            category = st.selectbox("分类*", ["RAG", "Data-Analysis", "Code-Execution", "EDA", "ML-Model"])
            subcategory = st.text_input("子分类", placeholder="例如: response, analysis")

        with col2:
            version = st.text_input("版本号", value="1.0.0", placeholder="语义版本号")
            priority = st.slider("优先级", 0, 100, 50)

        # Prompt内容
        st.subheader("📝 Prompt内容")
        content = st.text_area(
            "Prompt模板内容*",
            placeholder="输入Prompt内容，使用 {{variable_name}} 语法标记变量",
            height=300
        )

        # 变量定义
        st.subheader("🔧 变量定义")

        # 自动提取变量
        if content:
            import re
            variables = re.findall(r'\{\{\s*(\w+)\s*\}\}', content)
            if variables:
                st.info(f"检测到变量: {', '.join(variables)}")

        num_variables = st.number_input("变量数量", min_value=0, max_value=20, value=0)

        variables_list = []
        for i in range(num_variables):
            with st.expander(f"变量 {i+1}", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    var_name = st.text_input("变量名*", key=f"var_name_{i}")
                    var_type = st.selectbox("类型", ["string", "number", "boolean", "json"], key=f"var_type_{i}")
                    var_required = st.checkbox("必需", value=True, key=f"var_req_{i}")

                with col2:
                    var_default = st.text_input("默认值", key=f"var_default_{i}")
                    var_desc = st.text_input("描述", key=f"var_desc_{i}")

                variables_list.append({
                    "name": var_name,
                    "type": var_type,
                    "required": var_required,
                    "default_value": var_default,
                    "description": var_desc
                })

        # 元数据
        st.subheader("📋 元数据")
        metadata_input = st.text_area(
            "元数据 (JSON格式)",
            placeholder='{"description": "描述信息", "author": "作者"}',
            height=100
        )

        try:
            metadata = json.loads(metadata_input) if metadata_input else {}
        except json.JSONDecodeError:
            st.error("元数据格式错误，请输入有效的JSON")
            metadata = {}

        # 标签
        tags = st.text_input("标签", placeholder="用逗号分隔，例如: RAG, Response, 中文")
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

        # 创建者
        created_by = st.text_input("创建者", placeholder="输入创建者名称")

        # 提交按钮
        submitted = st.form_submit_button("✅ 创建Prompt", use_container_width=True)

        if submitted:
            # 验证必填字段
            if not name or not category or not content:
                st.error("请填写所有必填字段！")
                return

            try:
                prompt_data = {
                    "name": name,
                    "category": category,
                    "subcategory": subcategory,
                    "version": version,
                    "content": content,
                    "variables": [var for var in variables_list if var["name"]],
                    "metadata": metadata,
                    "priority": priority,
                    "tags": tag_list,
                    "created_by": created_by
                }

                new_prompt = asyncio.run(prompt_manager.create_prompt(prompt_data))

                st.success(f"✅ Prompt '{name}' 创建成功！")
                st.info(f"Prompt ID: {new_prompt['id']}")

                # 显示创建的Prompt
                st.json(new_prompt)

            except Exception as e:
                st.error(f"❌ 创建失败: {str(e)}")


def show_edit_prompt(prompt_manager):
    """显示编辑Prompt页面"""
    st.header("✏️ 编辑Prompt")

    # 检查是否有编辑状态
    if 'edit_prompt_id' not in st.session_state:
        st.warning("请从Prompt列表中选择要编辑的Prompt")
        return

    prompt_id = st.session_state['edit_prompt_id']
    prompt = asyncio.run(prompt_manager.get_prompt(prompt_id))

    if not prompt:
        st.error("Prompt不存在或已被删除")
        del st.session_state['edit_prompt_id']
        return

    st.subheader(f"编辑: {prompt['name']}")

    with st.form("edit_prompt_form"):
        # 基本信息
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Prompt名称*", value=prompt['name'])
            category = st.selectbox("分类*", ["RAG", "Data-Analysis", "Code-Execution", "EDA", "ML-Model"],
                                     index=["RAG", "Data-Analysis", "Code-Execution", "EDA", "ML-Model"].index(prompt['category']))
            subcategory = st.text_input("子分类", value=prompt.get('subcategory', ''))

        with col2:
            version = st.text_input("版本号", value=prompt['version'])
            priority = st.slider("优先级", 0, 100, prompt.get('priority', 50))

        # Prompt内容
        st.subheader("📝 Prompt内容")
        content = st.text_area("Prompt模板内容*", value=prompt['content'], height=300)

        # 当前变量
        st.subheader("🔧 当前变量")
        current_vars = prompt.get('variables', [])

        for i, var in enumerate(current_vars):
            with st.expander(f"变量: {var['name']}", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.text_input("变量名", value=var['name'], disabled=True)
                    st.selectbox("类型", ["string", "number", "boolean", "json"],
                                index=["string", "number", "boolean", "json"].index(var['type']), disabled=True)
                    st.checkbox("必需", value=var['required'], disabled=True)

                with col2:
                    st.text_input("默认值", value=str(var.get('default_value', '')), disabled=True)
                    st.text_input("描述", value=var.get('description', ''), disabled=True)

        # 更新按钮
        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("💾 保存更改", use_container_width=True):
                try:
                    update_data = {
                        "content": content,
                        "priority": priority
                    }

                    updated_prompt = asyncio.run(prompt_manager.update_prompt(prompt_id, update_data))

                    st.success("✅ Prompt更新成功！")

                    # 更新session状态
                    st.session_state['edit_prompt_id'] = None
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ 更新失败: {str(e)}")

        with col2:
            if st.form_submit_button("❌ 取消编辑", use_container_width=True):
                del st.session_state['edit_prompt_id']
                st.rerun()


def show_test_prompt(prompt_manager):
    """显示测试Prompt页面"""
    st.header("🧪 Prompt测试")

    # 检查是否有测试状态
    if 'test_prompt_id' not in st.session_state:
        st.warning("请从Prompt列表中选择要测试的Prompt")
        return

    prompt_id = st.session_state['test_prompt_id']
    prompt = asyncio.run(prompt_manager.get_prompt(prompt_id))

    if not prompt:
        st.error("Prompt不存在或已被删除")
        del st.session_state['test_prompt_id']
        return

    st.subheader(f"测试: {prompt['name']}")

    # 显示原始模板
    with st.expander("📋 查看原始模板", expanded=False):
        st.code(prompt['content'], language='text')

    # 变量输入
    st.subheader("🔧 变量输入")

    variables_input = {}
    variables = prompt.get('variables', [])

    if not variables:
        st.info("该Prompt没有变量定义")
    else:
        for var in variables:
            var_name = var['name']
            var_type = var.get('type', 'string')
            var_required = var.get('required', True)
            var_default = var.get('default_value')

            # 变量标签
            label = f"**{var_name}**"
            if var_required:
                label += " *"
            if var_default:
                label += f" (默认: {var_default})"

            # 根据类型创建输入控件
            if var_type == 'boolean':
                variables_input[var_name] = st.checkbox(label, value=bool(var_default) if var_default is not None else False)
            elif var_type == 'number':
                variables_input[var_name] = st.number_input(label, value=float(var_default) if var_default is not None else 0.0)
            elif var_type == 'json':
                json_str = st.text_area(label, value=json.dumps(var_default, indent=2) if var_default else "{}")
                try:
                    variables_input[var_name] = json.loads(json_str)
                except json.JSONDecodeError:
                    st.error(f"变量 {var_name} 的JSON格式错误")
                    variables_input[var_name] = {}
            else:  # string
                variables_input[var_name] = st.text_input(label, value=str(var_default) if var_default is not None else "")

    # 渲染测试
    if st.button("🧪 渲染测试", use_container_width=True):
        try:
            rendered_content = prompt_manager.render_template(prompt['content'], variables_input)

            st.success("✅ 渲染成功！")

            # 显示渲染结果
            st.subheader("📄 渲染结果")
            st.text_area("渲染后的内容", value=rendered_content, height=300, disabled=True)

            # 统计信息
            original_length = len(prompt['content'])
            rendered_length = len(rendered_content)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("原始长度", f"{original_length} 字符")

            with col2:
                st.metric("渲染长度", f"{rendered_length} 字符")

            with col3:
                st.metric("替换变量", f"{len([v for v in variables if v['name'] in variables_input])} 个")

        except Exception as e:
            st.error(f"❌ 渲染失败: {str(e)}")

    # 返回按钮
    if st.button("🔙 返回列表"):
        del st.session_state['test_prompt_id']
        st.rerun()


def show_performance_analysis(prompt_manager):
    """显示性能分析页面"""
    st.header("📈 性能分析")

    # 模拟性能数据
    performance_data = {
        "dates": pd.date_range(end=datetime.now(), periods=30, freq='D'),
        "usage_count": [45, 52, 48, 61, 55, 67, 72, 58, 63, 69, 71, 65, 78, 82, 75, 88, 92, 85, 79, 95, 98, 91, 87, 93, 99, 102, 96, 101, 105, 108],
        "success_rate": [0.89, 0.92, 0.87, 0.91, 0.93, 0.88, 0.94, 0.90, 0.92, 0.89, 0.95, 0.91, 0.93, 0.96, 0.92, 0.94, 0.97, 0.93, 0.90, 0.95, 0.96, 0.92, 0.94, 0.93, 0.95, 0.97, 0.94, 0.96, 0.98, 0.95],
        "avg_response_time": [2.3, 2.1, 2.5, 2.2, 2.0, 2.4, 2.1, 2.3, 2.0, 2.2, 1.9, 2.3, 2.1, 1.8, 2.2, 1.9, 1.7, 2.0, 2.2, 1.8, 1.9, 2.1, 1.9, 2.0, 1.8, 1.7, 1.9, 1.8, 1.7, 1.6]
    }

    df = pd.DataFrame(performance_data)

    # 使用量趋势
    st.subheader("📊 使用量趋势")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('每日使用量', '成功率', '平均响应时间', '综合性能'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    # 使用量
    fig.add_trace(
        go.Scatter(x=df['dates'], y=df['usage_count'], name='使用量', line=dict(color='blue')),
        row=1, col=1
    )

    # 成功率
    fig.add_trace(
        go.Scatter(x=df['dates'], y=df['success_rate'], name='成功率', line=dict(color='green')),
        row=1, col=2
    )

    # 响应时间
    fig.add_trace(
        go.Scatter(x=df['dates'], y=df['avg_response_time'], name='响应时间', line=dict(color='orange')),
        row=2, col=1
    )

    # 综合性能（标准化分数）
    performance_score = (df['success_rate'] + (1 - df['avg_response_time']/3)) / 2
    fig.add_trace(
        go.Scatter(x=df['dates'], y=performance_score, name='性能评分', line=dict(color='purple')),
        row=2, col=2
    )

    fig.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # 性能分布
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 性能分布")

        # 成功率分布
        success_bins = pd.cut(df['success_rate'], bins=[0.8, 0.85, 0.9, 0.95, 1.0],
                              labels=['80-85%', '85-90%', '90-95%', '95-100%'])
        success_dist = success_bins.value_counts().sort_index()

        fig = px.bar(x=success_dist.index, y=success_dist.values,
                     title="成功率分布", labels={'x': '成功率区间', 'y': '天数'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("⏱️ 响应时间分布")

        # 响应时间分布
        response_bins = pd.cut(df['avg_response_time'], bins=[0, 1.5, 2.0, 2.5, 3.0],
                              labels=['<1.5s', '1.5-2.0s', '2.0-2.5s', '>2.5s'])
        response_dist = response_bins.value_counts().sort_index()

        fig = px.bar(x=response_dist.index, y=response_dist.values,
                     title="响应时间分布", labels={'x': '响应时间区间', 'y': '天数'})
        st.plotly_chart(fig, use_container_width=True)

    # 关键指标
    st.subheader("🎯 关键性能指标")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_usage = df['usage_count'].mean()
        st.metric("平均日使用量", f"{avg_usage:.1f}")

    with col2:
        avg_success = df['success_rate'].mean()
        st.metric("平均成功率", f"{avg_success:.1%}")

    with col3:
        avg_response = df['avg_response_time'].mean()
        st.metric("平均响应时间", f"{avg_response:.2f}s")

    with col4:
        trend = "📈 上升" if df['usage_count'].iloc[-1] > df['usage_count'].iloc[0] else "📉 下降"
        st.metric("使用趋势", trend)


if __name__ == "__main__":
    main()
