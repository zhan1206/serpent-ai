"""
SerpentAI 推理引擎
实现智能体的思考和决策逻辑
"""

import asyncio
import logging
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.models.base_model import Message, create_adapter

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """行动类型"""
    TOOL = "tool"       # 调用工具
    RESPONSE = "response"  # 生成响应
    TASK = "task"       # 任务管理
    WAIT = "wait"       # 等待更多信息


@dataclass
class ReasoningResult:
    """推理结果"""
    thought: str                           # 思考过程
    action_type: str                        # 行动类型
    tool_name: Optional[str] = None         # 工具名称
    arguments: Optional[Dict[str, Any]] = None  # 工具参数
    response_content: Optional[str] = None  # 响应内容
    task_action: Optional[str] = None       # 任务动作 (create/complete)
    task_id: Optional[str] = None          # 任务 ID
    task_description: Optional[str] = None  # 任务描述
    task_priority: Optional[int] = None     # 任务优先级
    confidence: float = 0.0                 # 置信度
    reasoning_steps: List[str] = field(default_factory=list)  # 推理步骤


class ReasoningEngine:
    """
    推理引擎
    
    核心功能：
    1. 分析当前状态和上下文
    2. 生成推理步骤链
    3. 决定下一步行动
    4. 评估行动置信度
    """
    
    def __init__(self, config):
        self.config = config
        self.model_adapter = None
        self.max_steps = config.max_thinking_steps if hasattr(config, 'max_thinking_steps') else 5
        
        # 推理模板
        self.reasoning_template = """你是一个 AI 推理引擎，需要分析当前情况并决定最佳行动。

【当前状态】
{context}

【最近对话】
{recent_messages}

【可用工具】
{available_tools}

【你的任务】
根据当前状态，从以下行动中选择一个：

1. **TOOL**: 如果需要使用工具完成任务
   - 指定工具名称和参数
   
2. **RESPONSE**: 如果可以直接回答用户问题
   - 提供完整回答

3. **TASK**: 如果需要创建或完成任务
   - 指定任务动作和详情

请按以下格式输出你的推理：

**思考过程**:
[详细分析当前情况]

**行动选择**: [TOOL/RESPONSE/TASK]

**理由**: [为什么选择这个行动]

**详细计划**:
1. [第一步]
2. [第二步]
（如果需要）

**置信度**: [0-1 之间的小数]

**行动详情**:
- 工具名称: [如果选择 TOOL]
- 参数: [JSON 格式]
- 响应内容: [如果选择 RESPONSE]
- 任务动作: [如果选择 TASK]
"""
    
    def _init_model(self):
        """延迟初始化模型适配器"""
        if self.model_adapter is None:
            self.model_adapter = create_adapter(self.config.model)
    
    async def reason(
        self, 
        context_prompt: str,
        max_steps: int = None
    ) -> ReasoningResult:
        """
        执行推理
        
        Args:
            context_prompt: 上下文提示词
            max_steps: 最大推理步骤数
        
        Returns:
            ReasoningResult: 推理结果
        """
        self._init_model()
        max_steps = max_steps or self.max_steps
        
        reasoning_steps = []
        current_context = context_prompt
        
        logger.debug(f"推理引擎开始 | 最大步骤: {max_steps}")
        
        # 多次迭代思考（如果需要）
        for step in range(min(max_steps, 3)):
            step_result = await self._single_reasoning(current_context, step + 1)
            reasoning_steps.extend(step_result.reasoning_steps)
            
            # 如果有足够的置信度，可以提前结束
            if step_result.confidence >= 0.8:
                logger.debug(f"推理引擎提前结束 | 置信度: {step_result.confidence}")
                break
            
            # 更新上下文，加入之前的推理结果
            current_context = f"{context_prompt}\n\n【之前的推理】\n{step_result.thought}"
        
        # 最终决策
        final_result = await self._single_reasoning(
            f"{context_prompt}\n\n【推理步骤】\n" + "\n".join(reasoning_steps),
            max_steps
        )
        
        final_result.reasoning_steps = reasoning_steps
        return final_result
    
    async def _single_reasoning(
        self, 
        context: str,
        step: int
    ) -> ReasoningResult:
        """执行单次推理"""
        
        # 获取工具列表
        try:
            from backend.tools import get_global_registry
            registry = get_global_registry()
            tools = registry.list_tools()
            tools_info = self._format_tools(tools[:20])  # 限制数量
        except:
            tools_info = "无可用工具"
        
        # 获取最近消息
        recent_messages = self._get_recent_messages(context)
        
        # 构建提示词
        prompt = self.reasoning_template.format(
            context=context,
            recent_messages=recent_messages,
            available_tools=tools_info
        )
        
        # 调用模型（优先使用结构化输出）
        try:
            messages = [Message(role="system", content=prompt)]
            
            # 尝试结构化 JSON 输出（更可靠）
            result = await self._structured_reasoning(messages, step)
            if result:
                logger.debug(f"推理步骤 {step} 完成（结构化）| 类型: {result.action_type} | 置信度: {result.confidence}")
                return result
            
            # 回退到字符串解析
            response = self.model_adapter.generate(messages)
            response_text = response.content
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            return ReasoningResult(
                thought=f"推理失败: {e}",
                action_type="RESPONSE",
                response_content="抱歉，我在思考时遇到了问题。",
                confidence=0.0,
                reasoning_steps=[f"步骤 {step}: 推理失败"]
            )
        
        # 解析响应
        result = self._parse_reasoning_response(response_text, step)
        
        logger.debug(f"推理步骤 {step} 完成（回退解析）| 类型: {result.action_type} | 置信度: {result.confidence}")
        return result
    
    async def _structured_reasoning(self, messages: List[Message], step: int) -> Optional[ReasoningResult]:
        """
        使用结构化 JSON 输出进行推理（更可靠）
        
        通过在 prompt 中要求模型返回 JSON，减少字符串解析的错误。
        """
        structured_prompt = messages[0].content + """

【重要】请以 JSON 格式返回你的决策，不要包含其他内容：

{
    "action_type": "TOOL | RESPONSE | TASK",
    "tool_name": "工具名称（仅当 action_type=TOOL 时）",
    "arguments": {"参数名": "参数值"}（仅当 action_type=TOOL 时）,
    "response_content": "回答内容（仅当 action_type=RESPONSE 时）",
    "task_action": "create | complete | cancel（仅当 action_type=TASK 时）",
    "task_description": "任务描述（仅当 action_type=TASK 时）",
    "confidence": 0.85,
    "reasoning": "你的推理过程"
}
"""
        
        try:
            structured_messages = [Message(role="system", content=structured_prompt)]
            response = self.model_adapter.generate(structured_messages)
            
            # 提取 JSON
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            result = ReasoningResult(
                thought=data.get("reasoning", ""),
                action_type=data.get("action_type", "RESPONSE").lower(),
                tool_name=data.get("tool_name"),
                arguments=data.get("arguments", {}),
                response_content=data.get("response_content", ""),
                task_action=data.get("task_action"),
                task_description=data.get("task_description"),
                confidence=min(1.0, max(0.0, float(data.get("confidence", 0.5)))),
                reasoning_steps=[f"步骤 {step}: 结构化推理"]
            )
            return result
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(f"结构化推理解析失败，回退到字符串解析: {e}")
            return None
    
    def _format_tools(self, tools: List[Dict]) -> str:
        """格式化工具列表"""
        if not tools:
            return "无可用工具"
        
        lines = []
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            params = tool.get("parameters", {})
            lines.append(f"- {name}: {desc}")
            if params:
                lines.append(f"  参数: {list(params.keys())}")
        
        return "\n".join(lines)
    
    def _get_recent_messages(self, context: str, max_chars: int = 2000) -> str:
        """获取最近的对话历史（限制长度防止溢出）"""
        if "最近消息" in context:
            remaining = context.split("最近消息")[-1]
            # 截取到下一个【标记或达到最大长度
            if "【" in remaining:
                result = remaining.split("【")[0]
            else:
                result = remaining[:max_chars]
            return result[:max_chars]
        return "无历史消息"
    
    def _parse_reasoning_response(self, response: str, step: int) -> ReasoningResult:
        """解析推理响应（最终回退方案）
        
        当结构化 JSON 解析失败时，使用正则匹配多种格式标记。
        支持中英文混合，不依赖固定字符串。
        """
        result = ReasoningResult(
            thought="",
            action_type="RESPONSE",
            confidence=0.5,
            reasoning_steps=[f"步骤 {step}: {response[:200]}..."]
        )
        
        lines = response.split("\n")
        
        # 提取思考过程（支持中英文标记）
        thought_patterns = [
            re.compile(r'\*{0,2}(?:思考过程|思考)\*{0,2}\s*[:：]'),
            re.compile(r'\*{0,2}(?:thought|reasoning)\*{0,2}\s*[:：]', re.IGNORECASE),
            re.compile(r'(?:思考过程|思考|thought|reasoning)\s*[:：]', re.IGNORECASE),
        ]
        thought_start = -1
        for i, line in enumerate(lines):
            if any(p.search(line) for p in thought_patterns):
                thought_start = i
            elif thought_start >= 0 and (line.startswith("**") or line.startswith("#")):
                break
            elif thought_start >= 0 and line.strip():
                result.thought += line + "\n"
        
        # 提取行动类型（支持中英文和多种格式）
        action_patterns = [
            re.compile(r'\*{0,2}(?:行动选择|action)\*{0,2}\s*[:：]', re.IGNORECASE),
        ]
        for line in lines:
            if any(p.search(line) for p in action_patterns):
                # 匹配行动类型：支持 TOOL/RESPONSE/TASK 以及中文
                action_match = re.search(r'\b(TOOL|RESPONSE|TASK|tool|response|task)\b', line, re.IGNORECASE)
                if action_match:
                    result.action_type = action_match.group(1).lower()
                break
        
        # 提取置信度（允许星号标记）
        confidence_match = re.search(
            r'(?:\*{0,2}(?:置信度|confidence)\*{0,2})\s*[:：]\s*([0-9.]+)', 
            response, re.IGNORECASE
        )
        if not confidence_match:
            # 回退：在任何包含置信度关键词的行中找数字
            for line in lines:
                if re.search(r'置信度|confidence', line, re.IGNORECASE):
                    confidence_match = re.search(r'([0-9]+\.?[0-9]*)', line)
                    if confidence_match:
                        break
        if confidence_match:
            try:
                result.confidence = min(1.0, max(0.0, float(confidence_match.group(1))))
            except ValueError:
                pass
        
        # 提取工具信息
        if result.action_type == "tool":
            result.tool_name, result.arguments = self._extract_tool_info(lines)
        elif result.action_type == "response":
            result.response_content = self._extract_response_content(lines)
            if not result.response_content:
                result.response_content = result.thought or response[:500]
        elif result.action_type == "task":
            result.task_action, result.task_id, result.task_description = self._extract_task_info(lines)
        
        return result
    
    def _extract_tool_info(self, lines: List[str]) -> tuple:
        """提取工具调用信息"""
        tool_name = None
        arguments = {}
        
        in_tool_section = False
        for line in lines:
            if "工具名称" in line or "tool_name" in line.lower():
                in_tool_section = True
                parts = line.split(":")
                if len(parts) > 1:
                    tool_name = parts[-1].strip().strip('`').strip()
            elif in_tool_section and "参数" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    param_str = parts[-1].strip().strip('`').strip()
                    try:
                        if param_str.startswith('{'):
                            arguments = json.loads(param_str)
                        else:
                            arguments = {"input": param_str}
                    except:
                        arguments = {"input": param_str}
                break
        
        return tool_name, arguments
    
    def _extract_response_content(self, lines: List[str]) -> str:
        """提取响应内容"""
        content = []
        in_response = False
        
        for line in lines:
            if "响应内容" in line or "回答" in line:
                in_response = True
                continue
            elif in_response and line.startswith("**"):
                break
            elif in_response:
                content.append(line)
        
        return "\n".join(content).strip()
    
    def _extract_task_info(self, lines: List[str]) -> tuple:
        """提取任务信息"""
        action = None
        task_id = None
        description = None
        
        for line in lines:
            if "任务动作" in line or "action" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    action = parts[-1].strip().strip('`').strip()
            elif "任务ID" in line or "task_id" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    task_id = parts[-1].strip().strip('`').strip()
            elif "任务描述" in line or "description" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    description = parts[-1].strip().strip('`').strip()
        
        return action, task_id, description
