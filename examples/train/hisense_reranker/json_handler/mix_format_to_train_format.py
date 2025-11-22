from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    query=data['query']
    new_data={}
    new_data['query'] = query
    new_data['pos'] = []
    new_data['neg'] = []
    finals = data['finals']
    for item in finals:
        if item['kind'] == 'qna':
            item['block'] = item['content']
            item['content'] = item['title']
        if item['llm_relervance'] >=8:
            new_data['pos'].append(item)
        else:
            new_data['neg'].append(item)

    if len(new_data['pos'] )==0:
        print(f'bad case no pos, query:{query}')
        return None


    return new_data