# Debug script to find escaped triple quotes
content = open('tests/test_efficiency.py', 'rb').read()

# Find all occurrences of escaped quotes (\"\"\")
import re
escaped = [m.start() for m in re.finditer(b'\\"\\"\\"', content)]
print('Escaped triple quotes:', len(escaped))
for pos in escaped[:10]:
    line_num = content[:pos].count(b'\n') + 1
    print(f'  Position {pos}, line ~{line_num}')

# Also show lines around the problematic areas
lines = content.split(b'\n')
print('\nLine 60-70:')
for i in range(59, 71):
    if i < len(lines):
        print(f'{i+1}: {lines[i][:80]}')

print('\nLine 245-260:')
for i in range(244, 260):
    if i < len(lines):
        print(f'{i+1}: {lines[i][:80]}')