# -*- coding: utf-8 -*-
"""
代码助手技能 - 辅助代码编写、审查、调试和重构
"""

import logging
from typing import Dict, List, Any, Optional
from ..skill import Skill, SkillManifest

logger = logging.getLogger(__name__)


class CodeAssistantSkill(Skill):
    """代码助手技能"""
    
    def __init__(self):
        manifest = SkillManifest(
            name="code_assistant",
            version="1.0.0",
            display_name="代码助手",
            description="辅助代码编写、审查、调试和重构，支持多种编程语言",
            author="SerpentAI",
            category="development",
            tags=["code", "programming", "debug", "review"],
            tools=["code_analyze", "code_generate", "code_review", "code_refactor", "code_explain"],
            prompt_template="""你是一个专业的代码助手。你的职责是：
1. 分析代码结构和质量
2. 生成符合最佳实践的代码
3. 审查代码中的潜在问题
4. 建议重构方案
5. 解释复杂的代码逻辑

语言: {language}
框架: {framework}
要求: {requirements}""",
            examples=[
                {
                    "input": "帮我写一个Python的快速排序",
                    "output": "def quicksort(arr): ..."
                },
                {
                    "input": "这段代码有什么问题？\ndef add(a, b): return a + b",
                    "output": "缺少类型注解和输入验证..."
                },
            ],
        )
        super().__init__(manifest, skill_dir="skills/builtin_skills/code_assistant")
    
    def analyze_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """分析代码"""
        lines = code.strip().split('\n')
        issues = []
        
        # 基础静态分析
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 检测常见问题
            if len(stripped) > 120:
                issues.append({"line": i, "type": "style", "message": "行过长(>120字符)"})
            if stripped.endswith(";;"):
                issues.append({"line": i, "type": "syntax", "message": "多余的分号"})
            if "TODO" in stripped or "FIXME" in stripped:
                issues.append({"line": i, "type": "todo", "message": "待办事项标记"})
            if stripped == "except:" and language == "python":
                issues.append({"line": i, "type": "quality", "message": "裸except捕获所有异常"})
            if "print(" in stripped and language == "python":
                issues.append({"line": i, "type": "style", "message": "使用print而非logging"})
        
        return {
            "total_lines": len(lines),
            "code_lines": sum(1 for l in lines if l.strip() and not l.strip().startswith('#')),
            "comment_lines": sum(1 for l in lines if l.strip().startswith('#')),
            "blank_lines": sum(1 for l in lines if not l.strip()),
            "issues": issues,
            "complexity": "low" if len(lines) < 50 else "medium" if len(lines) < 200 else "high",
            "language": language,
        }
    
    def generate_code(self, prompt: str, language: str = "python",
                      style: str = "clean") -> Dict[str, Any]:
        """生成代码框架"""
        templates = {
            "python": {
                "function": 'def {name}({params}):\n    """{docstring}"""\n    pass',
                "class": 'class {name}:\n    """{docstring}"""\n    \n    def __init__(self{params}):\n        pass',
                "module": '"""Module docstring"""\n\nimport logging\n\nlogger = logging.getLogger(__name__)\n\n',
            },
            "javascript": {
                "function": 'function {name}({params}) {{\n  // {docstring}\n}}',
                "class": 'class {name} {{\n  constructor({params}) {{\n    // {docstring}\n  }}\n}}',
                "module": "// Module docstring\n\n",
            },
        }
        
        return {
            "prompt": prompt,
            "language": language,
            "style": style,
            "templates": templates.get(language, templates["python"]),
            "best_practices": [
                "添加类型注解" if language == "python" else "使用TypeScript类型",
                "编写文档字符串",
                "处理边界情况",
                "添加错误处理",
                "遵循命名规范",
            ],
        }
    
    def review_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """代码审查"""
        analysis = self.analyze_code(code, language)
        
        review_points = []
        if analysis["issues"]:
            review_points.extend([
                f"[{iss['type'].upper()}] 行{iss['line']}: {iss['message']}"
                for iss in analysis["issues"]
            ])
        
        if analysis["comment_lines"] / max(analysis["code_lines"], 1) < 0.1:
            review_points.append("[DOCUMENTATION] 注释比例过低，建议增加文档注释")
        
        if analysis["blank_lines"] / max(analysis["total_lines"], 1) < 0.1:
            review_points.append("[STYLE] 空行过少，代码可读性差")
        
        return {
            "score": max(0, 10 - len(review_points)),
            "issues": len(review_points),
            "points": review_points,
            "summary": f"代码评分: {max(0, 10 - len(review_points))}/10, 发现 {len(review_points)} 个问题",
        }
    
    def refactor_suggest(self, code: str, language: str = "python") -> Dict[str, Any]:
        """重构建议"""
        suggestions = []
        
        # 检测可重构模式
        lines = code.split('\n')
        
        # 检测重复代码
        line_counts = {}
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        for line, count in line_counts.items():
            if count > 2:
                suggestions.append({
                    "type": "duplication",
                    "message": f"重复代码(出现{count}次): {line[:50]}",
                    "suggestion": "提取为独立函数或常量",
                })
        
        # 检测过长函数
        indent_level = 0
        func_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') or line.strip().startswith('function '):
                if func_start and i - func_start > 50:
                    suggestions.append({
                        "type": "long_function",
                        "message": f"函数过长(行{func_start}-{i})",
                        "suggestion": "拆分为多个小函数",
                    })
                func_start = i
        
        return {
            "suggestions": suggestions,
            "priority": "high" if len(suggestions) > 3 else "medium" if suggestions else "low",
        }
