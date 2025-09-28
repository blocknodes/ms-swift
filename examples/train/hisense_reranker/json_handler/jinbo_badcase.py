from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""
    # 处理pos列表
    clean_data={}
    clean_data['doc'] = []
    clean_data['qna'] = []
    clean_data['query'] = data['question']
    if 'segment_raw' in data:
        for item in data['segment_raw']:
            filename = ''
            if 'fileName' in item['metadata'].keys():
                filename = item['metadata']['fileName']
            #import pdb;pdb.set_trace()
            clean_data['doc'].append({'filename':filename, 'content':item['content']})
    if 'qna_raw' in data:
        for item in data['qna_raw']:
            filename = ''
            if 'fileName' in item['metadata'].keys():
                filename = item['metadata']['fileName']

            #import pdb;pdb.set_trace()
            clean_data['qna'].append({'filename':filename, 'qna_title':item['metadata']['qna_title'],'qna_content':item['content']})


    return clean_data