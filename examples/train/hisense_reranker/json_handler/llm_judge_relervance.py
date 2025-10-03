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




    # 创建客户端
    client = SimpleLLMClient(llm_configs=LLM_CONFIGS, default_llm="deepseek-v3")
    query = data['query']
    pos_contents = None
    if 'pos' in data.keys() and len(data['pos']) > 0:
        pos_contents = [item['content'] for item in data['pos']]
        pos_contents = '\n' + '\n'.join(pos_contents) + '\n'


    for neg in data['neg']:
        prompt = f'''请判断能否根据以下的片段回答指定的问题：{query}，
需要判断的片段：{neg['content']}
输出两行，第一行是1或者0，表示是否相关，第二行输出reason，不要带任何格式和标题'''
        if pos_contents:
            prompt = f'''请根据判断以下的片段是否能回答指定的问题：{query}，
可以参考的能回答的例子如下：{pos_contents}，需要判断的片段：{neg['content']}
输出两行，第一行是1或者0，表示是否相关，第二行输出reason，不要带任何格式和标题'''



        # 发送请求
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(
            messages=messages,
            temperature=0,
            max_retries=3
        )

        if 'error' in response:
            print('###########')

        neg['llm_relervance'] ,neg['llm_reson'] = response['choices'][0]['message']['content'].split('\n')







    return data