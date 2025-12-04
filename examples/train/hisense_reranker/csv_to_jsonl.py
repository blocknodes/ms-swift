import csv
import sys
import json

def csv_to_jsonl(csv_input_path, jsonl_output_path):
    # 读取CSV并转换
    with open(csv_input_path, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)  # 自动用表头作为键
        with open(jsonl_output_path, mode='w', encoding='utf-8') as jsonl_file:
            for row in csv_reader:
                # 转换为JSON字符串并写入，每行一个对象
                json.dump(row, jsonl_file, ensure_ascii=False)
                jsonl_file.write('\n')

# 示例：替换为你的文件路径
csv_to_jsonl(sys.argv[1], sys.argv[2])
