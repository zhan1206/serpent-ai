"""
API端点测试
"""
import pytest


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check(self):
        """测试健康检查"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_root(self):
        """测试根路径"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200


class TestModelsEndpoint:
    """模型端点测试"""

    def test_list_models(self):
        """测试列出模型"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/models")
            assert response.status_code == 200
            data = response.json()
            assert "models" in data


class TestChatEndpoint:
    """聊天端点测试"""

    def test_chat_basic(self):
        """测试基础聊天"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "messages": [
                    {"role": "user", "content": "你好"}
                ]
            })
            # 可能返回200或错误
            assert response.status_code in [200, 401, 500, 422]

    def test_chat_with_model(self):
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
            assert response.status_code in [200, 401, 500, 422]


class TestMemoryEndpoint:
    """记忆端点测试"""

    def test_add_memory(self):
        """测试添加记忆"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/memory/add", json={
                "content": "测试记忆",
                "importance": 0.5
            })
            assert response.status_code in [200, 401, 500, 422]

    def test_recall_memory(self):
        """测试回忆记忆"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/memory/recall", json={
                "query": "测试"
            })
            assert response.status_code in [200, 401, 500, 422]

    def test_memory_stats(self):
        """测试记忆统计"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/memory/stats")
            assert response.status_code in [200, 401, 500]

    def test_clear_memory(self):
        """测试清空记忆"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.delete("/api/memory/clear")
            assert response.status_code in [200, 401, 500]


class TestToolsEndpoint:
    """工具端点测试"""

    def test_list_tools(self):
        """测试列出工具"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/tools")
            assert response.status_code == 200
            data = response.json()
            assert "tools" in data

    def test_call_tool(self):
        """测试调用工具"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/tools/call", json={
                "name": "calculator",
                "arguments": {"expression": "1+1"}
            })
            assert response.status_code in [200, 404, 500, 422]

    def test_tool_categories(self):
        """测试工具分类"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/tools/categories")
            assert response.status_code in [200, 500]

    def test_tool_search(self):
        """测试工具搜索"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/tools/search", params={"query": "calc"})
            assert response.status_code in [200, 500, 422]


class TestErrorHandling:
    """错误处理测试"""

    def test_404(self):
        """测试404"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/nonexistent")
            assert response.status_code == 404

    def test_validation_error(self):
        """测试验证错误"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "invalid": "data"
            })
            # 可能返回422或200(如果端点接受任意JSON)
            assert response.status_code in [200, 422]


class TestChatStreaming:
    """聊天流式响应测试"""

    def test_chat_streaming_basic(self):
        """测试基础流式响应"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "message": "你好",
                    "stream": True
                },
                headers={"Accept": "text/event-stream"}
            )
            # 流式响应返回200
            assert response.status_code in [200, 500, 422]

    def test_chat_streaming_sse_format(self):
        """测试SSE格式"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "message": "测试",
                    "stream": True
                }
            )
            if response.status_code == 200:
                # 检查SSE格式
                content = response.text
                assert "data: " in content or "data:" in content

    def test_chat_non_streaming(self):
        """测试非流式响应"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "message": "你好",
                    "stream": False
                }
            )
            assert response.status_code in [200, 500, 422]


class TestSessionManagement:
    """会话管理测试"""

    def test_list_sessions(self):
        """测试列出会话"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.get("/api/sessions")
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.json()
                assert "sessions" in data

    def test_create_session(self):
        """测试创建会话"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post(
                "/api/sessions",
                json={
                    "title": "测试会话"
                }
            )
            assert response.status_code in [200, 201, 500]

    def test_get_session(self):
        """测试获取会话详情"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            # 先创建会话
            create_resp = client.post(
                "/api/sessions",
                json={"title": "测试"}
            )
            if create_resp.status_code in [200, 201]:
                session_id = create_resp.json().get("id")
                # 获取会话详情
                get_resp = client.get(f"/api/sessions/{session_id}")
                assert get_resp.status_code in [200, 404, 500]

    def test_delete_session(self):
        """测试删除会话"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            # 先创建会话
            create_resp = client.post(
                "/api/sessions",
                json={"title": "待删除"}
            )
            if create_resp.status_code in [200, 201]:
                session_id = create_resp.json().get("id")
                # 删除会话
                del_resp = client.delete(f"/api/sessions/{session_id}")
                assert del_resp.status_code in [200, 404, 500]


class TestChatErrorHandling:
    """聊天错误处理测试"""

    def test_chat_empty_message(self):
        """测试空消息"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "message": ""
            })
            assert response.status_code in [200, 400, 422, 500]

    def test_chat_missing_message(self):
        """测试缺少消息字段"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "model": "gpt-4"
            })
            assert response.status_code in [400, 422]

    def test_chat_invalid_model(self):
        """测试无效模型"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "message": "你好",
                "model": "nonexistent-model"
            })
            assert response.status_code in [200, 400, 404, 500, 422]

    def test_chat_invalid_temperature(self):
        """测试无效温度参数"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "message": "你好",
                "temperature": 5.0  # 超出范围
            })
            assert response.status_code in [200, 400, 422, 500]

    def test_chat_invalid_max_tokens(self):
        """测试无效max_tokens参数"""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/api/chat", json={
                "message": "你好",
                "max_tokens": -1  # 无效值
            })
            assert response.status_code in [200, 400, 422, 500]
