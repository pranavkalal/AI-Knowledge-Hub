# API Reference

## Base URL
- Development: `http://localhost:8000`
- Production: `https://your-azure-app.azurecontainerapps.io`

---

## Endpoints

### POST `/api/ask`
**Purpose**: Ask a question and get an AI-generated answer with citations.

**Request Body**:
```json
{
  "question": "What are the best irrigation practices for cotton?",
  "k": 6,
  "temperature": 0.2,
  "max_output_tokens": 1000,
  "mode": "dense",
  "rerank": true,
  "persona": "grower",
  "filters": {
    "year_min": 2020,
    "year_max": 2024
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `question` | string | required | The user's question |
| `k` | int | 6 | Number of chunks to retrieve |
| `temperature` | float | 0.2 | LLM temperature (0-1) |
| `max_output_tokens` | int | 1000 | Max response length |
| `mode` | string | "dense" | Search mode |
| `rerank` | bool | true | Enable reranking |
| `persona` | string | "grower" | grower/researcher/extension |
| `filters` | object | {} | Metadata filters |

**Response** (streaming):
```json
{"type": "answer", "content": "Based on the research..."}
{"type": "sources", "citations": [{...}]}
{"type": "done", "usage": {"prompt_tokens": 1500, "completion_tokens": 300}}
```

---

### GET `/api/library`
**Purpose**: List available documents for browsing.

**Query Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Search term |
| `year` | int | Filter by year |
| `category` | string | Filter by category |
| `limit` | int | Max results (default 50) |
| `offset` | int | Pagination offset |

**Response**:
```json
{
  "items": [
    {
      "filename": "report_2024.pdf",
      "title": "Cotton Research Report 2024",
      "year": 2024,
      "category": "Research"
    }
  ],
  "total": 150
}
```

---

### GET `/api/pdf/{filename}`
**Purpose**: Serve PDF files for viewing.

**Response**: PDF file stream with CORS headers.

---

### GET `/api/health`
**Purpose**: Health check for monitoring.

**Response**:
```json
{
  "status": "ok",
  "database": "connected",
  "version": "0.1.0"
}
```

---

## Error Responses

```json
{
  "detail": "Question must be at least 5 characters"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Invalid request |
| 500 | Server error |
| 503 | Database unavailable |
