# rag/extract/pipeline.py
import json
import os
from typing import Dict, Iterable
from .cleaners import clean_document_text

def read_jsonl(path: str) -> Iterable[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def write_jsonl(path: str, records: Iterable[Dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def clean_records(records: Iterable[Dict]) -> Iterable[Dict]:
    for rec in records:
        txt = rec.get("text", "")
        # skip truly empty docs
        if not txt or sum(ch.isalnum() for ch in txt) < 50:
            continue
        out = dict(rec)               # keep id/title/year/filename/meta etc.
        out["text"] = clean_document_text(txt)
        yield out
