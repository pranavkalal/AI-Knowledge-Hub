import os
from sqlalchemy import create_engine, text

# Use the connection string from .env or default
conn_str = os.environ.get("POSTGRES_CONNECTION_STRING", "postgresql+psycopg2://postgres:password@localhost:5432/knowledge_hub")
engine = create_engine(conn_str)

with engine.connect() as conn:
    result = conn.execute(text("SELECT count(*) FROM chunks"))
    count = result.scalar()
    print(f"Total chunks in DB: {count}")
    
    if count > 0:
        sample = conn.execute(text("SELECT id, text FROM chunks LIMIT 1")).fetchone()
        print(f"Sample chunk: {sample}")
