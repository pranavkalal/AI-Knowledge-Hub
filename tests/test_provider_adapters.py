import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.litellm_catalog_adapter import LiteLLMCatalogAdapter
from app.adapters.mistral_adapter import MistralAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.services.normalize import normalize_raw_item
from app.services.update_pipeline import default_adapters


class ProviderAdapterTests(unittest.TestCase):
    def test_manual_seed_is_not_in_default_update_adapters(self):
        names = [adapter.name for adapter in default_adapters(include_network=True)]
        self.assertNotIn("manual_seed", names)
        self.assertIn("litellm_catalog", names)
        self.assertIn("openai", names)
        self.assertIn("anthropic", names)
        self.assertIn("google_gemini", names)
        self.assertIn("mistral", names)

    def test_keyed_provider_adapters_skip_without_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(OpenAIAdapter().fetch_models(), [])
            self.assertEqual(AnthropicAdapter().fetch_models(), [])
            self.assertEqual(GeminiAdapter().fetch_models(), [])
            self.assertEqual(MistralAdapter().fetch_models(), [])

    def test_litellm_catalog_maps_price_and_context(self):
        payload = {
            "sample_spec": {},
            "gpt-test": {
                "litellm_provider": "openai",
                "mode": "chat",
                "max_input_tokens": 128000,
                "input_cost_per_token": 0.000002,
                "output_cost_per_token": 0.000008,
                "supports_vision": True,
            },
        }
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
        with patch("urllib.request.urlopen", return_value=response):
            items = LiteLLMCatalogAdapter().fetch_models()
        self.assertEqual(len(items), 1)
        record = normalize_raw_item(items[0])
        self.assertEqual(record["provider"], "openai")
        self.assertEqual(record["context_window"], 128000)
        self.assertEqual(record["estimated_cost_input"], 2.0)
        self.assertEqual(record["estimated_cost_output"], 8.0)
        self.assertIn("image", record["modalities"])


if __name__ == "__main__":
    unittest.main()
