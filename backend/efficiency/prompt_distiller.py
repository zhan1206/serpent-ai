"""Prompt Distiller - 提示词蒸馏器"""

import json
import re
from typing import Dict, Optional


class PromptDistiller:
    """
    提示词蒸馏器
    动态蒸馏系统提示词，永久缓存核心部分
    预期效果：系统提示词Token消耗降低90%
    """
    
    def __init__(self):
        """初始化提示词蒸馏器"""
        self.cached_prompts: Dict[str, str] = {}  # prompt_id -> distilled_prompt
        self.prompt_hits = 0
        self.prompt_misses = 0
    
    def distill(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        蒸馏提示词
        
        Args:
            prompt: 原始提示词
            context: 上下文信息
            
        Returns:
            蒸馏后的提示词
        """
        # 生成提示词ID
        prompt_id = self._generate_prompt_id(prompt, context)
        
        # 检查缓存
        if prompt_id in self.cached_prompts:
            self.prompt_hits += 1
            return self.cached_prompts[prompt_id]
        
        self.prompt_misses += 1
        
        # 蒸馏提示词
        distilled = self._do_distillation(prompt, context)
        
        # 缓存
        self.cached_prompts[prompt_id] = distilled
        
        return distilled
    
    def _generate_prompt_id(self, prompt: str, context: Optional[Dict]) -> str:
        """生成提示词ID"""
        if context:
            return str(hash(prompt + json.dumps(context, sort_keys=True)))
        return str(hash(prompt))
    
    def _do_distillation(self, prompt: str, context: Optional[Dict]) -> str:
        """执行蒸馏"""
        # 移除多余空白
        distilled = re.sub(r'\s+', ' ', prompt).strip()
        
        # 移除注释和文档
        lines = distilled.split('\n')
        important_lines = []
        
        for line in lines:
            line = line.strip()
            # 保留关键指令
            if any(kw in line.lower() for kw in ['goal', 'role', 'task', 'always', 'never', 'important']):
                important_lines.append(line)
            elif line and not line.startswith('#'):
                important_lines.append(line)
        
        distilled = '\n'.join(important_lines)
        
        # 截断（如果太长）
        if len(distilled) > 2000:
            distilled = distilled[:1997] + "..."
        
        return distilled
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        total = self.prompt_hits + self.prompt_misses
        hit_rate = self.prompt_hits / max(1, total) * 100
        return {
            "cache_size": len(self.cached_prompts),
            "hits": self.prompt_hits,
            "misses": self.prompt_misses,
            "hit_rate_percent": hit_rate
        }
