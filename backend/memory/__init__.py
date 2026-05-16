"""
SerpentAI 记忆系统
四层记忆架构：
1. Instant Memory - 瞬时记忆（最近10条消息，<1ms）
2. Short-Term Memory - 短期记忆（最近7天，向量检索，<100ms）
3. Long-Term Memory - 长期记忆（知识图谱，<500ms）
4. Archive Memory - 归档记忆（压缩摘要，<5s）
"""

from .instant_memory import InstantMemory, get_instant_memory
from .short_term_memory import ShortTermMemory, get_short_term_memory
from .long_term_memory import LongTermMemory, get_long_term_memory
from .archive_memory import ArchiveMemory, get_archive_memory
from .memory_manager import MemoryManager, get_memory_manager

__all__ = [
    # 瞬时记忆
    "InstantMemory",
    "get_instant_memory",
    # 短期记忆
    "ShortTermMemory",
    "get_short_term_memory",
    # 长期记忆
    "LongTermMemory",
    "get_long_term_memory",
    # 归档记忆
    "ArchiveMemory",
    "get_archive_memory",
    # 记忆管理器
    "MemoryManager",
    "get_memory_manager",
]
