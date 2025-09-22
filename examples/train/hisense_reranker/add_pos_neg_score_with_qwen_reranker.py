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
        logging.info(f"Rerank client initialized with endpoint: {self.rerank_endpoint}")

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
        current_batch_size = initial_batch_size
        total_docs = len(documents)
        success = True

        # 按批次处理所有文档
        for i in range(0, total_docs, current_batch_size):
            batch_docs = documents[i:i+current_batch_size]
            batch_success = False

            # 尝试处理当前批次，失败时减小批次大小并重试
            while not batch_success and current_batch_size >= min_batch_size:
                try:
                    result = self.rerank_batch(query, batch_docs, instruction)
                    batch_scores = result.get("scores", [])

                    if len(batch_scores) != len(batch_docs):
                        raise ValueError(f"返回的分数数量({len(batch_scores)})与文档数量({len(batch_docs)})不匹配")

                    all_scores.extend(batch_scores)
                    batch_success = True
                    logging.debug(f"成功处理批次 {i//current_batch_size + 1}, 文档范围: {i}-{min(i+current_batch_size, total_docs)-1}")

                except Exception as e:
                    if len(batch_docs) <= min_batch_size:
                        # 已经是最小批次，无法再分割，记录错误并标记为失败
                        logging.error(f"处理批次失败，已达到最小批次大小 {min_batch_size}, 错误: {str(e)}")
                        success = False
                        # 为失败的文档添加NaN分数
                        all_scores.extend([float('nan')] * len(batch_docs))
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
            {"document": doc, "score": score}
            for doc, score in zip(documents, scores)
        ]

        ranked_docs.sort(key=lambda x: x["score"] if not float('nan') else -float('inf'), reverse=True)
        return ranked_docs


def read_jsonl(file_path: str) -> Generator[Dict, None, None]:
    """读取JSONL文件，逐行生成JSON对象"""
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def process_single_item(item, client, instruction, initial_batch_size):
    """处理单个JSONL条目"""
    try:
        query = item.get('query', '')
        pos_docs = item.get('pos', [])
        neg_docs = item.get('neg', [])

        pos_docs = [s['content'].rstrip('\n') for s in pos_docs]
        neg_docs = [s['content'].rstrip('\n') for s in neg_docs]

        if not query:
            logging.warning("跳过没有query的条目")
            return None, False, False

        # 对正样本打分
        pos_with_scores = []
        pos_success = True
        if pos_docs:
            raw_pos_scores, pos_success = client.rerank(
                query, pos_docs, instruction,
                initial_batch_size=initial_batch_size
            )
            pos_scores = [(score + 1) / 2 for score in raw_pos_scores]

            if len(pos_scores) == len(pos_docs):
                pos_with_scores = [
                    {'content': doc, 'score': score}
                    for doc, score in zip(pos_docs, pos_scores)
                ]
            else:
                logging.warning(f"正样本分数数量({len(pos_scores)})与文档数量({len(pos_docs)})不一致")
                pos_success = False

        # 对负样本打分
        neg_with_scores = []
        neg_success = True
        if neg_docs:
            raw_neg_scores, neg_success = client.rerank(
                query, neg_docs, instruction,
                initial_batch_size=initial_batch_size
            )
            neg_scores = [score / 2 for score in raw_neg_scores]

            if len(neg_scores) == len(neg_docs):
                neg_with_scores = [
                    {'content': doc, 'score': score}
                    for doc, score in zip(neg_docs, neg_scores)
                ]
            else:
                logging.warning(f"负样本分数数量({len(neg_scores)})与文档数量({len(neg_docs)})不一致")
                neg_success = False

        # 构建结果对象
        result_item = {
            'query': query,
            'pos': pos_with_scores,
            'neg': neg_with_scores
        }

        # 保留原始数据中的其他字段
        for key, value in item.items():
            if key not in result_item:
                result_item[key] = value

        return result_item, True, (pos_success and neg_success)

    except Exception as e:
        logging.error(f"处理条目时出错: {str(e)}", exc_info=True)
        return None, False, False


def process_jsonl_concurrent(input_file: str, output_file: str, base_url: str,
                             instruction: Optional[str] = None,
                             initial_batch_size: int = 32,
                             max_workers: int = 15) -> None:
    """并发处理JSONL文件，使用线程池实现并行处理"""
    client = RerankClient(base_url=base_url)

    # 收集所有条目以便并发处理
    all_items = list(read_jsonl(input_file))
    total_items = len(all_items)

    processed_count = 0
    failed_count = 0
    partial_failed_count = 0  # 部分文档处理失败的条目数

    # 创建偏函数，固定部分参数
    process_func = partial(
        process_single_item,
        client=client,
        instruction=instruction,
        initial_batch_size=initial_batch_size
    )

    # 使用线程池并发处理
    with open(output_file, 'w', encoding='utf-8') as out_f, \
         concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

        # 提交所有任务
        futures = [executor.submit(process_func, item) for item in all_items]

        # 处理结果
        for future in tqdm(concurrent.futures.as_completed(futures), total=total_items, desc="处理进度"):
            result_item, item_success, full_success = future.result()

            if item_success and result_item:
                # 写入处理结果
                json.dump(result_item, out_f, ensure_ascii=False)
                out_f.write('\n')
                out_f.flush()
                processed_count += 1

                if not full_success:
                    partial_failed_count += 1
            else:
                failed_count += 1

    logging.info(f"处理完成，共处理{total_items}条数据")
    logging.info(f"成功{processed_count}条，完全失败{failed_count}条，部分失败{partial_failed_count}条")
    logging.info(f"结果已保存到{output_file}")


def main():
    parser = argparse.ArgumentParser(description='并发处理JSONL文件，对query和正负样本进行打分，支持失败重试')
    parser.add_argument('--input', required=True, help='输入JSONL文件路径')
    parser.add_argument('--output', required=True, help='输出JSONL文件路径')
    parser.add_argument('--url', default='http://localhost:8080', help='Rerank服务端地址，默认为http://localhost:8080')
    parser.add_argument('--instruction', help='可选的指令字符串')
    parser.add_argument('--batch-size', type=int, default=32, help='初始批次大小，默认为32')
    parser.add_argument('--min-batch-size', type=int, default=1, help='最小批次大小，默认为1')
    parser.add_argument('--max-workers', type=int, default=15, help='并发工作线程数，默认为15')

    args = parser.parse_args()

    process_jsonl_concurrent(
        input_file=args.input,
        output_file=args.output,
        base_url=args.url,
        instruction=args.instruction,
        initial_batch_size=args.batch_size,
        max_workers=args.max_workers
    )


if __name__ == "__main__":
    main()
