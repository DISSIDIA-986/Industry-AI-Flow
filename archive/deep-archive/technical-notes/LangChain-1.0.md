LangChain 1.0的主要改变如下：

1. 引入统一的 create_agent API，简化各类 Agent 创建入口，降低使用复杂度。
2. 大幅重构和瘦身基础库，使架构更加清晰统一，提升生产可用性。
3. 新增 middleware（中间件）机制，允许开发者更灵活地“介入”Agent运行过程，提升可定制性和可观测性。
4. 输出结构控制能力增强，更好支持 JSON、Schema 等结构化输出，便于工具集成与下游解析。
5. Agent 主循环拥有更强的上下文与内容块（content_blocks）机制，增强多轮对话和工具调用的可控性。

升级到LangChain 1.0的迁移重点步骤和关注点总结如下：

1. **更新导入路径与依赖**：将遗留链（LLMChain、ConversationChain等）从`langchain`迁移至`langchain-classic`包，更新为新的包结构，同时升级至Python 3.10+、Node.js 20+。
2. **将旧版API迁移至invoke接口**：使用`invoke({...})`替代已废弃的`run()`方法，改为字典输入格式，同时调整输出访问方式（如`response.content`）。
3. **迁移旧版Agent至create_agent**：将原有的Agent实现（ReAct、Plan-and-Execute等）统一迁移至新的`create_agent` API，底层统一使用LangGraph执行引擎。
4. **适配新的content_blocks标准**：各LLM提供商的输出差异被标准化为`content_blocks`（如ToolCallBlock、TextBlock等），通过`message.contentBlocks`访问以确保跨模型兼容性。
5. **处理中间件与上下文注入**：用新的middleware机制替代旧的pre-model hook，采用`context`参数进行依赖注入而非`config["configurable"]`，同时修复特定模型的兼容性问题（如ChatOpenAI的max_tokens参数）。
