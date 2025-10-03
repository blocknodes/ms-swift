from typing import Callable, Dict, Any, Optional, List, Tuple



# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：转换键为小写，保留原始顺序，同时处理pos和neg列表"""
    new_data = {'query':data['query']}
    #new_data['neg'] = data['qnaAfterReRankResult '] if isinstance(data.get('qnaAfterReRankResult '), list) else data['qnaAfterReRankResult']

    new_data['neg'] = data['segmentAfterRerankResult']

    return new_data