"""Semantic Compressor - 语义压缩器

基于句子重要性的启发式压缩。
在生产环境中应集成 embedding 模型或 LLM 摘要以实现真正的语义压缩。
"""

from typing import Dict, List
import hashlib


class SemanticCompressor:
    """
    语义压缩器
    
    当前实现：基于句子长度和位置的启发式截断（保留首尾关键部分）。
    TODO: 集成 sentence-transformers 实现真正的语义压缩。
    """
    
    def __init__(self):
        """初始化语义压缩器"""
        self.compression_cache: Dict[str, str] = {}
    
    def compress(self, text: str, max_length: int = 500) -> str:
        """
        压缩文本，保留首尾关键内容
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            压缩后的文本
        """
        if len(text) <= max_length:
            return text
        
        sentences = text.split('. ')
        
        if len(sentences) <= 2:
            return text[:max_length] + "..." if len(text) > max_length else text
        
        # 保留前1/3和后1/3的句子（首尾通常包含主题和结论）
        keep_start = max(1, len(sentences) // 3)
        keep_end = max(1, len(sentences) // 3)
        
        start_sentences = sentences[:keep_start]
        end_sentences = sentences[-keep_end:]
        
        result = '. '.join(start_sentences) + '. ... ' + '. '.join(end_sentences)
        
        # 如果仍超长，继续截断
        if len(result) > max_length:
            result = result[:max_length] + "..."
        
        return result
    
    def compress_messages(self, messages: List[Dict], max_messages: int = 20) -> List[Dict]:
        """
        压缩消息列表，保留最新消息
        
        Args:
            messages: 消息列表
            max_messages: 最大消息数
            
        Returns:
            压缩后的消息列表
        """
        if len(messages) <= max_messages:
            return messages
        
        return messages[-max_messages:]
