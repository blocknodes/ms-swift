import requests
import json
from typing import Dict, List, Optional
from typing import Callable, Dict, Any, Optional, List, Tuple
import random
import time
import os

class KbpRetrievalClient:
    """
    封装 KBP 混合检索 API 的客户端类
    """

    def __init__(self, base_url="https://inner-apisix-test.hisense.com",
                 user_key="qimfvt7lwtqeyangfl259vjg8fzdhh5l",
                 api_key="bb3ee9d4-ee46-4b84-9a65-16d1a185ef8e"):
        """
        初始化客户端

        :param base_url: API 基础地址
        :param user_key: 用户 key
        :param api_key: API 密钥
        """
        self.base_url = base_url.rstrip('/')
        self.user_key = user_key
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'api-key': self.api_key
        })

    def retrieval(self, query, top_k=5, score_threshold=0, search_mode='hybrid',
                 tracing_model=False, max_retries=10, initial_delay=0.5, backoff_factor=2.0):
        """
        执行检索请求（带退火重试机制）

        :param query: 查询文本
        :param top_k: 返回结果数量
        :param score_threshold: 分数阈值
        :param search_mode: 搜索模式
        :param tracing_model: 是否追踪模型
        :param max_retries: 最大重试次数
        :param initial_delay: 初始延迟时间（秒）
        :param backoff_factor: 退避因子
        :return: API 响应结果（字典）
        """
        url = f"{self.base_url}/kbp-test/openapi/kbp/mix/retrieval?user_key={self.user_key}"

        payload = {
            "retrieval_setting": {
                "top_k": top_k,
                "score_threshold": score_threshold,
                "search_mode": search_mode,
                "search_strategy":"precise",
            },
            "query": query,
            "tracingModel": tracing_model
        }

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                response = self.session.post(url, data=json.dumps(payload))
                response.raise_for_status()  # 如果状态码不是 200, 则引发 HTTPError 异常
                return response.json()
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries:
                    # 计算退避时间（带随机抖动）
                    delay = initial_delay * (backoff_factor ** attempt)
                    delay += random.uniform(0, 0.5 * delay)  # 添加随机抖动
                    print(f"请求失败（第 {attempt+1} 次）: {e}，将在 {delay:.2f} 秒后重试...")
                    time.sleep(delay)
                else:
                    print(f"已达到最大重试次数 ({max_retries})，请求最终失败: {e}")

        return None


def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    #time.sleep(5)
    module = os.getenv("MODULE", default="EMB")
    query = data['query']
    client = KbpRetrievalClient()
    result = client.retrieval(
        query=query,
        top_k=10,
        score_threshold=0,
        search_mode="hybrid",
        tracing_model=True
    )
    #import pdb;pdb.set_trace()
    new_data_list=[]
    recalls = result['records']['midRunResult']
    for round in result['records']['midRunResult']:
        new_data=None
        if round.startswith('Round'):
            subquery = round.split(': ',1)[1]


            if module == 'EMB':
                round_value = result['records']['midRunResult'][round]['segmentEsRecallResult']
            else:
                round_value = result['records']['midRunResult'][round]['segmentAfterRerankResult']
            new_data={}
            new_data['query'] = subquery
            new_data['segments'] = []

            for value in round_value:
                print(value)
                #import pdb;pdb.set_trace()
                new_data['segments'].append(value['segmentContent'])

            #import pdb;pdb.set_trace()


            new_data_list.append(new_data)

    #import pdb;pdb.set_trace()


    return new_data_list
# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    client = KbpRetrievalClient()

    query="HRB-550冰箱保鲜室有多大"
    # 执行检索
    result = client.retrieval(
        query=query,
        top_k=3,
        score_threshold=0,
        search_mode="hybrid",

        tracing_model=False
    )

    print(f'query is {query}')
    # 打印结果
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))