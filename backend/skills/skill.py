# -*- coding: utf-8 -*-
"""
技能定义 - 技能的数据模型
技能 = 工具定义 + 提示词模板 + 示例用法
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:[0-9A-Za-z-]+)(?:\.(?:[0-9A-Za-z-]+))*))?(?:\+([0-9A-Za-z-]+))?$")


class SkillManifest:
    """
    技能清单 - 对应 skill.json
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        display_name: str = "",
        description: str = "",
        author: str = "",
        license: str = "MIT",
        category: str = "general",
        tags: List[str] = None,
        icon: str = "",
        tools: List[str] = None,
        required_plugins: List[str] = None,
        prompt_template: str = "",
        examples: List[Dict[str, str]] = None,
        config_schema: Dict[str, Any] = None,
        homepage: str = "",
        repository: str = "",
        min_serpentai_version: str = "0.1.0",
    ):
        self.name = name
        self.version = version
        self.display_name = display_name or name
        self.description = description
        self.author = author
        self.license = license
        self.category = category
        self.tags = tags or []
        self.icon = icon
        self.tools = tools or []
        self.required_plugins = required_plugins or []
        self.prompt_template = prompt_template
        self.examples = examples or []
        self.config_schema = config_schema or {}
        self.homepage = homepage
        self.repository = repository
        self.min_serpentai_version = min_serpentai_version
    
    @classmethod
    def from_file(cls, path: str) -> "SkillManifest":
        """从 skill.json 加载"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"技能清单文件不存在: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"技能清单JSON格式错误: {e}")
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillManifest":
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            display_name=data.get("display_name", data.get("name", "")),
            description=data.get("description", ""),
            author=data.get("author", ""),
            license=data.get("license", "MIT"),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            icon=data.get("icon", ""),
            tools=data.get("tools", []),
            required_plugins=data.get("required_plugins", []),
            prompt_template=data.get("prompt_template", ""),
            examples=data.get("examples", []),
            config_schema=data.get("config_schema", {}),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            min_serpentai_version=data.get("min_serpentai_version", "0.1.0"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "display_name": self.display_name,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "category": self.category,
            "tags": self.tags,
            "icon": self.icon,
            "tools": self.tools,
            "required_plugins": self.required_plugins,
            "prompt_template": self.prompt_template,
            "examples": self.examples,
            "config_schema": self.config_schema,
            "homepage": self.homepage,
            "repository": self.repository,
            "min_serpentai_version": self.min_serpentai_version,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class Skill:
    """
    技能实例
    """
    
    def __init__(self, manifest: SkillManifest, skill_dir: str):
        self.manifest = manifest
        self.skill_dir = skill_dir
        self.installed_at: Optional[str] = None
        self.rating: float = 0.0
        self.rating_count: int = 0
        self.enabled: bool = True
    
    @property
    def name(self) -> str:
        return self.manifest.name
    
    @property
    def version(self) -> str:
        return self.manifest.version
    
    def get_info(self) -> Dict[str, Any]:
        """获取技能信息"""
        return {
            "name": self.name,
            "version": self.version,
            "display_name": self.manifest.display_name,
            "description": self.manifest.description,
            "author": self.manifest.author,
            "category": self.manifest.category,
            "tags": self.manifest.tags,
            "icon": self.manifest.icon,
            "tools": self.manifest.tools,
            "required_plugins": self.manifest.required_plugins,
            "examples": self.manifest.examples,
            "installed_at": self.installed_at,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "enabled": self.enabled,
            "directory": self.skill_dir,
        }
