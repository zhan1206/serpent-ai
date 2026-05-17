#!/usr/bin/env python3
"""Test system tools"""

import sys
sys.path.insert(0, '.')

from backend.tools.system_tools import register_system_tools
from backend.tools.tool_registry import get_global_registry

# Clear and re-register
registry = get_global_registry()
registry.clear()
register_system_tools()

# List tools
tools = registry.list_tools()
print(f'Registered {len(tools)} tools:')
for t in tools:
    print(f'  - {t["name"]} ({t["category"]})')

# Test system_info
print()
print('Testing system_info:')
result = registry.call_tool('system_info', {})
print(f'  success: {result.get("success")}')
print(f'  system: {result.get("info", {}).get("system")}')

# Test fs_list
print()
print('Testing fs_list:')
result = registry.call_tool('fs_list', {'path': '.'})
print(f'  success: {result.get("success")}')
print(f'  count: {result.get("count")}')

# Test shell_exec
print()
print('Testing shell_exec:')
result = registry.call_tool('shell_exec', {'command': 'echo Hello SerpentAI'})
print(f'  success: {result.get("success")}')
print(f'  stdout: {result.get("stdout", "").strip()}')

# Test process_list
print()
print('Testing process_list:')
result = registry.call_tool('process_list', {'filter_name': 'python'})
print(f'  success: {result.get("success")}')
print(f'  count: {result.get("count")}')

print()
print('All tests passed!')
