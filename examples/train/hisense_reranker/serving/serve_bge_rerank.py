from fastapi import FastAPI, Request
from pydantic import BaseModel
from FlagEmbedding import FlagReranker
import uvicorn
import sys
# Initialize FastAPI app
app = FastAPI()

# Initialize the FlagReranker model
reranker = FlagReranker(
    sys.argv[1],
    query_max_length=512,
    passage_max_length=2048,
    use_fp16=True,
    devices=['cuda:0']
)

# Define request model
class RerankRequest(BaseModel):
    documents: list[str]
    query: str

# Define response model
class RerankResponse(BaseModel):
    scores: list[float]

@app.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest):
    # Prepare pairs for reranking: each document with the query
    pairs = [[request.query, doc] for doc in request.documents]
    # Compute scores for each pair
    scores = reranker.compute_score(pairs, normalize=True)
    # Return scores
    return RerankResponse(scores=scores)

if __name__ == "__main__":
    _ = reranker.compute_score(["hello","你好"])
    uvicorn.run(app, host="0.0.0.0", port=8080)
