# rag/segment/chunker.py
import logging
import os
from functools import lru_cache
from typing import Dict, Iterable, Iterator, List, Optional

from transformers import AutoTokenizer, PreTrainedTokenizerBase

logger = logging.getLogger(__name__)


DEFAULT_EMBED_MODEL = os.environ.get("EMB_MODEL", "BAAI/bge-small-en-v1.5")


def _coerce_int(value: Optional[str], default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


DEFAULT_MAX_TOKENS = _coerce_int(os.environ.get("CHUNK_MAX_TOKENS"), 896)
DEFAULT_OVERLAP = _coerce_int(os.environ.get("CHUNK_OVERLAP"), 128)


def _load_hf_tokenizer(name: str) -> Optional[PreTrainedTokenizerBase]:
    try:
        tok = AutoTokenizer.from_pretrained(name, use_fast=True)
    except (ValueError, OSError, RuntimeError):
        return None
    if getattr(tok, "model_max_length", None) and tok.model_max_length < 10**6:
        tok.model_max_length = 10**6
    return tok


@lru_cache(maxsize=4)
def get_tokenizer(model_name: Optional[str] = None) -> PreTrainedTokenizerBase:
    """Load and cache a fast tokenizer for chunking text.

    Falls back to ``CHUNK_TOKENIZER_MODEL`` or BAAI/bge-small-en-v1.5 when the
    requested embedding family (for example OpenAI ``text-embedding-3-small``)
    does not expose a Hugging Face tokenizer.
    
    Set USE_TIKTOKEN=1 to use OpenAI's tiktoken instead (recommended for OpenAI embeddings).
    """
    # Check if we should use tiktoken
    use_tiktoken = os.environ.get("USE_TIKTOKEN", "").lower() in ("1", "true", "yes")
    if use_tiktoken:
        from rag.segment.tiktoken_wrapper import TiktokenWrapper
        logger.info("Using OpenAI tiktoken encoder (cl100k_base)")
        return TiktokenWrapper()

    requested = model_name or DEFAULT_EMBED_MODEL
    fallback_env = os.environ.get("CHUNK_TOKENIZER_MODEL")
    fallback_default = "BAAI/bge-small-en-v1.5"

    candidates: List[str] = []
    # Attempt the requested model first
    candidates.append(requested)
    if fallback_env and fallback_env not in candidates:
        candidates.append(fallback_env)
    if requested.startswith("text-embedding-") and fallback_default not in candidates:
        candidates.append(fallback_default)

    for name in candidates:
        tok = _load_hf_tokenizer(name)
        if tok is not None:
            if name != requested:
                logger.warning(
                    "Tokenizer '%s' unavailable; falling back to '%s' for chunking.",
                    requested,
                    name,
                )
            logger.info("Loaded tokenizer: %s (model_max_length=%s)", name, tok.model_max_length)
            return tok

    raise RuntimeError(f"Could not load any tokenizer. Tried: {candidates}")


def _resolve_char_span(
    offsets: List[tuple[int, int]],
    start_idx: int,
    end_idx: int,
    text_len: int,
) -> tuple[int, int]:
    """Convert token index range to character offsets."""
    span_start = offsets[start_idx][0] if offsets[start_idx][0] is not None else 0
    span_end = span_start

    for idx in range(end_idx - 1, start_idx - 1, -1):
        off = offsets[idx]
        if off[1] is not None and off[1] > span_start:
            span_end = off[1]
            break

    if span_end <= span_start:
        span_end = offsets[end_idx - 1][1] or text_len
        if span_end <= span_start:
            span_end = text_len

    span_start = max(0, min(span_start, text_len))
    span_end = max(span_start, min(span_end, text_len))
    return span_start, span_end




def chunk_text(
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap: int = DEFAULT_OVERLAP,
    *,
    tokenizer: Optional[PreTrainedTokenizerBase] = None,
) -> Iterator[Dict[str, int | str]]:
    """
    Yield chunk dictionaries containing text and positional metadata.

    Each yielded dict includes: text, token_start, token_end, char_start, char_end.
    Defaults are tuned for OpenAI `text-embedding-3-small` (max_tokens≈896, overlap≈128).
    Override via function args or env vars `CHUNK_MAX_TOKENS` / `CHUNK_OVERLAP`.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= max_tokens:
        raise ValueError("overlap must be smaller than max_tokens")

    tokenizer = tokenizer or get_tokenizer()
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
    )
    input_ids = encoded.get("input_ids", [])
    offsets = encoded.get("offset_mapping", [])

    if not input_ids:
        return

    stride = max_tokens - overlap
    total_tokens = len(input_ids)
    truncated_logged = False
    index = 0

    while index < total_tokens:
        end = min(index + max_tokens, total_tokens)
        char_start, char_end = _resolve_char_span(offsets, index, end, len(text))
        chunk_text_value = text[char_start:char_end]
        if not chunk_text_value and char_end <= char_start:
            # Fallback: include at least one character to prevent empty chunks.
            char_end = min(len(text), char_start + 1)
            chunk_text_value = text[char_start:char_end]

        if end < total_tokens and not truncated_logged:
            logger.info(
                "Chunk truncated at %s tokens (document length %s tokens)",
                max_tokens,
                total_tokens,
            )
            truncated_logged = True

        yield {
            "text": chunk_text_value,
            "token_start": index,
            "token_end": end,
            "char_start": char_start,
            "char_end": char_end,
        }

        if end == total_tokens:
            break
        index += stride


def chunk_record(
    rec: Dict,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap: int = DEFAULT_OVERLAP,
    *,
    tokenizer: Optional[PreTrainedTokenizerBase] = None,
) -> List[Dict]:
    """Return chunked records with minimal metadata and offsets."""
    text = rec.get("text") or ""
    if not text:
        return []

    tokenizer = tokenizer or get_tokenizer()
    doc_id = rec.get("id") or rec.get("doc_id")
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
        chunk_text(text, max_tokens=max_tokens, overlap=overlap, tokenizer=tokenizer),
        start=1,
    ):
        chunk_rec = {
            "id": f"{doc_id}_chunk{idx:04d}",
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
    return chunks


def chunk_stream(
    records: Iterable[Dict],
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap: int = DEFAULT_OVERLAP,
    *,
    tokenizer: Optional[PreTrainedTokenizerBase] = None,
) -> Iterator[Dict]:
    tokenizer = tokenizer or get_tokenizer()
    for rec in records:
        for chunk in chunk_record(
            rec,
            max_tokens=max_tokens,
            overlap=overlap,
            tokenizer=tokenizer,
        ):
            yield chunk
