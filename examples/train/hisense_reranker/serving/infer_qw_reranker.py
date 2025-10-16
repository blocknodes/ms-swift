import requests
import logging
from typing import List, Optional, Dict
import sys

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class RerankClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        初始化Rerank客户端

        Args:
            base_url: 服务端地址，默认为"http://localhost:8080"
        """
        self.base_url = base_url
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

        try:
            # 发送POST请求
            logging.info(f"发送排序请求，查询: {query[:50]}..., 文档数量: {len(documents)}")
            response = requests.post(
                self.rerank_endpoint,
                json=payload,
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

    def rerank_and_sort(self, query: str, documents: List[str], instruction: Optional[str] = None) -> List[Dict]:
        """
        发送排序请求并返回按分数排序的文档列表

        Args:
            query: 查询字符串
            documents: 文档列表
            instruction: 可选的指令字符串

        Returns:
            按相关性分数降序排列的列表，每个元素为{"document": 文档内容, "score": 分数}
        """
        result = self.rerank(query, documents, instruction)
        scores = result.get("scores", [])

        # 确保分数数量与文档数量一致
        if len(scores) != len(documents):
            logging.warning(f"分数数量({len(scores)})与文档数量({len(documents)})不一致")
            return []

        # 组合文档和分数，并按分数降序排序
        ranked_docs = [
            {"document": doc, "score": score}
            for doc, score in zip(documents, scores)
        ]

        # 按分数降序排序
        ranked_docs.sort(key=lambda x: x["score"], reverse=True)

        return ranked_docs

# 示例使用
if __name__ == "__main__":
    port = 8080 if len(sys.argv) <1 else sys.argv[1]
    # 创建客户端实例
    client = RerankClient(base_url=f"http://localhost:{port}")

    # 示例查询和文档
    query = "没听说过璀璨，没有格力、美的有名呀？\n "
    documents = ['# 没听说过璀璨，没有格力、美的有名呀？',
    '很多顾客的想法跟您是一样的，对自己没听过的品牌有顾虑，我们也非常理解。刚好您今天过来了，让我有机会给您介绍一下我们海信品牌以及我们的璀璨系列。首先，海信集团是有年历史的国企，是强企业，在全球有所研发机构个工业园区和生产基地。而璀璨是海信旗下高端系列，主打高端智能套系家电，有电视、冰箱、空调（家用空调、中央空调）、洗衣机、油烟机、洗碗机等，集结了海信最高精尖的技术，并随着技术发展不断迭代更新。璀璨的服务您放心，我们有小时服务热线，及时帮您解决问题。',

    '东芝电视-100Z600NF-话术.xlsx',

]


    #instruction = '给定一个query，找到最有可能包含对应答案的filename'
    instruction = None

    # 仅获取分数
    scores = client.rerank(query, documents, instruction)
    #print("排序分数:", scores)

    # 获取排序后的文档
    ranked_results = client.rerank_and_sort(query, documents, instruction)

    # 打印排序结果
    print(f"query:\n{query}")

    for i, item in enumerate(ranked_results, 1):
        print(f"{i}. 分数: {item['score']:.4f}")
        print(f"   内容: {item['document'][:]}\n")
