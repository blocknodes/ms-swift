import json
import sys
import random
import string

def generate_random_string(length=5):
    """生成指定长度的随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_one_different(source):
    """生成一个只与源字符串有一位不同的新字符串"""
    # 随机选择要替换的位置
    position = random.randrange(len(source))

    # 生成一个与原字符不同的新字符
    new_char = random.choice(string.ascii_letters + string.digits)
    while new_char == source[position]:
        new_char = random.choice(string.ascii_letters + string.digits)

    # 替换字符并返回新字符串
    return source[:position] + new_char + source[position+1:]



result = []
#### 数字型号严格匹配
for i in range(100):
    data={}
    pos = generate_random_string()
    negs = []
    for j in range(7):
        negs.append({'content':generate_one_different(pos)})

    data['query'] = pos
    data['pos'] = [{'content':pos}]
    data['neg'] = negs
    result.append(data)


#### 品类严格匹配
products_string='电视机 空调 中央空调 冰箱 洗衣机 微波炉 电饭煲 吸尘器 电吹风 牙刷 电动牙刷 音响系统 燃气灶'

products = products_string.split(' ')

for j in range(10):
    for i in range(len(products)):
        data={}

        pos = products[i]
        data['query'] = pos
        #negs = products[:i].extend(products[i+1:])
        data['pos'] = [{'content':pos}]
        data['neg'] = [{'content':item} for item in products if item != pos]
        result.append(data)


######混合数据

products = products_string.split(' ')

for j in range(10):
    for i in range(len(products)):
        data={}
        model = generate_random_string()
        pos = products[i]
        data['query'] = pos + model
        #negs = products[:i].extend(products[i+1:])
        data['pos'] = [{'content':pos+model},{'content':pos},{'content':model}]
        for k in range(8):
            data['pos'].append({'content':pos})
        data['neg'] = [{'content':item+generate_one_different(model)} for item in products ]
        for k in range(4):
            data['neg'].append({'content':pos+generate_one_different(model)})
        result.append(data)


# 保存结果为 JSONL 格式
with open(sys.argv[1], "w", encoding="utf-8") as out_file:
    for item in result:
        json.dump(item, out_file, ensure_ascii=False)
        out_file.write("\n")

#print(f"总共处理了 {line_count} 行数据，生成了 {len(groups)} 组 key")