"""
SerpentAI 智能模型路由引擎
根据任务复杂度、成本、响应时间自动选择最优模型
支持故障转移和历史评分优化
"""
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """任务复杂度等级"""
    SIMPLE = "simple"       # 简单问答、翻译
    MEDIUM = "medium"       # 一般对话、摘要
    COMPLEX = "complex"     # 推理、代码生成、多步任务


@dataclass
class ModelScore:
    """模型评分记录"""
    model_name: str
    success_count: int = 0
    fail_count: int = 0
    total_latency_ms: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.5

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.success_count if self.success_count > 0 else 9999.0

    @property
    def avg_cost(self) -> float:
        return self.total_cost / self.success_count if self.success_count > 0 else 0.0


@dataclass
class RoutingRule:
    """路由规则"""
    complexity: TaskComplexity
    preferred_models: List[str]        # 按优先级排列
    fallback_models: List[str] = field(default_factory=list)
    max_cost_per_1k: float = 0.05     # 每1K token最大成本(USD)
    max_latency_ms: int = 10000       # 最大延迟(ms)


class ModelRouter:
    """
    智能模型路由引擎
    
    根据任务复杂度、成本预算、响应时间自动选择最优模型。
    支持规则路由和基于历史评分的路由，以及故障转移。
    """

    # 默认路由规则
    DEFAULT_RULES: Dict[TaskComplexity, RoutingRule] = {
        TaskComplexity.SIMPLE: RoutingRule(
            complexity=TaskComplexity.SIMPLE,
            preferred_models=["gpt-4o-mini", "gpt-3.5-turbo", "deepseek-chat", "qwen-turbo", "mock"],
            fallback_models=["mock"],
            max_cost_per_1k=0.001,
            max_latency_ms=3000,
        ),
        TaskComplexity.MEDIUM: RoutingRule(
            complexity=TaskComplexity.MEDIUM,
            preferred_models=["gpt-4o", "claude-3", "qwen-plus", "doubao-pro", "mock"],
            fallback_models=["gpt-4o-mini", "mock"],
            max_cost_per_1k=0.01,
            max_latency_ms=8000,
        ),
        TaskComplexity.COMPLEX: RoutingRule(
            complexity=TaskComplexity.COMPLEX,
            preferred_models=["gpt-4o", "claude-3-opus", "gemini-pro", "mock"],
            fallback_models=["gpt-4o", "mock"],
            max_cost_per_1k=0.05,
            max_latency_ms=30000,
        ),
    }

    def __init__(self, registry=None):
        """
        初始化模型路由引擎
        
        Args:
            registry: ModelRegistry实例
        """
        self._registry = registry
        self._scores: Dict[str, ModelScore] = {}
        self._rules: Dict[TaskComplexity, RoutingRule] = dict(self.DEFAULT_RULES)
        self._fail_cooldown: Dict[str, float] = {}  # model_name -> cooldown_until
        self._cooldown_seconds: int = 60

    def set_registry(self, registry):
        """设置模型注册表"""
        self._registry = registry

    def add_rule(self, rule: RoutingRule):
        """添加/更新路由规则"""
        self._rules[rule.complexity] = rule

    def classify_complexity(self, messages: List) -> TaskComplexity:
        """
        根据消息内容自动判断任务复杂度
        
        Args:
            messages: 对话消息列表
            
        Returns:
            TaskComplexity: 任务复杂度
        """
        if not messages:
            return TaskComplexity.SIMPLE

        last_msg = messages[-1] if hasattr(messages[-1], 'content') else messages[-1]
        text = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
        text_lower = text.lower()

        # 复杂任务关键词
        complex_keywords = [
            "分析", "推理", "代码", "编程", "debug", "架构",
            "对比", "评估", "设计", "优化", "复杂", "多步",
            "explain", "analyze", "reason", "code", "debug", "architect",
        ]
        # 中等任务关键词
        medium_keywords = [
            "总结", "摘要", "写", "翻译", "生成", "改写",
            "summarize", "write", "translate", "generate", "rewrite",
        ]

        complex_count = sum(1 for kw in complex_keywords if kw in text_lower)
        medium_count = sum(1 for kw in medium_keywords if kw in text_lower)

        if complex_count >= 2 or len(text) > 2000:
            return TaskComplexity.COMPLEX
        elif complex_count >= 1 or medium_count >= 2 or len(text) > 500:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE

    def select_model(
        self,
        messages: List,
        complexity: Optional[TaskComplexity] = None,
        preferred_model: Optional[str] = None,
        max_cost: Optional[float] = None,
        max_latency_ms: Optional[int] = None,
    ) -> str:
        """
        选择最优模型
        
        Args:
            messages: 对话消息列表
            complexity: 指定复杂度（不指定则自动判断）
            preferred_model: 用户指定的偏好模型
            max_cost: 最大成本预算
            max_latency_ms: 最大延迟
            
        Returns:
            str: 选择的模型名称
        """
        if not self._registry:
            logger.warning("模型注册表未设置，返回mock")
            return "mock"

        available = set(self._registry.list_models())
        if not available:
            return "mock"

        # 用户明确指定
        if preferred_model and preferred_model in available:
            if not self._is_in_cooldown(preferred_model):
                return preferred_model

        # 自动判断复杂度
        if complexity is None:
            complexity = self.classify_complexity(messages)

        rule = self._rules.get(complexity, self.DEFAULT_RULES[TaskComplexity.SIMPLE])

        # 从偏好列表中选择
        candidates = rule.preferred_models + rule.fallback_models
        for model_name in candidates:
            if model_name not in available:
                continue
            if self._is_in_cooldown(model_name):
                continue
            if not self._meets_constraints(model_name, rule, max_cost, max_latency_ms):
                continue
            return model_name

        # 所有偏好模型不可用，从可用模型中按评分选
        scored = []
        for model_name in available:
            if self._is_in_cooldown(model_name):
                continue
            score = self._compute_routing_score(model_name, rule)
            scored.append((model_name, score))

        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]

        # 最后兜底
        return "mock" if "mock" in available else (available.pop() if available else "mock")

    def _is_in_cooldown(self, model_name: str) -> bool:
        """检查模型是否在冷却期"""
        if model_name in self._fail_cooldown:
            if time.time() < self._fail_cooldown[model_name]:
                return True
            del self._fail_cooldown[model_name]
        return False

    def _meets_constraints(
        self,
        model_name: str,
        rule: RoutingRule,
        max_cost: Optional[float] = None,
        max_latency_ms: Optional[int] = None,
    ) -> bool:
        """检查模型是否满足约束"""
        cost_limit = max_cost or rule.max_cost_per_1k
        latency_limit = max_latency_ms or rule.max_latency_ms

        score = self._scores.get(model_name)
        if score and score.success_count > 0:
            if score.avg_cost > cost_limit:
                return False
            if score.avg_latency_ms > latency_limit:
                return False
        return True

    def _compute_routing_score(self, model_name: str, rule: RoutingRule) -> float:
        """
        计算路由评分（0-1，越高越好）
        
        综合考虑：成功率(40%) + 延迟(30%) + 成本(30%)
        """
        score = self._scores.get(model_name)
        if not score or score.success_count == 0:
            return 0.5  # 未知模型给中等分

        # 成功率分 (0-1)
        success_score = score.success_rate

        # 延迟分 (越低越好)
        latency_score = max(0, 1 - score.avg_latency_ms / rule.max_latency_ms)

        # 成本分 (越低越好)
        cost_score = max(0, 1 - score.avg_cost / rule.max_cost_per_1k) if rule.max_cost_per_1k > 0 else 1.0

        return success_score * 0.4 + latency_score * 0.3 + cost_score * 0.3

    def record_success(self, model_name: str, latency_ms: int, input_tokens: int, output_tokens: int, cost: float):
        """记录成功的模型调用"""
        if model_name not in self._scores:
            self._scores[model_name] = ModelScore(model_name=model_name)
        s = self._scores[model_name]
        s.success_count += 1
        s.total_latency_ms += latency_ms
        s.total_input_tokens += input_tokens
        s.total_output_tokens += output_tokens
        s.total_cost += cost
        logger.debug(f"路由记录成功: {model_name}, 延迟={latency_ms}ms, 成本=${cost:.4f}")

    def record_failure(self, model_name: str):
        """记录模型调用失败"""
        if model_name not in self._scores:
            self._scores[model_name] = ModelScore(model_name=model_name)
        self._scores[model_name].fail_count += 1
        self._fail_cooldown[model_name] = time.time() + self._cooldown_seconds
        logger.warning(f"路由记录失败: {model_name}, 冷却{self._cooldown_seconds}秒")

    def get_scores(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型评分"""
        return {
            name: {
                "success_rate": score.success_rate,
                "avg_latency_ms": score.avg_latency_ms,
                "avg_cost": score.avg_cost,
                "total_calls": score.success_count + score.fail_count,
            }
            for name, score in self._scores.items()
        }

    def get_routing_info(self) -> Dict[str, Any]:
        """获取路由引擎状态"""
        return {
            "rules": {c.value: {"preferred": r.preferred_models, "fallback": r.fallback_models}
                      for c, r in self._rules.items()},
            "scores": self.get_scores(),
            "cooldown": {k: int(v - time.time()) for k, v in self._fail_cooldown.items() if time.time() < v},
        }


# 全局路由实例
_global_router: Optional[ModelRouter] = None


def get_global_router() -> ModelRouter:
    """获取全局模型路由实例"""
    global _global_router
    if _global_router is None:
        _global_router = ModelRouter()
    return _global_router
