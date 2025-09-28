from typing import Callable, Dict, Any, Optional, List, Tuple
import json
import logging
from typing import List, Dict, Generator, Optional, Tuple
import argparse
from tqdm import tqdm  # 用于显示进度条
import concurrent.futures
from functools import partial

import requests

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

    def rerank_and_sort(self, query: str, documents: List[str], instruction: Optional[str] = None) -> List[Dict]:
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

        ranked_docs.sort(key=lambda x: x["score"] if not float('nan') else -float('inf'), reverse=True)
        return ranked_docs



def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    示例：使用 RerankClient 分别排序 doc 和 qna，合并后再取 top3
    """
    client = RerankClient()
    merged = []

    # 处理 doc 列表
    docs = data.get('doc', [])
    if docs:
        contents = [d['content'] for d in docs]
        reranked = client.rerank_and_sort(data['query'], contents)
        score_map = {item['content']: item['score'] for item in reranked}

        for d in docs:
            d['score'] = score_map.get(d['content'], 0.0)
            d['type'] = 'doc'  # 标记类型
        merged.extend(docs)

    # 处理 qna 列表
    prefix = '<qa>'
    suffix = '</qa>'
    qnas = data.get('qna', [])
    if qnas:
        titles = [prefix + q['qna_title'] + suffix for q in qnas]
        reranked = client.rerank_and_sort(data['query'], titles)
        score_map = {item['content'][len(prefix):-len(suffix)]: item['score'] for item in reranked}

        for q in qnas:
            q['score'] = score_map.get(q['qna_title'], 0.0)
            q['type'] = 'qna'  # 标记类型
        merged.extend(qnas)

    # 合并后按 score 降序排序
    merged.sort(key=lambda x: x['score'], reverse=True)

    # 取 top3
    data['top3'] = merged[:3]

    return data