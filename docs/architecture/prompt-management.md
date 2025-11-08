# Prompt 管理系统设计文档

## 1. 系统架构

### 1.1 核心组件
- **Prompt Manager**: 中央管理服务，负责Prompt的CRUD、版本控制、缓存
- **Prompt Repository**: 数据访问层，与PostgreSQL交互
- **Prompt Cache**: 内存缓存，提升性能
- **Prompt Router**: 动态路由选择最优Prompt
- **Prompt Evaluator**: 质量评估和A/B测试工具
- **Web UI**: 可视化管理界面

### 1.2 与LangChain 1.0集成
- **Middleware集成**: 在State Graph中动态注入Prompt
- **Agent智能选择**: 根据上下文自动选择Prompt版本
- **版本管理**: 支持多版本并存和灰度发布

## 2. 数据模型设计

### 2.1 主表 - prompts
```sql
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,  -- RAG, CODE_EXECUTION, DATA_ANALYSIS, EDA等
    subcategory VARCHAR(100),        -- 更细粒度分类
    version VARCHAR(50) NOT NULL,    -- 语义版本号
    content TEXT NOT NULL,           -- Prompt内容
    variables JSONB,                 -- 可变参数定义
    metadata JSONB,                  -- 元数据
    is_active BOOLEAN DEFAULT true,  -- 是否激活
    is_latest BOOLEAN DEFAULT false, -- 是否为最新版本
    priority INTEGER DEFAULT 0,      -- 优先级
    performance_score DECIMAL(3,2),  -- 性能评分 0.00-1.00
    usage_count BIGINT DEFAULT 0,    -- 使用次数
    success_count BIGINT DEFAULT 0,  -- 成功次数
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(255),

    UNIQUE(name, category, version),
    INDEX idx_prompts_category (category),
    INDEX idx_prompts_active_latest (is_active, is_latest),
    INDEX idx_prompts_priority (priority DESC)
);
```

### 2.2 版本历史表 - prompt_versions
```sql
CREATE TABLE prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB,
    change_description TEXT,
    performance_metrics JSONB,
    usage_stats JSONB,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_prompt_versions_prompt_id (prompt_id),
    INDEX idx_prompt_versions_created_at (created_at DESC)
);
```

### 2.3 使用记录表 - prompt_usage_logs
```sql
CREATE TABLE prompt_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID REFERENCES prompts(id),
    session_id VARCHAR(255),
    context JSONB,                   -- 使用上下文
    variables_used JSONB,            -- 实际使用的变量值
    execution_time_ms INTEGER,       -- 执行时间
    success BOOLEAN,                 -- 是否成功
    error_message TEXT,              -- 错误信息
    user_feedback INTEGER,           -- 用户反馈评分 1-5
    llm_response JSONB,             -- LLM响应摘要
    tokens_used INTEGER,             -- Token使用量
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_prompt_usage_logs_prompt_id (prompt_id),
    INDEX idx_prompt_usage_logs_created_at (created_at DESC),
    INDEX idx_prompt_usage_logs_success (success)
);
```

### 2.4 A/B测试表 - prompt_experiments
```sql
CREATE TABLE prompt_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    prompt_a_id UUID REFERENCES prompts(id),
    prompt_b_id UUID REFERENCES prompts(id),
    traffic_split DECIMAL(3,2) DEFAULT 0.5,  -- A版本流量比例
    metrics JSONB,                        -- 评估指标
    status VARCHAR(50) DEFAULT 'active',  -- active, paused, completed
    winner_prompt_id UUID REFERENCES prompts(id),  -- 获胜版本
    confidence_level DECIMAL(3,2),        -- 置信水平
    sample_size BIGINT,                   -- 样本数量
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,

    INDEX idx_prompt_experiments_status (status),
    INDEX idx_prompt_experiments_created_at (created_at DESC)
);
```

### 2.5 标签表 - prompt_tags
```sql
CREATE TABLE prompt_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7) DEFAULT '#007bff',  -- 十六进制颜色
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE prompt_tag_relations (
    prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES prompt_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (prompt_id, tag_id)
);
```

## 3. 核心功能设计

### 3.1 Prompt版本管理
- **语义化版本**: 使用 Major.Minor.Patch 格式
- **自动升级**: 支持自动版本号递增
- **版本比较**: 支持版本间的差异对比
- **回滚机制**: 快速回滚到指定版本

### 3.2 智能Prompt选择
- **基于上下文**: 根据用户请求类型自动选择
- **基于性能**: 优先选择高性能评分的Prompt
- **基于A/B测试**: 自动参与实验和结果分析
- **基于用户偏好**: 考虑用户历史反馈

### 3.3 动态变量注入
- **模板语法**: 支持 `{{variable_name}}` 语法
- **变量验证**: 使用前验证必需变量
- **默认值**: 支持变量默认值设置
- **类型检查**: 支持变量类型验证

### 3.4 性能监控
- **实时指标**: 成功率、响应时间、Token使用
- **趋势分析**: 历史性能趋势
- **异常检测**: 自动检测性能异常
- **报告生成**: 定期生成性能报告

## 4. LangChain 1.0 集成策略

### 4.1 Middleware集成
```python
class PromptManagerMiddleware:
    """Prompt管理中间件"""

    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # 动态选择和注入Prompt
        pass

    def select_optimal_prompt(self, context: Dict) -> Prompt:
        # 基于上下文选择最优Prompt
        pass
```

### 4.2 State Graph集成
```python
def create_prompt_enhanced_graph():
    workflow = StateGraph(AgentState)

    # 添加Prompt管理节点
    workflow.add_node("prompt_selector", select_prompt_node)
    workflow.add_node("prompt_optimizer", optimize_prompt_node)

    return workflow
```

### 4.3 Agent自适应调用
```python
class AdaptivePromptAgent:
    """自适应Prompt Agent"""

    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager

    async def execute_with_adaptive_prompt(
        self,
        task: str,
        context: Dict
    ) -> Dict:
        # 根据任务和上下文自适应选择Prompt
        pass
```

## 5. API设计

### 5.1 RESTful API
- `GET /api/prompts` - 获取Prompt列表
- `POST /api/prompts` - 创建新Prompt
- `PUT /api/prompts/{id}` - 更新Prompt
- `DELETE /api/prompts/{id}` - 删除Prompt
- `POST /api/prompts/{id}/test` - 测试Prompt
- `GET /api/prompts/{id}/versions` - 获取版本历史
- `POST /api/experiments` - 创建A/B测试

### 5.2 内部API
- `prompt_manager.get_prompt(category, context)` - 获取最优Prompt
- `prompt_manager.log_usage(prompt_id, metrics)` - 记录使用情况
- `prompt_manager.evaluate_performance(prompt_id)` - 评估性能

## 6. Web界面功能

### 6.1 Prompt编辑器
- **语法高亮**: 支持模板语法高亮
- **实时预览**: 实时预览Prompt效果
- **变量提示**: 智能变量名称提示
- **版本对比**: 可视化版本差异

### 6.2 性能仪表板
- **实时监控**: 实时显示Prompt性能
- **趋势图表**: 性能趋势可视化
- **对比分析**: 多版本性能对比
- **异常告警**: 性能异常提醒

### 6.3 A/B测试管理
- **实验配置**: 可视化配置A/B测试
- **实时结果**: 实时显示测试结果
- **统计分析**: 统计显著性分析
- **自动决策**: 自动选择获胜版本

## 7. 部署和扩展

### 7.1 数据库优化
- **索引策略**: 针对查询模式优化索引
- **分区策略**: 按时间分区使用日志表
- **连接池**: 数据库连接池管理
- **缓存策略**: 多层缓存提升性能

### 7.2 微服务架构
- **服务拆分**: Prompt管理、评估、缓存独立服务
- **负载均衡**: 支持水平扩展
- **服务发现**: 自动服务注册和发现
- **监控告警**: 完整的监控和告警体系

## 8. 安全和权限

### 8.1 访问控制
- **角色权限**: 基于角色的访问控制
- **API密钥**: API访问密钥管理
- **审计日志**: 完整的操作审计
- **数据加密**: 敏感数据加密存储

### 8.2 数据保护
- **备份策略**: 定期数据备份
- **灾难恢复**: 灾难恢复方案
- **数据脱敏**: 测试环境数据脱敏
- **合规性**: 满足数据保护法规要求

这个设计将为Luncheon AI Flow提供强大、灵活、可扩展的Prompt管理能力，为未来的Agentic AI工作流奠定坚实基础。