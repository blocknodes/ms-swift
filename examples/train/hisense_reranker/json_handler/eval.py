from typing import Callable, Dict, Any, Optional, List, Tuple
import json
import copy

def hit(item):
    if 'pos' in item.keys():
        return True
    return False


# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    ranked_docs = data['pos'] + data['neg']

    #import pdb;pdb.set_trace()
    for i in range(len(data['pos'])):
        ranked_docs[i]['pos'] = '1'
    #if data['add_mode']:
    #    ranked_docs=[item for item in ranked_docs if item['model'] == data['pos'][0]['model']]
    ranked_docs.sort(key=lambda x: x["score"], reverse=True)
    orig_len = len(ranked_docs)
    #ranked_docs = [item for item in ranked_docs if item['filename']!='QNA']





    if hit(ranked_docs[0]):
        data['hit1'] = True
        return data

    if hit(ranked_docs[1]) or hit(ranked_docs[2]):
        data['hit3'] = True
    return data
