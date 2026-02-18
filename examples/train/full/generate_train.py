from typing import Callable, Dict, Any, Optional, List, Tuple
import json
import re

products = ['油烟机','冰箱','空调','电视','洗衣机','冷柜','洗碗机','变温柜','电热水器','燃气灶','投影']

products_mapping={}
##使用index作为上面的代号
for i in range(len(products)):
    products_mapping[products[i]]=i

pattern = '(?!-)[A-Za-z0-9/-]*[A-Za-z0-9/](?<!-)'

def get_model(s):
    match = re.search(pattern, s)
    if  match:
        model = match.group()

        # 如果型号中没有任何字母，直接返回 None
        if not re.search('[A-Za-z]', model):
            #print(f'model:{model} query:{query}')
            return None
        else:
            return model

def get_meta_info(s):
    ### 这里有近似，需要大模型筛选下
    result = {}
    for key in products_mapping.keys():
        if key in s:
            result['p']= products_mapping[key]
            break
    model = get_model(s)
    if model:
        result['m']= model
    return result





# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    datas=[]
    candidates=[]
    #import pdb;pdb.set_trace()
    # 处理pos列表
    candidates.append(data['query'])

    if 'positive' in data:
        for item in data['positive']:

            candidates.append(item['content'])


    # 处理neg列表（与pos处理逻辑相同）
    if 'negative' in data:
        for item in data['negative']:

            candidates.append(item['content'])
    for item in candidates:
        result=get_meta_info(item)
        datas.append({'instruction':'','input':item, 'output': json.dumps(result)})


    return datas