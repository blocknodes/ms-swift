from typing import Callable, Dict, Any, Optional, List, Tuple
import json
import copy


# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    if 'badcase' not in data.keys() or data['hit3'] == 1:
        return None

    new_data = {}
    new_data['query'] = data['query']
    new_data['pos'] = [{'content'item['filename']} for item in data['pos']]

    neg

    ranked_docs = data['pos'] + data['neg']
    for i in range(len(data['pos'])):
        ranked_docs[i]['pos'] = '1'
    ranked_docs.sort(key=lambda x: x["score"], reverse=True)
    orig_len = len(ranked_docs)
    ### delete filename
    #ranked_docs = [x for x in ranked_docs if ('llm_filename_relervance' not in x.keys() or x['llm_filename_relervance'] != '0')]
    #if len(ranked_docs) != orig_len:
    #    print('hahhaha')
    hit1=1 if hit(ranked_docs[0]) else 0

    hit3 =0
    for item in ranked_docs[:3]:
        if hit(item):
            hit3=1
            break

    data['hit1'] = hit1
    data['hit3'] = hit3

    ranked_docs = [x for x in ranked_docs if ('llm_filename_relervance' not in x.keys() or x['llm_filename_relervance'] != '0')]
    hit1=1 if hit(ranked_docs[0]) else 0

    hit3 =0
    for item in ranked_docs[:3]:
        if hit(item):
            hit3=1
            break
    #new_data = None
    if data['hit1'] != hit1 or data['hit3'] != hit3:
        data['badcase'] = 1

    return data
