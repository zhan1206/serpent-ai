"""
Fix all third-party bare imports in backend/ to be optional (try-except wrapped).
This is critical for CI on Linux where some packages may fail to install.
"""
import re
import os

# Files and their risky imports that need try-except
fixes = {
    "backend/models/openai_adapter.py": [
        ("import openai", 'try:\n    import openai\nexcept ImportError:\n    openai = None'),
    ],
    "backend/models/anthropic_adapter.py": [
        ("import anthropic", 'try:\n    import anthropic\nexcept ImportError:\n    anthropic = None'),
    ],
    "backend/models/deepseek_adapter.py": [
        ("import openai", 'try:\n    import openai\nexcept ImportError:\n    openai = None'),
    ],
    "backend/models/doubao_adapter.py": [
        ("import openai", 'try:\n    import openai\nexcept ImportError:\n    openai = None'),
    ],
    "backend/models/gemini_adapter.py": [
        ("import openai", 'try:\n    import openai\nexcept ImportError:\n    openai = None'),
    ],
    "backend/models/qwen_adapter.py": [
        ("import openai", 'try:\n    import openai\nexcept ImportError:\n    openai = None'),
    ],
    "backend/models/wenxin_adapter.py": [
        ("import openai", 'try:\n    import openai\nexcept ImportError:\n    openai = None'),
    ],
    "backend/tools/tool_sandbox.py": [
        ("import resource", "import os  # resource module is Unix-only, use os as fallback"),
        ("import docker", 'try:\n    import docker\nexcept ImportError:\n    docker = None'),
    ],
    "backend/voice/speech_to_text.py": [
        ("import numpy as np", 'try:\n    import numpy as np\nexcept ImportError:\n    np = None'),
    ],
}

for filepath, import_fixes in fixes.items():
    if not os.path.exists(filepath):
        print(f"SKIP (not found): {filepath}")
        continue
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    for old_text, new_text in import_fixes:
        if old_text in content:
            content = content.replace(old_text, new_text, 1)
            print(f"FIXED: {filepath}: {old_text[:50]}")
        else:
            print(f"NOT FOUND: {filepath}: {old_text[:50]}")
    
    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

print("\nDone!")
