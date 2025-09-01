# app/clean_extract.py
import argparse
from rag.extract.pipeline import read_jsonl, clean_records, write_jsonl

def main():
    ap = argparse.ArgumentParser(description="Clean per-document JSONL for RAG ingestion")
    ap.add_argument("--in", dest="inp", required=True, help="Path to raw docs.jsonl")
    ap.add_argument("--out", dest="out", required=True, help="Path to cleaned.jsonl")
    args = ap.parse_args()

    recs = read_jsonl(args.inp)
    cleaned = list(clean_records(recs))
    write_jsonl(args.out, cleaned)

if __name__ == "__main__":
    main()
