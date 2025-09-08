# app/chunk.py
import argparse, json
from rag.extract.pipeline import read_jsonl, write_jsonl
from rag.segment.chunker import chunk_record

def main():
    ap = argparse.ArgumentParser(description="Chunk cleaned JSONL")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--max_tokens", type=int, default=512)
    ap.add_argument("--overlap", type=int, default=64)
    args = ap.parse_args()

    out = []
    for rec in read_jsonl(args.inp):
        out.extend(chunk_record(rec, args.max_tokens, args.overlap))

    write_jsonl(args.outp, out)

if __name__ == "__main__":
    main()
