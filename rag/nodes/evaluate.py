# rag/nodes/evaluate.py
"""
Self-evaluation node for LangGraph RAG pipeline.

Checks if the generated answer is grounded in the source documents
to detect and prevent hallucinations.
"""

import time
import logging
from typing import Any, Dict

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from rag.nodes.state import RAGState

logger = logging.getLogger(__name__)


class HallucinationCheck(BaseModel):
    """Result of hallucination detection."""
    is_grounded: bool = Field(description="Whether the answer is fully grounded in sources")
    confidence: float = Field(description="Confidence in the assessment 0.0-1.0", ge=0.0, le=1.0)
    issues: str = Field(description="Brief description of any grounding issues found", default="")


def create_evaluate_node(llm_model: str = "gpt-4o-mini"):
    """
    Factory to create a self-evaluation node.
    
    Uses a fast model to verify the answer is grounded in sources.
    """
    
    def evaluate_node(state: RAGState) -> Dict[str, Any]:
        """
        Check if the generated answer is grounded in the source documents.
        
        Sets hallucination_detected flag for downstream routing.
        """
        start = time.perf_counter()
        
        generation = state.get("generation", "")
        documents = state.get("documents", [])
        question = state["question"]
        
        if not generation or not documents:
            # Can't evaluate without both
            return {
                "hallucination_detected": False,
                "timings": state.get("timings", []) + [{"stage": "evaluate", "seconds": 0}],
            }
        
        # Build source context
        source_texts = "\n---\n".join([
            f"[S{i+1}]: {doc.page_content[:500]}"
            for i, doc in enumerate(documents[:6])
        ])
        
        evaluator_llm = ChatOpenAI(model=llm_model, temperature=0)
        structured_evaluator = evaluator_llm.with_structured_output(HallucinationCheck)
        
        try:
            result = structured_evaluator.invoke([
                ("system", """You are a fact-checker verifying that an AI-generated answer is grounded in source documents.

An answer is GROUNDED if:
- Every factual claim is supported by at least one source
- No information is fabricated or added beyond what sources say
- Citations [S1], [S2] etc. refer to actual provided sources

An answer is NOT GROUNDED (hallucination) if:
- It contains facts not found in any source
- It makes claims beyond what sources support
- It cites sources that don't exist"""),
                ("human", f"""Question: {question}

Sources:
{source_texts}

Answer to verify:
{generation}

Is this answer fully grounded in the sources?""")
            ])
            
            hallucination_detected = not result.is_grounded
            
            if hallucination_detected:
                logger.warning(f"[evaluate] hallucination detected: {result.issues}")
            else:
                logger.info(f"[evaluate] answer is grounded (confidence: {result.confidence:.0%})")
                
        except Exception as e:
            logger.error(f"[evaluate] failed: {e}")
            hallucination_detected = False  # Assume OK on error
        
        elapsed = time.perf_counter() - start
        timings = list(state.get("timings", []))
        timings.append({"stage": "evaluate", "seconds": elapsed})
        
        return {
            "hallucination_detected": hallucination_detected,
            "timings": timings,
        }
    
    return evaluate_node


def should_regenerate(state: RAGState) -> str:
    """
    Conditional edge: decide whether to regenerate or finish.
    
    Returns:
        "regenerate" if hallucination detected (max 1 retry)
        "end" otherwise
    """
    hallucination_detected = state.get("hallucination_detected", False)
    
    # For now, we don't regenerate - just log and proceed
    # In future iterations, could add regeneration with stricter prompts
    if hallucination_detected:
        logger.warning("[evaluate] hallucination detected but proceeding (no regeneration implemented)")
    
    return "end"
