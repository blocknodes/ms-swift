import logging
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict
from transformers import AutoModelForCausalLM, AutoTokenizer
import sys
from peft import PeftModel

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 初始化FastAPI应用
app = FastAPI(title="Qwen3-Reranker Service")

# 解析命令行参数，支持模型路径和端口配置
if len(sys.argv) < 2:
    logging.error("请提供模型路径作为第一个参数")
    sys.exit(1)

MODEL_PATH = sys.argv[1]
# 端口配置，第二个参数为端口号，默认8080
PORT = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 8080
MAX_LENGTH = 8192

# 定义请求数据模型
class RerankRequest(BaseModel):
    query: str  # 单个查询字符串
    documents: List[str]  # 文档列表
    filenames: List[str]  = None # 文件名列表
    instruction: Optional[str] = None
    # 0:qd 1:qq
    flag: Optional[int] = 0

# 定义响应数据模型
class RerankResponse(BaseModel):
    scores: List[float]

# 只在启动时加载一次模型
@app.on_event("startup")
def load_model():
    global tokenizer, model, token_false_id, token_true_id, prefix_tokens, suffix_tokens

    # 加载分词器和模型
    logging.info(f"Loading model from {MODEL_PATH}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, padding_side='left')
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH).eval()
    #adapter_path = sys.argv[3]
    #model = PeftModel.from_pretrained(base_model, adapter_path, adapter_name="adapter1")


    #adapter_path = sys.argv[4]
    #model.load_adapter(adapter_path, adapter_name="adapter2")
    #model.set_adapter("adapter1")

    # 移动模型到GPU（如果可用）
    if torch.cuda.is_available():
        model = model.cuda()
        logging.info("Model moved to GPU")
    else:
        logging.info("Using CPU for inference")

    # 准备特殊token和前缀后缀
    token_false_id = tokenizer.convert_tokens_to_ids("no")
    token_true_id = tokenizer.convert_tokens_to_ids("yes")

    prefix = "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n<|im_start|>user\n"
    suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

    prefix_tokens = tokenizer.encode(prefix, add_special_tokens=False)
    suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)

    # 预热模型
    try:
        test_query = "test query"
        test_doc = ["test document"]
        test_pairs = [format_instruction(None, test_query, doc) for doc in test_doc]
        inputs = process_inputs(test_pairs)
        with torch.no_grad():
            _ = model(** inputs).logits
        logging.info("Model warmed up successfully")
    except Exception as e:
        logging.error(f"Error during model warm-up: {str(e)}")

# 格式化指令
def format_instruction(instruction, query, doc):
    if instruction is None:
        instruction = 'Given a web search query, retrieve relevant passages that answer the query'
    output = "<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {doc}".format(instruction=instruction, query=query, doc=doc)
    return output

# 处理输入
def process_inputs(pairs):
    inputs = tokenizer(
        pairs, padding=False, truncation='longest_first',
        return_attention_mask=False, max_length=MAX_LENGTH - len(prefix_tokens) - len(suffix_tokens)
    )

    for i, ele in enumerate(inputs['input_ids']):
        inputs['input_ids'][i] = prefix_tokens + ele + suffix_tokens

    inputs = tokenizer.pad(inputs, padding=True, return_tensors="pt", max_length=MAX_LENGTH)

    # 移动到模型所在设备
    for key in inputs:
        inputs[key] = inputs[key].to(model.device)

    return inputs

# 计算logits并返回分数
@torch.no_grad()
def compute_scores(inputs):
    batch_scores = model(**inputs).logits[:, -1, :]
    true_vector = batch_scores[:, token_true_id]
    false_vector = batch_scores[:, token_false_id]

    batch_scores = torch.stack([false_vector, true_vector], dim=1)
    batch_scores = torch.nn.functional.log_softmax(batch_scores, dim=1)

    # 返回yes的概率作为相关性分数
    return batch_scores[:, 1].exp().tolist()

# 定义API端点 - 返回包含scores键的字典
@app.post("/rerank", response_model=RerankResponse)
def rerank(request: RerankRequest):
    """
    对查询和文档列表进行相关性评分，返回{'scores': score_list}格式的响应
    """
    if not request.documents:
        return {"scores": []}

    try:
        # 将单个query扩展为与documents长度相同的列表
        queries = [request.query] * len(request.documents)

        # 格式化输入对
        pairs = [format_instruction(request.instruction, query, doc)
                for query, doc in zip(queries, request.documents)]

        # 处理输入
        #print(pairs)
        inputs = process_inputs(pairs)

        # 计算分数并返回{'scores': score_list}格式
        scores = compute_scores(inputs)
        return {"scores": scores}

    except Exception as e:
        logging.error(f"Error during reranking: {str(e)}")
        return {"scores": []}

# 启动服务
if __name__ == "__main__":
    import uvicorn
    logging.info(f"Starting server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
