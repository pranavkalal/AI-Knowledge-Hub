# rag/segment/chunker.py
from typing import List, Dict, Iterable
from transformers import AutoTokenizer

# Use GPT-2 tokenizer with no length cap, just for tokenization
tokenizer = AutoTokenizer.from_pretrained(
    "gpt2",
    use_fast=True,
    model_max_length=10**9,   # disable max length warnings
    truncation=False
)

def chunk_text(text: str, max_tokens=512, overlap=64) -> List[str]:
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        # prevent cleanup messing with spacing
        chunk = tokenizer.decode(tokens[start:end], clean_up_tokenization_spaces=False)
        chunks.append(chunk)
        if end == len(tokens):
            break
        start = end - overlap  # step back for overlap
    return chunks

def chunk_record(rec: Dict, max_tokens=512, overlap=64) -> List[Dict]:
    parts = chunk_text(rec["text"], max_tokens, overlap)
    out = []
    for i, chunk in enumerate(parts, 1):
        new = dict(rec)
        new.update({
            "id": f"{rec['id']}_chunk{i:04d}",
            "doc_id": rec["id"],  # keep link to parent doc
            "chunk_index": i,
            "text": chunk,
            "n_tokens": len(tokenizer.encode(chunk)),
            "chars": len(chunk),
        })
        out.append(new)
    return out

def chunk_stream(records: Iterable[Dict], max_tokens=512, overlap=64) -> Iterable[Dict]:
    for rec in records:
        yield from chunk_record(rec, max_tokens=max_tokens, overlap=overlap)
