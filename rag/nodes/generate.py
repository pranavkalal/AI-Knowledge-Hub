# rag/nodes/generate.py
"""
Answer generation node for LangGraph RAG pipeline.

Uses the configured LLM with persona-aware prompts to generate
answers with inline citations.
"""

import time
import logging
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

from rag.nodes.state import RAGState
from rag.prompts.structured import (
    prepare_prompt_state,
    build_prompt_messages,
    message_to_text,
    extract_usage,
)
from app.services.prompting import DEFAULT_PERSONA

logger = logging.getLogger(__name__)


def create_generate_node(llm_model: str = "gpt-4o"):
    """
    Factory to create an answer generation node.
    
    Args:
        llm_model: Model to use for generation (default: gpt-4o)
        
    Returns:
        Node function for the graph
    """
    
    def generate_node(state: RAGState) -> Dict[str, Any]:
        """
        Generate an answer using retrieved documents.
        
        Uses the existing prompt templates and persona system.
        """
        start = time.perf_counter()
        
        documents = state.get("documents", [])
        question = state["question"]  # Always use original question for answer
        persona = state.get("persona", DEFAULT_PERSONA)
        temperature = state.get("temperature", 0.2)
        max_tokens = state.get("max_tokens", 600)
        
        logger.info(f"[generate] question='{question[:50]}...' docs={len(documents)} persona={persona}")
        
        # Use existing prompt preparation
        prompt_input = {
            "question": question,
            "docs": documents,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "persona": persona,
        }
        
        prompt_state = prepare_prompt_state(prompt_input)
        messages = build_prompt_messages(prompt_state)
        citations = prompt_state.get("citations", [])
        
        # Generate answer
        llm = ChatOpenAI(
            model=llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        try:
            response = llm.invoke(messages)
            answer_text = message_to_text(response)
            usage = extract_usage(response)
            
            logger.info(f"[generate] generated {len(answer_text)} chars")
            
        except Exception as e:
            logger.error(f"[generate] failed: {e}")
            answer_text = "I apologize, but I encountered an error generating an answer. Please try again."
            usage = {}
        
        elapsed = time.perf_counter() - start
        timings = list(state.get("timings", []))
        timings.append({"stage": "generate", "seconds": elapsed})
        
        return {
            "generation": answer_text,
            "citations": citations,
            "usage": usage,
            "timings": timings,
        }
    
    return generate_node
