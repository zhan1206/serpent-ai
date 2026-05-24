"""
SerpentAI 记忆系统 - 瞬时记忆
存储最近10条消息，响应时间 <1ms
"""
import logging
from typing import List, Dict, Any, Optional
from collections import deque
import threading
from datetime import datetime

from backend.models.base_model import Message

logger = logging.getLogger(__name__)

class InstantMemory:
    """
    瞬时记忆管理器
    使用双端队列(deque)存储最近N条消息，实现O(1)的插入和查询
    """
    
    def __init__(self, max_messages: int = 10):
        """
        初始化瞬时记忆
        
        Args:
            max_messages: 最大消息数（默认10条）
        """
        self.max_messages = max_messages
        self._messages: Dict[str, deque] = {}  # session_id -> deque of messages
        self._lock = threading.Lock()  # 线程锁，保证线程安全
        
        logger.info(f"瞬时记忆初始化完成，最大消息数: {max_messages}")
    
    def add_message(self, session_id: str, message: Message) -> None:
        """
        添加消息到瞬时记忆
        
        Args:
            session_id: 会话ID
            message: 消息对象
        """
        with self._lock:
            if session_id not in self._messages:
                self._messages[session_id] = deque(maxlen=self.max_messages)
            
            # 添加时间戳
            msg_dict = {
                "role": message.role,
                "content": message.content,
                "name": message.name,
                "timestamp": datetime.now().isoformat()
            }
            
            self._messages[session_id].append(msg_dict)
            
            logger.debug(f"瞬时记忆添加消息 | session: {session_id} | role: {message.role}")
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取瞬时记忆中的消息
        
        Args:
            session_id: 会话ID
            limit: 返回消息数量限制（None表示返回全部）
            
        Returns:
            List[Dict]: 消息列表（按时间正序）
        """
        with self._lock:
            if session_id not in self._messages:
                return []
            
            messages = list(self._messages[session_id])
            
            if limit is not None and limit > 0:
                messages = messages[-limit:]
            
            return messages
    
    def get_formatted_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取格式化的消息列表（用于LLM API调用）
        
        Args:
            session_id: 会话ID
            limit: 返回消息数量限制
            
        Returns:
            List[Dict]: 格式化为LLM API格式的消息列表
        """
        messages = self.get_messages(session_id, limit)
        
        formatted = []
        for msg in messages:
            formatted_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            if msg.get("name"):
                formatted_msg["name"] = msg["name"]
            formatted.append(formatted_msg)
        
        return formatted
    
    def clear_session(self, session_id: str) -> None:
        """
        清空指定会话的瞬时记忆
        
        Args:
            session_id: 会话ID
        """
        with self._lock:
            if session_id in self._messages:
                self._messages[session_id].clear()
                logger.info(f"瞬时记忆已清空 | session: {session_id}")
    
    def clear_all(self) -> None:
        """清空所有会话的瞬时记忆"""
        with self._lock:
            self._messages.clear()
            logger.info("瞬时记忆已全部清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        with self._lock:
            total_sessions = len(self._messages)
            total_messages = sum(len(msgs) for msgs in self._messages.values())
            
            return {
                "type": "instant",
                "max_messages": self.max_messages,
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
            }
    
    def get_last_message(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取最后一条消息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict]: 最后一条消息，如果不存在则返回None
        """
        with self._lock:
            if session_id not in self._messages or len(self._messages[session_id]) == 0:
                return None
            
            return self._messages[session_id][-1]
    
    def search_messages(self, session_id: str, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索消息（简单关键词匹配）
        
        Args:
            session_id: 会话ID
            keyword: 搜索关键词
            
        Returns:
            List[Dict]: 匹配的消息列表
        """
        messages = self.get_messages(session_id)
        
        results = []
        for msg in messages:
            if keyword.lower() in msg["content"].lower():
                results.append(msg)
        
        return results

# 全局瞬时记忆实例（单例模式）
_instant_memory_instance: Optional[InstantMemory] = None
_instant_memory_lock = threading.Lock()

def get_instant_memory() -> InstantMemory:
    """
    获取瞬时记忆单例
    
    Returns:
        InstantMemory: 瞬时记忆实例
    """
    global _instant_memory_instance
    
    if _instant_memory_instance is None:
        with _instant_memory_lock:
            if _instant_memory_instance is None:
                from backend.core.config import settings
                _instant_memory_instance = InstantMemory(
                    max_messages=settings.MAX_INSTANT_MEMORIES
                )
    
    return _instant_memory_instance

def reset_instant_memory():
    """重置瞬时记忆单例（用于测试）"""
    global _instant_memory_instance
    _instant_memory_instance = None
