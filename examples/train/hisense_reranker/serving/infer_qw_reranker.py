import requests
import logging
from typing import List, Optional, Dict
import sys

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

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
        if "scores" in result.keys():
            scores = result.get("scores", [])
        else:
            scores = result['data'][0]['value']
            scores = [item['relevance_score'] for item in scores]
            pass


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
    client = RerankClient()

    # 示例查询和文档
    query = '电视远场语音功能如何打开'
    documents=["空调不制热怎么处理","中央空调不制热","空调不制热如何解决","空调不制热，外机一直响","空调制热效果差","空调制热启动不开","海信空调没法制热 没有温度","空调制热温度上不来咋整","空调不制冷","空调制热温度就是上不去咋弄呀","空调制热温度上不去该咋整呢","空调不制冷如何解决","空调跟电风扇一样不凉快","空调不出冷气了","空调怎么不能打热风","空调制冷效果差","空调制热不出风","空调制冷制热反了","如何查看空调是否有制热功能","科龙空调为何找不到制热模式"]
    documents=['电视的远场语音如何打开','即设定温度（冷冻室）范围为： $-25^{\\circ}\\mathsf{C}^{\\sim}-12^{\\circ}\\mathsf{C}$ 。冷藏室温度随冷冻室设定温度浮动。\n5、速冻模式\n5.1进入速冻\n-非速冻模式下（如在儿童锁状态，需先解锁）,短按键,进入速冻状态：速冻图标(雪花灯，位于温度显示区，“-”的下方，)点亮，温度显示区域显示“Sd”。']


    instruction = None

    # 仅获取分数
    #scores = client.rerank(query, documents, instruction)
    #print("排序分数:", scores)

    # 获取排序后的文档
    ranked_results = client.rerank_and_sort(query, documents, instruction)

    # 打印排序结果
    print(f"query:\n{query}")

    for i, item in enumerate(ranked_results, 1):
        print(f"{i}. 分数: {item['score']:.4f}")
        print(f"   内容: {item['document'][:]}\n")
