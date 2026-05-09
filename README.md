# Auto-updated LLM Comparison Dashboard for GraphRAG Model Selection

This prototype keeps a local SQLite database of LLM model metadata and classifies each model by likely usefulness in a GraphRAG workflow. It focuses on practical model-selection questions: what can run locally, what is API-only, where a model fits in the GraphRAG pipeline, and which models are worth testing now.

It is intentionally not a notification system. There is no email, Slack, auth, cloud deployment, Kubernetes, or production cron setup.

## How It Relates To GraphRAG

The update pipeline collects model metadata from structured sources, normalizes records into one schema, deduplicates overlapping models, and applies rule-based GraphRAG classification. Roles include entity extraction, relationship extraction, graph cleaning, graph validation, retrieval, reranking, final answer generation, answer verification, coding tooling, query routing, and multimodal document understanding.

The first classifier is rule-based so the prototype works without an LLM API key.

## Scoring

Scores are 1 to 5, where 5 is best.

- GraphRAG score: based on detected GraphRAG roles, long context, local/API availability, reasoning/coding/retrieval tags, and any cost penalty.
- Hardware score: `laptop` = 5, `desktop_gpu` = 4, `workstation_gpu` = 3, `api_only` = 3, `server_gpu` = 2, `unknown` = 1.
- Cost score: local models = 5; API models use estimated USD per 1M input/output tokens. Cheaper is higher, expensive is lower.

The model detail page shows concise notes explaining why each score was assigned, including input/output cost per 1M tokens when known.

## Sources

- Hugging Face Hub through `huggingface_hub` or the public Hub API fallback.
- OpenRouter via `https://openrouter.ai/api/v1/models`.
- LiteLLM public pricing/context catalog from GitHub.
- OpenAI models API when `OPENAI_API_KEY` is configured.
- Anthropic models API when `ANTHROPIC_API_KEY` is configured.
- Google Gemini models API when `GEMINI_API_KEY` or `GOOGLE_API_KEY` is configured.
- Mistral models API when `MISTRAL_API_KEY` is configured.
- Ollama local runtime via `GET http://127.0.0.1:11434/api/tags` when Ollama is running.
- Manual seed JSON at `data/manual_models.seed.json` is optional and mainly for testing/manual trusted additions.

Environment variables are optional:

```powershell
$env:OPENROUTER_API_KEY="..."
$env:HF_TOKEN="..."
$env:OPENAI_API_KEY="..."
$env:ANTHROPIC_API_KEY="..."
$env:GEMINI_API_KEY="..."
$env:MISTRAL_API_KEY="..."
```

The app still runs without keys using public endpoints where available. Keyed provider adapters return no rows until their key is configured.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

To populate optional starter/manual data:

```powershell
python -m app.cli import-seed
```

Or use the dashboard buttons:

- `Import optional seed`
- `Run update now`
- `Reclassify`

## Admin Commands

Run all adapters:

```powershell
python -m app.cli update
```

Import a seed file:

```powershell
python -m app.cli import-seed --path data/manual_models.seed.json
```

Reclassify stored models:

```powershell
python -m app.cli reclassify
```

Export data:

```powershell
python -m app.cli export --format csv --out data/llm_models.csv
python -m app.cli export --format json --out data/llm_models.json
```

The web app also exposes:

- `POST /admin/update`
- `POST /admin/import-seed`
- `POST /admin/reclassify`
- `GET /export.csv`
- `GET /export.json`

## Adding Manual Models

Add records to `data/manual_models.seed.json`. The normalizer accepts partial records, but richer metadata improves classification:

```json
{
  "model_name": "provider/model-name",
  "provider": "provider",
  "source": "manual_seed",
  "source_url": "https://official-source.example/model",
  "model_type": "open_weight",
  "parameter_size": "8B",
  "context_window": 128000,
  "modalities": ["text"],
  "api_available": false,
  "local_available": true,
  "hardware_fit": "laptop",
  "estimated_cost_input": 0.2,
  "estimated_cost_output": 0.6,
  "tags": ["reasoning", "coding"],
  "notes": "Why this model is worth tracking."
}
```

## Adding New Sources

Create a new adapter in `app/adapters/` implementing:

```python
class SourceAdapter:
    name: str
    def fetch_models(self) -> list[RawModelItem]:
        ...
```

Then add it to `default_adapters()` in `app/services/update_pipeline.py`. Prefer official APIs, package SDKs, or structured datasets. Use scraping only when no API is available and the source is trusted.

## Tests

The core service tests use the Python standard library:

```powershell
python -m unittest discover -s tests
```

If `pytest` is installed:

```powershell
pytest
```

## Known Limitations

- Release dates and pricing depend on each source exposing usable metadata.
- Public source calls may be rate-limited or unavailable without credentials.
- Deduplication is intentionally simple and may need provider-specific aliases.
- GraphRAG scoring is heuristic and should be calibrated against real evaluation results.
- Ollama public library tracking is still an extension point; the current adapter covers locally installed tags.
