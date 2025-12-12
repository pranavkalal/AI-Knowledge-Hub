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


def _calculate_bbox(bboxes: Any) -> Optional[List[float]]:
    """
    Calculate the union bounding box from a list of Azure polygons.
    Converts from inches (Azure) to points (72 DPI).
    Returns [x, y, width, height].
    """
    import json
    if isinstance(bboxes, str):
        try:
            bboxes = json.loads(bboxes)
        except Exception:
            return None
            
    if not bboxes or not isinstance(bboxes, list):
        return None

    all_x = []
    all_y = []
    
    for item in bboxes:
        # item is {"text": "...", "polygon": [...]}
        poly = item.get("polygon")
        if not poly or not isinstance(poly, list):
            continue
        
        # polygon is [x1, y1, x2, y2, ...]
        # separate x and y
        xs = poly[0::2]
        ys = poly[1::2]
        all_x.extend(xs)
        all_y.extend(ys)
        
    if not all_x or not all_y:
        return None
        
    min_x = min(all_x)
    min_y = min(all_y)
    max_x = max(all_x)
    max_y = max(all_y)
    
    # Convert inches to points (72 DPI)
    return [
        min_x * 72,
        min_y * 72,
        (max_x - min_x) * 72,
        (max_y - min_y) * 72
    ]


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
    
    # Calculate bbox if available
    bbox = _calculate_bbox(metadata.get("bboxes"))

    faiss_score = None
    rerank_score = None
    if isinstance(hit, dict):
        faiss_score = hit.get("faiss_score")
        rerank_score = hit.get("rerank_score")
    if faiss_score is None:
        faiss_score = metadata.get("faiss_score")
    if rerank_score is None:
        rerank_score = metadata.get("rerank_score")

    return {
        "title": metadata.get("title"),
        "year": metadata.get("year"),
        "page": page,
        "bbox": bbox,
        "doc_id": metadata.get("doc_id"),
        "score": hit.get("score") if isinstance(hit, dict) else metadata.get("score"),
        "snippet": metadata.get("preview") or metadata.get("text") or "",
        "url": metadata.get("url"),
        "source_url": metadata.get("source_url"),
        "rel_path": metadata.get("rel_path") or metadata.get("filename"),
        "filename": metadata.get("filename"),
    }
