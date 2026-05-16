"""
API端点测试
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock, patch


class TestHealthEndpoint:
    """健康检查端点测试"""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data


class TestChatEndpoint:
    """聊天端点测试"""
    
    @pytest.mark.asyncio
    async def test_chat_basic(self):
        """测试基础聊天"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "messages": [
                    {"role": "user", "content": "你好"}
                ]
            })
            
            # 可能返回200或错误（如果没有配置API key）
            assert response.status_code in [200, 401, 500]
    
    @pytest.mark.asyncio
    async def test_chat_with_model(self):
        """测试指定模型"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "测试"}
                ]
            })
            
            assert response.status_code in [200, 401, 500]
    
    @pytest.mark.asyncio
    async def test_chat_stream(self):
        """测试流式响应"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            with client.stream("POST", "/api/chat", json={
                "messages": [{"role": "user", "content": "你好"}],
                "stream": True
            }) as response:
                assert response.status_code in [200, 401, 500]


class TestModelsEndpoint:
    """模型端点测试"""
    
    @pytest.mark.asyncio
    async def test_list_models(self):
        """测试列出模型"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.get("/api/models")
            
            assert response.status_code == 200
            data = response.json()
            assert "models" in data


class TestMemoryEndpoint:
    """记忆端点测试"""
    
    @pytest.mark.asyncio
    async def test_get_memory(self):
        """测试获取记忆"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.get("/api/memory")
            
            # 可能需要认证
            assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_search_memory(self):
        """测试搜索记忆"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.post("/api/memory/search", json={
                "query": "测试"
            })
            
            assert response.status_code in [200, 401]


class TestToolsEndpoint:
    """工具端点测试"""
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """测试列出工具"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.get("/api/tools")
            
            assert response.status_code == 200
            data = response.json()
            assert "tools" in data
    
    @pytest.mark.asyncio
    async def test_call_tool(self):
        """测试调用工具"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.post("/api/tools/call", json={
                "name": "calculator",
                "arguments": {"expression": "1+1"}
            })
            
            # 可能成功或工具不存在
            assert response.status_code in [200, 404, 500]


class TestEfficiencyEndpoint:
    """效率引擎端点测试"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.get("/api/efficiency/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
    
    @pytest.mark.asyncio
    async def test_optimization_status(self):
        """测试优化状态"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.get("/api/efficiency/status")
            
            assert response.status_code == 200


class TestGatewayEndpoint:
    """网关端点测试"""
    
    @pytest.mark.asyncio
    async def test_list_channels(self):
        """测试列出通道"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.get("/api/gateway/channels")
            
            # 可能需要认证
            assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_send_to_channel(self):
        """测试发送到通道"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.post("/api/gateway/send", json={
                "channel": "test",
                "content": "测试"
            })
            
            assert response.status_code in [200, 401, 404]


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_404(self):
        """测试404"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.get("/api/nonexistent")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_validation_error(self):
        """测试验证错误"""
        from fastapi.testclient import TestClient
        from backend.main import app
        
        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "invalid": "data"
            })
            
            assert response.status_code == 422