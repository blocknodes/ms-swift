from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    query=data['query']
    new_data={}
    new_data['query'] = query
    new_data['pos'] = []
    new_data['neg'] = []

    data['pos'].sort(key=lambda x: x['score'], reverse=True)
    data['neg'].sort(key=lambda x: x['score'], reverse=True)

    finals = data['pos']+data['neg']


    scores = [item['score'] for item in finals]
    cut_score = min(scores[:len(data['pos'])])
    scores.sort(reverse=True)
    pos_scores = scores[:len(data['pos'])]
    neg_scores = scores[len(data['pos']):]

    margin = 0.5

    for i in range(len(data['pos'])):
        data['pos'][i]['score'] = pos_scores[i]
    for i in range(len(data['neg'])):
        data['neg'][i]['score'] = neg_scores[i]

    ### 不需要比最小的pos小的数据


    for item in data['pos']:
        new_data['pos'].append({'content':item['content'], 'score':item['score']})

    for item in data['neg']:
        if item['score'] >= cut_score:
            new_data['neg'].append({'content':item['content'], 'score':item['score']})



    return new_data