# tasks.py
# Invoke is the source of truth.
# Primary:
#   invoke build   -> ingest -> (clean) -> chunk -> embed -> faiss  (fails fast if empty)
#   invoke dev     -> ensure index, then run API + UI together (cleans up API on exit)
# Helpers:
#   invoke api | ui | ingest | clean-extract | chunk | embed | faiss | query | eval-extract | clean | clobber | rebuild

from invoke import task
import os, sys, subprocess, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PY        = sys.executable
API_HOST  = os.environ.get("HOST", "0.0.0.0")
API_PORT  = int(os.environ.get("PORT", "8000"))
UI_PORT   = int(os.environ.get("UI_PORT", "8501"))
API_BASE  = os.environ.get("COTTON_API_BASE", f"http://localhost:{API_PORT}/api")
EMB_MODEL = os.environ.get("EMB_MODEL", "BAAI/bge-small-en-v1.5")

# Paths
RAW_DIR    = Path("data/raw")
INGEST_CFG = Path("configs/ingestion.yaml")
DOCS       = Path("data/staging/docs.jsonl")
CLEANED    = Path("data/staging/cleaned.jsonl")
CHUNKS     = Path("data/staging/chunks.jsonl")

EMB_DIR    = Path("data/embeddings")
EMB_EDS    = EMB_DIR / "embeddings.npy"
EMB_IDS    = EMB_DIR / "ids.npy"
FAISS_IDX  = EMB_DIR / "vectors.faiss"

def _run(cmd, env: dict | None = None, **kwargs):
    """Run shell cmd with repo root on PYTHONPATH, plus optional env overrides."""
    base = os.environ.copy()
    root = str(Path(".").resolve())
    base["PYTHONPATH"] = f'{root}{os.pathsep}{base.get("PYTHONPATH","")}'
    if env:
        base.update(env)
    print(f"$ {cmd}")
    return subprocess.run(cmd, shell=True, check=True, env=base, **kwargs)

def _ensure_parent(path: Path):
    """Ensure the parent directory exists (works for both file and dir paths)."""
    p = Path(path)
    parent = p if p.suffix == "" else p.parent
    parent.mkdir(parents=True, exist_ok=True)

def _jsonl_count(path: Path) -> int:
    if not Path(path).exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)

def _assert_nonempty(label: str, path: Path, hint: str):
    n = _jsonl_count(path)
    if n == 0:
        raise SystemExit(f"[{label}] produced 0 records at {path}.\nHint: {hint}")
    print(f"[{label}] {n} records at {path}")

@task
def ingest(c, config=None):
    """
    Crawl + extract → write docs.jsonl using YAML config.
    Default: configs/ingestion.yaml; override with --config path/to/file.yaml
    """
    cfg = Path(config) if config else INGEST_CFG
    if not cfg.exists():
        raise SystemExit(f"Missing ingest config: {cfg}")
    for p in [DOCS, CLEANED]:
        _ensure_parent(p)
    _ensure_parent(RAW_DIR)
    _run(f"{PY} -m app.ingest --config {cfg}")

@task(name="clean-extract")
def clean_extract(c):
    """Optional cleaning pass into cleaned.jsonl (if you use it)."""
    _ensure_parent(CLEANED)
    _run(f"{PY} -m app.clean_extract --in {DOCS} --out {CLEANED}")

@task
def chunk(c, max_tokens=512, overlap=64, use_cleaned=True):
    """Chunk docs -> chunks.jsonl"""
    _ensure_parent(CHUNKS)
    src = CLEANED if use_cleaned and CLEANED.exists() else DOCS
    _run(f'{PY} -m app.chunk --in {src} --out {CHUNKS} --max_tokens {max_tokens} --overlap {overlap}')

@task
def embed(c):
    """Build embeddings.npy + ids.npy"""
    if _jsonl_count(CHUNKS) == 0:
        raise SystemExit("No chunks with text found. Check data/staging/chunks.jsonl (ingestion probably produced 0 docs).")
    _ensure_parent(EMB_EDS)
    _run(
        f'{PY} -m scripts.build_embeddings '
        f'--chunks {CHUNKS} '
        f'--out_vecs {EMB_EDS} '
        f'--out_ids {EMB_IDS} '
        f'--model "{EMB_MODEL}"'
    )

@task
def faiss(c):
    """Build FAISS index (embeddings -> vectors.faiss)."""
    _ensure_parent(FAISS_IDX)
    _run(f'{PY} -m scripts.build_faiss --vecs {EMB_EDS} --index_out {FAISS_IDX}')

@task
def build(c):
    """Full pipeline: ingest -> (clean optional) -> chunk -> embed -> faiss"""
    if not RAW_DIR.exists():
        raise SystemExit("No data/raw directory found. Put PDFs in data/raw/")
    ingest(c)
    _assert_nonempty(
        "ingest", DOCS,
        "Source pages returned 415 or discovery found no links. Fix headers/methods in rag/ingest_lib/discover.py "
        "or drop a few PDFs into data/raw/ and rerun."
    )
    # optional clean step
    try:
        clean_extract(c)
    except subprocess.CalledProcessError:
        print("[warn] clean_extract missing; continuing with docs.jsonl")
    chunk(c)
    _assert_nonempty("chunk", CHUNKS, "docs.jsonl empty, so nothing to chunk. Fix ingestion first.")
    embed(c)
    faiss(c)

@task
def query(c, q, k=8, neighbors=2, per_doc=2):
    """CLI test against FAISS"""
    _run(f'{PY} -m scripts.query_faiss --q "{q}" --k {k} --neighbors {neighbors} --per-doc {per_doc}')

@task
def api(c, reload=True):
    """Start FastAPI only."""
    reload_flag = "--reload" if str(reload).lower() != "false" else ""
    _run(f'{PY} -m uvicorn app.main:app --host {API_HOST} --port {API_PORT} {reload_flag}')

@task
def ui(c):
    """Start Streamlit UI only."""
    env = {"COTTON_API_BASE": API_BASE}
    _run(f'streamlit run ui/streamlit_app.py --server.port {UI_PORT}', env=env)

@task
def dev(c, reload=True):
    """
    Ensure index exists, then run API + UI together.
    Works on Windows/macOS/Linux. Ctrl+C in Streamlit will shut down API too.
    """
    if not FAISS_IDX.exists():
        print("FAISS index missing → running full build...")
        build(c)

    reload_flag = "--reload" if str(reload).lower() != "false" else None
    env_api = os.environ.copy()
    env_api["PYTHONPATH"] = f'{Path(".").resolve()}{os.pathsep}{env_api.get("PYTHONPATH","")}'

    # Build uvicorn args and start API in background
    api_args = [PY, "-m", "uvicorn", "app.main:app", "--host", API_HOST, "--port", str(API_PORT)]
    if reload_flag:
        api_args.append(reload_flag)

    api_proc = subprocess.Popen(api_args, env=env_api)
    print(f"[api] pid={api_proc.pid} http://localhost:{API_PORT}/api")

    # crude health wait
    time.sleep(0.8)

    try:
        _run('streamlit run ui/streamlit_app.py --server.port {}'.format(UI_PORT),
             env={"COTTON_API_BASE": API_BASE})
    finally:
        if api_proc.poll() is None:
            try:
                api_proc.terminate()
                api_proc.wait(timeout=5)
            except Exception:
                try:
                    api_proc.kill()
                except Exception:
                    pass

@task(name="eval-extract")
def eval_extract(c):
    """Run extraction audit."""
    _run(f'{PY} -m app.extraction_eval')

@task
def clean(c):
    """Remove intermediate artifacts (safe)."""
    for p in [DOCS, CLEANED, CHUNKS]:
        if Path(p).exists():
            Path(p).unlink()
            print("deleted", p)

@task
def clobber(c):
    """Blow away embeddings + index (dangerous)."""
    for p in [EMB_EDS, EMB_IDS, FAISS_IDX]:
        if Path(p).exists():
            Path(p).unlink()
            print("deleted", p)

@task
def rebuild(c):
    """Full clean rebuild of the pipeline."""
    clobber(c)
    build(c)
    print("Rebuild complete.")
