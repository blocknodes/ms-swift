from typing import Callable, Dict, Any, Optional, List, Tuple

def split_filename_and_content(text):
    # 按第一个换行符分割
    parts = text.split('\n', 1)

    # 提取文件名（第一行）
    filename = parts[0].strip()  # 去除可能的前后空白

    # 提取内容（剩余部分），如果没有换行符则内容为空
    content = parts[1] if len(parts) > 1 else ''

    return filename.rstrip('\n'), content.rstrip('\n')


# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""
    # 处理pos列表
    if 'pos' in data:
        processed_pos = []
        for item in data['pos']:
            # 分割每个项目为文件名和内容
            filename, content = split_filename_and_content(item)
            # 将分割后的结果添加到新列表
            processed_pos.append({
                'filename': filename,
                'content': content
            })
        # 将处理后的pos添加到结果字典
        data['pos'] = processed_pos

    # 处理neg列表（与pos处理逻辑相同）
    if 'neg' in data:
        processed_neg = []
        for item in data['neg']:
            # 分割每个项目为文件名和内容
            filename, content = split_filename_and_content(item)
            # 将分割后的结果添加到新列表
            processed_neg.append({
                'filename': filename,
                'content': content
            })
        # 将处理后的neg添加到结果字典
        data['neg'] = processed_neg

    return data