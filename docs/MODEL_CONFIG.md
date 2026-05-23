# SerpentAI 模型配置指南

本文档介绍如何配置 SerpentAI 使用真实 AI 模型（OpenAI、Anthropic、Llama.cpp）。

## 目录

1. [快速开始](#快速开始)
2. [OpenAI 模型配置](#openai-模型配置)
3. [Anthropic 模型配置](#anthropic-模型配置)
4. [Llama.cpp 本地模型配置](#llamacpp-本地模型配置)
5. [模型选择策略](#模型选择策略)
6. [成本控制](#成本控制)
7. [故障排除](#故障排除)

---

## 快速开始

### 1. 复制配置模板

```bash
cd serpent-ai
cp .env.example .env
```

### 2. 编辑 `.env` 填写 API Key

```bash
# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
```

### 3. 启动服务器

```bash
python start_server.py
```

### 4. 验证模型初始化

```bash
# 查看日志
tail -f logs/serpent-ai.log

# 成功日志示例：
# INFO: OpenAI适配器初始化成功: gpt-4o
# INFO: Anthropic适配器初始化成功: claude-3-sonnet
```

---

## OpenAI 模型配置

### 支持的模型

| 模型 | 上下文长度 | 输入价格 ($/1K tokens) | 输出价格 ($/1K tokens) |
|------|------------|------------------------|------------------------|
| gpt-4o | 128,000 | 0.005 | 0.015 |
| gpt-4o-mini | 128,000 | 0.00015 | 0.0006 |
| gpt-4-turbo | 128,000 | 0.01 | 0.03 |
| gpt-3.5-turbo | 16,385 | 0.0005 | 0.0015 |
| o1-preview | 128,000 | 0.015 | 0.06 |
| o1-mini | 128,000 | 0.0003 | 0.0012 |

### 配置方式

#### 方式1：环境变量（推荐）

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
OPENAI_API_BASE=https://api.openai.com/v1  # 可选：自定义端点
```

#### 方式2：代码配置

```python
from backend.models.registry import get_global_registry, ModelRegistry

registry = get_global_registry()

# 注册自定义 OpenAI 模型
registry.register_model(
    name="gpt-4o-custom",
    adapter_class=OpenAIAdapter,
    config={
        "api_key": "sk-your-key",
        "base_url": "https://your-custom-endpoint/v1",
        "temperature": 0.5,  # 可选：默认温度
        "max_tokens": 4096,   # 可选：默认最大 tokens
    }
)
```

### 代理/防火墙场景

如果使用代理访问 OpenAI API：

```bash
# 设置环境变量
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# 或在 .env 中配置 base_url 指向内部代理
OPENAI_API_BASE=http://internal-proxy.example.com/v1
```

### 使用 Azure OpenAI

```bash
# .env
OPENAI_API_KEY=your-azure-api-key
OPENAI_API_BASE=https://your-resource-name.openai.azure.com/xxd/deployments
```

```python
# 自定义注册
registry.register_model(
    name="azure-gpt4",
    adapter_class=OpenAIAdapter,
    config={
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": "https://your-resource.openai.azure.com/xxd/deployments/your-deployment-name",
        "api_version": "2024-02-15-preview",
    }
)
```

---

## Anthropic 模型配置

### 支持的模型

| 模型 | 上下文长度 | 输入价格 ($/1K tokens) | 输出价格 ($/1K tokens) |
|------|------------|------------------------|------------------------|
| claude-3-opus | 200,000 | 0.015 | 0.075 |
| claude-3-sonnet | 200,000 | 0.003 | 0.015 |
| claude-3-haiku | 200,000 | 0.00025 | 0.00125 |
| claude-2.1 | 200,000 | 0.008 | 0.024 |

### 配置方式

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_API_BASE=https://api.anthropic.com  # 可选：自定义端点
```

### 使用 Anthropic Claude 3

```python
# 默认模型配置在 registry.py 的 init_default_models() 中
# 自动注册：claude-3-opus, claude-3-sonnet, claude-3-haiku

# 手动注册
from backend.models.anthropic_adapter import AnthropicAdapter
from backend.models.registry import get_global_registry

registry = get_global_registry()
registry.register_model(
    name="claude-3-sonnet",
    adapter_class=AnthropicAdapter,
    config={
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "temperature": 0.3,
    }
)
```

---

## Llama.cpp 本地模型配置

### 安装 Llama.cpp Python 绑定

```bash
# 安装 llama-cpp-python
pip install llama-cpp-python

# 或带 GPU 加速（需要 CUDA）
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
```

### 下载 GGUF 模型文件

```bash
# 使用 huggingface_hub 下载
from huggingface_hub import hf_hub_download

model_path = hf_hub_download(
    repo_id="TheBloke/Llama-3-8B-Instruct-GGUF",
    filename="llama-3-8b-instruct.q4_k_m.gguf",
    local_dir="./models"
)
```

或手动下载：
1. 访问 [Hugging Face](https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF)
2. 下载 `.gguf` 文件
3. 放置到 `./models/` 目录

### 配置方式

#### 方式1：环境变量

```bash
# .env
LLAMA_CPP_THREADS=8           # CPU 线程数（建议 = CPU 核心数）
LLAMA_CPP_GPU_LAYERS=32     # GPU 加速层数（0=仅CPU）
LLAMA_MODEL_PATH=./models/llama-3-8b-instruct.q4_k_m.gguf
```

#### 方式2：代码配置

```python
from backend.models.llama_adapter import LlamaAdapter
from backend.models.registry import get_global_registry

registry = get_global_registry()
registry.register_model(
    name="llama-3-8b",
    adapter_class=LlamaAdapter,
    config={
        "model_path": "./models/llama-3-8b-instruct.q4_k_m.gguf",
        "n_ctx": 8192,      # 上下文长度
        "n_threads": 8,      # CPU 线程数
        "n_gpu_layers": 32,  # GPU 加速层数
    }
)
```

### 支持的模型

SerpentAI 已内置以下模型配置：

| 模型 | 推荐上下文长度 | 推荐线程数 | GPU 层数 |
|------|----------------|-------------|-----------|
| llama-3-8b | 8,192 | 4-8 | 32 |
| llama-3-70b | 8,192 | 8-16 | 64 |
| mistral-7b | 8,192 | 4-8 | 32 |
| qwen-7b | 8,192 | 4-8 | 32 |
| gemma-7b | 8,192 | 4-8 | 32 |

### 性能优化

#### CPU 优化

```bash
# 设置线程数（建议 = 物理核心数）
LLAMA_CPP_THREADS=8

# 在代码中
adapter = LlamaAdapter("llama-3-8b", config={
    "n_threads": 8,
    "n_batch": 512,  # 批处理大小
})
```

#### GPU 加速

```bash
# 设置 GPU 加速层数（需要 CUDA）
LLAMA_CPP_GPU_LAYERS=32  # 0=仅CPU，32=部分GPU，70=全GPU

# 检查 GPU 状态
nvidia-smi
```

---

## 模型选择策略

SerpentAI 支持多模型配置和自动选择。

### 配置默认模型

```python
# 设置默认模型（用于 /api/chat 端点）
registry = get_global_registry()
registry.set_default_model("gpt-4o")  # 或 claude-3-sonnet, llama-3-8b
```

### 根据任务选择模型

```python
# 在代码中使用特定模型
response = await registry.generate(
    messages=[...],
    model="gpt-4o",  # 指定模型
    temperature=0.7
)
```

### 成本优化策略

```python
# 简单任务使用便宜模型
if is_simple_task(messages):
    model = "gpt-4o-mini"  # $0.00015/1K tokens
else:
    model = "gpt-4o"        # $0.005/1K tokens
```

---

## 成本控制

### 1. 设置预算

```bash
# .env
MAX_COST_PER_DAY=10.0     # 每天最大成本（$）
MAX_COST_PER_REQUEST=0.50  # 每个请求最大成本（$）
```

### 2. 使用便宜模型

```python
# 优先使用 mini 模型
registry.set_default_model("gpt-4o-mini")  # 比 gpt-4o 便宜 30x
```

### 3. 限制 Token 数

```python
response = await adapter.generate(
    messages=messages,
    max_tokens=1024  # 限制输出 Token 数
)
```

### 4. 启用缓存

```bash
# .env
CACHE_STRATEGY=two-tier  # memory + redis
CACHE_TTL=3600           # 缓存 1 小时
```

---

## 故障排除

### OpenAI 适配器初始化失败

**错误信息**：`OpenAI适配器初始化失败: AuthenticationError`

**解决方案**：
1. 检查 API Key 是否正确
2. 检查 API Key 是否有余额
3. 检查网络连通性：`ping api.openai.com`

```bash
# 测试 API Key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Anthropic 适配器初始化失败

**错误信息**：`Anthropic适配器初始化失败: APIConnectionError`

**解决方案**：
1. 检查 API Key 是否正确
2. 检查网络连通性：`ping api.anthropic.com`

```bash
# 测试 API Key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### Llama.cpp 适配器初始化失败

**错误信息**：`llama-cpp-python未安装，请运行: pip install llama-cpp-python`

**解决方案**：
```bash
# 安装 llama-cpp-python
pip install llama-cpp-python

# 或带 GPU 加速
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python
```

**错误信息**：`模型文件不存在: ./models/llama-3-8b.gguf`

**解决方案**：
1. 下载 GGUF 模型文件
2. 放置到 `./models/` 目录
3. 在配置中指定正确路径

```python
config = {
    "model_path": "C:/Users/YourName/models/llama-3-8b.gguf"
}
```

### 模型响应慢

**原因1**：网络延迟
**解决方案**：使用本地模型（Llama.cpp）或选择更近的 API 端点

**原因2**：模型太大
**解决方案**：使用更小的模型（`gpt-4o-mini` 而非 `gpt-4o`）

**原因3**：未启用流式输出
**解决方案**：
```python
response = await adapter.generate(
    messages=messages,
    stream=True  # 启用流式输出
)
```

---

## 常见问题

### Q: 如何同时使用多个模型？

A: SerpentAI 支持注册多个模型，并可通过 `registry.set_default_model()` 切换默认模型。

```python
# 注册多个模型
registry.register_model("gpt-4o", OpenAIAdapter, {...})
registry.register_model("claude-3-sonnet", AnthropicAdapter, {...})
registry.register_model("llama-3-8b", LlamaAdapter, {...})

# 在请求中指定模型
POST /api/chat
{
  "message": "Hello",
  "model": "claude-3-sonnet"
}
```

### Q: 如何监控 API 成本？

A: 查看 `/api/usage` 端点或检查日志。

```bash
# 查看成本统计
curl http://localhost:8000/api/usage

# 或在代码中
from backend.models.registry import get_global_registry
stats = registry.get_model_stats()
print(f"总成本: ${stats['total_cost']}")
```

### Q: 本地模型相比 API 模型有什么优势？

A: 
- **成本**: 无 API 费用
- **隐私**: 数据不离开本地
- **延迟**: 无网络延迟
- **可控**: 可自定义模型和参数

**劣势**:
- **硬件要求**: 需要足够的 RAM 和 GPU
- **质量**: 本地模型质量通常低于 GPT-4o/Claude 3

---

## 安全最佳实践

1. **不要提交 API Key 到 Git**
   ```bash
   # .gitignore 已包含 .env
   echo ".env" >> .gitignore
   ```

2. **使用环境变量**
   ```bash
   # 不要硬编码在代码中
   # ❌ 错误
   api_key = "sk-abc123..."
   
   # ✅ 正确
   api_key = os.getenv("OPENAI_API_KEY")
   ```

3. **限制 API Key 权限**
   - OpenAI: 设置 Usage Limits
   - Anthropic: 使用 Restricted Key

4. **定期轮换 API Key**
   - 每 3-6 个月更换一次
   - 立即撤销泄露的 Key

---

## 相关文档

- [快速开始指南](./QUICKSTART.md)
- [API 参考文档](./API_REFERENCE.md)
- [生产环境部署指南](./DEPLOYMENT.md)
- [故障排除指南](./TROUBLESHOOTING.md)

---

**文档版本**: 1.0.0  
**更新日期**: 2026-05-23  
**维护者**: SerpentAI 团队
