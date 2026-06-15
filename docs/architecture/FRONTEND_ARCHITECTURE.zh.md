# 前端架构设计

> 🇬🇧 English： **[FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md)**

## 概述

Industry AI Flow 前端是一个基于 Next.js（App Router）的单页应用，通过一层轻量代理与 FastAPI 后端通信。整体分为四层：App Router → React 组件 → 状态管理 → API 集成。

```
┌──────────────────────────────────────────────┐
│              Next.js 应用                      │
│  App Router   —— 页面路由、布局、               │
│                  服务端 + 客户端组件            │
│  组件层       —— UI（表单、表格、卡片、         │
│                  模态框）+ 业务 + 共享组件      │
│  状态层       —— React Context（认证、配置）、  │
│                  本地状态、服务端状态           │
│  API 层       —— REST 客户端、错误处理          │
└──────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│            FastAPI 后端                         │
│  认证（JWT）· AI 工作流 · 文档处理 ·            │
│  PostgreSQL + pgvector                         │
└──────────────────────────────────────────────┘
```

## 技术栈

- **框架** —— Next.js（App Router、Server Components）、React、TypeScript。
- **样式** —— Tailwind CSS。
- **状态** —— React Context 管理全局状态（认证、应用配置）；`useState`/`useReducer` 管理本地状态；服务端状态缓存用于数据获取。
- **API** —— 基于 Fetch 的 API 客户端；React Hook Form 处理表单。
- **UI** —— 自定义组件库、SVG 图标集、Recharts 数据可视化。

## 目录结构

```
frontend/src/
├── app/                 # Next.js App Router
│   ├── (mvp)/           # 主要功能页：overview、workflow-chat、
│   │                    #   documents、data-dashboard、cost-estimation、
│   │                    #   prompt-admin、intent-demo
│   ├── (simple)/        # 简化版仪表板页面
│   ├── login/           # 登录页
│   ├── api/             # 前端到后端的代理路由
│   ├── layout.tsx       # 根布局
│   └── globals.css      # 全局样式
├── components/          # forms、tables、cards、modals、charts、
│                        #   layout、ProtectedRoute、Navbar
├── contexts/            # AuthContext、AppConfigContext
├── hooks/               # useAuth、useApi、动画 Hook
├── lib/                 # api-client、formatters、validators、constants
└── styles/              # 组件 + 主题样式
```

## 功能模块

1. **用户认证** —— JWT 登录、token 自动刷新与过期处理、基于角色的访问控制。会话过期可自愈：受保护端点返回的任何 401 都会清空认证状态并跳转登录。
2. **工作流聊天** —— 主要演示界面。实时查询/响应并带来源引用、消息历史、文件上传，以及意图/流水线动画可视化。
3. **文档管理** —— 批量上传与格式校验、按格式预览（PDF、图片、文本/CSV/JSON、Office 提取）、全文检索，以及每份文档的 AI 生成摘要。
4. **数据仪表板 / 系统总览** —— 各模块的实时健康与指标、多种图表类型、可配置视图。
5. **成本估算** —— 参数表单、带 SHAP 可解释性的实时预测、What-if 情景滑块、相似项目对比、报告导出。

## 性能优化

- **代码分割** —— 路由级与组件级懒加载；第三方库按需加载。
- **缓存** —— Next.js 服务端缓存、客户端数据缓存、HTTP 缓存头。
- **图片** —— Next.js `Image` 组件，配合懒加载与 WebP。
- **打包** —— Tree Shaking、压缩、打包体积监控。

## 安全

- **认证** —— 全程 HTTPS、短期 JWT；防止会话劫持。
- **输入** —— 客户端实时校验 + 服务端校验；CSP 防 XSS。
- **API** —— `/api/v1/` 版本前缀；请求校验；上传文件扫描。

## 开发流程

```bash
npm install      # 安装依赖
npm run dev      # 开发服务器（:3123）
npm run build    # 生产构建
npm run lint     # 代码检查
npm run test     # 测试
```

质量工具链：严格 TypeScript、ESLint、Prettier。

## 兼容性与监控

- **浏览器** —— 现代常青浏览器（Chrome 90+、Firefox 88+、Safari 14+），并支持优雅降级。
- **监控** —— Core Web Vitals（LCP/INP/CLS）、自定义业务指标、前端错误追踪。

---

**文档版本：** 1.1 · **最后更新：** 2026-06-14
