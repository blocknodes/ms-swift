import jieba
import math
import re
from collections import defaultdict
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List, Dict, Any

# 初始化FastAPI应用
app = FastAPI(title="Chinese BM25 Text Retrieval API", version="1.0")

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

# -------------------------- BM25核心类 --------------------------
class ChineseBM25:
    def __init__(self, documents: List[str], k1: float = 0.2, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.stop_words = set(['的', '了', '是', '在', '和', '有', '我', '也', '很', '就', '/'])
        self.whitelist = set(['油烟机','冰箱','空调','电视','洗衣机','冷柜','洗碗机','变温柜','电热水器','燃气灶','投影'])
        self._preprocess()
        self._calc_avgdl()
        self._calc_idf()

    def _preprocess(self):
        """预处理：分词、过滤、统计文档频率"""
        self.corpus = []
        self.word_count = defaultdict(int)

        for doc in self.documents:
            words = jieba.lcut(doc, cut_all=True)
            filtered_words = clean_and_split(words)
            final_words = [
                word for word in filtered_words
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

    def get_score(self, query: str, doc_idx: int) -> float:
        """计算单个文档的BM25得分"""
        doc = self.corpus[doc_idx]
        doc_length = len(doc)

        # 处理查询词
        query_words = jieba.lcut(query)
        filtered_words = clean_and_split(query_words)
        query_words = [
            word for word in filtered_words
            if word not in self.stop_words and (word in self.whitelist or re.search(pattern, word))
        ]

        print(f'query words: {query_words}')

        score = 0.0
        for word in query_words:
            if word not in self.idf:
                continue
            tf = doc.count(word)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avgdl))
            score += self.idf[word] * (tf * (self.k1 + 1)) / denominator
        return score

    def get_normalized_scores(self, query: str) -> List[float]:
        """获取所有文档的归一化得分（0-1）"""
        # 计算原始得分
        raw_scores = [self.get_score(query, i) for i in range(len(self.documents))]

        # 处理空值和相同值情况
        if not raw_scores:
            return []
        min_score = min(raw_scores)
        max_score = max(raw_scores)

        # 归一化到0-1
        normalized_scores = []
        if max_score == min_score:
            normalized_scores = [1.0 for _ in raw_scores]
        else:
            normalized_scores = [(score - min_score) / (max_score - min_score) for score in raw_scores]

        return normalized_scores

# -------------------------- 请求模型 --------------------------
class BM25Request(BaseModel):
    """BM25检索请求模型"""
    query: str  # 查询语句
    documents: List[str]  # 文档集合
    k1: float = 0.2  # BM25参数k1
    b: float = 0.75   # BM25参数b

class BM25Response(BaseModel):
    """BM25检索响应模型"""
    normalized_scores: List[float]  # 每个文档的归一化得分（0-1）
    weights: Dict[str, float] = {}  # 得分统计信息

# -------------------------- API接口 --------------------------
@app.post("/bm25/rank", response_model=BM25Response)
async def bm25_rank(request: BM25Request = Body(...)):
    """
    BM25文本检索接口
    - 输入：查询语句、文档集合、BM25参数
    - 输出：每个文档的归一化得分（0-1）、得分统计信息
    """
    # 初始化BM25
    bm25 = ChineseBM25(
        documents=request.documents,
        k1=request.k1,
        b=request.b
    )

    # 获取归一化得分
    normalized_scores = bm25.get_normalized_scores(request.query)

    # 计算得分统计信息


    return {
        "normalized_scores": normalized_scores,
        "weights":{"alpha":0.1}
    }

@app.post("/bm25/single_score", response_model=Dict[str, float])
async def bm25_single_score(
    query: str = Body(..., description="查询语句"),
    document: str = Body(..., description="单个文档"),
    k1: float = Body(0.2, description="BM25参数k1"),
    b: float = Body(0.75, description="BM25参数b")
):
    """
    获取单个文档的BM25归一化得分
    - 输入：查询语句、单个文档、BM25参数
    - 输出：该文档的归一化得分
    """
    # 构造单文档集合
    documents = [document]

    # 初始化BM25并计算得分
    bm25 = ChineseBM25(documents=documents, k1=k1, b=b)
    normalized_scores = bm25.get_normalized_scores(query)

    return {
        "normalized_score": normalized_scores[0] if normalized_scores else 0.0
    }

# -------------------------- 启动服务 --------------------------
if __name__ == "__main__":
    import uvicorn
    # 启动FastAPI服务，默认端口8000
    uvicorn.run(app, host="0.0.0.0", port=8000)