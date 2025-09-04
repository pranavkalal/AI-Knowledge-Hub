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
