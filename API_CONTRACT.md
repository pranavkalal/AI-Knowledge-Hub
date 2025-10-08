# API Contract

## `/api/health`

**GET** `/api/health`  

### 200 Response

```json
{
  "status": "ok"
}
```

### Query Params

- `q` (string, required) — search text  
- `k` (int, optional, default = 8) — number of results to return  
- `neighbors` (int, optional, default = 2) — how many chunks around the hit to stitch  
- `cursor` (string, optional) — pagination token from last response  
- `year` (int or range, optional) — filter by year (e.g. `2019` or `2015-2020`)  
- `doc_id` (string, optional) — filter to one document  
- `sort` (string, optional, default = relevance) — `relevance` or `recency`

---

### 200 Response 2

```json
{
  "query": "string",
  "params": { "k": 8, "neighbors": 2, "sort": "relevance" },
  "count": 8,
  "total_available": 237,
  "cursor_next": "opaque-cursor-or-null",
  "took_ms": 12,
  "results": [
    {
      "doc_id": "string",
      "chunk_id": 123,
      "score": 0.72,
      "title": "string",
      "year": 2019,
      "preview": "stitched ~900 chars",
      "neighbor_window": [121, 125],
      "source_url": "https://…",
      "filename": "report.pdf"
    }
  ]
}
```

ErrorResponse

``` json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "k must be between 1 and 50"
  }
}
```

Notes
Only q is required.
Use cursor_next to get the next page.
Ignore highlight_spans for now (future).
Default sort is relevance.
