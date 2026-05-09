import unittest

from app.services.classify_graphrag import classify_model, infer_hardware_fit


class ClassificationTests(unittest.TestCase):
    def test_embedding_models_are_retrieval_candidates(self):
        record = classify_model(
            {
                "model_name": "bge-large-embedding",
                "provider": "baai",
                "model_type": "embedding_model",
                "modalities": ["embeddings"],
                "api_available": False,
                "local_available": True,
                "parameter_size": "1B",
                "context_window": 512,
                "tags": ["sentence-transformer"],
            }
        )
        self.assertIn("retrieval", record["graph_rag_roles"])
        self.assertGreaterEqual(record["graph_rag_score"], 3)

    def test_small_local_models_get_extraction_roles(self):
        record = classify_model(
            {
                "model_name": "qwen3-8b",
                "provider": "qwen",
                "modalities": ["text"],
                "api_available": False,
                "local_available": True,
                "parameter_size": "8B",
                "context_window": 32768,
                "tags": ["reasoning", "coding"],
            }
        )
        self.assertIn("entity_extraction", record["graph_rag_roles"])
        self.assertIn("query_routing", record["graph_rag_roles"])
        self.assertIn("graph_validation", record["graph_rag_roles"])
        self.assertEqual(record["hardware_fit"], "laptop")

    def test_api_only_long_context_gets_final_answer_role(self):
        record = classify_model(
            {
                "model_name": "openai/gpt-example",
                "provider": "openai",
                "modalities": ["text", "image"],
                "api_available": True,
                "local_available": False,
                "parameter_size": "unknown",
                "context_window": 1000000,
                "tags": ["coding", "vision"],
            }
        )
        self.assertEqual(record["hardware_fit"], "api_only")
        self.assertIn("final_answer_generation", record["graph_rag_roles"])
        self.assertIn("multimodal_document_understanding", record["graph_rag_roles"])
        self.assertEqual(record["recommendation"], "test_now")

    def test_hardware_fit_inference(self):
        self.assertEqual(infer_hardware_fit({"local_available": True, "parameter_size": "3B"}), "laptop")
        self.assertEqual(infer_hardware_fit({"local_available": True, "parameter_size": "14B"}), "desktop_gpu")
        self.assertEqual(infer_hardware_fit({"api_available": True, "local_available": False}), "api_only")

    def test_models_missing_costs_and_context_are_ignored(self):
        record = classify_model(
            {
                "model_name": "unknown/strong-reasoning-model",
                "provider": "unknown",
                "modalities": ["text"],
                "api_available": True,
                "local_available": False,
                "parameter_size": "unknown",
                "context_window": None,
                "estimated_cost_input": None,
                "estimated_cost_output": None,
                "tags": ["reasoning", "coding"],
            }
        )
        self.assertEqual(record["graph_rag_score"], 1)
        self.assertEqual(record["recommendation"], "ignore_for_now")
        self.assertIn("Ignored because input cost", record["classification_notes"][0])


if __name__ == "__main__":
    unittest.main()
