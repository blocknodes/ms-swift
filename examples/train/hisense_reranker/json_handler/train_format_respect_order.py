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

    pos_left = []

    for pos in data['pos']:
        #if pos['kind'] == 'qna':
        pos_left.append(pos)



    data['pos'] = pos_left[:2]


    finals = data['pos']+data['neg']


    scores = [item['score'] for item in finals]
    scores.sort(reverse=True)
    cut_score = min(scores[:len(data['pos'])])
    margin = 0.01
    cut_score = cut_score-margin
    negs_need_finetune = []
    for neg in data['neg']:
        if neg['score'] > cut_score:
            negs_need_finetune.append(neg)
        else:
            print(f"cutoff: {cut_score} scor: {neg['score']} ")
    data['neg'] = negs_need_finetune


    #scores.sort(reverse=True)
    pos_scores = scores[:len(data['pos'])]
    neg_scores = scores[len(data['pos']):]



    for i in range(len(data['pos'])):
        data['pos'][i]['orig_score']= data['pos'][i]['score']
        data['pos'][i]['score'] = pos_scores[i]
    for i in range(len(data['neg'])):
        data['neg'][i]['orig_score']= data['neg'][i]['score']
        data['neg'][i]['score'] = neg_scores[i] if neg_scores[i] < cut_score else cut_score


    ### 不需要比最小的pos小的数据
    new_data['pos'] = data['pos']
    new_data['neg'] = data['neg']







    return new_data