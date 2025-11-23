# rag/segment/semantic_chunker.py
"""
Semantic chunking that respects document structure.
Uses LangChain's RecursiveCharacterTextSplitter to preserve semantic boundaries.
"""

import logging
from typing import Dict, Iterator, List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from transformers import PreTrainedTokenizerBase

from rag.ingest.chunkers.base import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_OVERLAP,
    get_tokenizer,
)

logger = logging.getLogger(__name__)


def chunk_text_semantic(
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap: int = DEFAULT_OVERLAP,
    *,
    tokenizer: Optional[PreTrainedTokenizerBase] = None,
) -> Iterator[Dict[str, int | str]]:
    """
    Yield chunk dictionaries with semantic boundaries preserved.
    
    Unlike fixed-size chunking, this respects:
    - Section breaks (\\n\\n\\n)
    - Paragraph breaks (\\n\\n)
    - Sentence boundaries (. )
    - Word boundaries ( )
    
    Each yielded dict includes: text, token_start, token_end, char_start, char_end.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= max_tokens:
        raise ValueError("overlap must be smaller than max_tokens")
    
    tokenizer = tokenizer or get_tokenizer()
    
    # Define separators in order of preference
    # Try to split on larger semantic units first
    separators = [
        "\n\n\n",  # Section breaks (multiple blank lines)
        "\n\n",    # Paragraph breaks
        "\n",      # Line breaks
        ". ",      # Sentence boundaries
        "! ",      # Exclamation sentences
        "? ",      # Question sentences
        "; ",      # Semicolon clauses
        ", ",      # Comma phrases
        " ",       # Words
        "",        # Characters (fallback)
    ]
    
    # Create splitter with token-aware length function
    def token_length(text: str) -> int:
        """Count tokens instead of characters."""
        try:
            return len(tokenizer.encode(text, add_special_tokens=False))
        except Exception:
            # Fallback to character count if tokenization fails
            return len(text)
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=overlap,
        length_function=token_length,
        separators=separators,
        is_separator_regex=False,
        keep_separator=True,  # Preserve separators for context
    )
    
    # Split text into semantic chunks
    chunks = splitter.split_text(text)
    
    if not chunks:
        return
    
    # Convert to format compatible with existing pipeline
    char_offset = 0
    token_offset = 0
    
    for idx, chunk_text in enumerate(chunks):
        # Calculate token boundaries
        token_ids = tokenizer.encode(chunk_text, add_special_tokens=False)
        n_tokens = len(token_ids)
        
        # Calculate character boundaries
        char_start = char_offset
        char_end = char_offset + len(chunk_text)
        
        yield {
            "text": chunk_text,
            "token_start": token_offset,
            "token_end": token_offset + n_tokens,
            "char_start": char_start,
            "char_end": char_end,
        }
        
        # Update offsets
        # For overlap calculation, we need to account for the stride
        char_offset = char_end
        token_offset += n_tokens
        
        # Adjust for overlap in next iteration
        if idx < len(chunks) - 1:
            # The splitter handles overlap internally, so we just track position
            token_offset -= overlap


def chunk_record_semantic(
    rec: Dict,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap: int = DEFAULT_OVERLAP,
    *,
    tokenizer: Optional[PreTrainedTokenizerBase] = None,
) -> List[Dict]:
    """Return semantically chunked records with metadata and offsets."""
    text = rec.get("text") or ""
    if not text:
        return []
    
    tokenizer = tokenizer or get_tokenizer()
    # BUGFIX: Prioritize doc_id over id (id includes element suffix like _elem0001)
    doc_id = rec.get("doc_id") or rec.get("id")
    if not doc_id:
        raise ValueError("Record missing 'id' or 'doc_id' field")
    
    base_meta = {
        "doc_id": doc_id,
        "title": rec.get("title"),
        "year": rec.get("year"),
        "page": rec.get("page"),
    }
    
    chunks: List[Dict] = []
    for idx, chunk in enumerate(
        chunk_text_semantic(text, max_tokens=max_tokens, overlap=overlap, tokenizer=tokenizer),
        start=1,
    ):
        chunk_rec = {
            "id": f"{rec['id']}_chunk{idx:04d}",
            "chunk_index": idx,
            "text": chunk["text"],
            "token_start": chunk["token_start"],
            "token_end": chunk["token_end"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
            "n_tokens": chunk["token_end"] - chunk["token_start"],
        }
        for key, value in base_meta.items():
            if value is not None:
                chunk_rec[key] = value
        chunks.append(chunk_rec)
    
    logger.info(
        "Semantic chunking: %s → %d chunks (avg %.1f tokens)",
        doc_id,
        len(chunks),
        sum(c["n_tokens"] for c in chunks) / len(chunks) if chunks else 0,
    )
    
    return chunks
