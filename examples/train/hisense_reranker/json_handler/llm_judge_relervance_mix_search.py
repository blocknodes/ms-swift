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
    client = SimpleLLMClient(llm_configs=LLM_CONFIGS, default_llm="gpt-4")
    query = data['query']

    qna_cadidates = [{'score':item['score'], 'filename':'', 'content':item['content']+'\n'+item['filename']} for item in data['qna'][:3]]
    candidates = data['doc'][:3] + qna_cadidates
    #import pdb;pdb.set_trace()
    candidates.sort(key=lambda x: x['score'], reverse=True)

    for item in candidates[:3]:
        filename = item['filename']
        block = item['content']

        prompt = f"""
你是一名专业的信息检索与问答评估专家。请根据用户提出的问题（query）和检索到的文本块（block）及其所在文件名（filename），从多维度严格判断该文本块与问题的相关性，并进行细粒度评分。请仅依据文本块本身内容进行判断，不考虑外部信息或来源。

请综合考虑以下方面：
1. 主体一致性：文本块内容结合文件名是否与问题的主语和核心主体高度一致。只有当内容紧密围绕问题主体展开，才可视为相关。
2. 事实/数据支持：文本块内容结合文件名是否为问题提供了直接或间接的事实、数据、证据或操作方法。仅当这些信息与问题主体高度相关时，才算有效支持。
3. 解释说明：文本块内容结合文件名是否对问题涉及的概念、原理、流程等进行了有效解释或补充说明。泛泛而谈或与问题主体无关的内容不计入相关性。
4. 语义相关性：文本块内容结合文件名与问题在语义上是否高度一致。仅有部分词汇相关但语义不一致的，相关性应为低分或零分。
5. 权威性与数据源：如文本块内容明确来自权威或与问题相关的数据来源，可适当提高相关性评分，但前提是内容与问题主体高度相关。
6. 对于问题中涉及具体产品的参数（如BCD-515P60FZMAD的产品尺寸是多少？等），文本块内容结合文件名是否准确匹配或高度相关。仅有部分匹配但不准确的，相关性应为低分或零分。
评分原则：相关性是指文本块内容结合文件名与用户问题的主体高度相关，仅以文本块结合文件名的本身内容为依据，不考虑文本块的来源或其他外部信息。例如，若问题为“海信空调”，而文本块内容为“海信抽油烟机”的说明，尽管两者都来自海信，但内容未涉及问题主体，因此相关性得分应很低。

评分细则：
- 10分：文本块内容能够完整、准确地回答用户问题，涵盖所有关键信息，与问题主语和主体高度相关，无遗漏或错误。
- 1-9分：文本块内容与问题主体有部分相关，能够部分回答问题，但信息不全或有细节缺失。分数越高，表示相关性越强，内容越接近完整答案。
- 0分：文本块内容与问题主体完全无关，无法提供任何有效信息，或仅与问题的部分词汇相关但未涉及问题主语和主体。
判定依据
- 仅当文本块内容紧密围绕问题主体展开，并能直接或间接回答问题时，才可视为相关。
- 仅有部分词汇或片段相关，但整体内容未涉及问题主体时，不应视为相关。
- 排除泛泛描述、主观评价、无事实或操作支持的内容。
输入：
用户问题（query）：{query}
文本块所在文件名（filename）：{filename}
检索文本块（block）：{block}

请将你的相关性评分以如下严格的 JSON 格式输出，无需其他说明，示例：
{{"score": 8}}
"""




        # 发送请求
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(
            messages=messages,
            temperature=0,
            max_retries=20
        )


        #print(f'####{response}')
        item['llm_relervance'] = json.loads(response['choices'][0]['message']['content'])['score']


    new_data = {}
    new_data['query'] = query
    new_data['top3'] = candidates[:3]
    if new_data['top3'][0]['llm_relervance'] >=8 :
        new_data['hit1'] = True
        return new_data
    if new_data['top3'][1]['llm_relervance'] >=8 or new_data['top3'][2]['llm_relervance'] >=8:
        new_data['hit3'] = True
    return new_data
