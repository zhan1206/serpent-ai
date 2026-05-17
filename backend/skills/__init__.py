# -*- coding: utf-8 -*-
"""
SerpentAI 技能商店系统
技能 = 工具集合 + 提示词模板 + 示例用法
支持安装、搜索、评分和分享
"""

from .skill import Skill, SkillManifest
from .skill_store import SkillStore, get_skill_store
from .skill_installer import SkillInstaller

__all__ = [
    "Skill", "SkillManifest",
    "SkillStore", "get_skill_store",
    "SkillInstaller",
]
