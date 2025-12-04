import requests
import json
from typing import Dict, List, Optional, Any, Callable, Tuple
import random
import time

class KbpRetrievalClient:
    """
    封装 KBP 混合检索 API 的客户端类（兼容新接口）
    """

    def __init__(self, base_url="https://inner-apisix.hisense.com",
                 user_key="zzk5q1zvcyifdosdcmdnxqwhachp650o",
                 api_key: Optional[str] = None,
                 default_user_id: str = "piaochengyin"):
        """
        初始化客户端

        :param base_url: API 基础地址
        :param user_key: 用户 key（新接口默认值已更新）
        :param api_key: API 密钥（新接口可能不需要，设为可选）
        :param default_user_id: 默认用户ID（新接口必填参数）
        """
        self.base_url = base_url.rstrip('/')
        self.user_key = user_key
        self.default_user_id = default_user_id
        self.session = requests.Session()

        # 新接口请求头只需要Content-Type（如果需要api-key可保留）
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['api-key'] = api_key
        self.session.headers.update(headers)

    def retrieval(self, query: str,
                 top_k: int = 3,
                 score_threshold: float = 0.11,
                 search_mode: str = 'hybrid',
                 user_id: Optional[str] = None,
                 search_source: int = 2,
                 dir_request_list: Optional[List[Dict]] = None,
                 max_retries: int = 10,
                 initial_delay: float = 0.5,
                 backoff_factor: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        执行检索请求（兼容新接口，带退火重试机制）

        :param query: 查询文本
        :param top_k: 返回结果数量（新接口默认3）
        :param score_threshold: 分数阈值（新接口默认0.11）
        :param search_mode: 搜索模式（默认hybrid）
        :param user_id: 用户ID（新接口必填，默认使用初始化时的default_user_id）
        :param search_source: 搜索源（新接口必填，默认2）
        :param dir_request_list: 目录请求列表（新接口参数，默认None）
        :param max_retries: 最大重试次数
        :param initial_delay: 初始延迟时间（秒）
        :param backoff_factor: 退避因子
        :return: API 响应结果（字典）
        """
        # 构建完整URL（新接口路径和user_key已更新）
        url = f"{self.base_url}/kbp/openapi/kbp/mix/retrieval?user_key={self.user_key}"

        # 构建请求体（完全匹配新接口格式）
        payload = {
            "query": query,
            "user_id": user_id or self.default_user_id,  # 使用默认用户ID或传入的ID
            "retrieval_setting": {
                "top_k": top_k,
                "score_threshold": score_threshold,
                "search_mode": search_mode
            },
            "searchSource": search_source,
            "dirRequestList": dir_request_list,
            "tracingModel": True
        }

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                response = self.session.post(url, data=json.dumps(payload))
                response.raise_for_status()  # 如果状态码不是2xx，引发HTTPError异常
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
    """
    示例处理器：调用检索接口并格式化结果
    """

    query = data['query']
    # 可自定义用户ID和其他参数
    user_id = data.get('user_id')  # 从输入数据获取user_id，没有则使用默认值
    client = KbpRetrievalClient()

    result = client.retrieval(
        query=query,
        user_id=user_id,
        top_k=10,
        score_threshold=0.11,
        search_mode="hybrid",
        search_source=2,
        dir_request_list=None,
    )

    new_data = {
        'query': data['query'],
        'user_id': user_id or client.default_user_id,
        'finals': []
    }

    if result and 'records' in result and 'finalRecallResult' in result['records']:
        finals = result['records']['finalRecallResult']
        # 格式化结果（根据实际返回字段调整）
        new_data['finals'] = [
            {
                'kind': item.get('metadata', {}).get('kind', ''),
                'filename': item.get('file_name', ''),
                'title': item.get('title', ''),
                'content': item.get('content', ''),
                'score': item.get('score', 0.0),
                'human_judge': 0
            } for item in finals
        ]
    else:
        print(f"检索结果格式异常或为空: {result}")

    time.sleep(5)

    return new_data


# 使用示例
if __name__ == "__main__":
    # 初始化客户端（可自定义参数）
    client = KbpRetrievalClient(
        base_url="https://inner-apisix.hisense.com",
        user_key="zzk5q1zvcyifdosdcmdnxqwhachp650o",
        default_user_id="piaochengyin"
    )

    # 示例1：使用默认参数查询
    query = "WG100R6的内桶直径是多少？"
    print(f'query is {query}')
    result = client.retrieval(
        query=query,
        top_k=3,
        score_threshold=0.11,
        search_mode="hybrid"
    )

    # 打印结果
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n" + "="*50 + "\n")

    # 示例2：使用processor处理数据
    input_data = {
        'query': "HRB-550冰箱保鲜室有多大",
        'user_id': "piaochengyin"  # 自定义用户ID
    }
    processed_result = example_processor(input_data)
    print("处理器输出结果：")
    print(json.dumps(processed_result, ensure_ascii=False, indent=2))