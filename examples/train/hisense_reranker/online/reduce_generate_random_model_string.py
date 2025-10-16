import json
import sys
import random
import string
import re

pattern = '[a-zA-Z0-9-]+'

query_prefix=set()
query_suffix=set()

filename_prefix=set()
filename_suffix=set()
normal_filename = set()

model=set()

def has_letters_and_digits(s):
    s=s.replace("-", "")
    return s.isalnum() and not s.isalpha() and not s.isdigit()

def hit_model(s):
    match = re.findall(pattern, s)
    for m in match:
        if has_letters_and_digits(m):
            return m.strip('-')
    return None


with open(sys.argv[2], "r", encoding="utf-8") as file:
    # 3. 逐行读取（file 是可迭代对象，for 循环自动按行读取）
    for line_num, line in enumerate(file, start=1):  # line_num 记录行号，便于定位错误
        # 4. 去除行首尾空白（避免换行符、空格导致的解析失败）
        clean_line = line.strip()
        if not clean_line:  # 跳过空行（若文件存在空行）
            continue

        # 5. 解析当前行的 JSON 数据
        data = json.loads(clean_line)
        query = data['query']
        match = hit_model(query)
        #match = re.search(pattern, query)
        if match:
            #model.add(match.group())
            model.add(match)
        else:
            continue



        for item in data['pos']+data['neg']:
            filename = item['filename']
            if filename == 'QNA':
                continue
            #if filename == '海信-冷藏冷冻箱-BCD-556WFK1DP-电子说明书.pdf':
            #    import pdb;pdb.set_trace()
            match = hit_model(filename)
            #print(filename)

            if match:
                prefix = filename.split(match)[0]
                suffix= filename.split(match)[1]
                filename_prefix.add(prefix)
                filename_suffix.add(suffix)

                model.add(match)
                print(f'{prefix}##{match}##{suffix}')
            else:
                normal_filename.add(filename)


print(filename_prefix)
print(filename_suffix)
print(normal_filename)







#print(model)
result = {}






# 保存结果为 JSONL 格式
with open(sys.argv[1], "w", encoding="utf-8") as out_file:
    for item in result:
        json.dump(item, out_file, ensure_ascii=False)
        out_file.write("\n")

#print(f"总共处理了 {line_count} 行数据，生成了 {len(groups)} 组 key")