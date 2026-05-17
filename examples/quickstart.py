"""
SerpentAI 快速开始示例
"""

from serpent_sdk import SerpentAI

def main():
    # 初始化客户端
    client = SerpentAI("http://localhost:8000")
    
    print("=== SerpentAI 快速开始 ===\n")
    
    # 1. 健康检查
    print("1. 健康检查...")
    health = client.health()
    print(f"   状态: {health.status}")
    print(f"   版本: {health.version}")
    
    # 2. 列出模型
    print("\n2. 可用模型:")
    models = client.list_models()
    for m in models[:5]:
        print(f"   - {m.id} ({m.provider})")
    
    # 3. 聊天
    print("\n3. 聊天测试...")
    response = client.chat("请用一句话介绍自己")
    print(f"   响应: {response.text}")
    print(f"   模型: {response.model}")
    print(f"   Token: {response.usage.total_tokens}")
    print(f"   费用: ${response.cost:.6f}")
    
    # 4. 工具
    print("\n4. 内置工具:")
    tools = client.list_tools()
    for t in tools[:5]:
        print(f"   - {t.name} ({t.category})")
    
    # 5. 记忆系统
    print("\n5. 记忆系统:")
    session_id = "quickstart-demo"
    client.add_memory("今天学习了Python", session_id=session_id)
    memories = client.recall_memory("学习", session_id=session_id)
    print(f"   召回记忆数: {len(memories)}")
    stats = client.get_memory_stats()
    print(f"   记忆总量: {stats.total}")
    
    # 6. 智能体
    print("\n6. 智能体:")
    agents = client.agents.list()
    print(f"   已有智能体数: {len(agents)}")
    
    # 7. 工作流
    print("\n7. 工作流:")
    workflows = client.workflows.list()
    print(f"   已有工作流数: {len(workflows)}")
    templates = client.workflows.list_templates()
    print(f"   可用模板数: {len(templates)}")
    
    print("\n=== 完成 ===")
    client.close()


if __name__ == "__main__":
    main()
