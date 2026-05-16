"""
记忆系统测试
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from models.base_model import Message
    """瞬时记忆测试"""
    
    @pytest.mark.asyncio
    async def test_add_message(self):
        """测试添加消息"""
        from memory.instant_memory import InstantMemory
        
        memory = InstantMemory(max_messages=10)
        
        # 添加消息
        await memory.add_message(
            role="user",
            content="你好",
            metadata={"timestamp": datetime.now().isoformat()}
        )
        
        # 获取最近消息
        messages = await memory.get_recent_messages(1)
        assert len(messages) == 1
        assert messages[0]["content"] == "你好"
    
    @pytest.mark.asyncio
    async def test_max_messages(self):
        """测试消息数量限制"""
        from memory.instant_memory import InstantMemory
        
        memory = InstantMemory(max_messages=3)
        
        # 添加超过限制的消息
        for i in range(5):
            await memory.add_message(role="user", content=f"消息{i}")
        
        # 验证只保留最近的3条
        messages = await memory.get_recent_messages(10)
        assert len(messages) == 3
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空记忆"""
        from memory.instant_memory import InstantMemory
        
        memory = InstantMemory(max_messages=10)
        
        # 添加消息
        await memory.add_message(role="user", content="测试")
        
        # 清空
        await memory.clear()
        
        # 验证已清空
        messages = await memory.get_recent_messages(10)
        assert len(messages) == 0


class TestShortTermMemory:
    """短期记忆测试"""
    
    @pytest.mark.asyncio
    async def test_add_memory(self):
        """测试添加短期记忆"""
        from memory.short_term_memory import ShortTermMemory
        
        memory = ShortTermMemory()
        
        # 添加记忆
        await memory.add_memory(
            content="用户喜欢蓝色",
            importance=0.8,
            session_id="test_session"
        )
        
        # 搜索记忆
        results = await memory.search("蓝色", limit=5)
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search(self):
        """测试搜索"""
        from memory.short_term_memory import ShortTermMemory
        
        memory = ShortTermMemory()
        
        # 添加多条记忆
        await memory.add_memory(content="Python编程", importance=0.9)
        await memory.add_memory(content="JavaScript前端", importance=0.7)
        await memory.add_memory(content="Go并发", importance=0.8)
        
        # 搜索
        results = await memory.search("编程", limit=5)
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_get_recent(self):
        """测试获取近期记忆"""
        from memory.short_term_memory import ShortTermMemory
        
        memory = ShortTermMemory()
        
        # 添加记忆
        for i in range(5):
            await memory.add_memory(content=f"记忆{i}", importance=0.5)
        
        # 获取近期记忆
        recent = await memory.get_recent(days=7, limit=10)
        assert len(recent) > 0


class TestLongTermMemory:
    """长期记忆测试"""
    
    @pytest.mark.asyncio
    async def test_add_fact(self):
        """测试添加事实"""
        from memory.long_term_memory import LongTermMemory
        
        memory = LongTermMemory()
        
        # 添加事实
        fact_id = await memory.add_fact(
            content="SerpentAI是一个AI智能体框架",
            category="project",
            confidence=0.95
        )
        
        assert fact_id is not None
    
    @pytest.mark.asyncio
    async def test_add_relationship(self):
        """测试添加关系"""
        from memory.long_term_memory import LongTermMemory
        
        memory = LongTermMemory()
        
        # 添加关系
        rel_id = await memory.add_relationship(
            from_node="用户",
            relation="喜欢",
            to_node="Python",
            weight=0.8
        )
        
        assert rel_id is not None
    
    @pytest.mark.asyncio
    async def test_query_graph(self):
        """测试图查询"""
        from memory.long_term_memory import LongTermMemory
        
        memory = LongTermMemory()
        
        # 添加测试数据
        await memory.add_fact(content="Python是一种编程语言", category="language")
        await memory.add_fact(content="SerpentAI使用Python开发", category="project")
        
        # 查询
        results = await memory.query_graph("Python")
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_get_important_memories(self):
        """测试获取重要记忆"""
        from memory.long_term_memory import LongTermMemory
        
        memory = LongTermMemory()
        
        # 添加不同重要性的记忆
        await memory.add_fact(content="重要1", category="test", confidence=0.9)
        await memory.add_fact(content="重要2", category="test", confidence=0.8)
        await memory.add_fact(content="重要3", category="test", confidence=0.7)
        
        # 获取重要记忆
        important = await memory.get_important_memories(min_importance=0.75)
        assert len(important) >= 2


class TestArchiveMemory:
    """归档记忆测试"""
    
    @pytest.mark.asyncio
    async def test_archive(self):
        """测试归档"""
        from memory.archive_memory import ArchiveMemory
        
        memory = ArchiveMemory()
        
        # 归档记忆
        await memory.archive(
            content="2024年的旧对话",
            summary="关于Python的讨论",
            original_date=datetime.now() - timedelta(days=365)
        )
        
        # 获取归档
        archives = await memory.get_archives(limit=10)
        assert len(archives) >= 0
    
    @pytest.mark.asyncio
    async def test_search_archive(self):
        """测试搜索归档"""
        from memory.archive_memory import ArchiveMemory
        
        memory = ArchiveMemory()
        
        # 归档
        await memory.archive(
            content="测试内容",
            summary="测试摘要"
        )
        
        # 搜索
        results = await memory.search_archive("测试", limit=5)
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_restore(self):
        """测试恢复归档"""
        from memory.archive_memory import ArchiveMemory
        
        memory = ArchiveMemory()
        
        # 归档
        archive_id = await memory.archive(
            content="需要恢复的记忆",
            summary="测试"
        )
        
        # 恢复
        restored = await memory.restore(archive_id)
        assert restored is not None