# 🏗️ Industry AI Flow 系统架构说明

## 📊 架构可视化

**推荐查看方式**: 打开 [ARCHITECTURE_DIAGRAM.html](./ARCHITECTURE_DIAGRAM.html) 查看交互式分层架构图

## 🏛️ 分层架构概览

系统采用**6层分层架构**，每层职责清晰，易于理解和维护：

```
┌─────────────────────────────────────────────────────────────┐
│                    第1层：用户界面层                           │
│  • Streamlit Web UI (对话式交互)                              │
│  • Prompt Admin UI (模板管理)                                 │
│  • REST API Client (外部集成)                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    第2层：API网关层                            │
│  • FastAPI Router (请求路由)                                  │
│  • Auth & Rate Limit (认证授权)                                │
│  • Query Cache (查询缓存)                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    第3层：业务服务层                           │
│  • Intent Classifier (意图识别)                              │
│  • RAG Orchestrator (RAG工作流)                               │
│  • Document Processor (文档处理)                             │
│  • Prompt Manager (Prompt管理)                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    第4层：AI引擎层                             │
│  • Hybrid LLM Dispatcher (混合LLM调度)                         │
│  • Embedding Service (向量嵌入)                               │
│  • Reranker (重排序)                                          │
│  • Local LLM (本地LLM)                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    第5层：数据存储层                           │
│  • PostgreSQL + pgvector (向量数据库)                         │
│  • Document Store (文档存储)                                  │
│  • Conversation Memory (对话记忆)                             │
│  • Usage & Budget (使用统计)                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              第6层：安全与基础设施层 (支撑层)                    │
│  • Security Services (安全防护)                               │
│  • Observability (可观测性)                                    │
│  • Infrastructure (基础设施)                                 │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 核心设计原则

### 1. 分层解耦
- 每层只依赖下层，避免跨层调用
- 通过清晰的接口定义层间交互
- 支持独立演进和替换

### 2. 高可用性
- 多层降级机制（本地LLM → 云端LLM）
- 智能缓存减少依赖
- 熔断和重试机制

### 3. 安全优先
- 敏感信息脱敏（PII检测）
- 出站策略守卫
- 多租户隔离
- 审计日志追踪

### 4. 可观测性
- Prometheus指标暴露
- 结构化JSON日志
- 分布式追踪支持
- 性能监控仪表板

## 📊 数据流向

### 典型查询流程

```
用户提问
  ↓
[用户界面层] Streamlit UI接收输入
  ↓
[API网关层] 认证验证 → 查询缓存检查
  ↓ (缓存未命中)
[业务服务层] IntentClassifier识别意图 → RAGOrchestrator处理
  ↓
[AI引擎层] EmbeddingService向量化 → HybridLLMDispatcher调度
  ↓
[数据存储层] PostgreSQL检索相似文档 → LocalLLM生成答案
  ↓
[安全与基础设施层] SecurityServices脱敏 → Observability记录日志
  ↓
返回答案给用户
```

### 文档上传流程

```
用户上传文档
  ↓
[用户界面层] Streamlit UI接收文件
  ↓
[API网关层] 文件类型验证 → 大小限制检查
  ↓
[业务服务层] DocumentProcessor解析文档 → 智能分块
  ↓
[AI引擎层] EmbeddingService生成向量 → 存储到向量库
  ↓
[数据存储层] PostgreSQL存储文档和向量
  ↓
[安全与基础设施层] 审计日志记录
  ↓
返回处理结果
```

## 🎨 组件颜色标识

| 颜色 | 层级 | 说明 |
|------|------|------|
| 🔵 蓝色 | 用户界面层 | 前端交互界面 |
| 🟢 绿色 | API网关层 | API路由和认证 |
| 🟠 橙色 | 业务服务层 | 核心业务逻辑 |
| 🟣 紫色 | AI引擎层 | AI模型和推理 |
| 🔴 红色 | 数据存储层 | 数据持久化 |
| ⚫ 灰色 | 安全与基础设施层 | 支撑服务 |

## 🔧 技术栈映射

| 层级 | 技术 | 说明 |
|------|------|------|
| 用户界面层 | Streamlit | Python Web框架 |
| API网关层 | FastAPI | 高性能异步框架 |
| 业务服务层 | LangChain 1.0 | AI工作流编排 |
| AI引擎层 | Ollama + llama.cpp | 本地LLM推理 |
| 数据存储层 | PostgreSQL + pgvector | 向量数据库 |
| 安全与基础设施层 | Docker + Prometheus | 容器化和监控 |

## 📏 接口定义

### API网关层 → 业务服务层

```python
# 意图识别接口
class IntentRequest(BaseModel):
    query: str
    context: Optional[str]
    session_id: Optional[str]

class IntentResponse(BaseModel):
    intent: str  # knowledge | analysis | document | code
    confidence: float
    clarification: Optional[str]
```

### 业务服务层 → AI引擎层

```python
# LLM调度接口
class DispatchRequest(BaseModel):
    prompt: str
    tenant_id: str
    mode: str  # local_only | hybrid_auto | cloud_only
    trace_id: str

class DispatchResponse(BaseModel):
    success: bool
    text: str
    provider: str
    latency_ms: int
    error: Optional[str]
```

### AI引擎层 → 数据存储层

```python
# 向量检索接口
class SearchRequest(BaseModel):
    query_embedding: List[float]
    top_k: int
    filters: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[DocumentChunk]
    scores: List[float]
```

## 🚀 扩展性设计

### 水平扩展
- 无状态API网关层可横向扩展
- 业务服务层支持多实例部署
- 数据库层支持读写分离

### 垂直扩展
- AI引擎层可独立升级GPU资源
- 向量数据库可独立扩展存储

### 功能扩展
- 插件式意图分类器
- 可配置的Prompt模板
- 支持多种LLM后端

## 🔐 安全架构

### 多层安全防护
1. **网络层**: API限流、DDoS防护
2. **认证层**: API Key、JWT、租户隔离
3. **应用层**: XSS/SQL注入防护、输入验证
4. **数据层**: 敏感信息脱敏、加密存储
5. **审计层**: 全链路审计日志

### 数据隐私保护
- **敏感信息脱敏**: 自动检测和脱敏PII信息
- **出站策略守卫**: 控制敏感数据发送到云端LLM
- **租户隔离**: 数据和配置严格隔离
- **审计追踪**: 所有敏感操作可追溯

## 📊 性能优化

### 缓存策略
- **查询缓存**: LRU缓存，TTL可配置
- **向量缓存**: 热点查询向量缓存
- **Prompt缓存**: Prompt模板缓存

### 异步处理
- **异步API**: FastAPI异步处理
- **后台任务**: 文档处理异步化
- **批量操作**: 向量化批处理

### 数据库优化
- **索引优化**: 向量索引、全文索引
- **连接池**: 数据库连接池管理
- **查询优化**: 慢查询监控和优化

## 📈 监控与运维

### 核心监控指标
- **可用性**: 服务健康检查、错误率
- **性能**: 响应时间、吞吐量、资源利用率
- **业务**: 意图识别准确率、检索召回率、用户满意度

### 日志管理
- **结构化日志**: JSON格式，便于解析
- **分级日志**: DEBUG/INFO/WARNING/ERROR
- **审计日志**: 敏感操作独立记录

### 告警机制
- **Prometheus**: 指标监控和告警
- **Alertmanager**: 告警路由和通知
- **PagerDuty**: 紧急告警通知

## 🎯 最佳实践

### 开发建议
1. **遵循分层原则**: 不要跨层调用
2. **保持接口稳定**: API变更需要版本管理
3. **完善错误处理**: 优雅降级，明确错误信息
4. **编写测试**: 单元测试、集成测试、E2E测试

### 部署建议
1. **容器化部署**: 使用Docker容器
2. **配置外部化**: 环境变量管理配置
3. **健康检查**: 实现/health和/ready端点
4. **优雅关闭**: 处理SIGTERM信号

### 运维建议
1. **监控先行**: 先建立监控，再上线功能
2. **日志完善**: 关键路径必须有日志
3. **定期备份**: 数据库定期备份
4. **演练故障**: 定期进行故障演练

## 📚 相关文档

- [快速开始指南](../QUICK_START_GUIDE.md)
- [安装指南](../INSTALLATION_GUIDE.md)
- [安全和多租户配置](./SECURITY_AND_TENANT_GUIDE.md)
- [对话记忆系统](./MEMORY_SYSTEM.md)
- [API文档](../docs/API.md)

---

**最后更新**: 2026-02-11
**维护者**: OpenClaw AI Assistant