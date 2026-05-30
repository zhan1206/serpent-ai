"""Prompt Distiller - 提示词蒸馏器

通过规则过滤和缓存实现 prompt 去冗余。
在生产环境中应集成 LLM 进行真正的知识蒸馏。
"""

import json
import hashlib
import re
from typing import Dict, Optional


class PromptDistiller:
    """
    提示词蒸馏器
    
    当前实现：规则过滤（移除冗余空白、注释行、硬截断）+ SHA256 缓存。
    缓存键使用 SHA256（跨进程稳定），而非 Python hash()。
    TODO: 集成 LLM 蒸馏实现真正的知识压缩。
    """
    
    def __init__(self):
        """初始化提示词蒸馏器"""
        self.cached_prompts: Dict[str, str] = {}
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
        prompt_id = self._generate_prompt_id(prompt, context)
        
        if prompt_id in self.cached_prompts:
            self.prompt_hits += 1
            return self.cached_prompts[prompt_id]
        
        self.prompt_misses += 1
        distilled = self._do_distillation(prompt, context)
        self.cached_prompts[prompt_id] = distilled
        
        return distilled
    
    def _generate_prompt_id(self, prompt: str, context: Optional[Dict]) -> str:
        """生成提示词ID（使用 SHA256，跨进程稳定）"""
        if context:
            raw = prompt + json.dumps(context, sort_keys=True)
        else:
            raw = prompt
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
    
    def _do_distillation(self, prompt: str, context: Optional[Dict]) -> str:
        """执行蒸馏"""
        # 移除多余空白
        distilled = re.sub(r'\s+', ' ', prompt).strip()
        
        # 按行过滤
        lines = distilled.split('\n')
        important_lines = []
        
        for line in lines:
            line = line.strip()
            # 保留关键指令行，跳过纯注释
            if any(kw in line.lower() for kw in ['goal', 'role', 'task', 'always', 'never', 'important']):
                important_lines.append(line)
            elif line and not line.startswith('#'):
                important_lines.append(line)
        
        distilled = '\n'.join(important_lines)
        
        # 截断过长的结果
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
