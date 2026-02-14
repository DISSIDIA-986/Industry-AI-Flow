# 根因分析 (RCA) - 后端启动失败

## 问题概述

**现象**: 后端服务无法启动，API端点无响应
**影响**: 所有API功能不可用，系统无法交付给QA团队
**优先级**: P0 - 关键
**日期**: 2026-02-13

---

## 可能的根本原因分析

### 假设1: Ollama连接失败 ⚠️ 高概率

**描述**: 应用可能无法连接到Ollama服务，导致启动失败

**验证步骤**:
```bash
# 测试Ollama连接
curl -v http://localhost:11434/api/tags
```

**可能原因**:
1. Ollama监听在127.0.0.1而非0.0.0.0
2. 端口11434被防火墙阻止
3. Ollama服务启动异常

**修复方案**:
```bash
# 检查Ollama监听地址
lsof -i :11434

# 如果需要，重启Ollama
pkill ollama
ollama serve &

# 或在应用中调整连接地址
# 确保.env中OLLAMA_HOST正确
```

### 假设2: 数据库连接问题 ⚠️ 高概率

**描述**: 应用可能无法连接到PostgreSQL 17

**验证步骤**:
```bash
# 测试数据库连接
/opt/homebrew/opt/postgresql@17/bin/psql -d ai_workflow -c "SELECT 1;"

# 检查端口
netstat -an | grep 5432
```

**可能原因**:
1. PostgreSQL 17运行在5433端口而非5432
2. 数据库用户权限问题
3. 数据库连接字符串配置错误

**修复方案**:
```bash
# 确认PostgreSQL 17端口
brew services list | grep postgresql

# 检查实际监听端口
/opt/homebrew/opt/postgresql@17/bin/postgres -c "SHOW port;"

# 测试连接
/opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -d ai_workflow
```

### 假设3: Python依赖冲突或缺失 ⚠️ 中等概率

**描述**: 关键依赖可能未安装或版本不兼容

**验证步骤**:
```bash
# 检查关键依赖
source .venv_capstone/bin/activate
pip list | grep -E "(fastapi|uvicorn|pydantic|langchain)"
```

**可能原因**:
1. pydantic版本不兼容
2. langchain未正确安装
3. 其他依赖缺失

**修复方案**:
```bash
# 重新安装所有依赖
pip install --upgrade -r requirements/lock/py313-capstone.txt

# 如果有特定包冲突，尝试
pip uninstall pydantic
pip install pydantic==1.10.0
```

### 假设4: 端口冲突或占用 ⚠️ 中等概率

**描述**: 8000端口可能被其他进程占用

**验证步骤**:
```bash
# 检查端口占用
lsof -i :8000

# 查看所有uvicorn进程
ps aux | grep uvicorn
```

**修复方案**:
```bash
# 杀死占用端口的进程
kill -9 $(lsof -t -i :8000)

# 或使用其他端口
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

---

## 调试执行计划

### 阶段1: 快速诊断 (5分钟)

**目标**: 收集基础信息

```bash
# 1. 检查环境变量
cat .env

# 2. 测试数据库连接
source .venv_capstone/bin/activate
python -c "from backend.config import settings; print(settings.DATABASE_URL)"

# 3. 测试Ollama连接
python -c "import requests; r=requests.get('http://localhost:11434/api/tags'); print(r.status_code)"

# 4. 检查Python路径
which python3
python3 --version
```

### 阶段2: 日志分析 (10分钟)

**目标**: 查看详细错误信息

```bash
# 1. 查看系统日志
log show --predicate 'processImagePath contains "uvicorn"' --last 30m

# 2. 手动启动应用（前台运行）
source .venv_capstone/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 3. 查看启动日志
tail -100 logs/application.log

# 4. 检查Python错误
python backend/main.py 2>&1 | tee startup_error.log
```

### 阶段3: 依赖验证 (5分钟)

**目标**: 确保所有依赖正确安装

```bash
# 1. 检查关键依赖
source .venv_capstone/bin/activate
pip check

# 2. 重新安装核心依赖
pip install --upgrade fastapi uvicorn pydantic langchain

# 3. 验证langchain安装
python -c "import langchain; print(langchain.__version__)"
```

---

## 团队协作计划

### DevOps团队任务

1. **基础设施验证**
   - 确认PostgreSQL 17端口和连接性
   - 验证Ollama服务状态和端口
   - 检查网络连接和防火墙设置

2. **日志收集**
   - 提供完整的系统日志
   - 检查资源使用情况
   - 验证环境配置

### 开发团队任务

1. **应用调试**
   - 查看应用启动日志
   - 检查配置文件正确性
   - 验证所有导入语句

2. **依赖修复**
   - 解决任何依赖冲突
   - 更新requirements文件
   - 测试导入顺序

### 协作流程

1. **DevOps**先进行基础设施验证
2. 提供验证结果给**开发团队**
3. **开发团队**基于基础设施状态调试应用
4. 双方共同制定最终修复方案
5. **DevOps**执行修复并验证
6. 进行二次冒烟测试确认问题解决

---

## 成功标准

### 修复后必须满足

1. ✅ 后端服务成功启动
2. ✅ API健康端点返回200
3. ✅ 日志中无严重错误
4. ✅ 可以成功发起API请求

### 冒烟测试重测标准

1. ✅ 所有当前通过的测试继续通过
2. ✅ 后端服务测试通过
3. ✅ API端点测试通过
4. ✅ 总体通过率 > 90%

---

## 下一步行动

### 立即执行 (现在)

**DevOps团队**:
1. 检查PostgreSQL 17监听端口
2. 验证Ollama连接性
3. 提供环境变量状态

**开发团队**:
1. 准备调试版本的main.py
2. 准备完整的依赖检查脚本
3. 准备手动测试数据库连接的脚本

### 预计时间线

- **诊断**: 15分钟
- **修复**: 30分钟
- **验证**: 15分钟
- **总计**: 60分钟

---

**文档作者**: DevOps & Development Teams
**更新时间**: 2026-02-13 17:01 MST
**状态**: 等待团队协作开始