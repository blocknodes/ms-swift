import logging
import math
import gc
import sys
from typing import List, Optional, Dict

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from vllm.distributed.parallel_state import destroy_model_parallel
from vllm.inputs.data import TokensPrompt

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 初始化FastAPI应用
app = FastAPI(title="Qwen3-Reranker (vllm) Service")

# 定义请求数据模型
class RerankRequest(BaseModel):
    query: str  # 单个查询字符串
    documents: List[str]  # 文档列表
    filenames: Optional[List[str]] = None  # 文件名列表（可选）
    instruction: Optional[str] = None
    flag: Optional[int] = 0  # 0:qd 1:qq

# 定义响应数据模型
class RerankResponse(BaseModel):
    scores: List[float]

# 全局变量
tokenizer = None
model = None
suffix_tokens = None
true_token = None
false_token = None
sampling_params = None
max_length = 8192
MODEL_PATH = None
PORT = 8080  # 默认端口

def format_instruction(instruction, query, doc):
    """格式化指令、查询和文档为模型输入格式"""
    return [
        {"role": "system", "content": "Judge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be \"yes\" or \"no\"."},
        {"role": "user", "content": f"<Instruct>: {instruction}\n\n<Query>: {query}\n\n<Document>: {doc}"}
    ]

def process_inputs(pairs, instruction, max_length, suffix_tokens):
    """处理输入，转换为模型所需格式"""
    messages = [format_instruction(instruction, query, doc) for query, doc in pairs]
    messages = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
        enable_thinking=False
    )
    # 截断并添加后缀
    messages = [ele[:max_length] + suffix_tokens for ele in messages]
    # 转换为vllm的TokensPrompt格式
    return [TokensPrompt(prompt_token_ids=ele) for ele in messages]

def compute_logits(messages):
    """计算文档相关性分数"""
    global model, sampling_params, true_token, false_token

    try:
        outputs = model.generate(messages, sampling_params, use_tqdm=False)
        scores = []

        for output in outputs:
            # 获取最后一个token的logprobs
            final_logits = output.outputs[0].logprobs[-1]

            # 获取"yes"和"no"的log概率
            true_logit = final_logits[true_token].logprob if true_token in final_logits else -10.0
            false_logit = final_logits[false_token].logprob if false_token in final_logits else -10.0

            # 计算概率并归一化
            true_score = math.exp(true_logit)
            false_score = math.exp(false_logit)
            score = true_score / (true_score + false_score) if (true_score + false_score) > 0 else 0.0

            scores.append(score)

        return scores
    except Exception as e:
        logging.error(f"Error in compute_logits: {str(e)}")
        raise

@app.on_event("startup")
def load_model():
    """启动时加载模型和分词器"""
    global tokenizer, model, suffix_tokens, true_token, false_token, sampling_params, max_length, MODEL_PATH

    try:
        if not MODEL_PATH:
            raise ValueError("Model path is not specified")

        logging.info(f"Loading model from {MODEL_PATH}")

        # 确定GPU数量
        number_of_gpu = torch.cuda.device_count()
        logging.info(f"Detected {number_of_gpu} GPU(s)")

        # 加载分词器
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        tokenizer.padding_side = "left"
        tokenizer.pad_token = tokenizer.eos_token

        # 加载vllm模型
        model = LLM(
            model=MODEL_PATH,
            tensor_parallel_size=number_of_gpu,
            max_model_len=2000,
            enable_prefix_caching=True,
            gpu_memory_utilization=0.8
        )

        # 准备后缀和特殊token
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)
        true_token = tokenizer("yes", add_special_tokens=False).input_ids[0]
        false_token = tokenizer("no", add_special_tokens=False).input_ids[0]

        # 配置采样参数
        sampling_params = SamplingParams(
            temperature=0,
            max_tokens=1,
            logprobs=20,
            allowed_token_ids=[true_token, false_token],
        )

        # 预热模型
        test_query = "test query"
        test_docs = ["test document"]
        test_pairs = [(test_query, doc) for doc in test_docs]
        test_instruction = "Test instruction"
        test_inputs = process_inputs(
            test_pairs,
            test_instruction,
            max_length - len(suffix_tokens),
            suffix_tokens
        )
        _ = compute_logits(test_inputs)
        logging.info("Model warmed up successfully")

    except Exception as e:
        logging.error(f"Failed to load model: {str(e)}")
        # 清理资源
        destroy_model_parallel()
        gc.collect()
        raise

@app.on_event("shutdown")
def shutdown_model():
    """关闭时清理模型资源"""
    global model
    if model is not None:
        destroy_model_parallel()
        gc.collect()
        logging.info("Model resources released")

@app.post("/rerank", response_model=RerankResponse)
def rerank(request: RerankRequest):
    """
    对查询和文档列表进行相关性评分
    返回包含每个文档相关性分数的列表
    """
    if not request.documents:
        return {"scores": []}

    try:
        # 准备查询-文档对
        queries = [request.query] * len(request.documents)
        pairs = list(zip(queries, request.documents))

        # 使用默认指令如果未提供
        instruction = request.instruction or "Given a web search query, retrieve relevant passages that answer the query"

        # 处理输入
        inputs = process_inputs(
            pairs,
            instruction,
            max_length - len(suffix_tokens),
            suffix_tokens
        )

        # 计算分数
        scores = compute_logits(inputs)

        return {"scores": scores}

    except Exception as e:
        logging.error(f"Error during reranking: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during reranking")

if __name__ == "__main__":
    import uvicorn

    # 解析命令行参数
    if len(sys.argv) < 2:
        logging.error("请提供模型路径作为第一个参数")
        sys.exit(1)

    MODEL_PATH = sys.argv[1]
    # 端口配置，第二个参数为端口号，默认8080
    PORT = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 8080

    logging.info(f"Starting server on port {PORT} with model {MODEL_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)