# .PHONY: ingest

# ingest:
# 	python -m app.ingest --config configs/ingestion.yaml

.PHONY: ingest eval.extract

ingest:
	mkdir -p logs
	python -m app.ingest --config configs/ingestion.yaml 2>&1 | tee logs/ingest_$$(date +%F_%H-%M-%S).log

eval.extract:
	python -m app.extraction_eval

clean-extract:
	python -m app.clean_extract --in configs/../data/staging/docs.jsonl --out data/staging/cleaned.jsonl

chunk:
	python -m app.chunk --in data/staging/cleaned.jsonl --out data/staging/chunks.jsonl

chunk-stats:
	python scripts_sanity/chunk_stats.py --in data/staging/chunks.jsonl

embed:
	PU=.; PYTHONPATH=$$PU python -m scripts.build_embeddings --chunks data/staging/chunks.jsonl

faiss:
	PU=.; PYTHONPATH=$$PU python -m scripts.build_faiss --vecs data/embeddings/embeddings.npy

Q ?= water efficiency in irrigated cotton
K ?= 5
N ?= 2  # neighbors

query:
	PU=.; PYTHONPATH=$$PU python -m scripts.query_faiss --q "$(Q)" --k $(K) --per-doc 1 --neighbors $(N)


