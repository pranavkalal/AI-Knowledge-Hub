"""
Utility to sanity-check chunked JSONL files.

Usage:
    python scripts_sanity/chunk_stats.py --in data/staging/chunks.jsonl
"""
import argparse
import json
import statistics as st
from collections import defaultdict
import random

def load_chunks(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def summarize(chunks, max_cap: int | None = 512):
    bydoc = defaultdict(int)
    toks, chars = [], []
    cap_hits = 0
    runts = 0

    for c in chunks:
        doc = c.get("doc_id") or c["id"].split("_chunk")[0]
        bydoc[doc] += 1
        nt = c.get("n_tokens")
        if nt is not None:
            toks.append(nt)
            if max_cap and nt >= max_cap:
                cap_hits += 1
            if nt < 120:
                runts += 1
        ch = c.get("chars", len(c.get("text", "")))
        chars.append(ch)

    total_chunks = sum(bydoc.values())
    print("docs:", len(bydoc))
    print("total chunks:", total_chunks)
    print("avg chunks per doc:", round(st.mean(bydoc.values()), 1))

    if toks:
        toks_sorted = sorted(toks)
        p50 = toks_sorted[len(toks_sorted)//2]
        p90 = toks_sorted[int(0.9 * (len(toks_sorted)-1))]
        print("tokens per chunk:",
              "avg", round(st.mean(toks), 1),
              "min", min(toks),
              "p50", p50,
              "p90", p90,
              "max", max(toks))
        if max_cap:
            print(f"cap hits (=={max_cap}): {cap_hits} ({cap_hits*100/len(toks):.1f}%)")
            print(f"runts (<120): {runts} ({runts*100/len(toks):.1f}%)")

    print("chars per chunk:",
          "avg", round(st.mean(chars), 1),
          "min", min(chars),
          "max", max(chars))

def sample_chunk(path):
    with open(path, encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    sample = json.loads(random.choice(lines))
    print("\n--- Sample chunk ---")
    print("chunk_id:", sample["id"])
    print("doc_id:", sample.get("doc_id"))
    print("chunk_index:", sample.get("chunk_index"))
    print("n_tokens:", sample.get("n_tokens"))
    print("chars:", sample.get("chars"))
    print("--- text preview ---")
    print(sample.get("text","")[:500].replace("\n", " "))
    print("...")

def main():
    ap = argparse.ArgumentParser(description="Sanity check a chunked JSONL file.")
    ap.add_argument("--in", dest="inp", required=True, help="Path to chunks.jsonl")
    ap.add_argument("--cap", type=int, default=512, help="Token cap used during chunking")
    args = ap.parse_args()

    chunks = list(load_chunks(args.inp))
    summarize(chunks, max_cap=args.cap)
    sample_chunk(args.inp)

if __name__ == "__main__":
    main()
