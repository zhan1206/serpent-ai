# SerpentAI - 巨蛇AI

> 自托管企业级AI智能体框架 | 越用越省 · 越用越快 · 越用越好

## 徽章

[![CI](https://github.com/zhan1206/serpent-ai/actions/workflows/tests.yml/badge/pytest.svg)](https://github.com/zhan1206/serpent-ai/actions/workflows/tests.yml) [![Coverage](https://img.shields.io/badge/coverage-39%25-red)](https://github.com/zhan1206/serpent-ai) [![License](https://img.shields.io/github/license/zhan1206/serpent-ai)](LICENSE) [![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/) [![Docker](https://img.shields.io/docker/pulls/serpentai/serpent-ai)](https://hub.docker.com/r/serpentai/serpent-ai) [![Stars](https://img.shields.io/github/stars/zhan1206/serpent-ai)](https://github.com/zhan1206/serpent-ai/stargazers) [![Forks](https://img.shields.io/github/forks/zhan1206/serpent-ai)](https://github.com/zhan1206/serpent-ai/network/members) [![Issues](https://img.shields.io/github/issues/zhan1206/serpent-ai)](https://github.com/zhan1206/serpent-ai/issues) [![Last Commit](https://img.shields.io/github/last-commit/zhan1206/serpent-ai)](https://github.com/zhan1206/serpent-ai/commits) [![Code Size](https://img.shields.io/github/languages/code-size/zhan1206/serpent-ai)](https://github.com/zhan1206/serpent-ai) [![Repo Size](https://img.shields.io/github/repo-size/zhan1206/serpent-ai)](https://github.com/zhan1206/serpent-ai) [![Language](https://img.shields.io/github/languages/top/zhan1206/serpent-ai)](https://github.com/zhan1206/serpent-ai)

## 项目状态

✅ **测试版** - 项目已在积极开发中，核心功能已完成，测试覆盖率39%

## 特性

- **四层记忆系统**: 瞬时 → 短期 → 长期 → 归档
- **多模型支持**: OpenAI/Anthropic/Llama
- **工具生态**: MCP协议支持，内置13个系统工具
- **系统操作**: 文件管理、Shell命令、进程控制 - AI可操作电脑
- **多通道网关**: 飞书/Discord/Telegram
- **效率引擎**: Token优化、提示词蒸馏
- **自托管**: 完全可控，数据不出本地

---

# 新手教程 (详细步骤)

## 准备工作

### 环境要求
- Python 3.10 或更高版本
- Windows/Mac/Linux
- 建议 4GB+ 内存

### 检查Python版本
```bash
python --version
# 应该显示 Python 3.10.x 或更高
```

---

## 第一步：克隆项目

```bash
# 方式1: 克隆GitHub仓库
git clone https://github.com/zhan1206/serpent-ai.git
cd serpent-ai

# 方式2: 下载ZIP文件
# 访问 https://github.com/zhan1206/serpent-ai/releases 下载
```

---

## 第二步：创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 激活成功后，命令行前面会显示 (venv)
```

---

## 第三步：安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 如果遇到网络问题，可以使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 第四步：配置API密钥

### 4.1 复制配置文件
```bash
# Windows
copy backend\core\config.example.yaml backend\core\config.yaml

# Mac/Linux
cp backend/core/config.example.yaml backend/core/config.yaml
```

### 4.2 编辑配置文件
用文本编辑器打开 `backend/core/config.yaml`，填入你的API密钥：

```yaml
# OpenAI配置 (推荐)
openai:
  api_key: "sk-your-api-key-here"
  model: "gpt-4"

# 或 Anthropic配置
anthropic:
  api_key: "sk-ant-your-api-key-here"
  model: "claude-3-opus-20240229"

# 或本地Llama模型
llama:
  model_path: "./models/llama-7b.bin"
  base_url: "http://localhost:8080"
```

### 4.3 获取API密钥

**OpenAI:**
1. 访问 https://platform.openai.com/api-keys
2. 创建新的API key
3. 复制并粘贴到配置文件中

**Anthropic:**
1. 访问 https://console.anthropic.com/settings/keys
2. 创建API key
3. 复制并粘贴到配置文件中

---

## 第五步：启动服务

```bash
cd backend

# 启动服务 (默认端口8000)
python -m uvicorn main:app --reload --port 8000
```

---

## 第六步：验证安装

### 方法1：浏览器访问
打开浏览器访问 http://localhost:8000/docs

你应该能看到API文档页面。

### 方法2：健康检查
```bash
curl http://localhost:8000/health
# 返回: {"status":"ok","version":"0.1.0"}
```

### 方法3：测试聊天
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}
```

---

## 第七步：运行测试（验证功能）

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_memory.py -v

# 运行效率引擎测试
pytest tests/test_efficiency.py -v

# 查看测试覆盖率
pytest tests/ --cov=backend --cov-report=html
```

---

# 常见问题与解决方案

## 安装问题

### Q1: pip install 失败

**症状:**
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解决方案:**
```bash
# 1. 升级pip
pip install --upgrade pip

# 2. 清理缓存
pip cache purge

# 3. 使用镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 逐个安装有问题的包
pip install package_name
```

---

### Q2: Python版本不对

**症状:**
```
SyntaxError: invalid syntax
```
或者安装失败

**解决方案:**
```bash
# 检查版本
python --version

# 如果版本不对，安装正确版本

# Windows: 从 https://www.python.org/downloads/ 下载
# Mac: brew install python310
# Linux: sudo apt-get install python3.10
```

---

### Q3: Windows下编码问题

**症状:**
```
UnicodeDecodeError: 'gbk' codec can't decode
```

**解决方案:**
```bash
# 方案1: 设置环境变量
set PYTHONIOENCODING=utf-8

# 方案2: 在代码开头添加
# -*- coding: utf-8 -*-

# 方案3: 使用PowerShell
$env:PYTHONIOENCODING="utf-8"
```

---

### Q4: 路径问题

**症状:**
```
FileNotFoundError: [Errno 2] No such file or directory
```

**解决方案:**
```bash
# 方案1: 使用绝对路径
C:\Users\你的用户名\serpent-ai\backend

# 方案2: 检查当前目录
cd
pwd

# 方案3: 使用正斜杠
# Python中可以使用 / 代替 \
```

---

## 配置问题

### Q5: API密钥错误

**症状:**
```
Error: Invalid API key
```
或
```
Error: Authentication failed
```

**解决方案:**
```bash
# 1. 检查config.yaml中的密钥格式
# 确认没有多余的空格、引号、换行符

# 2. 确认密钥正确
# - OpenAI: sk-xxx 格式
# - Anthropic: sk-ant-xxx 格式

# 3. 检查密钥是否过期或被禁用
# 访问对应平台检查密钥状态
```

---

### Q6: 配置文件找不到

**症状:**
```
FileNotFoundError: config.yaml not found
```

**解决方案:**
```bash
# 1. 确认配置文件存在
ls backend/core/config.yaml

# 2. 如果不存在，复制示例
cp backend/core/config.example.yaml backend/core/config.yaml

# 3. 检查文件扩展名
# 应该是 .yaml 不是 .yml
```

---

### Q7: 模型配置错误

**症状:**
```
ValueError: Unknown model xxx
```

**解决方案:**
```yaml
# config.yaml 中使用支持的模型名
openai:
  model: "gpt-4"        # 支持: gpt-4, gpt-4-turbo, gpt-3.5-turbo
  # 或
  model: "gpt-3.5-turbo"

anthropic:
  model: "claude-3-opus-20240229"  # 支持的模型
  # 或
  model: "claude-3-sonnet-20240229"
```

---

## 运行问题

### Q8: 端口被占用

**症状:**
```
OSError: [Errno 98] Address already in use
```
或
```
error:98: Address already in use
```

**解决方案:**
```bash
# 方案1: 使用其他端口
python -m uvicorn main:app --port 8001

# 方案2: 找到占用的进程并杀掉
# Windows:
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F

# Mac/Linux:
lsof -i :8000
kill -9 <进程ID>
```

---

### Q9: 内存不足

**症状:**
```
MemoryError
```
或系统变卡

**解决方案:**
```bash
# 方案1: 关闭其他程序

# 方案2: 增加虚拟内存
# Windows: 系统属性 -> 高级 -> 性能设置 -> 虚拟内存

# 方案3: 使用更小的模型
# config.yaml 中使用 gpt-3.5-turbo 而不是 gpt-4
```

---

### Q10: 模块导入错误

**症状:**
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案:**
```bash
# 方案1: 安装缺失的模块
pip install xxx

# 方案2: 确认在正确的目录
cd serpent-ai
cd backend

# 方案3: 检查Python路径
import sys
print(sys.path)
```

---

## 功能问题

### Q11: 对话没有回复

**症状:**
发送消息后没有响应，页面一直在加载

**解决方案:**
```bash
# 1. 检查API密钥是否正确配置
cat backend/core/config.yaml

# 2. 检查网络连接
curl https://api.openai.com/v1/models

# 3. 检查日志输出
# 服务启动时查看日志中的错误信息

# 4. 尝试使用更简单的模型
# 将 gpt-4 改为 gpt-3.5-turbo
```

---

### Q12: 记忆系统不工作

**症状:**
对话没有记住之前的上下文

**解决方案:**
```bash
# 1. 确认session_id相同
# 每次对话使用相同的session_id

# 2. 检查session是否过期
# session有超时时间限制

# 3. 查看记忆系统日志
# 日志中会有记忆加载/保存的信息
```

---

### Q13: 工具调用失败

**症状:**
使用工具时返回错误

**解决方案:**
```bash
# 1. 检查工具配置
# config.yaml中的tools配置

# 2. 检查MCP服务器
# 确认工具服务器正在运行

# 3. 查看工具日志
# 错误信息会在返回中显示
```

---

### Q14: 向量数据库连接失败

**症状:**
```
ConnectionError: Could not connect to localhost:7687
```

**解决方案:**
```bash
# Neo4j是可选的，项目可以用内存模式运行

# 如果不需要向量搜索，可以忽略这个错误

# 如果需要:
# 1. 安装Neo4j Desktop
# 2. 启动数据库
# 3. 在config.yaml中配置连接信息
```

---

### Q15: 测试失败

**症状:**
pytest测试有失败

**解决方案:**
```bash
# 1. 查看失败原因
pytest tests/ -v --tb=long

# 2. 常见的失败原因:
# - 缺少依赖: pip install xxx
# - API配置问题: 检查config.yaml
# - 环境变量: 检查是否设置正确

# 3. 跳过有问题的测试
pytest tests/ -v --ignore=tests/test_specific.py

# 4. 只运行通过的测试
pytest tests/test_memory.py -v
pytest tests/test_efficiency.py -v
```

---

## API使用问题

### Q16: 如何发送聊天请求

**方法1：使用curl**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好",
    "session_id": "user123"
  }'
```

**方法2：使用Python**
```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "message": "你好",
    "session_id": "user123"
})
print(response.json())
```

**方法3：通过Web界面**
访问 http://localhost:8000 进行对话

---

### Q17: 如何查看记忆

```bash
curl "http://localhost:8000/memory?session_id=user123"
```

### Q18: 如何调用工具

```bash
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "calculator",
    "parameters": {"expression": "2+2"}
  }'
```

---

## 性能问题

### Q19: 响应慢

**解决方案:**
1. 使用更快的模型 (gpt-3.5-turbo > gpt-4)
2. 减少历史消息数量
3. 使用缓存
4. 检查网络延迟

### Q20: Token费用高

**解决方案:**
1. 开启Token优化
2. 使用提示词蒸馏
3. 减少对话历史长度
4. 使用更短的回复

---

# 调试技巧

## 1. 查看详细日志

```bash
# 启动时查看所有日志
python -m uvicorn main:app --log-level debug

# 查看实时日志
tail -f logs/app.log
```

## 2. Python调试

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用VS Code调试功能
```

## 3. API测试

```bash
# 使用Postman或Insomnia测试API
# 导入API schema: http://localhost:8000/openapi.json
```

---

# 目录结构说明

```
backend/
├── core/           # 核心基础设施
│   ├── config.py   # 配置管理
│   ├── database.py # 数据库
│   ├── cache.py   # 缓存
│   └── logging.py  # 日志
├── memory/        # 四层记忆系统
│   ├── instant_memory.py    # 瞬��记�� (<1ms)
│   ├── short_term_memory.py  # 短期记忆 (<100ms)
│   ├── long_term_memory.py  # 长期记忆 (知识图谱)
│   └── archive_memory.py    # 归档 (<5s)
├── models/        # 模型抽象层
│   ├── openai_adapter.py    # OpenAI
│   ├── anthropic_adapter.py # Anthropic
│   └── llama_adapter.py      # Llama
├── tools/         # 工具系统
│   ├── mcp_client.py        # MCP客户端
│   ├── tool_registry.py    # 工具注册
│   └── tool_executor.py   # 工具执行
├── efficiency/    # 效率引擎
│   ├── token_optimizer.py   # Token优化
│   ├── prompt_distiller.py # 提示词蒸馏
│   └── incremental_context.py # 增量上下文
├── gateways/     # 多通道网关
│   ├── feishu.py  # 飞书
│   ├── discord.py # Discord
│   └── telegram.py # Telegram
└── web/          # Web界面
    └── templates/ # HTML模板

tests/
├── test_memory.py        # 记忆系统测试
├── test_efficiency.py  # 效率引擎测试
└── test_tools.py       # 工具系统测试
```

---

## API端点完整列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/chat` | POST | 发送消息 |
| `/memory` | GET | 获取记忆 |
| `/memory` | POST | 保存记忆 |
| `/tools/list` | GET | 工具列表 |
| `/tools/call` | POST | 调用工具 |
| `/models` | GET | 模型列表 |
| `/config` | GET | 获取配置 |

---

## 开发相关

运行测试:
```bash
pytest tests/ -v
```

代码格式化:
```bash
black backend/
isort backend/
```

类型检查:
```bash
mypy backend/
```

---

## 技术支持

- GitHub Issues: https://github.com/zhan1206/serpent-ai/issues
- 讨论区: https://github.com/zhan1206/serpent-ai/discussions

---

## 许可证

MIT License