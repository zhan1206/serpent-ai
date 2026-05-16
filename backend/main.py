"""
SerpentAI 主应用入口
FastAPI应用初始化、路由配置、中间件设置
集成四层记忆系统（瞬时、短期、长期、归档）
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from core.config import settings, get_settings
from core.logging_config import setup_logging, get_logger
from core.database import init_db, check_db_health
from models.base_model import Message

# 导入工具系统集成
from tools import get_global_registry, get_global_precompiler, get_global_distiller
from tools.builtin_tools import register_all_builtin_tools

from routes.efficiency import router as efficiency_router
from routes.gateway import router as gateway_router
from gateways import get_gateway_manager, get_message_router

# 导入效率引擎
from efficiency import get_global_engine

# 初始化日志
setup_logging()
logger = get_logger(__name__)

# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理
    启动时初始化资源，关闭时清理资源
    """
    logger.info("=" * 60)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 正在启动...")
    logger.info("=" * 60)
    
    try:
        # 初始化数据库
        logger.info("正在初始化数据库...")
        init_db()
        
        # 检查数据库连接
        db_health = check_db_health()
        logger.info(f"数据库健康检查: {db_health}")
        
        # 初始化Neo4j约束
        from core.database import init_neo4j_constraints
        try:
            init_neo4j_constraints()
        except Exception as e:
            logger.warning(f"Neo4j初始化失败（可稍后重试）: {e}")
        
        logger.info(f"{settings.APP_NAME} 启动完成！")
        logger.info(f"调试模式: {settings.DEBUG}")
        logger.info(f"环境: {settings.ENVIRONMENT}")
        logger.info("记忆系统已集成：瞬时、短期、长期、归档")
        
        # 初始化工具系统
        logger.info("正在初始化工具系统...")
        try:
            # 注册内置工具
            register_all_builtin_tools()
            
            # 预编译和蒸馏工具（Token优化）
            from tools.tool_precompiler import precompile_tools
            from tools.tool_distiller import distill_tools
            
            precompile_tools()
            distill_tools()
            
            logger.info("工具系统初始化完成！")
            logger.info(f"已注册工具数: {len(get_global_registry().list_tools())}")
        except Exception as e:
            logger.warning(f"工具系统初始化失败（可稍后重试）: {e}")
        
    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise
    
    yield  # 应用运行期间
    
    # 关闭时清理资源
    logger.info("正在关闭应用...")
    
    from core.database import close_neo4j_driver
    close_neo4j_driver()
    
    logger.info("应用已关闭")

# ==================== FastAPI应用初始化 ====================

app = FastAPI(
    title=settings.APP_NAME,
    description="终极自托管全功能AI智能体框架（集成四层记忆系统）",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 注册效率引擎路由
app.include_router(efficiency_router)
app.include_router(gateway_router)

# ==================== 中间件配置 ====================

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 路由配置 ====================

@app.get("/")
async def root():
    """根路由 - API信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "终极自托管全功能AI智能体框架",
        "documentation": "/api/docs",
        "status": "running",
        "memory_system": "enabled（四层记忆：瞬时、短期、长期、归档）"
    }

@app.get("/health")
async def health_check():
    """
    健康检查端点（包含记忆系统状态）
    """
    db_health = check_db_health()
    
    # 检查记忆系统
    memory_stats = {}
    try:
        from memory import get_memory_manager
        memory_mgr = get_memory_manager()
        memory_stats = memory_mgr.get_stats()
    except Exception as e:
        logger.error(f"记忆系统健康检查失败: {e}")
        memory_stats = {"error": str(e)}
    
    health_status = {
        "status": "healthy" if all(db_health.values()) else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_health,
        "memory": memory_stats
    }
    
    return health_status

@app.get("/api/models")
async def list_models():
    """
    列出所有支持的模型
    """
    from models.base_model import list_supported_models
    return {
        "models": list_supported_models(),
        "count": len(list_supported_models())
    }

@app.post("/api/chat")
async def chat(
    request: Request,
    session_id: str = Query(..., description="会话ID")
):
    """
    聊天接口（集成记忆系统）
    1. 从记忆召回上下文
    2. 调用模型生成响应
    3. 保存消息到记忆
    """
    try:
        data = await request.json()
        
        model_name = data.get("model", "gpt-3.5-turbo")
        messages = data.get("messages", [])
        
        if not messages:
            raise HTTPException(status_code=400, detail="消息列表不能为空")
        
        # 获取记忆管理器
        from memory import get_memory_manager
        memory_mgr = get_memory_manager()
        
        # 1. 从记忆系统召回上下文
        query = messages[-1]["content"] if messages else None
        logger.info(f"聊天请求 | session: {session_id} | query: {query[:50] if query else 'None'}...")
        
        recalled = memory_mgr.recall(
            session_id=session_id,
            query=query,
            limit=10,
            include_instant=True,
            include_short_term=True,
            include_long_term=True,
            include_archive=False
        )
        logger.info(f"召回记忆 | 数量: {len(recalled)}")
        
        # 2. 构建完整消息列表（召回的上下文 + 当前消息）
        context_msgs = [
            Message(role=msg["role"], content=msg["content"])
            for msg in recalled
        ]
        
        current_msgs = [
            Message(role=msg["role"], content=msg["content"])
            for msg in messages
        ]
        
        # 合并消息（去重由memory_mgr.recall处理）
        all_msgs = context_msgs + current_msgs
        
        # 3. 创建模型适配器
        from models.base_model import create_adapter
        adapter = create_adapter(model_name)
        
        # 4. 生成响应
        response = adapter.generate(all_msgs)
        
        # 5. 保存当前消息到记忆系统
        for msg in current_msgs:
            memory_mgr.add_message(session_id, msg)
            logger.debug(f"保存消息到记忆 | role: {msg.role}")
        
        # 6. 保存助手响应到记忆系统
        assistant_msg = Message(role="assistant", content=response.content)
        memory_mgr.add_message(session_id, assistant_msg)
        
        logger.info(f"聊天完成 | session: {session_id} | 响应长度: {len(response.content)}")
        
        return {
            "response": response.content,
            "model": response.model,
            "usage": {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.total_tokens,
            },
            "cost": response.cost,
            "latency_ms": response.latency_ms,
            "context_used": len(recalled)  # 使用的上下文数量
        }
        
    except Exception as e:
        logger.error(f"聊天接口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 记忆系统接口 ====================

@app.post("/api/memory/add")
async def add_to_memory(
    request: Request,
    session_id: str = Query(..., description="会话ID")
):
    """
    添加消息到记忆系统
    """
    try:
        data = await request.json()
        
        role = data.get("role", "user")
        content = data.get("content", "")
        
        if not content:
            raise HTTPException(status_code=400, detail="内容不能为空")
        
        # 创建消息对象
        message = Message(role=role, content=content)
        
        # 添加到记忆系统
        from memory import get_memory_manager
        memory_mgr = get_memory_manager()
        memory_mgr.add_message(session_id, message)
        
        logger.info(f"手动添加消息到记忆 | session: {session_id} | role: {role}")
        
        return {
            "status": "success",
            "message": "已添加到记忆系统"
        }
        
    except Exception as e:
        logger.error(f"添加消息到记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/memory/recall")
async def recall_from_memory(
    request: Request,
    session_id: str = Query(..., description="会话ID")
):
    """
    从记忆系统召回消息
    """
    try:
        data = await request.json()
        
        query = data.get("query")
        limit = data.get("limit", 10)
        include_instant = data.get("include_instant", True)
        include_short_term = data.get("include_short_term", True)
        include_long_term = data.get("include_long_term", True)
        include_archive = data.get("include_archive", False)
        
        # 从记忆系统召回
        from memory import get_memory_manager
        memory_mgr = get_memory_manager()
        
        results = memory_mgr.recall(
            session_id=session_id,
            query=query,
            limit=limit,
            include_instant=include_instant,
            include_short_term=include_short_term,
            include_long_term=include_long_term,
            include_archive=include_archive
        )
        
        logger.info(f"召回记忆 | session: {session_id} | query: {query[:50] if query else 'None'}... | 结果数: {len(results)}")
        
        return {
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"从记忆召回失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 工具系统接口 ====================

@app.get("/api/tools")
async def list_tools(
    category: Optional[str] = Query(None, description="按分类过滤"),
    tool_type: Optional[str] = Query(None, description="按类型过滤(mcp/builtin/custom)")
):
    """
    列出所有可用工具
    """
    try:
        registry = get_global_registry()
        tools = registry.list_tools(category=category, tool_type=tool_type)
        
        logger.info(f"列出工具 | 数量: {len(tools)}")
        
        return {
            "tools": tools,
            "count": len(tools),
            "category": category,
            "type": tool_type
        }
        
    except Exception as e:
        logger.error(f"列出工具失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/call")
async def call_tool(request: Request):
    """
    调用工具
    """
    try:
        data = await request.json()
        
        tool_name = data.get("tool_name")
        arguments = data.get("arguments", {})
        
        if not tool_name:
            raise HTTPException(status_code=400, detail="tool_name不能为空")
        
        # 调用工具
        from tools.tool_executor import execute_tool
        result = execute_tool(tool_name, arguments)
        
        logger.info(f"调用工具 | 工具: {tool_name} | 参数: {arguments}")
        
        return {
            "status": "success",
            "tool_name": tool_name,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"调用工具失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools/categories")
async def list_tool_categories():
    """
    列出所有工具分类
    """
    try:
        registry = get_global_registry()
        categories = registry.list_categories()
        
        return {
            "categories": categories,
            "count": len(categories)
        }
        
    except Exception as e:
        logger.error(f"列出工具分类失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tools/search")
async def search_tools(
    query: str = Query(..., description="搜索关键词")
):
    """
    搜索工具
    """
    try:
        registry = get_global_registry()
        results = registry.search_tools(query)
        
        logger.info(f"搜索工具 | 查询: {query} | 结果数: {len(results)}")
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"搜索工具失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tools/optimized-prompt")
async def get_optimized_tool_prompt():
    """
    获取优化后的工具提示词（Token优化）
    使用预编译和蒸馏技术，减少80% Token消耗
    """
    try:
        from tools.tool_precompiler import get_tools_prompt as get_precompiled
        from tools.tool_distiller import get_distilled_prompt
        
        # 获取两种优化提示词
        precompiled_prompt = get_precompiled()
        distilled_prompt = get_distilled_prompt()
        
        return {
            "precompiled_prompt": precompiled_prompt,
            "distilled_prompt": distilled_prompt,
            "optimization": "Tool precompilation + distillation reduces Token consumption by 80%"
        }
        
    except Exception as e:
        logger.error(f"获取优化提示词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/stats")
async def get_memory_stats():
    """
    获取记忆系统统计信息
    """
    try:
        from memory import get_memory_manager
        memory_mgr = get_memory_manager()
        
        stats = memory_mgr.get_stats()
        logger.info(f"获取记忆统计: {stats}")
        
        return stats
        
    except Exception as e:
        logger.error(f"获取记忆统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/memory/clear")
async def clear_memory(
    session_id: Optional[str] = Query(None, description="会话ID（不提供则清空所有）")
):
    """
    清空记忆（指定会话或全部）
    """
    try:
        from memory import get_memory_manager
        memory_mgr = get_memory_manager()
        
        if session_id:
            memory_mgr.clear_session(session_id)
            logger.info(f"清空会话记忆 | session: {session_id}")
            return {
                "status": "success",
                "message": f"已清空会话 {session_id} 的记忆"
            }
        else:
            memory_mgr.clear_all()
            logger.info("清空所有记忆")
            return {
                "status": "success",
                "message": "已清空所有记忆"
            }
        
    except Exception as e:
        logger.error(f"清空记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 错误处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": str(exc),
            "type": type(exc).__name__
        }
    )

# ==================== 启动脚本 ====================

if __name__ == "__main__":
    """
    本地开发启动入口
    生产环境应使用: uvicorn backend.main:app --host 0.0.0.0 --port 8000
    """
    logger.info("启动本地开发服务器...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
