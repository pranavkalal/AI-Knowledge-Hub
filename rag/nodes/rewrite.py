# rag/nodes/rewrite.py
"""
Query rewriting node for LangGraph RAG pipeline.

When retrieved documents have low relevance, this node uses an LLM
to generate a better query that might retrieve more relevant results.
"""

import time
import logging
from typing import Any, Dict

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from rag.nodes.state import RAGState

logger = logging.getLogger(__name__)


class RewrittenQuery(BaseModel):
    """Output of query rewriting."""
    query: str = Field(description="The rewritten, improved query")
    reasoning: str = Field(description="Brief explanation of what was improved")


def create_rewrite_node(llm_model: str = "gpt-4o-mini"):
    """
    Factory to create a query rewriting node.
    
    Uses a fast model to rewrite vague or poorly-performing queries.
    """
    
    def rewrite_node(state: RAGState) -> Dict[str, Any]:
        """
        Rewrite the query to improve retrieval results.
        
        Analyzes what was retrieved and reformulates the question
        to be more specific or use different terminology.
        """
        start = time.perf_counter()
        
        original_query = state["question"]
        current_query = state.get("rewritten_query") or original_query
        documents = state.get("documents", [])
        rewrite_count = state.get("rewrite_count", 0)
        
        # Build context from current (poor) results
        doc_snippets = "\n".join([
            f"- {doc.page_content[:150]}..."
            for doc in documents[:3]
        ]) if documents else "(no documents retrieved)"
        
        rewriter_llm = ChatOpenAI(model=llm_model, temperature=0.3)
        structured_rewriter = rewriter_llm.with_structured_output(RewrittenQuery)
        
        try:
            result = structured_rewriter.invoke([
                ("system", """You are a search query optimizer for an agricultural research database about cotton farming.

Your task is to rewrite the user's query to retrieve more relevant documents.

Strategies:
- Add specific agricultural terms (e.g., "irrigation" → "drip irrigation scheduling")
- Include synonyms (e.g., "bugs" → "pests and insects")
- Be more specific about the topic
- Focus on the core information need

Keep the query concise (under 20 words)."""),
                ("human", f"""Original question: {original_query}

Current search query: {current_query}

Documents retrieved (low relevance):
{doc_snippets}

Rewrite the query to find better documents:""")
            ])
            
            new_query = result.query.strip()
            logger.info(f"[rewrite] '{current_query}' → '{new_query}' ({result.reasoning})")
            
        except Exception as e:
            logger.error(f"[rewrite] failed: {e}")
            new_query = current_query  # Keep current on failure
        
        elapsed = time.perf_counter() - start
        timings = list(state.get("timings", []))
        timings.append({"stage": "rewrite", "seconds": elapsed})
        
        return {
            "rewritten_query": new_query,
            "rewrite_count": rewrite_count + 1,
            "timings": timings,
            # Clear previous docs/grades for fresh retrieval
            "documents": [],
            "relevance_grades": [],
        }
    
    return rewrite_node
