"""Incremental Context Manager - 增量上下文管理器"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional


class IncrementalContextManager:
    """
    增量上下文管理器
    只发送增量消息，支持上下文状态保存和恢复
    预期效果：上下文Token消耗降低75%
    """
    
    def __init__(self):
        """初始化增量上下文管理器"""
        self.context_states: Dict[str, Dict] = {}  # session_id -> state
        self.last_messages: Dict[str, List[Dict]] = {}  # session_id -> last messages
    
    def save_state(self, session_id: str, messages: List[Dict]) -> str:
        """
        保存上下文状态
        
        Args:
            session_id: 会话ID
            messages: 消息列表
            
        Returns:
            状态ID
        """
        # 保存最后的消息
        self.last_messages[session_id] = messages[-10:] if len(messages) > 10 else messages
        
        # 生成状态ID
        state_id = hashlib.sha256(json.dumps(messages).encode()).hexdigest()[:16]
        
        # 保存状态
        self.context_states[session_id] = {
            "state_id": state_id,
            "message_count": len(messages),
            "last_save": datetime.now().isoformat(),
            "message_hashes": [hashlib.sha256(json.dumps(m).encode()).hexdigest()[:8] for m in messages]
        }
        
        return state_id
    
    def get_incremental_messages(self, session_id: str, new_messages: List[Dict]) -> List[Dict]:
        """
        获取增量消息
        
        Args:
            session_id: 会话ID
            new_messages: 新消息
            
        Returns:
            只包含新消息的列表（用于增量发送）
        """
        if session_id not in self.last_messages:
            # 没有历史，返回所有消息
            return new_messages
        
        last_msgs = self.last_messages[session_id]
        
        # 找到最后一个历史消息的索引
        if not last_msgs or not new_messages:
            return new_messages
        
        # 只返回新消息（从最后一条历史消息之后）
        incremental = []
        for msg in new_messages:
            if msg not in last_msgs:
                incremental.append(msg)
        
        return incremental if incremental else new_messages
    
    def get_state(self, session_id: str) -> Optional[Dict]:
        """获取状态"""
        return self.context_states.get(session_id)
