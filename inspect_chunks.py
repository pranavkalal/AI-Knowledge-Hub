import os
import json
from sqlalchemy import create_engine, text

conn_str = os.environ.get("POSTGRES_CONNECTION_STRING", "postgresql+psycopg2://postgres:password@localhost:5432/knowledge_hub")
engine = create_engine(conn_str)

ids_to_check = [
    "AE2101_Final_Reportpdf23671_KBpdfView__Open_3",
    "NACRA_11158_Final_Report_1pdf22612_KBpdfView__Open_4",
    "AE2101_Final_Reportpdf23671_KBpdfView__Open_2",
    "NANB_11067_Travel_Reportpdf6974_KBpdfView__Open_5",
    "NANB_11067_Travel_Reportpdf6974_KBpdfView__Open_0"
]

with engine.connect() as conn:
    # Check if these IDs exist (exact match might fail if I guessed the ID format wrong, 
    # but user provided them so they should be close. The user provided IDs look like filenames + index?)
    # Wait, the user provided "AE2101_Final_Reportpdf23671_KBpdfView__Open_3". 
    # My ingest script generates IDs as `rec_id + "_" + idx`. 
    # Let's try to match by ID or partial ID.
    
    print(f"Checking {len(ids_to_check)} IDs...")
    for cid in ids_to_check:
        # Try exact match
        row = conn.execute(text("SELECT id, text, metadata FROM chunks WHERE id = :id"), {"id": cid}).fetchone()
        if row:
            print(f"\n--- Chunk: {cid} ---")
            print(f"Text (first 200 chars): {row.text[:200]}...")
            print(f"Metadata: {json.dumps(row.metadata, indent=2)}")
        else:
            print(f"\n--- Chunk: {cid} NOT FOUND ---")
            # Try partial match to see if ID format is slightly different
            partial = conn.execute(text("SELECT id FROM chunks WHERE id LIKE :id LIMIT 1"), {"id": f"%{cid.split('_')[0]}%"}).fetchone()
            if partial:
                print(f"Did you mean: {partial.id}?")
