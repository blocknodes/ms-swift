import json
import sys
import random
import string

def generate_random_string(length=5, source=None):
    """生成指定长度的随机字符串"""
    result = ''.join(random.choices(string.ascii_letters + string.digits +'-', k=length))
    if not source:
        return result

    while result == source:
        result = ''.join(random.choices(string.ascii_letters + string.digits +'-', k=length))
    return result

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

def has_digit_or_alpha(s: str) -> bool:
    return any(c.isascii() and c.isalnum() for c in s)

query_set = set()
file_suffix = set()
with open(sys.argv[2], "r", encoding="utf-8") as file:
    # 3. 逐行读取（file 是可迭代对象，for 循环自动按行读取）
    for line_num, line in enumerate(file, start=1):  # line_num 记录行号，便于定位错误
        # 4. 去除行首尾空白（避免换行符、空格导致的解析失败）
        clean_line = line.strip()
        if not clean_line:  # 跳过空行（若文件存在空行）
            continue

        # 5. 解析当前行的 JSON 数据
        data = json.loads(clean_line)
        if 'query_suffix' in data.keys() and not has_digit_or_alpha(data['query_suffix']):
            query_set.add(data['query_suffix'])
        if 'file_suffix' in data.keys() and not has_digit_or_alpha(data['file_suffix'].split('.')[0]):
            file_suffix.add(data['file_suffix'])

result = []
#### 数字型号严格匹配
for i in range(1000):
    data={}
    pos = generate_random_string(10)
    negs = []
    for j in range(7):
        negs.append({'content':generate_one_different(pos)+random.choice(list(file_suffix))})

    data['query'] = pos+random.choice(list(query_set))
    data['pos'] = [{'content':pos+random.choice(list(file_suffix))}]
    data['neg'] = negs
    result.append(data)


#### 数字型号严格匹配
for i in range(1000):
    data={}
    pos = generate_random_string(10)
    product_chosen = random.sample(products,8)
    data['query'] =[]
    negs = []
    for j in range(7):
        negs.append({'content':generate_one_different(pos)+random.choice(list(file_suffix))})
        negs.append({'content':product_chosen[0]+generate_one_different(pos)+random.choice(list(file_suffix))})
        negs.append({'content':product_chosen[j+1]+random.choice(list(file_suffix))})
    for j in range(4):
        data['query'].append(product_chosen[0] + pos +random.choice(list(query_set))
    data['pos'] = [{'content':product_chosen[0]+pos+random.choice(list(file_suffix))}]
    for j in range(1):
        data['pos'].append({'content':product_chosen[0]+random.choice(list(file_suffix))})
    data['pos'].append({'content':pos+random.choice(list(file_suffix))})
    data['neg'] = negs
    result.append(data)


brand_string='容声 海信 vidda 科龙 东芝 璀璨'
brand = brand_string.split(' ')

products_string='电视机 空调 中央空调 冰箱 洗衣机 微波炉 电饭煲 吸尘器 电吹风 牙刷 电动牙刷 音响系统 燃气灶'
products = products_string.split(' ')


result = []
#### 品类严格匹配
products_string='电视机 空调 中央空调 冰箱 洗衣机 微波炉 电饭煲 吸尘器 电吹风 牙刷 电动牙刷 音响系统 燃气灶'

products = products_string.split(' ')

query_templates =['{}{}','请问下，这款{}型号的{}','您好，{}{}','介绍下这款{}{}']

#### Model only #######
for i in range(10000):
    data={}
    #product = products[i%len(products)]
    product_chosen = random.sample(products,8)
    product = product_chosen[0]
    product_reject = product_chosen[1:]
    if product in product_reject:
        raise
    #template = query_templates[i%len(query_templates)]
    template = random.choice(query_templates)
    pos = generate_random_string(10)
    data['query'] = template.format(pos, product)+random.choice(list(query_set))

    negs = []
    ## same product different model(one char)
    for j in range(7):
        negs.append({'content':product+generate_one_different(pos)})
    ## same product different model
    for j in range(7):
        negs.append({'content':product+generate_random_string((i+j*13)%10,pos)})
    ## different product same model
    for j in range(7):
        negs.append({'content':product_reject[j%len(product_reject)]+pos})
    data['pos'] = [{'content':product+pos}]
    data['neg'] = negs
    result.append(data)




# 保存结果为 JSONL 格式
with open(sys.argv[1], "w", encoding="utf-8") as out_file:
    for item in result:
        json.dump(item, out_file, ensure_ascii=False)
        out_file.write("\n")

#print(f"总共处理了 {line_count} 行数据，生成了 {len(groups)} 组 key")