from typing import Callable, Dict, Any, Optional, List, Tuple
import re


# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    query = data['query']

    pattern = '(?!-)[A-Za-z0-9-吋-寸]+'
    match = re.search(pattern, query)

    if not match:
        return None

    model = match.group()

    # 如果型号中没有任何字母，直接返回 None
    if not re.search('[A-Za-z]', model):
        return None

    query_list = data['query'].split(model)
    file_list = data['filename'].split(model)

    if len(file_list) != 2 or len(query_list) != 2:
        return None

    return {
        'key': model,
        'query_prefix': query_list[0],
        'query_suffix': query_list[1]+'/n'+data['content'],
        'file_prefix': file_list[0],
        'file_suffix': file_list[1]
    }