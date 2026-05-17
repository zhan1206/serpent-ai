# -*- coding: utf-8 -*-
"""
技能安装器 - 从URL/GitHub/本地安装技能
"""

import os
import json
import shutil
import tempfile
import zipfile
import logging
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Any

from .skill import Skill, SkillManifest

logger = logging.getLogger(__name__)

UA = "SerpentAI/1.0 (SkillInstaller)"


class SkillInstaller:
    """
    技能安装器
    
    支持的安装来源：
    1. HTTP/HTTPS URL（直接下载 skill.json 或 zip 包）
    2. GitHub 仓库（下载并解压）
    3. 本地文件路径
    """
    
    def __init__(self, install_dir: str):
        """
        Args:
            install_dir: 技能安装目录
        """
        self.install_dir = os.path.abspath(install_dir)
        os.makedirs(self.install_dir, exist_ok=True)
    
    def install_from_url(self, url: str) -> Skill:
        """
        从 URL 安装技能
        
        Args:
            url: 技能包URL（skill.json 或 zip 文件）
            
        Returns:
            安装的技能
            
        Raises:
            ValueError: 安装失败
        """
        if url.endswith(".zip"):
            return self._install_from_zip_url(url)
        elif url.endswith(".json") or "/raw/" in url:
            return self._install_from_json_url(url)
        elif "github.com" in url:
            return self._install_from_github(url)
        else:
            # 尝试作为 JSON 下载
            return self._install_from_json_url(url)
    
    def install_from_github(self, repo_url: str, branch: str = "main") -> Skill:
        """
        从 GitHub 仓库安装技能
        
        Args:
            repo_url: GitHub 仓库URL
            branch: 分支名
            
        Returns:
            安装的技能
        """
        # 构造 raw.githubusercontent.com URL
        repo_url = repo_url.rstrip("/")
        if repo_url.endswith(".git"):
            repo_url = repo_url[:-4]
        
        parts = repo_url.split("/")
        if len(parts) < 5:
            raise ValueError(f"无效的 GitHub URL: {repo_url}")
        
        owner = parts[-2]
        repo = parts[-1]
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/skill.json"
        
        return self._install_from_json_url(raw_url)
    
    def install_from_file(self, file_path: str) -> Skill:
        """
        从本地文件安装技能
        
        Args:
            file_path: 本地 skill.json 或 zip 文件路径
            
        Returns:
            安装的技能
        """
        if file_path.endswith(".zip"):
            return self._install_from_zip_file(file_path)
        else:
            return self._install_from_json_file(file_path)
    
    def install_from_dict(self, skill_data: Dict[str, Any]) -> Skill:
        """
        从字典直接安装技能
        
        Args:
            skill_data: 技能清单数据
            
        Returns:
            安装的技能
        """
        manifest = SkillManifest.from_dict(skill_data)
        skill_dir = os.path.join(self.install_dir, manifest.name)
        os.makedirs(skill_dir, exist_ok=True)
        
        manifest_path = os.path.join(skill_dir, "skill.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, ensure_ascii=False, indent=2)
        
        skill = Skill(manifest, skill_dir)
        logger.info(f"从字典安装技能: {manifest.name}")
        return skill
    
    def update_skill(self, name: str, url: str = None) -> Skill:
        """
        更新已安装的技能
        
        Args:
            name: 技能名称
            url: 新版本的URL（None则使用原来的来源）
        """
        skill_dir = os.path.join(self.install_dir, name)
        if not os.path.isdir(skill_dir):
            raise ValueError(f"技能未安装: {name}")
        
        # 重新安装
        new_skill = self.install_from_url(url) if url else None
        logger.info(f"技能已更新: {name}")
        return new_skill
    
    def uninstall(self, name: str) -> bool:
        """卸载技能"""
        skill_dir = os.path.join(self.install_dir, name)
        if os.path.isdir(skill_dir):
            shutil.rmtree(skill_dir, ignore_errors=True)
            logger.info(f"技能已卸载: {name}")
            return True
        return False
    
    def _install_from_json_url(self, url: str) -> Skill:
        """从 JSON URL 安装"""
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return self.install_from_dict(data)
    
    def _install_from_zip_url(self, url: str) -> Skill:
        """从 ZIP URL 安装"""
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_data = resp.read()
        
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(zip_data)
            tmp_path = tmp.name
        
        try:
            return self._install_from_zip_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def _install_from_zip_file(self, zip_path: str) -> Skill:
        """从 ZIP 文件安装"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)
            
            # 查找 skill.json
            manifest_path = None
            for root, dirs, files in os.walk(tmp_dir):
                if "skill.json" in files:
                    manifest_path = os.path.join(root, "skill.json")
                    break
            
            if not manifest_path:
                raise ValueError("ZIP 包中未找到 skill.json")
            
            return self._install_from_json_file(manifest_path)
    
    def _install_from_json_file(self, file_path: str) -> Skill:
        """从本地 JSON 文件安装"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        manifest = SkillManifest.from_dict(data)
        skill_dir = os.path.join(self.install_dir, manifest.name)
        
        if os.path.exists(skill_dir):
            shutil.rmtree(skill_dir)
        shutil.copytree(os.path.dirname(file_path), skill_dir)
        
        skill = Skill(manifest, skill_dir)
        logger.info(f"从文件安装技能: {manifest.name}")
        return skill
    
    def _install_from_github(self, url: str) -> Skill:
        """GitHub 安装"""
        return self.install_from_github(url)
