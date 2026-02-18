import json
import sys
import random
from itertools import chain




products = ['油烟机','冰箱','空调','电视','洗衣机','冷柜','洗碗机','变温柜','电热水器','燃气灶','投影']

product_query = {}
product_filename = {}
filter_free_query=[]
filter_free_filename=[]

file_path = sys.argv[1]

with open(file_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        data = json.loads(line)
        query = data['query']


        ##不涉及的query
        filter_free=True
        for product in products:
            if product in query:
                filter_free = False
                if product in product_query:
                    product_query[product].append(query)
                else:
                    product_query[product]=[query]

                break
        if filter_free:
            filter_free_query.append(query)

        filenames = [item['filename'] for item in data['pos'] + data['neg']]
        for filename in filenames:
            filter_free=True
            for product in products:
                if product in filename:
                    filter_free = False
                    if product in product_filename:
                        product_filename[product].append(filename)
                    else:
                        product_filename[product]=[filename]

                    break
            if filter_free:
                filter_free_filename.append(filename)

        #print(filenames)



####deduplicate
filter_free_query=list(set(filter_free_query))
filter_free_filename=list(set(filter_free_filename))
for key in product_query:
    product_query[key]=list(set(product_query[key]))

for key in product_filename:
    product_filename[key]=list(set(product_filename[key]))



result = []

INSTRUCTION=''
####filter_free_query### all negative
for query in filter_free_query+filter_free_filename:
    item = {}
    item['instruction']=query
    item['input']=None
    item['output']='无'

    result.append(item)

for k,v in product_query.items():
    for query in v:
        item = {}
        item['instruction']=query
        item['input']=None
        item['output']=k

        result.append(item)

for k,v in product_filename.items():
    for query in v:
        item = {}
        item['instruction']=query
        item['input']=None
        item['output']=k

        result.append(item)

# 保存结果为 JSONL 格式
with open(sys.argv[2], "w", encoding="utf-8") as out_file:
    for item in result:
        json.dump(item, out_file, ensure_ascii=False)
        out_file.write("\n")

#print(f"总共处理了 {line_count} 行数据，生成了 {len(groups)} 组 key")