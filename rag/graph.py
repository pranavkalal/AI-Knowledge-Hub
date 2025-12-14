# rag/graph.py
"""
LangGraph-based RAG pipeline for the CRDC Knowledge Hub.

Implements Corrective RAG pattern:
1. Retrieve documents
2. Grade relevance
3. Rewrite query if results poor (max 2 retries)
4. Rerank final results
5. Generate answer
6. Self-evaluate for hallucinations

This replaces the LCEL chain in rag/chain.py when USE_LANGGRAPH=true.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph, END
from langchain_core.runnables import Runnable

from rag.nodes.state import RAGState
from rag.nodes.retrieve import create_retrieve_node
from rag.nodes.grade import create_grade_node, should_rewrite
from rag.nodes.rewrite import create_rewrite_node
from rag.nodes.rerank import create_rerank_node
from rag.nodes.generate import create_generate_node
from rag.nodes.evaluate import create_evaluate_node, should_regenerate

from app.services.prompting import DEFAULT_PERSONA

logger = logging.getLogger(__name__)


def create_rag_graph(
    retriever: Any,
    reranker: Any = None,
    llm_model: str = "gpt-4o",
    grader_model: str = "gpt-4o-mini",
) -> Runnable:
    """
    Build the LangGraph RAG pipeline.
    
    Args:
        retriever: PortsRetriever instance
        reranker: Optional reranker instance
        llm_model: Model for answer generation
        grader_model: Model for grading/rewriting (should be fast/cheap)
        
    Returns:
        Compiled LangGraph as a Runnable
    """
    logger.info(f"[graph] creating RAG graph with llm={llm_model}, grader={grader_model}")
    
    # Create node functions
    retrieve_node = create_retrieve_node(retriever)
    grade_node = create_grade_node(grader_model)
    rewrite_node = create_rewrite_node(grader_model)
    rerank_node = create_rerank_node(reranker)
    generate_node = create_generate_node(llm_model)
    evaluate_node = create_evaluate_node(grader_model)
    
    # Build the state graph
    workflow = StateGraph(RAGState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade", grade_node)
    workflow.add_node("rewrite", rewrite_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("evaluate", evaluate_node)
    
    # Define edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade")
    
    # Conditional: grade → rewrite OR grade → rerank
    workflow.add_conditional_edges(
        "grade",
        should_rewrite,
        {
            "rewrite": "rewrite",
            "rerank": "rerank",
        }
    )
    
    # Rewrite loops back to retrieve
    workflow.add_edge("rewrite", "retrieve")
    
    # Linear path: rerank → generate → evaluate → END
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", "evaluate")
    
    # Conditional: evaluate → END (for now, could add regenerate later)
    workflow.add_conditional_edges(
        "evaluate",
        should_regenerate,
        {
            "end": END,
            "regenerate": "generate",  # Future: regenerate with stricter prompt
        }
    )
    
    # Compile the graph
    graph = workflow.compile()
    
    logger.info("[graph] RAG graph compiled successfully")
    return graph


class LangGraphRAGChain(Runnable):
    """
    Wrapper to make LangGraph compatible with existing chain interface.
    
    Accepts the same input format as build_chain() and returns the same output.
    """
    
    def __init__(
        self,
        retriever: Any,
        reranker: Any = None,
        llm_model: str = "gpt-4o",
        k: int = 6,
    ):
        self.graph = create_rag_graph(
            retriever=retriever,
            reranker=reranker,
            llm_model=llm_model,
        )
        self.default_k = k
    
    def invoke(self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the graph and format output for compatibility.
        """
        start = time.perf_counter()
        
        # Build initial state
        initial_state: RAGState = {
            "question": input.get("question", ""),
            "persona": input.get("persona", DEFAULT_PERSONA),
            "temperature": float(input.get("temperature", 0.2)),
            "max_tokens": int(input.get("max_tokens", 600)),
            "k": int(input.get("k", self.default_k)),
            "filters": input.get("filters", {}),
            "documents": [],
            "relevance_grades": [],
            "rewrite_count": 0,
            "rewritten_query": None,
            "generation": None,
            "citations": [],
            "usage": None,
            "hallucination_detected": False,
            "timings": [],
        }
        
        # Run the graph
        try:
            final_state = self.graph.invoke(initial_state, config=config)
        except Exception as e:
            logger.error(f"[graph] execution failed: {e}")
            return {
                "answer": "I apologize, but I encountered an error processing your question. Please try again.",
                "citations": [],
                "usage": {},
                "timings": [{"stage": "error", "seconds": time.perf_counter() - start}],
            }
        
        # Format output to match existing chain output
        answer = final_state.get("generation", "")
        citations = final_state.get("citations", [])
        usage = final_state.get("usage", {})
        timings = final_state.get("timings", [])
        
        # Add total timing
        total_seconds = time.perf_counter() - start
        timings.append({"stage": "total", "seconds": total_seconds})
        
        # Answer already contains inline citations from LLM - no need to append sources list
        
        return {
            "answer": answer,
            "citations": citations,
            "usage": usage,
            "timings": timings,
        }
    
    async def ainvoke(self, input: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Async version - delegates to sync for now."""
        # LangGraph supports async natively, but for simplicity we use sync
        import asyncio
        return await asyncio.to_thread(self.invoke, input, config)
