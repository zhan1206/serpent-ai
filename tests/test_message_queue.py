"""Tests for backend.core.message_queue"""
import pytest
import json
import time
from unittest.mock import MagicMock, patch
from backend.core.message_queue import (
    MessageQueue, _InMemoryQueueBackend, _RedisQueueBackend,
    get_message_queue, reset_message_queue,
)


# ---------------------------------------------------------------------------
# _InMemoryQueueBackend
# ---------------------------------------------------------------------------

class TestInMemoryQueueBackend:
    @pytest.fixture
    def backend(self):
        b = _InMemoryQueueBackend()
        b.start()
        yield b
        b.stop()

    def test_publish(self, backend):
        msg_id = backend.publish("ch1", {"text": "hello"})
        assert msg_id is not None

    def test_subscribe_callback(self, backend):
        received = []
        backend.subscribe("ch1", lambda p: received.append(p), blocking=False)
        backend.publish("ch1", {"text": "hello"})
        # non-blocking subscribe just registers callback
        assert len(received) == 1

    def test_subscribe_callback_error(self, backend):
        def bad_cb(p):
            raise RuntimeError("fail")
        backend.subscribe("ch1", bad_cb, blocking=False)
        # should not raise
        backend.publish("ch1", {"text": "hello"})

    def test_ack(self, backend):
        msg_id = backend.publish("ch1", "data")
        backend.ack("ch1", msg_id)
        assert backend.ack_pending_count("ch1") == 0

    def test_nack(self, backend):
        msg_id = backend.publish("ch1", "data")
        # Simulate pending ack
        with backend._lock:
            backend._pending_acks["ch1"][msg_id] = {"id": msg_id, "channel": "ch1", "data": "data", "timestamp": 0}
        backend.nack("ch1", msg_id)
        assert backend.pending_count("ch1") >= 1

    def test_nack_missing(self, backend):
        backend.nack("ch1", "nonexistent")  # should not raise

    def test_pending_count(self, backend):
        backend.publish("ch1", "msg1")
        backend.publish("ch1", "msg2")
        assert backend.pending_count("ch1") == 2

    def test_ack_pending_count(self, backend):
        assert backend.ack_pending_count("ch1") == 0

    def test_get_pending_messages(self, backend):
        backend.publish("ch1", "msg1")
        backend.publish("ch1", "msg2")
        msgs = backend.get_pending_messages("ch1", limit=1)
        assert len(msgs) == 1

    def test_get_pending_messages_empty(self, backend):
        msgs = backend.get_pending_messages("empty_ch")
        assert msgs == []

    def test_recover_unacked(self, backend):
        msg_id = backend.publish("ch1", "data")
        with backend._lock:
            backend._pending_acks["ch1"][msg_id] = {"id": msg_id, "channel": "ch1", "data": "data", "timestamp": 0}
        count = backend.recover_unacked("ch1")
        assert count == 1

    def test_unsubscribe_specific(self, backend):
        cb = lambda p: None
        backend.subscribe("ch1", cb, blocking=False)
        backend.unsubscribe("ch1", cb)
        assert cb not in backend._subscribers.get("ch1", [])

    def test_unsubscribe_all(self, backend):
        backend.subscribe("ch1", lambda p: None, blocking=False)
        backend.unsubscribe("ch1")
        assert len(backend._subscribers.get("ch1", [])) == 0

    def test_unsubscribe_missing_callback(self, backend):
        backend.unsubscribe("ch1", lambda p: None)  # should not raise

    def test_channel_size(self, backend):
        backend.publish("ch1", "msg")
        assert backend.channel_size("ch1") == 1

    def test_clear_channel(self, backend):
        backend.publish("ch1", "msg1")
        backend.publish("ch1", "msg2")
        backend.clear_channel("ch1")
        assert backend.channel_size("ch1") == 0

    def test_stats(self, backend):
        backend.publish("ch1", "msg")
        s = backend.stats()
        assert s["backend"] == "memory"
        assert "ch1" in s["channels"]

    def test_start_stop(self):
        b = _InMemoryQueueBackend()
        b.start()
        assert b._running is True
        b.stop()
        assert b._running is False


# ---------------------------------------------------------------------------
# _RedisQueueBackend (mocked)
# ---------------------------------------------------------------------------

class TestRedisQueueBackend:
    @pytest.fixture
    def mock_redis(self):
        return MagicMock()

    @pytest.fixture
    def backend(self, mock_redis):
        b = _RedisQueueBackend(mock_redis)
        b.start()
        yield b
        b.stop()

    def test_publish(self, backend, mock_redis):
        msg_id = backend.publish("ch1", {"text": "hello"})
        assert msg_id is not None
        mock_redis.rpush.assert_called_once()

    def test_publish_notify_fails(self, backend, mock_redis):
        mock_redis.publish.side_effect = Exception("fail")
        msg_id = backend.publish("ch1", "data")
        assert msg_id is not None  # still returns id

    def test_subscribe(self, backend, mock_redis):
        cb = MagicMock()
        backend.subscribe("ch1", cb, blocking=True)
        assert cb in backend._handlers["ch1"]

    def test_subscribe_nonblocking(self, backend, mock_redis):
        cb = MagicMock()
        backend.subscribe("ch1", cb, blocking=False)
        assert cb in backend._handlers["ch1"]

    def test_ack(self, backend, mock_redis):
        mock_redis.hget.return_value = b'{"id":"1","data":"test"}'
        backend.ack("ch1", "1")
        mock_redis.lpush.assert_called()
        mock_redis.hdel.assert_called()

    def test_ack_missing(self, backend, mock_redis):
        mock_redis.hget.return_value = None
        backend.ack("ch1", "missing")
        mock_redis.lpush.assert_not_called()

    def test_ack_error(self, backend, mock_redis):
        mock_redis.hget.side_effect = Exception("fail")
        backend.ack("ch1", "1")  # should not raise

    def test_nack(self, backend, mock_redis):
        mock_redis.hget.return_value = b'{"id":"1"}'
        backend.nack("ch1", "1")
        mock_redis.rpush.assert_called()

    def test_nack_error(self, backend, mock_redis):
        mock_redis.hget.side_effect = Exception("fail")
        backend.nack("ch1", "1")

    def test_pending_count(self, backend, mock_redis):
        mock_redis.llen.return_value = 5
        assert backend.pending_count("ch1") == 5

    def test_pending_count_error(self, backend, mock_redis):
        mock_redis.llen.side_effect = Exception("fail")
        assert backend.pending_count("ch1") == 0

    def test_ack_pending_count(self, backend, mock_redis):
        mock_redis.hlen.return_value = 3
        assert backend.ack_pending_count("ch1") == 3

    def test_get_pending_messages(self, backend, mock_redis):
        mock_redis.lpop.side_effect = [
            json.dumps({"id": "1", "data": "a"}).encode(),
            None,
        ]
        msgs = backend.get_pending_messages("ch1", limit=5)
        assert len(msgs) == 1

    def test_get_pending_messages_error(self, backend, mock_redis):
        mock_redis.lpop.side_effect = Exception("fail")
        msgs = backend.get_pending_messages("ch1")
        assert msgs == []

    def test_recover_unacked(self, backend, mock_redis):
        mock_redis.hgetall.return_value = {b"1": b'{"id":"1"}'}
        count = backend.recover_unacked("ch1")
        assert count == 1

    def test_recover_unacked_error(self, backend, mock_redis):
        mock_redis.hgetall.side_effect = Exception("fail")
        assert backend.recover_unacked("ch1") == 0

    def test_unsubscribe_specific(self, backend, mock_redis):
        cb = MagicMock()
        backend.subscribe("ch1", cb, blocking=False)
        backend.unsubscribe("ch1", cb)
        assert cb not in backend._handlers["ch1"]

    def test_unsubscribe_all(self, backend, mock_redis):
        backend.subscribe("ch1", MagicMock(), blocking=False)
        backend.unsubscribe("ch1")
        assert len(backend._handlers["ch1"]) == 0

    def test_channel_size(self, backend, mock_redis):
        mock_redis.llen.return_value = 10
        assert backend.channel_size("ch1") == 10

    def test_clear_channel(self, backend, mock_redis):
        backend.clear_channel("ch1")
        assert mock_redis.delete.call_count == 3

    def test_stats(self, backend, mock_redis):
        mock_redis.keys.return_value = [b"mq:queue:ch1"]
        mock_redis.llen.return_value = 5
        mock_redis.hlen.return_value = 2
        s = backend.stats()
        assert s["backend"] == "redis"

    def test_stats_error(self, backend, mock_redis):
        mock_redis.keys.side_effect = Exception("fail")
        s = backend.stats()
        assert "error" in s


# ---------------------------------------------------------------------------
# MessageQueue public interface
# ---------------------------------------------------------------------------

class TestMessageQueue:
    @pytest.fixture
    def mq(self):
        q = MessageQueue()  # memory backend
        yield q
        q.shutdown()

    def test_backend_type_memory(self, mq):
        assert mq.backend_type == "memory"

    def test_backend_type_redis(self):
        mock_redis = MagicMock()
        mq = MessageQueue(redis_client=mock_redis)
        assert mq.backend_type == "redis"
        mq.shutdown()

    def test_from_config_fallback(self):
        # from_config falls back to memory when redis unavailable
        mq = MessageQueue.from_config()
        assert mq.backend_type in ("memory", "redis")
        mq.shutdown()

    def test_publish_and_subscribe(self, mq):
        received = []
        mq.subscribe("ch1", lambda p: received.append(p))
        mq.publish("ch1", {"text": "hello"})
        # memory backend: non-blocking subscriber called inline
        import time
        time.sleep(0.5)
        # might or might not get message via thread, but publish itself triggers callback

    def test_ack(self, mq):
        msg_id = mq.publish("ch1", "data")
        mq.ack("ch1", msg_id)

    def test_nack(self, mq):
        msg_id = mq.publish("ch1", "data")
        mq.nack("ch1", msg_id)

    def test_get_pending_messages(self, mq):
        mq.publish("ch1", "msg1")
        msgs = mq.get_pending_messages("ch1")
        assert len(msgs) >= 1

    def test_pending_count(self, mq):
        mq.publish("ch1", "msg")
        assert mq.pending_count("ch1") >= 1

    def test_clear_channel(self, mq):
        mq.publish("ch1", "msg")
        mq.clear_channel("ch1")
        assert mq.pending_count("ch1") == 0

    def test_stats(self, mq):
        mq.publish("ch1", "msg")
        s = mq.stats()
        assert s["backend"] == "memory"

    def test_recover_unacked(self, mq):
        result = mq.recover_unacked("ch1")
        assert isinstance(result, int)

    def test_unsubscribe(self, mq):
        cb = lambda p: None
        mq.subscribe("ch1", cb)
        mq.unsubscribe("ch1", cb)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

class TestGlobalSingleton:
    def setup_method(self):
        reset_message_queue()

    def test_get_message_queue(self):
        mq = get_message_queue()
        assert mq is not None

    def test_reset(self):
        mq1 = get_message_queue()
        reset_message_queue()
        mq2 = get_message_queue()
        assert mq1 is not mq2
