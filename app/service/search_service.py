# app/service/search_service.py
import json, subprocess, sys, os
from typing import Dict, Any, List, Optional
from pathlib import Path

DEFAULTS = dict(k=8, neighbors=2, per_doc=2)
ROOT = Path(__file__).resolve().parents[2]   # project root
QUERY_SCRIPT = ROOT / "scripts" / "query_faiss.py"

def _run_cli(
    q: str,
    k: int,
    neighbors: int,
    per_doc: int,
    contains: Optional[str],
    year_min: Optional[int],
    year_max: Optional[int],
) -> List[dict]:
    if not QUERY_SCRIPT.exists():
        raise RuntimeError(f"Missing script: {QUERY_SCRIPT}")

    cmd = [
        sys.executable, str(QUERY_SCRIPT),
        "--q", q,
        "--k", str(k),
        "--neighbors", str(neighbors),
        "--per-doc", str(per_doc),
        "--json",
    ]
    if contains:
        cmd += ["--contains", contains]
    if year_min is not None:
        cmd += ["--year-min", str(year_min)]
    if year_max is not None:
        cmd += ["--year-max", str(year_max)]

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT}{os.pathsep}{env.get('PYTHONPATH','')}"

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=45)
    if proc.returncode != 0:
        raise RuntimeError(f"query_faiss failed (code {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}")

    out = []
    for ln in proc.stdout.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        out.append(json.loads(ln))
    return out


def search_service(
    q: str,
    k: int | None = None,
    neighbors: int | None = None,
    per_doc: int | None = None,
    contains: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
) -> Dict[str, Any]:
    k = k or DEFAULTS["k"]
    neighbors = neighbors if neighbors is not None else DEFAULTS["neighbors"]
    per_doc = per_doc if per_doc is not None else DEFAULTS["per_doc"]

    rows = _run_cli(q, k, neighbors, per_doc, contains, year_min, year_max)

    normalized = []
    for r in rows:
        cid = r.get("id") or ""
        normalized.append({
            "doc_id": r.get("doc_id") or cid.split("_chunk")[0],
            "chunk_id": int((cid.split("_chunk")[-1] or "0")[:4]) if "_chunk" in cid else 0,
            "score": r.get("score", 0.0),
            "title": r.get("title"),
            "year": r.get("year"),
            "preview": r.get("preview") or "",
            "neighbor_window": None,
            "source_url": None,
            "filename": None,
        })

    # >>> minimal fix: shape to SearchResponse <<<
    return {
        "query": q,
        "params": {
            "k": k,
            "neighbors": neighbors,
            "per_doc": per_doc,
            "contains": contains,
            "year_min": year_min,
            "year_max": year_max,
        },
        "count": len(normalized),
        "results": normalized,
    }
