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
            #words = jieba.lcut(doc)  # 结巴精确分词
            words = jieba.lcut(doc, cut_all=True)
            #words = jieba.lcut_for_search(doc)
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

        # 获取所有分数用于线性归一化
        all_scores = [score for _, score in scores]
        min_score = min(all_scores) if all_scores else 0
        max_score = max(all_scores) if all_scores else 1

        # 线性归一化到0~1范围
        normalized_scores = []
        for idx, score in scores:
            if max_score == min_score:
                normalized_score = 0.0  # 所有分数相同的情况
            else:
                normalized_score = (score - min_score) / (max_score - min_score)
            normalized_scores.append((idx, normalized_score))

        # 按归一化后的分数降序排序
        normalized_scores.sort(key=lambda x: x[1], reverse=True)
        return normalized_scores[:top_n]

# 示例使用
if __name__ == "__main__":
    # 示例文档集（中文）
    documents = [
        "Hisense 海信冰箱\n2026世界杯全球官方指定冰箱\n一级能效双变频\n516L十字精储\n高效抗菌99.99%\n516L",
        "Hisense\nFIFA\n2026世界杯™全球官方指定冰箱\nBCD-518WTDGVBPIS1\n三侧不留缝\n正面不凸出\n60cm纯平全嵌\n全空间离子主动除菌净味\n超大冷冻空间",
        "Hisense\n2025 FIFA世界杯™全球官方赞助商\n海信502V5真空纯平全嵌十字冰箱\n海信真空冰箱\n真空，才是真保鲜",
        "Hisense\n2025 FIFA世界杯全球官方赞助商\n海信真空冰箱\n真空·才是真保鲜\nBCD-515V5FZGQA\n原创新空冰温科技\n双系统不串味\n全域超净保鲜",
        "# 海信 2026世界杯™全球官方指定冰箱\n## 产品名称\n- 海信璀璨真空头等舱501冰箱（型号：TR-501U6FZIQA）\n- 璀璨·海信高端全套智能家电\n## 核心技术与功能\n### 真空分子级锁鲜\n- 真空保鲜技术叠加磁场保鲜技术一键低压低氧，借助磁场生物学效应，外部真空防氧化，内部磁场抑酶活，将保鲜深入分子层面，实现7天封藏一级鲜。\n- 真空保鲜定格食材原鲜，磁场保鲜锁鲜7日如初。\n#### 牛肉7天新鲜度对比实验"
    ]

    # 初始化中文BM25
    bm25 = ChineseBM25(documents)

    # 测试查询
    query = "2026年世界杯冰箱"
    print(f"查询：{query}")
    print("Top-3相关文档：")
    results = bm25.rank(query, top_n=100)

    print(f"查询: {query}")
    print("排名结果:")
    for idx, score in results:
        print(f"文档 {idx}: {bm25.documents[idx]} (得分: {score:.4f})\n\n")



