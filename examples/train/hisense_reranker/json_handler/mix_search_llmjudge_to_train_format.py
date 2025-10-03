from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""
    if 'neg' not in data.keys():
        print('no key found!')
        return None
    processed_pos = []
    processed_neg = []
    new_data = {'query':data['query']}
    for item in data['neg']:
        if item['score'] >= 0.9 and item['llm_relervance'] =='1':
            processed = processed_pos
        else:
            processed = processed_neg


        processed.append({
            'content': item['content'],
            'filename': item['filename'],
            'score': item['score'],
            'llm_relervance': item['llm_relervance'],
            'llm_reson' : item['llm_reson'],

        })
    # 将处理后的neg添加到结果字典
    if len(processed_pos) == 0:
        print('没有正例！！！')
        return None
    new_data['pos'] = processed_pos
    new_data['neg'] = processed_neg


    return new_data