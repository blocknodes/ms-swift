from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    #import pdb;pdb.set_trace()
    if 'hit1' in data.keys() or 'hit3' in data.keys():
        return None

    # 处理pos列表
    #import pdb;pdb.set_trace()
    if 'pos' in data:
        processed_pos = []
        for item in data['pos']:
            if item['filename']!='QNA':
                processed_pos.append({'content':f"{item['filename']}\n{item['content']}", 'score':1.0})
        data['pos'] = processed_pos
        if len(processed_pos) == 0:
            print('#####')
            return None

    # 处理neg列表（与pos处理逻辑相同）
    if 'neg' in data:
        processed_neg = []
        for item in data['neg']:
            if item['filename']!='QNA':

                processed_neg.append({'content':item['content'], 'score':0.0})
        # 将处理后的neg添加到结果字典
        data['neg'] = processed_neg

    return data