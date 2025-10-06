from typing import Callable, Dict, Any, Optional, List, Tuple
import json
import logging
from typing import List, Dict, Generator, Optional, Tuple
import argparse
from tqdm import tqdm  # 用于显示进度条
import concurrent.futures
from functools import partial

import requests
import os
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class RerankClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        """初始化Rerank客户端"""
        self.base_url = base_url
        self.rerank_endpoint = f"{self.base_url}/rerank"
        #logging.info(f"Rerank client initialized with endpoint: {self.rerank_endpoint}")

    def rerank_batch(self, query: str, documents: List[str], instruction: Optional[str] = None) -> Dict:
        """发送单个批次的排序请求到服务端"""
        if not documents:
            logging.warning("文档列表为空，直接返回空结果")
            return {"scores": []}

        payload = {
            "query": query,
            "documents": documents,
            "instruction": instruction
        }

        try:
            logging.debug(f"发送批次排序请求，查询: {query[:50]}..., 文档数量: {len(documents)}")
            response = requests.post(
                self.rerank_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )

            response.raise_for_status()
            result = response.json()
            logging.debug(f"批次排序请求成功，返回{len(result.get('scores', []))}个分数")
            return result

        except requests.exceptions.RequestException as e:
            logging.error(f"批次排序请求失败: {str(e)}")
            raise  # 重新抛出异常，让调用者处理

    def rerank(self, query: str, documents: List[str], instruction: Optional[str] = None,
                   initial_batch_size: int = 32, min_batch_size: int = 1) -> Tuple[List[float], bool]:
        """
        发送排序请求到服务端，支持批次处理和失败重试

        参数:
            query: 查询字符串
            documents: 文档列表
            instruction: 可选指令
            initial_batch_size: 初始批次大小
            min_batch_size: 最小批次大小，低于此值不再减小

        返回:
            (scores, success): 分数列表和是否成功的标志
        """
        if not documents:
            logging.warning("文档列表为空，直接返回空结果")
            return [], True

        all_scores = []
        total_docs = len(documents)
        success = True
        current_position = 0  # 跟踪当前处理位置

        # 处理所有文档，直到全部完成
        while current_position < total_docs:
            # 每次处理都从初始批次大小开始尝试
            current_batch_size = initial_batch_size
            # 计算当前批次的文档范围
            remaining_docs = total_docs - current_position
            batch_docs = documents[current_position:current_position + min(current_batch_size, remaining_docs)]
            batch_success = False

            # 尝试处理当前批次，失败时减小批次大小并重试
            while not batch_success and current_batch_size >= min_batch_size:
                try:
                    # 确保批次大小不超过剩余文档数
                    actual_batch_size = min(current_batch_size, remaining_docs)
                    if actual_batch_size < len(batch_docs):
                        batch_docs = documents[current_position:current_position + actual_batch_size]

                    result = self.rerank_batch(query, batch_docs, instruction)
                    batch_scores = result.get("scores", [])

                    if len(batch_scores) != len(batch_docs):
                        raise ValueError(f"返回的分数数量({len(batch_scores)})与文档数量({len(batch_docs)})不匹配")

                    all_scores.extend(batch_scores)
                    batch_success = True
                    current_position += actual_batch_size  # 移动到下一批次位置
                    logging.debug(f"成功处理批次, 文档范围: {current_position - actual_batch_size}-{current_position - 1}")

                except Exception as e:
                    if len(batch_docs) <= min_batch_size:
                        # 已经是最小批次，无法再分割，记录错误并标记为失败
                        logging.error(f"处理批次失败，已达到最小批次大小 {min_batch_size}, 错误: {str(e)}")
                        success = False
                        # 为失败的文档添加NaN分数
                        all_scores.extend([float('nan')] * len(batch_docs))
                        current_position += len(batch_docs)  # 移动到下一批次位置
                        break

                    # 减小批次大小并重试
                    current_batch_size = max(current_batch_size // 2, min_batch_size)
                    logging.warning(f"批次处理失败，将批次大小从 {current_batch_size * 2} 减小到 {current_batch_size} 并重试, 错误: {str(e)}")

        return all_scores, success

    def do_rerank(self, query: str, documents: List[str], instruction: Optional[str] = None) -> List[Dict]:
        """发送排序请求并返回按分数排序的文档列表"""
        scores, success = self.rerank(query, documents, instruction)

        if not success:
            logging.warning("部分或全部文档排序失败")

        if len(scores) != len(documents):
            logging.warning(f"分数数量({len(scores)})与文档数量({len(documents)})不一致")
            return []

        ranked_docs = [
            {"content": doc, "score": score}
            for doc, score in zip(documents, scores)
        ]
        #import random
        #random.shuffle(ranked_docs)

        #ranked_docs.sort(key=lambda x: x["score"] if not float('nan') else -float('inf'), reverse=False)
        return ranked_docs

def filename_clean(filename):
    filename = filename.rstrip()
    if '.' in  filename:
        filename = filename.split('.')[0]
    return filename


# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """示例：为 pos 和 neg 列表增加 score 字段，保留原始顺序和结构"""
    client = RerankClient()
    concat_filename = False
    if os.environ.get('ADD_FILENAMW'):
        concat_filename = True

    # 处理 pos 列表
    if isinstance(data.get('pos'), list):

        #import pdb;pdb.set_trace()
        pos_contents = [item.get('model', '') for item in data['pos']]

        results = client.do_rerank(data.get('query', ''), pos_contents)




        # 用结果中的 score 更新原始数据
        for item, result in zip(data['pos'], results):
            #assert item['content'] == result['content']
            #import pdb;pdb.set_trace()
            mode_score = 1 if result.get('score')>0.5 else 0
            item['score'] += mode_score  # 只增加 score 字段
            item['model_score'] = result.get('score')
            #item['score'] = 1
            pos_score = mode_score
            if mode_score!=1:
                print(f"!!!{data['query']} vs {result['content']}")
                data['key_badcase'] = True

    # 处理 neg 列表
    if isinstance(data.get('neg'), list):
        neg_contents = [item.get('model', '') for item in data['neg']]
        neg_contents = [item if item else 'abcdfgh' for item in neg_contents]
        #import pdb;pdb.set_trace()
        results = client.do_rerank(data.get('query', ''), neg_contents)

        # 用结果中的 score 更新原始数据
        for item, result in zip(data['neg'], results):
            pass
            #assert item['content'] == result['content']
            #import pdb;pdb.set_trace()
            mode_score = 1 if result.get('score')>0.5 else 0
            item['score'] += mode_score # 只增加 score 字段
            item['model_score'] = result.get('score')
            if result['content'] != pos_contents[0] and mode_score==1:
                print(f"{result['content']} vs {pos_contents[0]}")
                data['key_badcase'] = True




    return data
