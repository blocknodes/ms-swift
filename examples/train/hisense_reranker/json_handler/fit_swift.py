from typing import Callable, Dict, Any, Optional, List, Tuple

def example_processor(data: Dict[str, Any]) -> Dict[str, Any] | List[Dict[str, Any]]:
    """处理函数：当pos超过1个时拆分成多条数据，neg超过7个时分组，每组不超过7个"""
    # 先处理pos列表（可能会产生多条数据）
    processed_data = [data.copy()]  # 初始化为包含原始数据副本的列表

    # 处理pos列表，如果长度超过1则拆分
    if 'pos' in data and len(data['pos']) > 1:
        new_processed = []
        for item in data['pos']:
            # 为每个pos项创建新数据
            new_data = data.copy()
            new_data['pos'] = [item]  # 每个新数据只包含一个pos项
            new_processed.append(new_data)
        processed_data = new_processed

    # 处理neg列表，如果长度超过7则分组
    final_result = []
    for item in processed_data:
        if 'neg' in item and len(item['neg']) > 7:
            # 拆分neg列表，每组最多7个
            for i in range(0, len(item['neg']), 7):
                grouped_data = item.copy()
                grouped_data['neg'] = item['neg'][i:i+7]
                final_result.append(grouped_data)
        else:
            final_result.append(item)

    # 对pos和neg进行格式转换
    for data_item in final_result:
        # 处理pos格式
        if 'pos' in data_item:
            data_item['pos'] = [pos_item for pos_item in data_item['pos']]

        # 处理neg格式
        if 'neg' in data_item:
            data_item['neg'] = [neg_item for neg_item in data_item['neg']]

    # 如果只有一个结果，直接返回字典，否则返回列表
    return final_result[0] if len(final_result) == 1 else final_result