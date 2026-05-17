"""
SerpentAI 工作流示例
"""

from serpent_sdk import SerpentAI

def main():
    client = SerpentAI("http://localhost:8000")
    
    print("=== 工作流示例 ===\n")
    
    # 列出模板
    print("1. 可用模板:")
    templates = client.workflows.list_templates()
    for t in templates[:3]:
        print(f"   - {t['name']}: {t['description'][:50]}...")
    
    # 从模板创建
    if templates:
        print(f"\n2. 从模板创建工作流...")
        workflow = client.workflows.create_from_template(templates[0]['id'])
        print(f"   创建成功: {workflow.name} ({workflow.id})")
        
        # 执行
        print("\n3. 执行工作流...")
        result = client.workflows.execute(
            workflow.id,
            input_data={"user_input": "test"},
        )
        print(f"   状态: {result.status}")
        print(f"   耗时: {result.duration_ms}ms")
    
    # 创建自定义工作流
    print("\n4. 创建自定义工作流...")
    workflow = client.workflows.create(
        name="我的工作流",
        description="测试工作流",
        nodes=[
            {
                "id": "node_1",
                "name": "开始",
                "type": "start",
                "position": {"x": 100, "y": 200},
                "config": {},
            },
            {
                "id": "node_2",
                "name": "AI处理",
                "type": "agent",
                "position": {"x": 300, "y": 200},
                "config": {"agent_model": "gpt-4"},
            },
        ],
        edges=[
            {
                "id": "edge_1",
                "source": "node_1",
                "target": "node_2",
            },
        ],
    )
    print(f"   创建成功: {workflow.name} ({workflow.id})")
    
    # 添加调度
    print("\n5. 添加定时调度...")
    task_id = client.workflows.add_schedule(
        workflow.id,
        trigger_type="cron",
        expression="0 9 * * *",  # 每天9点
        input_data={"input": "daily.csv"},
    )
    print(f"   调度任务ID: {task_id}")
    
    print("\n=== 完成 ===")
    client.close()


if __name__ == "__main__":
    main()
