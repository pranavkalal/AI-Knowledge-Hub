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
    Calculate the union bounding box from a list of line bboxes.
    Handles both OLD format (polygon) and NEW format (simplified [x,y,w,h]).
    Returns [x, y, width, height] in points.
    """
    import json
    if isinstance(bboxes, str):
        try:
            bboxes = json.loads(bboxes)
        except Exception:
            return None
            
    if not bboxes or not isinstance(bboxes, list):
        return None

    all_x1, all_y1, all_x2, all_y2 = [], [], [], []
    
    for item in bboxes:
        # NEW FORMAT: {"text": "...", "bbox": [x, y, w, h]} - already in points
        if "bbox" in item:
            bbox = item.get("bbox")
            if bbox and isinstance(bbox, list) and len(bbox) >= 4:
                x, y, w, h = bbox[:4]
                all_x1.append(x)
                all_y1.append(y)
                all_x2.append(x + w)
                all_y2.append(y + h)
                continue
        
        # OLD FORMAT: {"text": "...", "polygon": [...]} - in inches
        poly = item.get("polygon")
        if poly and isinstance(poly, list) and len(poly) >= 4:
            # polygon is [x1, y1, x2, y2, ...]
            xs = poly[0::2]
            ys = poly[1::2]
            # Convert inches to points (72 DPI)
            all_x1.append(min(xs) * 72)
            all_y1.append(min(ys) * 72)
            all_x2.append(max(xs) * 72)
            all_y2.append(max(ys) * 72)
        
    if not all_x1:
        return None
        
    min_x = min(all_x1)
    min_y = min(all_y1)
    max_x = max(all_x2)
    max_y = max(all_y2)
    
    return [min_x, min_y, max_x - min_x, max_y - min_y]


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
    bboxes_raw = metadata.get("bboxes")
    bbox = _calculate_bbox(bboxes_raw)

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
