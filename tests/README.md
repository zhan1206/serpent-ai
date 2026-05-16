# SerpentAI 后端单元测试

本目录包含SerpentAI后端核心模块的单元测试。

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/test_core/
pytest tests/test_memory/
pytest tests/test_tools/

# 运行带覆盖率
pytest --cov=backend --cov-report=html
```

## 测试结构

```
tests/
├── __init__.py
├── conftest.py           # pytest配置和fixtures
├── test_core/          # 核心模块测试
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_cache.py
│   └── test_encryption.py
├── test_memory/         # 记忆系统测试
│   ├── __init__.py
│   ├── test_instant_memory.py
│   ├── test_short_term_memory.py
│   ├── test_long_term_memory.py
│   └── test_archive_memory.py
├── test_models/         # 模型抽象层测试
│   ├── __init__.py
│   └── test_adapters.py
├── test_tools/          # 工具集成测试
│   ├── __init__.py
│   ├── test_registry.py
│   └── test_executor.py
├── test_efficiency/    # 效率引擎测试
│   └── __init__.py
├── test_gateways/      # 网关测试
│   └── __init__.py
└── test_api/          # API端点测试
    ├── __init__.py
    └── test_chat.py
```

## 测试要求

- 所有新功能必须包含单元测试
- 测试覆盖率目标：核心模块 > 80%
- 使用pytest和pytest-asyncio
- 使用faker生成测试数据
- 包含边缘情况和错误处理测试