import requests
import logging
import time
import threading
from typing import List, Optional, Dict
import sys
import random
import string
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class RerankClient:
    def __init__(self, base_url: str = "https://inner-apisix-test.hisense.com/kbp/rerank",
                 user_key: str = "sxwox9bfz6hrunpeo4dsndfjtniaqmj3"):
        """初始化Rerank客户端"""
        self.base_url = base_url
        self.user_key = user_key
        self.rerank_endpoint = f"{self.base_url}/rerank"
        logging.info(f"Rerank client initialized with endpoint: {self.rerank_endpoint}")

    def rerank(self, query: str, documents: List[str], instruction: Optional[str] = None) -> Dict:
        """发送排序请求到服务端"""
        if not documents:
            logging.warning("文档列表为空，直接返回空结果")
            return {"scores": []}

        # 构建请求数据
        payload = {
            "query": query,
            "documents": documents,
            "instruction": instruction
        }

        # 构建请求参数（包含user_key）
        params = {
            "user_key": self.user_key
        }

        try:
            # 发送POST请求
            start_time = time.time()
            response = requests.post(
                self.rerank_endpoint,
                json=payload,
                params=params,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            end_time = time.time()
            rt = (end_time - start_time) * 1000  # 转换为毫秒

            response.raise_for_status()
            result = response.json()
            logging.debug(f"排序请求成功，RT: {rt:.2f}ms")
            return {"result": result, "rt": rt}

        except requests.exceptions.RequestException as e:
            end_time = time.time()
            rt = (end_time - start_time) * 1000
            logging.error(f"排序请求失败: {str(e)}, RT: {rt:.2f}ms")
            return {"result": None, "rt": rt, "error": str(e)}

    def rerank_and_sort(self, query: str, documents: List[str], instruction: Optional[str] = None) -> Dict:
        """发送排序请求并返回带分数的排序结果及响应时间"""
        result = self.rerank(query, documents, instruction)
        if "error" in result:
            return {
                "ranked_docs": [],
                "rt": result["rt"],
                "error": result["error"]
            }

        try:
            # 解析分数
            if "scores" in result["result"]:
                scores = result["result"]["scores"]
            else:
                scores = [item['relevance_score'] for item in result["result"]['data'][0]['value']]

            # 确保分数数量与文档数量一致
            if len(scores) != len(documents):
                logging.warning(f"分数数量({len(scores)})与文档数量({len(documents)})不一致")
                return {
                    "ranked_docs": [],
                    "rt": result["rt"],
                    "error": "分数与文档数量不匹配"
                }

            # 组合并排序
            ranked_docs = [
                {"document": doc, "score": score}
                for doc, score in zip(documents, scores)
            ]
            ranked_docs.sort(key=lambda x: x["score"], reverse=True)

            return {
                "ranked_docs": ranked_docs,
                "rt": result["rt"],
                "error": None
            }

        except Exception as e:
            logging.error(f"处理排序结果失败: {str(e)}")
            return {
                "ranked_docs": [],
                "rt": result["rt"],
                "error": str(e)
            }

def generate_random_document(token_count: int = 200) -> str:
    """生成指定token数量的随机文档（假设1token≈1.3个字符）"""
    chars_per_token = 1.3
    total_chars = int(token_count * chars_per_token)

    # 生成随机字符串，包含空格和标点以模拟自然语言
    letters = string.ascii_letters + " " + ",.?!;:"
    return ''.join(random.choice(letters) for _ in range(total_chars)).strip()

def generate_test_data(doc_count: int = 40, token_count: int = 200) -> tuple:
    """生成测试用的查询和文档列表"""
    query = f"这是一个测试查询 {random.randint(1000, 9999)}，用于评估排序服务的性能"
    documents = [generate_random_document(token_count) for _ in range(doc_count)]
    return query, documents

def worker(client: RerankClient, results: list, doc_count: int, token_count: int, stop_event: threading.Event):
    """压测工作线程，持续发送请求直到收到停止信号"""
    thread_name = threading.current_thread().name
    logging.debug(f"线程 {thread_name} 启动")

    while not stop_event.is_set():
        # 生成新的测试数据
        query, documents = generate_test_data(doc_count, token_count)

        # 发送请求并记录结果
        start_time = time.time()
        result = client.rerank_and_sort(query, documents)
        result["timestamp"] = start_time  # 记录请求开始时间
        results.append(result)

        # 短暂休眠避免请求过于密集（可根据需要调整）
        # time.sleep(0.01)

    logging.debug(f"线程 {thread_name} 收到停止信号，退出")

def run_load_test(
    client: RerankClient,
    concurrency: int = 7,
    doc_count: int = 40,
    token_count: int = 200,
    duration: int = 30  # 压测持续时间（秒）
):
    """运行指定时长的负载测试"""
    logging.info(
        f"开始压测 - 并发数: {concurrency}, "
        f"每个请求文档数: {doc_count}, "
        f"每个文档token数: {token_count}, "
        f"持续时间: {duration}秒"
    )

    start_time = time.time()
    end_time = start_time + duration
    stop_event = threading.Event()
    threads = []
    results = []

    # 创建并启动所有线程
    for i in range(concurrency):
        thread = threading.Thread(
            target=worker,
            args=(client, results, doc_count, token_count, stop_event),
            name=f"worker-{i+1}"
        )
        threads.append(thread)
        thread.start()
        logging.debug(f"启动线程: {thread.name}")

    # 等待指定时长
    try:
        remaining = end_time - time.time()
        while remaining > 0:
            # 每0.1秒检查一次
            time.sleep(min(0.1, remaining))
            remaining = end_time - time.time()
    except KeyboardInterrupt:
        logging.info("收到中断信号，提前结束压测")

    # 发送停止信号并等待所有线程完成
    stop_event.set()
    for thread in threads:
        thread.join()
        logging.debug(f"线程完成: {thread.name}")

    total_elapsed = (time.time() - start_time) * 1000  # 总耗时(毫秒)

    # 统计结果
    rts = []
    errors = 0
    total_requests = len(results)

    for res in results:
        if res["error"]:
            errors += 1
            # 只打印前10个错误详情，避免日志过多
            if errors <= 10:
                logging.warning(f"请求错误: {res['error']}")
        else:
            rts.append(res["rt"])

    # 计算统计指标
    if rts:
        avg_rt = sum(rts) / len(rts)
        min_rt = min(rts)
        max_rt = max(rts)
        # 计算分位数
        sorted_rts = sorted(rts)
        p90_idx = int(len(sorted_rts) * 0.9)
        p90_rt = sorted_rts[p90_idx] if p90_idx < len(sorted_rts) else sorted_rts[-1]
        p95_idx = int(len(sorted_rts) * 0.95)
        p95_rt = sorted_rts[p95_idx] if p95_idx < len(sorted_rts) else sorted_rts[-1]
    else:
        avg_rt = min_rt = max_rt = p90_rt = p95_rt = None

    # 计算吞吐量（每秒请求数）
    throughput = total_requests / (total_elapsed / 1000) if total_elapsed > 0 else 0

    # 输出统计结果
    logging.info("\n===== 压测结果统计 =====")
    logging.info(f"压测时长: {total_elapsed:.2f}ms ({duration}秒预期)")
    logging.info(f"总请求数: {total_requests}")
    logging.info(f"成功请求数: {len(rts)}")
    logging.info(f"失败请求数: {errors}")
    logging.info(f"成功率: {len(rts)/total_requests*100:.2f}%" if total_requests > 0 else "成功率: 0%")
    logging.info(f"吞吐量: {throughput:.2f} 请求/秒")
    if rts:
        logging.info(f"平均响应时间(RT): {avg_rt:.2f}ms")
        logging.info(f"最小响应时间: {min_rt:.2f}ms")
        logging.info(f"最大响应时间: {max_rt:.2f}ms")
        logging.info(f"90%响应时间(P90): {p90_rt:.2f}ms")
        logging.info(f"95%响应时间(P95): {p95_rt:.2f}ms")
    logging.info("=========================")

if __name__ == "__main__":
    # 解析端口参数
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logging.warning(f"无效端口参数: {sys.argv[1]}, 使用默认端口 {port}")

    # 创建客户端实例
    client = RerankClient(base_url=f"http://localhost:{port}")

    # 运行压测（7并发，每个请求40个文档，每个文档200token，持续30秒）
    run_load_test(
        client=client,
        concurrency=7,
        doc_count=40,
        token_count=200,
        duration=30  # 半分钟
    )