#!/usr/bin/env python3
"""
现有Prompt迁移脚本
将系统中硬编码的Prompt迁移到数据库中，实现集中化管理
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import uuid

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.prompt_manager import PromptManager, PromptVariable
from backend.config import get_database_pool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PromptMigrator:
    """Prompt迁移器"""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
        self.migration_stats = {
            'total_prompts': 0,
            'migrated_prompts': 0,
            'failed_prompts': 0,
            'skipped_prompts': 0,
            'errors': []
        }

    async def migrate_all_prompts(self):
        """迁移所有现有的Prompt"""
        logger.info("开始Prompt迁移过程")

        # 1. 从代码中提取硬编码的Prompt
        code_prompts = await self._extract_prompts_from_code()

        # 2. 从配置文件中提取Prompt
        config_prompts = await self._extract_prompts_from_config()

        # 3. 合并所有Prompt
        all_prompts = {**code_prompts, **config_prompts}
        self.migration_stats['total_prompts'] = len(all_prompts)

        logger.info(f"发现 {len(all_prompts)} 个待迁移Prompt")

        # 4. 批量迁移Prompt
        for name, prompt_data in all_prompts.items():
            await self._migrate_single_prompt(name, prompt_data)

        # 5. 生成迁移报告
        self._generate_migration_report()

        return self.migration_stats

    async def _extract_prompts_from_code(self) -> Dict[str, Any]:
        """从代码中提取硬编码的Prompt"""
        prompts = {}

        # RAG系统Prompt
        prompts.update(self._get_rag_prompts())

        # 代码执行Prompt
        prompts.update(self._get_code_execution_prompts())

        # 数据分析Prompt
        prompts.update(self._get_data_analysis_prompts())

        # 系统Prompt
        prompts.update(self._get_system_prompts())

        return prompts

    def _get_rag_prompts(self) -> Dict[str, Any]:
        """获取RAG相关的Prompt"""
        return {
            "rag_response": {
                "category": "RAG",
                "subcategory": "response",
                "version": "1.0.0",
                "content": """基于以下检索到的文档，请准确回答用户问题：

【检索到的文档】
{{context}}

【用户问题】
{{query}}

【回答要求】
1. 基于提供的文档内容进行回答
2. 如果文档中没有相关信息，请明确说明
3. 回答要准确、完整、有条理
4. 引用具体的文档内容支持你的回答
5. 使用{{language}}语言进行回答

请开始回答：""",
                "variables": [
                    PromptVariable(
                        name="context",
                        type="string",
                        required=True,
                        description="检索到的文档内容"
                    ),
                    PromptVariable(
                        name="query",
                        type="string",
                        required=True,
                        description="用户的问题"
                    ),
                    PromptVariable(
                        name="language",
                        type="string",
                        required=False,
                        default_value="中文",
                        description="回答使用的语言"
                    )
                ],
                "metadata": {
                    "description": "RAG检索增强生成的响应Prompt",
                    "purpose": "基于检索文档生成准确回答",
                    "author": "system_migration"
                },
                "priority": 100,
                "tags": ["RAG", "Response", "Core"]
            },

            "rag_context_compression": {
                "category": "RAG",
                "subcategory": "processing",
                "version": "1.0.0",
                "content": """请对以下检索到的文档进行压缩和整理，提取最相关的信息：

【原始文档】
{{raw_context}}

【用户问题】
{{query}}

【整理要求】
1. 保留与问题最相关的核心信息
2. 去除冗余和不相关的内容
3. 保持信息的准确性和完整性
4. 按重要性排序信息
5. 输出长度控制在{{max_length}}字符以内

整理后的上下文：""",
                "variables": [
                    PromptVariable(
                        name="raw_context",
                        type="string",
                        required=True,
                        description="原始检索到的文档"
                    ),
                    PromptVariable(
                        name="query",
                        type="string",
                        required=True,
                        description="用户问题"
                    ),
                    PromptVariable(
                        name="max_length",
                        type="number",
                        required=False,
                        default_value=2000,
                        description="最大输出长度"
                    )
                ],
                "metadata": {
                    "description": "RAG上下文压缩Prompt",
                    "purpose": "压缩和整理检索到的文档内容"
                },
                "priority": 80,
                "tags": ["RAG", "Processing", "Compression"]
            }
        }

    def _get_code_execution_prompts(self) -> Dict[str, Any]:
        """获取代码执行相关的Prompt"""
        return {
            "code_execution_main": {
                "category": "Code-Execution",
                "subcategory": "execution",
                "version": "1.0.0",
                "content": """请执行以下{{language}}代码并处理{{task_type}}任务：

【代码】
```{{language}}
{{code}}
```

【任务描述】
{{description}}

【要求】
1. 安全执行代码，避免恶意操作
2. 捕获并处理所有可能的异常
3. 提供清晰的执行结果
4. 如果有错误，给出详细的错误信息和修复建议
5. 执行时间限制：{{timeout_limit}}秒

【输出格式】
```
执行状态：[成功/失败]
执行结果：[具体结果或错误信息]
执行时间：[实际执行时间秒数]
附加信息：[其他相关信息]
```""",
                "variables": [
                    PromptVariable(
                        name="code",
                        type="string",
                        required=True,
                        description="要执行的代码"
                    ),
                    PromptVariable(
                        name="language",
                        type="string",
                        required=True,
                        description="编程语言"
                    ),
                    PromptVariable(
                        name="task_type",
                        type="string",
                        required=True,
                        description="任务类型"
                    ),
                    PromptVariable(
                        name="description",
                        type="string",
                        required=True,
                        description="任务描述"
                    ),
                    PromptVariable(
                        name="timeout_limit",
                        type="number",
                        required=False,
                        default_value=30,
                        description="执行超时限制（秒）"
                    )
                ],
                "metadata": {
                    "description": "代码执行主要Prompt",
                    "purpose": "安全执行代码并处理结果"
                },
                "priority": 100,
                "tags": ["Code-Execution", "Core", "Security"]
            },

            "code_debugging": {
                "category": "Code-Execution",
                "subcategory": "debugging",
                "version": "1.0.0",
                "content": """请分析和调试以下{{language}}代码：

【问题代码】
```{{language}}
{{code}}
```

【错误信息】
{{error_message}}

【期望行为】
{{expected_behavior}}

【分析要求】
1. 识别代码中的错误和问题
2. 分析错误产生的原因
3. 提供修复方案
4. 给出改进建议
5. 确保修复后的代码符合最佳实践

【输出格式】
1. 问题诊断
2. 根本原因分析
3. 修复代码
4. 验证方案
5. 预防措施""",
                "variables": [
                    PromptVariable(
                        name="code",
                        type="string",
                        required=True,
                        description="有问题的代码"
                    ),
                    PromptVariable(
                        name="language",
                        type="string",
                        required=True,
                        description="编程语言"
                    ),
                    PromptVariable(
                        name="error_message",
                        type="string",
                        required=False,
                        description="错误信息"
                    ),
                    PromptVariable(
                        name="expected_behavior",
                        type="string",
                        required=False,
                        description="期望的行为"
                    )
                ],
                "metadata": {
                    "description": "代码调试Prompt",
                    "purpose": "分析和修复代码问题"
                },
                "priority": 90,
                "tags": ["Code-Execution", "Debugging", "Analysis"]
            }
        }

    def _get_data_analysis_prompts(self) -> Dict[str, Any]:
        """获取数据分析相关的Prompt"""
        return {
            "data_analysis_eda": {
                "category": "Data-Analysis",
                "subcategory": "EDA",
                "version": "2.0.0",
                "content": """请对提供的数据进行全面的探索性数据分析（EDA）：

【数据集信息】
{{dataset_info}}

【分析目标】
{{analysis_goals}}

【分析要求】
1. 数据概览：数据维度、类型、基本统计
2. 数据质量：缺失值、重复值、异常值分析
3. 分布分析：数值型和分类型变量的分布
4. 关系分析：变量间的相关性和关联性
5. 可视化：生成关键图表和可视化
6. 洞察发现：总结关键发现和业务洞察

【技术要求】
- 使用{{language}}进行分析
- 生成可执行的{{language}}代码
- 包含中文字体支持配置
- 输出高清图表（DPI≥150）
- 保存所有可视化结果

【输出格式】
1. 分析报告（Markdown格式）
2. 完整的{{language}}代码
3. 生成的图表文件列表
4. 关键发现和建议""",
                "variables": [
                    PromptVariable(
                        name="dataset_info",
                        type="string",
                        required=True,
                        description="数据集信息"
                    ),
                    PromptVariable(
                        name="analysis_goals",
                        type="string",
                        required=True,
                        description="分析目标"
                    ),
                    PromptVariable(
                        name="language",
                        type="string",
                        required=False,
                        default_value="Python",
                        description="分析语言"
                    )
                ],
                "metadata": {
                    "description": "探索性数据分析（EDA）Prompt",
                    "purpose": "全面的数据探索性分析",
                    "version_notes": "v2.0增强中文字体支持和可视化"
                },
                "priority": 100,
                "tags": ["Data-Analysis", "EDA", "Visualization"]
            },

            "data_analysis_ml": {
                "category": "Data-Analysis",
                "subcategory": "ML-Model",
                "version": "1.0.0",
                "content": """请基于提供的数据构建和评估机器学习模型：

【数据集信息】
{{dataset_info}}

【建模任务】
{{task_description}}

【目标变量】
{{target_variable}}

【建模要求】
1. 数据预处理：特征工程、数据清洗、编码转换
2. 模型选择：尝试多种合适的算法
3. 模型训练：交叉验证、超参数调优
4. 模型评估：准确率、精确率、召回率、F1分数等
5. 特征重要性：分析特征对模型的影响
6. 结果解释：提供模型结果的业务解释

【技术要求】
- 使用{{language}}进行建模
- 包含完整的模型训练和评估流程
- 生成性能评估图表
- 提供模型保存和预测代码

【输出格式】
1. 建模报告
2. 完整的建模代码
3. 模型性能评估结果
4. 特征重要性分析
5. 业务建议和洞察""",
                "variables": [
                    PromptVariable(
                        name="dataset_info",
                        type="string",
                        required=True,
                        description="数据集信息"
                    ),
                    PromptVariable(
                        name="task_description",
                        type="string",
                        required=True,
                        description="建模任务描述"
                    ),
                    PromptVariable(
                        name="target_variable",
                        type="string",
                        required=True,
                        description="目标变量名称"
                    ),
                    PromptVariable(
                        name="language",
                        type="string",
                        required=False,
                        default_value="Python",
                        description="建模语言"
                    )
                ],
                "metadata": {
                    "description": "机器学习建模Prompt",
                    "purpose": "构建和评估机器学习模型"
                },
                "priority": 90,
                "tags": ["Data-Analysis", "ML-Model", "Prediction"]
            },

            "chinese_data_analysis": {
                "category": "Data-Analysis",
                "subcategory": "Chinese-Support",
                "version": "1.0.0",
                "content": """请对中文数据进行分析，确保所有输出都支持中文显示：

【数据集信息】
{{dataset_info}}

【分析要求】
1. 确保中文字体正确显示
2. 生成中文标签和标题的图表
3. 使用中文进行分析报告编写
4. 处理中文文本数据（如果存在）

【中文字体配置】
请在代码开头添加以下中文字体支持配置：
```python
import sys
try:
    if '/app/utils' not in sys.path:
        sys.path.insert(0, '/app/utils')
    import matplotlib_chinese_support
    matplotlib_chinese_support.setup_chinese_matplotlib()
    print("✓ 已启用中文字体支持")
except ImportError:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Zen Hei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    print("✓ 使用备用中文字体配置")
```

【输出要求】
- 所有图表标题、轴标签、图例使用中文
- 分析报告使用中文编写
- 数据可视化支持中文显示
- 错误信息和日志使用中文""",
                "variables": [
                    PromptVariable(
                        name="dataset_info",
                        type="string",
                        required=True,
                        description="中文数据集信息"
                    )
                ],
                "metadata": {
                    "description": "中文数据分析专用Prompt",
                    "purpose": "确保中文数据分析和可视化的正确显示"
                },
                "priority": 95,
                "tags": ["Data-Analysis", "Chinese", "Visualization"]
            }
        }

    def _get_system_prompts(self) -> Dict[str, Any]:
        """获取系统级Prompt"""
        return {
            "agent_system": {
                "category": "System",
                "subcategory": "agent",
                "version": "1.0.0",
                "content": """你是一个智能AI助手，专门为Luncheon AI Flow系统服务。

【系统特性】
- 多模态AI工作流支持
- RAG检索增强生成
- 代码执行和数据分析
- 中文语言优化

【能力范围】
1. 信息检索和知识问答
2. 数据分析和可视化
3. 代码生成和调试
4. 文档理解和生成
5. 多轮对话和上下文理解

【交互原则】
- 准确理解用户意图
- 提供详细、有用的回答
- 遇到不确定时主动询问
- 保持对话的连贯性和上下文
- 使用{{language}}与用户交流

【安全要求】
- 不生成有害内容
- 保护用户隐私
- 遵守伦理准则
- 对敏感话题保持谨慎

请开始与用户对话。""",
                "variables": [
                    PromptVariable(
                        name="language",
                        type="string",
                        required=False,
                        default_value="中文",
                        description="交互语言"
                    )
                ],
                "metadata": {
                    "description": "Agent系统Prompt",
                    "purpose": "定义AI助手的身份和能力"
                },
                "priority": 100,
                "tags": ["System", "Agent", "Core"]
            },

            "error_handling": {
                "category": "System",
                "subcategory": "error",
                "version": "1.0.0",
                "content": """处理系统错误和异常情况的标准化流程：

【错误分类】
1. 用户输入错误：格式错误、参数缺失等
2. 系统执行错误：代码执行失败、API调用错误等
3. 数据处理错误：格式不匹配、缺失值等
4. 资源限制错误：超时、内存不足等

【处理原则】
1. 友好的错误提示，使用{{language}}
2. 提供具体的错误原因和解决建议
3. 保持用户体验，避免技术术语
4. 记录错误日志用于系统改进
5. 提供重试或替代方案

【错误响应模板】
```
❌ 遇到了问题：[简要描述问题]

🔍 问题原因：[具体原因分析]

💡 解决建议：
1. [建议1]
2. [建议2]
3. [建议3]

🔄 重试方案：[如何重新尝试]

需要更多帮助吗？
```""",
                "variables": [
                    PromptVariable(
                        name="language",
                        type="string",
                        required=False,
                        default_value="中文",
                        description="错误提示语言"
                    )
                ],
                "metadata": {
                    "description": "错误处理Prompt",
                    "purpose": "标准化错误处理流程"
                },
                "priority": 80,
                "tags": ["System", "Error", "User-Experience"]
            }
        }

    async def _extract_prompts_from_config(self) -> Dict[str, Any]:
        """从配置文件中提取Prompt"""
        prompts = {}

        # 检查是否存在配置文件
        config_paths = [
            "config/prompts.json",
            "prompts.json",
            "backend/config/prompts.json"
        ]

        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)

                    if 'prompts' in config_data:
                        prompts.update(config_data['prompts'])
                        logger.info(f"从 {config_path} 加载了 {len(config_data['prompts'])} 个Prompt")

                except Exception as e:
                    logger.error(f"加载配置文件 {config_path} 失败: {e}")

        return prompts

    async def _migrate_single_prompt(self, name: str, prompt_data: Dict[str, Any]):
        """迁移单个Prompt"""
        try:
            # 检查是否已存在
            try:
                existing_prompt = await self.prompt_manager._get_prompt_by_version(
                    name, prompt_data['category'], prompt_data.get('version', '1.0.0')
                )
                if existing_prompt:
                    logger.info(f"Prompt {name} v{prompt_data.get('version', '1.0.0')} 已存在，跳过")
                    self.migration_stats['skipped_prompts'] += 1
                    return
            except:
                pass  # Prompt不存在，继续创建

            # 创建新Prompt
            prompt_info = await self.prompt_manager.create_prompt(
                name=name,
                category=prompt_data['category'],
                content=prompt_data['content'],
                subcategory=prompt_data.get('subcategory'),
                version=prompt_data.get('version', '1.0.0'),
                variables=prompt_data.get('variables', []),
                metadata=prompt_data.get('metadata', {}),
                priority=prompt_data.get('priority', 0),
                tags=prompt_data.get('tags', []),
                created_by="system_migration"
            )

            logger.info(f"✅ 成功迁移Prompt: {name} (ID: {prompt_info.id})")
            self.migration_stats['migrated_prompts'] += 1

        except Exception as e:
            logger.error(f"❌ 迁移Prompt {name} 失败: {e}")
            self.migration_stats['failed_prompts'] += 1
            self.migration_stats['errors'].append({
                'prompt': name,
                'error': str(e)
            })

    def _generate_migration_report(self):
        """生成迁移报告"""
        stats = self.migration_stats

        report = f"""
# Prompt迁移报告

**迁移时间**: {datetime.now().isoformat()}

## 迁移统计

- 总Prompt数量: {stats['total_prompts']}
- 成功迁移: {stats['migrated_prompts']}
- 跳过迁移: {stats['skipped_prompts']}
- 迁移失败: {stats['failed_prompts']}
- 成功率: {stats['migrated_prompts'] / max(stats['total_prompts'], 1):.1%}

## 迁移详情

### 成功迁移的Prompt
{self._list_prompt_names('migrated')}

### 跳过的Prompt
{self._list_prompt_names('skipped')}

### 失败的Prompt
{self._list_prompt_names('failed')}

## 错误详情

{self._format_errors()}

## 后续建议

1. 验证迁移的Prompt内容是否正确
2. 测试Prompt的渲染和执行
3. 更新相关代码以使用数据库Prompt
4. 设置A/B测试优化Prompt性能
5. 建立Prompt版本管理流程

---

*报告由Prompt迁移系统自动生成*
        """

        # 保存报告
        report_path = "prompt_migration_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"📋 迁移报告已保存到: {report_path}")

        # 打印摘要
        print("\n" + "="*60)
        print("🎉 Prompt迁移完成!")
        print("="*60)
        print(f"总数量: {stats['total_prompts']}")
        print(f"成功: {stats['migrated_prompts']} ✅")
        print(f"跳过: {stats['skipped_prompts']} ⏭️")
        print(f"失败: {stats['failed_prompts']} ❌")
        print(f"成功率: {stats['migrated_prompts'] / max(stats['total_prompts'], 1):.1%}")
        print(f"报告: {report_path}")
        print("="*60)

    def _list_prompt_names(self, status: str) -> str:
        """列出指定状态的Prompt名称"""
        if status == 'migrated':
            return "已成功迁移到数据库"
        elif status == 'skipped':
            return "已存在相同版本，跳过迁移"
        elif status == 'failed':
            names = [error['prompt'] for error in self.migration_stats['errors']]
            return ', '.join(names) if names else "无"
        return ""

    def _format_errors(self) -> str:
        """格式化错误信息"""
        if not self.migration_stats['errors']:
            return "无错误"

        error_text = ""
        for error in self.migration_stats['errors']:
            error_text += f"### {error['prompt']}\n"
            error_text += f"错误: {error['error']}\n\n"

        return error_text


async def main():
    """主函数"""
    print("🚀 开始Prompt迁移过程")

    try:
        # 获取数据库连接池
        pool = await get_database_pool()

        # 初始化Prompt管理器
        prompt_manager = PromptManager(pool)

        # 创建迁移器
        migrator = PromptMigrator(prompt_manager)

        # 执行迁移
        stats = await migrator.migrate_all_prompts()

        return 0 if stats['failed_prompts'] == 0 else 1

    except Exception as e:
        logger.error(f"迁移过程失败: {e}")
        print(f"❌ 迁移失败: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)