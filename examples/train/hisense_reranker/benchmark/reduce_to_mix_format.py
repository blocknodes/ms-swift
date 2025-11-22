import json
import sys

def split_list_by_key(items, target_key):
    """
    按元素是否包含目标键拆分列表，保持原顺序

    :param items: 原始列表（元素为字典或类似映射类型）
    :param target_key: 需要判断的键
    :return: 包含两个列表的元组 (有目标键的元素列表, 无目标键的元素列表)
    """
    has_key = []
    no_key = []
    for item in items:
        # 判断元素是否为字典且包含目标键（可根据实际类型调整判断逻辑）
        if isinstance(item, dict) and target_key in item:
            has_key.append(item)
        else:
            no_key.append(item)
    return has_key, no_key

def extract_top3_qd_qq(recall):
    qds,qqs=split_list_by_key(recall, 'seg_content')
    return qds,qqs

results=[]

def list_of_dict_to_jsonl(data_list, output_file):
    """
    将 list of dict 转换为 JSONL 文件

    :param data_list: 包含字典的列表
    :param output_file: 输出的 JSONL 文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in data_list:
            # 确保中文等特殊字符正常显示（ensure_ascii=False）
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')  # 每行一个 JSON 对象

import csv

def list_of_dict_to_csv(data_list, output_file):
    """
    将 list of dict 转换为 CSV 文件

    :param data_list: 包含字典的列表
    :param output_file: 输出的 CSV 文件路径
    """
    if not data_list:
        return  # 空列表直接返回

    # 获取所有字段名（取所有字典的键的并集）
    fieldnames = set()
    for item in data_list:
        fieldnames.update(item.keys())
    fieldnames = sorted(fieldnames)  # 排序保证表头顺序固定

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        # 初始化 CSV 写入器，指定表头
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()  # 写入表头

        # 写入每行数据（自动处理缺失字段，填充空值）
        for item in data_list:
            writer.writerow(item)

def restruct_item(item):
    return item["title"] + '##\n' + item["content"]



def process_two_jsonl(file1_path, file2_path):
    # 同时打开两个文件
    with open(file1_path, 'r', encoding='utf-8') as f1, \
         open(file2_path, 'r', encoding='utf-8') as f2:

        # 使用zip组合两个文件的行迭代器，逐行处理
        for line_num, (line1, line2) in enumerate(zip(f1, f2), 1):

            # 解析JSON行
            data1 = json.loads(line1.strip())
            data2 = json.loads(line2.strip())

            # 这里写你的处理逻辑
            assert data1['query'] == data2['query']
            print(f"第{line_num}行处理:")
            query = data1['query']
            print(data1.keys())
            item={}
            item['query'] = data1['query']
            item['finals'] = []
            item_num = len(data2['value'])
            assert item_num==len(data1['top3'])
            for i in range(item_num):
                single_item={}
                assert data1['top3'][i]['filename'] == data2['value'][i]['filename']
                single_item['filename'] = data1['top3'][i]['filename']
                single_item['llm_relervance'] = data1['top3'][i]['llm_relervance']

                if 'document' in data2['value'][i].keys():
                    single_item['kind']='document'
                    assert data1['top3'][i]['block'] == data2['value'][i]['block']
                    single_item['content'] = data2['value'][i]['document']
                    single_item['block'] = data2['value'][i]['block']
                    single_item['title'] = data1['top3'][i]['filename']

                else:
                    single_item['kind']='qna'
                    single_item['content'] = data2['value'][i]['qna_content']
                    single_item['title'] = data2['value'][i]['qna_title']

                item['finals'].append(single_item)

            results.append(item)


# 使用示例
if __name__ == "__main__":
    process_two_jsonl(sys.argv[1], sys.argv[2])
    list_of_dict_to_jsonl(results, sys.argv[3]+'jsonl')
    #list_of_dict_to_csv(results, sys.argv[3]+'csv')