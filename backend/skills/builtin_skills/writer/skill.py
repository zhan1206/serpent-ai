# -*- coding: utf-8 -*-
"""
写作技能 - 内容创作、编辑、翻译和风格调整
"""

import logging
from typing import Dict, List, Any, Optional
from ..skill import Skill, SkillManifest

logger = logging.getLogger(__name__)


class WriterSkill(Skill):
    """写作技能"""
    
    def __init__(self):
        manifest = SkillManifest(
            name="writer",
            version="1.0.0",
            display_name="写作助手",
            description="内容创作、编辑润色、翻译和风格调整",
            author="SerpentAI",
            category="writing",
            tags=["writing", "editing", "translation", "content"],
            tools=["write_content", "edit_content", "translate", "adjust_style", "outline"],
            prompt_template="""你是一个专业的写作助手。你的职责是：
1. 根据要求创作内容
2. 编辑和润色文本
3. 调整写作风格和语气
4. 生成文章大纲
5. 多语言翻译

写作类型: {type}
目标读者: {audience}
风格: {style}
语言: {language}""",
            examples=[
                {
                    "input": "写一篇关于AI发展趋势的技术博客",
                    "output": "# AI发展趋势：2025年展望\n\n## 引言\n...",
                },
            ],
        )
        super().__init__(manifest, skill_dir="skills/builtin_skills/writer")
    
    def generate_outline(self, topic: str, sections: int = 5,
                         style: str = "article") -> Dict[str, Any]:
        """生成文章大纲"""
        templates = {
            "article": [
                "引言/背景",
                "核心概念",
                "详细分析",
                "案例/实践",
                "总结与展望",
            ],
            "report": [
                "执行摘要",
                "研究方法",
                "发现与分析",
                "建议与结论",
                "附录",
            ],
            "blog": [
                "引人入胜的开头",
                "问题陈述",
                "解决方案",
                "实操步骤",
                "行动呼吁",
            ],
            "email": [
                "问候/开头",
                "核心信息",
                "行动项",
                "结尾/签名",
            ],
            "technical": [
                "概述/动机",
                "架构设计",
                "实现细节",
                "测试与评估",
                "相关工作与未来方向",
            ],
        }
        
        section_list = templates.get(style, templates["article"])[:sections]
        
        return {
            "topic": topic,
            "style": style,
            "sections": [
                {"number": i + 1, "title": sec, "description": f"{sec}部分"}
                for i, sec in enumerate(section_list)
            ],
            "estimated_words": sections * 300,
        }
    
    def edit_content(self, content: str, instructions: Optional[List[str]] = None) -> Dict[str, Any]:
        """编辑内容（基础分析）"""
        issues = []
        improved = content
        
        # 检查段落长度
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs):
            if len(para) > 500:
                issues.append({
                    "type": "paragraph_length",
                    "location": f"第{i+1}段",
                    "message": f"段落过长({len(para)}字)，建议拆分",
                })
        
        # 检查句子重复
        sentences = []
        for para in paragraphs:
            for s in para.replace('。', '。\n').replace('. ', '.\n').split('\n'):
                s = s.strip()
                if s:
                    sentences.append(s)
        
        seen = {}
        for s in sentences:
            s_lower = s.lower()
            if s_lower in seen:
                seen[s_lower] += 1
                if seen[s_lower] == 2:
                    issues.append({
                        "type": "repetition",
                        "location": s[:50],
                        "message": "重复句子",
                    })
            else:
                seen[s_lower] = 1
        
        # 检查被动语态过多
        passive_markers = ["被", "是...的", "was", "were", "been", "being"]
        passive_count = sum(1 for s in sentences if any(m in s for m in passive_markers))
        if passive_count > len(sentences) * 0.3:
            issues.append({
                "type": "passive_voice",
                "message": f"被动语态比例过高({passive_count}/{len(sentences)})",
            })
        
        # 应用编辑指令
        if instructions:
            for inst in instructions:
                issues.append({
                    "type": "user_instruction",
                    "message": inst,
                })
        
        return {
            "original_length": len(content),
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences),
            "issues": issues,
            "readability": self._assess_readability(content),
        }
    
    def _assess_readability(self, content: str) -> Dict[str, Any]:
        """评估可读性"""
        sentences = []
        for line in content.replace('。', '。\n').replace('. ', '.\n').split('\n'):
            line = line.strip()
            if line and len(line) > 5:
                sentences.append(line)
        
        if not sentences:
            return {"score": 0, "level": "unknown"}
        
        avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
        
        # 简化的可读性评分
        if avg_sentence_len < 20:
            level = "easy"
            score = 9
        elif avg_sentence_len < 35:
            level = "moderate"
            score = 7
        elif avg_sentence_len < 50:
            level = "difficult"
            score = 5
        else:
            level = "very_difficult"
            score = 3
        
        return {
            "score": score,
            "level": level,
            "avg_sentence_length": round(avg_sentence_len, 1),
            "recommendation": "建议缩短句子" if avg_sentence_len > 35 else "句子长度适中",
        }
    
    def adjust_style(self, content: str, target_style: str = "formal") -> Dict[str, Any]:
        """风格调整建议"""
        style_guides = {
            "formal": {
                "name": "正式",
                "rules": [
                    "避免缩写和口语表达",
                    "使用完整句子",
                    "保持客观语气",
                    "使用专业术语",
                ],
                "avoid": ["我觉得", "I think", "kinda", "gonna"],
            },
            "casual": {
                "name": "轻松",
                "rules": [
                    "可使用缩写",
                    "短句为主",
                    "可加入个人观点",
                    "口语化表达",
                ],
                "avoid": ["因此", "综上所述", "henceforth"],
            },
            "technical": {
                "name": "技术",
                "rules": [
                    "精确使用术语",
                    "代码/公式用标记格式",
                    "逻辑严密",
                    "引用来源",
                ],
                "avoid": ["大概", "maybe", "sort of"],
            },
            "creative": {
                "name": "创意",
                "rules": [
                    "使用比喻和修辞",
                    "多样化句式",
                    "情感丰富",
                    "避免刻板表述",
                ],
                "avoid": ["根据", "数据显示", "as shown"],
            },
        }
        
        guide = style_guides.get(target_style, style_guides["formal"])
        
        violations = []
        for avoid_word in guide.get("avoid", []):
            if avoid_word in content:
                violations.append(f"发现不符合风格的表达: '{avoid_word}'")
        
        return {
            "target_style": target_style,
            "guide": guide,
            "violations": violations,
            "compliance": "high" if not violations else "medium" if len(violations) < 3 else "low",
        }
    
    def translate_content(self, content: str, source_lang: str = "auto",
                          target_lang: str = "en") -> Dict[str, Any]:
        """翻译内容（提供框架，实际翻译由模型完成）"""
        return {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "content_length": len(content),
            "paragraph_count": len([p for p in content.split('\n\n') if p.strip()]),
            "note": "翻译由AI模型执行，此方法提供翻译框架和格式指导",
            "format_preserved": True,
        }
