# tasks.py
# Cross-platform task runner (Invoke) so we stop arguing about make.
# Usage:
#   invoke -l                       # list tasks
#   invoke build                    # ingest -> chunk -> embed -> faiss
#   invoke api                      # start FastAPI (dev)
#   invoke ui                       # start Streamlit
#   invoke dev                      # build if needed, start API+UI together
#   invoke eval-extract             # run extraction audit
#   invoke query --q="water use"    # quick FAISS query
#   invoke clean / clobber / rebuild

from invoke import task
import os, sys, subprocess
from pathlib import Path

PY        = sys.executable
API_HOST  = os.environ.get("HOST", "0.0.0.0")
API_PORT  = int(os.environ.get("PORT", "8000"))
UI_PORT   = int(os.environ.get("UI_PORT", "8501"))
API_BASE  = os.environ.get("COTTON_API_BASE", f"http://localhost:{API_PORT}/api")

# Paths
RAW_DIR   = Path("data/raw")
DOCS      = Path("data/staging/docs.jsonl")
CHUNKS    = Path("data/staging/chunks.jsonl")
EMB_DIR   = Path("data/embeddings")
EMB_EDS   = EMB_DIR / "embeddings.npy"
EMB_IDS   = EMB_DIR / "ids.npy"
FAISS     = EMB_DIR / "vectors.faiss"

def _run(cmd, **kwargs):
    print(f"$ {cmd}")
    return subprocess.run(cmd, shell=True, check=True, **kwargs)

def _ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

@task
def ingest(c):
    """Parse PDFs -> docs.jsonl"""
    _ensure_dir(DOCS)
    _run(f'{PY} app/ingest.py --in {RAW_DIR} --out {DOCS}')

@task
def chunk(c, max_tokens=512, overlap=64):
    """Chunk docs -> chunks.jsonl"""
    _ensure_dir(CHUNKS)
    _run(f'{PY} app/chunk.py --in {DOCS} --out {CHUNKS} --max_tokens {max_tokens} --overlap {overlap}')

@task
def embed(c):
    """Build embeddings.npy + ids.npy"""
    _ensure_dir(EMB_EDS)
    _run(f'{PY} scripts/build_embeddings.py --in {CHUNKS} --out_dir {EMB_DIR}')

@task
def faiss(c):
    """Build FAISS index"""
    _ensure_dir(FAISS)
    _run(f'{PY} scripts/build_faiss.py --embeddings {EMB_EDS} --ids {EMB_IDS} --out {FAISS}')

@task
def build(c):
    """Full pipeline: ingest -> chunk -> embed -> faiss"""
    if not RAW_DIR.exists():
        raise SystemExit("No data/raw directory found. Put PDFs in data/raw/")
    ingest(c)
    chunk(c)
    embed(c)
    faiss(c)

@task
def query(c, q, k=8, neighbors=2, per_doc=2):
    """CLI test against FAISS"""
    _run(
        f'{PY} scripts/query_faiss.py --q "{q}" --k {k} --neighbors {neighbors} --per-doc {per_doc}'
    )

@task
def api(c, reload=True):
    """Start FastAPI only"""
    reload_flag = "--reload" if str(reload).lower() != "false" else ""
    env = os.environ.copy()
    env["PYTHONPATH"] = f'{Path(".").resolve()}{os.pathsep}{env.get("PYTHONPATH","")}'
    cmd = f'{PY} -m uvicorn app.main:app --host {API_HOST} --port {API_PORT} {reload_flag}'
    _run(cmd, env=env)

@task
def ui(c):
    """Start Streamlit UI only"""
    env = os.environ.copy()
    env["COTTON_API_BASE"] = API_BASE
    _run(f'streamlit run ui/streamlit_app.py --server.port {UI_PORT}', env=env)

@task
def dev(c):
    """Ensure index exists, then run API + UI together; stop API when UI exits."""
    # Build if missing
    if not FAISS.exists():
        print("FAISS index missing → running full build...")
        build(c)

    # Start API in background
    env_api = os.environ.copy()
    env_api["PYTHONPATH"] = f'{Path(".").resolve()}{os.pathsep}{env_api.get("PYTHONPATH","")}'
    api_proc = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", API_HOST, "--port", str(API_PORT), "--reload"],
        env=env_api,
    )
    print(f"[api] pid={api_proc.pid} on http://localhost:{API_PORT}/api")

    try:
        # Start UI (blocking)
        env_ui = os.environ.copy()
        env_ui["COTTON_API_BASE"] = API_BASE
        _run(f'streamlit run ui/streamlit_app.py --server.port {UI_PORT}', env=env_ui)
    finally:
        # Kill API when UI closes
        api_proc.terminate()
        try:
            api_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            api_proc.kill()

@task(name="eval-extract")
def eval_extract(c):
    """Run extraction audit"""
    _run(f'{PY} app/extraction_eval.py')

@task
def clean(c):
    """Remove intermediate artifacts (safe)"""
    for p in [DOCS, CHUNKS]:
        if p.exists():
            p.unlink()
            print("deleted", p)

@task
def clobber(c):
    """Blow away embeddings + index (dangerous)"""
    for p in [EMB_EDS, EMB_IDS, FAISS]:
        if p.exists():
            p.unlink()
            print("deleted", p)

@task
def rebuild(c):
    """Full clean rebuild of the pipeline"""
    clobber(c)
    build(c)
    print("Rebuild complete.")