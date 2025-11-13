from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    # 处理pos列表
    new_data={}
    new_data['query'] = data['query']
    for i in range(3):
        item = data['top3'][i]
        new_data[f'{i}st filename'] = item['filename']
        new_data[f'{i}st block'] = item['block']
        new_data[f'{i}st llm judge'] = item['llm_relervance']

    new_data['hit'] = 'hit1' in data.keys() or 'hit3' in data.keys()



    return new_data