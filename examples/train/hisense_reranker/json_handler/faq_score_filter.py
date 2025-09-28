from typing import Callable, Dict, Any, Optional, List, Tuple
import random



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""

    prefix = '<qa>'
    # 处理pos列表
    if 'pos' in data:
        processed_pos = []
        for item in data['pos']:
            # 1. 过滤出 score > 0.95 的
            filtered_pos = [item for item in data['pos'] if item.get('score', 0) > 0.95]

            # 2. 必须保留 content 以 '<qa>' 开头的
            must_keep = [item for item in filtered_pos if item.get('content', '').startswith(prefix)]

            # 3. 可选池（去掉必须保留的）
            optional_pool = [item for item in filtered_pos if item not in must_keep]

            # 4. 随机选，补满到 3 个
            num_needed = max(0, 3 - len(must_keep))
            selected_optional = random.sample(optional_pool, min(num_needed, len(optional_pool)))

            # 5. 合并结果
            final_pos = must_keep + selected_optional


        data['pos'] = final_pos


    return data