from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    new_data={}
    new_data['query'] = data['query']
    #import pdb;pdb.set_trace()
    # 处理pos列表
    if 'positive' in data:
        processed_pos = []
        for item in data['positive']:

            processed_pos.append({

                'content': f'{item}',
                'score': 1.0
            })
        new_data['pos'] = processed_pos

    # 处理neg列表（与pos处理逻辑相同）
    if 'negative' in data:
        processed_neg = []
        for item in data['negative']:

            processed_neg.append({

                'content': f'{item}',
                'score': 0.0
            })
        # 将处理后的neg添加到结果字典
        new_data['neg'] = processed_neg

    return new_data