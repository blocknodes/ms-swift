import json
import sys
import random
import string
import re
embedding_problem = 0
rerank_problem = 0
hit = 0
pos_num = 0
neg_num = 0
with open(sys.argv[1], "r", encoding="utf-8") as file:
    # 3. 逐行读取（file 是可迭代对象，for 循环自动按行读取）
    for line_num, line in enumerate(file, start=0):  # line_num 记录行号，便于定位错误
        # 4. 去除行首尾空白（避免换行符、空格导致的解析失败）
        clean_line = line.strip()
        if not clean_line:  # 跳过空行（若文件存在空行）

            continue



        # 5. 解析当前行的 JSON 数据
        data = json.loads(clean_line)
        if 'hit1' in data.keys() or 'hit3' in data.keys():
            hit += 1
            continue
        else:
            if 'pos' not in data.keys():
                embedding_problem += 1
            else:
                pos_num += len(data['pos'])
                rerank_problem += 1

        neg_num += len(data['neg'])





# 保存结果为 JSONL 格式
#with open(sys.argv[1], "w", encoding="utf-8") as out_file:
#    for item in result:
#        json.dump(item, out_file, ensure_ascii=False)
#        out_file.write("\n")
ratio=pos_num/(neg_num+pos_num)
print(f"hit: {hit} embedding problem: {embedding_problem} rerank problem: {rerank_problem}")
print(f"pos: {pos_num} neg: {neg_num} ratio: {ratio}")