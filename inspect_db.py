import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import json

load_dotenv()

connection_string = os.environ.get("POSTGRES_CONNECTION_STRING")
if not connection_string:
    print("Error: POSTGRES_CONNECTION_STRING not found in .env")
    exit(1)

engine = create_engine(connection_string)

sql = """
SELECT id, metadata->>'page' as page, metadata->>'bboxes' as bboxes 
FROM chunks 
WHERE id LIKE '%Community%' OR id LIKE '%DAQ%'
LIMIT 5;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql))
    rows = result.fetchall()
    
    print(f"Found {len(rows)} rows:")
    for row in rows:
        # row is a tuple-like object, access by index or name
        # In SQLAlchemy 1.4/2.0 text() result, we can access by name
        id_val = row[0]
        page_val = row[1]
        bboxes_val = row[2]
        
        # Truncate bboxes for display if it's a long string
        if bboxes_val and len(str(bboxes_val)) > 100:
             bboxes_display = str(bboxes_val)[:100] + "..."
        else:
             bboxes_display = str(bboxes_val)
             
        print(f"ID: {id_val}")
        print(f"  Page: {page_val}")
        print(f"  BBoxes: {bboxes_display}")
        print("-" * 40)
