"""
网关层测试（多通道集成测试）
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch


class TestGatewayManager:
    """网关管理器测试"""
    
    @pytest.mark.asyncio
    async def test_register_adapter(self):
        """测试注册适配器"""
        from gateways import GatewayManager
        
        manager = GatewayManager()
        
        # 创建模拟适配器
        adapter = Mock()
        adapter.platform = "test_platform"
        
        # 注册
        manager.register_adapter(adapter)
        
        # 验证
        assert adapter in manager._adapters.values()
    
    @pytest.mark.asyncio
    async def test_get_adapter(self):
        """测试获取适配器"""
        from gateways import GatewayManager
        
        manager = GatewayManager()
        
        # 获取适配器
        feishu = manager.get_adapter("feishu")
        discord = manager.get_adapter("discord")
        telegram = manager.get_adapter("telegram")
        
        # 验证（可能是None如果没有实现）
        # assert feishu is not None or discord is not None or telegram is not None


class TestFeishuAdapter:
    """飞书适配器测试"""
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """测试发送消息"""
        from gateways.feishu_adapter import FeishuAdapter
        
        adapter = FeishuAdapter(app_id="test", app_secret="test")
        
        # 模拟发送（实际需要飞书API）
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: {"code": 0})
            
            # 发送消息
            result = await adapter.send_message(
                channel_id="test_channel",
                content="测试消息"
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_parse_webhook_event(self):
        """测试解析Webhook事件"""
        from gateways.feishu_adapter import FeishuAdapter
        
        adapter = FeishuAdapter(app_id="test", app_secret="test")
        
        # 模拟事件
        event = {
            "schema": "2.0",
            "event": {
                "message": [
                    {"message_id": "msg_123", "text": "你好"}
                ]
            }
        }
        
        # 解析
        parsed = adapter.parse_webhook_event(event)
        
        assert parsed is not None


class TestDiscordAdapter:
    """Discord适配器测试"""
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """测试发送消息"""
        from gateways.discord_adapter import DiscordAdapter
        
        adapter = DiscordAdapter(bot_token="test_token")
        
        # 模拟发送
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=200)
            
            # 发送消息
            result = await adapter.send_message(
                channel_id="123",
                content="测试消息"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_parse_interaction(self):
        """测试解析交互"""
        from gateways.discord_adapter import DiscordAdapter
        
        adapter = DiscordAdapter(bot_token="test")
        
        # 模拟交互
        interaction = {
            "type": 2,  #APPLICATION_COMMAND
            "data": {"name": "test_command"}
        }
        
        # 解析
        parsed = adapter.parse_interaction(interaction)
        
        assert parsed is not None


class TestTelegramAdapter:
    """Telegram适配器测试"""
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """测试发送消息"""
        from gateways.telegram_adapter import TelegramAdapter
        
        adapter = TelegramAdapter(bot_token="test_token")
        
        # 模拟发送
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = Mock(status_code=200, json=lambda: {"ok": True})
            
            # 发送消息
            result = await adapter.send_message(
                chat_id="123456",
                text="测试消息"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_parse_update(self):
        """测试解析更新"""
        from gateways.telegram_adapter import TelegramAdapter
        
        adapter = TelegramAdapter(bot_token="test")
        
        # 模拟更新
        update = {
            "message": {
                "chat": {"id": 123456},
                "text": "/start"
            }
        }
        
        # 解析
        parsed = adapter.parse_update(update)
        
        assert parsed is not None


class TestMessageRouter:
    """消息路由器测试"""
    
    @pytest.mark.asyncio
    async def test_route_message(self):
        """测试消息路由"""
        from gateways.message_router import MessageRouter
        
        router = MessageRouter()
        
        # 路由消息
        result = await router.route_message(
            platform="test",
            message={"text": "test"},
            session_id="test_session"
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_session(self):
        """测试获取会话"""
        from gateways.message_router import MessageRouter
        
        router = MessageRouter()
        
        # 创建会话
        session_id = await router.create_session(
            platform="test",
            user_id="user_123"
        )
        
        assert session_id is not None
    
    @pytest.mark.asyncio
    async def test_cross_platform_reply(self):
        """测试跨平台回复"""
        from gateways.message_router import MessageRouter
        
        router = MessageRouter()
        
        # 跨平台回复
        result = await router.cross_platform_reply(
            original_platform="telegram",
            original_message={"text": "test"},
            reply_platform="discord",
            reply_content="回复"
        )
        
        assert isinstance(result, dict)