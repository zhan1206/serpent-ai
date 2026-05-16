"""
SerpentAI 记忆系统 - 记忆管理器
统一管理四层记忆（瞬时、短期、长期、归档）
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading

from models.base_model import Message
from .instant_memory import get_instant_memory, reset_instant_memory
from .short_term_memory import get_short_term_memory, reset_short_term_memory

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    记忆管理器（四层统一接口）
    提供统一的添加、检索、清理接口
    """
    
    def __init__(self):
        """初始化记忆管理器"""
        self.instant_memory = get_instant_memory()
        self.short_term_memory = get_short_term_memory()
        self.long_term_memory = None  # 延迟初始化
        self.archive_memory = None    # 延迟初始化
        self._lock = threading.Lock()
        
        logger.info("记忆管理器初始化完成")
    
    def _ensure_long_term_memory(self):
        """确保长期记忆已初始化（延迟加载）"""
        if self.long_term_memory is not None:
            return
        
        with self._lock:
            if self.long_term_memory is not None:
                return
            
            try:
                from .long_term_memory import get_long_term_memory
                self.long_term_memory = get_long_term_memory()
                logger.info("长期记忆已初始化")
            except Exception as e:
                logger.warning(f"长期记忆初始化失败（将禁用）: {e}")
                self.long_term_memory = None
    
    def _ensure_archive_memory(self):
        """确保归档记忆已初始化（延迟加载）"""
        if self.archive_memory is not None:
            return
        
        with self._lock:
            if self.archive_memory is not None:
                return
            
            try:
                from .archive_memory import get_archive_memory
                self.archive_memory = get_archive_memory()
                logger.info("归档记忆已初始化")
            except Exception as e:
                logger.warning(f"归档记忆初始化失败（将禁用）: {e}")
                self.archive_memory = None
    
    def add_message(self, session_id: str, message: Message) -> None:
        """
        添加消息到所有记忆层
        
        Args:
            session_id: 会话ID
            message: 消息对象
        """
        # 1. 添加到瞬时记忆（始终成功）
        try:
            self.instant_memory.add_message(session_id, message)
        except Exception as e:
            logger.error(f"添加到瞬时记忆失败: {e}")
        
        # 2. 添加到短期记忆（可能失败，降级处理）
        try:
            self.short_term_memory.add_message(session_id, message)
        except Exception as e:
            logger.error(f"添加到短期记忆失败: {e}")
        
        # 3. 添加到长期记忆（如果重要）
        try:
            self._ensure_long_term_memory()
            if self.long_term_memory and self._is_important(message):
                self.long_term_memory.add_memory(
                    session_id=session_id,
                    content=message.content,
                    memory_type="fact",
                    importance=0.8
                )
        except Exception as e:
            logger.error(f"添加到长期记忆失败: {e}")
        
        # 4. 归档记忆不参与实时添加（定期归档）
        
        logger.debug(f"消息已添加到记忆系统 | session: {session_id} | role: {message.role}")
    
    def recall(
        self, 
        session_id: str, 
        query: Optional[str] = None,
        limit: int = 10,
        include_instant: bool = True,
        include_short_term: bool = True,
        include_long_term: bool = True,
        include_archive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        从所有记忆层召回消息
        
        Args:
            session_id: 会话ID
            query: 搜索查询（None表示返回最近消息）
            limit: 返回消息总数
            include_instant: 是否包含瞬时记忆
            include_short_term: 是否包含短期记忆
            include_long_term: 是否包含长期记忆
            include_archive: 是否包含归档记忆
            
        Returns:
            List[Dict]: 按相关性/时间排序的消息列表
        """
        results = []
        
        # 1. 瞬时记忆（最近N条，直接返回）
        if include_instant:
            try:
                instant_msgs = self.instant_memory.get_formatted_messages(
                    session_id, 
                    limit=10 if query is None else 5
                )
                for msg in instant_msgs:
                    results.append({
                        **msg,
                        "source": "instant",
                        "relevance": 1.0  # 最高相关性
                    })
            except Exception as e:
                logger.error(f"从瞬时记忆召回失败: {e}")
        
        # 2. 短期记忆（语义检索）
        if include_short_term and query is not None:
            try:
                short_term_msgs = self.short_term_memory.search_messages(
                    query=query,
                    session_id=session_id,
                    limit=limit // 2
                )
                for msg in short_term_msgs:
                    results.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        "source": "short_term",
                        "relevance": msg.get("similarity", 0.5),
                        "timestamp": msg.get("timestamp")
                    })
            except Exception as e:
                logger.error(f"从短期记忆召回失败: {e}")
        elif include_short_term and query is None:
            # 无查询时，返回最近消息
            try:
                short_term_msgs = self.short_term_memory.get_messages_by_session(
                    session_id=session_id,
                    limit=limit // 2
                )
                for msg in short_term_msgs:
                    results.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        "source": "short_term",
                        "relevance": 0.5,
                        "timestamp": msg.get("timestamp")
                    })
            except Exception as e:
                logger.error(f"从短期记忆获取失败: {e}")
        
        # 3. 长期记忆（知识图谱检索）
        if include_long_term:
            try:
                self._ensure_long_term_memory()
                if self.long_term_memory:
                    if query is not None:
                        long_term_memories = self.long_term_memory.search_memories(
                            query=query,
                            session_id=session_id,
                            limit=limit // 3
                        )
                        for mem in long_term_memories:
                            results.append({
                                "role": "system",
                                "content": mem["content"],
                                "source": "long_term",
                                "relevance": mem.get("score", 0.3),
                                "memory_type": mem.get("memory_type")
                            })
            except Exception as e:
                logger.error(f"从长期记忆召回失败: {e}")
        
        # 4. 归档记忆（压缩摘要）
        if include_archive:
            try:
                self._ensure_archive_memory()
                if self.archive_memory:
                    if query is not None:
                        archive_summaries = self.archive_memory.search_summaries(
                            query=query,
                            session_id=session_id,
                            limit=limit // 5
                        )
                        for summary in archive_summaries:
                            results.append({
                                "role": "system",
                                "content": summary["summary"],
                                "source": "archive",
                                "relevance": summary.get("score", 0.2),
                                "date": summary.get("date")
                            })
            except Exception as e:
                logger.error(f"从归档记忆召回失败: {e}")
        
        # 去重和排序
        results = self._deduplicate_and_sort(results, query)
        
        # 限制返回数量
        return results[:limit]
    
    def _deduplicate_and_sort(
        self, 
        results: List[Dict[str, Any]], 
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        去重和排序结果
        
        Args:
            results: 召回结果列表
            query: 原始查询（用于排序）
            
        Returns:
            List[Dict]: 去重并排序后的结果
        """
        # 去重（基于content的前100字符）
        seen = set()
        unique_results = []
        
        for result in results:
            content_key = result["content"][:100]  # 取前100字符作为去重键
            if content_key not in seen:
                seen.add(content_key)
                unique_results.append(result)
        
        # 排序（按相关性降序）
        if query is not None:
            unique_results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        else:
            # 无查询时按时间排序（新的在前）
            unique_results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return unique_results
    
    def _is_important(self, message: Message) -> bool:
        """
        判断消息是否重要（是否需要存入长期记忆）
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否重要
        """
        # 简单启发式规则：
        # 1. 系统消息始终重要
        if message.role == "system":
            return True
        
        # 2. 包含关键词的消息
        important_keywords = ["记住", "记得", "重要", "必须", "不要忘记", "remember", "important"]
        for keyword in important_keywords:
            if keyword in message.content.lower():
                return True
        
        # 3. 长消息（可能包含重要信息）
        if len(message.content) > 200:
            return True
        
        # 4. 默认不重要（避免长期记忆膨胀）
        return False
    
    def get_context_for_llm(
        self, 
        session_id: str, 
        query: Optional[str] = None,
        max_tokens: int = 2000
    ) -> List[Dict[str, str]]:
        """
        获取用于LLM的上下文（格式化消息列表）
        
        Args:
            session_id: 会话ID
            query: 搜索查询（可选）
            max_tokens: 最大Token数（估算）
            
        Returns:
            List[Dict]: 格式化为LLM API的消息列表
        """
        # 召回消息
        messages = self.recall(
            session_id=session_id,
            query=query,
            limit=20,
            include_instant=True,
            include_short_term=True,
            include_long_term=True,
            include_archive=False
        )
        
        # 转换为LLM格式并估算Token
        formatted = []
        estimated_tokens = 0
        
        for msg in messages:
            # 估算Token数（简单方法：1个Token ≈ 1.3个字符）
            msg_tokens = len(msg["content"]) // 1
            
            # 如果超过预算，停止添加
            if estimated_tokens + msg_tokens > max_tokens:
                break
            
            formatted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
            estimated_tokens += msg_tokens
        
        # 确保系统消息在前
        system_msgs = [m for m in formatted if m["role"] == "system"]
        other_msgs = [m for m in formatted if m["role"] != "system"]
        
        return system_msgs + other_msgs
    
    def clear_session(self, session_id: str) -> None:
        """
        清空指定会话的所有记忆
        
        Args:
            session_id: 会话ID
        """
        try:
            self.instant_memory.clear_session(session_id)
        except Exception as e:
            logger.error(f"清空瞬时记忆失败: {e}")
        
        try:
            self.short_term_memory.clear_session(session_id)
        except Exception as e:
            logger.error(f"清空短期记忆失败: {e}")
        
        try:
            self._ensure_long_term_memory()
            if self.long_term_memory:
                self.long_term_memory.clear_session(session_id)
        except Exception as e:
            logger.error(f"清空长期记忆失败: {e}")
        
        try:
            self._ensure_archive_memory()
            if self.archive_memory:
                self.archive_memory.clear_session(session_id)
        except Exception as e:
            logger.error(f"清空归档记忆失败: {e}")
        
        logger.info(f"已清空会话的所有记忆 | session: {session_id}")
    
    def clear_all(self) -> None:
        """清空所有会话的记忆"""
        try:
            self.instant_memory.clear_all()
        except Exception as e:
            logger.error(f"清空瞬时记忆失败: {e}")
        
        try:
            self.short_term_memory.clear_all()
        except Exception as e:
            logger.error(f"清空短期记忆失败: {e}")
        
        try:
            self._ensure_long_term_memory()
            if self.long_term_memory:
                self.long_term_memory.clear_all()
        except Exception as e:
            logger.error(f"清空长期记忆失败: {e}")
        
        try:
            self._ensure_archive_memory()
            if self.archive_memory:
                self.archive_memory.clear_all()
        except Exception as e:
            logger.error(f"清空归档记忆失败: {e}")
        
        logger.info("已清空所有记忆")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取所有记忆层的统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            "instant": {},
            "short_term": {},
            "long_term": {},
            "archive": {}
        }
        
        try:
            stats["instant"] = self.instant_memory.get_stats()
        except Exception as e:
            stats["instant"] = {"error": str(e)}
        
        try:
            stats["short_term"] = self.short_term_memory.get_stats()
        except Exception as e:
            stats["short_term"] = {"error": str(e)}
        
        try:
            self._ensure_long_term_memory()
            if self.long_term_memory:
                stats["long_term"] = self.long_term_memory.get_stats()
            else:
                stats["long_term"] = {"status": "disabled"}
        except Exception as e:
            stats["long_term"] = {"error": str(e)}
        
        try:
            self._ensure_archive_memory()
            if self.archive_memory:
                stats["archive"] = self.archive_memory.get_stats()
            else:
                stats["archive"] = {"status": "disabled"}
        except Exception as e:
            stats["archive"] = {"error": str(e)}
        
        return stats

# 全局记忆管理器实例（单例模式）
_memory_manager_instance: Optional[MemoryManager] = None
_memory_manager_lock = threading.Lock()

def get_memory_manager() -> MemoryManager:
    """
    获取记忆管理器单例
    
    Returns:
        MemoryManager: 记忆管理器实例
    """
    global _memory_manager_instance
    
    if _memory_manager_instance is None:
        with _memory_manager_lock:
            if _memory_manager_instance is None:
                _memory_manager_instance = MemoryManager()
    
    return _memory_manager_instance

def reset_memory_manager():
    """重置记忆管理器单例（用于测试）"""
    global _memory_manager_instance
    _memory_manager_instance = None
