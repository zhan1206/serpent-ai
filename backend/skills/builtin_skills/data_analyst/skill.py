# -*- coding: utf-8 -*-
"""
数据分析技能 - 数据处理、统计分析和可视化建议
"""

import logging
from typing import Dict, List, Any, Optional
from ..skill import Skill, SkillManifest

logger = logging.getLogger(__name__)


class DataAnalystSkill(Skill):
    """数据分析技能"""
    
    def __init__(self):
        manifest = SkillManifest(
            name="data_analyst",
            version="1.0.0",
            display_name="数据分析师",
            description="数据处理、统计分析、可视化建议和报告生成",
            author="SerpentAI",
            category="data",
            tags=["data", "analytics", "statistics", "visualization"],
            tools=["data_load", "data_clean", "data_analyze", "data_visualize", "data_report"],
            prompt_template="""你是一个专业的数据分析师。你的职责是：
1. 加载和预处理数据
2. 执行统计分析
3. 发现数据中的模式和趋势
4. 生成可视化建议
5. 撰写分析报告

数据源: {data_source}
分析目标: {objective}
输出格式: {output_format}""",
            examples=[
                {
                    "input": "分析这组销售数据的趋势",
                    "output": "根据数据分析，销售额呈现上升趋势..."
                },
            ],
        )
        super().__init__(manifest, skill_dir="skills/builtin_skills/data_analyst")
    
    def analyze_data(self, data: List[Any], columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """基础数据分析"""
        if not data:
            return {"error": "数据为空"}
        
        # 数值型数据分析
        numeric_data = []
        for item in data:
            if isinstance(item, (int, float)):
                numeric_data.append(item)
            elif isinstance(item, dict) and columns:
                for col in columns:
                    val = item.get(col)
                    if isinstance(val, (int, float)):
                        numeric_data.append(val)
        
        result = {
            "total_records": len(data),
            "columns": columns or [],
        }
        
        if numeric_data:
            sorted_data = sorted(numeric_data)
            n = len(sorted_data)
            result["statistics"] = {
                "count": n,
                "sum": sum(sorted_data),
                "mean": sum(sorted_data) / n,
                "min": sorted_data[0],
                "max": sorted_data[-1],
                "median": sorted_data[n // 2] if n % 2 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2,
                "range": sorted_data[-1] - sorted_data[0],
                "std_dev": (sum((x - sum(sorted_data) / n) ** 2 for x in sorted_data) / n) ** 0.5 if n > 1 else 0,
            }
            # 四分位数
            q1_idx = n // 4
            q3_idx = 3 * n // 4
            result["statistics"]["q1"] = sorted_data[q1_idx]
            result["statistics"]["q3"] = sorted_data[q3_idx]
            result["statistics"]["iqr"] = sorted_data[q3_idx] - sorted_data[q1_idx]
        
        return result
    
    def suggest_visualization(self, data_type: str, purpose: str) -> Dict[str, Any]:
        """可视化建议"""
        visualization_map = {
            "comparison": {
                "bar": "柱状图 - 适合分类数据对比",
                "grouped_bar": "分组柱状图 - 适合多组对比",
                "radar": "雷达图 - 适合多维度对比",
            },
            "trend": {
                "line": "折线图 - 适合展示趋势变化",
                "area": "面积图 - 适合展示累计趋势",
                "scatter": "散点图 - 适合展示相关性",
            },
            "distribution": {
                "histogram": "直方图 - 适合展示数据分布",
                "box": "箱线图 - 适合展示离群值",
                "violin": "小提琴图 - 适合展示密度分布",
            },
            "composition": {
                "pie": "饼图 - 适合展示占比",
                "donut": "环形图 - 适合展示占比(更美观)",
                "treemap": "树图 - 适合层次结构占比",
                "stacked_bar": "堆叠柱状图 - 适合组成对比",
            },
            "relationship": {
                "scatter": "散点图 - 适合展示相关性",
                "heatmap": "热力图 - 适合展示矩阵关系",
                "bubble": "气泡图 - 适合三维关系展示",
            },
        }
        
        suggestions = visualization_map.get(data_type, visualization_map["comparison"])
        
        return {
            "data_type": data_type,
            "purpose": purpose,
            "recommended": list(suggestions.keys())[0],
            "options": suggestions,
            "libraries": {
                "python": ["matplotlib", "seaborn", "plotly"],
                "javascript": ["d3.js", "echarts", "chart.js"],
            },
        }
    
    def clean_data(self, data: List[Dict], rules: Optional[Dict] = None) -> Dict[str, Any]:
        """数据清洗"""
        rules = rules or {}
        cleaned = []
        removed = 0
        modified = 0
        
        for record in data:
            skip = False
            
            # 去除空值记录
            if rules.get("drop_null"):
                if any(v is None or v == "" for v in record.values()):
                    removed += 1
                    skip = True
            
            # 去除重复记录
            if rules.get("drop_duplicates") and not skip:
                if record in cleaned:
                    removed += 1
                    skip = True
            
            if not skip:
                new_record = {}
                for key, value in record.items():
                    # 字符串去空格
                    if isinstance(value, str) and rules.get("trim_strings", True):
                        new_value = value.strip()
                        if new_value != value:
                            modified += 1
                        new_record[key] = new_value
                    else:
                        new_record[key] = value
                cleaned.append(new_record)
        
        return {
            "original_count": len(data),
            "cleaned_count": len(cleaned),
            "removed": removed,
            "modified": modified,
            "sample": cleaned[:5],
        }
    
    def generate_report(self, analysis: Dict, format: str = "markdown") -> str:
        """生成分析报告"""
        if format == "markdown":
            lines = ["# 数据分析报告\n"]
            
            if "total_records" in analysis:
                lines.append(f"## 概览\n")
                lines.append(f"- 总记录数: {analysis['total_records']}")
                if "columns" in analysis:
                    lines.append(f"- 字段: {', '.join(analysis['columns'])}")
                lines.append("")
            
            if "statistics" in analysis:
                stats = analysis["statistics"]
                lines.append("## 统计摘要\n")
                lines.append(f"| 指标 | 值 |")
                lines.append(f"|------|------|")
                for key, val in stats.items():
                    lines.append(f"| {key} | {val:.4f} |" if isinstance(val, float) else f"| {key} | {val} |")
            
            return "\n".join(lines)
        
        return str(analysis)
