# -*- coding: utf-8 -*-
"""
技能商店 - 技能的发现、安装、搜索和管理
"""

import os
import json
import logging
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime

from .skill import Skill, SkillManifest

logger = logging.getLogger(__name__)

# 技能元数据存储文件
_METADATA_FILE = "data/skills_meta.json"

# 技能类别
SKILL_CATEGORIES = {
    "general": "通用",
    "research": "研究",
    "coding": "编程",
    "writing": "写作",
    "analysis": "数据分析",
    "communication": "沟通",
    "productivity": "效率",
    "creative": "创意",
    "education": "教育",
    "entertainment": "娱乐",
}


class SkillStore:
    """
    技能商店
    
    功能：
    1. 管理已安装的技能
    2. 发现内置技能和在线技能
    3. 技能搜索和分类浏览
    4. 评分和评论
    5. 技能启用/禁用
    """
    
    def __init__(self, skill_dirs: List[str] = None):
        self.skill_dirs = skill_dirs or []
        self._skills: Dict[str, Skill] = {}  # name -> Skill
        self._metadata: Dict[str, Dict] = {}  # name -> meta
        self._load_metadata()
    
    def add_skill_dir(self, directory: str):
        """添加技能搜索目录"""
        abs_dir = os.path.abspath(directory)
        if abs_dir not in self.skill_dirs:
            self.skill_dirs.append(abs_dir)
    
    def discover_all(self) -> List[str]:
        """发现所有可用技能"""
        discovered = []
        
        for skill_dir in self.skill_dirs:
            if not os.path.isdir(skill_dir):
                continue
            for entry in os.listdir(skill_dir):
                entry_path = os.path.join(skill_dir, entry)
                manifest_path = os.path.join(entry_path, "skill.json")
                if os.path.isdir(entry_path) and os.path.exists(manifest_path):
                    try:
                        manifest = SkillManifest.from_file(manifest_path)
                        skill = Skill(manifest, entry_path)
                        self._skills[manifest.name] = skill
                        # 恢复元数据
                        if manifest.name in self._metadata:
                            meta = self._metadata[manifest.name]
                            skill.installed_at = meta.get("installed_at")
                            skill.rating = meta.get("rating", 0.0)
                            skill.rating_count = meta.get("rating_count", 0)
                            skill.enabled = meta.get("enabled", True)
                        elif skill.installed_at is None:
                            skill.installed_at = datetime.now().isoformat()
                            self._save_metadata_for(manifest.name, skill)
                        discovered.append(manifest.name)
                    except Exception as e:
                        logger.warning(f"跳过技能 {entry}: {e}")
        
        logger.info(f"技能发现完成: 发现 {len(discovered)} 个技能")
        return discovered
    
    def install_skill(self, skill_data: Dict[str, Any], target_dir: str) -> Skill:
        """
        安装技能到本地
        
        Args:
            skill_data: 技能清单数据（字典）
            target_dir: 目标安装目录
            
        Returns:
            安装的技能实例
        """
        manifest = SkillManifest.from_dict(skill_data)
        skill_dir = os.path.join(target_dir, manifest.name)
        os.makedirs(skill_dir, exist_ok=True)
        
        # 写入 skill.json
        manifest_path = os.path.join(skill_dir, "skill.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)
        
        skill = Skill(manifest, skill_dir)
        skill.installed_at = datetime.now().isoformat()
        self._skills[manifest.name] = skill
        self._save_metadata_for(manifest.name, skill)
        
        logger.info(f"技能已安装: {manifest.name} v{manifest.version}")
        return skill
    
    def remove_skill(self, name: str) -> bool:
        """移除技能"""
        skill = self._skills.get(name)
        if not skill:
            return False
        
        # 移除目录
        if os.path.isdir(skill.skill_dir):
            shutil.rmtree(skill.skill_dir, ignore_errors=True)
        
        del self._skills[name]
        self._metadata.pop(name, None)
        self._save_metadata()
        
        logger.info(f"技能已移除: {name}")
        return True
    
    def enable_skill(self, name: str) -> bool:
        """启用技能"""
        skill = self._skills.get(name)
        if not skill:
            return False
        skill.enabled = True
        self._save_metadata_for(name, skill)
        return True
    
    def disable_skill(self, name: str) -> bool:
        """禁用技能"""
        skill = self._skills.get(name)
        if not skill:
            return False
        skill.enabled = False
        self._save_metadata_for(name, skill)
        return True
    
    def rate_skill(self, name: str, rating: float) -> bool:
        """为技能评分（1-5）"""
        if not 1 <= rating <= 5:
            return False
        skill = self._skills.get(name)
        if not skill:
            return False
        # 简单的平均评分
        total = skill.rating * skill.rating_count + rating
        skill.rating_count += 1
        skill.rating = round(total / skill.rating_count, 1)
        self._save_metadata_for(name, skill)
        return True
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(name)
    
    def list_skills(self, category: Optional[str] = None,
                   enabled_only: bool = False) -> List[Dict[str, Any]]:
        """列出技能"""
        results = []
        for skill in self._skills.values():
            if category and skill.manifest.category != category:
                continue
            if enabled_only and not skill.enabled:
                continue
            results.append(skill.get_info())
        return results
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """搜索技能"""
        query = query.lower()
        results = []
        for skill in self._skills.values():
            searchable = " ".join([
                skill.name, skill.manifest.display_name,
                skill.manifest.description,
                " ".join(skill.manifest.tags),
                skill.manifest.author,
                skill.manifest.category,
            ]).lower()
            if query in searchable:
                results.append(skill.get_info())
        return results
    
    def get_categories(self) -> Dict[str, int]:
        """获取技能分类统计"""
        cats: Dict[str, int] = {}
        for skill in self._skills.values():
            cat = skill.manifest.category
            cats[cat] = cats.get(cat, 0) + 1
        return cats
    
    def get_stats(self) -> Dict[str, Any]:
        """获取技能统计"""
        total = len(self._skills)
        enabled = sum(1 for s in self._skills.values() if s.enabled)
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "categories": self.get_categories(),
        }
    
    def _load_metadata(self):
        """加载元数据"""
        if os.path.exists(_METADATA_FILE):
            try:
                with open(_METADATA_FILE, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.warning(f"加载技能元数据失败: {e}")
                self._metadata = {}
    
    def _save_metadata(self):
        """保存元数据"""
        try:
            os.makedirs(os.path.dirname(_METADATA_FILE), exist_ok=True)
            with open(_METADATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存技能元数据失败: {e}")
    
    def _save_metadata_for(self, name: str, skill: Skill):
        """保存单个技能的元数据"""
        self._metadata[name] = {
            "installed_at": skill.installed_at,
            "rating": skill.rating,
            "rating_count": skill.rating_count,
            "enabled": skill.enabled,
            "version": skill.version,
        }
        self._save_metadata()


# 全局技能商店实例
_store_instance = None


def get_skill_store() -> SkillStore:
    """获取全局技能商店实例"""
    global _store_instance
    if _store_instance is None:
        _store_instance = SkillStore()
    return _store_instance
