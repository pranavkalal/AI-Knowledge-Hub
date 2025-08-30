# .PHONY: ingest

# ingest:
# 	python -m app.ingest --config configs/ingestion.yaml

.PHONY: ingest eval.extract

ingest:
	mkdir -p logs
	python -m app.ingest --config configs/ingestion.yaml 2>&1 | tee logs/ingest_$$(date +%F_%H-%M-%S).log

eval.extract:
	python -m app.extraction_eval