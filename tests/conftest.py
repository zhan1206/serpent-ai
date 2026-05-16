"""
SerpentAI 测试配置
Pytest fixtures和配置
"""
import pytest
import asyncio
from typing import Generator
from pathlib import Path

# 测试配置
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_DB_DIR = Path(__file__).parent / "data" / "db"
TEST_CACHE_DIR = Path(__file__).parent / "data" / "cache"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_data_dir(tmp_path) -> Path:
    """临时测试数据目录"""
    return tmp_path / "data"


@pytest.fixture
def test_db_dir(tmp_path) -> Path:
    """临时测试数据库目录"""
    db_dir = tmp_path / "db"
    db_dir.mkdir(exist_ok=True)
    return db_dir


@pytest.fixture
def test_cache_dir(tmp_path) -> Path:
    """临时测试缓存目录"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


@pytest.fixture
def mock_settings(monkeypatch):
    """模拟设置用于测试"""
    from core.config import Settings
    
    class TestSettings(Settings):
        DEBUG = True
        APP_NAME = "SerpentAI-Test"
        DATABASE_URL = "sqlite+aiosqlite:///:memory:"
        REDIS_URL = None
        
    return TestSettings()


@pytest.fixture
def sample_messages():
    """示例消息用于测试"""
    return [
        {"role": "system", "content": "你是一个有用的AI助手"},
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"},
        {"role": "user", "content": "请介绍一下SerpentAI"},
    ]


@pytest.fixture
def sample_tool_calls():
    """示例工具调用用于测试"""
    return [
        {
            "name": "web_search",
            "arguments": {"query": "Python async await", "max_results": 5}
        },
        {
            "name": "calculator",
            "arguments": {"expression": "2 + 2 * 3"}
        },
        {
            "name": "file_read",
            "arguments": {"path": "/tmp/test.txt"}
        }
    ]


@pytest.fixture
def sample_memory_items():
    """示例记忆项用于测试"""
    return [
        {
            "content": "用户喜欢用中文交流",
            "importance": 0.8,
            "memory_type": "preference"
        },
        {
            "content": "用户是一名Python开发者",
            "importance": 0.9,
            "memory_type": "fact"
        },
        {
            "content": "上次对话提到了SerpentAI项目",
            "importance": 0.5,
            "memory_type": "context"
        }
    ]


@pytest.fixture
async def test_client():
    """测试用HTTP客户端"""
    from httpx import AsyncClient, ASGITransport
    
    async with AsyncClient(transport=ASGITransport(app="backend.main:app"), base_url="http://test") as client:
        yield client