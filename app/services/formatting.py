"""
Common helpers for formatting snippets and metadata across native, CLI, and LangChain paths.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def format_snippet(text: str, length: int = 320) -> str:
    """
    Truncate `text` to at most `length` characters. Append an ellipsis if it was shortened.

    Args:
        text: The full text to trim.
        length: Maximum number of characters to retain.

    Returns:
        The original text if shorter than `length`, otherwise a truncated version with `…`.
    """
    if not text:
        return ""
    text = text.strip()
    if len(text) <= length:
        return text
    return text[:length] + "…"


def format_metadata(meta: Dict[str, Any]) -> str:
    """
    Build a human-readable suffix from metadata fields.

    Prioritises title, year, and page when available. Missing fields are skipped gracefully.

    Args:
        meta: Mapping that may include keys like 'title', 'year', and 'page'.

    Returns:
        A formatted string such as "(Document Title, 2024, p5)" or an empty string if no data.
    """
    if not meta:
        return ""

    parts: list[str] = []
    title = meta.get("title")
    if title:
        parts.append(str(title))

    year = meta.get("year")
    if year not in (None, ""):
        parts.append(str(year))

    page = meta.get("page")
    if page not in (None, ""):
        parts.append(f"p{page}")

    if not parts:
        return ""
    return f"({', '.join(parts)})"


def _coerce_page(value: Any) -> Optional[int]:
    if isinstance(value, list) and value:
        value = value[0]
    if value in (None, "", []):
        return None
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return None


def format_citation(hit: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a normalized citation payload for API responses.

    Args:
        hit: Dictionary containing metadata returned from retrieval.

    Returns:
        A dictionary with standardised keys: title, year, page, doc_id, score, snippet.
    """
    metadata = hit.get("metadata", {}) if isinstance(hit, dict) else {}
    page = _coerce_page(metadata.get("page"))

    return {
        "title": metadata.get("title"),
        "year": metadata.get("year"),
        "page": page,
        "doc_id": metadata.get("doc_id"),
        "score": hit.get("score") if isinstance(hit, dict) else None,
        "snippet": metadata.get("preview") or metadata.get("text") or "",
        "url": metadata.get("url"),
        "source_url": metadata.get("source_url"),
        "rel_path": metadata.get("rel_path") or metadata.get("filename"),
        "filename": metadata.get("filename"),
    }
