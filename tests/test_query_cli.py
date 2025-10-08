import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data/embeddings/vectors.faiss"
IDS = ROOT / "data/embeddings/ids.npy"
CHUNKS = ROOT / "data/staging/chunks.jsonl"


pytestmark = pytest.mark.skipif(
    any(not path.exists() for path in (INDEX, IDS, CHUNKS)),
    reason="FAISS index fixtures missing; run the embedding pipeline first.",
)


def test_query_cli_metadata_output():
    cmd = [
        sys.executable,
        "-m",
        "scripts.query_faiss",
        "--q",
        "water",
        "--k",
        "1",
        "--neighbors",
        "0",
        "--per-doc",
        "1",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT), env.get("PYTHONPATH", "") or ""]
    ).rstrip(os.pathsep)

    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    stdout = proc.stdout.strip()
    assert stdout, "CLI produced no output"
    first_line = next((line for line in stdout.splitlines() if line.strip()), "")
    assert first_line, f"No non-empty lines in CLI output:\n{stdout}"
    assert re.search(r"\b\d+\s+[+-]?\d+\.\d{3}", first_line), first_line
    assert "(" in first_line and ")" in first_line, first_line
    assert re.search(r"p[-\d]+", first_line), first_line
