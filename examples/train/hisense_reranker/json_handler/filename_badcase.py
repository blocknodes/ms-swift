from typing import Callable, Dict, Any, Optional, List, Tuple
import json
import copy
import random


# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    if 'badcase' not in data.keys() or data['hit3'] == 1:
        return []

    new_data = {}
    new_data['query'] = data['query']
    pos_filenames = list(set([item['filename'] for item in data['pos']]))
    pos_contents = list(set([item['content'] for item in data['pos']]))

    neg_filenames = list(set([item['filename'] for item in data['neg'] if item['llm_filename_relervance'] == '0' and 'FAQ' not in item['filename']]))
    neg_contents = list(set([item['content'] for item in data['neg'] if item['llm_relervance'] == '0' ]))

    new_data['pos_filenames'] = pos_filenames
    new_data['pos_contents'] = pos_contents
    new_data['neg_filenames'] = neg_filenames
    new_data['neg_contents'] = neg_contents



    #return new_data

    #### 更进一步处理 ######
    query = data['query']
    data = {}
    data['query'] = query

    pos_filenames = random.choices(pos_filenames, k=2)
    pos_contents = random.choices(pos_contents, k=2)

    pos_list = [
        {'filename': f, 'content': c}
        for f in pos_filenames
        for c in pos_contents
    ] + [
        {'filename': '', 'content': c}
        for c in pos_contents]

    neg_list = [
        {'filename': f, 'content': c}
        for f in neg_filenames
        for c in pos_contents
    ] + [
        {'filename': f, 'content': c}
        for f in pos_filenames
        for c in neg_contents
    ]


    data['pos'] = pos_list
    data['neg'] = neg_list

    return data

