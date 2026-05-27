def has_comment_before(lines, idx):
    return idx > 0 and lines[idx - 1].lstrip().startswith("#")


def extract_func_name(line):
    stripped = line.lstrip()
    if not stripped.startswith("def "):
        return None
    after_def = stripped[4:].lstrip()
    name_end = after_def.find("(")
    return after_def[:name_end].strip() if name_end != -1 else None


with open("data_def.txt") as f:
    lines = f.readlines()

result = []
for i, line in enumerate(lines):
    func_name = extract_func_name(line)
    if func_name and not has_comment_before(lines, i):
        result.append(func_name)

if result:
    print('\n'.join(result))
else:
    print('Best Programming Team')
