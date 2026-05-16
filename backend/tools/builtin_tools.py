"""
Builtin Tools - SerpentAI内置工具
提供1000+常用工具的示例实现
"""

import os
import json
import time
import datetime
import math
import random
import string
import hashlib
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def register_all_builtin_tools():
    """
    注册所有内置工具
    在实际部署时，这个函数会注册1000+工具
    """
    from .tool_registry import register_builtin_tool
    
    # 基础工具
    register_builtin_tool({
        "name": "get_current_time",
        "description": "Get current date and time",
        "category": "system",
        "handler": get_current_time
    })
    
    register_builtin_tool({
        "name": "calculate",
        "description": "Perform mathematical calculations. Supports basic arithmetic, trigonometry, logarithms, etc.",
        "category": "math",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        },
        "handler": calculate
    })
    
    register_builtin_tool({
        "name": "hash_text",
        "description": "Calculate hash of text using various algorithms (MD5, SHA1, SHA256, SHA512)",
        "category": "crypto",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "algorithm": {"type": "string", "enum": ["md5", "sha1", "sha256", "sha512"]}
            },
            "required": ["text", "algorithm"]
        },
        "handler": hash_text
    })
    
    register_builtin_tool({
        "name": "generate_password",
        "description": "Generate a random password with customizable length and character sets",
        "category": "security",
        "inputSchema": {
            "type": "object",
            "properties": {
                "length": {"type": "integer", "minimum": 8, "maximum": 128},
                "include_symbols": {"type": "boolean"},
                "include_numbers": {"type": "boolean"}
            },
            "required": ["length"]
        },
        "handler": generate_password
    })
    
    register_builtin_tool({
        "name": "json_format",
        "description": "Format JSON string with indentation",
        "category": "formatting",
        "inputSchema": {
            "type": "object",
            "properties": {
                "json_str": {"type": "string"},
                "indent": {"type": "integer"}
            },
            "required": ["json_str"]
        },
        "handler": json_format
    })
    
    logger.info("Registered 5 builtin tools (demo)")


# 工具处理函数
def get_current_time(args: Dict) -> Dict:
    """
    获取当前时间
    """
    now = datetime.datetime.now()
    return {
        "timestamp": int(now.timestamp()),
        "iso_format": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": "local"
    }


def calculate(args: Dict) -> Any:
    """
    执行数学计算
    安全限制：不允许使用__import__、eval、exec等危险函数
    """
    expression = args.get("expression", "")
    
    # 安全检查：禁止危险函数
    dangerous_keywords = ["__import__", "eval", "exec", "open", "os.", "sys."]
    for keyword in dangerous_keywords:
        if keyword in expression:
            raise ValueError(f"Dangerous keyword not allowed: {keyword}")
    
    # 允许的数学函数
    allowed_globals = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "len": len,
        # 数学函数
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "sqrt": math.sqrt,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "ceil": math.ceil,
        "floor": math.floor,
        "pi": math.pi,
        "e": math.e
    }
    
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_globals)
        return {"result": result}
    except Exception as e:
        raise ValueError(f"Calculation error: {str(e)}")


def hash_text(args: Dict) -> Dict:
    """
    计算文本哈希
    """
    text = args.get("text", "")
    algorithm = args.get("algorithm", "sha256")
    
    text_bytes = text.encode("utf-8")
    
    if algorithm == "md5":
        hash_obj = hashlib.md5(text_bytes)
    elif algorithm == "sha1":
        hash_obj = hashlib.sha1(text_bytes)
    elif algorithm == "sha256":
        hash_obj = hashlib.sha256(text_bytes)
    elif algorithm == "sha512":
        hash_obj = hashlib.sha512(text_bytes)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    return {
        "text": text,
        "algorithm": algorithm,
        "hash": hash_obj.hexdigest()
    }


def generate_password(args: Dict) -> Dict:
    """
    生成随机密码
    """
    length = args.get("length", 16)
    include_symbols = args.get("include_symbols", True)
    include_numbers = args.get("include_numbers", True)
    
    # 构建字符集
    chars = string.ascii_letters  # a-z, A-Z
    
    if include_numbers:
        chars += string.digits  # 0-9
    
    if include_symbols:
        chars += string.punctuation  # !@#$%^&*()...
    
    # 生成密码
    password = ''.join(random.choice(chars) for _ in range(length))
    
    return {
        "password": password,
        "length": length,
        "includes_symbols": include_symbols,
        "includes_numbers": include_numbers
    }


def json_format(args: Dict) -> Dict:
    """
    格式化JSON字符串
    """
    json_str = args.get("json_str", "")
    indent = args.get("indent", 2)
    
    try:
        data = json.loads(json_str)
        formatted = json.dumps(data, indent=indent, ensure_ascii=False)
        return {
            "formatted": formatted,
            "valid": True
        }
    except json.JSONDecodeError as e:
        return {
            "error": str(e),
            "valid": False
        }


# 示例：如何添加新的内置工具
if __name__ == "__main__":
    # 注册所有内置工具
    register_all_builtin_tools()
    
    # 测试工具
    from .tool_registry import list_tools, call_tool
    
    # 列出所有工具
    tools = list_tools()
    print(f"Registered {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
    
    # 测试调用工具
    result = call_tool("get_current_time", {})
    print(f"\nCurrent time: {result}")
    
    result = call_tool("calculate", {"expression": "2 + 2 * 3"})
    print(f"Calculate: 2 + 2 * 3 = {result['result']}")
    
    result = call_tool("hash_text", {"text": "Hello SerpentAI", "algorithm": "sha256"})
    print(f"Hash: {result['hash']}")
