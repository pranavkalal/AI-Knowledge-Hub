import csv
import json
import os
from typing import Iterable, Dict

def _ensure_parent_dir(path: str):
    parent = os.path.dirname(path) or "."
    if os.path.exists(parent) and not os.path.isdir(parent):
        raise RuntimeError(f"Output parent is a file, not a directory: {parent}. "
                           f"Delete it and recreate the folder.")
    os.makedirs(parent, exist_ok=True)

def write_jsonl(records: Iterable[Dict], path: str):
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def write_csv(records: Iterable[Dict], path: str):
    _ensure_parent_dir(path)
    rows = list(records)
    with open(path, "w", newline="", encoding="utf-8") as f:
        if not rows:
            f.write("")  # create empty file
            return
        keys = sorted({k for r in rows for k in r.keys()})
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
