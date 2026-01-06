import jieba
import math
import re
from collections import defaultdict
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import asyncio
import aiohttp
import json

# 初始化FastAPI应用
app = FastAPI(title="Chinese Precise Matching Text Retrieval API", version="1.0")

# ===================== 原有代码（仅修改BM25相关部分） =====================
class AsyncChatCompletionClient:
    """异步调用Chat Completions API的客户端（适配FastAPI异步环境）"""

    def __init__(
        self,
        base_url: str = "http://10.18.231.45:30642",
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
        async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
            try:
                async with session.post(
                    url=f"{self.base_url}/v1/chat/completions",
                    json=payload
                ) as response:
                    response.raise_for_status()
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
        requests = [
            {
                "model": target_model,
                "messages": [{"role": "user", "content": content}],** kwargs
            }
            for content in [query]+content_list
        ]
        tasks = [
            self.create_chat_completion(**req)
            for req in requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        results = [item['choices'][0]['message']['content'] for item in results]
        return json.loads(results[0])


# 正则模式定义
pattern = '(?!-)[A-Za-z0-9/-]*[A-Za-z0-9/](?<!-)'

# -------------------------- 工具函数 --------------------------
def split_num_alpha(s: str) -> List[str]:
    """拆分数字+字母组合（如85U8N → 85、U8N）"""
    pattern = r'^(\d+)([A-Za-z].*)$'
    match = re.match(pattern, s)
    if match:
        return [match.group(1), match.group(2)]
    return [s]

def clean_and_split(words: List[str]) -> List[str]:
    """清理空值+拆分混合字符串"""
    cleaned = []
    for word in words:
        stripped_word = word.strip()
        if not stripped_word:
            continue
        split_parts = split_num_alpha(stripped_word)
        cleaned.extend(split_parts)
    return cleaned

# -------------------------- 精准匹配核心类 --------------------------
class ChinesePreciseMatching:
    def __init__(self, documents: List[str], k1: float = 0.2, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        jieba.suggest_freq(("激光", "电视"), True)
        jieba.add_word("激光电视", freq=1000)
        jieba.add_word("强制恢复", freq=1000)
        self.stop_words = set(['的', '了', '是', '在', '和', '有', '我', '也', '很', '就', '/','pdf','vip'])
        self.whitelist = set(['折扣','强制恢复','恢复','制冷','制热','实时','开机','关机','电视','空调','激光电视','进水', '排水', '洗衣机', '洗碗机','油烟机','冰箱','空调','电视','平板电视','洗衣机','冷柜','洗碗机','变温柜','电热水器','燃气灶','投影'])
        self.conflict_map={'空调':['油烟机'],'恢复':['强制恢复']}
        self.productlist = set(['油烟机','冰箱','空调','电视','洗衣机','冷柜','洗碗机','变温柜','电热水器','燃气灶','投影','微波炉'])
        self._preprocess()
        self._calc_avgdl()
        self._calc_idf()
        self.model_blacklist=['vip']
        self.model_cutoff=-0.25



    def _preprocess(self):
        """预处理：分词、过滤、统计文档频率"""
        self.corpus = []
        self.word_count = defaultdict(int)

        for doc in self.documents:
            words = jieba.lcut(doc, cut_all=True)
            filtered_words = clean_and_split(words)
            final_words = [
                word.lower() for word in filtered_words
                if word not in self.stop_words and (word in self.whitelist or re.search(pattern, word))
            ]
            print(f'final words: {final_words}')
            self.corpus.append(final_words)

            # 更新文档频率
            for word in set(final_words):
                self.word_count[word] += 1

    def _calc_avgdl(self):
        """计算平均文档长度"""
        total_length = sum(len(doc) for doc in self.corpus)
        self.avgdl = total_length / len(self.corpus) if len(self.corpus) > 0 else 0

    def _calc_idf(self):
        """计算IDF值"""
        self.idf = {}
        N = len(self.documents)
        for word, df in self.word_count.items():
            self.idf[word] = math.log((N - df + 0.5) / (df + 0.5) + 1)

    def filter(self, query: str) -> float:
        query_product_set = set()
        doc_product_set_list = []
        for i in range(len(self.documents)):
            doc_product_set_list.append(set())

        for word in self.productlist:
            if word in query:
                query_product_set.add(word)
            for i in range(len(self.documents)):
                if word in self.documents[i]:
                    doc_product_set_list[i].add(word)

        result = []

        if len(query_product_set) == 0:
            return [1] * len(self.documents)

        print(f'*** {query_product_set}  \n{self.documents} \n{doc_product_set_list} \n\n{zip(self.documents,doc_product_set_list)}')

        for i in range(len(self.documents)):
            if len(query_product_set) == 0 or len(doc_product_set_list[i])==0 or not query_product_set.isdisjoint(doc_product_set_list[i]):
                result.append(1)
            else:
                result.append(0)
        return result




    def get_score(self, query: str, doc_idx: int, meta_data: dict) -> float:
        """计算单个文档的精准匹配得分"""
        doc = self.corpus[doc_idx]
        doc_length = len(doc)
        model = meta_data['model'] if 'model' in meta_data else None
        print(self.corpus[doc_idx])
        print(f'#### model is {model}#####')
        if model and model.lower() not in self.documents[doc_idx].lower() and model.lower() not in self.model_blacklist:
            return self.model_cutoff

        # 处理查询词
        query_words = jieba.lcut(query)
        filtered_words = clean_and_split(query_words)
        query_words = [
            word for word in filtered_words
            if word not in self.stop_words and (word in self.whitelist or re.search(pattern, word))
        ]

        print(f'query words: {query_words}')

        for word in query_words:
            if word in self.conflict_map:
                for conflit in self.conflict_map[word]:
                    if conflit in self.documents[doc_idx]:
                        return self.model_cutoff

        score = 0.0
        for word in query_words:
            if word not in self.idf:
                continue
            tf = doc.count(word)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avgdl))
            score += self.idf[word] * (tf * (self.k1 + 1)) / denominator
        return score

    def get_normalized_scores(self, query: str, meta_data: dict) -> List[float]:
        """获取所有文档的归一化得分（0-1）"""
        # 计算原始得分

        raw_scores = [self.get_score(query, i, meta_data) for i in range(len(self.documents))]
        #return raw_scores

        # 处理空值和相同值情况
        if not raw_scores:
            return []


        min_score = min(raw_scores)
        if min_score==self.model_cutoff:
            print('EEEEEE####')
            min_score = 0
        max_score = max(raw_scores)
        if max_score==self.model_cutoff:
            max_score =0.1

        # 归一化到0-1
        normalized_scores = []
        if max_score == min_score:
            normalized_scores = [1.0 for _ in raw_scores]
        else:
            normalized_scores = [(score - min_score) / (max_score - min_score) for score in raw_scores]

        return normalized_scores

# -------------------------- 请求模型 --------------------------
class PreciseMatchingRequest(BaseModel):
    """精准匹配检索请求模型"""
    query: str  # 查询语句
    documents: List[str]  # 文档集合
    meta_data: Optional[List[dict]] = None
    k1: float = 0.2  # 精准匹配参数k1
    b: float = 0.75   # 精准匹配参数b

class PreciseMatchingResponse(BaseModel):
    """精准匹配检索响应模型"""
    normalized_scores: List[float]  # 每个文档的归一化得分（0-1）
    weights: Dict[str, float] = {}  # 得分统计信息

# -------------------------- API接口 --------------------------
@app.post("/precise_matching/rank", response_model=PreciseMatchingResponse)
async def precise_matching_rank(request: PreciseMatchingRequest = Body(...)):
    """
    精准匹配文本检索接口
    - 输入：查询语句、文档集合、精准匹配参数
    - 输出：每个文档的归一化得分（0-1）、得分统计信息
    """
    # 初始化精准匹配
    print(f'#############{request.meta_data}')
    content_list=[]
    scores = [1] * len(request.documents)
    if request.meta_data:
        for item in request.meta_data:
            if item['kind'] == 'document':
                filename = item['fileName']
                if filename:
                    content_list.append(item['fileName'])
                else:
                    content_list.append('')
        if request.meta_data[0]['kind'] == 'qna':
            content_list=request.documents

        assert len(content_list) == len(request.documents)


    ranked_results =await AsyncChatCompletionClient().batch_requests(
                query = request.query,
                content_list=[]
            )

    precise_matching = ChinesePreciseMatching(
        documents=content_list,
        k1=request.k1,
        b=request.b
    )
    if request.meta_data:
        scores = precise_matching.filter(request.query)
        print(f'^^^^^^^^ {scores}')
    ### 找到互斥关系

    precise_matching = ChinesePreciseMatching(
        documents=request.documents,
        k1=request.k1,
        b=request.b
    )
    #print(ranked_results)

    # 获取归一化得分
    normalized_scores = precise_matching.get_normalized_scores(request.query, ranked_results)

    # 计算得分统计信息


    return {
        "normalized_scores": [a * b for a, b in zip(normalized_scores, scores)],
        "weights":{"alpha":0.1}
    }



# -------------------------- 启动服务 --------------------------
if __name__ == "__main__":
    import uvicorn
    # 启动FastAPI服务，默认端口8000
    uvicorn.run(app, host="0.0.0.0", port=8000)