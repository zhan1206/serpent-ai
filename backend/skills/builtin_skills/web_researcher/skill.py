# -*- coding: utf-8 -*-
"""
网络研究技能 - 信息搜索、摘要和事实核查
"""

import logging
from typing import Dict, List, Any, Optional
from ..skill import Skill, SkillManifest

logger = logging.getLogger(__name__)


class WebResearcherSkill(Skill):
    """网络研究技能"""
    
    def __init__(self):
        manifest = SkillManifest(
            name="web_researcher",
            version="1.0.0",
            display_name="网络研究员",
            description="信息搜索、内容摘要、事实核查和多源整合",
            author="SerpentAI",
            category="research",
            tags=["search", "research", "fact-check", "summarize"],
            tools=["web_search", "web_scrape", "summarize", "fact_check", "compare_sources"],
            prompt_template="""你是一个专业的网络研究员。你的职责是：
1. 搜索和收集相关信息
2. 评估信息源的可靠性
3. 摘要和整合多源信息
4. 核查事实和数据
5. 生成研究报告

研究主题: {topic}
深度要求: {depth}
语言: {language}""",
            examples=[
                {
                    "input": "研究量子计算的最新进展",
                    "output": "量子计算领域在2025年有以下重大进展...",
                },
            ],
        )
        super().__init__(manifest, skill_dir="skills/builtin_skills/web_researcher")
    
    def evaluate_source(self, url: str, content: str) -> Dict[str, Any]:
        """评估信息源可靠性"""
        score = 5  # 基准分5/10
        signals = []
        
        # 域名可信度
        trusted_domains = [
            ".edu", ".gov", ".org", "wikipedia.org", "nature.com",
            "science.org", "arxiv.org", "github.com",
        ]
        suspicious_domains = [".biz", ".click", ".top", ".xyz"]
        
        for domain in trusted_domains:
            if domain in url:
                score += 2
                signals.append(f"可信域名: {domain}")
                break
        
        for domain in suspicious_domains:
            if domain in url:
                score -= 2
                signals.append(f"可疑域名: {domain}")
                break
        
        # 内容质量信号
        if len(content) > 500:
            score += 1
            signals.append("内容详实")
        
        if any(marker in content for marker in ["参考文献", "Sources", "Citation", "DOI"]):
            score += 1
            signals.append("含引用/参考文献")
        
        # 红旗信号
        red_flags = [
            "惊人", "震惊", "你不会相信", "secret", "shocking",
            "点击查看", "click here", "广告", "sponsored",
        ]
        for flag in red_flags:
            if flag.lower() in content.lower():
                score -= 1
                signals.append(f"红旗信号: {flag}")
        
        # 日期信息
        import re
        year_matches = re.findall(r'\b(20[2][0-9])\b', content)
        if year_matches:
            latest_year = max(int(y) for y in year_matches)
            if latest_year >= 2025:
                score += 1
                signals.append(f"内容较新: {latest_year}年")
        
        return {
            "url": url,
            "reliability_score": min(10, max(1, score)),
            "level": "high" if score >= 7 else "medium" if score >= 4 else "low",
            "signals": signals,
        }
    
    def summarize_content(self, content: str, max_length: int = 500) -> Dict[str, Any]:
        """摘要内容"""
        sentences = []
        for line in content.replace('。', '。\n').replace('. ', '.\n').split('\n'):
            line = line.strip()
            if line and len(line) > 10:
                sentences.append(line)
        
        if not sentences:
            return {"summary": "", "key_points": [], "original_length": len(content)}
        
        # 提取关键句（基于位置和长度）
        key_points = []
        if sentences:
            key_points.append(sentences[0])  # 首句
        if len(sentences) > 2:
            key_points.append(sentences[-1])  # 末句
        
        # 提取含关键词的句子
        importance_keywords = [
            "重要", "关键", "发现", "结论", "significant", "important",
            "key", "finding", "conclusion", "result", "shows",
        ]
        for s in sentences[1:-1]:
            if any(kw in s.lower() for kw in importance_keywords):
                key_points.append(s)
        
        summary = " ".join(key_points[:5])
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return {
            "summary": summary,
            "key_points": key_points[:8],
            "original_length": len(content),
            "summary_length": len(summary),
            "sentence_count": len(sentences),
        }
    
    def fact_check(self, claim: str, sources: List[Dict[str, str]]) -> Dict[str, Any]:
        """事实核查"""
        results = []
        supporting = 0
        contradicting = 0
        neutral = 0
        
        claim_lower = claim.lower()
        claim_keywords = set(claim_lower.split())
        
        for source in sources:
            content = source.get("content", "").lower()
            url = source.get("url", "unknown")
            
            # 关键词匹配度
            content_words = set(content.split())
            overlap = claim_keywords & content_words
            overlap_ratio = len(overlap) / max(len(claim_keywords), 1)
            
            if overlap_ratio > 0.5:
                supporting += 1
                verdict = "supporting"
            elif overlap_ratio > 0.2:
                neutral += 1
                verdict = "neutral"
            else:
                contradicting += 1
                verdict = "insufficient_evidence"
            
            source_eval = self.evaluate_source(url, source.get("content", ""))
            results.append({
                "url": url,
                "verdict": verdict,
                "keyword_overlap": round(overlap_ratio, 2),
                "reliability": source_eval["level"],
            })
        
        total = max(len(sources), 1)
        if supporting / total > 0.5:
            overall = "likely_true"
        elif contradicting / total > 0.5:
            overall = "likely_false"
        else:
            overall = "unverified"
        
        return {
            "claim": claim,
            "overall_verdict": overall,
            "confidence": round(supporting / total, 2),
            "sources_checked": len(sources),
            "supporting": supporting,
            "contradicting": contradicting,
            "neutral": neutral,
            "details": results,
        }
    
    def compare_sources(self, sources: List[Dict[str, str]]) -> Dict[str, Any]:
        """多源对比"""
        comparisons = []
        all_key_points = []
        
        for source in sources:
            summary = self.summarize_content(source.get("content", ""))
            evaluation = self.evaluate_source(source.get("url", ""), source.get("content", ""))
            all_key_points.extend(summary["key_points"])
            comparisons.append({
                "url": source.get("url", "unknown"),
                "reliability": evaluation["level"],
                "score": evaluation["reliability_score"],
                "summary": summary["summary"],
                "key_points": summary["key_points"],
            })
        
        # 去重关键点
        unique_points = list(dict.fromkeys(all_key_points))
        
        return {
            "source_count": len(sources),
            "comparisons": comparisons,
            "consensus_points": unique_points[:10],
            "best_source": max(comparisons, key=lambda x: x["score"]) if comparisons else None,
        }
