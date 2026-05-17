"""
SerpentAI 安全模块 - 输入守卫 (Layer 1)
防止注入攻击、XSS、恶意输入
"""

import re
import html
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    sanitized_data: Dict[str, Any] = field(default_factory=dict)
    threat_detected: List[str] = field(default_factory=list)
    
    def add_error(self, field_name: str, error: str):
        self.is_valid = False
        self.errors.append(f"{field_name}: {error}")
    
    def add_threat(self, threat: str):
        self.threat_detected.append(threat)


class InputGuard:
    """
    输入守卫 - 第一层防御
    功能：
    1. SQL注入检测
    2. XSS检测
    3. 命令注入检测
    4. 路径遍历检测
    5. Prompt注入检测
    6. 数据验证和清理
    """
    
    # 危险模式
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|\#|/\*|\*/)",
        r"('|\"|;|\\)",
        r"(OR\s+1\s*=\s*1|AND\s+1\s*=\s*1)",
        r"(UNION\s+SELECT)",
        r"(INTO\s+OUTFILE|INTO\s+DUMPFILE)",
    ]
    
    XSS_PATTERNS = [
        r"(<script|</script>)",
        r"(javascript:)",
        r"(on\w+\s*=)",  # onclick, onerror, etc.
        r"(<iframe|<object|<embed)",
        r"(expression\s*\()",  # CSS expression
        r"(data:text/html)",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"([;&|`$])",
        r"(\b(cat|ls|dir|rm|wget|curl|nc|bash|sh|python|node)\b)",
        r"(\b(echo|cat|head|tail)\s+.*(/etc|/var))",
        r"(\|\s*\w+)",
        r"(\$\()",
        r"(\{\{.*\}\})",  # Template injection
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\./)",
        r"(\.\.\\)",
        r"(/etc/passwd|/etc/shadow)",
        r"(C:\\Windows|C:\\Program Files)",
        r"(%2e%2e)",
    ]
    
    PROMPT_INJECTION_PATTERNS = [
        r"(ignore\s+(previous|above|all)\s+(instructions|commands))",
        r"(forget\s+everything)",
        r"(you\s+are\s+now\s+)",
        r"(pretend\s+you\s+are)",
        r"(disregard\s+(your|safety))",
        r"(reveal\s+(your|system))",
        r"(new\s+system\s+prompt)",
        r"(#\s*system|#\s*instructions)",
        r"(\[INST\]|\[/INST\])",
    ]
    
    def __init__(self):
        self.blocked_domains: Set[str] = set()
        self.max_string_length = 100000
        self.max_depth = 10
        self.whitelist_patterns: List[re.Pattern] = []
        
        # 编译正则表达式
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.cmd_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_INJECTION_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
        self.prompt_patterns = [re.compile(p, re.IGNORECASE) for p in self.PROMPT_INJECTION_PATTERNS]
    
    def validate_all(self, data: Dict[str, Any]) -> ValidationResult:
        """
        对所有输入数据进行完整验证
        
        Args:
            data: 输入数据字典
        
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult()
        
        try:
            self._validate_recursive(data, result, path="root")
        except RecursionError:
            result.add_error("depth", "数据嵌套深度超出限制")
        except Exception as e:
            result.add_error("validation", f"验证过程出错: {e}")
        
        return result
    
    def _validate_recursive(self, data: Any, result: ValidationResult, path: str, depth: int = 0):
        """递归验证数据"""
        if depth > self.max_depth:
            result.add_error(path, f"嵌套深度超出限制 ({self.max_depth})")
            return
        
        if data is None:
            return
        
        if isinstance(data, str):
            self._validate_string(data, result, path)
        
        elif isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}" if path != "root" else key
                
                # 检查键名
                if self._contains_malicious(key):
                    result.add_threat(f"恶意键名: {key}")
                    result.add_error(new_path, "键名包含危险字符")
                
                self._validate_recursive(value, result, new_path, depth + 1)
        
        elif isinstance(data, (list, tuple)):
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]"
                self._validate_recursive(item, result, new_path, depth + 1)
    
    def _validate_string(self, text: str, result: ValidationResult, path: str):
        """验证字符串输入"""
        if not isinstance(text, str):
            return
        
        # 检查长度
        if len(text) > self.max_string_length:
            result.add_error(path, f"字符串长度超出限制 ({len(text)} > {self.max_string_length})")
            return
        
        # SQL注入检测
        for i, pattern in enumerate(self.sql_patterns):
            if pattern.search(text):
                result.add_threat(f"SQL注入风险 (pattern #{i})")
                result.add_error(path, "检测到SQL注入风险")
        
        # XSS检测
        for i, pattern in enumerate(self.xss_patterns):
            if pattern.search(text):
                result.add_threat(f"XSS风险 (pattern #{i})")
                result.add_error(path, "检测到XSS风险")
        
        # 命令注入检测
        for i, pattern in enumerate(self.cmd_patterns):
            if pattern.search(text):
                result.add_threat(f"命令注入风险 (pattern #{i})")
                result.add_error(path, "检测到命令注入风险")
        
        # 路径遍历检测
        for i, pattern in enumerate(self.path_patterns):
            if pattern.search(text):
                result.add_threat(f"路径遍历风险 (pattern #{i})")
                result.add_error(path, "检测到路径遍历风险")
        
        # Prompt注入检测
        for i, pattern in enumerate(self.prompt_patterns):
            if pattern.search(text):
                result.add_threat(f"Prompt注入风险 (pattern #{i})")
                result.add_error(path, "检测到Prompt注入风险")
    
    def _contains_malicious(self, text: str) -> bool:
        """检查是否包含恶意内容"""
        for pattern in self.sql_patterns + self.xss_patterns + self.cmd_patterns:
            if pattern.search(text):
                return True
        return False
    
    def sanitize_html(self, text: str) -> str:
        """
        HTML转义，防止XSS
        
        Args:
            text: 原始文本
        
        Returns:
            str: 转义后的文本
        """
        return html.escape(text)
    
    def sanitize_sql(self, text: str) -> str:
        """
        SQL清理，移除危险字符
        
        Args:
            text: 原始文本
        
        Returns:
            str: 清理后的文本
        """
        # 移除单引号（可能导致注入）
        sanitized = text.replace("'", "''")
        # 移除分号（语句分隔）
        sanitized = sanitized.replace(";", "")
        # 移除注释
        sanitized = re.sub(r"(--|#|/\*|\*/)", "", sanitized)
        return sanitized
    
    def validate_json(self, json_str: str) -> ValidationResult:
        """
        验证JSON字符串
        
        Args:
            json_str: JSON字符串
        
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult()
        
        try:
            data = json.loads(json_str)
            self._validate_recursive(data, result, "json")
        except json.JSONDecodeError as e:
            result.add_error("json", f"JSON格式错误: {e}")
        
        return result
    
    def validate_file_path(self, path: str) -> ValidationResult:
        """
        验证文件路径
        
        Args:
            path: 文件路径
        
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult()
        
        # 检查路径遍历
        for pattern in self.path_patterns:
            if pattern.search(path):
                result.add_threat("路径遍历")
                result.add_error("path", "检测到路径遍历攻击")
        
        # 检查是否是绝对路径
        if not path.startswith("/") and not path.startswith("."):
            # 允许相对路径和绝对路径
            pass
        
        return result
    
    def validate_url(self, url: str) -> ValidationResult:
        """
        验证URL
        
        Args:
            url: URL字符串
        
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult()
        
        # 检查是否是危险协议
        dangerous_protocols = ["javascript:", "data:", "vbscript:", "file:"]
        for protocol in dangerous_protocols:
            if url.lower().startswith(protocol):
                result.add_threat(f"危险协议: {protocol}")
                result.add_error("url", f"不允许的协议: {protocol}")
        
        # 检查域名是否在黑名单
        for domain in self.blocked_domains:
            if domain in url:
                result.add_threat(f"被阻止的域名: {domain}")
                result.add_error("url", f"域名被阻止: {domain}")
        
        return result
    
    def add_blocked_domain(self, domain: str):
        """添加阻止的域名"""
        self.blocked_domains.add(domain)
    
    def remove_blocked_domain(self, domain: str):
        """移除阻止的域名"""
        self.blocked_domains.discard(domain)
