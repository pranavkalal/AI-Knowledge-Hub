# SQLite vs PostgreSQL: Trade-off Analysis

## 1. Overview

| Feature | SQLite | PostgreSQL |
| :--- | :--- | :--- |
| **Type** | Embedded (Serverless) | Client-Server |
| **Setup** | Zero configuration (it's a file) | Requires installation, config, and a running service |
| **Concurrency** | Single-writer (WAL mode improves this) | Robust Multi-user / Multi-writer |
| **Vector Support** | `sqlite-vss` (Extension, experimental) | `pgvector` (Production-ready, industry standard) |

---

## 2. Resource Usage (Memory & Storage)

### SQLite
*   **Memory**: Extremely low footprint. It runs **inside your application process**. It only uses memory when you run a query.
    *   *Ideal for:* Local development, single-user apps, embedded devices, or low-memory environments (e.g., a cheap VPS with 512MB RAM).
*   **Storage**: A single file on disk (`cotton.db`).
    *   *Pros:* Easy to backup (just copy the file).
    *   *Cons:* Can grow large; vacuuming (reclaiming space) locks the database.

### PostgreSQL
*   **Memory**: Higher baseline. Requires a dedicated background process (daemon) that reserves memory for caching, connections, and buffers.
    *   *Minimum:* Needs ~50-100MB just to idle comfortably.
    *   *Recommended:* 1GB+ RAM for decent performance with vector search.
*   **Storage**: Data is spread across many files in a data directory.
    *   *Pros:* Efficient storage management, compression, and handling of terabytes of data.
    *   *Cons:* Backups require `pg_dump` tools; harder to move around than a single file.

---

## 3. Cost Efficiency

### SQLite (Winner for Low Cost)
*   **Infrastructure**: Free. No separate server needed. Runs on the same machine as your API.
*   **Maintenance**: Near zero. No user management, no network configuration, no ports to expose.

### PostgreSQL
*   **Infrastructure**: Often requires a separate managed instance (e.g., AWS RDS, Google Cloud SQL) which costs money ($15-50/month min), or a larger container/VPS to host it yourself.
*   **Maintenance**: Requires updates, security patching, connection pooling, and tuning.

---

## 4. Vector Search & RAG Specifics

### SQLite (`sqlite-vss`)
*   **Status**: Newer, less mature.
*   **Performance**: Good for <100k vectors.
*   **Limitation**: Vector search functionality is an external extension that can be tricky to compile/install on some platforms (e.g., specific Docker images).

### PostgreSQL (`pgvector`)
*   **Status**: Industry standard for open-source vector search.
*   **Performance**: Excellent. Supports IVFFlat and HNSW indexes for millions of vectors.
*   **Ecosystem**: Supported by almost every RAG framework (LangChain, LlamaIndex).

---

## 5. Recommendation

### **Scenario A: Local Dev / MVP / Single User** -> **Choose SQLite**
*   **Why**: You are currently running locally. You don't want to debug "Postgres connection refused" errors. You want to just run `python ingest.py` and have it work.
*   **Deep Linking**: SQLite handles the relational data (Document ID -> Page Number) perfectly fine.

### **Scenario B: Production / Multi-User / Enterprise** -> **Choose PostgreSQL**
*   **Why**: If you have multiple users querying at once, or if you reach >100k documents, SQLite will lock up. `pgvector` is much faster at scale.

### **My Advice for NOW:**
Start with **SQLite**.
1.  It requires **no Docker changes** (no new container).
2.  It requires **no credentials** management.
3.  We can migrate to Postgres later by simply changing the connection string (using an ORM like SQLAlchemy or SQLModel makes this trivial).
