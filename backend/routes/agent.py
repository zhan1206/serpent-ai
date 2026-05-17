"""
SerpentAI Agent API 路由
提供智能体相关的 API 接口
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.agent import (
    get_agent, get_multi_agent,
    SerpentAgent, AgentConfig, AgentMode,
    MultiAgentCollaboration, AgentRole,
    SelfEvolution, Task, TaskStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["Agent"])


# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: Optional[str] = "gpt-4o"
    max_iterations: Optional[int] = 10


class TaskCreateRequest(BaseModel):
    description: str
    priority: Optional[int] = 3
    session_id: Optional[str] = None


class SkillGenerateRequest(BaseModel):
    requirement: str
    category: Optional[str] = "custom"


# ==================== 智能体接口 ====================

@router.post("/chat")
async def agent_chat(request: ChatRequest):
    """
    智能体聊天接口
    
    使用 ReAct 范式进行推理和行动
    """
    try:
        # 获取或创建智能体
        agent = get_agent(AgentConfig(model=request.model))
        
        # 运行智能体
        result = await agent.run(
            session_id=request.session_id,
            user_message=request.message
        )
        
        return result
    
    except Exception as e:
        logger.error(f"智能体聊天失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_agent_stats():
    """获取智能体统计信息"""
    try:
        agent = get_agent()
        return agent.get_stats()
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_session(session_id: str = Query(..., description="会话ID")):
    """重置会话上下文"""
    try:
        agent = get_agent()
        agent.reset_context(session_id)
        return {"status": "success", "message": f"会话 {session_id} 已重置"}
    except Exception as e:
        logger.error(f"重置会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 任务管理接口 ====================

@router.post("/tasks")
async def create_task(request: TaskCreateRequest):
    """创建任务"""
    try:
        agent = get_agent()
        scheduler = agent.task_scheduler
        
        task_id = scheduler.create_task(
            description=request.description,
            priority=request.priority,
            metadata={"session_id": request.session_id} if request.session_id else {}
        )
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": f"任务已创建: {request.description[:50]}"
        }
    
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态过滤"),
    session_id: Optional[str] = Query(None, description="按会话过滤")
):
    """列出任务"""
    try:
        agent = get_agent()
        scheduler = agent.task_scheduler
        
        tasks = scheduler.get_pending_tasks()
        
        # 过滤
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        
        return {
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "status": t.status.value,
                    "priority": t.priority,
                    "created_at": t.created_at.isoformat()
                }
                for t in tasks
            ],
            "count": len(tasks)
        }
    
    except Exception as e:
        logger.error(f"列出任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    try:
        agent = get_agent()
        task = agent.task_scheduler.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "id": task.id,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority,
            "progress": task.progress,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "error": task.error
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        agent = get_agent()
        success = agent.task_scheduler.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="无法取消任务（可能正在运行）")
        
        return {"status": "success", "message": f"任务 {task_id} 已取消"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    """恢复任务"""
    try:
        agent = get_agent()
        success = agent.task_scheduler.resume_task(task_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="无法恢复任务")
        
        return {"status": "success", "message": f"任务 {task_id} 已恢复"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 自进化接口 ====================

@router.post("/evolve/fix")
async def evolve_fix(
    tool_name: str = Query(..., description="工具名称"),
    error_message: str = Query(..., description="错误信息")
):
    """自进化：修复错误"""
    try:
        agent = get_agent()
        evolution = agent.self_evolution
        
        result = await evolution.analyze_and_fix(
            tool_name=tool_name,
            error_message=error_message,
            context={}
        )
        
        return {
            "success": result.success,
            "fixed": result.fixed,
            "suggestion": result.suggestion,
            "fix_description": result.fix_description,
            "improvement": result.improvement
        }
    
    except Exception as e:
        logger.error(f"自进化修复失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolve/optimize")
async def evolve_optimize(tool_name: str = Query(..., description="工具名称")):
    """自进化：优化工具"""
    try:
        agent = get_agent()
        evolution = agent.self_evolution
        
        result = await evolution.optimize_tool(tool_name)
        
        return {
            "success": result.success,
            "improvement": result.improvement,
            "fix_description": result.fix_description
        }
    
    except Exception as e:
        logger.error(f"自进化优化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolve/generate")
async def evolve_generate(request: SkillGenerateRequest):
    """自进化：生成新技能"""
    try:
        agent = get_agent()
        evolution = agent.self_evolution
        
        result = await evolution.generate_skill(
            requirement=request.requirement,
            category=request.category
        )
        
        return {
            "success": result.success,
            "tool_name": result.tool_name,
            "fix_description": result.fix_description,
            "code_change": result.code_change
        }
    
    except Exception as e:
        logger.error(f"技能生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolve/distill")
async def evolve_distill(tool_name: str = Query(..., description="工具名称")):
    """自进化：蒸馏工具描述"""
    try:
        agent = get_agent()
        evolution = agent.self_evolution
        
        result = await evolution.distill_skill_description(tool_name)
        
        return {
            "success": result.success,
            "improvement": result.improvement,
            "fix_description": result.fix_description
        }
    
    except Exception as e:
        logger.error(f"工具蒸馏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolve/stats")
async def get_evolution_stats():
    """获取自进化统计"""
    try:
        agent = get_agent()
        return agent.self_evolution.get_stats()
    
    except Exception as e:
        logger.error(f"获取进化统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 多智能体协作接口 ====================

@router.post("/team/create")
async def create_team():
    """创建默认团队"""
    try:
        multi_agent = get_multi_agent()
        agent_ids = multi_agent.create_default_team()
        
        return {
            "status": "success",
            "agent_ids": agent_ids,
            "message": f"团队创建完成，共 {len(agent_ids)} 名成员"
        }
    
    except Exception as e:
        logger.error(f"创建团队失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team")
async def get_team():
    """获取团队信息"""
    try:
        multi_agent = get_multi_agent()
        
        agents = multi_agent.list_agents()
        
        return {
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role.value,
                    "capabilities": a.capabilities,
                    "status": a.status,
                    "tasks_completed": a.tasks_completed
                }
                for a in agents
            ],
            "stats": multi_agent.get_team_stats()
        }
    
    except Exception as e:
        logger.error(f"获取团队信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team/collaborate")
async def team_collaborate(
    task: str = Query(..., description="协作任务"),
    mode: str = Query("parallel", description="协作模式 (parallel/sequential/vote/pipeline)")
):
    """多智能体协作"""
    try:
        multi_agent = get_multi_agent()
        
        # 如果没有团队，创建默认团队
        if not multi_agent.list_agents():
            multi_agent.create_default_team()
        
        result = await multi_agent.collaborate(task=task, mode=mode)
        
        return {
            "success": result.success,
            "task_id": result.task_id,
            "final_result": result.final_result,
            "duration": result.duration,
            "errors": result.errors,
            "sub_results_count": len(result.sub_results)
        }
    
    except Exception as e:
        logger.error(f"多智能体协作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team/register")
async def register_sub_agent(
    name: str = Query(..., description="智能体名称"),
    role: str = Query(..., description="智能体角色"),
    capabilities: str = Query("", description="能力列表，逗号分隔")
):
    """注册子智能体"""
    try:
        multi_agent = get_multi_agent()
        
        # 解析角色
        try:
            agent_role = AgentRole(role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的角色: {role}")
        
        # 解析能力
        cap_list = [c.strip() for c in capabilities.split(",") if c.strip()]
        
        # 注册
        agent_id = multi_agent.register_agent(
            name=name,
            role=agent_role,
            capabilities=cap_list
        )
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "message": f"智能体 {name} 已注册"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册子智能体失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
