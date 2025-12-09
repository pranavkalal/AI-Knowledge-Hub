# app/ingest.py
import argparse
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

    # Skip scraping, iterate local files
    pdf_files = list(Path(download_dir).glob("*.pdf"))
    print(f"[ingest] found {len(pdf_files)} local PDFs in {download_dir}")
    
    links = []
    for p in pdf_files:
        # Create a dummy link object for compatibility
        links.append(type('obj', (object,), {
            "url": f"file://{p.absolute()}",
            "title": p.stem,
            "year": None,
            "source_page": None,
            "local_path": str(p)
        })())

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

    # Limit processed documents
    doc_limit = cfg.get("limit", 15)
    
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

        try:
            if parser_type == "azure":
                from rag.ingest_lib.parser_azure import AzureParser
                parser = AzureParser()
                # parse returns List[Dict] (pages)
                pages = parser.parse(pdf_path)
                
                # Construct a "parsed" object that fits our record structure
                # We need to aggregate text for the 'text' field (backward compat)
                full_text = "\n\n".join([p["text"] for p in pages])
                
                # Create a pseudo-object or dict to hold metadata
                parsed = type('obj', (object,), {
                    "text": full_text,
                    "meta": {
                        "source_url": link.url,
                        "source_page": link.source_page,
                        "title": link.title or "",
                        "year": link.year or "",
                        "page_count": len(pages)
                    },
                    "pages": pages # This will be used in the chunking loop
                })()
                # We need to pass 'pages' list through to the record
                # The 'parsed' object above is a bit hacky to match existing 'parsed.meta' access
                # Let's adjust the record creation below instead.
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
            
        # Rename file based on title if available
        title = parsed.meta.get("title")
        if title:
            # Sanitize title
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')
            if safe_title:
                new_filename = f"{safe_title}.pdf"
                new_path = Path(download_dir) / new_filename
                # Handle duplicates
                counter = 1
                while new_path.exists():
                    new_filename = f"{safe_title}_{counter}.pdf"
                    new_path = Path(download_dir) / new_filename
                    counter += 1
                
                try:
                    os.rename(pdf_path, new_path)
                    print(f"[rename] {Path(pdf_path).name} -> {new_filename}")
                    pdf_path = str(new_path)
                    rec_id = new_path.stem
                    parsed.meta["filename"] = new_filename
                except OSError as e:
                    print(f"[warn] failed to rename file: {e}")

        rec = {
            "id": rec_id,
            "title": parsed.meta.get("title", ""),
            "year": parsed.meta.get("year", ""),
            "source_url": parsed.meta.get("source_url", ""),
            "source_page": parsed.meta.get("source_page", ""),
            "filename": parsed.meta["filename"],
            "text": parsed.text,
            "meta": parsed.meta,
            "parsed": parsed.pages, # Pass the list of pages directly
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
        print("[store] pushing to Postgres with hybrid semantic chunking...")
        
        # Import the semantic chunker and bbox mapper
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from rag.ingest_lib.chunk_bbox_mapper import (
            find_matching_bboxes, 
            calculate_union_bbox,
            simplify_page_bboxes
        )
        
        # Hybrid chunking config: semantic-aware, respects sentence boundaries
        # Smaller chunks (600 tokens) work better for retrieval than 1000
        chunking_config = cfg.get("chunking", {})
        chunk_size = chunking_config.get("max_tokens", 600)
        chunk_overlap = chunking_config.get("overlap", 100)
        min_chunk_tokens = chunking_config.get("min_chunk_tokens", 50)
        
        # Use semantic-aware separators
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 4,  # Approximate chars (4 chars/token avg)
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
            # rec["parsed"] is a list of page dicts (from AzureParser.parse)
            pages = rec.get("parsed")
            if not pages or not isinstance(pages, list):
                print(f"[warn] no pages found for {rec['id']}, skipping chunking")
                continue

            for page in pages:
                page_num = page["page_number"]
                page_text = page["text"]
                page_bboxes = page.get("bboxes", [])
                
                # Skip empty pages
                if not page_text.strip():
                    continue
                
                # Split this page's text with semantic awareness
                chunks = splitter.split_text(page_text)
                
                for idx, text_chunk in enumerate(chunks):
                    # Skip tiny chunks (often just headers or noise)
                    if len(text_chunk.split()) < min_chunk_tokens // 4:
                        continue
                    
                    # ID format: doc_id + _p + page + _ + index
                    chunk_id = f"{rec['id']}_p{page_num}_{idx}"
                    
                    # Find matching bboxes for this specific chunk
                    matching_bboxes = find_matching_bboxes(text_chunk, page_bboxes)
                    
                    # Calculate union bbox for deep linking highlight
                    union_bbox = calculate_union_bbox(matching_bboxes)
                    
                    # Build metadata
                    meta = {
                        "title": rec["meta"].get("title"),
                        "year": rec["meta"].get("year"),
                        "source_url": rec["meta"].get("source_url"),
                        "filename": rec["meta"].get("filename"),
                        "page": page_num,
                        "page_width": page.get("width"),
                        "page_height": page.get("height"),
                        # Store only matching bboxes (much smaller than all page bboxes)
                        "bboxes": matching_bboxes,
                    }
                    
                    all_chunks.append({
                        "id": chunk_id,
                        "doc_id": rec["id"],
                        "chunk_index": idx,
                        "page_number": page_num,  # First-class field for DB
                        "text": text_chunk,
                        "metadata": meta
                    })
        
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
