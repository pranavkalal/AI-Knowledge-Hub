# app/service/search_service.py
# Purpose: Call the existing CLI (scripts/query_faiss.py), parse its JSONL output,
# and normalize it into the stable /search response contract.

import json
import subprocess
import sys
import os
from typing import Dict, Any, List
from pathlib import Path

DEFAULTS = dict(k=8, neighbors=2, per_doc=2)
ROOT = Path(__file__).resolve().parents[2]
QUERY_SCRIPT = ROOT / "scripts" / "query_faiss.py"

def _run_cli(q: str, k: int) -> List[dict]:
    if not QUERY_SCRIPT.exists():
        raise RuntimeError(f"Missing script: {QUERY_SCRIPT}")

    cmd = [
        sys.executable, str(QUERY_SCRIPT),
        "--q", q,
        "--k", str(k),
        "--neighbors", str(DEFAULTS["neighbors"]),
        "--per-doc", str(DEFAULTS["per_doc"]),
        "--json",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT}{os.pathsep}{env.get('PYTHONPATH','')}"

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=45,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"query_faiss failed (code {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")

    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    out: List[dict] = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Non-JSON line from query_faiss: {e}: {ln[:200]}")
    return out

def search_service(q: str, k: int | None = None) -> Dict[str, Any]:
    k = k or DEFAULTS["k"]
    rows = _run_cli(q, k)

    # Your script outputs: score, id, doc_id, title, year, preview
    normalized = []
    for r in rows:
        normalized.append({
            "doc_id": r.get("doc_id") or r.get("id", "").split("_chunk")[0],
            "chunk_id": int((r.get("id","").split("_chunk")[-1] or "0")[:4]) if "_chunk" in (r.get("id") or "") else 0,
            "score": r.get("score", 0.0),
            "title": r.get("title"),
            "year": r.get("year"),
            "preview": r.get("preview") or "",
            "neighbor_window": None,      # not emitted by CLI; keep null for now
            "source_url": None,           # add later when you wire it
            "filename": None              # add later if available
        })

    return {
        "query": q,
        "params": {"k": k},
        "count": len(normalized),
        "results": normalized,
    }
