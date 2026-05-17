"""
SerpentAI 本地模型示例
使用 llama.cpp 在本地运行大模型
"""

from serpent_sdk import SerpentAI

def main():
    # 连接到本地服务（确保 llama.cpp 模型已配置）
    client = SerpentAI("http://localhost:8000")
    
    print("=== 本地模型示例 ===\n")
    
    # 列出所有模型
    print("1. 可用模型:")
    models = client.list_models()
    local_models = [m for m in models if "llama" in m.id.lower() or "mistral" in m.id.lower()]
    
    if local_models:
        for m in local_models:
            print(f"   - {m.id} (本地)")
        print()
        
        # 使用本地模型
        model = local_models[0].id
        print(f"2. 使用本地模型 {model}...")
        
        response = client.chat(
            "解释什么是量子纠缠，用简单的语言",
            model=model,
            temperature=0.7,
        )
        
        print(f"\n响应:\n{response.text}")
        print(f"\nToken使用: {response.usage.total_tokens}")
        print(f"费用: ${response.cost:.6f} (本地模型免费!)")
    else:
        print("   未找到本地模型")
        print("   请确保已下载 GGUF 格式模型文件到 models/ 目录")
    
    print("\n=== 完成 ===")
    client.close()


if __name__ == "__main__":
    main()
