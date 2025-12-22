# rag/nodes/state.py
"""
State definition for the LangGraph RAG pipeline.

The state flows through the graph, accumulating information at each node.
"""

from typing import TypedDict, List, Optional, Any, Dict
from langchain_core.documents import Document


class RAGState(TypedDict, total=False):
    """
    State passed through the LangGraph RAG pipeline.
    
    Attributes:
        question: Original user query
        persona: User persona (grower/researcher/extension)
        temperature: LLM temperature setting
        max_tokens: Max tokens for generation
        k: Number of documents to retrieve
        
        documents: Retrieved chunks as LangChain Documents
        relevance_grades: Per-document relevance scores (0.0-1.0)
        rewrite_count: Number of query rewrites attempted
        rewritten_query: Modified query after rewrite (if any)
        
        generation: LLM-generated answer
        citations: Formatted citation objects for frontend
        usage: Token usage from LLM
        
        hallucination_detected: Whether self-check found issues
        timings: Performance metrics for each stage
    """
    # Input
    question: str
    persona: str
    temperature: float
    max_tokens: int
    k: int
    filters: Dict[str, Any]
    
    # Retrieval
    documents: List[Document]
    relevance_grades: List[float]
    rewrite_count: int
    rewritten_query: Optional[str]
    
    # Generation
    generation: Optional[str]
    citations: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]]
    
    # Evaluation
    hallucination_detected: bool
    
    # Observability
    timings: List[Dict[str, Any]]


# Configuration constants
MAX_REWRITE_ATTEMPTS = 2
RELEVANCE_THRESHOLD = 0.5  # 50% of docs must be relevant to skip rewrite
