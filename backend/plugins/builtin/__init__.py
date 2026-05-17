# -*- coding: utf-8 -*-
"""
SerpentAI 内置插件
提供基础功能：计算器、网页搜索、代码执行、提醒、翻译
"""

from .calculator_plugin import CalculatorPlugin
from .web_search_plugin import WebSearchPlugin
from .code_executor_plugin import CodeExecutorPlugin
from .reminder_plugin import ReminderPlugin
from .translator_plugin import TranslatorPlugin

BUILTIN_PLUGINS = [
    CalculatorPlugin,
    WebSearchPlugin,
    CodeExecutorPlugin,
    ReminderPlugin,
    TranslatorPlugin,
]
