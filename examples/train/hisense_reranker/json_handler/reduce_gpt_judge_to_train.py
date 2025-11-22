import subprocess
import json
import shlex
from typing import Dict, Any, Optional

def write_list_of_dict_to_jsonl(data, output_file):
    """
    将字典列表写入 JSONL 文件（每行一个 JSON 对象）

    参数:
        data (list): 字典组成的列表
        output_file (str): 输出 JSONL 文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in data:
            # 将单个字典转换为 JSON 字符串并写入，添加换行符
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')


def process_commands_file(input_path: str,input_path1: str,  output_path: str) -> None:
    query_set = set()

    with open(input_path, 'r') as f:
        for line in f:
            # 去除行首尾的空白字符
            stripped_line = line.strip()

            data = json.loads(line)
            #print(data['query'])
            query_set.add(data['query'])
    #print(f'########\n{query_set}')
    datas=[]
    with open(input_path1, 'r') as f:
        for line in f:
            # 去除行首尾的空白字符
            stripped_line = line.strip()

            data = json.loads(line)
            query = data['query']
            if query in query_set:
                datas.append(data)



    # 执行命令并写入结果到JSONL文件
    write_list_of_dict_to_jsonl(datas, output_path)




if __name__ == "__main__":
    import sys

    # 检查命令行参数
    if len(sys.argv) != 4:
        print("用法: python command_processor.py <输入命令文件> <输出JSONL文件>")

        sys.exit(1)

    input_file = sys.argv[1]
    input_file1 = sys.argv[2]
    output_file = sys.argv[3]

    # 处理命令文件
    process_commands_file(input_file,input_file1,output_file)
