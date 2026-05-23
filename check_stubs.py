import os, re

backend = 'backend'
results = []

for root, dirs, files in os.walk(backend):
    for f in files:
        if not f.endswith('.py') or f == '__init__.py':
            continue
        path = os.path.join(root, f)
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            content = fh.read()
        
        # Find all methods with just 'pass' body
        pass_methods = re.findall(r'def (\w+)\([^)]*\)[^:]*:\s*\n\s+pass', content)
        # Find TODO lines
        todo_lines = [(i+1, line.strip()) for i, line in enumerate(content.split('\n')) if re.search(r'TODO|FIXME|HACK', line)]
        # Find stub returns
        stub_methods = re.findall(r'def (\w+)\([^)]*\)[^:]*:\s*\n\s+return (None|\{\}|\[\]|0|0\.0|""|\'\')', content)
        
        size = len(content)
        lines = content.count('\n')
        
        if pass_methods or todo_lines or stub_methods:
            rel = os.path.relpath(path, '.')
            results.append((rel, size, lines, pass_methods, stub_methods, todo_lines))

results.sort(key=lambda x: -(len(x[3])+len(x[4])+len(x[5])))
for rel, size, lines, pm, sm, tl in results:
    details = []
    if pm: details.append(f"pass-stubs: {pm}")
    if sm: details.append(f"stub-returns: {sm}")
    if tl: details.append(f"TODOs: {[t[1] for t in tl]}")
    print(f"\n{rel} ({lines} lines, {size} bytes)")
    for d in details:
        print(f"  {d}")
