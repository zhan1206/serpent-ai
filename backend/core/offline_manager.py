"""
SerpentAI 离线模式管理器
自动检测网络状态，离线时缓存消息/任务，上线后同步
"""
import socket
import logging
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import deque
import uuid

logger = logging.getLogger(__name__)


class NetworkStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class QueuedMessage:
    """离线队列消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: str = ""
    target: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0               # 优先级（0=普通，1=高，2=紧急）
    created_at: float = 0.0
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(f"{self.channel}:{self.target}:{time.time()}".encode()).hexdigest()[:12]
        if not self.created_at:
            self.created_at = time.time()


class OfflineManager:
    """
    离线模式管理器

    功能：
    - 网络状态检测（定期ping检查）
    - 离线/在线模式自动切换
    - 离线队列（离线时缓存消息/任务）
    - 上线同步（恢复网络后批量发送缓存）
    - 离线降级策略（使用本地模型/缓存响应）
    - 事件回调（on_online/on_offline）
    """

    def __init__(
        self,
        check_hosts: Optional[List[str]] = None,
        check_interval: int = 30,
        max_queue_size: int = 10000,
        auto_sync: bool = True,
    ):
        """
        初始化离线管理器

        Args:
            check_hosts: 网络检测主机列表
            check_interval: 检测间隔（秒）
            max_queue_size: 离线队列最大容量
            auto_sync: 上线后是否自动同步
        """
        self._status = NetworkStatus.UNKNOWN
        self._check_hosts = check_hosts or ["8.8.8.8", "1.1.1.1", "dns.baidu.com"]
        self._check_interval = check_interval
        self._max_queue_size = max_queue_size
        self._auto_sync = auto_sync

        self._queue: deque = deque(maxlen=max_queue_size)
        self._callbacks: Dict[str, List[Callable]] = {
            "online": [], "offline": [], "status_change": [],
        }

        self._last_check_time = 0.0
        self._last_online_time = 0.0
        self._last_offline_time = 0.0
        self._online_count = 0
        self._offline_count = 0
        self._synced_count = 0
        self._failed_sync_count = 0
        self._sync_in_progress = False

    @property
    def status(self) -> NetworkStatus:
        return self._status

    @property
    def is_online(self) -> bool:
        return self._status == NetworkStatus.ONLINE

    @property
    def is_offline(self) -> bool:
        return self._status == NetworkStatus.OFFLINE

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    def check_network(self) -> NetworkStatus:
        """
        检测当前网络状态

        Returns:
            NetworkStatus: 当前网络状态
        """
        old_status = self._status
        is_reachable = False

        for host in self._check_hosts:
            try:
                sock = socket.create_connection((host, 53), timeout=2)
                sock.close()
                is_reachable = True
                break
            except (socket.timeout, socket.error, OSError):
                continue

        new_status = NetworkStatus.ONLINE if is_reachable else NetworkStatus.OFFLINE
        self._last_check_time = time.time()

        if new_status != old_status:
            old = self._status
            self._status = new_status
            self._on_status_change(old, new_status)

        return new_status

    def _on_status_change(self, old_status: NetworkStatus, new_status: NetworkStatus):
        """处理状态变化"""
        if new_status == NetworkStatus.ONLINE:
            self._last_online_time = time.time()
            self._online_count += 1
            logger.info(f"网络已连接（离线 {(time.time() - self._last_offline_time):.0f}s）")
            self._fire_callbacks("online")
            if self._auto_sync and self._queue:
                self._fire_callbacks("status_change", {"old": old_status.value, "new": new_status.value, "pending_sync": len(self._queue)})
                self.sync_pending()
        elif new_status == NetworkStatus.OFFLINE:
            self._last_offline_time = time.time()
            self._offline_count += 1
            logger.info("网络已断开，进入离线模式")
            self._fire_callbacks("offline")
            self._fire_callbacks("status_change", {"old": old_status.value, "new": new_status.value})

        self._fire_callbacks("status_change", {"old": old_status.value, "new": new_status.value})

    def register_callback(self, event: str, callback: Callable):
        """
        注册事件回调

        Args:
            event: 事件名称（online/offline/status_change）
            callback: 回调函数
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug(f"已注册回调: {event}")

    def unregister_callback(self, event: str, callback: Callable):
        """取消事件回调"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    def _fire_callbacks(self, event: str, data: Any = None):
        """触发回调"""
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.warning(f"回调执行失败 ({event}): {e}")

    def enqueue(self, channel: str, target: str, payload: Dict[str, Any],
                priority: int = 0) -> str:
        """
        将消息加入离线队列

        Args:
            channel: 目标通道
            target: 目标地址
            payload: 消息内容
            priority: 优先级（0=普通，1=高，2=紧急）

        Returns:
            str: 消息ID
        """
        msg = QueuedMessage(
            channel=channel, target=target, payload=payload, priority=priority,
        )
        # 按优先级插入（紧急在前）
        inserted = False
        for i, existing in enumerate(self._queue):
            if existing.priority < priority:
                self._queue.insert(i, msg)
                inserted = True
                break
        if not inserted:
            self._queue.append(msg)

        logger.info(f"消息入队: {msg.id} -> {channel}:{target} (优先级={priority}, 队列长度={len(self._queue)})")
        return msg.id

    def dequeue(self) -> Optional[QueuedMessage]:
        """从队列取出下一条消息"""
        if self._queue:
            return self._queue.popleft()
        return None

    def remove_from_queue(self, message_id: str) -> bool:
        """从队列移除指定消息"""
        for i, msg in enumerate(self._queue):
            if msg.id == message_id:
                self._queue.remove(msg)
                return True
        return False

    def sync_pending(self, send_func: Optional[Callable] = None) -> Dict[str, int]:
        """
        同步离线队列（上线后批量发送）

        Args:
            send_func: 发送函数 send_func(channel, target, payload) -> bool

        Returns:
            Dict: {"synced": int, "failed": int, "remaining": int}
        """
        if self._sync_in_progress:
            return {"synced": 0, "failed": 0, "remaining": len(self._queue)}

        if not self.is_online and self._status != NetworkStatus.UNKNOWN:
            logger.warning("当前离线，无法同步")
            return {"synced": 0, "failed": 0, "remaining": len(self._queue)}

        if send_func is None:
            return {"synced": 0, "failed": 0, "remaining": len(self._queue)}

        self._sync_in_progress = True
        synced = 0
        failed = 0

        while self._queue:
            msg = self._queue[0]
            if msg.retry_count >= msg.max_retries:
                self._queue.popleft()
                self._failed_sync_count += 1
                failed += 1
                logger.warning(f"消息 {msg.id} 超过最大重试次数，丢弃")
                continue

            try:
                success = send_func(msg.channel, msg.target, msg.payload)
            except Exception as e:
                success = False
                logger.warning(f"发送消息 {msg.id} 异常: {e}")

            if success:
                self._queue.popleft()
                synced += 1
                self._synced_count += 1
            else:
                msg.retry_count += 1
                if msg.retry_count >= msg.max_retries:
                    self._queue.popleft()
                    self._failed_sync_count += 1
                    failed += 1
                else:
                    self._queue.rotate(-1)

        self._sync_in_progress = False
        result = {"synced": synced, "failed": failed, "remaining": len(self._queue)}
        if synced > 0 or failed > 0:
            logger.info(f"离线队列同步完成: {result}")
        return result

    def get_queue_messages(self, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取队列中的消息列表"""
        msgs = list(self._queue)
        if channel:
            msgs = [m for m in msgs if m.channel == channel]
        return [
            {
                "id": m.id, "channel": m.channel, "target": m.target,
                "payload": m.payload, "priority": m.priority,
                "created_at": datetime.fromtimestamp(m.created_at).isoformat(),
                "retry_count": m.retry_count,
            }
            for m in msgs
        ]

    def clear_queue(self, channel: Optional[str] = None):
        """清空离线队列"""
        if channel:
            self._queue = deque((m for m in self._queue if m.channel != channel), maxlen=self._max_queue_size)
        else:
            self._queue.clear()
        logger.info(f"离线队列已清空 (filter={channel})")

    def get_offline_fallback(self, query: str) -> Optional[str]:
        """
        离线降级策略：返回离线提示消息

        Args:
            query: 用户查询

        Returns:
            离线提示或None（在线时返回None）
        """
        if self.is_online:
            return None
        return (
            "[SerpentAI 离线模式]\n"
            f"当前网络不可用，您的消息已缓存到离线队列（队列长度: {len(self._queue)}）。\n"
            "网络恢复后将自动发送。"
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取离线管理器统计"""
        return {
            "status": self._status.value,
            "queue_size": len(self._queue),
            "max_queue_size": self._max_queue_size,
            "last_check": datetime.fromtimestamp(self._last_check_time).isoformat() if self._last_check_time else None,
            "last_online": datetime.fromtimestamp(self._last_online_time).isoformat() if self._last_online_time else None,
            "last_offline": datetime.fromtimestamp(self._last_offline_time).isoformat() if self._last_offline_time else None,
            "online_count": self._online_count,
            "offline_count": self._offline_count,
            "total_synced": self._synced_count,
            "total_failed_sync": self._failed_sync_count,
            "sync_in_progress": self._sync_in_progress,
        }
