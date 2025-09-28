import json
import time
import random
import requests
from typing import Dict, List, Optional
from typing import Callable, Dict, Any, Optional, List, Tuple
import os



class SimpleLLMClient:
    """
    精简版LLM客户端，只保留自动重试功能
    """

    def __init__(self, llm_configs: Dict[str, Dict], default_llm: Optional[str] = None):
        """
        初始化LLM客户端

        Args:
            llm_configs: LLM模型配置字典
            default_llm: 默认使用的LLM模型名称
        """
        self.llm_configs = llm_configs
        self.default_llm = default_llm or next(iter(llm_configs.keys()))

        if self.default_llm not in self.llm_configs:
            raise ValueError(f"默认模型 {self.default_llm} 不在配置中")

    def _prepare_request_parameters(self, llm_name: str) -> tuple:
        """准备LLM API请求的URL和headers"""
        config = self.llm_configs[llm_name]

        # 处理URL参数
        url_params = config["url_params"]
        if url_params:
            formatted_params = {k: v.format(key=config["key"]) for k, v in url_params.items()}
            query_string = "&".join([f"{k}={v}" for k, v in formatted_params.items()])
            request_url = f"{config['url']}?{query_string}"
        else:
            request_url = config["url"]

        # 处理请求头
        headers = {k: v.format(key=config["key"]) for k, v in config["headers"].items()}

        return request_url, headers

    def _create_payload(self, llm_name: str, messages: List[Dict[str, str]],
                       temperature: float = 0, n: int = 1, **kwargs) -> Dict:
        """创建LLM API请求的payload"""
        return {
            "model": self.llm_configs[llm_name]["model"],
            "messages": messages,
            "temperature": temperature,
            "n": n,
            **kwargs
        }

    def chat_completion(self, messages: List[Dict[str, str]], llm_name: Optional[str] = None,
                       temperature: float = 0, n: int = 1, max_retries: int = 3,
                       initial_delay: float = 1.0, **kwargs) -> Dict:
        """
        调用LLM的聊天接口，带自动重试功能

        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "..."}, ...]
            llm_name: LLM模型名称，不提供则使用默认模型
            temperature: 温度参数
            n: 返回结果数量
            max_retries: 最大重试次数
            initial_delay: 初始延迟时间（秒）
            **kwargs: 其他payload参数

        Returns:
            LLM返回的JSON响应
        """
        llm_name = llm_name or self.default_llm
        if llm_name not in self.llm_configs:
            raise ValueError(f"未知的LLM模型: {llm_name}")

        payload = self._create_payload(llm_name, messages, temperature, n, **kwargs)
        request_url, headers = self._prepare_request_parameters(llm_name)

        # 带指数退避的重试机制
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(request_url, json=payload, headers=headers, timeout=30)

                if response.status_code == 200:
                    return response.json()

                # 非200状态码，准备重试
                if attempt < max_retries:
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    time.sleep(delay)
                else:
                    return {"error": f"API请求失败，状态码: {response.status_code}", "details": response.text}

            except Exception as e:
                # 发生异常，准备重试
                if attempt < max_retries:
                    delay = initial_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    time.sleep(delay)
                else:
                    return {"error": "调用LLM时发生错误", "details": str(e)}

        return {"error": "达到最大重试次数"}



def read_jsonl(file_path=None):
    """读取 jsonl 文件，返回 list[dict]"""
    if file_path is None:
        file_path = os.environ.get('ORIG_FILE_PATH')
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            data.append(obj)
    return data

# 示例处理函数 - 当不指定外部处理器时使用
def example_processor(data: Dict[str, Any]) -> Dict[str, Any]:
    # LLM配置
    LLM_CONFIGS = {
        "deepseek-v3": {
            "url": "http://10.18.217.60:30264/xinghai-aliyun-ds-v3/v1/chat/completions",
            "headers": {"Content-Type": "application/json", "Authorization": "Bearer {key}"},
            "key": "",
            "model": "deepseek-v3",
            "url_params": {}
        },
        "gpt-4": {
            "url": "https://inner-apisix.hisense.com/openai/deployments/gpt-4-1/chat/completions",
            "headers": {"Content-Type": "application/json", "api-key": "Oi4rzFyLbMOmqVn8YYEyT2Pt0mkr3lgU"},
            "key": "nregzh6g2oviajyjstgzlhjsjmp9rtql",
            "model": "gpt-4-1",
            "url_params": {"user_key": "{key}"}
        }
    }

    orig_data = read_jsonl()

    # 创建客户端
    client = SimpleLLMClient(llm_configs=LLM_CONFIGS, default_llm="deepseek-v3")
    query = data['query']
    neg_contents = []
    for item in orig_data:
        if item['query'] == query:
            filename = item['filename']
            content = item['content']
        else:
            neg_contents.append(item['content'])

    neg_contents = random.sample(neg_contents, k=3)

    # 发送请求
    messages = [{"role": "user", "content": f"文件名：{filename}n请生成更加简洁的文件名，注意，仅输出文件名,不加序号，每行一个"}]
    response = client.chat_completion(
        messages=messages,
        temperature=0,
        max_retries=3
    )

    pos_filenames = random.sample(response['choices'][0]['message']['content'].split('\n'), k=3)

    # 发送请求
    messages = [{"role": "user", "content": f"文件名：{filename}n请生成型号随机的文件名，注意，仅输出文件名,不加序号，每行一个"}]
    response = client.chat_completion(
        messages=messages,
        temperature=0,
        max_retries=3
    )

    neg_filenames = random.sample(response['choices'][0]['message']['content'].split('\n'), k=3)
    #import pdb;pdb.set_trace()

    new_data = {}
    new_data['query'] = query
    new_data['pos'] = [{'filename':'', 'content':content}]
    new_data['pos'].extend({'filename': item, 'content':content} for item in pos_filenames)

    ### pos filename + neg content 3 samples
    negatives = []
    for neg_content in neg_contents:
        negatives.append({'filename': filename, 'content': neg_content})

    ### neg filename + pos content 3 samples
    for filename in neg_filenames:
        negatives.append({'filename': filename, 'content': content})

    ### neg filename + neg content 1 sample
    negatives.append({'filename': neg_filenames[-1], 'content': neg_contents[0]})

    new_data['neg'] = negatives




    return new_data