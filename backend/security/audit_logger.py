"""
SerpentAI 安全模块 - 审计日志 (Layer 5)
完整的操作审计和安全事件记录
"""

import json
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import threading
import queue

logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    # 安全特定级别
    SECURITY_BLOCK = "SECURITY_BLOCK"  # 安全拦截
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    ACCESS_DENIED = "ACCESS_DENIED"
    DATA_ACCESS = "DATA_ACCESS"
    DATA_MODIFICATION = "DATA_MODIFICATION"
    SYSTEM_CHANGE = "SYSTEM_CHANGE"


class AuditEventType(Enum):
    """审计事件类型"""
    # 认证事件
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_CREATED = "token_created"
    TOKEN_REVOKED = "token_revoked"
    
    # 授权事件
    ACCESS_DENIED = "access_denied"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    
    # 数据事件
    DATA_READ = "data_read"
    DATA_CREATED = "data_created"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    
    # 安全事件
    SECURITY_BLOCK = "security_block"
    INJECTION_ATTEMPT = "injection_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SESSION_HIJACK = "session_hijack"
    
    # 系统事件
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGED = "config_changed"
    ERROR = "error"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    timestamp: datetime
    event_type: str
    level: str
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    action: str
    resource: Optional[str]
    result: str  # success, failure, denied, blocked
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "level": self.level,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "details": self.details,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    审计日志器 - 第五层防御
    功能：
    1. 记录所有安全相关事件
    2. 实时告警
    3. 日志持久化
    4. 查询和分析
    """
    
    def __init__(self, log_dir: str = "./logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存存储（最近的审计事件）
        self._events: List[AuditEvent] = []
        self._max_events = 10000
        
        # 事件队列（异步写入）
        self._event_queue: queue.Queue = queue.Queue()
        self._writer_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 告警规则
        self._alert_rules: List[Dict] = []
        
        # 事件统计
        self._stats: Dict[str, int] = {}
        
        # 文件锁
        self._file_lock = threading.Lock()
        
        logger.info("审计日志器初始化完成")
    
    def start(self):
        """启动异步写入线程"""
        if self._running:
            return
        
        self._running = True
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer_thread.start()
        logger.info("审计日志写入线程已启动")
    
    def stop(self):
        """停止异步写入"""
        self._running = False
        if self._writer_thread:
            self._writer_thread.join(timeout=5)
        logger.info("审计日志写入线程已停止")
    
    def _writer_loop(self):
        """异步写入循环"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=1)
                self._write_to_file(event)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"审计日志写入失败: {e}")
    
    def _write_to_file(self, event: AuditEvent):
        """写入日志文件"""
        with self._file_lock:
            try:
                # 按日期分文件
                date_str = event.timestamp.strftime("%Y-%m-%d")
                log_file = self.log_dir / f"audit_{date_str}.jsonl"
                
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(event.to_json() + "\n")
                
            except Exception as e:
                logger.error(f"写入审计日志失败: {e}")
    
    def log(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        action: str = "",
        resource: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict] = None,
        level: AuditLevel = AuditLevel.INFO,
        metadata: Optional[Dict] = None
    ) -> AuditEvent:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            session_id: 会话ID
            ip_address: IP地址
            action: 操作描述
            resource: 资源路径
            result: 结果 (success/failure/denied/blocked)
            details: 详细信息
            level: 审计级别
            metadata: 元数据
        
        Returns:
            AuditEvent: 审计事件
        """
        import secrets
        
        event = AuditEvent(
            event_id=secrets.token_urlsafe(16),
            timestamp=datetime.now(),
            event_type=event_type,
            level=level.value if isinstance(level, AuditLevel) else level,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            metadata=metadata or {}
        )
        
        # 存入内存
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        
        # 更新统计
        self._stats[event_type] = self._stats.get(event_type, 0) + 1
        
        # 检查告警规则
        self._check_alerts(event)
        
        # 异步写入文件
        if self._running:
            self._event_queue.put(event)
        
        return event
    
    def _check_alerts(self, event: AuditEvent):
        """检查是否触发告警"""
        for rule in self._alert_rules:
            if self._matches_rule(event, rule):
                self._trigger_alert(event, rule)
    
    def _matches_rule(self, event: AuditEvent, rule: Dict) -> bool:
        """检查事件是否匹配规则"""
        # 检查事件类型
        if "event_types" in rule and event.event_type not in rule["event_types"]:
            return False
        
        # 检查级别
        if "min_level" in rule:
            levels = list(AuditLevel)
            event_level_idx = levels.index(AuditLevel(event.level)) if event.level in [l.value for l in levels] else 0
            min_level_idx = levels.index(AuditLevel(rule["min_level"])) if rule["min_level"] in [l.value for l in levels] else 0
            if event_level_idx < min_level_idx:
                return False
        
        # 检查用户
        if "user_ids" in rule and event.user_id not in rule["user_ids"]:
            return False
        
        # 检查结果
        if "results" in rule and event.result not in rule["results"]:
            return False
        
        return True
    
    def _trigger_alert(self, event: AuditEvent, rule: Dict):
        """触发告警"""
        alert_msg = f"安全告警 [{rule.get('name', 'Unknown')}] - {event.event_type}: {event.action}"
        
        if rule.get("level") == "critical":
            logger.critical(alert_msg)
        elif rule.get("level") == "error":
            logger.error(alert_msg)
        else:
            logger.warning(alert_msg)
    
    def add_alert_rule(self, rule: Dict):
        """添加告警规则"""
        self._alert_rules.append(rule)
        logger.info(f"告警规则已添加: {rule.get('name', 'Unknown')}")
    
    # ==================== 查询接口 ====================
    
    def get_events(
        self,
        event_type: str = None,
        user_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """查询审计事件"""
        events = self._events.copy()
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        return events[-limit:]
    
    def get_user_activity(self, user_id: str, limit: int = 50) -> List[AuditEvent]:
        """获取用户活动历史"""
        return self.get_events(user_id=user_id, limit=limit)
    
    def get_security_events(self, hours: int = 24) -> List[AuditEvent]:
        """获取最近的安全事件"""
        from datetime import timedelta
        start_time = datetime.now() - timedelta(hours=hours)
        
        security_types = [
            AuditEventType.SECURITY_BLOCK.value,
            AuditEventType.INJECTION_ATTEMPT.value,
            AuditEventType.ACCESS_DENIED.value,
            AuditEventType.LOGIN_FAILED.value,
        ]
        
        events = []
        for event in self._events:
            if event.timestamp >= start_time and event.event_type in security_types:
                events.append(event)
        
        return events
    
    def get_failed_logins(self, hours: int = 24) -> List[AuditEvent]:
        """获取失败的登录尝试"""
        return self.get_events(
            event_type=AuditEventType.LOGIN_FAILED.value,
            limit=100
        )
    
    # ==================== 统计接口 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取审计统计"""
        return {
            "total_events": len(self._events),
            "event_counts": self._stats.copy(),
            "alert_rules_count": len(self._alert_rules),
            "queue_size": self._event_queue.qsize(),
            "writer_running": self._running
        }
    
    def get_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取审计摘要"""
        from datetime import timedelta
        start_time = datetime.now() - timedelta(hours=hours)
        
        recent_events = [e for e in self._events if e.timestamp >= start_time]
        
        # 统计各类型事件
        event_type_counts = {}
        user_activity = {}
        
        for event in recent_events:
            event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1
            
            if event.user_id:
                user_activity[event.user_id] = user_activity.get(event.user_id, 0) + 1
        
        # 统计结果
        results = {"success": 0, "failure": 0, "denied": 0, "blocked": 0}
        for event in recent_events:
            if event.result in results:
                results[event.result] += 1
        
        return {
            "period_hours": hours,
            "total_events": len(recent_events),
            "event_type_counts": event_type_counts,
            "top_users": sorted(user_activity.items(), key=lambda x: -x[1])[:10],
            "result_summary": results,
            "unique_users": len(user_activity),
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    def export_to_file(self, output_path: str, event_type: str = None, limit: int = None):
        """导出审计日志到文件"""
        events = self.get_events(event_type=event_type, limit=limit or 10000)
        
        output_file = Path(output_path)
        
        with open(output_file, "w", encoding="utf-8") as f:
            for event in events:
                f.write(event.to_json() + "\n")
        
        logger.info(f"审计日志已导出到: {output_path}")
        return len(events)
