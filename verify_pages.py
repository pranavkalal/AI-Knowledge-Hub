import os
import json
from sqlalchemy import create_engine, text

conn_str = os.environ.get("POSTGRES_CONNECTION_STRING", "postgresql+psycopg2://postgres:password@localhost:5432/knowledge_hub")
engine = create_engine(conn_str)

with engine.connect() as conn:
    print("Checking for page metadata...")
    # Select a few chunks and check their metadata
    rows = conn.execute(text("SELECT id, metadata FROM chunks")).fetchall()
    chunks_with_page = 0
    i = 0
    for row in rows:
        meta = row.metadata
        if "page" in meta:
            chunks_with_page += 1
            if i < 5:
                print(f"ID: {row.id}")
                print(f"  Page: {meta['page']}")
                print(f"  Has bboxes: {'bboxes' in meta}")
                print(f"  Metadata keys: {list(meta.keys())}")
                i += 1
        
    # Count chunks with page info
    count = conn.execute(text("SELECT count(*) FROM chunks WHERE metadata->>'page' IS NOT NULL")).scalar()
    total = conn.execute(text("SELECT count(*) FROM chunks")).scalar()
    print(f"\nChunks with page info: {count}/{total}")
