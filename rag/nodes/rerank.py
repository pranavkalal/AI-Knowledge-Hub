# rag/nodes/rerank.py
"""
Reranking node for LangGraph RAG pipeline.

Uses the existing OpenAI reranker to re-score and filter documents
before answer generation.
"""

import time
import logging
from typing import Any, Dict, List

from langchain_core.documents import Document

from rag.nodes.state import RAGState

logger = logging.getLogger(__name__)


def create_rerank_node(reranker: Any):
    """
    Factory to create a rerank node with the given reranker.
    
    Args:
        reranker: OpenAI reranker instance from app/adapters/rerank_openai.py
        
    Returns:
        Node function for the graph
    """
    
    def rerank_node(state: RAGState) -> Dict[str, Any]:
        """
        Rerank documents using cross-encoder scoring.
        
        Converts documents to hit format expected by reranker,
        applies reranking, and converts back to documents.
        """
        start = time.perf_counter()
        
        documents = state.get("documents", [])
        query = state.get("rewritten_query") or state["question"]
        k = state.get("k", 6)
        
        if not documents:
            logger.info("[rerank] no documents to rerank")
            return {
                "documents": [],
                "timings": state.get("timings", []) + [{"stage": "rerank", "seconds": 0}],
            }
        
        if reranker is None:
            # No reranker configured, just truncate to k
            logger.info(f"[rerank] no reranker, returning top {k} docs")
            return {
                "documents": documents[:k],
                "timings": state.get("timings", []) + [{"stage": "rerank", "seconds": 0}],
            }
        
        # Convert documents to hit format for reranker
        # Filter out docs with empty content as they cause OpenAI API errors
        hits = []
        for doc in documents:
            md = dict(getattr(doc, "metadata", {}) or {})
            # Try multiple sources for text content
            text = (
                getattr(doc, "page_content", "") or 
                md.get("preview") or 
                md.get("text") or 
                ""
            ).strip()
            
            if not text:
                logger.warning(f"[rerank] skipping document with empty text, metadata keys: {list(md.keys())}")
                continue
                
            md["text"] = text
            md["preview"] = text
            
            hits.append({
                "score": md.get("score"),
                "faiss_score": md.get("faiss_score", md.get("score")),
                "metadata": md,
            })
        
        if not hits:
            logger.warning("[rerank] all documents had empty text, returning original order")
            return {
                "documents": documents[:k],
                "timings": state.get("timings", []) + [{"stage": "rerank", "seconds": 0}],
            }
        
        logger.info(f"[rerank] reranking {len(hits)} documents (filtered from {len(documents)})")
        
        try:
            reranked = reranker.rerank(query, hits)
            
            if not isinstance(reranked, list):
                reranked = hits
                
            logger.info(f"[rerank] reranked {len(reranked)} documents")
            
        except Exception as e:
            logger.error(f"[rerank] failed: {e}")
            reranked = hits
        
        # Convert back to documents
        reranked_docs: List[Document] = []
        for hit in reranked[:k]:
            md = dict(hit.get("metadata", {}) or {})
            text = md.pop("text", "") or md.get("preview", "")
            
            # Preserve rerank scores
            faiss_score = hit.get("faiss_score", md.get("faiss_score"))
            rerank_score = hit.get("rerank_score")
            
            if faiss_score is not None:
                md["faiss_score"] = faiss_score
            if rerank_score is not None:
                md["rerank_score"] = rerank_score
                md["score"] = rerank_score
            else:
                md["score"] = hit.get("score")
            
            reranked_docs.append(Document(page_content=text, metadata=md))
        
        elapsed = time.perf_counter() - start
        timings = list(state.get("timings", []))
        timings.append({"stage": "rerank", "seconds": elapsed})
        
        # Also record reranker-specific metrics if available
        if hasattr(reranker, "last_run_ms"):
            logger.info(f"[rerank] reranker took {reranker.last_run_ms:.1f}ms")
        
        return {
            "documents": reranked_docs,
            "timings": timings,
        }
    
    return rerank_node
