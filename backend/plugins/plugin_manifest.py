# -*- coding: utf-8 -*-
"""
插件清单 - plugin.json 解析与验证
管理插件的元数据、依赖、权限等信息
"""

import json
import os
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 语义化版本正则
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:[0-9A-Za-z-]+)(?:\.(?:[0-9A-Za-z-]+))*))?(?:\+([0-9A-Za-z-]+))?$")

# 插件类型枚举
PLUGIN_TYPES = {"tool", "model", "gateway", "hook", "general"}

# 支持的权限列表
SUPPORTED_PERMISSIONS = {
    "network": "网络访问（HTTP请求等）",
    "filesystem": "文件系统读写",
    "clipboard": "剪贴板访问",
    "notification": "发送系统通知",
    "database": "数据库访问",
    "shell": "执行系统命令",
    "camera": "摄像头访问",
    "microphone": "麦克风访问",
    "location": "位置信息",
    "contacts": "通讯录访问",
    "calendar": "日历访问",
}


@dataclass
class PluginManifest:
    """
    插件清单数据类
    对应插件目录中的 plugin.json 文件
    """
    name: str
    version: str
    description: str
    plugin_type: str = "general"
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    entry_point: str = "main.py"
    dependencies: Dict[str, str] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    api_hooks: List[Dict[str, str]] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    min_serpentai_version: str = "0.1.0"
    python_requires: str = ">=3.8"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        """从字典创建清单实例"""
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            plugin_type=data.get("type", "general"),
            author=data.get("author", ""),
            license=data.get("license", "MIT"),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            entry_point=data.get("entry_point", "main.py"),
            dependencies=data.get("dependencies", {}),
            permissions=data.get("permissions", []),
            api_hooks=data.get("api_hooks", []),
            config_schema=data.get("config_schema", {}),
            tags=data.get("tags", []),
            icon=data.get("icon", ""),
            min_serpentai_version=data.get("min_serpentai_version", "0.1.0"),
            python_requires=data.get("python_requires", ">=3.8"),
        )

    @classmethod
    def from_file(cls, path: str) -> "PluginManifest":
        """
        从 plugin.json 文件加载清单
        
        Args:
            path: plugin.json 文件的绝对路径
            
        Returns:
            PluginManifest 实例
            
        Raises:
            ManifestError: 清单文件不存在或格式错误
        """
        if not os.path.exists(path):
            raise ManifestError(f"插件清单文件不存在: {path}")
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ManifestError(f"插件清单JSON格式错误: {e}")
        
        manifest = cls.from_dict(data)
        manifest._validate()
        return manifest

    @classmethod
    def create_template(cls, name: str, plugin_type: str = "tool",
                        description: str = "") -> Dict[str, Any]:
        """
        生成插件清单模板
        
        Args:
            name: 插件名称
            plugin_type: 插件类型
            description: 插件描述
            
        Returns:
            可序列化为JSON的字典
        """
        return {
            "name": name,
            "version": "0.1.0",
            "type": plugin_type,
            "description": description or f"{name} 插件",
            "author": "",
            "license": "MIT",
            "homepage": "",
            "repository": "",
            "entry_point": "main.py",
            "dependencies": {},
            "permissions": [],
            "api_hooks": [],
            "config_schema": {},
            "tags": [],
            "icon": "",
            "min_serpentai_version": "0.1.0",
            "python_requires": ">=3.8",
        }

    def _validate(self):
        """
        验证清单数据的完整性和合法性
        
        Raises:
            ManifestError: 验证失败
        """
        errors = []
        
        # 必填字段检查
        if not self.name:
            errors.append("name 不能为空")
        if not self.version:
            errors.append("version 不能为空")
        if not self.description:
            errors.append("description 不能为空")
        
        # 名称格式：只允许字母、数字、下划线和连字符
        if self.name and not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
            errors.append(f"插件名称格式错误: {self.name}，只允许字母、数字、下划线和连字符")
        
        # 版本格式验证
        if self.version and not SEMVER_RE.match(self.version):
            errors.append(f"版本号格式错误: {self.version}，需要语义化版本 (如 1.2.3)")
        
        # 插件类型验证
        if self.plugin_type not in PLUGIN_TYPES:
            errors.append(f"未知插件类型: {self.plugin_type}，支持: {PLUGIN_TYPES}")
        
        # 权限验证
        for perm in self.permissions:
            if perm not in SUPPORTED_PERMISSIONS:
                errors.append(f"未知权限: {perm}，支持: {list(SUPPORTED_PERMISSIONS.keys())}")
        
        # API hooks 验证
        for hook in self.api_hooks:
            if not isinstance(hook, dict) or "event" not in hook:
                errors.append(f"API hook 格式错误，必须包含 event 字段: {hook}")
        
        # 依赖版本验证
        for dep_name, dep_ver in self.dependencies.items():
            if not dep_name:
                errors.append("依赖名称不能为空")
            if dep_ver and not SEMVER_RE.match(dep_ver):
                errors.append(f"依赖版本格式错误: {dep_name}@{dep_ver}")
        
        if errors:
            raise ManifestError(f"清单验证失败:\n" + "\n".join(f"  - {e}" for e in errors))

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "type": self.plugin_type,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "api_hooks": self.api_hooks,
            "config_schema": self.config_schema,
            "tags": self.tags,
            "icon": self.icon,
            "min_serpentai_version": self.min_serpentai_version,
            "python_requires": self.python_requires,
        }

    def to_json(self, indent: int = 2) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent= indent)

    def matches_version(self, version_range: str) -> bool:
        """
        检查当前版本是否匹配版本范围
        支持简单的 ^, ~, >=, >, = 前缀
        
        Args:
            version_range: 版本范围表达式
            
        Returns:
            是否匹配
        """
        if not version_range:
            return True
        
        range_str = version_range.strip()
        my_parts = [int(x) for x in self.version.split(".")[:3]]
        
        if range_str.startswith("^"):
            # 兼容版本：主版本号相同
            target = [int(x) for x in range_str[1:].split(".")[:3]]
            return my_parts[0] == target[0] and tuple(my_parts) >= tuple(target)
        elif range_str.startswith("~"):
            # 近似版本：主.次版本号相同
            target = [int(x) for x in range_str[1:].split(".")[:3]]
            return my_parts[:2] == target[:2] and tuple(my_parts) >= tuple(target)
        elif range_str.startswith(">="):
            target = [int(x) for x in range_str[2:].split(".")[:3]]
            return tuple(my_parts) >= tuple(target)
        elif range_str.startswith(">"):
            target = [int(x) for x in range_str[1:].split(".")[:3]]
            return tuple(my_parts) > tuple(target)
        elif range_str.startswith("=") or range_str.startswith("=="):
            target = [int(x) for x in range_str.lstrip("= ").split(".")[:3]]
            return tuple(my_parts) == tuple(target)
        else:
            # 精确匹配
            target = [int(x) for x in range_str.split(".")[:3]]
            return tuple(my_parts) == tuple(target)


class ManifestError(Exception):
    """插件清单错误"""
    pass
