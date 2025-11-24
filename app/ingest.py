# app/ingest.py
import argparse
import yaml
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
    ap.add_argument("--config", default="configs/ingestion/default.yaml")
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
    
    # Parser config
    parser_type = cfg.get("parser", "docling").lower()
    
    # Storage config
    store_type = cfg.get("storage", {}).get("type", "file").lower()

    skip_ids = load_skip_ids()
    if skip_ids:
        print(f"[skiplist] loaded {len(skip_ids)} IDs to ignore")

    print("[discover] scanning seed URLs...")
    links = collect_pdf_links(seed_urls, include_patterns, exclude_patterns, years, timeout, ua)

    print(f"[discover] found {len(links)} candidate PDFs")

    records = []
    seen_ids = set()
    seen_urls = set()
    
    # Initialize Postgres adapter if needed
    pg_store = None
    if store_type == "postgres":
        from app.adapters.vector_postgres import PostgresStoreAdapter
        # We need an embedder for ingestion? 
        # Actually, usually we chunk and embed.
        # Let's assume we just store text chunks for now, or we need to load embedder here too.
        # For simplicity, let's load the embedder defined in runtime config or just use OpenAI directly if configured.
        # But wait, `ingest.py` usually just creates JSONL. 
        # If we want to write to Postgres, we should probably do it here.
        
        # Let's load the embedder using the factory helper
        from app.adapters.loader import load_embedder
        # We might need a separate config for ingestion embedder or reuse runtime config
        # For now, let's assume we use the same embedder config as runtime if available, 
        # or just default to OpenAI if we are pushing to Postgres.
        
        # To keep it simple, let's require an embedder config in ingestion.yaml if using postgres
        embed_cfg = cfg.get("embedder")
        if not embed_cfg:
             # Fallback to env vars or default
             embed_cfg = {"provider": "openai", "model": "text-embedding-3-small"}
        
        embedder = load_embedder(embed_cfg, os.environ)
        pg_store = PostgresStoreAdapter(
            table_name=cfg.get("storage", {}).get("table_name", "chunks"),
            connection_string=os.environ.get("POSTGRES_CONNECTION_STRING"),
            embedder=embedder
        )

    for i, link in enumerate(links, 1):
        print(f"[download] ({i}/{len(links)}) {link.url}")
        if link.url in seen_urls:
            print(f"[skip] already processed url: {link.url}")
            continue
        pdf_path = download_pdf(link.url, download_dir, timeout, ua, attempts, backoff)
        if not pdf_path:
            print(f"[skip] not a pdf or failed: {link.url}")
            continue
        rec_id = Path(pdf_path).stem
        if rec_id in skip_ids:
            print(f"[skip] {rec_id} is in skip_ids.txt")
            continue
        if rec_id in seen_ids:
            print(f"[skip] duplicate document id: {rec_id}")
            continue

        if parser_type == "azure":
            from rag.ingest_lib.parser_azure import parse_pdf as parse_pdf_azure
            parsed = parse_pdf_azure(
                pdf_path,
                extra_meta={
                    "source_url": link.url,
                    "source_page": link.source_page,
                    "title": link.title or "",
                    "year": link.year or "",
                },
            )
        else:
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
        seen_ids.add(rec_id)
        seen_urls.add(link.url)
        
        # If Postgres, chunk and store immediately
        if pg_store:
            # We need a chunker. Let's use the semantic chunker or a simple one.
            # For now, let's use a simple recursive character splitter from langchain if available,
            # or just import the one from `rag/ingest/chunkers` if it exists.
            # Let's check `rag/ingest/chunkers` content first.
            # Assuming we have a chunker available.
            pass # TODO: Implement chunking and pushing to Postgres

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
    
    if pg_store:
        print("[store] pushing to Postgres...")
        # Here we would iterate records, chunk them, embed them, and push to PG.
        # Since I didn't implement the chunking loop above, I'll do it here.
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        all_chunks = []
        all_embeddings = []
        
        for rec in records:
            chunks = splitter.split_text(rec["text"])
            for idx, text_chunk in enumerate(chunks):
                chunk_id = f"{rec['id']}_{idx}"
                all_chunks.append({
                    "id": chunk_id,
                    "doc_id": rec["id"],
                    "chunk_index": idx,
                    "text": text_chunk,
                    "metadata": rec["meta"]
                })
        
        # Batch embed
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i+batch_size]
            texts = [c["text"] for c in batch]
            embeddings = pg_store.embedder.embed_texts(texts)
            pg_store.add_documents(batch, embeddings)
            print(f"   pushed {len(batch)} chunks")

    print("[done] ingestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
