#!/usr/bin/env python
import uvicorn
import logging
import math
import gc
import sys
import re
import json
import time
from typing import Optional, List, Dict, Any, Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from vllm.distributed.parallel_state import destroy_model_parallel
from vllm.inputs.data import TokensPrompt
import torch
from log import init_logger
import random
import requests
from bm25 import ChineseBM25

# 初始化日志

import random
import requests

import asyncio
import aiohttp

logger = init_logger("rerank.log")
__all__ = ['logger', 'init_logger']

# 初始化FastAPI应用
app = FastAPI(title="Rerank Service (vllm backend)")
class AsyncChatCompletionClient:
    """异步调用Chat Completions API的客户端（适配FastAPI异步环境）"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        default_model: str = "filter"  # 默认模型名称
    ):
        """
        初始化客户端

        Args:
            base_url: API基础地址
            timeout: 请求超时时间（秒）
            headers: 自定义请求头
            default_model: 默认使用的模型名称（批量请求时自动使用）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = headers or {"Content-Type": "application/json"}
        self.default_model = default_model

    async def create_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        异步创建单个聊天补全请求

        Args:
            model: 模型名称（如filter）
            messages: 消息列表，格式为[{"role": "...", "content": "..."}]
            **kwargs: 其他可选参数（如temperature、max_tokens等）

        Returns:
            API响应数据（字典格式）

        Raises:
            aiohttp.ClientError: HTTP请求错误
            asyncio.TimeoutError: 请求超时
            ValueError: 响应JSON解析失败
        """
        # 构建请求体
        payload = {
            "model": model,
            "messages": messages,** kwargs
        }

        # 发送POST请求（复用客户端会话，提升性能）
        async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
            try:
                async with session.post(
                    url=f"{self.base_url}/v1/chat/completions",
                    json=payload
                ) as response:
                    # 检查HTTP状态码
                    response.raise_for_status()

                    # 解析JSON响应
                    try:
                        return await response.json()
                    except ValueError as e:
                        raise ValueError(f"响应JSON解析失败: {e}") from e

            except aiohttp.ClientError as e:
                raise aiohttp.ClientError(f"HTTP请求失败: {e}") from e
            except asyncio.TimeoutError as e:
                raise asyncio.TimeoutError(f"请求超时（{self.timeout.total}秒）") from e

    async def batch_requests(
        self,
        query: str,
        content_list: List[str],  # 仅接收content字符串列表
        model: Optional[str] = None,** kwargs: Any
    ) -> List[Union[Dict[str, Any], Exception]]:
        """
        异步批量执行多个聊天补全请求（仅需传入content列表）

        Args:
            content_list: 内容字符串列表，每个元素对应一个请求的content
            model: 可选，指定模型名称（默认使用客户端初始化的default_model）
            **kwargs: 其他请求参数（如temperature、max_tokens等）

        Returns:
            按请求顺序返回的结果列表，每个元素为响应字典或异常对象
        """
        # 使用指定模型或默认模型
        target_model = model or self.default_model

        # 构建完整的请求参数列表（自动封装message格式）

        requests = [
            {
                "model": target_model,
                "messages": [{"role": "user", "content": content}],** kwargs
            }
            for content in [query]+content_list
        ]

        # 创建异步任务列表
        tasks = [
            self.create_chat_completion(**req)
            for req in requests
        ]

        # 并发执行所有任务（return_exceptions=True 避免单个失败导致整体失败）
        results = await asyncio.gather(*tasks, return_exceptions=True)

        results = [item['choices'][0]['message']['content'] for item in results]
        print(results)
        if results[0] == '无':
            return {'scores':[1 * len(content_list)]}
        else:
            scores = []
            for item in results[1:]:
                if item == results[0] or item == '无':
                    scores.append(1)
                else:
                    scores.append(0)



            return  {'scores': scores}

# ========== 数据模型 ==========
class QADocs(BaseModel):
    query: Optional[str]
    documents: Optional[List[str]]
    meta_data: Optional[List[dict]] = None  # 新增可选字段
    instruction: Optional[str] = None      # 新增可选字段



class RerankClient:
    def __init__(self, base_url: str = "https://inner-apisix-test.hisense.com/kbp/rerank",
                 user_key: str = "sxwox9bfz6hrunpeo4dsndfjtniaqmj3"):
        """
        初始化Rerank客户端

        Args:
            base_url: 服务端基础地址，默认为"https://inner-apisix-test.hisense.com/kbp/rerank"
            user_key: 访问API的用户密钥
        """
        self.base_url = base_url
        self.user_key = user_key
        self.rerank_endpoint = f"{self.base_url}/rerank"
        logging.info(f"Rerank client initialized with endpoint: {self.rerank_endpoint}")

    def rerank(self, query: str, documents: List[str], instruction: Optional[str] = None) -> Dict:
        """
        发送排序请求到服务端

        Args:
            query: 查询字符串
            documents: 文档列表
            instruction: 可选的指令字符串

        Returns:
            包含排序分数的字典，格式为{"scores": [分数列表]}
        """
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
            logging.info(f"发送排序请求，查询: {query[:50]}..., 文档数量: {len(documents)}")
            response = requests.post(
                self.rerank_endpoint,
                json=payload,
                params=params,  # 将user_key放在URL参数中
                headers={"Content-Type": "application/json"},
                timeout=60  # 设置超时时间
            )

            # 检查响应状态
            response.raise_for_status()

            # 返回结果
            result = response.json()
            logging.info(f"排序请求成功，返回{len(result.get('scores', []))}个分数")
            return result

        except requests.exceptions.RequestException as e:
            logging.error(f"排序请求失败: {str(e)}")
            return {"scores": []}


class ReRanker():
    def __init__(self, base_url):
        self.base_url = base_url
        # 初始化异步客户端（复用，避免重复创建）
        self.filter_client = AsyncChatCompletionClient()

    def preprocess(self, text: str) -> str:
        """文本预处理，保留原有的清洗逻辑"""
        if not text:
            return ""
        text = re.sub(r'!\[\]\([^)]*\)', '', text)  # 去除图片链接
        text = re.sub(r'\s+', ' ', text)  # 合并空格
        text = re.sub(r'([^a-zA-Z0-9\s])\1{1,}', r'\1', text)  # 去除重复标点
        return text.strip()

    def clear_and_duplicate(self, q_d: QADocs) -> (List[str], List[int]):
        """移除去重逻辑，文档原样保留，索引按序返回（保持原有数据结构）"""
        unique_docs = []
        original_indices = []

        for idx, doc in enumerate(q_d.documents):
            cleaned_doc = self.preprocess(doc)
            # 保留所有文档，不做去重
            unique_docs.append(cleaned_doc)
            # 每个索引以列表形式存储，保持原有数据结构
            original_indices.append([idx])

        return unique_docs, original_indices


    async def compute(self, query: str, documents: List[str], instruction: str, type:str='doc',meta_data:dict=None):
        """使用vllm模型计算相关性分数"""

        if not query or not documents:
            return []
        # 构建查询-文档对
        client_configs = {
            'doc': [
                ("http://10.18.231.31:30287/", "reranker_q"),  # client1
                ("http://10.18.231.47:30374/", "reraner-copy"),  # client3 (备用)
                ("http://10.18.231.46:30642/", "reranker-filter")  # client2

            ],
            'qna': [
                ("http://10.18.231.31:30287/", "reranker_q"),  # client1
                ("http://10.18.231.47:30374/", "reraner-copy"),  # client1
                ("http://10.18.231.46:30642/", "reranker-filter")  # client2 (备用)
            ]
        }
        pairs = [(query, doc) for doc in documents]
        # 尝试使用配置的客户端，直到成功或全部失败
        configs = client_configs.get(type, client_configs['doc'])
        for idx, (base_url, client_name) in enumerate(configs):
            logger.info(f"尝试使用{client_name}客户端 (地址: {base_url})，序号: {idx+1}")
            client = RerankClient(base_url=base_url)
            ranked_results = client.rerank(query, documents, instruction)
            print(f'#######{ranked_results} {len(ranked_results)}')
            if 'scores' in ranked_results and len(ranked_results['scores']) != 0:
                logger.info(f"成功使用{client_name}客户端获取结果")
                break  # 成功则退出循环

        if type not in ['doc', 'qna']:
            ranked_results = await self.filter_client.batch_requests(
                query = query,
                content_list=documents
                # 可选：指定模型 model="custom-model"
                # 可选：传入其他参数 temperature=0.7
            )
        ### 兼容vllm serve 暂时不用
        if 'scores' not in ranked_results:
            #assert False
            ranked_results['scores']=[item['relevance_score'] for item in ranked_results['data'][0]['value']]#['results']]
        #print(ranked_results)
        if type=='doc':
            for i in range(len(documents)):
                documents[i] = documents[i]+meta_data[i]['fileName']
                #print(f'######!!!!!!{documents}')

        bm25 = ChineseBM25(documents)
        results = bm25.rank(query, top_n=100)
        alpha=0.1
        beta=1-alpha
        print(results)


        for i in range(len(ranked_results['scores'])):
            #print(results)
            ranked_results['scores'][i] = alpha*results[i][1] + beta* ranked_results['scores'][i]
        #print(f"####{ranked_results['scores']}")
        return ranked_results['scores']


# ========== API 路由 ==========
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post('/rerank')
async def handle_post_request(docs: QADocs):
    start_time = time.time()
    try:
        logger.info("收到重排序请求")
        meta_data=docs.meta_data
        logger.info(f"meta_data is {meta_data}")

        type='doc'
        if meta_data:
            type='qna'
            for item in meta_data:
                if item['kind'] != 'qna':
                    type = 'doc'
                    break



        # 验证输入
        if not docs.query or not docs.documents:
            logger.warning("查询或文档列表为空")
            return {"code": 0, "data": []}



        # 文档去重
        reranker = ReRanker("http://10.18.231.47:30373/")
        unique_docs, original_indices = reranker.clear_and_duplicate(docs)
        if not unique_docs:
            logger.info("去重后文档为空")
            return {"code": 0, "data": []}

        # 获取指令(使用默认值如果未提供)
        instruction = docs.instruction or "Given a web search query, retrieve relevant passages that answer the query"

        # 计算分数
        scores = await reranker.compute(docs.query, unique_docs, instruction, type, meta_data)


    # 映射分数到原始索引
        score_map = {}
        for idx_list, score in zip(original_indices, scores):
            for idx in idx_list:
                score_map[idx] = float(score)
        restored_scores = [score_map[i] for i in range(len(docs.documents))]

        # 构建结果
        results = [
            {"index": i, "relevance_score": score}
            for i, score in enumerate(restored_scores)
        ]
        response_data = {
            "code": 0,
            "data": [{
                "value": results,
                "status": 0,
                "detail": "",
                "msg": ""
            }]
        }

        # 记录处理时间
        elapsed_time = time.time() - start_time
        logger.info(f"请求处理成功，耗时 {elapsed_time:.3f} 秒. 请求内容: {json.dumps(docs.dict(), ensure_ascii=False)}. 响应内容: {response_data}")
        return response_data

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.exception(f"请求处理失败，耗时 {elapsed_time:.3f} 秒. 请求内容: {json.dumps(docs.dict(), ensure_ascii=False)}. 错误信息: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

# ========== 启动服务 ==========
if __name__ == "__main__":
    try:
        # 解析命令行参数
        logger.info(f"启动服务")
        uvicorn.run(app, host='0.0.0.0', port=8080, reload=False)
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        print(f"API启动失败！\n报错：\n{e}")