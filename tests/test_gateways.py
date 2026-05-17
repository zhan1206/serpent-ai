"""
网关层测试（多通道集成测试）
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch


class TestGatewayManager:
    """网关管理器测试"""

    def test_create_manager(self):
        """测试创建管理器"""
        from gateways import GatewayManager

        manager = GatewayManager()
        assert manager is not None
        assert isinstance(manager.adapters, dict)

    def test_get_instance(self):
        """测试单例获取"""
        from gateways import GatewayManager

        manager1 = GatewayManager.get_instance()
        manager2 = GatewayManager.get_instance()
        assert manager1 is manager2

    def test_create_adapter_feishu(self):
        """测试创建飞书适配器"""
        from gateways import GatewayManager

        manager = GatewayManager()
        adapter = manager._create_adapter("feishu", {"enabled": False})
        assert adapter is not None

    def test_create_adapter_discord(self):
        """测试创建Discord适配器"""
        from gateways import GatewayManager

        manager = GatewayManager()
        adapter = manager._create_adapter("discord", {"enabled": False})
        assert adapter is not None

    def test_create_adapter_telegram(self):
        """测试创建Telegram适配器"""
        from gateways import GatewayManager

        manager = GatewayManager()
        adapter = manager._create_adapter("telegram", {"enabled": False})
        assert adapter is not None

    def test_create_adapter_unsupported(self):
        """测试不支持的适配器"""
        from gateways import GatewayManager

        manager = GatewayManager()
        adapter = manager._create_adapter("unsupported", {})
        assert adapter is None


class TestFeishuAdapter:
    """飞书适配器测试"""

    def test_create_adapter(self):
        """测试创建适配器"""
        from gateways.feishu_adapter import FeishuAdapter

        adapter = FeishuAdapter(config={"app_id": "test", "app_secret": "test", "enabled": False})
        assert adapter is not None
        assert adapter.platform_name == "feishu"

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        from gateways.feishu_adapter import FeishuAdapter

        adapter = FeishuAdapter(config={"app_id": "test", "app_secret": "test", "enabled": False})
        health = await adapter.health_check()
        assert "platform" in health


class TestDiscordAdapter:
    """Discord适配器测试"""

    def test_create_adapter(self):
        """测试创建适配器"""
        from gateways.discord_adapter import DiscordAdapter

        adapter = DiscordAdapter(config={"bot_token": "test_token", "enabled": False})
        assert adapter is not None
        assert adapter.platform_name == "discord"

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        from gateways.discord_adapter import DiscordAdapter

        adapter = DiscordAdapter(config={"bot_token": "test", "enabled": False})
        health = await adapter.health_check()
        assert "platform" in health


class TestTelegramAdapter:
    """Telegram适配器测试"""

    def test_create_adapter(self):
        """测试创建适配器"""
        from gateways.telegram_adapter import TelegramAdapter

        adapter = TelegramAdapter(config={"bot_token": "test_token", "enabled": False})
        assert adapter is not None
        assert adapter.platform_name == "telegram"

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        from gateways.telegram_adapter import TelegramAdapter

        adapter = TelegramAdapter(config={"bot_token": "test", "enabled": False})
        health = await adapter.health_check()
        assert "platform" in health


class TestMessageRouter:
    """消息路由器测试"""

    def test_create_router(self):
        """测试创建路由器"""
        from gateways.message_router import MessageRouter

        router = MessageRouter()
        assert router is not None

    def test_register_handler(self):
        """测试注册处理器"""
        from gateways.message_router import MessageRouter

        router = MessageRouter()

        async def handler(msg):
            return None

        router.register_handler("test_platform", handler)
        assert "test_platform" in router.handlers

    def test_set_fallback_handler(self):
        """测试设置默认处理器"""
        from gateways.message_router import MessageRouter

        router = MessageRouter()

        async def fallback(msg):
            return None

        router.set_fallback_handler(fallback)
        assert router.fallback_handler is not None

    @pytest.mark.asyncio
    async def test_route_message(self):
        """测试消息路由"""
        from gateways.message_router import MessageRouter
        from gateways import Message

        router = MessageRouter()
        routed = []

        async def handler(msg):
            routed.append(msg)
            from gateways import Response
            return Response(message="ok")

        router.register_handler("test", handler)

        msg = Message(
            msg_id="1", platform="test", msg_type="text",
            content="hello", sender={"id": "u1"}
        )
        result = await router.route(msg)
        assert result is not None
        assert len(routed) == 1

    @pytest.mark.asyncio
    async def test_route_no_handler(self):
        """测试无处理器时的路由"""
        from gateways.message_router import MessageRouter
        from gateways import Message

        router = MessageRouter()

        msg = Message(
            msg_id="1", platform="unknown", msg_type="text",
            content="hello", sender={"id": "u1"}
        )
        result = await router.route(msg)
        assert result is None


class TestGatewayMessages:
    """网关消息模型测试"""

    def test_message_creation(self):
        """测试消息创建"""
        from gateways import Message

        msg = Message(
            msg_id="1", platform="test", msg_type="text",
            content="hello", sender={"id": "u1"}
        )
        assert msg.msg_id == "1"
        assert msg.content == "hello"

    def test_message_to_dict(self):
        """测试消息转字典"""
        from gateways import Message

        msg = Message(
            msg_id="1", platform="test", msg_type="text",
            content="hello", sender={"id": "u1"}
        )
        d = msg.to_dict()
        assert "msg_id" in d
        assert "content" in d

    def test_response_creation(self):
        """测试响应创建"""
        from gateways import Response

        resp = Response(message="test reply")
        assert resp.message == "test reply"
        assert resp.msg_type == "text"
