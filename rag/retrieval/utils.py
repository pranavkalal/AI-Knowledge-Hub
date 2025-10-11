"""
Shared retrieval utilities for both CLI and service layers.
Keeps neighbour stitching, keyword/year filtering, and preview construction consistent.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from rag.retrieval.pdf_links import enrich_metadata


def neighbor_ids(chunk_id: str, neighbors: int) -> List[str]:
    """Return a list of neighbour chunk IDs ±N around chunk_id (expects suffix `_chunkNNNN`)."""
    if neighbors <= 0:
        return [chunk_id]
    base, _, tail = chunk_id.partition("_chunk")
    try:
        idx = int(tail)
    except ValueError:
        return [chunk_id]
    ids: List[str] = []
    for j in range(idx - neighbors, idx + neighbors + 1):
        ids.append(f"{base}_chunk{j:04d}")
    return ids


def load_lookup(chunks_path: str | Path, needed_ids: Iterable[str]) -> Dict[str, Dict]:
    """Load only the required chunk records from disk."""
    path = Path(chunks_path)
    lookup: Dict[str, Dict] = {}
    if not needed_ids or not path.exists():
        return lookup

    needed = set(needed_ids)
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cid = rec.get("id")
            if cid in needed:
                lookup[cid] = rec
                if len(lookup) == len(needed):
                    break
    return lookup


def passes_filters(
    rec: Dict,
    contains_any: Optional[List[str]] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> bool:
    """Apply keyword and year filters to a chunk record."""
    contains_any = contains_any or []
    if contains_any:
        text = (rec.get("text") or rec.get("preview") or "").lower()
        if not any(kw in text for kw in contains_any):
            return False

    year = rec.get("year")
    try:
        year_int = int(year)
    except (TypeError, ValueError):
        year_int = None

    if year_min is not None and year_int is not None and year_int < year_min:
        return False
    if year_max is not None and year_int is not None and year_int > year_max:
        return False

    return True


def stitch_preview(
    center_rec: Dict,
    lookup: Dict[str, Dict],
    *,
    neighbors: int = 1,
    max_chars: int = 1800,
    no_truncate: bool = False,
) -> str:
    """
    Stitch ±neighbors chunks from the same doc to form a readable preview.
    Falls back to the center chunk text if neighbours cannot be found.
    """
    chunk_id = center_rec.get("id")
    if not chunk_id:
        return (center_rec.get("text") or "")[:max_chars]

    doc_id = center_rec.get("doc_id") or chunk_id.split("_chunk")[0]
    parts: List[str] = []
    total_len = 0

    for nid in neighbor_ids(chunk_id, neighbors):
        rec = lookup.get(nid)
        if not rec:
            continue
        rec_doc = rec.get("doc_id") or nid.split("_chunk")[0]
        if rec_doc != doc_id:
            continue
        txt = (rec.get("text") or "").replace("\n", " ").strip()
        if not txt:
            continue
        if no_truncate:
            parts.append(txt)
            continue
        room = max_chars - total_len
        if room <= 0:
            break
        if len(txt) <= room:
            parts.append(txt)
            total_len += len(txt)
        else:
            parts.append(txt[:room])
            total_len += room
            break

    if not parts:
        return ((center_rec.get("text") or "").replace("\n", " "))[:max_chars]
    joined = " ".join(parts)
    return joined if no_truncate else joined[:max_chars]


@dataclass
class RetrievalSettings:
    contains: List[str]
    year_min: Optional[int]
    year_max: Optional[int]
    neighbors: int
    per_doc: int
    max_preview_chars: int
    max_snippet_chars: int


def resolve_retrieval_settings(filters: Optional[Dict[str, Any]]) -> RetrievalSettings:
    """Normalise filter inputs from API or config into a structured settings object."""
    filters = filters or {}

    def _to_int(value, *, default: Optional[int] = None, minimum: Optional[int] = None) -> Optional[int]:
        if value is None or value == "":
            return default
        try:
            num = int(value)
            if minimum is not None and num < minimum:
                return minimum
            return num
        except (TypeError, ValueError):
            return default

    raw_contains = filters.get("contains")
    if isinstance(raw_contains, str):
        contains = [s.strip().lower() for s in raw_contains.split(",") if s.strip()]
    elif isinstance(raw_contains, (list, tuple, set)):
        contains = [str(s).strip().lower() for s in raw_contains if str(s).strip()]
    else:
        contains = []

    # Deduplicate while preserving order
    seen = set()
    unique_contains: List[str] = []
    for kw in contains:
        if kw not in seen:
            seen.add(kw)
            unique_contains.append(kw)

    year_min = _to_int(filters.get("year_min"))
    year_max = _to_int(filters.get("year_max"))
    neighbors = _to_int(filters.get("neighbors"), default=1, minimum=0)
    per_doc = _to_int(filters.get("per_doc"), default=2, minimum=1)
    max_preview_chars = _to_int(filters.get("max_preview_chars"), default=1800, minimum=100) or 1800
    max_snippet_chars = _to_int(filters.get("max_snippet_chars"), default=500, minimum=120) or 500

    return RetrievalSettings(
        contains=unique_contains,
        year_min=year_min,
        year_max=year_max,
        neighbors=neighbors,
        per_doc=per_doc,
        max_preview_chars=max_preview_chars,
        max_snippet_chars=max_snippet_chars,
    )


def prepare_hits(
    hits: Sequence[Dict[str, Any]],
    store: Any,
    settings: RetrievalSettings,
    *,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Apply filters, per-doc limits, and neighbour stitching to a list of raw FAISS hits."""
    if not hits:
        return []

    lookup: Dict[str, Dict[str, Any]] = {}
    if hasattr(store, "get_meta_map"):
        try:
            lookup = dict(store.get_meta_map())  # type: ignore[attr-defined]
        except Exception:
            lookup = {}

    per_doc_counts = defaultdict(int)
    processed: List[Dict[str, Any]] = []

    for hit in hits:
        md = hit.get("metadata", {}) if isinstance(hit, dict) else {}
        chunk_id = md.get("id") or hit.get("id")
        if not chunk_id:
            continue

        if chunk_id not in lookup and hasattr(store, "get_metadata"):
            try:
                extra = store.get_metadata(chunk_id)  # type: ignore[attr-defined]
            except Exception:
                extra = None
            if extra:
                lookup[chunk_id] = extra

        base_meta = lookup.get(chunk_id, md)
        meta = dict(base_meta) if isinstance(base_meta, dict) else {}
        meta["id"] = chunk_id
        doc_id = meta.get("doc_id") or chunk_id.split("_chunk")[0]
        meta["doc_id"] = doc_id

        title = meta.get("title") or meta.get("doc_title") or doc_id or chunk_id
        meta["title"] = title
        year_val = meta.get("year")
        if isinstance(year_val, str):
            try:
                meta["year"] = int(year_val)
            except ValueError:
                meta["year"] = year_val

        meta = enrich_metadata(meta)

        if not passes_filters(meta, settings.contains, settings.year_min, settings.year_max):
            continue

        if settings.per_doc > 0 and per_doc_counts[doc_id] >= settings.per_doc:
            continue

        preview_lookup = lookup if lookup else {chunk_id: meta}
        preview = stitch_preview(
            meta,
            preview_lookup,
            neighbors=settings.neighbors,
            max_chars=settings.max_preview_chars,
        )
        meta["preview"] = preview
        meta.setdefault("text", preview)

        score = hit.get("score")
        score_float = float(score) if score is not None else 0.0
        meta["score"] = score_float

        processed.append({"id": chunk_id, "score": score_float, "metadata": meta})
        per_doc_counts[doc_id] += 1

        if limit is not None and len(processed) >= limit:
            break

    return processed


def build_prompt_entries(
    hits: Sequence[Dict[str, Any]],
    *,
    snippet_char_limit: int = 500,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Return formatted prompt lines and structured citation data from prepared hits."""
    lines: List[str] = []
    citations: List[Dict[str, Any]] = []

    for idx, hit in enumerate(hits, start=1):
        md = hit.get("metadata", {}) if isinstance(hit, dict) else {}
        sid = f"S{idx}"

        snippet_text = md.get("preview") or md.get("text") or ""
        snippet = snippet_text[:snippet_char_limit]
        if len(snippet_text) > snippet_char_limit:
            snippet += "…"

        title = md.get("title") or md.get("doc_id") or md.get("id") or "Source"
        doc_id = md.get("doc_id") or md.get("id") or ""
        year = md.get("year")
        page = md.get("page")

        meta_parts: List[str] = []
        if year not in (None, ""):
            meta_parts.append(str(year))
        if doc_id:
            meta_parts.append(doc_id)
        if page not in (None, ""):
            meta_parts.append(f"p.{page}")
        suffix = f" ({', '.join(meta_parts)})" if meta_parts else ""

        lines.append(f"[{sid}] {title}{suffix}: {snippet}")

        citations.append(
            {
                "sid": sid,
                "doc_id": doc_id,
                "title": md.get("title"),
                "name": md.get("name"),
                "year": year,
                "page": page,
                "url": md.get("url"),
                "score": hit.get("score"),
                "cosine": hit.get("score"),
                "snippet": snippet_text,
            }
        )

    return lines, citations
