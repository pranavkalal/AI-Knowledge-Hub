# rag/nodes/retrieve.py
"""
Retrieval node for LangGraph RAG pipeline.

Uses the existing PortsRetriever to fetch documents from PostgreSQL.
"""

import time
import logging
from typing import Any, Dict, List

from langchain_core.documents import Document

from rag.nodes.state import RAGState

logger = logging.getLogger(__name__)


def create_retrieve_node(retriever: Any):
    """
    Factory to create a retrieve node with the given retriever.
    
    Args:
        retriever: PortsRetriever instance (wraps vector_postgres.py)
        
    Returns:
        Node function for the graph
    """
    
    def retrieve_node(state: RAGState) -> Dict[str, Any]:
        """
        Retrieve documents for the current query.
        
        Uses rewritten_query if available, otherwise original question.
        """
        start = time.perf_counter()
        
        # Use rewritten query if we've done a rewrite
        query = state.get("rewritten_query") or state["question"]
        k = state.get("k", 6)
        filters = state.get("filters", {})
        
        logger.info(f"[retrieve] query='{query[:50]}...' k={k}")
        
        # Build retriever input - PortsRetriever expects specific format
        retriever_input = {
            "question": query,
            "k": k * 2,  # Overfetch for grading/reranking
        }
        
        # Add filters if any
        if filters:
            for key, value in filters.items():
                if value is not None:
                    retriever_input[key] = value
        
        try:
            # PortsRetriever returns List[Document]
            raw_documents = retriever.invoke(retriever_input)
            
            if not isinstance(raw_documents, list):
                raw_documents = list(raw_documents) if raw_documents else []
            
            # Post-process: ensure page_content is populated from metadata
            # PortsRetriever stores text in metadata.preview/metadata.text
            documents: List[Document] = []
            for doc in raw_documents:
                content = doc.page_content or ""
                md = dict(doc.metadata) if doc.metadata else {}
                
                # If page_content is empty, try to get from metadata
                if not content.strip():
                    content = md.get("preview") or md.get("text") or ""
                
                if content.strip():
                    documents.append(Document(page_content=content, metadata=md))
                else:
                    logger.warning(f"[retrieve] skipping doc with no content: {md.get('doc_id', 'unknown')}")
            
            logger.info(f"[retrieve] found {len(documents)} documents with content (from {len(raw_documents)} raw)")
            
        except Exception as e:
            logger.error(f"[retrieve] error: {e}", exc_info=True)
            documents = []
        
        elapsed = time.perf_counter() - start
        
        # Initialize or update timings
        timings = list(state.get("timings", []))
        timings.append({"stage": "retrieve", "seconds": elapsed})
        
        return {
            "documents": documents,
            "timings": timings,
        }
    
    return retrieve_node


