# -*- coding: utf-8 -*-
"""
提醒插件 - 提醒和定时任务管理
支持一次性提醒和周期性提醒
"""

import time
import threading
import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from backend.plugins.plugin_base import ToolPlugin
from backend.plugins.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

# 存储文件路径
_REMINDERS_FILE = "data/reminders.json"


class Reminder:
    """提醒条目"""
    
    def __init__(self, reminder_id: str, content: str, trigger_time: str,
                 recurring: str = None, created_at: str = None,
                 triggered: bool = False):
        self.id = reminder_id
        self.content = content
        self.trigger_time = trigger_time
        self.recurring = recurring  # cron 表达式或 None
        self.created_at = created_at or datetime.now().isoformat()
        self.triggered = triggered
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "trigger_time": self.trigger_time,
            "recurring": self.recurring,
            "created_at": self.created_at,
            "triggered": self.triggered,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Reminder":
        return cls(
            reminder_id=data["id"],
            content=data["content"],
            trigger_time=data["trigger_time"],
            recurring=data.get("recurring"),
            created_at=data.get("created_at"),
            triggered=data.get("triggered", False),
        )


class ReminderPlugin(ToolPlugin):
    """提醒插件"""
    
    def __init__(self, manifest: PluginManifest):
        super().__init__(manifest)
        self._reminders: Dict[str, Reminder] = {}
        self._callbacks: List = []
        self._running = False
        self._check_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._counter = 0
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "create_reminder",
                "description": "创建提醒。支持相对时间（如 '5m', '1h', '30m'）和绝对时间（如 '2025-01-01 09:00'）。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "提醒内容"
                        },
                        "trigger_time": {
                            "type": "string",
                            "description": "触发时间。相对时间（5m=5分钟, 1h=1小时, 1h30m=1.5小时, 1d=1天）或绝对时间（YYYY-MM-DD HH:MM）"
                        },
                        "recurring": {
                            "type": "string",
                            "description": "周期表达式（可选），如 'daily', 'weekly', '0 9 * * *'（cron格式）"
                        }
                    },
                    "required": ["content", "trigger_time"]
                },
                "handler": self._handle_create_reminder,
                "category": "reminder"
            },
            {
                "name": "list_reminders",
                "description": "列出所有提醒",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "include_triggered": {
                            "type": "boolean",
                            "description": "是否包含已触发的提醒（默认false）",
                            "default": False
                        }
                    }
                },
                "handler": self._handle_list_reminders,
                "category": "reminder"
            },
            {
                "name": "delete_reminder",
                "description": "删除提醒",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "reminder_id": {
                            "type": "string",
                            "description": "提醒ID"
                        }
                    },
                    "required": ["reminder_id"]
                },
                "handler": self._handle_delete_reminder,
                "category": "reminder"
            },
        ]
    
    def on_start(self):
        """启动时开始检查线程"""
        super().on_start()
        self._load_reminders()
        self._running = True
        self._check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self._check_thread.start()
        self._logger.info("提醒检查线程已启动")
    
    def on_stop(self):
        """停止检查线程"""
        self._running = False
        self._save_reminders()
        super().on_stop()
    
    def _parse_trigger_time(self, time_str: str) -> datetime:
        """解析触发时间"""
        now = datetime.now()
        
        # 相对时间模式
        rel_match = __import__("re").match(r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?$", time_str.strip())
        if rel_match:
            days = int(rel_match.group(1) or 0)
            hours = int(rel_match.group(2) or 0)
            minutes = int(rel_match.group(3) or 0)
            if days or hours or minutes:
                return now + timedelta(days=days, hours=hours, minutes=minutes)
        
        # 绝对时间
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%H:%M", "%H:%M:%S"]:
            try:
                dt = datetime.strptime(time_str.strip(), fmt)
                if fmt.startswith("%H"):
                    dt = dt.replace(year=now.year, month=now.month, day=now.day)
                    if dt < now:
                        dt += timedelta(days=1)
                return dt
            except ValueError:
                continue
        
        raise ValueError(f"无法解析时间: {time_str}")
    
    def _handle_create_reminder(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._counter += 1
            rid = f"rem_{self._counter:04d}_{int(time.time())}"
            
            try:
                trigger_dt = self._parse_trigger_time(arguments["trigger_time"])
            except ValueError as e:
                return {"error": str(e)}
            
            reminder = Reminder(
                reminder_id=rid,
                content=arguments["content"],
                trigger_time=trigger_dt.isoformat(),
                recurring=arguments.get("recurring"),
            )
            
            self._reminders[rid] = reminder
            self._save_reminders()
            
            return {
                "id": rid,
                "content": reminder.content,
                "trigger_time": reminder.trigger_time,
                "remaining": str(trigger_dt - datetime.now()).split(".")[0],
                "recurring": reminder.recurring,
                "message": f"提醒已创建: {reminder.content} ({reminder.trigger_time})",
            }
    
    def _handle_list_reminders(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        include_triggered = arguments.get("include_triggered", False)
        reminders = []
        
        with self._lock:
            for r in self._reminders.values():
                if not include_triggered and r.triggered:
                    continue
                reminders.append(r.to_dict())
        
        reminders.sort(key=lambda x: x["trigger_time"])
        return {"reminders": reminders, "count": len(reminders)}
    
    def _handle_delete_reminder(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rid = arguments["reminder_id"]
        with self._lock:
            if rid in self._reminders:
                del self._reminders[rid]
                self._save_reminders()
                return {"message": f"提醒已删除: {rid}"}
            return {"error": f"提醒不存在: {rid}"}
    
    def _check_loop(self):
        """定期检查提醒"""
        while self._running:
            try:
                now = datetime.now()
                with self._lock:
                    for reminder in list(self._reminders.values()):
                        if reminder.triggered:
                            continue
                        trigger_dt = datetime.fromisoformat(reminder.trigger_time)
                        if now >= trigger_dt:
                            reminder.triggered = True
                            self._logger.info(f"提醒触发: {reminder.content}")
                            self._save_reminders()
            except Exception as e:
                self._logger.error(f"提醒检查错误: {e}")
            
            time.sleep(10)
    
    def _save_reminders(self):
        """保存提醒到文件"""
        try:
            os.makedirs(os.path.dirname(_REMINDERS_FILE), exist_ok=True)
            data = [r.to_dict() for r in self._reminders.values()]
            with open(_REMINDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._logger.error(f"保存提醒失败: {e}")
    
    def _load_reminders(self):
        """从文件加载提醒"""
        if not os.path.exists(_REMINDERS_FILE):
            return
        try:
            with open(_REMINDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                r = Reminder.from_dict(item)
                self._reminders[r.id] = r
            self._counter = max((int(r.id.split("_")[1]) for r in self._reminders.values()), default=0)
        except Exception as e:
            self._logger.error(f"加载提醒失败: {e}")


def create_plugin(manifest: PluginManifest) -> ReminderPlugin:
    return ReminderPlugin(manifest)
