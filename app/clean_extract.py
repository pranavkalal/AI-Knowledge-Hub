import argparse, json, os
from rag.extract.pipeline import run_clean, write_jsonl

def stream_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="outp", required=True)
    args = ap.parse_args()

    # group pages by doc_id
    by_doc = {}
    metas = {}
    for rec in stream_jsonl(args.inp):
        did = rec["doc_id"]
        by_doc.setdefault(did, []).append(rec.get("text",""))
        metas.setdefault(did, {
            "doc_id": did,
            "filename": rec.get("filename"),
            "source_url": rec.get("source_url"),
            "title": rec.get("title"),
            "year": rec.get("year"),
        })

    cleaned = []
    from rag.extract.pipeline import strip_headers_footers
    for did, pages in by_doc.items():
        meta = metas[did]
        cleaned.extend(run_clean(strip_headers_footers(pages), meta))

    write_jsonl(cleaned, args.outp)

if __name__ == "__main__":
    main()
