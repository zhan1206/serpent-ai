"""
SerpentAI 消息队列
基于 Redis pub/sub，优雅降级到内存队列（threading.Queue）
"""
import json
import uuid
import logging
import threading
import time
from collections import defaultdict
from queue import Queue, Empty
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 内存降级后端
# ---------------------------------------------------------------------------

class _InMemoryQueueBackend:
    """Redis 不可用时的内存队列实现"""

    def __init__(self):
        self._queues: Dict[str, Queue] = defaultdict(Queue)
        self._persistent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._pending_acks: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._sub_threads: Dict[str, List[threading.Thread]] = defaultdict(list)
        self._running = False
        self._lock = threading.Lock()

    def publish(self, channel: str, message: Any) -> str:
        msg_id = str(uuid.uuid4())
        payload = {
            "id": msg_id,
            "channel": channel,
            "data": message,
            "timestamp": time.time(),
        }
        with self._lock:
            self._queues[channel].put(payload)
            self._persistent[channel].append(payload)
            # notify subscribers
            for callback in self._subscribers.get(channel, []):
                try:
                    callback(payload)
                except Exception as e:
                    logger.error(f"内存队列订阅回调异常: {e}")
        return msg_id

    def subscribe(self, channel: str, callback: Callable, blocking: bool = True):
        with self._lock:
            self._subscribers[channel].append(callback)
            if blocking:
                t = threading.Thread(target=self._consume_loop, args=(channel, callback), daemon=True)
                self._sub_threads[channel].append(t)
                t.start()

    def _consume_loop(self, channel: str, callback: Callable):
        q = self._queues[channel]
        while self._running:
            try:
                payload = q.get(timeout=1.0)
                msg_id = payload["id"]
                self._pending_acks[channel][msg_id] = payload
                try:
                    callback(payload)
                except Exception as e:
                    logger.error(f"消费回调异常 (ch={channel}): {e}")
            except Empty:
                continue

    def ack(self, channel: str, message_id: str):
        with self._lock:
            self._pending_acks[channel].pop(message_id, None)

    def nack(self, channel: str, message_id: str):
        with self._lock:
            payload = self._pending_acks[channel].pop(message_id, None)
            if payload:
                self._queues[channel].put(payload)

    def pending_count(self, channel: str) -> int:
        with self._lock:
            return self._queues[channel].qsize()

    def ack_pending_count(self, channel: str) -> int:
        with self._lock:
            return len(self._pending_acks[channel])

    def get_pending_messages(self, channel: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            q = self._queues[channel]
            msgs = []
            for _ in range(min(limit, q.qsize())):
                try:
                    msgs.append(q.get_nowait())
                except Empty:
                    break
            return msgs

    def recover_unacked(self, channel: str) -> int:
        with self._lock:
            unacked = list(self._pending_acks[channel].values())
            count = len(unacked)
            for payload in unacked:
                self._queues[channel].put(payload)
            self._pending_acks[channel].clear()
            return count

    def unsubscribe(self, channel: str, callback: Optional[Callable] = None):
        with self._lock:
            if callback:
                try:
                    self._subscribers[channel].remove(callback)
                except ValueError:
                    pass
            else:
                self._subscribers[channel].clear()

    def channel_size(self, channel: str) -> int:
        with self._lock:
            return self._queues[channel].qsize()

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def clear_channel(self, channel: str):
        with self._lock:
            while not self._queues[channel].empty():
                try:
                    self._queues[channel].get_nowait()
                except Empty:
                    break
            self._persistent[channel].clear()
            self._pending_acks[channel].clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "backend": "memory",
            "channels": {ch: self._queues[ch].qsize() for ch in self._queues if self._queues[ch].qsize() > 0},
            "total_pending": sum(q.qsize() for q in self._queues.values()),
            "total_unacked": sum(len(p) for p in self._pending_acks.values()),
        }


# ---------------------------------------------------------------------------
# Redis 后端
# ---------------------------------------------------------------------------

class _RedisQueueBackend:
    """基于 Redis pub/sub + List 的消息队列实现"""

    def __init__(self, redis_client):
        self._redis = redis_client
        self._pubsub = self._redis.pubsub()
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._sub_threads: Dict[str, List[threading.Thread]] = defaultdict(list)
        self._running = False
        self._lock = threading.Lock()

    def _queue_key(self, channel: str) -> str:
        return f"mq:queue:{channel}"

    def _ack_key(self, channel: str) -> str:
        return f"mq:pending:{channel}"

    def _processed_key(self, channel: str) -> str:
        return f"mq:processed:{channel}"

    def publish(self, channel: str, message: Any) -> str:
        msg_id = str(uuid.uuid4())
        payload = {
            "id": msg_id,
            "channel": channel,
            "data": message,
            "timestamp": time.time(),
        }
        payload_str = json.dumps(payload, ensure_ascii=False, default=str)
        # persist to list
        self._redis.rpush(self._queue_key(channel), payload_str)
        # pub/sub notify
        try:
            self._redis.publish(channel, payload_str)
        except Exception as e:
            logger.warning(f"Redis publish 通知失败: {e}")
        return msg_id

    def subscribe(self, channel: str, callback: Callable, blocking: bool = True):
        with self._lock:
            self._handlers[channel].append(callback)
            if blocking:
                # start a thread to listen on pub/sub
                t = threading.Thread(target=self._listen_loop, args=(channel,), daemon=True)
                self._sub_threads[channel].append(t)
                t.start()

    def _listen_loop(self, channel: str):
        ps = self._redis.pubsub()
        try:
            ps.subscribe(channel)
            for item in ps.listen():
                if not self._running:
                    break
                if item["type"] != "message":
                    continue
                try:
                    payload = json.loads(item["data"])
                    msg_id = payload["id"]
                    # move to pending
                    self._redis.hset(self._ack_key(channel), msg_id, item["data"])
                    for handler in self._handlers.get(channel, []):
                        try:
                            handler(payload)
                        except Exception as e:
                            logger.error(f"Redis 消费回调异常 (ch={channel}): {e}")
                except Exception as e:
                    logger.error(f"Redis 消息解析失败: {e}")
        except Exception as e:
            logger.error(f"Redis pub/sub 监听异常: {e}")
        finally:
            try:
                ps.unsubscribe(channel)
                ps.close()
            except Exception:
                pass

    def ack(self, channel: str, message_id: str):
        try:
            data = self._redis.hget(self._ack_key(channel), message_id)
            if data:
                # move to processed
                self._redis.lpush(self._processed_key(channel), data)
                self._redis.hdel(self._ack_key(channel), message_id)
        except Exception as e:
            logger.error(f"Redis ACK 失败: {e}")

    def nack(self, channel: str, message_id: str):
        try:
            data = self._redis.hget(self._ack_key(channel), message_id)
            if data:
                # re-queue
                self._redis.rpush(self._queue_key(channel), data)
                self._redis.hdel(self._ack_key(channel), message_id)
        except Exception as e:
            logger.error(f"Redis NACK 失败: {e}")

    def pending_count(self, channel: str) -> int:
        try:
            return self._redis.llen(self._queue_key(channel))
        except Exception:
            return 0

    def ack_pending_count(self, channel: str) -> int:
        try:
            return self._redis.hlen(self._ack_key(channel))
        except Exception:
            return 0

    def get_pending_messages(self, channel: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            results = []
            for _ in range(limit):
                data = self._redis.lpop(self._queue_key(channel))
                if data is None:
                    break
                payload = json.loads(data)
                self._redis.hset(self._ack_key(channel), payload["id"], data)
                results.append(payload)
            return results
        except Exception as e:
            logger.error(f"Redis 获取待处理消息失败: {e}")
            return []

    def recover_unacked(self, channel: str) -> int:
        try:
            pending_data = self._redis.hgetall(self._ack_key(channel))
            count = 0
            for msg_id, data in pending_data.items():
                if isinstance(msg_id, bytes):
                    msg_id = msg_id.decode()
                self._redis.rpush(self._queue_key(channel), data)
                self._redis.hdel(self._ack_key(channel), msg_id)
                count += 1
            return count
        except Exception as e:
            logger.error(f"Redis 恢复未确认消息失败: {e}")
            return 0

    def unsubscribe(self, channel: str, callback: Optional[Callable] = None):
        with self._lock:
            if callback:
                try:
                    self._handlers[channel].remove(callback)
                except ValueError:
                    pass
            else:
                self._handlers[channel].clear()

    def channel_size(self, channel: str) -> int:
        return self.pending_count(channel)

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
        try:
            self._pubsub.unsubscribe()
            self._pubsub.close()
        except Exception:
            pass

    def clear_channel(self, channel: str):
        try:
            self._redis.delete(self._queue_key(channel))
            self._redis.delete(self._ack_key(channel))
            self._redis.delete(self._processed_key(channel))
        except Exception as e:
            logger.error(f"Redis 清空频道失败: {e}")

    def stats(self) -> Dict[str, Any]:
        try:
            keys = self._redis.keys("mq:queue:*")
            channels = {}
            total = 0
            for key in keys:
                ch = key.decode().replace("mq:queue:", "") if isinstance(key, bytes) else key.replace("mq:queue:", "")
                size = self._redis.llen(key)
                if size > 0:
                    channels[ch] = size
                    total += size
            return {
                "backend": "redis",
                "channels": channels,
                "total_pending": total,
                "total_unacked": sum(self.ack_pending_count(ch) for ch in channels),
            }
        except Exception as e:
            return {"backend": "redis", "error": str(e)}


# ---------------------------------------------------------------------------
# MessageQueue 公共接口
# ---------------------------------------------------------------------------

class MessageQueue:
    """
    消息队列：Redis 优先，内存队列优雅降级。
    支持 pub/sub、消息持久化、ACK 确认、频道隔离。
    """

    def __init__(self, redis_client=None):
        if redis_client is not None:
            self._backend: Any = _RedisQueueBackend(redis_client)
            self._backend_type = "redis"
            logger.info("消息队列使用 Redis 后端")
        else:
            self._backend = _InMemoryQueueBackend()
            self._backend_type = "memory"
            logger.info("消息队列使用内存后端（Redis 不可用）")
        self._backend.start()

    @classmethod
    def from_config(cls) -> "MessageQueue":
        """尝试连接 Redis，失败则降级"""
        try:
            import redis
            from backend.core.config import settings
            client = redis.Redis(
                host=getattr(settings, "REDIS_HOST", "localhost"),
                port=getattr(settings, "REDIS_PORT", 6379),
                db=getattr(settings, "REDIS_DB", 0),
                password=getattr(settings, "REDIS_PASSWORD", None),
                decode_responses=False,
                socket_timeout=2,
            )
            client.ping()
            return cls(redis_client=client)
        except Exception as e:
            logger.warning(f"Redis 连接失败，降级到内存队列: {e}")
        return cls()

    @property
    def backend_type(self) -> str:
        return self._backend_type

    def publish(self, channel: str, message: Any) -> str:
        """发布消息到频道，返回消息 ID"""
        return self._backend.publish(channel, message)

    def subscribe(self, channel: str, callback: Callable) -> None:
        """订阅频道，收到消息时调用 callback(payload)"""
        self._backend.subscribe(channel, callback, blocking=True)

    def unsubscribe(self, channel: str, callback: Optional[Callable] = None) -> None:
        """取消订阅"""
        self._backend.unsubscribe(channel, callback)

    def ack(self, channel: str, message_id: str) -> None:
        """确认消息已处理"""
        self._backend.ack(channel, message_id)

    def nack(self, channel: str, message_id: str) -> None:
        """拒绝消息，重新入队"""
        self._backend.nack(channel, message_id)

    def get_pending_messages(self, channel: str, limit: int = 10) -> List[Dict[str, Any]]:
        """主动拉取待处理消息（消费者模式）"""
        return self._backend.get_pending_messages(channel, limit)

    def pending_count(self, channel: str) -> int:
        """获取频道待处理消息数"""
        return self._backend.pending_count(channel)

    def ack_pending_count(self, channel: str) -> int:
        """获取频道未确认消息数"""
        return self._backend.ack_pending_count(channel)

    def recover_unacked(self, channel: str) -> int:
        """恢复所有未确认消息到待处理队列"""
        return self._backend.recover_unacked(channel)

    def clear_channel(self, channel: str) -> None:
        """清空频道所有消息"""
        self._backend.clear_channel(channel)

    def stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return self._backend.stats()

    def shutdown(self):
        """关闭队列"""
        self._backend.stop()


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_message_queue_instance: Optional[MessageQueue] = None
_message_queue_lock = threading.Lock()


def get_message_queue() -> MessageQueue:
    global _message_queue_instance
    if _message_queue_instance is None:
        with _message_queue_lock:
            if _message_queue_instance is None:
                _message_queue_instance = MessageQueue.from_config()
    return _message_queue_instance


def reset_message_queue():
    global _message_queue_instance
    if _message_queue_instance:
        _message_queue_instance.shutdown()
    _message_queue_instance = None
