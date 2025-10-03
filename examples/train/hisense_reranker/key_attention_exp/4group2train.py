from typing import Callable, Dict, Any, Optional, List, Tuple
import re
import random
import string

def generate_with_model(model, pair):
    return pair.split('\n')[0]+model+pair.split('\n')[1]

def replace_with_random_letter(s):
    if not s:  # 空字符串直接返回
        return s
    # 随机选择一个位置
    index = random.randint(0, len(s) - 1)
    # 随机选择一个字母（a-z, A-Z）
    new_char = random.choice(string.ascii_letters)
    # 切片拼接
    return s[:index] + new_char + s[index+1:]

def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    models  = data['keys']
    querys = data['selected_query']
    files = data['selected_file']

    result = []
    all_content=set()
    for query_pair in querys:
        all_content.add(query_pair.split('/n')[1])

    for i in range(len(querys)):
        query_pair = querys[i]
        sample = {}
        #sample['query'] = 'TCL微波炉'+generate_with_model(models[0], query_pair)
        sample['query'] = generate_with_model(models[0], query_pair).split('/n')[0]
        content = generate_with_model(models[0], query_pair).split('/n')[1]
        ## pos
        sample['pos'] = []
        sample['neg'] = []
        for file in files:
            pos_file = generate_with_model(models[0], file)
            if query_pair.split('\n')[0] != 0:
                    pos_file = query_pair.split('\n')[0] + models[0] + file.split('\n')[1]
            sample['pos'].append({'content':content, 'filename':pos_file})
            #sample['pos'].append({'content':content, 'filename':''})
            for model in models[1:]:
                model = replace_with_random_letter(models[0])

                neg_file = generate_with_model(model, file)
                if query_pair.split('\n')[0] != 0:
                    neg_file = query_pair.split('\n')[0] + model + file.split('\n')[1]
                sample['neg'].append({'content':content, 'filename': neg_file})
            for neg_content in all_content:
                if neg_content != content:
                    sample['neg'].append({'content':neg_content})
        result.append(sample)

    return result