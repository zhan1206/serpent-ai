# SerpentAI Python SDK

官方 Python SDK，用于与 SerpentAI 服务交互。

## 安装

```bash
pip install serpent-ai-sdk
```

或从源码安装：

```bash
git clone https://github.com/zhan1206/serpent-ai.git
cd serpent-ai
pip install -e ./sdk
```

## 快速开始

```python
from serpent_sdk import SerpentAI

# 初始化客户端
client = SerpentAI("http://localhost:8000")

# 聊天
response = client.chat("你好，请介绍一下自己")
print(response.text)

# 使用本地模型
response = client.chat("解释量子计算", model="llama-3-8b")
print(response.text)
```

## 完整示例

```python
from serpent_sdk import SerpentAI
from serpent_sdk.types import ChatMessage

# 初始化
client = SerpentAI(
    base_url="http://localhost:8000",
    api_key="your-api-key",  # 可选
    timeout=120,
)

# 聊天
response = client.chat(
    message="帮我写一个快速排序算法",
    model="gpt-4",
    temperature=0.7,
)
print(f"响应: {response.text}")
print(f"Token使用: {response.usage.total_tokens}")

# 列出模型
models = client.list_models()
for m in models:
    print(f"  - {m.id} ({m.provider})")

# 列出工具
tools = client.list_tools(category="filesystem")
for t in tools:
    print(f"  - {t.name}: {t.description}")

# 调用工具
result = client.call_tool("fs_list", {"path": "/tmp"})
print(f"目录内容: {result}")

# 记忆系统
client.add_memory("用户喜欢用中文交流", session_id="user123")
memories = client.recall_memory("用户偏好", session_id="user123")
print(f"召回记忆: {memories}")

# 智能体
agent = client.agents.create(name="代码助手", model="gpt-4")
result = client.agents.run(agent.id, "帮我写一个Web服务器")
print(f"智能体响应: {result.text}")

# 工作流
workflows = client.workflows.list()
if workflows:
    result = client.workflows.execute(workflows[0].id, {"input": "data.csv"})
    print(f"执行结果: {result.status}")

# 语音聊天
with open("audio.webm", "rb") as f:
    audio = f.read()
result = client.voice.voice_chat(audio, language="zh-CN")
print(f"识别: {result['text']}")
print(f"AI响应: {result['response']}")

# 健康检查
health = client.health()
print(f"状态: {health.status}")

client.close()
```

## 智能体

```python
# 创建智能体
agent = client.agents.create(
    name="我的助手",
    model="gpt-4",
    system_prompt="你是一个专业的Python程序员",
)

# 运行智能体
response = client.agents.run(agent.id, "写一个装饰器")
print(response.text)

# 触发自进化
client.agents.evolve(agent.id, evolution_type="optimize")

# 任务管理
task = client.agents.run_task(agent.id, "分析这份数据", priority=8, background=True)
print(f"任务ID: {task['task_id']}")
```

## 工作流

```python
# 列出模板
templates = client.workflows.list_templates()
for t in templates:
    print(f"  - {t['name']}: {t['description']}")

# 从模板创建
workflow = client.workflows.create_from_template("chatbot-basic")

# 执行工作流
result = client.workflows.execute(
    workflow.id,
    input_data={"user_message": "你好"}
)
print(f"状态: {result.status}, 耗时: {result.duration_ms}ms")

# 调度工作流
client.workflows.add_schedule(
    workflow.id,
    trigger_type="cron",
    expression="0 9 * * *",  # 每天9点
    input_data={"input": "daily_report.csv"},
)

# 异步执行
exec_id = client.workflows.execute_async(workflow.id, {"input": "data.csv"})
# ... later ...
result = client.workflows.get_execution(exec_id)
print(f"执行结果: {result.status}")
```

## 插件系统

```python
# 浏览插件市场
marketplace = client.plugins.get_marketplace()
for p in marketplace:
    print(f"  - {p.name} v{p.version} by {p.author}")

# 安装插件
plugin = client.plugins.install("https://example.com/my-plugin.zip")

# 执行插件动作
result = client.plugins.execute(plugin.id, "run", {"param": "value"})

# 热重载
plugin = client.plugins.reload(plugin.id)
```

## 技能商店

```python
# 浏览技能市场
skills = client.skills.get_marketplace(sort_by="popular")
for s in skills:
    print(f"  - {s.name} ({s.category}) ⭐{s.rating}")

# 搜索技能
skills = client.skills.search("web scraping", category="data")
for s in skills:
    print(f"  - {s.name}: {s.description}")

# 安装技能
skill = client.skills.install(skill_id="web-researcher")

# 评价
client.skills.rate(skill.id, rating=5)
```

## 语音交互

```python
# 文字转语音
audio = client.voice.text_to_speech(
    "你好，欢迎使用SerpentAI！",
    voice="zh-CN-XiaoxiaoNeural",
    speed=1.0,
)
with open("output.mp3", "wb") as f:
    f.write(audio)

# 语音转文字
with open("input.webm", "rb") as f:
    text = client.voice.speech_to_text(f.read(), language="zh-CN")
print(f"识别结果: {text}")

# 列出可用声音
voices = client.voice.list_voices()
for v in voices:
    print(f"  - {v['name']} ({v['language']})")
```

## 异步客户端

```python
import asyncio
from serpent_sdk import AsyncSerpentAI

async def main():
    async with AsyncSerpentAI() as client:
        # 并发聊天
        responses = await asyncio.gather(
            client.chat("你好", model="gpt-4"),
            client.chat("讲个笑话", model="gpt-3.5-turbo"),
        )
        for r in responses:
            print(r.text)

asyncio.run(main())
```

## 异常处理

```python
from serpent_sdk import SerpentAI
from serpent_sdk.exceptions import (
    SerpentAIError,
    APIError,
    RateLimitError,
    AuthenticationError,
    NotFoundError,
)

try:
    client = SerpentAI("http://localhost:8000")
    response = client.chat("你好")
except AuthenticationError:
    print("请检查API密钥")
except RateLimitError as e:
    print(f"频率超限，请在{e.retry_after}秒后重试")
except NotFoundError:
    print("资源不存在")
except APIError as e:
    print(f"API错误: {e.status_code} - {e.message}")
except SerpentAIError as e:
    print(f"SDK错误: {e}")
```

## 类型提示

SDK 提供完整的类型提示：

```python
from serpent_sdk.types import (
    ChatMessage,
    ChatResponse,
    ModelInfo,
    ToolInfo,
    AgentInfo,
    WorkflowInfo,
    MemoryStats,
    VoiceSession,
    PluginInfo,
    SkillInfo,
)

def process_response(response: ChatResponse) -> str:
    return f"[{response.model}] {response.text}"
```

## 环境变量

```bash
# 设置默认API地址
export SERPENT_API_URL=http://localhost:8000

# 设置API密钥
export SERPENT_API_KEY=your-api-key
```

## 许可证

MIT License
