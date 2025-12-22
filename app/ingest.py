# app/ingest.py
"""
Production ingestion pipeline for CRDC Knowledge Hub.

Features:
- Azure Document Intelligence Read parser (production-ready)
- CSV metadata enrichment from scraped_reports.csv
- Semantic chunking with page-level tracking
- PostgreSQL vector storage
"""
import argparse
import csv
import os
import yaml
from pathlib import Path
from dataclasses import asdict
from dotenv import load_dotenv

load_dotenv()

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


def load_csv_metadata(csv_path: str) -> dict:
    """
    Load metadata from CSV file and index by filename.
    
    Returns:
        Dict mapping filename -> metadata dict
    """
    metadata_map = {}
    
    if not os.path.exists(csv_path):
        print(f"[warn] CSV metadata file not found: {csv_path}")
        return metadata_map
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row.get("filename", "").strip()
            if filename:
                metadata_map[filename] = {
                    "title": row.get("title", "").strip(),
                    "year": row.get("year", "").strip(),
                    "project_code": row.get("project_code", "").strip(),
                    "author": row.get("author", "").strip(),
                    "publisher": row.get("publisher", "").strip(),
                    "abstract": row.get("abstract", "").strip(),
                    "category": row.get("category", "").strip(),
                    "subject": row.get("subject", "").strip(),
                    "pdf_url": row.get("pdf_url", "").strip(),
                    "source_page": row.get("source_page", "").strip(),
                }
    
    print(f"[metadata] loaded {len(metadata_map)} records from CSV")
    return metadata_map


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/ingestion/default.yaml")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    download_dir = cfg["download_dir"]
    out_jsonl = cfg["output"]["jsonl"]
    out_csv = cfg["output"]["csv"]
    
    # Parser config
    parser_type = cfg.get("parser", "azure_read").lower()
    
    # Storage config
    store_type = cfg.get("storage", {}).get("type", "file").lower()
    
    # Load CSV metadata for enrichment
    metadata_cfg = cfg.get("metadata", {})
    csv_path = metadata_cfg.get("csv_path", "data/metadata/scraped_reports.csv")
    csv_metadata = load_csv_metadata(csv_path)

    skip_ids = load_skip_ids()
    if skip_ids:
        print(f"[skiplist] loaded {len(skip_ids)} IDs to ignore")

    # Iterate local PDF files
    pdf_files = list(Path(download_dir).glob("*.pdf"))
    print(f"[ingest] found {len(pdf_files)} local PDFs in {download_dir}")
    
    links = []
    for p in pdf_files:
        filename = p.name
        # Enrich from CSV metadata if available
        meta = csv_metadata.get(filename, {})
        
        links.append(type('obj', (object,), {
            "url": meta.get("pdf_url") or f"file://{p.absolute()}",
            "title": meta.get("title") or p.stem,
            "year": meta.get("year"),
            "author": meta.get("author"),
            "abstract": meta.get("abstract"),
            "category": meta.get("category"),
            "subject": meta.get("subject"),
            "project_code": meta.get("project_code"),
            "source_page": meta.get("source_page"),
            "local_path": str(p),
            "filename": filename,
        })())

    records = []
    seen_ids = set()
    seen_urls = set()
    
    # Initialize Postgres adapter if needed
    pg_store = None
    if store_type == "postgres":
        from app.adapters.vector_postgres import PostgresStoreAdapter
        from app.adapters.loader import load_embedder
        
        embed_cfg = cfg.get("embedder")
        if not embed_cfg:
            embed_cfg = {"provider": "openai", "model": "text-embedding-3-large"}
        
        embedder = load_embedder(embed_cfg, os.environ)
        pg_store = PostgresStoreAdapter(
            table_name=cfg.get("storage", {}).get("table_name", "chunks"),
            connection_string=os.environ.get("POSTGRES_CONNECTION_STRING"),
            embedder=embedder
        )

    # Limit processed documents (set high for production)
    doc_limit = cfg.get("limit", 100)
    
    for i, link in enumerate(links, 1):
        if len(records) >= doc_limit:
            print(f"[limit] reached limit of {doc_limit} documents")
            break
            
        print(f"[processing] ({i}/{len(links)}) {link.title}")
        
        if hasattr(link, "local_path") and os.path.exists(link.local_path):
            pdf_path = link.local_path
        else:
            if link.url in seen_urls:
                print(f"[skip] already processed url: {link.url}")
                continue
            pdf_path = download_pdf(link.url, download_dir, 20, "CRDC-Ingest/0.2", 3, 2)
            
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

        try:
            if parser_type == "azure_read":
                # New simplified Azure Read parser (no bbox)
                from rag.ingest_lib.parser_azure_read import AzureReadParser
                parser = AzureReadParser()
                pages = parser.parse(pdf_path)
                
                full_text = "\n\n".join([p["text"] for p in pages])
                
                parsed = type('obj', (object,), {
                    "text": full_text,
                    "meta": {
                        "source_url": link.url,
                        "source_page": link.source_page,
                        "title": link.title or "",
                        "year": link.year or "",
                        "author": getattr(link, "author", "") or "",
                        "abstract": getattr(link, "abstract", "") or "",
                        "category": getattr(link, "category", "") or "",
                        "subject": getattr(link, "subject", "") or "",
                        "project_code": getattr(link, "project_code", "") or "",
                        "page_count": len(pages),
                        "filename": link.filename,
                    },
                    "pages": pages
                })()
            elif parser_type == "azure":
                # Legacy Azure Layout parser (with bbox - deprecated)
                from rag.ingest_lib.parser_azure import AzureParser
                parser = AzureParser()
                pages = parser.parse(pdf_path)
                
                full_text = "\n\n".join([p["text"] for p in pages])
                
                parsed = type('obj', (object,), {
                    "text": full_text,
                    "meta": {
                        "source_url": link.url,
                        "source_page": link.source_page,
                        "title": link.title or "",
                        "year": link.year or "",
                        "page_count": len(pages),
                        "filename": link.filename,
                    },
                    "pages": pages
                })()
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
        except Exception as e:
            print(f"[error] failed to parse {pdf_path}: {e}")
            continue

        rec = {
            "id": rec_id,
            "title": parsed.meta.get("title", ""),
            "year": parsed.meta.get("year", ""),
            "source_url": parsed.meta.get("source_url", ""),
            "source_page": parsed.meta.get("source_page", ""),
            "filename": parsed.meta.get("filename", link.filename),
            "text": parsed.text,
            "meta": parsed.meta,
            "parsed": getattr(parsed, "pages", None),
        }
        records.append(rec)
        seen_ids.add(rec_id)
        seen_urls.add(link.url)

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
        print("[store] pushing to Postgres with semantic chunking...")
        
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        # Chunking config
        chunking_config = cfg.get("chunking", {})
        chunk_size = chunking_config.get("max_tokens", 600)
        chunk_overlap = chunking_config.get("overlap", 100)
        min_chunk_tokens = chunking_config.get("min_chunk_tokens", 50)
        
        # Semantic-aware separators
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 4,  # Approx chars (4 chars/token)
            chunk_overlap=chunk_overlap * 4,
            separators=[
                "\n\n\n",  # Section breaks
                "\n\n",    # Paragraph breaks
                "\n",      # Line breaks
                ". ",      # Sentence boundaries
                "! ",
                "? ",
                "; ",
                ", ",
                " ",
                ""
            ],
            keep_separator=True
        )
        
        all_chunks = []
        for rec in records:
            pages = rec.get("parsed")
            if not pages or not isinstance(pages, list):
                print(f"[warn] no pages found for {rec['id']}, skipping chunking")
                continue

            for page in pages:
                page_num = page["page_number"]
                page_text = page["text"]
                
                # Skip empty pages
                if not page_text.strip():
                    continue
                
                # Split this page's text
                chunks = splitter.split_text(page_text)
                
                chunk_counter = 0
                for text_chunk in chunks:
                    # Skip tiny chunks
                    if len(text_chunk.split()) < min_chunk_tokens // 4:
                        continue
                    
                    chunk_id = f"{rec['id']}_p{page_num}_{chunk_counter}"
                    
                    # Build metadata (no bbox - page-level tracking only)
                    meta = {
                        "title": rec["meta"].get("title"),
                        "year": rec["meta"].get("year"),
                        "author": rec["meta"].get("author"),
                        "abstract": rec["meta"].get("abstract"),
                        "category": rec["meta"].get("category"),
                        "subject": rec["meta"].get("subject"),
                        "project_code": rec["meta"].get("project_code"),
                        "source_url": rec["meta"].get("source_url"),
                        "filename": rec["meta"].get("filename"),
                        "page": page_num,
                        "page_width": page.get("width"),
                        "page_height": page.get("height"),
                    }
                    
                    all_chunks.append({
                        "id": chunk_id,
                        "doc_id": rec["id"],
                        "chunk_index": chunk_counter,
                        "page_number": page_num,
                        "text": text_chunk,
                        "metadata": meta
                    })
                    chunk_counter += 1
        
        print(f"[chunks] generated {len(all_chunks)} chunks from {len(records)} documents")
        
        # Batch embed and store
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i+batch_size]
            texts = [c["text"] for c in batch]
            embeddings = pg_store.embedder.embed_texts(texts)
            pg_store.add_documents(batch, embeddings)
            print(f"   pushed batch {i//batch_size + 1}: {len(batch)} chunks")

    print("[done] ingestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
