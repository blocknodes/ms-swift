from typing import Callable, Dict, Any, Optional, List, Tuple
import re


# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    new_data={}
    query = data['query']
    new_data['query'] = query


    processed = set()
    for item in data['pos']:

        processed.add(item['filename'])
    new_data['pos'] = [{'content': item, 'score':0} for item in processed]


    processed = set()
    for item in data['neg']:

        processed.add(item['filename'])
    new_data['neg'] = [{'content': item, 'score':0} for item in processed]
    ### 打分规则
    ### 1.query中含有关键品类与filename关键品类冲突

    ### 3.query中无型号与但filename中有型号


    products = ['冰箱','空调','电视','洗衣机','冷柜','洗碗机']
    product = None
    for item in products:
        if item in query:
            product = item
            break

    if product:
        for neg in new_data['neg'] :
            for item in products:
                if item in neg['content']:
                    if item != product:
                        neg['score'] = 1
                    else:
                        neg['score'] = 0
                        break

    ### 2.query中型号与filename型号冲突
    pattern = r"[A-Za-z]+\d{2,}-[A-Za-z0-9]+"
    result = re.search(pattern, query)

    if result:
        #import pdb;pdb.set_trace()
        #print(f"query:{query} 提取的型号：{result.group()}" )  # 输出：WF18-C507IPRO
        for neg in new_data['neg'] :
            neg_result = re.search(pattern, neg['content'])
            if neg_result and neg_result.group()!=result.group():
                #print(f"query:{query} 提取的型号：{result.group()} neg: {neg_result.group()}" )
                neg['score'] = 1


    all = new_data['pos']  + new_data['neg']
    new_data['pos'] = [item for item in all if item['score']==1]
    new_data['neg'] = [item for item in all if item['score']==0]

    if len(new_data['pos']) == 0:
        new_data['pos'] = new_data['neg']


    return new_data