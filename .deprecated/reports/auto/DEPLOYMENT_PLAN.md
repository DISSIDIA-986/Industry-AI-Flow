# Industry AI Flow - 部署方案 (Deployment Plan)

## 环境信息

### 硬件配置
- **设备**: Apple Mac Studio
- **芯片**: M1 Max (Apple Silicon)
- **内存**: 32GB UMA (统一内存架构)
- **架构**: arm64

### 软件环境
- **操作系统**: macOS
- **包管理器**: Homebrew
- **LLM运行时**: Ollama (已安装)
- **Python版本**: Python 3.13 (推荐)

## 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                │
│  FastAPI Backend | Streamlit Frontend | Prompt Admin UI    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  数据层 (Data Layer)                        │
│  PostgreSQL + pgvector | Ollama LLM | File Storage        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              监控与日志层 (Monitoring & Logging)            │
│  Application Logs | Metrics | Health Checks                 │
└─────────────────────────────────────────────────────────────┘
```

## 部署策略

### 1. 本地开发环境部署 (Development)
适用于开发人员日常开发和调试。

### 2. 演示环境部署 (Demo)
适用于向利益相关者演示功能。

### 3. 测试环境部署 (Testing)
适用于测试团队进行功能和性能测试。

## 部署前检查清单

### 系统依赖
- [ ] Homebrew已安装
- [ ] PostgreSQL已安装 (支持pgvector扩展)
- [ ] Ollama已安装并运行
- [ ] Python 3.13已安装
- [ ] Git已安装

### 配置文件
- [ ] `.env`文件已配置
- [ ] 数据库连接已测试
- [ ] Ollama模型已下载
- [ ] 必要的API密钥已配置

### 数据准备
- [ ] 示例数据集已准备
- [ ] 测试文档已准备
- [ ] 向量索引已初始化

## 部署步骤

### 阶段1: 环境准备 (5-10分钟)

#### 1.1 系统依赖安装
```bash
# 安装PostgreSQL (如果尚未安装)
brew install postgresql@15
brew install pgvector

# 安装Python 3.13 (如果尚未安装)
brew install python@3.13

# 安装Redis (可选，用于缓存)
brew install redis
```

#### 1.2 数据库配置
```bash
# 启动PostgreSQL服务
brew services start postgresql@15

# 创建数据库
createdb ai_workflow

# 安装pgvector扩展
psql -d ai_workflow -c "CREATE EXTENSION vector;"
```

#### 1.3 Ollama配置
```bash
# 启动Ollama服务
ollama serve

# 下载所需的模型
ollama pull qwen2.5:7b
ollama pull llama2:7b

# 验证安装
ollama list
curl http://localhost:11434/api/tags
```

### 阶段2: 应用部署 (10-15分钟)

#### 2.1 代码克隆与配置
```bash
# 克隆代码仓库
git clone https://github.com/DISSIDIA-986/Industry-AI-Flow.git
cd Industry-AI-Flow

# 创建并激活虚拟环境
python3.13 -m venv .venv_capstone
source .venv_capstone/bin/activate

# 安装依赖
pip install -r requirements/lock/py313-capstone.txt
```

#### 2.2 环境配置
```bash
# 复制环境变量模板
cp .env.example .env

# 根据实际情况编辑.env文件
# 关键配置项:
# - POSTGRES_HOST=localhost
# - OLLAMA_HOST=http://localhost:11434
# - OLLAMA_MODEL=qwen2.5:7b
# - LLM_PROVIDER=ollama
# - DEMO_MODE=live_hybrid
```

#### 2.3 数据库初始化
```bash
# 运行数据库初始化脚本
python backend/init_database.py

# 运行数据库迁移
alembic upgrade head

# 导入示例数据 (可选)
python scripts/utilities/import_csv_datasets.py --input datasets/sample_data.csv
```

### 阶段3: 应用启动与验证 (5-10分钟)

#### 3.1 启动后端服务
```bash
# 开发模式启动
make run

# 或生产模式启动
make run-prod

# 验证服务健康状态
curl http://localhost:8000/api/intent/health
```

#### 3.2 启动前端服务 (可选)
```bash
# 启动Streamlit应用
make streamlit

# 启动Prompt管理界面
make prompt-admin
```

#### 3.3 运行冒烟测试
```bash
# 运行CI友好的冒烟测试
make test-demo-smoke-gate

# 或运行完整的冒烟测试 (需要外部依赖)
make test-demo-smoke-live-gate
```

## 监控与运维

### 健康检查端点
- **应用健康**: `GET /api/intent/health`
- **数据库状态**: `GET /api/v1/health/db`
- **Ollama状态**: `GET /api/v1/health/ollama`

### 日志位置
- **应用日志**: `logs/application.log`
- **错误日志**: `logs/error.log`
- **访问日志**: `logs/access.log`

### 性能监控
- **响应时间**: 通过FastAPI中间件记录
- **LLM调用成本**: 通过`CostTracker`服务追踪
- **数据库查询性能**: 通过pg_stat_statements监控

## 故障排查指南

### 常见问题

#### 1. PostgreSQL连接失败
```bash
# 检查PostgreSQL服务状态
brew services list

# 启动服务
brew services start postgresql@15

# 检查端口占用
lsof -i :5432
```

#### 2. Ollama连接失败
```bash
# 检查Ollama服务状态
ps aux | grep ollama

# 重启Ollama
pkill ollama
ollama serve &

# 测试连接
curl http://localhost:11434/api/tags
```

#### 3. Python依赖冲突
```bash
# 清除虚拟环境
rm -rf .venv_capstone

# 重新创建
python3.13 -m venv .venv_capstone
source .venv_capstone/bin/activate

# 重新安装依赖
pip install -r requirements/lock/py313-capstone.txt
```

## 回滚策略

### 代码回滚
```bash
# 查看提交历史
git log --oneline

# 回滚到指定版本
git checkout <commit-hash>

# 重新安装依赖
pip install -r requirements/lock/py313-capstone.txt
```

### 数据库回滚
```bash
# 查看迁移历史
alembic history

# 回滚到指定版本
alembic downgrade <revision>
```

## 备份策略

### 数据库备份
```bash
# 备份数据库
pg_dump ai_workflow > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
psql ai_workflow < backup_YYYYMMDD_HHMMSS.sql
```

### 配置备份
```bash
# 备份环境配置
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 备份Prompt目录
tar -czf prompts_backup_$(date +%Y%m%d_%H%M%S).tar.gz prompts/
```

## 性能优化建议

### Apple Silicon优化
1. **使用原生ARM64包**: 确保所有Python包都是arm64架构
2. **UMA内存利用**: 32GB统一内存可用于大模型推理
3. **多线程优化**: FastAPI workers数量设置为CPU核心数

### Ollama优化
1. **模型量化**: 使用量化模型减少内存占用
2. **批处理**: 对请求进行批处理提高吞吐量
3. **缓存策略**: 启用Redis缓存常见查询

### PostgreSQL优化
1. **连接池配置**: 合理配置连接池大小
2. **索引优化**: 为常用查询字段添加索引
3. **向量索引**: 使用HNSW索引加速向量检索

## 安全最佳实践

### 网络安全
- [ ] 仅在本地网络暴露服务 (127.0.0.1)
- [ ] 使用防火墙限制外部访问
- [ ] 启用HTTPS (生产环境)

### 数据安全
- [ ] 敏感数据脱敏
- [ ] 定期备份
- [ ] 访问日志审计

### API安全
- [ ] 实施速率限制
- [ ] 输入验证
- [ ] 输出过滤

## 交付物清单

### 代码交付
- [ ] 源代码 (Git仓库)
- [ ] 依赖清单 (requirements.txt)
- [ ] 配置文件 (.env.example)
- [ ] 数据库迁移脚本

### 文档交付
- [ ] 部署文档 (本文档)
- [ ] 架构文档 (docs/ARCHITECTURE.md)
- [ ] API文档 (OpenAPI规范)
- [ ] 用户手册 (README.md)

### 运维脚本
- [ ] 部署脚本 (scripts/deploy/)
- [ ] 监控脚本 (scripts/monitoring/)
- [ ] 备份脚本 (scripts/backup/)
- [ ] 健康检查脚本 (scripts/health/)

## 联系信息

- **技术支持**: [GitHub Issues](https://github.com/DISSIDIA-986/Industry-AI-Flow/issues)
- **文档**: [项目Wiki](https://github.com/DISSIDIA-986/Industry-AI-Flow/wiki)
- **邮件**: support@example.com