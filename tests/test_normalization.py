import unittest

from app.adapters.base import RawModelItem
from app.services.normalize import normalize_raw_item


class NormalizationTests(unittest.TestCase):
    def test_openrouter_pricing_and_context_are_normalized(self):
        item = RawModelItem(
            model_name="openai/gpt-test",
            provider="openai",
            source="openrouter",
            raw_metadata={
                "context_length": 128000,
                "created": 1754669020,
                "pricing": {"prompt": "0.000002", "completion": "0.000008"},
                "architecture": {"modality": "text+image"},
            },
        )
        record = normalize_raw_item(item)
        self.assertTrue(record["api_available"])
        self.assertEqual(record["release_date"], "2025-08-08")
        self.assertEqual(record["context_window"], 128000)
        self.assertEqual(record["estimated_cost_input"], 2.0)
        self.assertEqual(record["estimated_cost_output"], 8.0)
        self.assertIn("image", record["modalities"])

    def test_release_date_keeps_iso_date_readable(self):
        item = RawModelItem(
            model_name="openai/gpt-test",
            provider="openai",
            source="manual_seed",
            raw_metadata={"release_date": "2025-03-01T12:30:00Z"},
        )
        record = normalize_raw_item(item)
        self.assertEqual(record["release_date"], "2025-03-01")

    def test_parameter_size_is_inferred_from_name(self):
        item = RawModelItem(model_name="meta-llama/llama-3.1-8b-instruct", provider="meta", source="manual_seed")
        record = normalize_raw_item(item)
        self.assertEqual(record["parameter_size"], "8B")
        self.assertEqual(record["model_family"], "llama")


if __name__ == "__main__":
    unittest.main()
