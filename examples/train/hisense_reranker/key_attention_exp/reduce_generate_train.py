import json
import sys
import random

file_path = sys.argv[1]
line_count = 0

with open(file_path, "r", encoding="utf-8") as f:
    keys = set()
    query_prefix_suffix = set()
    file_prefix_suffix = set()

    for line in f:
        line = line.strip()
        if not line:
            continue

        data = json.loads(line)

        if 'key' not in data:
            continue

        keys.add(data['key'])

        # 确保查询前缀和后缀存在
        query_prefix_suffix.add('\n'.join([data['query_prefix'], data['query_suffix']]))
        file_prefix_suffix.add('\n'.join([data['file_prefix'], data['file_suffix']]))

        line_count += 1

keys = list(keys)
group_size = 4
num_groups = 100

# 检查 key 数量是否足够
if len(keys) < group_size * num_groups:
    raise ValueError(f"key 数量不足，需要至少 {group_size * num_groups} 个，实际只有 {len(keys)} 个")

# 随机打乱
random.shuffle(keys)

# 分组
groups = [keys[i:i + group_size] for i in range(0, group_size * num_groups, group_size)]

# 生成结果
result = []
for group in groups:
    selected_query = random.sample(list(query_prefix_suffix), min(4, len(query_prefix_suffix)))
    selected_file = random.sample(list(file_prefix_suffix), min(4, len(file_prefix_suffix)))

    result.append({
        'keys': group,
        'selected_query': selected_query,
        'selected_file': selected_file
    })

# 保存结果为 JSONL 格式
with open(sys.argv[2], "w", encoding="utf-8") as out_file:
    for item in result:
        json.dump(item, out_file, ensure_ascii=False)
        out_file.write("\n")

print(f"总共处理了 {line_count} 行数据，生成了 {len(groups)} 组 key")