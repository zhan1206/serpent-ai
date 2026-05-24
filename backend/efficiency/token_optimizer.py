"""Token Optimizer - Token优化器"""

import time
from typing import Dict


class TokenOptimizer:
    """
    全局Token优化器
    监控和优化Token消耗
    """
    
    def __init__(self):
        """初始化Token优化器"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0
        self.start_time = time.time()
        
        # 优化统计
        self.optimization_stats = {
            "prompt_distillation_savings": 0,
            "context_compression_savings": 0,
            "tool_precompilation_savings": 0,
            "tool_distillation_savings": 0,
            "output_compression_savings": 0
        }
    
    def record_request(self, input_tokens: int, output_tokens: int, cost: float):
        """记录API请求"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.request_count += 1
    
    def record_savings(self, optimization_type: str, tokens_saved: int):
        """记录优化节省的Token"""
        if optimization_type in self.optimization_stats:
            self.optimization_stats[optimization_type] += tokens_saved
    
    def get_stats(self) -> Dict:
        """获取优化统计"""
        uptime = time.time() - self.start_time
        return {
            "total_requests": self.request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "uptime_seconds": uptime,
            "avg_tokens_per_request": (self.total_input_tokens + self.total_output_tokens) / max(1, self.request_count),
            "optimization_stats": self.optimization_stats,
            "total_savings": sum(self.optimization_stats.values())
        }
    
    def reset(self):
        """重置统计"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0
        self.optimization_stats = {k: 0 for k in self.optimization_stats}
