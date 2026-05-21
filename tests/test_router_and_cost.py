import unittest

from app.adapters.base import RawModelItem
from app.services.classify_graphrag import classify_model
from app.services.normalize import normalize_cost_per_million, normalize_raw_item


class RouterAndCostTests(unittest.TestCase):
    def test_negative_source_price_means_unknown(self):
        self.assertIsNone(normalize_cost_per_million("-1"))

    def test_reclassify_converts_per_token_prices_to_per_million(self):
        classified = classify_model(
            {
                "model_name": "openai/gpt-test",
                "provider": "openai",
                "source": "litellm_catalog",
                "api_available": True,
                "local_available": False,
                "estimated_cost_input": 0.00000025,
                "estimated_cost_output": 0.00000125,
                "context_window": 128000,
                "modalities": ["text"],
                "strengths": [],
                "weaknesses": [],
                "graph_rag_roles": [],
            }
        )
        self.assertEqual(classified["estimated_cost_input"], 0.25)
        self.assertEqual(classified["estimated_cost_output"], 1.25)

    def test_openrouter_auto_is_not_scored_as_real_llm(self):
        record = normalize_raw_item(
            RawModelItem(
                model_name="openrouter/auto",
                provider="openrouter",
                source="openrouter",
                raw_metadata={
                    "name": "Auto Router",
                    "description": "Processed by a meta-model and routed to one of dozens of models.",
                    "context_length": 2000000,
                    "architecture": {"tokenizer": "Router", "modality": "text+image->text"},
                    "pricing": {"prompt": "-1", "completion": "-1"},
                },
            )
        )
        classified = classify_model(record)
        self.assertEqual(classified["model_type"], "api_router")
        self.assertEqual(classified["graph_rag_score"], 2)
        self.assertEqual(classified["recommendation"], "monitor")
        self.assertIsNone(classified["estimated_cost_input"])
        self.assertIsNone(classified["estimated_cost_output"])


if __name__ == "__main__":
    unittest.main()
