"""
记忆系统测试
"""
import pytest
from datetime import datetime
from backend.models.base_model import Message


class TestInstantMemory:
    """瞬时记忆测试"""

    def test_add_message(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=10)
        memory.add_message("session_1", Message(role="user", content="你好"))
        messages = memory.get_messages("session_1")
        assert len(messages) == 1
        assert messages[0]["content"] == "你好"

    def test_max_messages(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=3)
        for i in range(5):
            memory.add_message("s1", Message(role="user", content=f"消息{i}"))
        messages = memory.get_messages("s1")
        assert len(messages) == 3

    def test_clear_session(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=10)
        memory.add_message("s1", Message(role="user", content="测试"))
        memory.clear_session("s1")
        assert len(memory.get_messages("s1")) == 0

    def test_clear_all(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=10)
        memory.add_message("s1", Message(role="user", content="a"))
        memory.add_message("s2", Message(role="user", content="b"))
        memory.clear_all()
        assert len(memory.get_messages("s1")) == 0
        assert len(memory.get_messages("s2")) == 0

    def test_get_formatted_messages(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=10)
        memory.add_message("s1", Message(role="user", content="hello"))
        formatted = memory.get_formatted_messages("s1")
        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"

    def test_get_stats(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=10)
        stats = memory.get_stats()
        assert stats["type"] == "instant"

    def test_search_messages(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=10)
        memory.add_message("s1", Message(role="user", content="Python编程"))
        memory.add_message("s1", Message(role="user", content="Java开发"))
        results = memory.search_messages("s1", "Python")
        assert len(results) == 1

    def test_get_last_message(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=10)
        memory.add_message("s1", Message(role="user", content="first"))
        memory.add_message("s1", Message(role="assistant", content="last"))
        last = memory.get_last_message("s1")
        assert last["content"] == "last"

    def test_multiple_sessions(self):
        from backend.memory.instant_memory import InstantMemory
        memory = InstantMemory(max_messages=10)
        memory.add_message("s1", Message(role="user", content="a"))
        memory.add_message("s2", Message(role="user", content="b"))
        assert len(memory.get_messages("s1")) == 1
        assert len(memory.get_messages("s2")) == 1


class TestShortTermMemory:
    """短期记忆测试"""

    def test_create(self):
        from backend.memory.short_term_memory import ShortTermMemory
        memory = ShortTermMemory()
        assert memory is not None

    def test_add_message(self):
        from backend.memory.short_term_memory import ShortTermMemory
        memory = ShortTermMemory()
        memory.add_message("session_1", Message(role="user", content="Python编程"))

    def test_search_messages(self):
        from backend.memory.short_term_memory import ShortTermMemory
        memory = ShortTermMemory()
        results = memory.search_messages("Python", limit=5)
        assert isinstance(results, list)

    def test_get_stats(self):
        from backend.memory.short_term_memory import ShortTermMemory
        memory = ShortTermMemory()
        stats = memory.get_stats()
        assert "type" in stats


class TestLongTermMemory:
    """长期记忆测试"""

    def test_create(self):
        from backend.memory.long_term_memory import LongTermMemory
        memory = LongTermMemory()
        assert memory is not None

    def test_add_memory(self):
        from backend.memory.long_term_memory import LongTermMemory
        memory = LongTermMemory()
        memory.add_memory(session_id="test", content="测试内容", importance=0.8)

    def test_search_memories(self):
        from backend.memory.long_term_memory import LongTermMemory
        memory = LongTermMemory()
        results = memory.search_memories("Python", limit=5)
        assert isinstance(results, list)

    def test_get_stats(self):
        from backend.memory.long_term_memory import LongTermMemory
        memory = LongTermMemory()
        stats = memory.get_stats()
        assert "type" in stats


class TestArchiveMemory:
    """归档记忆测试"""

    def test_create(self):
        from backend.memory.archive_memory import ArchiveMemory
        memory = ArchiveMemory()
        assert memory is not None

    def test_add_summary(self):
        from backend.memory.archive_memory import ArchiveMemory
        memory = ArchiveMemory()
        now = datetime.now().isoformat()
        memory.add_summary(
            session_id="test",
            summary="测试摘要",
            start_date=now,
            end_date=now,
            message_count=5
        )

    def test_search_summaries(self):
        from backend.memory.archive_memory import ArchiveMemory
        memory = ArchiveMemory()
        results = memory.search_summaries("测试", limit=5)
        assert isinstance(results, list)

    def test_get_stats(self):
        from backend.memory.archive_memory import ArchiveMemory
        memory = ArchiveMemory()
        stats = memory.get_stats()
        assert "type" in stats
