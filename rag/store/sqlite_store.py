"""
SQLite database utilities for AI Knowledge Hub.
Manages documents and chunks with rich metadata support.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from datetime import datetime


DEFAULT_DB_PATH = Path("data/knowledge_hub.db")


@contextmanager
def get_db_connection(db_path: Path = DEFAULT_DB_PATH):
    """Context manager for database connections."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DEFAULT_DB_PATH):
    """Initialize the database with schema."""
    schema_path = Path(__file__).parent / "db_schema.sql"
    
    with get_db_connection(db_path) as conn:
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
    
    print(f"✅ Database initialized: {db_path}")


def insert_document(
    doc_id: str,
    title: str,
    source_url: str,
    **kwargs
) -> None:
    """
    Insert a document into the database.
    
    Args:
        doc_id: Unique document identifier (uuid from Excel)
        title: Document title
        source_url: PDF download URL
        **kwargs: Additional fields (year, authors, categories, etc.)
    """
    with get_db_connection() as conn:
        # Extract known fields
        fields = {
            'id': doc_id,
            'title': title,
            'source_url': source_url,
            'filename': kwargs.get('filename', f"{doc_id}.pdf"),
            'year': kwargs.get('year'),
            'authors': kwargs.get('authors'),
            'categories': kwargs.get('categories'),
            'description': kwargs.get('description'),
            'publisher': kwargs.get('publisher'),
            'document_type': kwargs.get('document_type'),
            'uid': kwargs.get('uid'),
            'alternative_title': kwargs.get('alternative_title'),
        }
        
        # Pack remaining fields into metadata JSON
        metadata_fields = {
            k: v for k, v in kwargs.items() 
            if k not in fields and v is not None
        }
        if metadata_fields:
            fields['metadata'] = json.dumps(metadata_fields)
        
        # Build INSERT statement
        columns = [k for k, v in fields.items() if v is not None]
        placeholders = ', '.join(['?' for _ in columns])
        values = [fields[k] for k in columns]
        
        sql = f"""
            INSERT OR REPLACE INTO documents ({', '.join(columns)})
            VALUES ({placeholders})
        """
        
        conn.execute(sql, values)


def get_document(doc_id: str) -> Optional[Dict]:
    """Get a document by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM documents WHERE id = ?",
            (doc_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_pending_documents() -> List[Dict]:
    """Get all documents with status='pending'."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM documents WHERE status = 'pending'"
        )
        return [dict(row) for row in cursor.fetchall()]


def update_document_status(doc_id: str, status: str) -> None:
    """Update document status."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE documents SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), doc_id)
        )


def insert_chunks(chunks: List[Dict]) -> None:
    """
    Batch insert chunks into the database.
    
    Args:
        chunks: List of chunk dictionaries with keys:
            - id, doc_id, chunk_index, text, page, bbox
    """
    with get_db_connection() as conn:
        for chunk in chunks:
            # Serialize bbox if it's a list/dict
            bbox = chunk.get('bbox')
            if isinstance(bbox, (list, dict)):
                bbox = json.dumps(bbox)
            
            conn.execute("""
                INSERT OR REPLACE INTO chunks 
                (id, doc_id, chunk_index, text, page, bbox)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                chunk['id'],
                chunk['doc_id'],
                chunk['chunk_index'],
                chunk['text'],
                chunk.get('page'),
                bbox
            ))


def get_chunks_by_doc_id(doc_id: str) -> List[Dict]:
    """Get all chunks for a document."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index",
            (doc_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_chunk_by_id(chunk_id: str) -> Optional[Dict]:
    """Get a single chunk by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM chunks WHERE id = ?",
            (chunk_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_chunks() -> List[Dict]:
    """Get all chunks (for embedding generation)."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM chunks ORDER BY doc_id, chunk_index")
        return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
