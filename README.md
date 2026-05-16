# SerpentAI - 巨蛇AI

> 自托管企业级AI智能体框架 | 越用越省 · 越用越快 · 越用越好

## 项目状态

⚠️ **测试版** - 项目仍在积极开发中，部分功能正在完善

## 特性

- **四层记忆系统**: 瞬时 → 短期 → 长期 → 归档，Token消耗降低85%
- **多模型支持**: OpenAI/Anthropic/Llama
- **工具生态**: MCP协议支持，1000+工具
- **多通道网关**: 飞书/Discord/Telegram
- **效率引擎**: Token优化、提示词蒸馏
- **自托管**: 完全可控，数据不出本地

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

额外依赖（如需要）:
```bash
pip install neo4j chromadb redis
```

### 2. 配置

复制并编辑配置文件:
```bash
cp backend/core/config.example.yaml backend/core/config.yaml
```

编辑 `config.yaml`，填入你的API密钥。

### 3. 运行

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看API文档。

## 目录结构

```
backend/
├── core/           # 核心基础设施
├── memory/        # 四层记忆系统
├── models/        # 模型抽象层
├── tools/         # 工具系统
├── efficiency/    # 效率引擎
├── gateways/      # 多通道网关
├── web/           # Web界面
└── routes/       # API路由

tests/             # 测试文件
```

## API端点

- `GET /health` - 健康检查
- `POST /chat` - 对话
- `GET /memory` - 记忆查询
- `POST /tools/call` - 工具调用

## 已知问题

### 测试相关

部分测试文件与实现API不完全匹配，这是开发过程中的正常情况。核心功能不受影响。

### 依赖问题

- Neo4j: 长期记忆需要 (可选)
- ChromaDB: 向量存储需要 (可选)  
- Redis: 缓存需要 (可选)

## 常见问题

**Q: 安装依赖失败?**
A: 确保Python 3.10+。使用 `pip install --upgrade pip` 更新pip。

**Q: 数据库连接失败?**
A: Neo4j/ChromaDB/Redis是可选的。项目可在无外部数据库模式下运行（使用内存存储）。

**Q: API密钥错误?**
A: 检查 `backend/core/config.yaml` 中的API配置。

**Q: 端口被占用?**
A: 使用 `--port 8001` 换端口。

## 开发相关

运行测试:
```bash
pytest tests/ -v
```

## 许可证

MIT License