# pgvector 安装指南

## 问题

PostgreSQL 需要 pgvector 扩展才能存储和查询向量数据。

## 解决方案

### 方式一：修复 Homebrew 权限后安装（推荐）

```bash
# 1. 修复权限
sudo chown -R $(whoami) /usr/local/bin /usr/local/include /usr/local/lib /usr/local/share

# 2. 安装 pgvector
brew install pgvector

# 3. 重新运行 setup
bash scripts/setup_local.sh
```

### 方式二：从源码编译安装

```bash
# 1. 克隆仓库
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector

# 2. 编译安装
make
sudo make install

# 3. 重新运行 setup
cd ~/Documents/github.com/Industry-AI-Flow
bash scripts/setup_local.sh
```

### 方式三：跳过 pgvector，使用纯 Python 实现（临时方案）

如果无法安装 pgvector，可以暂时使用纯 Python 的向量搜索实现（性能较差）。

## 验证安装

安装完成后，验证：

```bash
psql ai_workflow -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql ai_workflow -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

应该看到 vector 扩展已安装。
