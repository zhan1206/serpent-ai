import os
import re
import sys

backend_dir = "backend"

# Find all .py files in backend/
issues = []
for root, dirs, files in os.walk(backend_dir):
    # Skip __pycache__
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if not f.endswith(".py"):
            continue
        filepath = os.path.join(root, f)
        relpath = filepath.replace("\\", "/")
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for bare imports (no try-except wrapping)
            # Pattern 1: import xxx (not from xxx.yyy import)
            if re.match(r'^import\s+(\w+)\s*$', stripped) or re.match(r'^import\s+(\w+)\s*,', stripped):
                mod = re.match(r'^import\s+(\w+)', stripped).group(1)
                if mod in ("os", "sys", "json", "re", "time", "datetime", "logging", 
                           "functools", "collections", "itertools", "pathlib", "abc",
                           "typing", "copy", "hashlib", "base64", "uuid", "io",
                           "threading", "asyncio", "contextlib", "inspect", "textwrap",
                           "enum", "dataclasses", "warnings", "operator", "math",
                           "random", "string", "struct", "unicodedata", "codecs",
                           "pickle", "shelve", "sqlite3", "html", "xml", "csv",
                           "tempfile", "glob", "fnmatch", "subprocess", "signal",
                           "argparse", "configparser", "secrets", "hmac", "ssl",
                           "zipfile", "tarfile", "gzip", "bz2", "lzma", "errno",
                           "stat", "shutil", "platform", "getpass", "pwd", "grp"):
                    continue  # stdlib, safe
                # Check if this import is inside a try-except
                # Look backwards for try: before this line
                in_try = False
                for j in range(max(0, i-20), i-1):
                    prev = lines[j].strip()
                    if prev == "try:":
                        in_try = True
                        break
                    if prev and not prev.startswith("#") and prev.startswith(("except", "finally", "def ", "class ", "@")):
                        break
                if not in_try:
                    issues.append(f"{relpath}:{i}: {stripped}")
            
            # Pattern 2: from xxx import (bare module, no dots)
            m = re.match(r'^from\s+(\w+)\s+import\s+', stripped)
            if m:
                mod = m.group(1)
                if mod in ("__future__", "typing", "collections", "abc", "contextlib",
                           "enum", "dataclasses", "functools", "pathlib", "asyncio"):
                    continue
                if mod == "backend":
                    continue  # internal module
                # Check if it's a known third-party that might not be installed
                risky = ("redis", "neo4j", "chromadb", "pandas", "numpy", "scipy",
                         "torch", "tensorflow", "transformers", "openai", "anthropic")
                if mod in risky:
                    in_try = False
                    for j in range(max(0, i-20), i-1):
                        prev = lines[j].strip()
                        if prev == "try:":
                            in_try = True
                            break
                        if prev and not prev.startswith("#") and prev.startswith(("except", "finally", "def ", "class ", "@")):
                            break
                    if not in_try:
                        issues.append(f"{relpath}:{i}: RISKY IMPORT (no try-except): {stripped}")

print("=== POTENTIAL CI-BREAKING IMPORTS ===")
for issue in issues:
    print(issue)
if not issues:
    print("None found!")
