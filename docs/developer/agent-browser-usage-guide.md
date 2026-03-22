# Agent-Browser 使用指南

## ✅ 安装确认

agent-browser CLI 和技能已成功安装：

```bash
$ agent-browser --version
agent-browser 0.15.2

$ ls -la skills/agent-browser
lrwxr-xr-x@ 1 openclaw staff 31 Mar 2 19:16 agent-browser -> ../.agents/skills/agent-browser
```

## 🚀 如何使用

### 方式 1: 直接在 Claude Code 中使用（推荐）

您可以直接在对话中让我使用 agent-browser 技能来测试页面：

```
请使用 agent-browser 打开 http://localhost:3123 并测试 RAG 查询功能
```

我会自动：
1. 使用 agent-browser 技能
2. 打开页面
3. 获取快照
4. 执行交互操作
5. 生成测试报告

### 方式 2: 手动使用 agent-browser CLI

```bash
# 打开页面
agent-browser open http://localhost:3123

# 等待页面加载完成
agent-browser wait --load networkidle

# 获取页面快照（显示所有可交互元素的引用）
agent-browser snapshot -i

# 使用元素引用进行交互
agent-browser fill @QueryInput "建筑项目成本超支原因有哪些？"
agent-browser click @SubmitButton

# 等待结果加载
agent-browser wait --load networkidle

# 截图
agent-browser screenshot /tmp/rag_test_result.png

# 关闭浏览器
agent-browser close
```

### 方式 3: 使用测试脚本

```bash
# 启动前端和后端服务
make run                    # 启动后端
cd frontend && npm run dev   # 启动前端

# 在另一个终端运行测试
./scripts/testing/test_rag_frontend_with_agent_browser.sh
```

## 📋 测试前准备

### 1. 启动服务

```bash
# 启动后端服务
make run
# 或
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端服务
cd frontend
npm run dev
# 前端默认运行在 http://localhost:3123
```

### 2. 确认服务状态

```bash
# 检查后端
curl http://localhost:8000/health
# 或
curl http://localhost:8000/docs

# 检查前端
curl http://localhost:3123
```

## 🎯 典型测试场景

### 场景 1: 测试 RAG 查询功能

**直接对我说：**
```
使用 agent-browser 测试 RAG 查询功能，查询"建筑项目中常见的成本超支原因有哪些？"
```

**我会自动执行：**
1. 打开前端页面 (http://localhost:3123)
2. 获取页面快照，找到输入框和按钮
3. 输入测试查询
4. 点击提交按钮
5. 等待响应
6. 验证结果显示
7. 生成测试报告

### 场景 2: 性能测试

```
使用 agent-browser 测试 RAG 页面的响应时间
```

我会测量：
- 页面加载时间
- 查询响应时间
- 首个 token 时间 (TTFT)
- 完整渲染时间

### 场景 3: 回归测试

```
使用 agent-browser 运行完整的 RAG 功能测试
```

我会测试：
- 多个不同的查询
- 页面交互流畅性
- 结果准确性
- 来源引用显示
- 错误处理

## 📝 Agent-Browser 核心命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `open <url>` | 打开网页 | `agent-browser open http://localhost:3123` |
| `snapshot -i` | 获取页面快照（交互式） | `agent-browser snapshot -i` |
| `fill <ref> <text>` | 填写输入框 | `agent-browser fill @QueryInput "test query"` |
| `click <ref>` | 点击元素 | `agent-browser click @SubmitButton` |
| `wait --load <state>` | 等待加载状态 | `agent-browser wait --load networkidle` |
| `screenshot <path>` | 截图 | `agent-browser screenshot /tmp/page.png` |
| `close` | 关闭浏览器 | `agent-browser close` |

## 🔍 页面快照说明

`agent-browser snapshot -i` 会返回所有可交互元素的引用：

```json
{
  "data": {
    "refs": {
      "@e1": "[input type='text' id='query']",
      "@e2": "[button type='submit'] 提交",
      "@e3": "[div class='result']"
    }
  }
}
```

使用这些引用进行交互：
```bash
agent-browser fill @e1 "测试查询"
agent-browser click @e2
```

## 🛠️ 故障排查

### 问题 1: agent-browser 命令找不到

```bash
# 重新安装
npm install -g @agent-browser/cli
```

### 问题 2: 浏览器无法启动

```bash
# 检查依赖
agent-browser --version

# 查看帮助
agent-browser --help
```

### 问题 3: 页面元素找不到

```bash
# 使用 --json 格式查看详细快照
agent-browser snapshot -i --json > snapshot.json

# 检查快照内容
cat snapshot.json | jq '.data.refs'
```

## 📚 参考资源

- **agent-browser GitHub**: https://github.com/vercel-labs/agent-browser
- **技能文档**: `.agents/skills/agent-browser/SKILL.md`
- **测试脚本**: `scripts/testing/test_rag_frontend_with_agent_browser.sh`
- **RAG 测试脚本**: `scripts/testing/test_rag_with_browser.py`

## 🎬 快速开始

**现在就可以测试！**

1. 确保前端服务运行在 http://localhost:3123
2. 对我说：**"使用 agent-browser 测试 RAG 页面功能"**
3. 我会自动完成测试并生成报告

就这么简单！ 🚀
