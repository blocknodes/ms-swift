from typing import Callable, Dict, Any, Optional, List, Tuple


# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""
    # 处理pos列表
    if 'pos' in data:
        processed_pos = []
        for item in data['pos']:
            #import pdb;pdb.set_trace()

            # 将分割后的结果添加到新列表
            processed_pos.append({
                'content': item['content']
            })
            processed_pos.append({
                'content': '<key>' +item['filename'] + '</key>'+item['content']
            })
        # 将处理后的pos添加到结果字典
        data['pos'] = processed_pos

    # 处理neg列表（与pos处理逻辑相同）
    if 'neg' in data:
        processed_neg = []
        for item in data['neg']:
            if 'filename' in item:
                processed_neg.append({
                    'content': '<key>' +item['filename'] + '</key>'+item['content']
                })
            else:
                processed_neg.append({
                    'content': item['content']
                })

        # 将处理后的neg添加到结果字典
        data['neg'] = processed_neg

    return data