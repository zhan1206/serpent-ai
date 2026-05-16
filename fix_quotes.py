# Fix escaped triple quotes in test_efficiency.py
content = open('tests/test_efficiency.py', 'r', encoding='utf-8').read()

# Replace escaped triple quotes (\"\"\") with proper triple quotes (""")
# This pattern appears in string content where the closing was wrongly escaped
fixed_content = content.replace('\\"\\"\\"', '"""')

# Write back
open('tests/test_efficiency.py', 'w', encoding='utf-8').write(fixed_content)

print("Fixed escaped quotes")
# Count what was replaced
count = content.count('\\"\\"\\"')
print(f"Replaced {count} occurrences")