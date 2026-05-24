# -*- coding: utf-8 -*-
"""
插件商店 - 插件仓库管理、搜索、安装/卸载/更新、安全审核
支持内置插件和远程仓库，基于SQLite持久化
"""

import json
import os
import shutil
import logging
import sqlite3
import tempfile
import zipfile
import subprocess
import sys
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

from .plugin_manifest import PluginManifest, ManifestError
from .plugin_base import PluginState
from .plugin_manager import get_plugin_manager

logger = logging.getLogger(__name__)


@dataclass
class StorePluginInfo:
    """商店中的插件信息"""
    name: str
    version: str
    description: str
    plugin_type: str = "general"
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    rating: float = 0.0
    downloads: int = 0
    source: str = "builtin"  # builtin / remote
    remote_url: str = ""
    signature: str = ""  # 数字签名（Base64）
    manifest_dict: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_manifest(cls, manifest: PluginManifest, source: str = "builtin",
                      remote_url: str = "", **kwargs) -> "StorePluginInfo":
        return cls(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            plugin_type=manifest.plugin_type,
            author=manifest.author,
            license=manifest.license,
            homepage=manifest.homepage,
            repository=manifest.repository,
            tags=manifest.tags,
            icon=manifest.icon,
            source=source,
            remote_url=remote_url,
            manifest_dict=manifest.to_dict(),
            **kwargs,
        )


class PluginStore:
    """
    插件商店

    功能：
    - 插件仓库管理（内置 + 远程仓库）
    - 插件搜索（按名称/分类/标签）
    - 插件安装/卸载/更新
    - 插件启用/禁用
    - 插件信息查看（版本/作者/描述/评分）
    - 安全审核：安装前检查manifest，验证签名（框架）
    - 一键分享：将本地插件打包发布到仓库
    - 依赖管理：自动安装插件依赖
    - 基于SQLite持久化已安装插件列表
    """

    # 默认远程仓库列表
    DEFAULT_REMOTES = [
        "https://plugins.serpentai.dev/api/v1",
    ]

    def __init__(self, data_dir: str = None, plugin_install_dir: str = None):
        """
        初始化插件商店

        Args:
            data_dir: 数据存储目录（SQLite文件位置）
            plugin_install_dir: 插件安装目录
        """
        self._data_dir = data_dir or os.path.join(
            os.path.expanduser("~"), ".serpentai", "store"
        )
        self._plugin_install_dir = plugin_install_dir or os.path.join(
            self._data_dir, "installed"
        )
        os.makedirs(self._data_dir, exist_ok=True)
        os.makedirs(self._plugin_install_dir, exist_ok=True)

        self._db_path = os.path.join(self._data_dir, "plugin_store.db")
        self._remotes: List[str] = list(self.DEFAULT_REMOTES)
        self._builtin_cache: Dict[str, StorePluginInfo] = {}
        self._audit_callbacks: List[Callable] = []

        self._init_db()
        self._scan_builtins()

    # ==================== 数据库 ====================

    def _init_db(self):
        """初始化SQLite数据库"""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS installed_plugins (
                    name TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    plugin_type TEXT DEFAULT 'general',
                    author TEXT DEFAULT '',
                    license TEXT DEFAULT 'MIT',
                    homepage TEXT DEFAULT '',
                    repository TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    icon TEXT DEFAULT '',
                    source TEXT DEFAULT 'builtin',
                    remote_url TEXT DEFAULT '',
                    enabled INTEGER DEFAULT 1,
                    rating REAL DEFAULT 0.0,
                    downloads INTEGER DEFAULT 0,
                    signature TEXT DEFAULT '',
                    install_path TEXT DEFAULT '',
                    installed_at TEXT DEFAULT '',
                    updated_at TEXT DEFAULT '',
                    manifest_json TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS remote_repos (
                    url TEXT PRIMARY KEY,
                    name TEXT DEFAULT '',
                    enabled INTEGER DEFAULT 1,
                    last_sync TEXT DEFAULT '',
                    added_at TEXT DEFAULT ''
                )
            """)
            conn.commit()
        logger.info(f"插件商店数据库初始化完成: {self._db_path}")

    def _db_execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(sql, params)

    def _db_executemany(self, sql: str, params_list: list):
        with sqlite3.connect(self._db_path) as conn:
            conn.executemany(sql, params_list)
            conn.commit()

    def _db_execute_commit(self, sql: str, params: tuple = ()):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(sql, params)
            conn.commit()

    # ==================== 内置插件扫描 ====================

    def _scan_builtins(self):
        """扫描内置插件目录"""
        self._builtin_cache.clear()
        builtin_dir = os.path.join(os.path.dirname(__file__), "builtin")
        if not os.path.isdir(builtin_dir):
            return

        for entry in os.listdir(builtin_dir):
            entry_path = os.path.join(builtin_dir, entry)
            manifest_path = os.path.join(entry_path, "plugin.json")
            if os.path.isdir(entry_path) and os.path.exists(manifest_path):
                try:
                    manifest = PluginManifest.from_file(manifest_path)
                    info = StorePluginInfo.from_manifest(manifest, source="builtin")
                    info.manifest_dict = manifest.to_dict()
                    self._builtin_cache[manifest.name] = info
                except ManifestError as e:
                    logger.warning(f"内置插件清单错误 [{entry}]: {e}")

        # 同步内置插件到数据库
        for name, info in self._builtin_cache.items():
            self._upsert_installed(info, install_path="builtin")
        logger.info(f"内置插件扫描完成: {len(self._builtin_cache)} 个")

    def _upsert_installed(self, info: StorePluginInfo, install_path: str = ""):
        """插入或更新已安装插件记录"""
        now = datetime.now().isoformat()
        existing = self._db_execute(
            "SELECT name FROM installed_plugins WHERE name = ?", (info.name,)
        ).fetchone()

        if existing:
            self._db_execute_commit(
                """UPDATE installed_plugins SET
                    version=?, description=?, plugin_type=?, author=?,
                    license=?, homepage=?, repository=?, tags=?,
                    icon=?, source=?, remote_url=?, signature=?,
                    updated_at=?, manifest_json=?
                WHERE name=?""",
                (
                    info.version, info.description, info.plugin_type, info.author,
                    info.license, info.homepage, info.repository,
                    json.dumps(info.tags, ensure_ascii=False), info.icon,
                    info.source, info.remote_url, info.signature,
                    now, json.dumps(info.manifest_dict, ensure_ascii=False),
                    info.name,
                ),
            )
        else:
            self._db_execute_commit(
                """INSERT INTO installed_plugins
                    (name, version, description, plugin_type, author, license,
                     homepage, repository, tags, icon, source, remote_url,
                     enabled, rating, downloads, signature, install_path,
                     installed_at, updated_at, manifest_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    info.name, info.version, info.description, info.plugin_type,
                    info.author, info.license, info.homepage, info.repository,
                    json.dumps(info.tags, ensure_ascii=False), info.icon,
                    info.source, info.remote_url, 1, info.rating, info.downloads,
                    info.signature, install_path, now, now,
                    json.dumps(info.manifest_dict, ensure_ascii=False),
                ),
            )

    # ==================== 远程仓库管理 ====================

    def add_remote(self, url: str, name: str = "") -> bool:
        """
        添加远程仓库

        Args:
            url: 仓库API地址
            name: 仓库名称
        """
        if url in self._remotes:
            return False
        self._remotes.append(url)
        now = datetime.now().isoformat()
        self._db_execute_commit(
            "INSERT OR REPLACE INTO remote_repos (url, name, enabled, added_at) VALUES (?,?,?,?)",
            (url, name or url, 1, now),
        )
        logger.info(f"添加远程仓库: {url}")
        return True

    def remove_remote(self, url: str) -> bool:
        """移除远程仓库"""
        if url in self._remotes:
            self._remotes.remove(url)
        self._db_execute_commit("DELETE FROM remote_repos WHERE url = ?", (url,))
        return True

    def list_remotes(self) -> List[Dict[str, Any]]:
        """列出所有远程仓库"""
        rows = self._db_execute("SELECT * FROM remote_repos").fetchall()
        return [dict(r) for r in rows]

    def sync_remote(self, url: str = None) -> List[StorePluginInfo]:
        """
        同步远程仓库插件列表

        Args:
            url: 指定仓库URL，None则同步所有

        Returns:
            同步到的插件列表
        """
        import urllib.request
        import urllib.error

        targets = [url] if url else self._remotes
        results = []

        for repo_url in targets:
            try:
                api_url = f"{repo_url.rstrip('/')}/plugins"
                req = urllib.request.Request(api_url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                plugins = data if isinstance(data, list) else data.get("plugins", [])
                for p in plugins:
                    info = StorePluginInfo(
                        name=p.get("name", ""),
                        version=p.get("version", "0.0.0"),
                        description=p.get("description", ""),
                        plugin_type=p.get("type", "general"),
                        author=p.get("author", ""),
                        tags=p.get("tags", []),
                        source="remote",
                        remote_url=repo_url,
                        rating=p.get("rating", 0.0),
                        downloads=p.get("downloads", 0),
                        signature=p.get("signature", ""),
                    )
                    results.append(info)

                now = datetime.now().isoformat()
                self._db_execute_commit(
                    "UPDATE remote_repos SET last_sync = ? WHERE url = ?",
                    (now, repo_url),
                )
                logger.info(f"远程仓库同步成功: {repo_url} ({len(plugins)} 个插件)")

            except urllib.error.URLError as e:
                logger.warning(f"远程仓库同步失败 [{repo_url}]: {e}")
            except Exception as e:
                logger.error(f"远程仓库同步异常 [{repo_url}]: {e}")

        return results

    # ==================== 搜索 ====================

    def search(self, query: str = "", category: str = None,
               tags: List[str] = None, source: str = None,
               limit: int = 50) -> List[Dict[str, Any]]:
        """
        搜索插件

        Args:
            query: 关键词（匹配名称、描述、作者）
            category: 按插件类型过滤
            tags: 按标签过滤
            source: 按来源过滤 (builtin/remote)
            limit: 最大返回数
        """
        results = []

        # 1. 从内置缓存搜索
        for info in self._builtin_cache.values():
            if self._match_search(info, query, category, tags, source):
                results.append(self._enrich_info(info))

        # 2. 从已安装数据库搜索（补充远程安装的）
        installed = self._db_execute(
            "SELECT * FROM installed_plugins"
        ).fetchall()
        for row in installed:
            info = self._row_to_info(row)
            if self._match_search(info, query, category, tags, source):
                # 避免重复
                if not any(r["name"] == info.name for r in results):
                    results.append(self._enrich_info(info))

        return results[:limit]

    def _match_search(self, info: StorePluginInfo, query: str,
                      category: str, tags: List[str], source: str) -> bool:
        """检查插件是否匹配搜索条件"""
        if source and info.source != source:
            return False
        if category and info.plugin_type != category:
            return False
        if tags:
            if not all(t in info.tags for t in tags):
                return False
        if query:
            q = query.lower()
            searchable = f"{info.name} {info.description} {info.author} {' '.join(info.tags)}".lower()
            if q not in searchable:
                return False
        return True

    def _enrich_info(self, info: StorePluginInfo) -> Dict[str, Any]:
        """丰富插件信息（加上安装/启用状态）"""
        row = self._db_execute(
            "SELECT enabled, installed_at, updated_at, install_path FROM installed_plugins WHERE name = ?",
            (info.name,),
        ).fetchone()
        d = info.to_dict()
        if row:
            d["installed"] = True
            d["enabled"] = bool(row["enabled"])
            d["installed_at"] = row["installed_at"]
            d["updated_at"] = row["updated_at"]
            d["install_path"] = row["install_path"]
        else:
            d["installed"] = False
            d["enabled"] = False
        return d

    def _row_to_info(self, row: sqlite3.Row) -> StorePluginInfo:
        """数据库行转StorePluginInfo"""
        return StorePluginInfo(
            name=row["name"],
            version=row["version"],
            description=row["description"],
            plugin_type=row["plugin_type"],
            author=row["author"],
            license=row["license"],
            homepage=row["homepage"],
            repository=row["repository"],
            tags=json.loads(row["tags"]),
            icon=row["icon"],
            source=row["source"],
            remote_url=row["remote_url"],
            rating=row["rating"],
            downloads=row["downloads"],
            signature=row["signature"],
            manifest_dict=json.loads(row["manifest_json"]) if row["manifest_json"] else {},
        )

    # ==================== 安装/卸载/更新 ====================

    def install(self, name: str, source_url: str = None,
                verify_signature: bool = True) -> Dict[str, Any]:
        """
        安装插件

        Args:
            name: 插件名称
            source_url: 指定远程仓库URL（None则自动搜索）
            verify_signature: 是否验证签名

        Returns:
            安装结果 {"success": bool, "message": str, "info": dict|None}
        """
        # 检查是否已安装
        existing = self._db_execute(
            "SELECT * FROM installed_plugins WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            return {"success": False, "message": f"插件 {name} 已安装", "info": dict(existing)}

        # 尝试从内置安装
        if name in self._builtin_cache:
            info = self._builtin_cache[name]
            self._upsert_installed(info, install_path="builtin")
            return {"success": True, "message": f"内置插件 {name} 安装成功", "info": self._enrich_info(info)}

        # 从远程仓库安装
        plugin_data = self._fetch_remote_plugin(name, source_url)
        if not plugin_data:
            return {"success": False, "message": f"未找到插件 {name}", "info": None}

        # 安全审核
        audit_result = self._audit_plugin(plugin_data, verify_signature)
        if not audit_result["passed"]:
            return {"success": False, "message": f"安全审核未通过: {audit_result['reason']}", "info": None}

        # 下载并解压
        try:
            install_path = self._download_and_extract(plugin_data)
        except Exception as e:
            return {"success": False, "message": f"下载安装失败: {e}", "info": None}

        # 验证manifest
        manifest_path = os.path.join(install_path, "plugin.json")
        if not os.path.exists(manifest_path):
            shutil.rmtree(install_path, ignore_errors=True)
            return {"success": False, "message": "插件包缺少 plugin.json", "info": None}

        try:
            manifest = PluginManifest.from_file(manifest_path)
        except ManifestError as e:
            shutil.rmtree(install_path, ignore_errors=True)
            return {"success": False, "message": f"插件清单无效: {e}", "info": None}

        # 安装依赖
        dep_result = self._install_dependencies(manifest)
        if not dep_result["success"]:
            logger.warning(f"插件依赖安装部分失败: {dep_result['message']}")

        # 持久化
        info = StorePluginInfo.from_manifest(manifest, source="remote",
                                             remote_url=plugin_data.get("repo_url", ""))
        info.signature = plugin_data.get("signature", "")
        self._upsert_installed(info, install_path=install_path)

        # 注册到插件管理器
        try:
            pm = get_plugin_manager()
            pm.add_plugin_dir(install_path)
            pm.discover_all()
        except Exception as e:
            logger.warning(f"注册到插件管理器失败: {e}")

        return {"success": True, "message": f"插件 {name} 安装成功", "info": self._enrich_info(info)}

    def uninstall(self, name: str, remove_data: bool = True) -> Dict[str, Any]:
        """
        卸载插件

        Args:
            name: 插件名称
            remove_data: 是否删除插件文件

        Returns:
            卸载结果
        """
        row = self._db_execute(
            "SELECT * FROM installed_plugins WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return {"success": False, "message": f"插件 {name} 未安装"}

        # 不允许卸载内置插件
        if row["source"] == "builtin":
            return {"success": False, "message": f"内置插件 {name} 不可卸载"}

        # 先停止插件
        try:
            pm = get_plugin_manager()
            pm.unload_plugin(name)
        except Exception:
            pass

        # 删除文件
        if remove_data and row["install_path"] and row["install_path"] != "builtin":
            install_path = row["install_path"]
            if os.path.isdir(install_path):
                shutil.rmtree(install_path, ignore_errors=True)

        # 从数据库删除
        self._db_execute_commit("DELETE FROM installed_plugins WHERE name = ?", (name,))

        return {"success": True, "message": f"插件 {name} 已卸载"}

    def update(self, name: str, verify_signature: bool = True) -> Dict[str, Any]:
        """
        更新插件

        Args:
            name: 插件名称
            verify_signature: 是否验证签名

        Returns:
            更新结果
        """
        row = self._db_execute(
            "SELECT * FROM installed_plugins WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return {"success": False, "message": f"插件 {name} 未安装"}

        current_version = row["version"]
        source = row["source"]
        remote_url = row["remote_url"]

        # 检查更新
        plugin_data = self._fetch_remote_plugin(name, remote_url if source == "remote" else None)
        if not plugin_data:
            return {"success": False, "message": f"未找到插件 {name} 的远程版本"}

        new_version = plugin_data.get("version", "0.0.0")
        if new_version == current_version:
            return {"success": True, "message": f"插件 {name} 已是最新版本 {current_version}"}

        # 卸载旧版（保留配置）
        old_config = {}
        try:
            pm = get_plugin_manager()
            plugin_info = pm.registry.get_plugin(name)
            if plugin_info:
                old_config = plugin_info.get("config", {})
            pm.unload_plugin(name)
        except Exception:
            pass

        # 安装新版
        audit_result = self._audit_plugin(plugin_data, verify_signature)
        if not audit_result["passed"]:
            return {"success": False, "message": f"安全审核未通过: {audit_result['reason']}"}

        try:
            install_path = self._download_and_extract(plugin_data)
        except Exception as e:
            return {"success": False, "message": f"下载更新失败: {e}"}

        # 清理旧安装目录
        if row["install_path"] and row["install_path"] != "builtin" and os.path.isdir(row["install_path"]):
            shutil.rmtree(row["install_path"], ignore_errors=True)

        manifest_path = os.path.join(install_path, "plugin.json")
        try:
            manifest = PluginManifest.from_file(manifest_path)
        except ManifestError as e:
            return {"success": False, "message": f"新版本清单无效: {e}"}

        dep_result = self._install_dependencies(manifest)

        info = StorePluginInfo.from_manifest(manifest, source="remote",
                                             remote_url=plugin_data.get("repo_url", ""))
        self._upsert_installed(info, install_path=install_path)

        # 重新加载
        try:
            pm = get_plugin_manager()
            pm.add_plugin_dir(install_path)
            pm.discover_all()
            pm.load_plugin(name, old_config)
        except Exception as e:
            logger.warning(f"重新加载插件失败: {e}")

        return {
            "success": True,
            "message": f"插件 {name} 更新成功: {current_version} -> {new_version}",
            "old_version": current_version,
            "new_version": new_version,
        }

    def check_updates(self) -> List[Dict[str, Any]]:
        """检查所有已安装插件的更新"""
        updates = []
        rows = self._db_execute("SELECT * FROM installed_plugins").fetchall()

        for row in rows:
            name = row["name"]
            current_version = row["version"]
            remote_url = row["remote_url"]
            source = row["source"]

            plugin_data = self._fetch_remote_plugin(
                name, remote_url if source == "remote" else None
            )
            if plugin_data:
                new_version = plugin_data.get("version", current_version)
                if new_version != current_version:
                    updates.append({
                        "name": name,
                        "current_version": current_version,
                        "new_version": new_version,
                        "source": source,
                    })

        return updates

    # ==================== 启用/禁用 ====================

    def enable(self, name: str) -> Dict[str, Any]:
        """启用插件"""
        row = self._db_execute(
            "SELECT enabled FROM installed_plugins WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return {"success": False, "message": f"插件 {name} 未安装"}
        if row["enabled"]:
            return {"success": False, "message": f"插件 {name} 已启用"}

        self._db_execute_commit("UPDATE installed_plugins SET enabled = 1 WHERE name = ?", (name,))

        # 加载插件
        try:
            pm = get_plugin_manager()
            pm.load_plugin(name)
        except Exception as e:
            logger.warning(f"启用插件加载失败: {e}")

        return {"success": True, "message": f"插件 {name} 已启用"}

    def disable(self, name: str) -> Dict[str, Any]:
        """禁用插件"""
        row = self._db_execute(
            "SELECT enabled FROM installed_plugins WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return {"success": False, "message": f"插件 {name} 未安装"}
        if not row["enabled"]:
            return {"success": False, "message": f"插件 {name} 已禁用"}

        # 停止插件
        try:
            pm = get_plugin_manager()
            pm.unload_plugin(name)
        except Exception:
            pass

        self._db_execute_commit("UPDATE installed_plugins SET enabled = 0 WHERE name = ?", (name,))
        return {"success": True, "message": f"插件 {name} 已禁用"}

    # ==================== 插件信息 ====================

    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取插件详细信息"""
        if name in self._builtin_cache:
            return self._enrich_info(self._builtin_cache[name])

        row = self._db_execute(
            "SELECT * FROM installed_plugins WHERE name = ?", (name,)
        ).fetchone()
        if row:
            info = self._row_to_info(row)
            return self._enrich_info(info)
        return None

    def list_installed(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """列出已安装插件"""
        sql = "SELECT * FROM installed_plugins"
        if enabled_only:
            sql += " WHERE enabled = 1"
        rows = self._db_execute(sql).fetchall()
        return [self._enrich_info(self._row_to_info(row)) for row in rows]

    # ==================== 安全审核 ====================

    def _audit_plugin(self, plugin_data: Dict[str, Any],
                      verify_signature: bool = True) -> Dict[str, Any]:
        """
        安全审核插件

        检查：
        1. manifest完整性
        2. 权限合理性
        3. 签名验证（框架）
        """
        result = {"passed": True, "reason": "", "warnings": []}

        # 检查基本字段
        required = ["name", "version", "description"]
        for field_name in required:
            if not plugin_data.get(field_name):
                result["passed"] = False
                result["reason"] = f"缺少必要字段: {field_name}"
                return result

        # 检查危险权限
        dangerous_perms = {"shell", "filesystem"}
        manifest = plugin_data.get("manifest", {})
        permissions = manifest.get("permissions", [])
        for perm in permissions:
            if perm in dangerous_perms:
                result["warnings"].append(f"插件请求危险权限: {perm}")

        # 签名验证（框架）
        if verify_signature and plugin_data.get("signature"):
            sig_valid = self._verify_signature(
                plugin_data.get("package_hash", ""),
                plugin_data["signature"],
            )
            if not sig_valid:
                result["warnings"].append("签名验证未通过（可能为自签名或未知来源）")
                # 不阻止安装，仅警告

        # 触发审核回调
        for cb in self._audit_callbacks:
            try:
                cb_result = cb(plugin_data)
                if isinstance(cb_result, dict) and not cb_result.get("passed", True):
                    result["passed"] = False
                    result["reason"] = cb_result.get("reason", "自定义审核未通过")
                    return result
            except Exception as e:
                logger.warning(f"审核回调异常: {e}")

        return result

    def _verify_signature(self, data_hash: str, signature_b64: str) -> bool:
        """
        验证插件签名（框架实现）

        Args:
            data_hash: 数据哈希
            signature_b64: Base64编码的签名

        Returns:
            签名是否有效
        """
        # 框架：实际实现需加载公钥并验证
        if not data_hash or not signature_b64:
            return False
        # TODO: 接入 EncryptionManager 的签名验证
        logger.debug("签名验证框架：跳过实际验证")
        return True

    def add_audit_callback(self, callback: Callable):
        """添加安全审核回调"""
        self._audit_callbacks.append(callback)

    # ==================== 一键分享 ====================

    def publish(self, name: str, repo_url: str = None) -> Dict[str, Any]:
        """
        将本地插件打包发布到仓库

        Args:
            name: 插件名称
            repo_url: 目标仓库URL

        Returns:
            发布结果
        """
        row = self._db_execute(
            "SELECT * FROM installed_plugins WHERE name = ?", (name,)
        ).fetchone()
        if not row and name not in self._builtin_cache:
            return {"success": False, "message": f"插件 {name} 不存在"}

        # 获取插件目录
        if name in self._builtin_cache:
            plugin_dir = os.path.join(os.path.dirname(__file__), "builtin", name)
        elif row and row["install_path"] and row["install_path"] != "builtin":
            plugin_dir = row["install_path"]
        else:
            return {"success": False, "message": f"无法找到插件 {name} 的目录"}

        if not os.path.isdir(plugin_dir):
            return {"success": False, "message": f"插件目录不存在: {plugin_dir}"}

        # 打包为zip
        try:
            zip_path = self._pack_plugin(plugin_dir, name)
        except Exception as e:
            return {"success": False, "message": f"打包失败: {e}"}

        # 上传到仓库（框架）
        target_url = repo_url or (self._remotes[0] if self._remotes else None)
        if not target_url:
            return {"success": True, "message": f"插件已打包: {zip_path}（无远程仓库配置，未上传）", "zip_path": zip_path}

        try:
            upload_result = self._upload_plugin(zip_path, target_url, name)
            return {
                "success": True,
                "message": f"插件 {name} 已发布到 {target_url}",
                "zip_path": zip_path,
                "upload_result": upload_result,
            }
        except Exception as e:
            return {"success": False, "message": f"上传失败: {e}", "zip_path": zip_path}

    def _pack_plugin(self, plugin_dir: str, name: str) -> str:
        """打包插件为zip"""
        tmp_dir = tempfile.mkdtemp(prefix="serpentai_publish_")
        zip_path = os.path.join(tmp_dir, f"{name}.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(plugin_dir):
                # 排除 __pycache__
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for file in files:
                    if file.endswith((".pyc", ".pyo")):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, plugin_dir)
                    zf.write(file_path, arcname)

        logger.info(f"插件打包完成: {zip_path}")
        return zip_path

    def _upload_plugin(self, zip_path: str, repo_url: str, name: str) -> Dict[str, Any]:
        """上传插件到远程仓库（框架）"""
        import urllib.request
        import urllib.error

        api_url = f"{repo_url.rstrip('/')}/plugins/{name}/upload"
        with open(zip_path, "rb") as f:
            zip_data = f.read()

        req = urllib.request.Request(
            api_url,
            data=zip_data,
            headers={"Content-Type": "application/zip"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return {"status": resp.status, "body": resp.read().decode("utf-8", errors="replace")}
        except urllib.error.URLError as e:
            raise RuntimeError(f"上传请求失败: {e}")

    # ==================== 依赖管理 ====================

    def _install_dependencies(self, manifest: PluginManifest) -> Dict[str, Any]:
        """
        自动安装插件依赖

        Args:
            manifest: 插件清单

        Returns:
            安装结果
        """
        deps = manifest.dependencies
        if not deps:
            return {"success": True, "message": "无依赖"}

        failed = []
        python_exe = sys.executable

        for dep_name, dep_version in deps.items():
            # 检查是否为Python包依赖（pip）
            if dep_name.startswith("pip:"):
                package = dep_name[4:]
                try:
                    cmd = [python_exe, "-m", "pip", "install", "--quiet", package]
                    if dep_version and dep_version != "*":
                        cmd[-1] = f"{package}=={dep_version}"
                    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
                    logger.info(f"依赖安装成功: {package}")
                except Exception as e:
                    failed.append(f"{package}: {e}")
                    logger.warning(f"依赖安装失败: {package}: {e}")
            else:
                # 插件间依赖
                try:
                    pm = get_plugin_manager()
                    if not pm.registry.get_instance(dep_name):
                        pm.load_plugin(dep_name)
                except Exception as e:
                    failed.append(f"plugin:{dep_name}: {e}")

        if failed:
            return {"success": False, "message": f"部分依赖安装失败: {', '.join(failed)}"}
        return {"success": True, "message": "所有依赖安装成功"}

    # ==================== 远程插件获取 ====================

    def _fetch_remote_plugin(self, name: str, source_url: str = None) -> Optional[Dict[str, Any]]:
        """
        从远程仓库获取插件信息

        Args:
            name: 插件名称
            source_url: 指定仓库URL

        Returns:
            插件数据字典，未找到返回None
        """
        import urllib.request
        import urllib.error

        targets = [source_url] if source_url else self._remotes

        for repo_url in targets:
            try:
                api_url = f"{repo_url.rstrip('/')}/plugins/{name}"
                req = urllib.request.Request(api_url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                data["repo_url"] = repo_url
                return data
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue
                logger.warning(f"远程获取插件失败 [{repo_url}/{name}]: {e}")
            except Exception as e:
                logger.warning(f"远程获取插件异常 [{repo_url}/{name}]: {e}")

        return None

    def _download_and_extract(self, plugin_data: Dict[str, Any]) -> str:
        """
        下载并解压插件包

        Returns:
            解压后的目录路径
        """
        import urllib.request

        download_url = plugin_data.get("download_url")
        name = plugin_data["name"]

        if not download_url:
            raise ValueError("插件数据中缺少 download_url")

        # 下载
        tmp_dir = tempfile.mkdtemp(prefix="serpentai_install_")
        zip_path = os.path.join(tmp_dir, f"{name}.zip")

        urllib.request.urlretrieve(download_url, zip_path)

        # 解压
        install_dir = os.path.join(self._plugin_install_dir, name)
        if os.path.isdir(install_dir):
            shutil.rmtree(install_dir, ignore_errors=True)
        os.makedirs(install_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(install_dir)

        # 清理临时文件
        os.remove(zip_path)

        logger.info(f"插件下载解压完成: {install_dir}")
        return install_dir


# 全局插件商店实例
_store_instance = None


def get_plugin_store() -> PluginStore:
    """获取全局插件商店实例"""
    global _store_instance
    if _store_instance is None:
        _store_instance = PluginStore()
    return _store_instance
