"""
效率引擎API路由
Token优化、提示词蒸馏、缓存管理等
"""
from fastapi import APIRouter, Request, HTTPException, Query

router = APIRouter(prefix="/api/efficiency", tags=["效率引擎"])


@router.get("/stats")
async def get_efficiency_stats():
    """获取效率引擎统计信息"""
    try:
        from backend.efficiency import get_global_engine
        engine = get_global_engine()
        return {
            "token_optimizer": engine["token_optimizer"].get_stats(),
            "prompt_distiller": engine["prompt_distiller"].get_cache_stats(),
            "output_compressor": engine["output_compressor"].get_stats(),
            "cache": engine["cache"].get_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compress")
async def compress_output(request: Request):
    """压缩模型输出"""
    try:
        from backend.efficiency import get_global_engine
        data = await request.json()
        output = data.get("output", "")
        format_type = data.get("format", "plain")
        engine = get_global_engine()
        compressed = engine["output_compressor"].compress(output)
        formatted = engine["output_compressor"].format_output(compressed, format_type)
        return {
            "original_length": len(output),
            "compressed_length": len(compressed),
            "output": formatted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/distill-prompt")
async def distill_prompt(request: Request):
    """蒸馏提示词"""
    try:
        from backend.efficiency import get_global_engine
        data = await request.json()
        prompt = data.get("prompt", "")
        context = data.get("context")
        engine = get_global_engine()
        distilled = engine["prompt_distiller"].distill(prompt, context)
        return {
            "original_length": len(prompt),
            "distilled_length": len(distilled),
            "output": distilled
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/")
async def cache_operation(request: Request, op: str = Query(..., alias="operation")):
    """缓存操作"""
    try:
        from backend.efficiency import get_global_engine
        data = await request.json() if op == "set" else {}
        cache_type = data.get("cache_type", "prompt")
        key = data.get("key", "")
        value = data.get("value")
        engine = get_global_engine()
        cache = engine["cache"]
        if op == "get":
            return {"value": cache.get(cache_type, key)}
        elif op == "set":
            cache.set(cache_type, key, value)
            return {"status": "success"}
        elif op == "clear":
            cache.clear(cache_type if cache_type != "all" else None)
            return {"status": "success"}
        raise HTTPException(status_code=400, detail=f"Unknown: {op}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def efficiency_health_check():
    """效率引擎健康检查"""
    try:
        from backend.efficiency import get_global_engine
        engine = get_global_engine()
        
        # 检查各个组件
        status = {
            "token_optimizer": "healthy",
            "prompt_distiller": "healthy", 
            "output_compressor": "healthy",
            "cache": "healthy"
        }
        
        # 检查实际组件
        try:
            engine["token_optimizer"].get_stats()
        except Exception:
            status["token_optimizer"] = "error"
        
        try:
            engine["prompt_distiller"].get_cache_stats()
        except Exception:
            status["prompt_distiller"] = "error"
            
        try:
            engine["output_compressor"].get_stats()
        except Exception:
            status["output_compressor"] = "error"
        
        try:
            engine["cache"].get_stats()
        except Exception:
            status["cache"] = "error"
        
        all_healthy = all(v == "healthy" for v in status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "components": status
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }