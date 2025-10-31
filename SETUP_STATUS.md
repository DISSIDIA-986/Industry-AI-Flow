# 环境搭建状态

## ✅ 已完成

1. **PostgreSQL**: ✅ 已安装并运行 (v14.19)
2. **Redis**: ✅ 已安装并运行 (v7.0.0)
3. **Ollama**: ✅ 已安装
4. **Python**: ✅ v3.13.5 (miniconda)
5. **数据库**: ✅ ai_workflow 已创建
6. **Python依赖**: 🔄 正在安装...

## ⚠️ 待解决

### pgvector 扩展未安装

**问题**: PostgreSQL 需要 pgvector 扩展来存储向量数据

**解决方案**（选择其一）:

#### 方式一：修复 Homebrew 权限（最简单）

```bash
# 修复权限
sudo chown -R $(whoami) /usr/local/bin /usr/local/include /usr/local/lib /usr/local/share

# 安装 pgvector
brew install pgvector
```

#### 方式二：从源码安装

```bash
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

#### 验证安装

```bash
psql ai_workflow -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 📋 下一步操作

### 1. 安装 pgvector（必需）

运行上述任一方式安装 pgvector

### 2. 完成环境搭建

```bash
# 重新运行 setup 脚本
bash scripts/setup_local.sh
```

### 3. 验证环境

```bash
bash scripts/verify_env.sh
```

### 4. 下载 Ollama 模型

```bash
ollama pull qwen2.5:7b
```

这个模型约 5GB，需要 5-10 分钟下载时间。

### 5. 启动 API 服务

```bash
# 确保环境变量配置
cp .env.example .env

# 启动服务
cd backend && python main.py
```

### 6. 测试 RAG 系统

```bash
# 导入测试文档
python scripts/import_docs.py ./samples/

# 运行评估测试
python scripts/test_rag.py
```

## 📞 需要帮助？

查看详细文档：
- 完整指南: `README.md`
- pgvector安装: `INSTALL_PGVECTOR.md`
- 实施规范: `research/local-development-feasibility.prompt.v2.md`
