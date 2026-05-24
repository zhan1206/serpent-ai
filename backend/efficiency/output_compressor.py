"""Output Compressor - 输出压缩器"""

import json
import re
from typing import Dict


class OutputCompressor:
    """
    输出压缩器
    模型输出的智能压缩和格式化
    预期效果：输出Token消耗降低40%
    """
    
    def __init__(self):
        """初始化输出压缩器"""
        self.compression_stats = {
            "total_compressions": 0,
            "total_savings": 0
        }
    
    def compress(self, output: str) -> str:
        """
        压缩模型输出
        
        Args:
            output: 原始输出
            
        Returns:
            压缩后的输出
        """
        self.compression_stats["total_compressions"] += 1
        
        # 移除多余空白
        compressed = re.sub(r'\s+', ' ', output).strip()
        
        # 计算节省
        savings = len(output) - len(compressed)
        self.compression_stats["total_savings"] += savings
        
        return compressed
    
    def format_output(self, output: str, format_type: str = "plain") -> str:
        """
        格式化输出
        
        Args:
            output: 输出文本
            format_type: 格式类型 (plain/markdown/json)
            
        Returns:
            格式化后的输出
        """
        if format_type == "json":
            # 尝试解析为JSON
            try:
                data = json.loads(output)
                return json.dumps(data, ensure_ascii=False, indent=2)
            except:
                return output
        
        elif format_type == "markdown":
            # 简化Markdown（移除多余的格式标记）
            # 移除多个连续的空行
            output = re.sub(r'\n{3,}', '\n\n', output)
            return output
        
        return output
    
    def get_stats(self) -> Dict:
        """获取压缩统计"""
        return self.compression_stats.copy()
