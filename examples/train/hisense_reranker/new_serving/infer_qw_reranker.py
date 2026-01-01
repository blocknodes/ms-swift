import requests
import logging
from typing import List, Optional, Dict
import sys

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class RerankClient:
    def __init__(self, base_url: str = "https://inner-apisix-test.hisense.com/kbp/sit/",
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

    def rerank(self, query: str, documents: List[str], instruction: Optional[str] = None, meta_data=None ) -> Dict:
        """
        发送排序请求到服务端

        Args:
            query: 查询字符串
            documents: 文档列表
            instruction: 可选的指令字符串
            meta_data: 文档的元数据列表

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
            "instruction": instruction,
            "meta_data": meta_data
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

    def rerank_and_sort(self, query: str, documents: List[str], instruction: Optional[str] = None, meta_data=None) -> List[Dict]:
        """
        发送排序请求并返回按分数排序的文档列表

        Args:
            query: 查询字符串
            documents: 文档列表
            instruction: 可选的指令字符串
            meta_data: 文档的元数据列表

        Returns:
            按相关性分数降序排列的列表，每个元素为{"document": 文档内容, "score": 分数, "meta": 元数据}
        """
        result = self.rerank(query, documents, instruction, meta_data)

        # 解析分数
        if "scores" in result.keys():
            scores = result.get("scores", [])
        else:
            scores = result['data'][0]['value']
            scores = [item['relevance_score'] for item in scores]

        # 确保分数数量与文档数量一致
        if len(scores) != len(documents):
            logging.warning(f"分数数量({len(scores)})与文档数量({len(documents)})不一致")
            return []

        # 组合文档、分数和元数据，并按分数降序排序
        ranked_docs = []
        for i, (doc, score) in enumerate(zip(documents, scores)):
            # 获取对应文档的元数据，如果存在的话
            meta = None
            if meta_data and i < len(meta_data):
                meta = meta_data[i]

            ranked_docs.append({
                "document": doc,
                "score": score,
                "meta": meta
            })

        # 按分数降序排序
        ranked_docs.sort(key=lambda x: x["score"], reverse=True)

        return ranked_docs

# 示例使用
if __name__ == "__main__":
    # 修复端口参数解析逻辑
    port = 8080 if len(sys.argv) < 2 else sys.argv[1]

    # 创建客户端实例
    client = RerankClient(base_url=f"http://localhost:{port}")
    # client = RerankClient()  # 使用默认地址

    # 示例查询和文档
    query = '如何选择适合的电视显示模式'
    documents = [
        '选择适合的模式，核心原则是匹配观看场景和片源类型，不同模式的色彩、对比度、锐度调校差异很大，直接影响观感。',
        '选择适合的模式，核心是匹配当前的环境需求和使用场景，不同模式的制冷、制热、除湿逻辑不同，合理使用还能节省能耗'
    ]

    # 元数据（取消注释以使用）
    meta_data = [
        {"fileName": "海信电视百问百答-温州分公司---海信电视.docx", "kind": "document"},
        {"fileName": "海信空调百问百答-温州分公司---海信空调.docx", "kind": "document"}
    ]
    meta_data = None  # 可以注释掉上面的meta_data，启用这个来测试无元数据的情况

    instruction = None

    # 获取排序后的文档
    ranked_results = client.rerank_and_sort(query, documents, instruction, meta_data)

    # 打印排序结果
    print(f"query:\n{query}\n")
    print("="*80)

    for i, item in enumerate(ranked_results, 1):
        print(f"{i}. 分数: {item['score']:.4f}")
        print(f"   内容: {item['document']}")

        # 打印元数据
        if item['meta']:
            print(f"   元数据:")
            for key, value in item['meta'].items():
                print(f"     - {key}: {value}")
        else:
            print(f"   元数据: 无")

        print("-" * 80)