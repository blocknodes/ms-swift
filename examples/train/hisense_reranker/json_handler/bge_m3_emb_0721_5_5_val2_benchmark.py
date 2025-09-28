from typing import Callable, Dict, Any, Optional, List, Tuple

def split_filename_and_content(text):
    # 按第一个换行符分割
    parts = text.split('\n', 1)

    # 提取文件名（第一行）
    filename = parts[0].strip()  # 去除可能的前后空白

    # 提取内容（剩余部分），如果没有换行符则内容为空
    content = parts[1] if len(parts) > 1 else ''

    return filename.rstrip('\n'), content.rstrip('\n').replace(' ', '')


# 修改后的处理函数
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理pos和recall列表，将recall中与pos不同的项作为neg"""
    # 处理pos列表
    processed_pos = []
    topk = 10
    if 'pos' in data:
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

    # 处理recall列表并生成neg
    data['neg'] = []
    if 'recall' in data and processed_pos:  # 确保pos有数据可供比较
        # 创建pos内容的集合用于快速查找
        pos_contents = {item['content'] for item in processed_pos}
        pos_filename_and_contents = {(item['filename'], item['content']) for item in processed_pos}

        for item in data['recall'][:topk]:
            # 分割每个项目为文件名和内容
            filename, content = split_filename_and_content(item)
            if (filename, content) in pos_filename_and_contents:
                continue
            if content in pos_contents:
                processed_pos.append({
                    'filename': filename,
                    'content': content
                })


            # 只保留不在pos中的项
            else:
                data['neg'].append({
                    'filename': filename,
                    'content': content
                })

    # 删除recall字段
    if 'recall' in data:
        del data['recall']

    return data