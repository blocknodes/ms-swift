from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    # 处理pos列表

    processed_pos = []
    #import pdb;pdb.set_trace()
    for item in data['pos'].rstrip('\n').split('\n'):

        processed_pos.append({

            'content': f'{item}',
            'score': 1.0
        })
    data['pos'] = processed_pos

    # 处理neg列表（与pos处理逻辑相同）
    processed_neg = []
    for item in data['neg'].rstrip('\n').split('\n'):

        processed_neg.append({

            'content': f'{item}',
            'score': 0.0
        })
    # 将处理后的neg添加到结果字典
    data['neg'] = processed_neg

    return data