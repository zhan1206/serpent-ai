# -*- coding: utf-8 -*-
"""
SerpentAI 内置技能
"""

from .web_researcher import WEB_RESEARCHER_SKILL
from .data_analyst import DATA_ANALYST_SKILL
from .code_assistant import CODE_ASSISTANT_SKILL
from .writer import WRITER_SKILL

BUILTIN_SKILLS = [
    WEB_RESEARCHER_SKILL,
    DATA_ANALYST_SKILL,
    CODE_ASSISTANT_SKILL,
    WRITER_SKILL,
]
