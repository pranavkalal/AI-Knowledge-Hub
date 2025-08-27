# app/ingest.py
import argparse, yaml
from pathlib import Path

from rag.ingest_lib.discover import collect_pdf_links
from rag.ingest_lib.download import download_pdf
from rag.ingest_lib.parse_pdf import parse_pdf
from rag.ingest_lib.store import write_jsonl, write_csv


def load_cfg(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_skip_ids():
    skip_file = Path("eval/skip_ids.txt")
    if not skip_file.exists():
        return set()
    return {
        ln.strip()
        for ln in skip_file.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/ingestion.yaml")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    years = cfg.get("years")
    seed_urls = cfg["seed_urls"]
    include_patterns = cfg.get("include_patterns", [r"\.pdf$"])
    exclude_patterns = cfg.get("exclude_patterns", [])
    timeout = int(cfg.get("timeout_secs", 20))
    ua = cfg.get("user_agent", "CRDC-Ingest/0.1")
    download_dir = cfg["download_dir"]
    out_jsonl = cfg["output"]["jsonl"]
    out_csv = cfg["output"]["csv"]
    retry = cfg.get("retry", {})
    attempts = int(retry.get("attempts", 3))
    backoff = int(retry.get("backoff_secs", 2))

    skip_ids = load_skip_ids()
    if skip_ids:
        print(f"[skiplist] loaded {len(skip_ids)} IDs to ignore")

    print("[discover] scanning seed URLs...")
    links = collect_pdf_links(seed_urls, include_patterns, exclude_patterns, years, timeout, ua)

    print(f"[discover] found {len(links)} candidate PDFs")

    records = []
    for i, link in enumerate(links, 1):
        print(f"[download] ({i}/{len(links)}) {link.url}")
        pdf_path = download_pdf(link.url, download_dir, timeout, ua, attempts, backoff)
        if not pdf_path:
            print(f"[skip] not a pdf or failed: {link.url}")
            continue
        rec_id = Path(pdf_path).stem
        if rec_id in skip_ids:
            print(f"[skip] {rec_id} is in skip_ids.txt")
            continue

        parsed = parse_pdf(
            pdf_path,
            extra_meta={
                "source_url": link.url,
                "source_page": link.source_page,
                "title": link.title or "",
                "year": link.year or "",
            },
        )
        rec = {
            "id": rec_id,
            "title": parsed.meta.get("title", ""),
            "year": parsed.meta.get("year", ""),
            "source_url": parsed.meta.get("source_url", ""),
            "source_page": parsed.meta.get("source_page", ""),
            "filename": parsed.meta["filename"],
            "text": parsed.text,
            "meta": parsed.meta,
        }
        records.append(rec)

    print(f"[store] writing {len(records)} records")
    write_jsonl(records, out_jsonl)
    write_csv(
        [
            {
                "id": r["id"],
                "title": r["title"],
                "year": r["year"],
                "source_url": r["source_url"],
                "filename": r["filename"],
                "chars": len(r["text"]),
            }
            for r in records
        ],
        out_csv,
    )
    print("[done] ingestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
