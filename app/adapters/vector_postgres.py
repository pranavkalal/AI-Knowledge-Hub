# app/adapters/vector_postgres.py
import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class PostgresStoreAdapter:
    def __init__(self, table_name: str = "chunks", connection_string: Optional[str] = None, embedder: Any = None):
        self.table_name = table_name
        self.connection_string = connection_string or os.environ.get("POSTGRES_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError("Missing POSTGRES_CONNECTION_STRING environment variable")
        
        self.embedder = embedder
        self.engine = create_engine(self.connection_string)
        self.Session = sessionmaker(bind=self.engine)
        
        # Ensure pgvector extension and table exist
        self._init_db()

    def _init_db(self):
        with self.engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT,
                    chunk_index INTEGER,
                    text TEXT,
                    embedding vector(1536),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # Create HNSW index for faster search
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx 
                ON {self.table_name} USING hnsw (embedding vector_cosine_ops)
            """))
            conn.commit()

    def add_documents(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        Add chunks and their embeddings to the database.
        """
        if not chunks:
            return
            
        session = self.Session()
        try:
            for chunk, emb in zip(chunks, embeddings):
                # Prepare metadata
                meta = chunk.get("metadata", {}).copy()
                # Ensure core fields are top-level
                doc_id = chunk.get("doc_id") or meta.get("doc_id")
                chunk_index = chunk.get("chunk_index") or meta.get("chunk_index") or 0
                text_content = chunk.get("text") or meta.get("text") or ""
                
                # Insert or update
                stmt = text(f"""
                    INSERT INTO {self.table_name} (id, doc_id, chunk_index, text, embedding, metadata)
                    VALUES (:id, :doc_id, :chunk_index, :text, :embedding, :metadata)
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata
                """)
                
                session.execute(stmt, {
                    "id": chunk["id"],
                    "doc_id": doc_id,
                    "chunk_index": chunk_index,
                    "text": text_content,
                    "embedding": str(emb),  # pgvector expects string representation or list
                    "metadata": json.dumps(meta)
                })
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add documents: {e}")
            raise
        finally:
            session.close()

    def search_raw(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.
        """
        if not self.embedder:
            raise RuntimeError("PostgresStoreAdapter initialized without embedder; cannot use search_raw(text).")
            
        # Embed the query
        # Assuming embedder has embed_query(text) -> list[float]
        if hasattr(self.embedder, "embed_query"):
            embedding = self.embedder.embed_query(query_text)
        elif hasattr(self.embedder, "embed"):
            embedding = self.embedder.embed(query_text)
        else:
             raise RuntimeError(f"Embedder {type(self.embedder)} does not have embed_query or embed method")

        return self.search_with_vector(embedding, top_k)

    def search_with_vector(self, embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        session = self.Session()
        try:
            # Cosine distance operator is <=>
            # We want similarity, so we order by distance ASC
            stmt = text(f"""
                SELECT id, doc_id, chunk_index, text, metadata, 
                       1 - (embedding <=> :embedding) as score
                FROM {self.table_name}
                ORDER BY embedding <=> :embedding
                LIMIT :top_k
            """)
            
            result = session.execute(stmt, {
                "embedding": str(embedding),
                "top_k": top_k
            })
            
            hits = []
            for row in result:
                hit = {
                    "id": row.id,
                    "doc_id": row.doc_id,
                    "chunk_index": row.chunk_index,
                    "text": row.text,
                    "score": float(row.score),
                    "metadata": row.metadata
                }
                hits.append(hit)
            return hits
        finally:
            session.close()
