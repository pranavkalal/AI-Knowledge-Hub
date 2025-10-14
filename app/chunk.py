# app/chunk.py
import argparse

from rag.extract.pipeline import read_jsonl, write_jsonl
from rag.segment.chunker import chunk_stream, get_tokenizer

def main():
    ap = argparse.ArgumentParser(description="Chunk cleaned JSONL")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    ap.add_argument("--max_tokens", type=int, default=896)
    ap.add_argument("--overlap", type=int, default=128)
    ap.add_argument("--model", default=None, help="tokenizer model (defaults to EMB_MODEL or BGE-small).")
    args = ap.parse_args()

    tokenizer = get_tokenizer(args.model)
    records = read_jsonl(args.inp)
    chunks_iter = chunk_stream(
        records,
        max_tokens=args.max_tokens,
        overlap=args.overlap,
        tokenizer=tokenizer,
    )

    count = write_jsonl(args.outp, chunks_iter)
    if count is not None:
        print(f"[chunk] Wrote {count} chunks to {args.outp} (max_tokens={args.max_tokens}, overlap={args.overlap})")
    else:
        print(f"[chunk] Chunking complete → {args.outp}")

if __name__ == "__main__":
    main()
