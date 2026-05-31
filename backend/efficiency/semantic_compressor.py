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
    
    @staticmethod
    def head_tail_truncate(items: list, keep_ratio: float = 1/3) -> list:
        """
        保留首尾各 keep_ratio 比例的元素，中间用占位符替代。
        被 TokenOptimizer._smart_truncate 复用以消除代码重复。

        Args:
            items: 可分割的列表（句子、行等）
            keep_ratio: 首尾各保留比例（默认 1/3）
        Returns:
            截断后的列表（含中间占位符）
        """
        if len(items) <= 2:
            return items
        keep_start = max(1, int(len(items) * keep_ratio))
        keep_end = max(1, int(len(items) * keep_ratio))
        return items[:keep_start] + ['...'] + items[-keep_end:]

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
        truncated = self.head_tail_truncate(sentences)
        result = '. '.join(truncated)

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
