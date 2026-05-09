Current default sources:

- `OpenRouterAdapter`: reads model data from OpenRouter's models API
- `HuggingFaceAdapter`: reads model data from Hugging Face Hub / `huggingface_hub`
- `LiteLLMCatalogAdapter`: reads a public pricing/context catalog from LiteLLM on GitHub
- `OpenAIAdapter`: reads OpenAI models when an API key is configured
- `AnthropicAdapter`: reads Anthropic models when an API key is configured
- `GeminiAdapter`: reads Google Gemini models when an API key is configured
- `MistralAdapter`: reads Mistral models when an API key is configured
- `OllamaAdapter`: reads local Ollama models from `http://127.0.0.1:11434/api/tags`

`ManualSeedAdapter` still exists, but it is optional. It is useful for testing or for models found from official pages, release notes, or sources that do not have a clean API.

## Step By Step Pipeline

### 1. Get Model Data

Each source adapter fetches model data from one source.

For example:

```text
OpenRouterAdapter  -> OpenRouter models endpoint
HuggingFaceAdapter -> Hugging Face Hub
LiteLLM adapter    -> public pricing/context catalog
Provider adapters  -> OpenAI, Anthropic, Google Gemini, Mistral APIs
OllamaAdapter      -> local Ollama API
```

Each adapter returns raw model items with information such as:

```text
model name
provider
source
source URL
tags
raw metadata
```

### 2. Normalize The Data

Different sources use different field names.

The normalizer converts them into one common format.

Examples:

```text
context_length      -> context_window
pricing.prompt      -> estimated_cost_input
pricing.completion  -> estimated_cost_output
architecture.modality -> modalities
```

This makes all models easier to compare in one table.

### 3. Deduplicate Models

The same model may appear in more than one source.

The app tries to merge duplicates using:

```text
provider + normalized model name
```

For example:

```text
meta-llama/Llama-3.1-8B-Instruct
llama-3.1-8b-instruct
```

These can be treated as the same model if the provider and normalized name match.

### 4. Classify For GraphRAG

The classifier checks model metadata using Python rules.

It does not use an AI agent.

It does not use an LLM API.

It looks at:

```text
model name
model type
tags
parameter size
context window
modalities
local availability
API availability
cost metadata
```

### 5. Score The Model

The app calculates:

```text
GraphRAG score
Hardware score
Cost score
Recommendation
```

Scores go from `1` to `5`.

Higher is better.

### 6. Store In SQLite

The final records are saved in:

```text
data/llm_dashboard.sqlite3
```

### 7. Show In Dashboard

The FastAPI dashboard reads from SQLite and displays the table.

You can search, filter, sort, open detail pages, and export CSV/JSON.

## Simple Pipeline View

```text
Get data
  ↓
Clean data
  ↓
Merge duplicates
  ↓
Apply GraphRAG rules
  ↓
Score model
  ↓
Save to SQLite
  ↓
Show dashboard
```

## How The App Determines GraphRAG Roles

The app uses metadata signals.

It does not truly know model quality like a benchmark would. It uses reasonable rules to decide where a model may fit in a GraphRAG workflow.

Example rules:

```text
Embedding model
=> retrieval

Model name or tags mention rerank/reranker
=> reranking

Context window >= 128000
=> final_answer_generation and graph_validation

Small local model, around 8B or smaller
=> entity_extraction, query_routing, graph_cleaning

Reasoning/coding/tool/math tags
=> relationship_extraction, graph_validation, answer_verification, coding_tooling

Image/audio/multimodal metadata
=> multimodal_document_understanding
```

## GraphRAG Roles

The dashboard can assign roles such as:

```text
entity_extraction
relationship_extraction
graph_cleaning
graph_validation
query_routing
retrieval
reranking
final_answer_generation
answer_verification
coding_tooling
multimodal_document_understanding
```

## How Strengths And Weaknesses Are Created

Strengths and weaknesses come from two places.

### 1. Manual Seed Data

Some model records in `data/manual_models.seed.json` already include notes, strengths, or weaknesses.

Example:

```json
{
  "strengths": ["Small enough for local extraction experiments."],
  "weaknesses": ["License and deployment constraints should be reviewed."]
}
```

### 2. Rule-Based Classifier

The classifier adds strengths and weaknesses from metadata.

Example strengths:

```text
Long context window supports synthesis over large retrieved subgraphs.
Good candidate for local, privacy-preserving extraction and preprocessing.
Reasoning/coding signals make it promising for validation and relationship extraction.
```

Example weaknesses:

```text
License is unknown and should be verified before production use.
Context window is unknown.
Input cost, output cost, and context window are all unknown, so the model is not ready for comparison.
```

## Did The App Use An Agent Or LLM To Decide?

No.

The app does not use an AI agent or LLM API to classify models.

It uses:

```text
metadata + Python rules
```

This is intentional because it is:

```text
explainable
cheap
testable
usable without API keys
easy for the client to inspect
```

An LLM-based classifier could be added later, but the current prototype is rule-based.

## Scoring

All scores are from `1` to `5`.

Higher is better.

## GraphRAG Score

The GraphRAG score estimates how useful the model looks for GraphRAG.

It considers:

```text
number of GraphRAG roles
long context window
local or API availability
reasoning/coding/retrieval tags
cost penalty if API price is high
```

Simple meaning:

```text
5 = very useful for GraphRAG
4 = strong candidate
3 = useful but not top priority
2 = weak or special-case candidate
1 = not enough useful evidence
```

## Hardware Score

Hardware score estimates how easy the model is to run.

Current mapping:

```text
laptop          = 5
desktop_gpu     = 4
workstation_gpu = 3
api_only        = 3
server_gpu      = 2
unknown         = 1
```

Meaning:

```text
laptop = should be practical on a laptop-class local setup
desktop_gpu = needs a stronger desktop GPU
workstation_gpu = needs workstation-class GPU memory
server_gpu = needs server-grade GPU resources
api_only = runs through an API, not local hardware
unknown = not enough hardware metadata
```

## Cost Score

Cost score estimates affordability.

Higher is better.

Important:

```text
Cost score 1 does not mean $1.
Cost score 1 means expensive.
```

Current meaning:

```text
5 = local model or very cheap API
4 = cheap API
3 = medium or unknown API cost
2 = expensive API
1 = very expensive API
```

For API models, the app uses:

```text
estimated input cost per 1M tokens
estimated output cost per 1M tokens
```

If a source gives negative prices like `-1`, the app treats them as `unknown`. For example, OpenRouter's `openrouter/auto` can return `-1`, but that is not a real negative price.

## Recommendation Labels

The app assigns one of three recommendation labels:

```text
test_now
monitor
ignore_for_now
```

### test_now

Means the model looks immediately useful for GraphRAG testing.

Usually it has strong signals like:

```text
many GraphRAG roles
long context
reasoning/coding/retrieval tags
local or API availability
acceptable cost or hardware fit
```

### monitor

Means the model may be useful, but is not the highest priority.

Common reasons:

```text
moderate score
unknown price
special-case model
not enough evidence yet
```

### ignore_for_now

Means the model should not be prioritized right now.

The app now ignores models when all three are unknown:

```text
input cost
output cost
context window
```

This is because there is not enough information to compare the model properly.

## Special Case: openrouter/auto

`openrouter/auto` is not a real single LLM.

It is an OpenRouter router/meta-model entry. OpenRouter chooses another model behind the scenes.

The dashboard now marks it as:

```text
model_type = api_router
recommendation = monitor
```

It should not be compared directly against real models like GPT, Claude, Gemini, Llama, Qwen, or Mistral.

## Example

Suppose the app sees this model:

```text
model_name: qwen3-8b
parameter_size: 8B
local_available: true
tags: reasoning, coding
context_window: 32768
```

The rules infer:

```text
8B + local
=> entity_extraction, query_routing, graph_cleaning

reasoning/coding
=> relationship_extraction, graph_validation, answer_verification, coding_tooling
```

So the dashboard may show:

```text
GraphRAG roles:
entity_extraction
query_routing
graph_cleaning
relationship_extraction
graph_validation
answer_verification
coding_tooling
```

This is rule-based classification, not agent judgement.
