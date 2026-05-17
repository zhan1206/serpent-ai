#!/usr/bin/env python3
"""
SerpentAI 系统操作工具演示
展示如何让 AI 操作电脑
"""

import sys
sys.path.insert(0, '.')

from backend.tools.system_tools import register_system_tools
from backend.tools.tool_registry import get_global_registry


def demo():
    """演示系统工具的使用"""
    
    # 初始化工具注册表
    registry = get_global_registry()
    registry.clear()
    register_system_tools()
    
    print("=" * 60)
    print("SerpentAI System Tools Demo")
    print("=" * 60)
    print()
    
    # 1. 获取系统信息
    print("[1] Get System Information")
    result = registry.call_tool('system_info', {})
    info = result.get('info', {})
    print(f"    操作系统: {info.get('system')} {info.get('release')}")
    print(f"    主机名: {info.get('node')}")
    print(f"    CPU: {info.get('processor')}")
    print(f"    Python: {info.get('python_version')}")
    print()
    
    # 2. 列出目录内容
    print("[2] List directory contents (current directory)")
    result = registry.call_tool('fs_list', {'path': '.'})
    items = result.get('items', [])[:5]  # 只显示前5个
    for item in items:
        type_str = '[DIR]' if item['type'] == 'directory' else '[FILE]'
        print(f"    {type_str} {item['name']}")
    if result.get('count', 0) > 5:
        print(f"    ... 还有 {result['count'] - 5} 个项目")
    print()
    
    # 3. 创建测试文件
    print("[3] Create test file")
    result = registry.call_tool('fs_write', {
        'path': 'test_hello.txt',
        'content': 'Hello from SerpentAI!\nAI can write files now!\n'
    })
    print(f"    Wrote file: test_hello.txt ({result.get('size')} bytes)")
    print()
    
    # 4. 读取文件内容
    print("[4] Read file content")
    result = registry.call_tool('fs_read', {'path': 'test_hello.txt'})
    print(f"    Content:")
    for line in result.get('content', '').split('\n'):
        if line:
            print(f"      {line}")
    print()
    
    # 5. 执行 Shell 命令
    print("[5] Execute Shell command")
    if sys.platform == 'win32':
        result = registry.call_tool('shell_exec', {'command': 'whoami'})
    else:
        result = registry.call_tool('shell_exec', {'command': 'whoami'})
    print(f"    Command: whoami")
    print(f"    Output: {result.get('stdout', '').strip()}")
    print()
    
    # 6. 列出进程
    print("[6] List running Python processes")
    result = registry.call_tool('process_list', {'filter_name': 'python'})
    processes = result.get('processes', [])[:3]
    for p in processes:
        print(f"    PID {p['pid']}: {p['name']}")
    print()
    
    # 7. 磁盘使用情况
    print("[7] Disk usage")
    if sys.platform == 'win32':
        result = registry.call_tool('system_disk_usage', {'path': 'C:\\'})
    else:
        result = registry.call_tool('system_disk_usage', {'path': '/'})
    print(f"    Total: {result.get('total_gb')} GB")
    print(f"    Used: {result.get('used_gb')} GB ({result.get('percent_used')}%)")
    print(f"    Free: {result.get('free_gb')} GB")
    print()
    
    # 8. 清理测试文件
    print("[8] Cleanup test file")
    result = registry.call_tool('fs_delete', {'path': 'test_hello.txt'})
    print(f"    Deleted: test_hello.txt")
    print()
    
    print("=" * 60)
    print("Demo complete! SerpentAI can now operate the computer!")
    print("=" * 60)


if __name__ == '__main__':
    demo()
