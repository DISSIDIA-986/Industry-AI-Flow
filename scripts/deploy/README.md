# 部署脚本使用指南

本目录包含Industry AI Flow项目的自动化部署脚本，适用于Apple Mac Studio (M1 Max, 32GB RAM)环境。

## 脚本列表

### 1. one_click_deploy.sh - 一键部署脚本
**用途**: 快速部署，适用于演示和测试环境
**特点**: 
- 自动化程度高，无需人工干预
- 包含完整的部署流程
- 适合首次部署和快速测试

**使用方法**:
```bash
chmod +x one_click_deploy.sh
./one_click_deploy.sh
```

**输出**:
- 系统环境检查结果
- 部署进度
- 服务访问地址
- 常用命令提示

---

### 2. deploy.sh - 完整部署脚本
**用途**: 交互式完整部署，支持自定义部署流程
**特点**:
- 交互式菜单，灵活选择部署步骤
- 详细的日志输出
- 支持分步骤部署
- 包含健康检查

**使用方法**:
```bash
chmod +x deploy.sh
./deploy.sh
```

**菜单选项**:
1. 完整部署 (推荐)
2. 仅检查环境
3. 仅安装依赖
4. 仅配置数据库
5. 仅配置Ollama
6. 仅部署应用
7. 仅启动服务
8. 仅运行测试
9. 退出

---

### 3. monitor.sh - 系统监控脚本
**用途**: 实时监控系统健康状态
**特点**:
- 实时显示系统资源使用情况
- 监控服务运行状态
- 显示最近日志
- 自动刷新 (5秒间隔)

**使用方法**:
```bash
chmod +x monitor.sh
./monitor.sh
```

**监控内容**:
- CPU和内存使用率
- 服务运行状态
- 端口占用情况
- HTTP端点响应
- 最近5行日志

**退出**: 按Ctrl+C

---

### 4. health_check.sh - 健康检查脚本
**用途**: 一次性系统健康检查
**特点**:
- 全面的系统检查
- 彩色输出，易于阅读
- 生成健康评分
- 提供详细的诊断信息

**使用方法**:
```bash
chmod +x health_check.sh
./health_check.sh
```

**检查项**:
- 硬件信息
- 系统依赖
- 服务状态
- 端口检查
- HTTP端点
- 数据库状态
- Ollama模型
- 应用配置

**输出**:
- PASS (通过): 绿色 ✓
- WARN (警告): 黄色 ⚠
- FAIL (失败): 红色 ✗
- 健康评分百分比

---

## 部署流程

### 推荐流程 (演示环境)

```bash
# 1. 使用一键部署脚本
./one_click_deploy.sh

# 2. 打开新终端窗口，运行监控
./monitor.sh

# 3. 运行健康检查
./health_check.sh

# 4. 访问应用
open http://localhost:8000/docs
```

### 推荐流程 (测试环境)

```bash
# 1. 使用交互式部署脚本
./deploy.sh

# 2. 选择选项1 (完整部署)
# 或根据需要选择单独步骤

# 3. 部署完成后运行健康检查
./health_check.sh

# 4. 运行完整测试套件
cd ../..
make test-demo-smoke-live-gate

# 5. 启动监控
./scripts/deploy/monitor.sh
```

---

## 常见问题

### 1. 权限错误
**问题**: bash: ./deploy.sh: Permission denied
**解决**: 
```bash
chmod +x *.sh
```

### 2. Python版本不匹配
**问题**: Python版本不是3.13
**解决**: 
```bash
# 使用默认Python版本
# 修改脚本中的 python3.13 为 python3 或 python
```

### 3. Ollama模型下载失败
**问题**: ollama pull命令失败
**解决**: 
```bash
# 手动启动Ollama服务
ollama serve

# 在新终端下载模型
ollama pull qwen2.5:7b
```

### 4. PostgreSQL连接失败
**问题**: 无法连接到数据库
**解决**: 
```bash
# 启动PostgreSQL服务
brew services start postgresql@15

# 创建数据库
createdb ai_workflow

# 安装扩展
psql -d ai_workflow -c "CREATE EXTENSION vector;"
```

### 5. 端口已被占用
**问题**: 端口8000已被占用
**解决**: 
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

---

## 日志文件位置

- **应用日志**: `../../logs/application.log`
- **错误日志**: `../../logs/error.log`
- **访问日志**: `../../logs/access.log`

查看实时日志:
```bash
tail -f ../../logs/application.log
```

---

## 服务管理

### 启动服务
```bash
# 启动后端服务
cd ../..
make run
# 或
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs/application.log 2>&1 &
```

### 停止服务
```bash
# 使用Makefile
cd ../..
make stop

# 或手动杀死进程
pkill -f 'uvicorn backend.main:app'
```

### 重启服务
```bash
# 停止服务
pkill -f 'uvicorn backend.main:app'

# 启动服务
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs/application.log 2>&1 &
```

---

## 配置文件

### 环境变量 (.env)
```bash
# 复制模板
cp ../../.env.example ../../.env

# 编辑配置
nano ../../.env
```

### 关键配置项
```bash
# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_workflow

# Ollama配置
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# LLM提供商
LLM_PROVIDER=ollama

# 演示模式
DEMO_MODE=live_hybrid
```

---

## 备份与恢复

### 数据库备份
```bash
# 备份
pg_dump ai_workflow > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复
psql ai_workflow < backup_YYYYMMDD_HHMMSS.sql
```

### 配置备份
```bash
# 备份环境配置
cp ../../.env ../../.env.backup.$(date +%Y%m%d_%H%M%S)

# 备份Prompt目录
tar -czf prompts_backup_$(date +%Y%m%d_%H%M%S).tar.gz ../../prompts/
```

---

## 性能优化

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

---

## 技术支持

如遇问题，请访问:
- GitHub Issues: https://github.com/DISSIDIA-986/Industry-AI-Flow/issues
- 项目文档: https://github.com/DISSIDIA-986/Industry-AI-Flow/wiki
- 部署文档: ../DEPLOYMENT_PLAN.md

---

## 版本信息

- **脚本版本**: 1.0.0
- **最后更新**: 2026-02-13
- **适用环境**: Apple Mac Studio (M1 Max, 32GB RAM)
- **操作系统**: macOS (Apple Silicon)