"""
SerpentAI 智能体示例
"""

from serpent_sdk import SerpentAI

def main():
    client = SerpentAI("http://localhost:8000")
    
    print("=== 智能体示例 ===\n")
    
    # 创建智能体
    print("1. 创建编程助手...")
    agent = client.agents.create(
        name="Python助手",
        model="gpt-4",
        system_prompt="你是一个专业的Python程序员，简洁明了。",
    )
    print(f"   创建成功: {agent.name} ({agent.id})")
    
    # 运行智能体
    print("\n2. 运行智能体...")
    response = client.agents.run(
        agent.id,
        "写一个计算斐波那契数列的函数",
    )
    print(f"   响应:\n{response.text}")
    
    # 创建任务
    print("\n3. 创建后台任务...")
    task = client.agents.run_task(
        agent.id,
        "分析这个数据集并生成报告",
        priority=5,
        background=True,
    )
    print(f"   任务ID: {task.get('task_id')}")
    
    # 自进化
    print("\n4. 触发自进化...")
    result = client.agents.evolve(
        agent.id,
        evolution_type="optimize",
    )
    print(f"   进化结果: {result.get('status')}")
    
    print("\n=== 完成 ===")
    client.close()


if __name__ == "__main__":
    main()
