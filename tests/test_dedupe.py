import json
import unittest

from app.services.dedupe import dedupe_records, merge_raw_metadata


class DedupeTests(unittest.TestCase):
    def test_records_with_same_provider_and_normalized_name_merge(self):
        records = [
            {
                "model_name": "meta-llama/Llama-3.1-8B-Instruct",
                "provider": "meta",
                "source": "huggingface",
                "context_window": 128000,
                "modalities": ["text"],
                "graph_rag_roles": ["entity_extraction"],
                "raw_metadata_json": "{\"huggingface\": {\"id\": 1}}",
            },
            {
                "model_name": "llama-3.1-8b-instruct",
                "provider": "meta",
                "source": "manual_seed",
                "context_window": 64000,
                "modalities": ["image"],
                "graph_rag_roles": ["multimodal_document_understanding"],
                "raw_metadata_json": "{\"manual_seed\": {\"id\": 2}}",
            },
        ]
        merged = dedupe_records(records)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["context_window"], 128000)
        self.assertIn("image", merged[0]["modalities"])
        self.assertIn("manual_seed", merged[0]["raw_metadata_json"])

    def test_raw_metadata_merges_source_keys(self):
        merged = merge_raw_metadata('{"a": 1}', '{"b": 2}')
        self.assertEqual(json.loads(merged), {"a": 1, "b": 2})


if __name__ == "__main__":
    unittest.main()
