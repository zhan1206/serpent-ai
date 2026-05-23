"""
SerpentAI 聊天路由
支持流式响应（Server-Sent Events）
"""
import json
import logging
import time
from typing import AsyncGenerator, List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models.base_model import Message, ModelResponse
from models.registry import ModelRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    model: Optional[str] = None
    session_id: Optional[str] = None
    stream: bool = True
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    tools: Optional[List[Dict[str, Any]]] = None

class ChatResponse(BaseModel):
    """聊天响应（非流式）"""
    message: str
    model: str
    usage: Dict[str, int]
    latency_ms: int

class SessionCreateRequest(BaseModel):
    """创建会话请求"""
    title: Optional[str] = None

# ==================== 聊天端点 ====================

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    聊天端点（支持流式/非流式）
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: 流式响应（SSE格式）
        JSONResponse: 非流式响应
    """
    try:
        # 获取模型
        model = await _get_model(request.model)
        
        # 构建消息历史（简化版，实际使用应从会话中获取）
        messages = [
            Message(role="user", content=request.message)
        ]
        
        # 流式响应
        if request.stream:
            return StreamingResponse(
                _stream_response(model, messages, request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
                }
            )
        
        # 非流式响应
        else:
            response = await model.generate(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools,
                stream=False
            )
            
            return {
                "message": response.content,
                "model": response.model,
                "usage": {
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens,
                    "cost": response.cost,
                },
                "latency_ms": response.latency_ms,
            }
            
    except Exception as e:
        logger.error(f"聊天失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 会话管理端点 ====================

@router.get("/sessions")
async def list_sessions():
    """
    列出所有会话
    
    Returns:
        Dict: 会话列表
    """
    # TODO: 从数据库获取会话列表
    # 暂时返回模拟数据
    return {
        "sessions": [
            {
                "id": "new",
                "title": "新对话",
                "created_at": int(time.time()),
                "message_count": 0,
            }
        ]
    }

@router.post("/sessions")
async def create_session(request: SessionCreateRequest):
    """
    创建新会话
    
    Args:
        request: 创建会话请求
        
    Returns:
        Dict: 新会话信息
    """
    session_id = f"session_{int(time.time())}"
    
    # TODO: 保存到数据库
    
    return {
        "id": session_id,
        "title": request.title or "新对话",
        "created_at": int(time.time()),
        "message_count": 0,
    }

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    获取会话详情和消息历史
    
    Args:
        session_id: 会话ID
        
    Returns:
        Dict: 会话详情和消息列表
    """
    # TODO: 从数据库获取会话和消息
    # 暂时返回模拟数据
    return {
        "id": session_id,
        "title": "新对话",
        "created_at": int(time.time()),
        "messages": []
    }

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话
    
    Args:
        session_id: 会话ID
        
    Returns:
        Dict: 删除结果
    """
    # TODO: 从数据库删除会话
    return {"status": "deleted", "session_id": session_id}

# ==================== 内部辅助函数 ====================

async def _get_model(model_name: Optional[str]):
    """
    获取模型实例
    
    Args:
        model_name: 模型名称（None 表示使用默认模型）
        
    Returns:
        模型适配器实例
    """
    registry = ModelRegistry()
    
    if model_name:
        # 按名称获取
        return registry.get_model(model_name)
    else:
        # 获取默认模型
        return registry.get_default_model()

async def _stream_response(
    model,
    messages: List[Message],
    request: ChatRequest
) -> AsyncGenerator[str, None]:
    """
    生成流式响应（SSE格式）
    
    Args:
        model: 模型实例
        messages: 消息历史
        request: 聊天请求
        
    Yields:
        str: SSE 格式的数据块
    """
    start_time = time.time()
    full_content = ""
    
    try:
        # 调用模型生成（流式）
        response_stream = await model.generate(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=request.tools,
            stream=True
        )
        
        # 处理流式响应
        if hasattr(response_stream, '__aiter__'):
            # 异步生成器
            async for chunk in response_stream:
                content = _extract_content(chunk)
                if content:
                    full_content += content
                    yield _sse_format({
                        "content": content,
                        "done": False
                    })
        else:
            # 同步生成器
            for chunk in response_stream:
                content = _extract_content(chunk)
                if content:
                    full_content += content
                    yield _sse_format({
                        "content": content,
                        "done": False
                    })
        
        # 发送完成信号（包含使用统计）
        latency_ms = int((time.time() - start_time) * 1000)
        input_tokens = model.count_tokens(request.message)
        output_tokens = model.count_tokens(full_content)
        
        yield _sse_format({
            "content": "",
            "done": True,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": 0.0,  # 本地模型无成本
            },
            "latency_ms": latency_ms,
        })
        
        # 结束标记
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"流式响应失败: {e}", exc_info=True)
        yield _sse_format({
            "error": str(e)
        })
        yield "data: [DONE]\n\n"

def _extract_content(chunk) -> str:
    """
    从数据块中提取文本内容
    
    Args:
        chunk: 数据块（可能是 dict、string 或对象）
        
    Returns:
        str: 文本内容
    """
    if isinstance(chunk, dict):
        # OpenAI 格式: {"choices": [{"delta": {"content": "..."}}]}
        if 'choices' in chunk and len(chunk['choices']) > 0:
            delta = chunk['choices'][0].get('delta', {})
            return delta.get('content', '')
        # 自定义格式: {"content": "..."}
        elif 'content' in chunk:
            return chunk['content']
        else:
            return ''
    elif isinstance(chunk, str):
        return chunk
    else:
        # 尝试获取 text 属性
        if hasattr(chunk, 'text'):
            return chunk.text
        else:
            return str(chunk)

def _sse_format(data: Dict[str, Any]) -> str:
    """
    格式化为 SSE 格式
    
    Args:
        data: 数据字典
        
    Returns:
        str: SSE 格式字符串
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
