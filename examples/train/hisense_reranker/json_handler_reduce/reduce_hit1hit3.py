import json
import sys

file_path = sys.argv[1]
line_count = 0  # 初始化计数器
hit1=0
hit3=0

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        # 去掉行尾换行符
        line = line.strip()
        if not line:
            continue

        # 解析 JSON
        data = json.loads(line)

        # 在这里处理你的数据
        hit1 += data['hit1']
        hit3 += data['hit3']


        # 每处理一行，计数器加1
        line_count += 1

# 循环结束后打印总行数
print(f"总共处理了 {line_count} 行数据, hit1:{hit1/line_count}, hit3:{hit3/line_count}")