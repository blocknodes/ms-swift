from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import requests
import json

app = FastAPI(title="Rerank Service API", description="基于Qwen3-Reranker的重排服务")

# 配置重排服务端地址（原客户端连接的服务地址）
RERANK_SERVER_BASE_URL = "http://localhost:8000/v1"
RERANK_ENDPOINT = f"{RERANK_SERVER_BASE_URL}/rerank"

# 请求头配置
HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json"
}

# 定义请求数据模型（根据需求定制）
class RerankRequest(BaseModel):
    query: str  # 单个查询字符串
    documents: List[str]  # 文档列表
    filenames: Optional[List[str]] = None  # 文件名列表（可选）
    instruction: Optional[str] = None  # 指令（可选）
    flag: Optional[int] = 0  # 0:qd 1:qq（默认0）

# 定义响应数据模型（仅返回得分列表）
class RerankResponse(BaseModel):
    scores: List[float]

@app.post("/rerank",
          response_model=RerankResponse,
          status_code=status.HTTP_200_OK,
          description="接收查询和文档列表，返回重排后的得分列表")
async def rerank(request: RerankRequest) -> Any:
    """
    重排API接口：
    - 接收查询语句、文档列表及可选参数
    - 调用后端重排服务
    - 返回排序后的相关性得分列表（与输入文档顺序对应）
    """
    # 参数验证
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="查询语句不能为空"
        )

    if not isinstance(request.documents, list) or len(request.documents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文档列表必须是非空数组"
        )

    # 验证文件名列表（如果提供）
    if request.filenames is not None:
        if not isinstance(request.filenames, list) or len(request.filenames) != len(request.documents):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名列表必须与文档列表长度一致"
            )

    # 验证flag参数
    if request.flag not in (0, 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="flag参数必须为0（qd）或1（qq）"
        )

    # 构造请求体（根据后端服务要求调整字段）
    payload = {
        "model": "qwen3-reranker",  # 固定使用qwen3-reranker模型
        "query": request.query,
        "documents": request.documents,
        # 附加可选参数（如果后端服务支持）
        "flag": request.flag
    }

    # 可选参数：仅在有值时添加到请求体
    if request.instruction:
        payload["instruction"] = request.instruction
    if request.filenames:
        payload["filenames"] = request.filenames

    try:
        # 发送请求到重排服务
        response = requests.post(
            url=RERANK_ENDPOINT,
            headers=HEADERS,
            data=json.dumps(payload),
            timeout=30
        )

        # 检查响应状态
        response.raise_for_status()

        # 解析原始响应
        raw_result = response.json()

        # 提取得分列表（假设原始响应中results包含relevance_score字段）
        # 这里根据实际后端服务的响应结构调整
        if "results" not in raw_result:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="重排服务返回结果格式不正确（缺少results字段）"
            )

        # 提取得分并保持与输入文档的对应关系
        # 注意：如果后端返回的是排序后的结果，需要根据index字段还原原始顺序
        scores = []
        result_map = {item["index"]: item["relevance_score"] for item in raw_result["results"]}

        # 按原始文档顺序填充得分
        for i in range(len(request.documents)):
            scores.append(result_map.get(i, 0.0))  # 默认为0.0如果未找到

        return RerankResponse(scores=scores)

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"无法连接到重排服务 {RERANK_ENDPOINT}，请检查服务是否启动"
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="重排服务请求超时（30秒）"
        )
    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"重排服务返回错误：{str(e)}，状态码：{response.status_code}"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="重排服务返回无效的JSON格式"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求时发生错误：{str(e)}"
        )

@app.get("/health", description="服务健康检查")
async def health_check() -> Dict[str, str]:
    """健康检查接口，用于验证服务是否正常运行"""
    return {"status": "healthy", "service": "rerank-service"}

if __name__ == "__main__":
    import uvicorn
    # 启动服务，使用8001端口避免与后端重排服务冲突
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")