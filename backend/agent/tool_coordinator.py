"""
SerpentAI 工具协调器
管理工具调用、执行、错误处理和结果缓存
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class ToolCallResult:
    """工具调用结果"""
    success: bool
    tool_name: str
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    cached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "cached": self.cached,
            "timestamp": self.timestamp.isoformat()
        }


class ToolCoordinator:
    """
    工具协调器
    
    功能：
    1. 工具调用编排
    2. 执行超时控制
    3. 结果缓存
    4. 错误处理和重试
    5. 执行日志
    """
    
    def __init__(self):
        self.registry = None
        self.executor = None
        self.cache: Dict[str, ToolCallResult] = {}
        self.call_history: List[ToolCallResult] = []
        self.max_history = 100
        self.max_cache_size = 50
        
        # 配置
        self.default_timeout = 30  # 秒
        self.max_retries = 2
        
        logger.info("工具协调器初始化完成")
    
    def _get_registry(self):
        """获取工具注册表"""
        if self.registry is None:
            from backend.tools import get_global_registry
            self.registry = get_global_registry()
        return self.registry
    
    def _get_executor(self):
        """获取工具执行器"""
        if self.executor is None:
            from backend.tools.tool_executor import execute_tool
            self.executor = execute_tool
        return self.executor
    
    def _generate_cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 简单哈希（实际生产应该用更好的哈希）
        args_str = json.dumps(arguments, sort_keys=True)
        return f"{tool_name}:{hash(args_str)}"
    
    def _is_cacheable(self, tool_name: str) -> bool:
        """判断工具是否可缓存"""
        # 读取类工具通常可缓存
        cacheable_prefixes = ['fs_read', 'fs_exists', 'process_list', 'system_', 'memory_']
        return any(tool_name.startswith(prefix) for prefix in cacheable_prefixes)
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        session_id: str = None,
        timeout: int = None,
        use_cache: bool = True
    ) -> ToolCallResult:
        """
        执行工具调用
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            session_id: 会话 ID
            timeout: 超时时间（秒）
            use_cache: 是否使用缓存
        
        Returns:
            ToolCallResult: 调用结果
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        logger.info(f"工具调用开始 | 工具: {tool_name} | 会话: {session_id}")
        
        # 检查缓存
        cache_key = self._generate_cache_key(tool_name, arguments)
        if use_cache and cache_key in self.cache:
            cached_result = self.cache[cache_key]
            cached_result.cached = True
            self._add_to_history(cached_result)
            logger.info(f"工具调用命中缓存 | 工具: {tool_name}")
            return cached_result
        
        # 执行工具
        result = await self._execute_with_timeout(
            tool_name=tool_name,
            arguments=arguments,
            timeout=timeout
        )
        
        result.execution_time = time.time() - start_time
        
        # 缓存结果
        if result.success and use_cache and self._is_cacheable(tool_name):
            if len(self.cache) >= self.max_cache_size:
                # 移除最旧的缓存
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            self.cache[cache_key] = result
        
        # 记录历史
        self._add_to_history(result)
        
        logger.info(
            f"工具调用完成 | 工具: {tool_name} | "
            f"成功: {result.success} | 耗时: {result.execution_time:.2f}s"
        )
        
        return result
    
    async def _execute_with_timeout(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: int
    ) -> ToolCallResult:
        """带超时的工具执行"""
        try:
            # 使用 asyncio.wait_for 添加超时
            result = await asyncio.wait_for(
                self._execute_tool(tool_name, arguments),
                timeout=timeout
            )
            return result
        
        except asyncio.TimeoutError:
            logger.warning(f"工具执行超时 | 工具: {tool_name} | 超时: {timeout}s")
            return ToolCallResult(
                success=False,
                tool_name=tool_name,
                error=f"执行超时（{timeout}秒）",
                result={"timeout": True, "tool_name": tool_name}
            )
        
        except Exception as e:
            logger.error(f"工具执行异常 | 工具: {tool_name} | 错误: {e}")
            return ToolCallResult(
                success=False,
                tool_name=tool_name,
                error=str(e),
                result={}
            )
    
    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolCallResult:
        """执行单个工具"""
        registry = self._get_registry()
        executor = self._get_executor()
        
        # 检查工具是否存在
        tool_info = registry.get_tool(tool_name)
        if not tool_info:
            return ToolCallResult(
                success=False,
                tool_name=tool_name,
                error=f"工具不存在: {tool_name}"
            )
        
        # 尝试执行
        try:
            result = executor(tool_name, arguments)
            
            # 处理同步结果
            if asyncio.iscoroutine(result):
                result = await result
            
            return ToolCallResult(
                success=True,
                tool_name=tool_name,
                result=result if isinstance(result, dict) else {"result": result}
            )
        
        except Exception as e:
            return ToolCallResult(
                success=False,
                tool_name=tool_name,
                error=str(e)
            )
    
    async def execute_chain(
        self,
        chain: List[Dict[str, Any]],
        session_id: str = None
    ) -> List[ToolCallResult]:
        """
        执行工具链
        
        Args:
            chain: 工具链，每个元素包含 tool_name 和 arguments
            session_id: 会话 ID
        
        Returns:
            List[ToolCallResult]: 所有工具的调用结果
        """
        results = []
        
        for item in chain:
            tool_name = item.get("tool_name")
            arguments = item.get("arguments", {})
            
            # 执行当前工具
            result = await self.execute(tool_name, arguments, session_id)
            results.append(result)
            
            # 如果失败，停止链式执行
            if not result.success:
                logger.warning(f"工具链执行中断 | 工具: {tool_name} | 错误: {result.error}")
                break
            
            # 如果有下一个工具，将当前结果传递给下一个
            # （根据工具定义决定是否传递）
        
        return results
    
    def _add_to_history(self, result: ToolCallResult):
        """添加结果到历史记录"""
        self.call_history.append(result)
        
        # 保持历史记录在限制内
        if len(self.call_history) > self.max_history:
            self.call_history = self.call_history[-self.max_history:]
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("工具缓存已清空")
    
    def clear_history(self):
        """清空历史记录"""
        self.call_history.clear()
        logger.info("工具调用历史已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.call_history)
        success_count = sum(1 for r in self.call_history if r.success)
        failed_count = total - success_count
        
        return {
            "total_calls": total,
            "successful_calls": success_count,
            "failed_calls": failed_count,
            "success_rate": success_count / total if total > 0 else 0,
            "cache_size": len(self.cache),
            "history_size": len(self.call_history),
            "avg_execution_time": sum(r.execution_time for r in self.call_history) / total if total > 0 else 0
        }
    
    def get_history(
        self,
        tool_name: str = None,
        limit: int = 10
    ) -> List[ToolCallResult]:
        """获取调用历史"""
        history = self.call_history
        
        if tool_name:
            history = [r for r in history if r.tool_name == tool_name]
        
        return history[-limit:]
