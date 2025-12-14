# rag/nodes/grade.py
"""
Relevance grading node for LangGraph RAG pipeline.

Uses LLM to score each retrieved document for relevance to the query.
This enables Corrective RAG - rewriting queries when results are poor.
"""

import time
import logging
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from rag.nodes.state import RAGState, RELEVANCE_THRESHOLD

logger = logging.getLogger(__name__)


class RelevanceGrade(BaseModel):
    """Grading result for a single document."""
    is_relevant: bool = Field(description="Whether the document is relevant to the query")
    confidence: float = Field(description="Confidence score 0.0-1.0", ge=0.0, le=1.0)


def create_grade_node(llm_model: str = "gpt-4o-mini"):
    """
    Factory to create a grading node.
    
    Uses a fast, cheap model (gpt-4o-mini) for grading to minimize cost.
    """
    
    def grade_node(state: RAGState) -> Dict[str, Any]:
        """
        Grade each document for relevance to the query.
        
        Returns relevance_grades list with scores for each document.
        """
        start = time.perf_counter()
        
        documents = state.get("documents", [])
        query = state.get("rewritten_query") or state["question"]
        
        if not documents:
            logger.info("[grade] no documents to grade")
            return {
                "relevance_grades": [],
                "timings": state.get("timings", []) + [{"stage": "grade", "seconds": 0}],
            }
        
        # Use structured output for reliable grading
        grader_llm = ChatOpenAI(model=llm_model, temperature=0)
        structured_grader = grader_llm.with_structured_output(RelevanceGrade)
        
        grades: List[float] = []
        relevant_count = 0
        
        for i, doc in enumerate(documents):
            content = doc.page_content[:500]  # Truncate for speed
            
            try:
                result = structured_grader.invoke([
                    ("system", "You are a relevance grader. Determine if the document excerpt is relevant to the user's question. Be strict - only mark as relevant if it directly helps answer the question."),
                    ("human", f"Question: {query}\n\nDocument excerpt:\n{content}\n\nIs this document relevant?")
                ])
                
                grade = result.confidence if result.is_relevant else 0.0
                grades.append(grade)
                
                if result.is_relevant:
                    relevant_count += 1
                    
            except Exception as e:
                logger.warning(f"[grade] failed to grade doc {i}: {e}")
                grades.append(0.5)  # Neutral on error
        
        relevance_ratio = relevant_count / len(documents) if documents else 0
        logger.info(f"[grade] {relevant_count}/{len(documents)} relevant ({relevance_ratio:.0%})")
        
        elapsed = time.perf_counter() - start
        timings = list(state.get("timings", []))
        timings.append({"stage": "grade", "seconds": elapsed})
        
        return {
            "relevance_grades": grades,
            "timings": timings,
        }
    
    return grade_node


def should_rewrite(state: RAGState) -> str:
    """
    Conditional edge: decide whether to rewrite query or proceed to rerank.
    
    Returns:
        "rewrite" if relevance is below threshold and retries remain
        "rerank" otherwise
    """
    from rag.nodes.state import MAX_REWRITE_ATTEMPTS, RELEVANCE_THRESHOLD
    
    grades = state.get("relevance_grades", [])
    rewrite_count = state.get("rewrite_count", 0)
    
    if not grades:
        # No documents found at all - try rewriting
        if rewrite_count < MAX_REWRITE_ATTEMPTS:
            logger.info("[grade] no documents, triggering rewrite")
            return "rewrite"
        return "rerank"
    
    # Calculate relevance ratio
    relevant = sum(1 for g in grades if g > 0.5)
    ratio = relevant / len(grades)
    
    if ratio < RELEVANCE_THRESHOLD and rewrite_count < MAX_REWRITE_ATTEMPTS:
        logger.info(f"[grade] relevance {ratio:.0%} < {RELEVANCE_THRESHOLD:.0%}, triggering rewrite")
        return "rewrite"
    
    return "rerank"
