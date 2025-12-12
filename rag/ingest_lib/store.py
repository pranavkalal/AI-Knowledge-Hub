# rag/ingest_lib/store.py
import json
import csv
from typing import List, Dict, Any
from pathlib import Path

def write_jsonl(records: List[Dict[str, Any]], path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

def write_csv(records: List[Dict[str, Any]], path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not records:
        return
    
    keys = records[0].keys()
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)
