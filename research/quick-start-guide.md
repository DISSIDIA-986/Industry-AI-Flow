# Industry AI Flow 快速启动指南

## 环境要求

### 硬件要求：
- Mac Studio M1 Max 32GB RAM（最低要求）
- 100GB可用磁盘空间
- 稳定的网络连接（混合架构需要）

### 软件要求：
- macOS 14.0+
- Docker Desktop 4.25+
- Python 3.11+
- Ollama 0.1.30+

## 5分钟快速启动

### 步骤1：基础环境安装

```bash
# 1. 安装Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装Ollama
brew install ollama

# 3. 安装Docker Desktop
# 从 https://www.docker.com/products/docker-desktop/ 下载安装

# 4. 安装Python依赖
pip install langchain chromadb sentence-transformers pandas numpy
```

### 步骤2：下载并运行模型

```bash
# 1. 拉取DeepSeek-Coder-7B模型（Q4量化版）
ollama pull deepseek-coder:7b-q4_K_M

# 2. 启动Ollama服务
ollama serve &

# 3. 验证模型运行
curl http://localhost:11434/api/generate -d '{
  "model": "deepseek-coder:7b-q4_K_M",
  "prompt": "def hello_world():",
  "stream": false
}'
```

### 步骤3：启动沙箱环境

```bash
# 1. 创建沙箱Docker镜像
cat > Dockerfile.sandbox << 'EOF'
FROM python:3.11-slim

WORKDIR /app
RUN pip install pandas numpy

# 创建非root用户
RUN useradd -m -u 1000 sandbox && chown -R sandbox:sandbox /app
USER sandbox

CMD ["python", "-c", "print('Sandbox ready')"]
EOF

# 2. 构建镜像
docker build -f Dockerfile.sandbox -t ai-sandbox .

# 3. 测试沙箱
docker run --rm --memory="512m" --cpus="1" ai-sandbox
```

### 步骤4：运行示例应用

```python
# quick_demo.py
import requests
import json
import subprocess
import time

class QuickDemo:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        
    def generate_code(self, requirement: str) -> str:
        """使用本地模型生成代码"""
        prompt = f"""
        请为以下需求生成Python代码：
        需求：{requirement}
        
        要求：
        1. 使用pandas处理数据
        2. 包含错误处理
        3. 输出格式化结果
        
        只返回代码，不要解释。
        """
        
        response = requests.post(self.ollama_url, json={
            "model": "deepseek-coder:7b-q4_K_M",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 500
            }
        })
        
        return response.json()["response"]
    
    def execute_in_sandbox(self, code: str) -> dict:
        """在Docker沙箱中执行代码"""
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 在沙箱中执行
            result = subprocess.run([
                'docker', 'run', '--rm',
                '--memory=512m',
                '--cpus=1',
                '--network=none',
                '-v', f'{temp_file}:/app/code.py',
                'ai-sandbox',
                'python', '/app/code.py'
            ], capture_output=True, text=True, timeout=30)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
        finally:
            import os
            os.unlink(temp_file)
    
    def demo_cost_calculation(self):
        """演示成本计算功能"""
        requirement = """
        计算项目成本：
        1. 人工成本：每小时$50，共80小时
        2. 材料成本：$5000
        3. 设备租赁：$2000
        4. 税费：总成本的15%
        请计算总成本并生成详细报告。
        """
        
        print("📊 生成成本计算代码...")
        code = self.generate_code(requirement)
        print(f"生成的代码：\n{code}\n")
        
        print("🔒 在沙箱中执行代码...")
        result = self.execute_in_sandbox(code)
        
        if result['success']:
            print("✅ 执行成功！")
            print(f"输出：\n{result['output']}")
        else:
            print("❌ 执行失败")
            print(f"错误：\n{result['error']}")

if __name__ == "__main__":
    demo = QuickDemo()
    demo.demo_cost_calculation()
```

运行演示：
```bash
python quick_demo.py
```

## 完整配置示例

### 配置文件：`config.yaml`

```yaml
# Industry AI Flow 配置文件
version: "1.0"

# LLM配置
llm:
  local:
    model: "deepseek-coder:7b-q4_K_M"
    endpoint: "http://localhost:11434"
    timeout: 30
    max_tokens: 1024
  
  cloud:
    enabled: false  # 初始禁用混合模式
    provider: "openai"
    model: "gpt-4"
    api_key: "${OPENAI_API_KEY}"
    fallback_to_local: true

# RAG配置
rag:
  vector_store:
    type: "chromadb"
    path: "./data/vector_store"
    embedding_model: "all-MiniLM-L6-v2"
  
  retrieval:
    top_k: 5
    similarity_threshold: 0.7
    hybrid_search: true

# 沙箱配置
sandbox:
  type: "docker"
  image: "ai-sandbox"
  resources:
    memory: "512m"
    cpus: 1
    timeout: 30
  
  security:
    network_disabled: true
    read_only: true
    user: "sandbox"
    capabilities_drop: ["ALL"]

# 业务配置
business:
  cost_calculation:
    default_currency: "USD"
    tax_rate: 0.15
    labor_rate: 50
    
  reporting:
    format: "markdown"
    include_charts: true
    auto_save: true

# 监控配置
monitoring:
  enabled: true
  metrics:
    - "response_time"
    - "accuracy"
    - "cost_per_request"
  
  logging:
    level: "INFO"
    path: "./logs"
    retention_days: 30
```

### 环境变量文件：`.env`

```bash
# API密钥（混合模式使用）
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here

# 应用配置
APP_ENV=development
APP_PORT=8000
APP_SECRET=change_this_in_production

# 数据库配置
DATABASE_URL=sqlite:///./data/app.db

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

## 常见问题解决

### 问题1：Ollama模型下载慢
```bash
# 使用镜像加速
export OLLAMA_HOST="https://ollama.mirror.example.com"
ollama pull deepseek-coder:7b-q4_K_M
```

### 问题2：Docker内存不足
```bash
# 调整Docker资源限制
# 1. 打开Docker Desktop
# 2. 进入Settings → Resources
# 3. 调整Memory到8GB以上
# 4. 重启Docker
```

### 问题3：Python依赖冲突
```bash
# 使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 问题4：模型响应慢
```bash
# 优化Ollama配置
cat > ~/.ollama/config.json << 'EOF'
{
  "models": {
    "deepseek-coder:7b-q4_K_M": {
      "num_gpu": 1,
      "num_thread": 8,
      "batch_size": 512
    }
  }
}
EOF

# 重启Ollama
pkill ollama
ollama serve &
```

## 性能调优指南

### 1. 模型量化选择
```bash
# 测试不同量化级别
ollama pull deepseek-coder:7b-q2_K  # 最小，最快
ollama pull deepseek-coder:7b-q4_K_M  # 推荐平衡
ollama pull deepseek-coder:7b-q6_K  # 最高精度
```

### 2. 批处理优化
```python
# 批量处理请求
import asyncio
from typing import List

async def batch_generate(prompts: List[str], batch_size: int = 4):
    """批量生成代码，提高吞吐量"""
    results = []
    for i in range(0, len(prompts), batch_size):
        batch = prompts[i:i+batch_size]
        tasks = [generate_single(prompt) for prompt in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
    return results
```

### 3. 缓存策略
```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_generation(prompt: str, model: str) -> str:
    """缓存常见查询结果"""
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
    cache_key = f"{model}:{prompt_hash}"
    
    # 检查缓存
    if cache_key in generation_cache:
        return generation_cache[cache_key]
    
    # 生成并缓存
    result = generate_code(prompt, model)
    generation_cache[cache_key] = result
    return result
```

## 安全检查清单

### 部署前检查：
- [ ] 所有API密钥已加密存储
- [ ] 数据库连接使用SSL
- [ ] 防火墙规则已配置
- [ ] 访问日志已启用
- [ ] 备份策略已实施

### 运行时检查：
- [ ] 沙箱网络隔离正常
- [ ] 资源限制生效
- [ ] 审计日志记录完整
- [ ] 异常检测系统运行

### 定期检查：
- [ ] 安全漏洞扫描（每周）
- [ ] 权限审计（每月）
- [ ] 数据备份验证（每日）
- [ ] 性能基准测试（每月）

## 下一步行动

### 短期（1周内）：
1. 完成基础环境搭建
2. 运行快速演示验证
3. 收集性能基准数据

### 中期（1个月内）：
1. 集成企业知识库
2. 开发完整业务功能
3. 进行安全测试

### 长期（3个月内）：
1. 部署生产环境
2. 建立监控系统
3. 优化性能与成本

## 获取帮助

### 文档资源：
- [Ollama官方文档](https://github.com/ollama/ollama)
- [LangChain文档](https://python.langchain.com/)
- [Docker安全最佳实践](https://docs.docker.com/engine/security/)

### 社区支持：
- GitHub Issues: 项目问题跟踪
- Discord社区: AI开发者交流
- Stack Overflow: 技术问题解答

### 紧急联系：
- 安全漏洞报告: security@example.com
- 技术支持: support@example.com
- 业务咨询: business@example.com

---

*指南版本: 1.0*
*最后更新: 2026年2月6日*
*适用环境: Mac Studio M1 Max 32GB*