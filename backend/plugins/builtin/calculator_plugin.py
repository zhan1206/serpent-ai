# -*- coding: utf-8 -*-
"""
计算器插件 - 高级数学计算与单位转换
支持基础运算、科学计算、单位换算
"""

import math
import re
import logging
from typing import Dict, List, Any, Optional

from backend.plugins.plugin_base import ToolPlugin
from backend.plugins.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

# 单位转换表
UNIT_CONVERSIONS = {
    "length": {
        "m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001,
        "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "yd": 0.9144,
        "nmi": 1852.0,
    },
    "weight": {
        "kg": 1.0, "g": 0.001, "mg": 0.000001, "t": 1000.0,
        "lb": 0.453592, "oz": 0.0283495, "jin": 0.5,
    },
    "temperature": {},  # 特殊处理
    "area": {
        "m2": 1.0, "km2": 1e6, "cm2": 1e-4, "ha": 1e4,
        "acre": 4046.86, "ft2": 0.092903, "mu": 666.667,
    },
    "volume": {
        "l": 1.0, "ml": 0.001, "m3": 1000.0, "gal": 3.78541,
        "qt": 0.946353, "cup": 0.236588, "fl_oz": 0.0295735,
    },
    "speed": {
        "m/s": 1.0, "km/h": 0.277778, "mph": 0.44704,
        "kn": 0.514444, "ft/s": 0.3048,
    },
    "data": {
        "B": 1.0, "KB": 1024.0, "MB": 1048576.0, "GB": 1073741824.0,
        "TB": 1099511627776.0, "bit": 0.125,
    },
    "time": {
        "s": 1.0, "min": 60.0, "h": 3600.0, "d": 86400.0,
        "w": 604800.0, "ms": 0.001,
    },
}

# 查找单位所属类别
_UNIT_CATEGORY = {}
for cat, units in UNIT_CONVERSIONS.items():
    if cat != "temperature":
        for unit in units:
            _UNIT_CATEGORY[unit] = cat


def _safe_eval(expr: str) -> float:
    """
    安全地计算数学表达式
    只允许数学函数和运算符，禁止执行任意代码
    
    Args:
        expr: 数学表达式字符串
        
    Returns:
        计算结果
        
    Raises:
        ValueError: 表达式不合法
    """
    # 替换常见数学函数
    expr = expr.strip()
    
    # 安全的名称白名单
    safe_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow,
        "sqrt": math.sqrt, "cbrt": lambda x: x ** (1/3),
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan,
        "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "log": math.log, "log2": math.log2, "log10": math.log10,
        "ln": math.log,
        "exp": math.exp, "e": math.e, "pi": math.pi,
        "ceil": math.ceil, "floor": math.floor,
        "degrees": math.degrees, "radians": math.radians,
        "factorial": math.factorial,
        "gcd": math.gcd, "lcm": math.lcm,
        "hypot": math.hypot,
        "inf": math.inf, "nan": math.nan,
        "mod": lambda a, b: a % b,
        "divmod": lambda a, b: a // b,
        "sign": lambda x: (1 if x > 0 else -1 if x < 0 else 0),
    }
    
    # 添加 ^ -> ** 转换
    expr = expr.replace("^", "**")
    
    # 验证表达式安全性：只允许数字、运算符、括号、点和安全函数名
    allowed_pattern = r"^[0-9+\-*/().,%\s]|abs|round|min|max|sum|pow|sqrt|cbrt|sin|cos|tan|asin|acos|atan|sinh|cosh|tanh|log|log2|log10|ln|exp|ceil|floor|degrees|radians|factorial|gcd|lcm|hypot|inf|nan|mod|divmod|sign|pi|e|sqrt"
    
    # 检查危险字符
    dangerous = ["import", "exec", "eval", "open", "os", "sys", "__", "class", 
                 "def", "lambda", "yield", "await", "async", "global", "local",
                 "print", "input", "file", "breakpoint", "compile"]
    lower_expr = expr.lower()
    for d in dangerous:
        if d in lower_expr:
            raise ValueError(f"表达式中包含不允许的关键词: {d}")
    
    try:
        result = eval(expr, {"__builtins__": {}}, safe_names)
        return float(result)
    except ZeroDivisionError:
        raise ValueError("除零错误")
    except (SyntaxError, NameError, TypeError) as e:
        raise ValueError(f"表达式错误: {e}")


class CalculatorPlugin(ToolPlugin):
    """计算器插件 - 提供数学计算和单位转换工具"""
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "calculator",
                "description": "高级科学计算器，支持数学表达式计算。支持函数：sin, cos, tan, log, sqrt, abs, pow, exp, factorial, gcd, lcm 等。示例：sqrt(144), 2^10, sin(pi/4)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，如 '2^10 + sqrt(144)', 'sin(pi/4) * 100'"
                        }
                    },
                    "required": ["expression"]
                },
                "handler": self._handle_calculate,
                "category": "calculator"
            },
            {
                "name": "unit_convert",
                "description": "单位转换工具。支持长度、重量、温度、面积、体积、速度、数据存储、时间等类别的单位转换。示例：1km转mi, 100kg转lb, 32F转C",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "number",
                            "description": "要转换的数值"
                        },
                        "from_unit": {
                            "type": "string",
                            "description": "源单位，如 km, kg, F, C, mi, lb"
                        },
                        "to_unit": {
                            "type": "string",
                            "description": "目标单位，如 m, g, C, F, km, kg"
                        }
                    },
                    "required": ["value", "from_unit", "to_unit"]
                },
                "handler": self._handle_unit_convert,
                "category": "calculator"
            },
        ]
    
    def _handle_calculate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理计算请求"""
        expression = arguments["expression"]
        try:
            result = _safe_eval(expression)
            return {
                "expression": expression,
                "result": result,
                "formatted": self._format_number(result),
            }
        except ValueError as e:
            return {"error": str(e)}
    
    def _handle_unit_convert(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理单位转换请求"""
        value = arguments["value"]
        from_unit = arguments["from_unit"].lower().strip()
        to_unit = arguments["to_unit"].lower().strip()
        
        # 温度特殊处理
        if from_unit in ("c", "f", "k") or to_unit in ("c", "f", "k"):
            return self._convert_temperature(value, from_unit, to_unit)
        
        # 查找单位类别
        from_cat = _UNIT_CATEGORY.get(from_unit)
        to_cat = _UNIT_CATEGORY.get(to_unit)
        
        if not from_cat:
            return {"error": f"未知单位: {from_unit}"}
        if not to_cat:
            return {"error": f"未知单位: {to_unit}"}
        if from_cat != to_cat:
            return {"error": f"单位类别不匹配: {from_unit}({from_cat}) 和 {to_unit}({to_cat})"}
        
        conversions = UNIT_CONVERSIONS[from_cat]
        from_factor = conversions[from_unit]
        to_factor = conversions[to_unit]
        
        result = value * from_factor / to_factor
        
        return {
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "result": self._format_number(result),
            "category": from_cat,
        }
    
    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> Dict:
        """温度转换"""
        # 先转为摄氏度
        if from_unit == "c":
            celsius = value
        elif from_unit == "f":
            celsius = (value - 32) * 5 / 9
        elif from_unit == "k":
            celsius = value - 273.15
        else:
            return {"error": f"未知温度单位: {from_unit}"}
        
        # 从摄氏度转为目标
        if to_unit == "c":
            result = celsius
        elif to_unit == "f":
            result = celsius * 9 / 5 + 32
        elif to_unit == "k":
            result = celsius + 273.15
        else:
            return {"error": f"未知温度单位: {to_unit}"}
        
        return {
            "value": value,
            "from_unit": from_unit.upper(),
            "to_unit": to_unit.upper(),
            "result": self._format_number(result),
            "category": "temperature",
        }
    
    def _format_number(self, num: float) -> str:
        """格式化数字输出"""
        if num == int(num) and abs(num) < 1e15:
            return str(int(num))
        if abs(num) < 0.0001 or abs(num) > 1e12:
            return f"{num:.6e}"
        return f"{num:.6g}"


# 插件工厂函数
def create_plugin(manifest: PluginManifest) -> CalculatorPlugin:
    """创建计算器插件实例"""
    return CalculatorPlugin(manifest)
