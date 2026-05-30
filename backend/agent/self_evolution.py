"""
SerpentAI 自进化系统
实现技能自动生成、优化、修复和蒸馏

⚠️ 安全设计：所有代码修改默认存储到待审批队列，由管理员确认后才应用。
仅当 safe_mode=False 时才自动应用修复。
"""

import asyncio
import logging
import ast
import re
import os
import shutil
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib

from backend.models.base_model import Message, create_adapter

logger = logging.getLogger(__name__)


@dataclass
class EvolutionResult:
    """进化结果"""
    success: bool
    tool_name: str
    evolution_type: str  # 'fix', 'optimize', 'generate', 'distill'
    fixed: bool = False
    applied: bool = False  # 是否已实际应用到文件
    suggestion: Optional[str] = None
    fix_description: Optional[str] = None
    code_change: Optional[str] = None
    improvement: float = 0.0  # 改进程度 0-1
    timestamp: datetime = field(default_factory=datetime.now)


class SelfEvolution:
    """
    自进化系统
    
    核心功能：
    1. 错误分析：从失败中提取错误模式
    2. 技能修复：自动修复工具中的 bug
    3. 技能优化：优化代码性能和可维护性
    4. 技能生成：根据需求生成新工具
    5. 技能蒸馏：压缩和简化技能描述
    """
    
    def __init__(self):
        self.model_adapter = None
        self.evolution_log: List[EvolutionResult] = []
        
        # 进化配置
        self.auto_fix = False  # 默认关闭，需管理员审批
        self.auto_optimize = False
        self.learn_from_errors = True
        
        # 待审批的修复队列
        self.pending_fixes: List[Dict[str, Any]] = []
        
        # 备份目录
        self.backup_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "backups", "evolutions"
        )
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 工具代码路径映射
        self._tool_code_paths: Dict[str, str] = {}
        self._discover_tool_paths()
        
        logger.info("自进化系统初始化完成（安全模式：修复需审批）")
        logger.warning("⚠️ auto_fix=False，建议通过 pending_fixes 队列审批修复")
    
    def _init_model(self):
        """延迟初始化模型"""
        if self.model_adapter is None:
            self.model_adapter = create_adapter("gpt-4o")
    
    async def analyze_and_fix(
        self,
        tool_name: str,
        error_message: str,
        context: Dict[str, Any]
    ) -> EvolutionResult:
        """
        分析错误并尝试修复
        
        Args:
            tool_name: 工具名称
            error_message: 错误信息
            context: 错误上下文
        
        Returns:
            EvolutionResult: 进化结果
        """
        self._init_model()
        
        logger.info(f"自进化：分析错误 | 工具: {tool_name}")
        
        try:
            # 1. 分析错误
            analysis = await self._analyze_error(tool_name, error_message, context)
            
            if not analysis["fixable"]:
                return EvolutionResult(
                    success=False,
                    tool_name=tool_name,
                    evolution_type="fix",
                    suggestion=analysis.get("suggestion", "无法自动修复")
                )
            
            # 2. 生成修复代码
            fix = await self._generate_fix(tool_name, analysis)
            
            # 3. 验证修复
            if await self._verify_fix(tool_name, fix):
                # 4. 应用修复
                await self._apply_fix(tool_name, fix)
                
                return EvolutionResult(
                    success=True,
                    tool_name=tool_name,
                    evolution_type="fix",
                    fixed=True,
                    fix_description=fix.get("description"),
                    code_change=fix.get("new_code"),
                    improvement=0.7
                )
            else:
                return EvolutionResult(
                    success=False,
                    tool_name=tool_name,
                    evolution_type="fix",
                    suggestion="修复验证失败，需要人工介入"
                )
        
        except Exception as e:
            logger.error(f"自进化失败 | 工具: {tool_name} | 错误: {e}")
            return EvolutionResult(
                success=False,
                tool_name=tool_name,
                evolution_type="fix",
                suggestion=f"分析过程出错: {e}"
            )
    
    async def optimize_tool(self, tool_name: str) -> EvolutionResult:
        """
        优化工具代码
        
        优化方向：
        1. 性能优化（减少循环、缓存结果）
        2. 代码简化（删除冗余代码）
        3. 错误处理增强
        """
        self._init_model()
        
        logger.info(f"自进化：优化工具 | 工具: {tool_name}")
        
        try:
            # 获取工具代码
            tool_code = self._get_tool_code(tool_name)
            if not tool_code:
                return EvolutionResult(
                    success=False,
                    tool_name=tool_name,
                    evolution_type="optimize",
                    suggestion="无法获取工具代码"
                )
            
            # 分析优化点
            optimization_prompt = f"""分析以下 Python 工具代码，找出可优化的地方：

工具名称: {tool_name}

代码:
```python
{tool_code}
```

请分析：
1. 性能问题（循环、重复计算等）
2. 代码冗余
3. 错误处理不完善的地方
4. 可缓存的结果

提供具体的优化建议和优化后的代码片段。"""
            
            messages = [Message(role="user", content=optimization_prompt)]
            response = self.model_adapter.generate(messages)
            
            # 解析优化建议
            optimization = self._parse_optimization_response(response.content)
            
            if optimization["optimized"]:
                # 应用优化
                optimized_code = await self._apply_optimization(tool_name, optimization)
                
                return EvolutionResult(
                    success=True,
                    tool_name=tool_name,
                    evolution_type="optimize",
                    fix_description=optimization.get("description"),
                    code_change=optimized_code,
                    improvement=optimization.get("improvement", 0.3)
                )
            
            return EvolutionResult(
                success=False,
                tool_name=tool_name,
                evolution_type="optimize",
                suggestion="未发现明显的优化空间"
            )
        
        except Exception as e:
            logger.error(f"优化失败 | 工具: {tool_name} | 错误: {e}")
            return EvolutionResult(
                success=False,
                tool_name=tool_name,
                evolution_type="optimize",
                suggestion=f"优化过程出错: {e}"
            )
    
    async def generate_skill(
        self,
        requirement: str,
        category: str = "custom"
    ) -> EvolutionResult:
        """
        根据需求生成新技能
        
        Args:
            requirement: 技能需求描述
            category: 技能分类
        
        Returns:
            EvolutionResult: 生成结果
        """
        self._init_model()
        
        logger.info(f"自进化：生成技能 | 需求: {requirement[:50]}...")
        
        try:
            generation_prompt = f"""根据以下需求生成一个完整的 Python 工具函数：

需求: {requirement}

要求：
1. 函数名使用 snake_case 命名
2. 参数使用 Dict[str, Any] 类型
3. 返回 Dict[str, Any] 类型
4. 包含完整的错误处理
5. 添加详细的文档字符串
6. 遵循 SerpentAI 工具编写规范

返回格式：
1. 函数名称
2. 函数代码（完整可运行）
3. 工具描述（用于注册）
4. 参数说明

代码规范：
- 导入标准库，不依赖第三方库
- 处理可能的异常
- 返回值包含 success 字段表示执行是否成功"""
            
            messages = [Message(role="user", content=generation_prompt)]
            response = self.model_adapter.generate(messages)
            
            # 解析生成的代码
            generated = self._parse_generated_code(response.content)
            
            if generated["code"]:
                # 注册新工具
                await self._register_generated_tool(generated, category)
                
                return EvolutionResult(
                    success=True,
                    tool_name=generated.get("name", "generated_tool"),
                    evolution_type="generate",
                    fixed=True,
                    fix_description=f"成功生成 {category} 类工具",
                    code_change=generated["code"],
                    improvement=1.0
                )
            
            return EvolutionResult(
                success=False,
                tool_name="unknown",
                evolution_type="generate",
                suggestion="代码生成失败，请重试或提供更详细的需求"
            )
        
        except Exception as e:
            logger.error(f"技能生成失败 | 错误: {e}")
            return EvolutionResult(
                success=False,
                tool_name="unknown",
                evolution_type="generate",
                suggestion=f"生成过程出错: {e}"
            )
    
    async def distill_skill_description(self, tool_name: str) -> EvolutionResult:
        """
        蒸馏技能描述，减少 Token 消耗
        
        策略：
        1. 简化描述文本
        2. 合并相似参数
        3. 移除冗余说明
        4. 压缩参数名称
        """
        self._init_model()
        
        logger.info(f"自进化：蒸馏工具描述 | 工具: {tool_name}")
        
        try:
            # 获取工具信息
            registry = self._get_registry()
            tool_info = registry.get_tool(tool_name)
            
            if not tool_info:
                return EvolutionResult(
                    success=False,
                    tool_name=tool_name,
                    evolution_type="distill",
                    suggestion="工具不存在"
                )
            
            distillation_prompt = f"""精简以下工具描述，减少 Token 消耗但不损失功能：

工具名称: {tool_name}
当前描述: {tool_info.get('description', '')}

当前参数:
{self._format_parameters(tool_info.get('parameters', {}))}

要求：
1. 描述精简到 50 字以内
2. 移除冗余的说明文字
3. 合并相似参数的说明
4. 使用缩写代替长词（如 'directory' -> 'dir'）

返回精简后的：
1. 工具描述
2. 参数说明（精简版）"""
            
            messages = [Message(role="user", content=distillation_prompt)]
            response = self.model_adapter.generate(messages)
            
            # 应用蒸馏结果
            distilled = self._parse_distilled_response(response.content)
            
            if distilled:
                await self._apply_distillation(tool_name, distilled)
                
                # 计算 Token 减少量
                original_tokens = len(json.dumps(tool_info))
                distilled_tokens = len(json.dumps(distilled))
                improvement = (original_tokens - distilled_tokens) / original_tokens
                
                return EvolutionResult(
                    success=True,
                    tool_name=tool_name,
                    evolution_type="distill",
                    fixed=True,
                    fix_description="描述已精简",
                    improvement=max(improvement, 0.2)
                )
            
            return EvolutionResult(
                success=False,
                tool_name=tool_name,
                evolution_type="distill",
                suggestion="蒸馏失败"
            )
        
        except Exception as e:
            logger.error(f"蒸馏失败 | 工具: {tool_name} | 错误: {e}")
            return EvolutionResult(
                success=False,
                tool_name=tool_name,
                evolution_type="distill",
                suggestion=f"蒸馏过程出错: {e}"
            )
    
    # ==================== 内部方法 ====================
    
    async def _analyze_error(
        self,
        tool_name: str,
        error_message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析错误"""
        
        analysis_prompt = f"""分析以下工具执行错误：

工具名称: {tool_name}
错误信息: {error_message}

上下文:
{self._format_context(context)}

请判断：
1. 错误类型（语法错误、运行时错误、参数错误、网络错误等）
2. 是否可以自动修复
3. 如果可以修复，提供修复方案

返回 JSON 格式：
{{
    "fixable": true/false,
    "error_type": "...",
    "root_cause": "...",
    "fix_suggestion": "...",
    "code_fix": "..." (如果有)
}}"""
        
        messages = [Message(role="user", content=analysis_prompt)]
        response = self.model_adapter.generate(messages)
        
        try:
            # 提取 JSON
            import json
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"fixable": False, "suggestion": "无法自动分析"}
    
    async def _generate_fix(
        self,
        tool_name: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成修复代码"""
        fix_prompt = f"""基于以下分析，生成工具修复代码：

工具名称: {tool_name}
错误类型: {analysis.get('error_type')}
根因: {analysis.get('root_cause')}
修复建议: {analysis.get('fix_suggestion')}

请生成修复后的完整函数代码。"""
        
        messages = [Message(role="user", content=fix_prompt)]
        response = self.model_adapter.generate(messages)
        
        return {
            "description": analysis.get("fix_suggestion", ""),
            "new_code": self._extract_code(response.content)
        }
    
    async def _verify_fix(self, tool_name: str, fix: Dict[str, Any]) -> bool:
        """验证修复"""
        # 基本验证
        if not fix.get("new_code"):
            return False
        
        # 语法检查
        try:
            compile(fix["new_code"], "<string>", "exec")
            return True
        except SyntaxError:
            return False
    
    async def _apply_fix(self, tool_name: str, fix: Dict[str, Any]):
        """应用修复
        
        安全策略：
        1. 所有修复先存入 pending_fixes 队列
        2. auto_fix=True 时自动备份+应用
        3. auto_fix=False 时仅记录，人工审批后调用 apply_pending_fix()
        """
        new_code = fix.get("new_code", "")
        if not new_code:
            logger.warning(f"修复代码为空，跳过: {tool_name}")
            return
        
        fix_record = {
            "tool_name": tool_name,
            "new_code": new_code,
            "description": fix.get("description", ""),
            "timestamp": datetime.now().isoformat(),
            "applied": False,
        }
        
        if tool_name in self._tool_code_paths:
            # 备份原文件
            src_path = self._tool_code_paths[tool_name]
            backup_name = f"{tool_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py.bak"
            backup_path = os.path.join(self.backup_dir, backup_name)
            try:
                shutil.copy2(src_path, backup_path)
                fix_record["backup_path"] = backup_path
                fix_record["source_path"] = src_path
                logger.info(f"已备份: {backup_path}")
            except Exception as e:
                logger.error(f"备份失败: {e}")
        
        if self.auto_fix:
            # 自动应用（危险！仅建议开发环境使用）
            await self._do_apply_fix(tool_name, new_code)
            fix_record["applied"] = True
            fix_record["auto_applied"] = True
            logger.warning(f"⚠️ 自动应用修复（auto_fix=True）: {tool_name}")
        else:
            logger.info(f"修复已加入待审批队列: {tool_name}")
        
        # 加入待审批队列
        self.pending_fixes.append(fix_record)
        
        # 记录到进化日志
        self.evolution_log.append(EvolutionResult(
            success=True,
            tool_name=tool_name,
            evolution_type="fix",
            fixed=True,
            applied=fix_record["applied"],
            fix_description=fix.get("description"),
            code_change=new_code,
        ))
    
    async def _do_apply_fix(self, tool_name: str, new_code: str):
        """Execute actual code fix (high-risk operation)

        Security constraints:
        1. Only files under backend/ directory allowed
        2. AST syntax validation before writing
        3. Backup before writing
        4. Full file replacement
        """
        if tool_name not in self._tool_code_paths:
            logger.error(f"Unknown tool, cannot fix: {tool_name}")
            return False

        src_path = self._tool_code_paths[tool_name]
        abs_src = os.path.abspath(src_path)
        backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if not abs_src.startswith(backend_root + os.sep):
            logger.error(f"[SECURITY] Rejected: path outside backend/: {src_path}")
            return False

        try:
            # 1. AST validation
            try:
                ast.parse(new_code)
            except SyntaxError as e:
                logger.error(f"[SECURITY] AST validation failed, rejected: {tool_name} -- {e}")
                return False

            # 2. Dangerous pattern detection
            for pat in ["__import__", "exec(", "eval(", "open(", "compile(",
                        "os.system", "subprocess.call", "importlib"]:
                if pat in new_code:
                    logger.error(f"[SECURITY] Dangerous pattern detected ({pat}), rejected: {tool_name}")
                    return False

            with open(src_path, "r", encoding="utf-8") as f:
                original_content = f.read()
            # 3. Backup
            backup_name = f"{os.path.basename(src_path)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py.bak"
            backup_path = os.path.join(self.backup_dir, backup_name)
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)
            logger.info(f"Backed up: {backup_path}")

            # 4. Write new file (full replacement)
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(new_code)

            logger.info(f"Fix applied: {tool_name} -> {src_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply fix: {e}")
            return False
    
    def apply_pending_fix(self, index: int) -> bool:
        """手动审批并应用待定的修复"""
        if index < 0 or index >= len(self.pending_fixes):
            logger.error(f"无效的修复索引: {index}")
            return False
        
        fix = self.pending_fixes[index]
        if fix["applied"]:
            logger.warning(f"修复已应用: {fix['tool_name']}")
            return False
        
        # 同步执行（不能在 async 外直接 await，但这里是同步调用）
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self._do_apply_fix(fix["tool_name"], fix["new_code"])
            )
            if result:
                fix["applied"] = True
                fix["approved_at"] = datetime.now().isoformat()
            return result
        finally:
            loop.close()
    
    def get_pending_fixes(self) -> List[Dict[str, Any]]:
        """获取待审批的修复列表"""
        return [
            {"index": i, **f}
            for i, f in enumerate(self.pending_fixes)
            if not f["applied"]
        ]
    
    def _discover_tool_paths(self):
        """发现工具代码文件路径"""
        import backend.tools.builtin_tools as bt_module
        tools_dir = os.path.dirname(bt_module.__file__)
        if os.path.isdir(tools_dir):
            for fname in os.listdir(tools_dir):
                if fname.endswith('.py') and not fname.startswith('_'):
                    fpath = os.path.join(tools_dir, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 提取函数名
                        for match in re.finditer(r'^def (\w+)\(', content, re.MULTILINE):
                            self._tool_code_paths[match.group(1)] = fpath
        logger.info(f"已发现 {len(self._tool_code_paths)} 个工具函数")

    def _get_tool_code(self, tool_name: str) -> Optional[str]:
        """获取工具源代码"""
        if tool_name not in self._tool_code_paths:
            logger.warning(f"工具 '{tool_name}' 代码路径未知")
            return None
        
        try:
            fpath = self._tool_code_paths[tool_name]
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取单个函数的代码
            pattern = rf'(def {re.escape(tool_name)}\([^)]*\):.*?)(?=\n(?:def |class |\Z))'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            logger.error(f"读取工具代码失败: {e}")
            return None
    
    def _get_registry(self):
        """获取工具注册表"""
        from backend.tools import get_global_registry
        return get_global_registry()
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文"""
        return "\n".join([f"{k}: {v}" for k, v in context.items()])
    
    def _format_parameters(self, params: Dict) -> str:
        """格式化参数"""
        if not params:
            return "无参数"
        return "\n".join([f"- {k}: {v.get('type', 'any')}" for k, v in params.items()])
    
    def _parse_optimization_response(self, response: str) -> Dict[str, Any]:
        """解析优化响应"""
        return {
            "optimized": "optimized" in response.lower() or "优化" in response,
            "description": "代码已优化",
            "improvement": 0.3
        }
    
    def _parse_generated_code(self, response: str) -> Dict[str, Any]:
        """解析生成的代码"""
        code = self._extract_code(response)
        
        # 提取函数名
        name_match = re.search(r'def\s+(\w+)', code) if code else None
        name = name_match.group(1) if name_match else "generated_tool"
        
        return {
            "code": code,
            "name": name,
            "description": f"自动生成的工具: {name}"
        }
    
    def _parse_distilled_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析蒸馏响应"""
        # 提取精简后的描述
        return {"description": response[:200]}
    
    def _extract_code(self, text: str) -> str:
        """从文本中提取代码块"""
        # 提取 ```python ... ``` 或 ``` ... ``` 中的内容
        patterns = [
            r'```python\s*(.*?)```',
            r'```\s*(.*?)```'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return text.strip()
    
    async def _apply_optimization(self, tool_name: str, optimization: Dict) -> str:
        """应用优化代码"""
        optimized_code = optimization.get("code", "")
        if optimized_code and self.auto_optimize:
            await self._do_apply_fix(tool_name, optimized_code)
            logger.info(f"✅ 优化已应用: {tool_name}")
        else:
            logger.info(f"优化已记录（待审批）: {tool_name}")
        return optimized_code
    
    async def _register_generated_tool(self, generated: Dict, category: str):
        """注册生成的工具"""
        try:
            registry = self._get_registry()
            registry.register_builtin_tool({
                "name": generated["name"],
                "description": generated.get("description", ""),
                "category": category,
                "code": generated["code"]
            })
            logger.info(f"工具已注册 | 名称: {generated['name']}")
        except Exception as e:
            logger.error(f"工具注册失败: {e}")
    
    def _apply_distillation(self, tool_name: str, distilled: Dict):
        """应用蒸馏结果到工具注册表"""
        try:
            registry = self._get_registry()
            # 更新工具描述（需要 registry 支持 update_tool）
            new_description = distilled.get("description", "")
            if new_description and hasattr(registry, 'update_tool_description'):
                registry.update_tool_description(tool_name, new_description)
                logger.info(f"✅ 蒸馏描述已更新: {tool_name}")
            elif new_description:
                # 如果注册表不支持 update，存入进化日志供参考
                logger.info(f"蒸馏结果已记录（注册表不支持动态更新）: {tool_name}")
                self.evolution_log.append(EvolutionResult(
                    success=True,
                    tool_name=tool_name,
                    evolution_type="distill",
                    fixed=True,
                    applied=False,
                    suggestion="蒸馏结果已记录，需手动更新",
                    improvement=distilled.get("improvement", 0.0)
                ))
        except Exception as e:
            logger.error(f"蒸馏应用失败: {e}")
    
    def get_evolution_history(self, limit: int = 20) -> List[EvolutionResult]:
        """获取进化历史"""
        return self.evolution_log[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取进化统计"""
        total = len(self.evolution_log)
        fixes = sum(1 for e in self.evolution_log if e.evolution_type == "fix" and e.fixed)
        optimizations = sum(1 for e in self.evolution_log if e.evolution_type == "optimize" and e.fixed)
        generations = sum(1 for e in self.evolution_log if e.evolution_type == "generate" and e.fixed)
        
        return {
            "total_evolutions": total,
            "fixes_applied": fixes,
            "optimizations_applied": optimizations,
            "skills_generated": generations,
            "auto_fix_enabled": self.auto_fix,
            "auto_optimize_enabled": self.auto_optimize,
            "learn_from_errors": self.learn_from_errors
        }


# 需要 json 模块
import json
