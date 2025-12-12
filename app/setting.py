"""
app/settings.py

Central configuration for the Cotton RAG API.
- Defines project-wide paths and constants (data directories, embeddings, FAISS index).
- Uses Pydantic's BaseSettings so values can be overridden via environment variables or a `.env` file.
- Import `from app.settings import settings` anywhere in the project to access shared config.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """
    Settings model holding configuration for data locations, model choice, and retrieval defaults.
    Values can be customized by setting environment variables or editing `.env`.
    """

    # ---------- Data directories ----------
    data_dir: Path = Path("data")                    # Root data folder
    staging_dir: Path = Path("data/staging")         # Cleaned/chunked JSONL files
    embeddings_dir: Path = Path("data/embeddings")   # Stored numpy embeddings + FAISS index

    # ---------- Embedding + index paths ----------
    faiss_index: Path = Path("data/embeddings/vectors.faiss")   # FAISS vector index file
    ids_path: Path = Path("data/embeddings/ids.npy")            # Array of chunk/document IDs
    embs_path: Path = Path("data/embeddings/embeddings.npy")    # Array of dense embeddings

    # ---------- Embedding model & retrieval defaults ----------
    embed_model: str = "text-embedding-3-small"  # Model used for embeddings
    llm_model: str = "gpt-4o"                    # Model used for generation
    rerank_model: str = "text-embedding-3-large" # Model used for reranking
    
    embedding_adapter: str = "openai"            # Adapter: 'openai' or 'bge'
    rerank_adapter: str = "openai"               # Adapter: 'openai' or 'bge'

    per_doc: int = 2                             # Diversification: max chunks per doc
    neighbors: int = 2                           # Extra neighbor chunks to stitch for context

    class Config:
        # Allows values to be overridden via a `.env` file or env vars
        env_file = ".env"
        extra = "ignore"


# Singleton settings instance used across the app
settings = Settings()
