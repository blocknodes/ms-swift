import jieba
import math
from collections import defaultdict

class ChineseBM25:
    def __init__(self, documents, k1=1.2, b=0.75):
        self.documents = documents  # 文档列表（每个文档为字符串）
        self.k1 = k1  # TF饱和参数
        self.b = b    # 文档长度归一化参数
        self._preprocess()  # 预处理（分词、停用词过滤）
        self._calc_avgdl()  # 计算平均文档长度
        self._calc_idf()    # 计算IDF

    def _preprocess(self):
        # 中文停用词表（可扩展）
        self.stop_words = set(['的', '了', '是', '在', '和', '有', '我', '也', '很', '就', '/'])
        # 分词 + 过滤停用词
        self.corpus = []  # 分词后的文档列表（每个元素为词语列表）
        self.word_count = defaultdict(int)  # 记录每个词的文档频率（df）
        for doc in self.documents:
            words = jieba.lcut(doc)  # 结巴精确分词
            print(words)
            filtered_words = [word for word in words if word not in self.stop_words and len(word) > 1]  # 过滤停用词和单字
            self.corpus.append(filtered_words)
            # 更新文档频率（df）：每个词在多少文档中出现
            for word in set(filtered_words):
                self.word_count[word] += 1

    def _calc_avgdl(self):
        # 计算所有文档的平均长度（分词后的词语数）
        total_length = sum(len(doc) for doc in self.corpus)
        self.avgdl = total_length / len(self.corpus) if len(self.corpus) > 0 else 0

    def _calc_idf(self):
        # 计算每个词的IDF
        self.idf = {}
        N = len(self.documents)  # 总文档数
        for word, df in self.word_count.items():
            # IDF平滑公式：避免df=0时log无意义
            self.idf[word] = math.log((N - df + 0.5) / (df + 0.5) + 1)

    def get_score(self, query, doc_idx):
        # 计算查询与指定文档（doc_idx）的BM25得分
        doc = self.corpus[doc_idx]
        doc_length = len(doc)
        query_words = jieba.lcut(query)  # 查询分词
        print(query_words)
        query_words = [word for word in query_words if word not in self.stop_words and len(word) > 1]  # 过滤

        score = 0.0
        for word in query_words:
            if word not in self.idf:
                continue  # 词不在语料中，IDF为0，跳过
            # 计算词在文档中的TF（词频）
            tf = doc.count(word)
            # BM25核心公式
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avgdl))
            score += self.idf[word] * (tf * (self.k1 + 1)) / denominator
        return score

    def rank(self, query, top_n=5):
        # 对所有文档排序，返回Top-N相关文档（索引+得分）
        scores = [(i, self.get_score(query, i)) for i in range(len(self.documents))]
        scores.sort(key=lambda x: x[1], reverse=True)  # 降序排序
        return scores[:top_n]

# ------------------- 测试 -------------------
if __name__ == "__main__":
    # 示例文档集（中文）
    documents = [
        "产品知识库/家用冰箱/冷藏冷冻箱/容声/通用系列",
        "容声_卧式冷藏冷冻柜_BCD186ZEAM/RX_产品详情页.jpg",
        "人工智能包含机器学习、深度学习、自然语言处理等领域",
        "产品知识库/家用房间空调/分体式空调器整机/Hisense/通用系列",
        "神经网络是深度学习的基础，模拟人脑神经元结构"
    ]

    # 初始化中文BM25
    bm25 = ChineseBM25(documents)

    # 测试查询
    query = "BCD186ZEAM容声空调是几级能效的？"
    print(f"查询：{query}")
    print("Top-3相关文档：")
    results = bm25.rank(query, top_n=3)
    for idx, score in results:
        print(f"文档{idx+1}（得分：{score:.4f}）：{documents[idx]}")