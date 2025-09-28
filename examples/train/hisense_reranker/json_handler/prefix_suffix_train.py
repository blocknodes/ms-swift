from typing import Callable, Dict, Any, Optional, List, Tuple
import os


def filename_clean(filename):
    filename = filename.rstrip()
    if '.' in  filename:
        filename = filename.split('.')[0]
    return filename


def pos_neg_process(l):
    new_l = []
    for item in l:
        if item['filename'] == '':
            new_l.append({'content': item['content']})
        else:
            filename = item['filename']
            new_l.append({'content': f"<filename>{filename_clean(filename)}</filename>{item['content']}"})

    return new_l

# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""
    prefix = '<filename>'
    suffix = '</filename>'

    # 处理pos列表
    if 'pos' in data:
        data['pos'] = pos_neg_process(data['pos'])
    if 'neg' in data:
        data['neg'] = pos_neg_process(data['neg'])



    return data