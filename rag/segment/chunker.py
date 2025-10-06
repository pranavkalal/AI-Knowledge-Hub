# rag/segment/chunker.py

from __future__ import annotations
from typing import List, Dict, Iterable, Tuple, Callable, Optional, Set
import re
import json

# Tokenizer: prefer cl100k_base; fall back to GPT-2 fast tokenizer
def _get_tokenizer() -> Tuple[Callable[[str], List[int]], Callable[[List[int]], str], str]:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return enc.encode, enc.decode, "cl100k_base"
    except Exception:
        from transformers import AutoTokenizer  # type: ignore
        tok = AutoTokenizer.from_pretrained("gpt2", use_fast=True, model_max_length=10**9)
        return tok.encode, tok.decode, "gpt2"

encode, decode, _TOKENIZER_NAME = _get_tokenizer()

#Page break marker must match what parse_pdf.py outputs
PAGE_BREAK = "\n\n----- PAGE BREAK -----\n\n"
SPLIT_PAGE = re.compile(r"\n\s*----- PAGE BREAK -----\s*\n", re.I)

#  Heuristics for tables & sentences
TABLE_ROW = re.compile(r"^\s*\|.+\|\s*$")
TABLE_SEP = re.compile(r"^\s*\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|\s*$")

# conservative sentence split that avoids most abbreviations
_SENT_SPLIT = re.compile(
    r"(?<!\b[A-Z])[.!?](?=\s+[A-Z0-9])|(?<=[.?!])\n+(?=[A-Z0-9])"
)

def _split_pages(text: str) -> List[str]:
    return SPLIT_PAGE.split(text)

def _paragraphs(s: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n{2,}", s) if p.strip()]

def _is_table_block(lines: List[str]) -> bool:
    # A minimal check: lines start with '|' and there is a header separator row
    if len(lines) < 2:
        return False
    if not all(l.strip().startswith("|") for l in lines):
        return False
    return any(TABLE_SEP.match(l) for l in lines)

def _split_para_into_blocks(p: str) -> List[str]:
    """
    Split a paragraph into either:
      - one table block (if it's a Markdown table),
      - else sentences (conservative).
    """
    lines = p.splitlines()
    if _is_table_block(lines):
        # keep whole table intact
        return [p]
    # sentence-wise
    parts = []
    start = 0
    for m in _SENT_SPLIT.finditer(p):
        end = m.end()
        seg = p[start:end].strip()
        if seg:
            parts.append(seg)
        start = end
    tail = p[start:].strip()
    if tail:
        parts.append(tail)
    # if nothing matched, return the paragraph
    return parts if parts else [p]

def _blocks_for_page(page_text: str) -> List[str]:
    blocks: List[str] = []
    for para in _paragraphs(page_text):
        blocks.extend(_split_para_into_blocks(para))
    return [b for b in blocks if b.strip()]

def _pack_blocks_with_overlap(
    pages: List[List[str]],
    max_tokens: int = 900,
    overlap: int = 100,
) -> List[Tuple[str, int, int]]:
    """
    Returns list of (chunk_text, page_start, page_end).
    """
    out: List[Tuple[str, int, int]] = []
    cur_tokens: List[int] = []
    chunk_first_page = 0
    cur_page_seen: Optional[int] = None
    last_chunk_tokens: Optional[List[int]] = None

    for pg_idx, blocks in enumerate(pages):
        for blk in blocks:
            t = encode(blk)
            if not cur_tokens:
                # starting a new chunk
                chunk_first_page = pg_idx
            if len(cur_tokens) + len(t) <= max_tokens:
                cur_tokens += t
                cur_page_seen = pg_idx
            else:
                if cur_tokens:
                    out.append((decode(cur_tokens), chunk_first_page, cur_page_seen if cur_page_seen is not None else pg_idx))
                    last_chunk_tokens = cur_tokens
                # start a new chunk with overlap tail (from previous chunk)
                if overlap and last_chunk_tokens:
                    tail = last_chunk_tokens[-overlap:] if len(last_chunk_tokens) > overlap else last_chunk_tokens
                    cur_tokens = tail + t
                else:
                    cur_tokens = list(t)
                chunk_first_page = pg_idx
                cur_page_seen = pg_idx
        # hard page boundary respected implicitly since we iterate per page

    if cur_tokens:
        out.append((decode(cur_tokens), chunk_first_page, cur_page_seen if cur_page_seen is not None else chunk_first_page))

    return out

def _parse_ocr_pages(meta: Optional[Dict]) -> Set[int]:
    if not meta:
        return set()
    raw = meta.get("ocr_pages") or ""
    try:
        return {int(x) for x in str(raw).split(",") if str(x).strip().isdigit()}
    except Exception:
        return set()

def _chunk_has_table(txt: str) -> bool:
    # quick sniff for a Markdown table
    lines = txt.splitlines()
    had_pipe_rows = sum(1 for l in lines if TABLE_ROW.match(l)) >= 2
    has_sep = any(TABLE_SEP.match(l) for l in lines)
    return had_pipe_rows and has_sep

# Public API

def chunk_text(
    text: str,
    max_tokens: int = 900,
    overlap: int = 100,
) -> List[Dict]:
    """
    Returns: list of {"text": str, "page_start": int, "page_end": int}
    """
    page_texts = _split_pages(text)
    page_blocks = [_blocks_for_page(p) for p in page_texts]
    packed = _pack_blocks_with_overlap(page_blocks, max_tokens=max_tokens, overlap=overlap)
    return [{"text": c, "page_start": ps, "page_end": pe} for (c, ps, pe) in packed]

def chunk_record(
    rec: Dict,
    max_tokens: int = 900,
    overlap: int = 100,
) -> List[Dict]:
    """
    Input record must contain at least: { "id": str, "text": str, "meta": dict? }
    """
    assert "id" in rec and "text" in rec, "record must contain 'id' and 'text'"
    meta = rec.get("meta") or {}
    ocr_pages = _parse_ocr_pages(meta)

    chunks = chunk_text(rec["text"], max_tokens=max_tokens, overlap=overlap)
    out: List[Dict] = []
    for i, ch in enumerate(chunks, 1):
        txt = ch["text"]
        toks = encode(txt)
        hints: List[str] = []
        if _chunk_has_table(txt):
            hints.append("table")
        # hint "ocr" if any page in range intersects OCR pages
        if any(p in ocr_pages for p in range(ch["page_start"], ch["page_end"] + 1)):
            hints.append("ocr")

        new = {
            "id": f"{rec['id']}_chunk{i:04d}",
            "doc_id": rec["id"],
            "chunk_index": i,
            "text": txt,
            "n_tokens": len(toks),
            "chars": len(txt),
            "page_start": ch["page_start"],
            "page_end": ch["page_end"],
            "source_hints": hints,
        }
        # keep original record’s meta if you want it at chunk level 
        if meta:
            new["meta"] = meta
        out.append(new)
    return out

def chunk_stream(
    records: Iterable[Dict],
    max_tokens: int = 900,
    overlap: int = 100,
) -> Iterable[Dict]:
    for rec in records:
        for ch in chunk_record(rec, max_tokens=max_tokens, overlap=overlap):
            yield ch

# small CLI for ad-hoc use
if __name__ == "__main__":
    import sys
    import fileinput
    import itertools

    max_tokens = int(sys.argv[1]) if len(sys.argv) > 1 else 900
    overlap = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    # Read JSONL from stdin, write JSONL to stdout
    for line in fileinput.input("-"):
        rec = json.loads(line)
        for ch in chunk_record(rec, max_tokens=max_tokens, overlap=overlap):
            sys.stdout.write(json.dumps(ch, ensure_ascii=False) + "\n")
