# tasks.py
# Invoke is the source of truth.
# Primary:
#   invoke build   -> ingest -> (clean) -> chunk -> embed -> faiss  (fails fast if empty)
#   invoke dev     -> ensure index, then run API + UI together (cleans up API on exit)
# Helpers:
#   invoke api | ui | ingest | clean-extract | chunk | embed | faiss | query | eval-extract | clean | clobber | rebuild

from invoke import task
import os
import sys
import subprocess
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

from invoke import Collection

PY = sys.executable
API_HOST = os.environ.get("HOST", "0.0.0.0")
API_PORT = int(os.environ.get("PORT", "8000"))
UI_PORT = int(os.environ.get("UI_PORT", "8501"))
API_BASE = os.environ.get("COTTON_API_BASE", f"http://localhost:{API_PORT}/api")

RUNTIME_CFG = Path(os.environ.get("COTTON_RUNTIME", "configs/runtime/openai.yaml"))
OPENAI_RUNTIME_CFG = Path("configs/runtime/openai.yaml")
_RUNTIME_CACHE: dict | None = None


def _coerce_bool(value, default=None):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    try:
        return bool(int(value))
    except Exception:
        return default


def _load_runtime_cfg() -> dict:
    global _RUNTIME_CACHE
    if _RUNTIME_CACHE is not None:
        return _RUNTIME_CACHE
    if not RUNTIME_CFG.exists():
        _RUNTIME_CACHE = {}
        return _RUNTIME_CACHE
    try:
        with RUNTIME_CFG.open("r", encoding="utf-8") as fh:
            _RUNTIME_CACHE = yaml.safe_load(fh) or {}
    except Exception:
        _RUNTIME_CACHE = {}
    return _RUNTIME_CACHE


def _switch_runtime_cfg(path: Path) -> None:
    global RUNTIME_CFG, _RUNTIME_CACHE
    RUNTIME_CFG = Path(path)
    _RUNTIME_CACHE = None
    os.environ["COTTON_RUNTIME"] = str(RUNTIME_CFG)
    if not RUNTIME_CFG.exists():
        raise SystemExit(f"Runtime config not found: {RUNTIME_CFG}")


def _resolve_embed_settings() -> dict:
    cfg = _load_runtime_cfg().get("embedder", {}) or {}
    adapter = os.environ.get("EMB_ADAPTER") or cfg.get("adapter") or "bge_local"
    adapter_key = adapter.lower()
    default_model = "BAAI/bge-small-en-v1.5"
    if adapter_key.startswith("openai"):
        default_model = "text-embedding-3-small"
    model = os.environ.get("EMB_MODEL") or cfg.get("model") or default_model
    normalize = _coerce_bool(cfg.get("normalize"), True)
    batch_size = cfg.get("batch_size", cfg.get("batch", 64))
    try:
        batch_size = int(batch_size)
    except (TypeError, ValueError):
        batch_size = 64
    return {
        "adapter": adapter,
        "model": model,
        "batch_size": batch_size,
        "normalize": normalize,
    }


def _resolve_llm_model(default: str = "gpt-4o-mini") -> str:
    cfg = _load_runtime_cfg().get("llm", {}) or {}
    return os.environ.get("LLM_MODEL") or cfg.get("model") or default


LLM_MODEL = _resolve_llm_model()

# Paths
RAW_DIR    = Path("data/raw")
INGEST_CFG = Path("configs/ingestion/default.yaml")
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
    Default: configs/ingestion/default.yaml; override with --config path/to/file.yaml
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
def chunk(c, max_tokens=896, overlap=128, use_cleaned=True):
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
    settings = _resolve_embed_settings()
    adapter = settings["adapter"]
    model = settings["model"]
    batch = settings["batch_size"]
    normalize = settings["normalize"]
    print(f"[embed] adapter={adapter} model={model} batch={batch}")
    normalize_flag = ""
    if normalize is False:
        normalize_flag = " --no-normalize"
    elif normalize is True:
        normalize_flag = " --normalize"

    _run(
        f'{PY} -m scripts.build_embeddings '
        f'--chunks {CHUNKS} '
        f'--out_vecs {EMB_EDS} '
        f'--out_ids {EMB_IDS} '
        f'--model "{model}" '
        f'--adapter "{adapter}" '
        f'--batch {batch}'
        f'{normalize_flag}'
    )

@task
def faiss(c):
    """Build FAISS index (embeddings -> vectors.faiss)."""
    settings = _resolve_embed_settings()
    print(f"[faiss] using embeddings from adapter={settings['adapter']} model={settings['model']}")
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
def query(c, q, k=8, neighbors=2, per_doc=2, show_titles=True):
    """CLI test against FAISS (toggle metadata with --show-titles/--no-show-titles)."""
    title_flag = "--show-titles" if show_titles else "--no-show-titles"
    cmd = (
        f'{PY} -m scripts.query_faiss '
        f'--q "{q}" '
        f'--k {k} '
        f'--neighbors {neighbors} '
        f'--per-doc {per_doc} '
        f'{title_flag}'
    )
    print(f"[query] {cmd}")
    _run(cmd)

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


@task(name="dev2")
def dev_openai(c, reload=True):
    """Run dev task with OpenAI runtime preset."""
    _switch_runtime_cfg(OPENAI_RUNTIME_CFG)
    print(f"[dev2] Using runtime config {RUNTIME_CFG}")
    dev(c, reload=reload)

@task(name="eval-extract")
def eval_extract(c):
    """Run extraction audit."""
    _run(f'{PY} -m app.extraction_eval')

@task
def eval_retrieval(c, cfg="configs/runtime/openai.yaml", q="eval/gold/gold_ai_knowledge_hub.jsonl", k=6):
    """Evaluate retrieval metrics for native vs LangChain orchestrators."""
    _run(f'{PY} -m scripts.eval_retrieval --cfg {cfg} --q {q} --k {k}')

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


@task(name="regress-langchain")
def regress_langchain(c, before=None, after=None, queries="eval/gold/gold_ai_knowledge_hub.jsonl", k=None, out=None):
    """
    Compare retrieval hit-rate/latency between two runtime configs.
    Defaults: before=configs/runtime/openai.yaml, after=current COTTON_RUNTIME.
    """
    before_cfg = Path(before) if before else OPENAI_RUNTIME_CFG
    after_cfg = Path(after) if after else RUNTIME_CFG
    cmd = (
        f"{PY} -m scripts.retrieval.regress "
        f"--before {before_cfg} "
        f"--after {after_cfg} "
        f"--queries {queries}"
    )
    if k is not None:
        cmd += f" --k {k}"
    if out is not None:
        cmd += f" --out {out}"
    _run(cmd)

@task
def rebuild(c):
    """Full clean rebuild of the pipeline."""
    clobber(c)
    build(c)
    print("Rebuild complete.")


ns = Collection.from_module(sys.modules[__name__])
try:
    eval_task = ns["eval_retrieval"]
except KeyError:
    pass
else:
    eval_ns = Collection("eval")
    eval_ns.add_task(eval_task, name="retrieval")
    ns.add_collection(eval_ns)
