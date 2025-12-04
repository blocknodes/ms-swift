from typing import Callable, Dict, Any, Optional, List, Tuple
import random



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""


    for item in data['finals'][:3]:
        score = 0
        score += item['human_judge']
        if score>0:
            return None




    return data