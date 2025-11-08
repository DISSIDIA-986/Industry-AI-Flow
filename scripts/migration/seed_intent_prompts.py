#!/usr/bin/env python3
"""
意图分类Prompt种子数据初始化脚本
将问题分类相关的Prompt导入到数据库中
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.prompt_manager import PromptManager, PromptVariable


async def seed_intent_prompts():
    """初始化意图分类相关Prompt"""
    print("🚀 开始初始化意图分类Prompt...")

    # 模拟数据库连接（实际使用时需要真实的数据库连接）
    try:
        # 这里应该使用真实的数据库连接
        # from backend.config import get_database_pool
        # pool = await get_database_pool()
        # prompt_manager = PromptManager(pool)

        # 暂时使用模拟的PromptManager进行演示
        from backend.services.intent_classifier import MockPromptManager

        prompt_manager = MockPromptManager()

        # 1. 主分类Prompt
        await create_main_classification_prompt(prompt_manager)

        # 2. 澄清Prompt
        await create_clarification_prompt(prompt_manager)

        # 3. 子分类Prompt
        await create_sub_classification_prompts(prompt_manager)

        # 4. 上下文增强Prompt
        await create_context_enhancement_prompt(prompt_manager)

        # 5. 路由决策Prompt
        await create_routing_decision_prompt(prompt_manager)

        print("✅ 意图分类Prompt初始化完成!")
        return True

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False


async def create_main_classification_prompt(prompt_manager):
    """创建主分类Prompt"""
    print("📝 创建主分类Prompt...")

    main_classification_prompt = await prompt_manager.create_prompt(
        name="intent_classification",
        category="Intent",
        subcategory="classification",
        version="1.0.0",
        content="""你是一个专业的AI系统意图分类器。请分析用户的问题，并将其分类到以下类别之一：

【分类类别】
1. knowledge_retrieval - 知识检索类：询问事实、概念、解释等问题
2. data_analysis - 数据分析类：对数据集进行统计分析、可视化等
3. document_processing - 文档处理类：PDF、图片OCR、文本提取等
4. code_execution - 代码执行类：运行程序、计算任务、算法实现等

【用户问题】
{{user_query}}

【上下文信息】
- 会话主题: {{session_topic}}
- 最近意图: {{recent_intents}}
- 上传文件: {{uploaded_files}}
- 用户偏好: {{user_preferences}}

【分析要求】
1. 仔细分析用户问题的核心意图
2. 结合上下文信息进行综合判断
3. 考虑用户的语言习惯和表达方式
4. 给出明确的分类结果和置信度

【输出格式】
请严格按照以下JSON格式输出：
```json
{
  "intent": "分类结果",
  "confidence": 0.00,
  "reasoning": "分类理由",
  "keywords": ["关键词1", "关键词2"],
  "context_clues": ["上下文线索1", "上下文线索2"],
  "suggested_action": "建议的处理动作",
  "uncertainty_factors": ["不确定因素"]
}
```

置信度范围：0.0-1.0，其中：
- 0.9-1.0: 非常确定的分类
- 0.7-0.9: 比较确定的分类
- 0.5-0.7: 一定不确定的分类
- 0.0-0.5: 非常不确定的分类""",
        variables=[
            PromptVariable(
                name="user_query", type="string", required=True, description="用户的问题文本"
            ),
            PromptVariable(
                name="session_topic",
                type="string",
                required=False,
                description="当前会话主题",
            ),
            PromptVariable(
                name="recent_intents",
                type="string",
                required=False,
                description="最近的意图列表",
            ),
            PromptVariable(
                name="uploaded_files",
                type="string",
                required=False,
                description="上传的文件列表",
            ),
            PromptVariable(
                name="user_preferences",
                type="json",
                required=False,
                description="用户偏好设置",
            ),
        ],
        metadata={
            "description": "主意图分类Prompt",
            "purpose": "识别用户查询的主要意图类型",
            "llm_compatible": True,
            "supported_llms": ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini-pro"],
        },
        priority=100,
        tags=["Intent", "Classification", "Core"],
    )

    print(f"✅ 主分类Prompt创建成功: {main_classification_prompt.id}")


async def create_clarification_prompt(prompt_manager):
    """创建澄清Prompt"""
    print("📝 创建澄清Prompt...")

    clarification_prompt = await prompt_manager.create_prompt(
        name="intent_clarification",
        category="Intent",
        subcategory="clarification",
        version="1.0.0",
        content="""用户的意图不够明确，需要澄清。请生成友好的澄清问题。

【用户问题】
{{user_query}}

【可能的意图】
{{possible_intents}}

【分类结果分析】
{{classification_result}}

【澄清要求】
1. 使用友好、自然的语言
2. 提供具体的选择项
3. 避免技术术语
4. 保持简短清晰
5. 基于{{language}}语言进行交流

【输出格式】
```json
{
  "clarification_needed": true,
  "clarification_message": "澄清问句",
  "suggested_options": [
    "选项1",
    "选项2",
    "选项3"
  ],
  "follow_up_questions": [
    "追问1",
    "追问2"
  ],
  "language": "{{language}}"
}
```

【语言说明】
- 如果用户使用中文提问，请用中文澄清
- 如果用户使用英文提问，请用英文澄清
- 保持与用户提问语言一致""",
        variables=[
            PromptVariable(
                name="user_query", type="string", required=True, description="用户的问题"
            ),
            PromptVariable(
                name="possible_intents",
                type="json",
                required=True,
                description="可能的意图列表",
            ),
            PromptVariable(
                name="classification_result",
                type="string",
                required=False,
                description="分类结果分析",
            ),
            PromptVariable(
                name="language",
                type="string",
                required=False,
                default_value="中文",
                description="澄清使用的语言",
            ),
        ],
        metadata={"description": "意图澄清Prompt", "purpose": "当用户意图不明确时进行澄清对话"},
        priority=90,
        tags=["Intent", "Clarification", "UX"],
    )

    print(f"✅ 澄清Prompt创建成功: {clarification_prompt.id}")


async def create_sub_classification_prompts(prompt_manager):
    """创建子分类Prompt"""
    print("📝 创建子分类Prompt...")

    # 数据分析子分类
    data_analysis_subprompt = await prompt_manager.create_prompt(
        name="data_analysis_subclassification",
        category="Intent",
        subcategory="sub_classification",
        version="1.0.0",
        content="""对数据分析类请求进行细分子分类：

【子分类选项】
- exploratory_analysis - 探索性数据分析（EDA）
- statistical_analysis - 统计分析和假设检验
- machine_learning - 机器学习模型训练
- visualization - 数据可视化和报告生成
- data_cleaning - 数据清洗和预处理
- feature_engineering - 特征工程

【用户查询】
{{user_query}}

【分析要求】
1. 识别具体的数据分析需求
2. 确定最合适的分析方法
3. 给出子分类和置信度

【输出格式】
```json
{
  "sub_intent": "子分类结果",
  "confidence": 0.00,
  "reasoning": "子分类理由",
  "required_tools": ["工具1", "工具2"],
  "expected_output": "预期输出类型"
}
```""",
        variables=[
            PromptVariable(
                name="user_query", type="string", required=True, description="用户查询"
            )
        ],
        metadata={"description": "数据分析子分类Prompt", "purpose": "对数据分析请求进行细分子分类"},
        priority=80,
        tags=["Intent", "Sub-Classification", "Data-Analysis"],
    )

    # 文档处理子分类
    document_subprompt = await prompt_manager.create_prompt(
        name="document_processing_subclassification",
        category="Intent",
        subcategory="sub_classification",
        version="1.0.0",
        content="""对文档处理类请求进行细分子分类：

【子分类选项】
- ocr_processing - OCR文字识别
- table_extraction - 表格数据提取
- image_analysis - 图像内容分析
- text_extraction - 纯文本提取
- document_parsing - 文档结构解析
- metadata_extraction - 元数据提取

【用户查询】
{{user_query}}

【文档信息】
{{document_info}}

【输出格式】
```json
{
  "sub_intent": "子分类结果",
  "confidence": 0.00,
  "reasoning": "子分类理由",
  "processing_type": "处理类型",
  "expected_format": "预期输出格式"
}
```""",
        variables=[
            PromptVariable(
                name="user_query", type="string", required=True, description="用户查询"
            ),
            PromptVariable(
                name="document_info",
                type="string",
                required=False,
                description="文档相关信息",
            ),
        ],
        metadata={"description": "文档处理子分类Prompt", "purpose": "对文档处理请求进行细分子分类"},
        priority=80,
        tags=["Intent", "Sub-Classification", "Document-Processing"],
    )

    # 代码执行子分类
    code_subprompt = await prompt_manager.create_prompt(
        name="code_execution_subclassification",
        category="Intent",
        subcategory="sub_classification",
        version="1.0.0",
        content="""对代码执行类请求进行细分子分类：

【子分类选项】
- script_execution - 脚本程序执行
- computation_task - 数值计算任务
- algorithm_implementation - 算法实现和测试
- data_processing - 数据处理和转换
- simulation - 模拟和建模
- debugging - 代码调试和优化

【用户查询】
{{user_query}}

【代码信息】
{{code_info}}

【输出格式】
```json
{
  "sub_intent": "子分类结果",
  "confidence": 0.00,
  "reasoning": "子分类理由",
  "language_preference": "编程语言偏好",
  "execution_environment": "执行环境要求",
  "estimated_complexity": "complexity_level"
}
```""",
        variables=[
            PromptVariable(
                name="user_query", type="string", required=True, description="用户查询"
            ),
            PromptVariable(
                name="code_info", type="string", required=False, description="代码相关信息"
            ),
        ],
        metadata={"description": "代码执行子分类Prompt", "purpose": "对代码执行请求进行细分子分类"},
        priority=80,
        tags=["Intent", "Sub-Classification", "Code-Execution"],
    )

    print(f"✅ 子分类Prompt创建完成")


async def create_context_enhancement_prompt(prompt_manager):
    """创建上下文增强Prompt"""
    print("📝 创建上下文增强Prompt...")

    context_prompt = await prompt_manager.create_prompt(
        name="context_enhancement",
        category="Intent",
        subcategory="context",
        version="1.0.0",
        content="""增强意图分类的上下文信息：

【上下文类型】
1. 会话历史 - 用户最近的交互历史
2. 文件信息 - 用户上传或引用的文件
3. 用户偏好 - 用户的习惯和偏好设置
4. 时间信息 - 当前时间、会话时长等
5. 主题跟踪 - 当前对话的主题和进展

【当前会话信息】
{{session_info}}

【文件处理状态】
{{file_status}}

【用户行为模式】
{{behavior_pattern}}

【增强要求】
1. 提取与当前查询最相关的上下文
2. 过滤不相关的历史信息
3. 识别用户的潜在意图
4. 预测可能的后续请求

【输出格式】
```json
{
  "enriched_context": {
    "session_topic": "会话主题",
    "relevant_history": ["相关历史1", "相关历史2"],
    "file_context": "文件上下文信息",
    "user_preferences": {"preference1": "value1"},
    "conversation_stage": "对话阶段",
    "anticipated_intents": ["预期意图1", "预期意图2"]
  },
  "confidence_boost": 0.00,
  "context_quality": "high/medium/low"
}
```""",
        variables=[
            PromptVariable(
                name="session_info", type="json", required=True, description="当前会话信息"
            ),
            PromptVariable(
                name="file_status", type="string", required=False, description="文件处理状态"
            ),
            PromptVariable(
                name="behavior_pattern",
                type="string",
                required=False,
                description="用户行为模式",
            ),
        ],
        metadata={"description": "上下文增强Prompt", "purpose": "增强意图分类的上下文信息"},
        priority=70,
        tags=["Intent", "Context", "Enhancement"],
    )

    print(f"✅ 上下文增强Prompt创建成功: {context_prompt.id}")


async def create_routing_decision_prompt(prompt_manager):
    """创建路由决策Prompt"""
    print("📝 创建路由决策Prompt...")

    routing_prompt = await prompt_manager.create_prompt(
        name="routing_decision",
        category="Intent",
        subcategory="routing",
        version="1.0.0",
        content="""基于意图分类结果做出路由决策：

【分类结果】
{{classification_result}}

【系统状态】
{{system_status}}

【路由规则】
1. 高置信度（≥0.7）：直接路由到对应Agent
2. 中等置信度（0.5-0.7）：添加额外验证
3. 低置信度（<0.5）：进入澄清流程

【Agent配置】
{{agent_config}}

【决策要求】
1. 选择最合适的处理路径
2. 考虑系统负载和可用性
3. 提供备选方案
4. 确保用户体验连续性

【输出格式】
```json
{
  "routing_decision": "路由决策",
  "selected_agent": "选择的Agent",
  "confidence": 0.00,
  "routing_path": "main/alternative/clarification",
  "parameters": {
    "timeout": 30,
    "priority": "normal",
    "retry_count": 3
  },
  "fallback_options": ["备选方案1", "备选方案2"],
  "routing_reasoning": "路由决策理由",
  "estimated_processing_time": "预计处理时间"
}
```""",
        variables=[
            PromptVariable(
                name="classification_result",
                type="json",
                required=True,
                description="分类结果",
            ),
            PromptVariable(
                name="system_status", type="json", required=True, description="系统状态"
            ),
            PromptVariable(
                name="agent_config",
                type="json",
                required=False,
                description="Agent配置信息",
            ),
        ],
        metadata={"description": "路由决策Prompt", "purpose": "基于分类结果做出智能路由决策"},
        priority=90,
        tags=["Intent", "Routing", "Decision"],
    )

    print(f"✅ 路由决策Prompt创建成功: {routing_prompt.id}")


class MockPromptManager:
    """模拟Prompt管理器（用于演示）"""

    def __init__(self):
        self.next_id = 1

    async def create_prompt(self, **kwargs):
        """模拟创建Prompt"""

        class MockPromptInfo:
            def __init__(self, id, **kwargs):
                self.id = id
                for k, v in kwargs.items():
                    setattr(self, k, v)

        prompt_info = MockPromptInfo(f"mock_prompt_{self.next_id}", **kwargs)
        self.next_id += 1
        return prompt_info


if __name__ == "__main__":
    success = asyncio.run(seed_intent_prompts())
    sys.exit(0 if success else 1)
