"""Incremental Context Manager - 增量上下文管理器

基于消息哈希的增量差异检测。
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional


class IncrementalContextManager:
    """
    增量上下文管理器
    
    当前实现：基于消息内容哈希比对，仅发送新增消息。
    使用 SHA256 哈希避免全字段 O(n²) 比对。
    """
    
    def __init__(self):
        """初始化增量上下文管理器"""
        self.context_states: Dict[str, Dict] = {}
        self.last_message_hashes: Dict[str, set] = {}
    
    def save_state(self, session_id: str, messages: List[Dict]) -> str:
        """
        保存上下文状态
        
        Args:
            session_id: 会话ID
            messages: 消息列表
            
        Returns:
            状态ID
        """
        # 计算每条消息的哈希
        msg_hashes = {
            hashlib.sha256(json.dumps(m, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            for m in messages
        }
        self.last_message_hashes[session_id] = msg_hashes
        
        state_id = hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        
        self.context_states[session_id] = {
            "state_id": state_id,
            "message_count": len(messages),
            "last_save": datetime.now().isoformat(),
        }
        
        return state_id
    
    def get_incremental_messages(self, session_id: str, new_messages: List[Dict]) -> List[Dict]:
        """
        获取增量消息（仅返回新增的消息）
        
        Args:
            session_id: 会话ID
            new_messages: 新消息
            
        Returns:
            只包含新消息的列表
        """
        if session_id not in self.last_message_hashes:
            return new_messages
        
        known_hashes = self.last_message_hashes[session_id]
        
        incremental = []
        for msg in new_messages:
            msg_hash = hashlib.sha256(json.dumps(msg, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            if msg_hash not in known_hashes:
                incremental.append(msg)
        
        return incremental if incremental else new_messages
    
    def get_state(self, session_id: str) -> Optional[Dict]:
        """获取状态"""
        return self.context_states.get(session_id)
