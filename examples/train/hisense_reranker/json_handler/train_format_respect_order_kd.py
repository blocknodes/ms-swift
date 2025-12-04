from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    query=data['query']
    new_data={}
    new_data['query'] = query

    #finals = data['pos']+data['neg']

    data['pos'].sort(key=lambda x: x['score'], reverse=True)
    data['neg'].sort(key=lambda x: x['score'], reverse=True)

    new_data['pos'] = data['pos']
    new_data['neg'] = data['neg']


    return new_data