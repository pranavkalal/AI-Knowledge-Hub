import json
import tempfile
import unittest
from pathlib import Path

from app.adapters.manual_seed_adapter import ManualSeedAdapter
from app.services.export import export_records_csv, export_records_json


class ManualSeedAndExportTests(unittest.TestCase):
    def test_manual_seed_adapter_loads_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_path = Path(tmp) / "seed.json"
            seed_path.write_text(
                json.dumps(
                    [
                        {
                            "model_name": "example/model-7b",
                            "provider": "example",
                            "tags": ["reasoning"],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            items = ManualSeedAdapter(seed_path).fetch_models()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].model_name, "example/model-7b")
            self.assertEqual(items[0].tags, ["reasoning"])

    def test_export_csv_and_json(self):
        records = [
            {
                "model_name": "example/model",
                "provider": "example",
                "source": "manual_seed",
                "model_type": "open_weight",
                "modalities": ["text"],
                "graph_rag_roles": ["retrieval"],
                "graph_rag_score": 4,
            }
        ]
        csv_text = export_records_csv(records)
        json_text = export_records_json(records)
        self.assertIn("model_name", csv_text)
        self.assertIn("example/model", csv_text)
        self.assertEqual(json.loads(json_text)[0]["graph_rag_score"], 4)


if __name__ == "__main__":
    unittest.main()
