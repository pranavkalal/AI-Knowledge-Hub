from typing import List
from app.ports import RerankerPort

class NoopReranker(RerankerPort):
    def rerank(self, query: str, hits: List[dict]) -> List[dict]:
        return hits
