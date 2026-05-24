"""Semantic Compressor - 语义压缩器"""

from typing import Dict, List


class SemanticCompressor:
    """
    语义压缩器
    对话历史和记忆的智能语义压缩
    """
    
    def __init__(self):
        """初始化语义压缩器"""
        self.compression_cache: Dict[str, str] = {}
    
    def compress(self, text: str, max_length: int = 500) -> str:
        """
        语义压缩文本
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            压缩后的文本
        """
        if len(text) <= max_length:
            return text
        
        # 简单截断（保留关键信息）
        # 在实际实现中，可以使用LLM进行摘要
        sentences = text.split('. ')
        
        compressed = ""
        for sent in sentences:
            if len(compressed) + len(sent) <= max_length:
                compressed += sent + ". "
            else:
                break
        
        return compressed.strip() if compressed else text[:max_length]
    
    def compress_messages(self, messages: List[Dict], max_messages: int = 20) -> List[Dict]:
        """
        压缩消息列表
        
        Args:
            messages: 消息列表
            max_messages: 最大消息数
            
        Returns:
            压缩后的消息列表
        """
        if len(messages) <= max_messages:
            return messages
        
        # 保留最新的消息
        return messages[-max_messages:]
