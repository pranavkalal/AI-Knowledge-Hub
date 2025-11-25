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
            
            # Create table with search_vector for hybrid search
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT,
                    chunk_index INTEGER,
                    text TEXT,
                    embedding vector(1536),
                    metadata JSONB,
                    search_vector tsvector,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create HNSW index for faster vector search
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx 
                ON {self.table_name} USING hnsw (embedding vector_cosine_ops)
            """))
            
            # Create GIN index for fast keyword search
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_search_vector_idx 
                ON {self.table_name} USING gin (search_vector)
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
                # We use to_tsvector('english', :text) to populate the search vector
                stmt = text(f"""
                    INSERT INTO {self.table_name} (id, doc_id, chunk_index, text, embedding, metadata, search_vector)
                    VALUES (:id, :doc_id, :chunk_index, :text, :embedding, :metadata, to_tsvector('english', :text))
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        search_vector = to_tsvector('english', EXCLUDED.text)
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

    def search_raw(self, query_text: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using hybrid search (vector + keyword) and metadata filtering.
        """
        if not self.embedder:
            raise RuntimeError("PostgresStoreAdapter initialized without embedder; cannot use search_raw(text).")
            
        # Embed the query
        if hasattr(self.embedder, "embed_query"):
            embedding = self.embedder.embed_query(query_text)
        elif hasattr(self.embedder, "embed"):
            embedding = self.embedder.embed(query_text)
        else:
             raise RuntimeError(f"Embedder {type(self.embedder)} does not have embed_query or embed method")

        return self.search_hybrid(query_text, embedding, top_k, filters)

    def search_hybrid(self, query_text: str, embedding: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        session = self.Session()
        try:
            # Build WHERE clause for filters
            where_clauses = []
            params = {
                "embedding": str(embedding),
                "query_text": query_text,
                "top_k": top_k
            }
            
            if filters:
                if "doc_id" in filters:
                    where_clauses.append("doc_id = :filter_doc_id")
                    params["filter_doc_id"] = filters["doc_id"]
                
                if "year_min" in filters:
                    where_clauses.append("(metadata->>'year')::int >= :year_min")
                    params["year_min"] = filters["year_min"]
                    
                if "year_max" in filters:
                    where_clauses.append("(metadata->>'year')::int <= :year_max")
                    params["year_max"] = filters["year_max"]
                    
                if "contains" in filters:
                    # 'contains' is usually a list of strings for exact match in metadata or text
                    # For simplicity, let's assume it filters by filename or title if present
                    # Or we can use it as a keyword filter on the text
                    pass 

            where_sql = " AND ".join(where_clauses)
            if where_sql:
                where_sql = "WHERE " + where_sql
            else:
                where_sql = ""

            # Hybrid Search Query
            # Combines Vector Similarity (1 - cosine distance) and Keyword Rank (ts_rank)
            # We use a simple weighted sum: 0.7 * vector_score + 0.3 * keyword_score
            # Note: vector score is [0, 1], ts_rank is unbounded but usually small. We normalize ts_rank roughly.
            stmt = text(f"""
                WITH vector_scores AS (
                    SELECT id, doc_id, chunk_index, text, metadata,
                           1 - (embedding <=> :embedding) as v_score
                    FROM {self.table_name}
                    {where_sql}
                    ORDER BY embedding <=> :embedding
                    LIMIT :top_k * 2  -- Overfetch for re-ranking
                ),
                keyword_scores AS (
                    SELECT id, 
                           ts_rank_cd(search_vector, plainto_tsquery('english', :query_text)) as k_score
                    FROM {self.table_name}
                    WHERE id IN (SELECT id FROM vector_scores)
                )
                SELECT v.id, v.doc_id, v.chunk_index, v.text, v.metadata,
                       v.v_score, COALESCE(k.k_score, 0) as k_score,
                       (v.v_score * 0.8 + LEAST(COALESCE(k.k_score, 0), 1.0) * 0.2) as final_score
                FROM vector_scores v
                LEFT JOIN keyword_scores k ON v.id = k.id
                ORDER BY final_score DESC
                LIMIT :top_k
            """)
            
            result = session.execute(stmt, params)
            
            hits = []
            for row in result:
                hit = {
                    "id": row.id,
                    "doc_id": row.doc_id,
                    "chunk_index": row.chunk_index,
                    "text": row.text,
                    "score": float(row.final_score),
                    "vector_score": float(row.v_score),
                    "keyword_score": float(row.k_score),
                    "metadata": row.metadata
                }
                hits.append(hit)
            return hits
        finally:
            session.close()
