"""
Cross-encoder reranker using BAAI/bge-reranker-base from Hugging Face.
Scores (query, passage) pairs and sorts descending. Big quality boost for citations.
"""

from typing import List
from app.ports import RerankerPort
from sentence_transformers import CrossEncoder

class BGERerankerAdapter(RerankerPort):
    def __init__(self, model_name: str = "BAAI/bge-reranker-base", device: str = None):
        self.ce = CrossEncoder(model_name, device=device)

    def rerank(self, query: str, hits: List[dict]) -> List[dict]:
        passages = [h["metadata"].get("text","") for h in hits]
        pairs = [(query, p) for p in passages]
        scores = self.ce.predict(pairs).tolist()
        for h, s in zip(hits, scores):
            h["score"] = float(s)
        return sorted(hits, key=lambda x: x.get("score", 0.0), reverse=True)
