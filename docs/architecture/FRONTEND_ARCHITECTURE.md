# 前端架构设计文档

> 🌐 Language: **中文** · [English](./FRONTEND_ARCHITECTURE.en.md)

## 架构概述

Industry AI Flow前端采用现代化的前后端分离架构，基于Next.js 14构建，提供高性能、可扩展的用户界面。

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js 14 应用层                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                App Router (App Directory)           │  │
│  │  • 页面路由 (Page Routes)                           │  │
│  │  • 布局组件 (Layout Components)                     │  │
│  │  • 服务端组件 (Server Components)                   │  │
│  │  • 客户端组件 (Client Components)                   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                 React 组件层                         │  │
│  │  • UI组件库 (Forms, Tables, Cards, Modals)          │  │
│  │  • 业务组件 (Chat, DocumentManager, Dashboard)      │  │
│  │  • 共享组件 (Navbar, Sidebar, Footer)               │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                 状态管理层                           │  │
│  │  • React Context (Auth, AppConfig)                  │  │
│  │  • 本地状态 (useState, useReducer)                  │  │
│  │  • 服务端状态 (React Query / SWR)                   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  API集成层                           │
│  │  • API客户端 (RESTful API调用)                      │  │
│  │  • WebSocket客户端 (实时通信)                       │  │
│  │  • 错误处理和重试机制                               │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI 后端服务层                         │
│  • 认证授权 (JWT, OAuth2)                                 │
│  • 业务逻辑 (AI工作流, 文档处理)                          │
│  • 数据存储 (PostgreSQL, pgvector)                        │
│  • 文件存储 (MinIO / S3)                                  │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

### 核心框架
- **Next.js 14**: 全栈React框架，支持App Router和Server Components
- **React 18**: 现代React版本，支持并发特性
- **TypeScript**: 类型安全的JavaScript超集
- **Tailwind CSS**: 实用优先的CSS框架

### 状态管理
- **React Context**: 全局状态管理（认证、应用配置）
- **React Query**: 服务端状态管理和数据获取
- **Zustand**: 轻量级状态管理（可选）

### API集成
- **Fetch API**: 现代浏览器原生API
- **Axios**: HTTP客户端（备用）
- **WebSocket**: 实时通信
- **React Hook Form**: 表单处理

### 组件库
- **自定义组件库**: 项目特定的UI组件
- **Headless UI**: 无样式UI组件
- **Heroicons**: SVG图标库
- **Recharts**: 数据可视化图表

## 目录结构

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── (mvp)/                    # MVP功能页面组
│   │   │   ├── layout.tsx            # MVP布局
│   │   │   ├── overview/             # 概览页面
│   │   │   ├── workflow-chat/        # 工作流聊天
│   │   │   ├── documents/            # 文档管理
│   │   │   ├── data-dashboard/       # 数据仪表板
│   │   │   ├── cost-estimation/      # 成本估算
│   │   │   ├── prompt-admin/         # Prompt管理
│   │   │   └── components-demo/      # 组件演示
│   │   ├── (simple)/                 # 简化版页面组
│   │   ├── login/                    # 登录页面
│   │   ├── register/                 # 注册页面
│   │   ├── api/                      # API路由（前端代理）
│   │   ├── layout.tsx                # 根布局
│   │   └── globals.css               # 全局样式
│   │
│   ├── components/                   # React组件
│   │   ├── forms/                    # 表单组件
│   │   ├── tables/                   # 表格组件
│   │   ├── cards/                    # 卡片组件
│   │   ├── modals/                   # 模态框组件
│   │   ├── feedback/                 # 反馈组件
│   │   ├── files/                    # 文件组件
│   │   ├── charts/                   # 图表组件
│   │   ├── layout/                   # 布局组件
│   │   ├── ProtectedRoute.tsx        # 受保护路由
│   │   └── Navbar.tsx                # 导航栏
│   │
│   ├── contexts/                     # React上下文
│   │   ├── AuthContext.tsx           # 认证上下文
│   │   └── AppConfigContext.tsx      # 应用配置上下文
│   │
│   ├── hooks/                        # 自定义Hook
│   │   ├── useAuth.ts                # 认证Hook
│   │   ├── useApi.ts                 # API调用Hook
│   │   └── useWebSocket.ts           # WebSocket Hook
│   │
│   ├── lib/                          # 工具库
│   │   ├── api-client.ts             # API客户端
│   │   ├── websocket-client.ts       # WebSocket客户端
│   │   ├── formatters.ts             # 格式化工具
│   │   ├── validators.ts             # 验证工具
│   │   └── constants.ts              # 常量定义
│   │
│   └── styles/                       # 样式文件
│       ├── components.css            # 组件样式
│       └── themes.css                # 主题样式
│
├── public/                           # 静态资源
│   ├── favicon.ico                   # 网站图标
│   ├── images/                       # 图片资源
│   └── fonts/                        # 字体文件
│
├── package.json                      # 依赖配置
├── next.config.js                    # Next.js配置
├── tailwind.config.js                # Tailwind配置
├── tsconfig.json                     # TypeScript配置
└── .env.local                        # 环境变量
```

## 核心功能模块

### 1. 用户认证系统
- **登录/注册**: 基于JWT的认证流程
- **会话管理**: 自动token刷新和过期处理
- **权限控制**: 基于角色的访问控制
- **社交登录**: OAuth2集成（可选）

### 2. 工作流聊天界面
- **实时聊天**: WebSocket双向通信
- **消息历史**: 本地存储和服务器同步
- **文件上传**: 拖拽上传和进度显示
- **意图识别**: AI意图分类展示

### 3. 文档管理系统
- **文档上传**: 批量上传和格式验证
- **文档预览**: PDF、Word、Excel预览
- **文档搜索**: 全文检索和过滤
- **版本控制**: 文档版本管理

### 4. 数据可视化仪表板
- **实时监控**: 系统状态和性能指标
- **图表展示**: 多种图表类型支持
- **数据导出**: CSV、Excel、PDF导出
- **自定义视图**: 用户可配置的仪表板

### 5. 成本估算工具
- **参数输入**: 项目参数表单
- **实时计算**: 成本预测和风险评估
- **结果对比**: 多方案比较
- **报告生成**: 详细估算报告

## 性能优化策略

### 1. 代码分割
- **路由级分割**: 按页面动态加载
- **组件级分割**: 大型组件懒加载
- **库级分割**: 第三方库按需加载

### 2. 缓存策略
- **服务端缓存**: Next.js内置缓存
- **客户端缓存**: React Query缓存
- **浏览器缓存**: HTTP缓存头

### 3. 图片优化
- **Next.js Image**: 自动图片优化
- **懒加载**: 视口内图片加载
- **格式转换**: WebP格式支持

### 4. 打包优化
- **Tree Shaking**: 未使用代码移除
- **代码压缩**: JavaScript和CSS压缩
- **Bundle分析**: 打包体积监控

## 安全考虑

### 1. 认证安全
- **JWT安全**: HTTPS传输，短期token
- **密码安全**: 加盐哈希存储
- **会话安全**: 防止会话劫持

### 2. 输入验证
- **客户端验证**: 实时表单验证
- **服务端验证**: API参数验证
- **XSS防护**: 内容安全策略

### 3. 数据保护
- **敏感数据**: 本地存储加密
- **API安全**: 请求签名和防重放
- **文件安全**: 上传文件扫描

## 开发工作流

### 1. 本地开发
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 运行测试
npm run test

# 代码检查
npm run lint
```

### 2. 构建部署
```bash
# 生产构建
npm run build

# 启动生产服务器
npm start

# 静态导出（可选）
npm run export
```

### 3. 代码质量
- **TypeScript**: 严格类型检查
- **ESLint**: 代码规范检查
- **Prettier**: 代码格式化
- **Husky**: Git钩子

## 向后兼容性

### 1. API版本控制
- **API版本**: `/api/v1/` 前缀
- **向后兼容**: 旧版本API支持
- **弃用策略**: 逐步迁移计划

### 2. 浏览器支持
- **现代浏览器**: Chrome 90+, Firefox 88+, Safari 14+
- **渐进增强**: 基础功能降级支持
- **Polyfill**: 必要的polyfill支持

## 监控和日志

### 1. 性能监控
- **Core Web Vitals**: LCP, FID, CLS
- **自定义指标**: 业务相关指标
- **错误跟踪**: 前端错误收集

### 2. 用户分析
- **用户行为**: 页面浏览和交互
- **功能使用**: 功能使用统计
- **性能分析**: 用户端性能数据

---

**文档版本**: 1.0  
**最后更新**: 2026-02-14  
**维护者**: Industry AI Flow开发团队