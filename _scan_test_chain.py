import os
import re

# Find all import statements in test files to understand the import chain
test_dir = "tests"
imports_in_tests = set()

for root, dirs, files in os.walk(test_dir):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if not f.endswith(".py"):
            continue
        filepath = os.path.join(root, f)
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        
        # Find all from/import statements
        for m in re.finditer(r'(?:from|import)\s+(backend[\w.]*)', content):
            imports_in_tests.add(m.group(1))

print("=== Modules imported by tests ===")
for imp in sorted(imports_in_tests):
    print(f"  {imp}")

# Now check which of these have risky top-level imports
print("\n=== Checking for risky imports in imported modules ===")
risky_modules = {
    "resource": "Linux-only stdlib (not on Windows/Mac)",
    "docker": "Not in requirements.txt",
    "whisper": "Not in requirements.txt (openai-whisper)",
    "openai": "Not in requirements.txt",
    "anthropic": "Not in requirements.txt",
}

checked = set()
for mod_name in imports_in_tests:
    # Convert module path to file path
    parts = mod_name.split(".")
    file_path = os.path.join(*parts) + ".py"
    if not os.path.exists(file_path):
        continue
    if file_path in checked:
        continue
    checked.add(file_path)
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        for risk, reason in risky_modules.items():
            if re.match(rf'^import\s+{risk}\b', stripped) or re.match(rf'^from\s+{risk}\s+import', stripped):
                # Check try-except
                in_try = False
                for j in range(max(0, i-15), i-1):
                    prev = lines[j].strip()
                    if prev == "try:":
                        in_try = True
                        break
                    if prev and not prev.startswith("#") and prev.startswith(("except", "finally", "def ", "class ", "@")):
                        break
                if not in_try:
                    print(f"  {file_path}:{i}: {stripped}  [{reason}]")
